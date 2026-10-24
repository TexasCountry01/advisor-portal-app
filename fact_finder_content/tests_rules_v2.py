from unittest.mock import patch

from django.test import SimpleTestCase

from fact_finder_content.rules import (
    AVAILABLE_FIELDS,
    OP_EQUALS,
    OP_NOT_EQUALS,
    OPERATORS_BY_TYPE,
    RuleEvaluationError,
    RuleOutcome,
    RuleValidationError,
    evaluate_rules,
    evaluate_rules_v2,
)


def rule(field, value, operator=OP_EQUALS):
    return {'field': field, 'operator': operator, 'value': value}


def and_group(*rules):
    return {'all': list(rules)}


def or_groups(*groups):
    return {'any': list(groups)}


class EvaluateRulesV2Tests(SimpleTestCase):
    def setUp(self):
        self.facts = {
            'system': {
                'system_type': 'FERS',
                'retirement_type': 'Regular',
            },
            'computed_flags': {
                'is_special_provision': False,
                'is_deferred_retirement': True,
            },
        }

    def test_match_and_no_match_for_equals(self):
        self.assertIs(
            evaluate_rules_v2(rule('system.system_type', 'FERS'), self.facts).outcome,
            RuleOutcome.MATCH,
        )
        self.assertIs(
            evaluate_rules_v2(rule('system.system_type', 'CSRS'), self.facts).outcome,
            RuleOutcome.NO_MATCH,
        )

    def test_existing_system_and_retirement_fields_evaluate(self):
        self.assertIs(
            evaluate_rules_v2(rule('system.retirement_type', 'Regular'), self.facts).outcome,
            RuleOutcome.MATCH,
        )
        self.assertIs(
            evaluate_rules_v2(
                rule('computed_flags.is_special_provision', False),
                self.facts,
            ).outcome,
            RuleOutcome.MATCH,
        )
        self.assertIs(
            evaluate_rules_v2(
                rule('computed_flags.is_deferred_retirement', True),
                self.facts,
            ).outcome,
            RuleOutcome.MATCH,
        )

    def test_missing_and_explicit_null_fields_are_unknown(self):
        missing = evaluate_rules_v2(rule('system.system_type', 'FERS'), {})
        explicit_null = evaluate_rules_v2(
            rule('system.system_type', 'FERS'),
            {'system': {'system_type': None}},
        )
        self.assertIs(missing.outcome, RuleOutcome.UNKNOWN)
        self.assertEqual(missing.unknown_facts, ('system.system_type',))
        self.assertIs(explicit_null.outcome, RuleOutcome.UNKNOWN)
        self.assertEqual(explicit_null.unknown_facts, ('system.system_type',))

    def test_not_equals_with_missing_or_null_is_unknown(self):
        condition = rule('system.system_type', 'FERS', OP_NOT_EQUALS)
        for facts in ({}, {'system': {'system_type': None}}):
            result = evaluate_rules_v2(condition, facts)
            self.assertIs(result.outcome, RuleOutcome.UNKNOWN)
            self.assertEqual(result.unknown_facts, ('system.system_type',))

    def test_known_false_and_true_booleans_are_distinct_from_unknown(self):
        false_result = evaluate_rules_v2(
            rule('computed_flags.is_special_provision', False),
            self.facts,
        )
        true_result = evaluate_rules_v2(
            rule('computed_flags.is_deferred_retirement', True),
            self.facts,
        )
        unknown_result = evaluate_rules_v2(
            rule('computed_flags.is_special_provision', False),
            {'computed_flags': {'is_special_provision': None}},
        )
        self.assertIs(false_result.outcome, RuleOutcome.MATCH)
        self.assertIs(true_result.outcome, RuleOutcome.MATCH)
        self.assertIs(unknown_result.outcome, RuleOutcome.UNKNOWN)

    def test_known_numeric_zero_is_distinct_from_null(self):
        field_key = 'test.numeric_zero'
        with (
            patch.dict(
                AVAILABLE_FIELDS,
                {field_key: {'label': 'Synthetic Numeric', 'type': 'numeric'}},
            ),
            patch.dict(
                OPERATORS_BY_TYPE,
                {'numeric': [(OP_EQUALS, 'is'), (OP_NOT_EQUALS, 'is not')]},
            ),
        ):
            condition = rule(field_key, 0)
            known_zero = evaluate_rules_v2(
                condition,
                {'test': {'numeric_zero': 0}},
            )
            known_nonzero = evaluate_rules_v2(
                condition,
                {'test': {'numeric_zero': 1}},
            )
            missing = evaluate_rules_v2(condition, {'test': {}})

        self.assertIs(known_zero.outcome, RuleOutcome.MATCH)
        self.assertIs(known_nonzero.outcome, RuleOutcome.NO_MATCH)
        self.assertIs(missing.outcome, RuleOutcome.UNKNOWN)

    def test_and_group_requires_all_rules_to_match(self):
        condition = and_group(
            rule('system.system_type', 'FERS'),
            rule('system.retirement_type', 'Regular'),
        )
        self.assertIs(evaluate_rules_v2(condition, self.facts).outcome, RuleOutcome.MATCH)
        condition['all'][1] = rule('system.retirement_type', 'Deferred')
        self.assertIs(evaluate_rules_v2(condition, self.facts).outcome, RuleOutcome.NO_MATCH)

    def test_or_alternatives_match_when_any_rule_matches(self):
        condition = or_groups(
            and_group(rule('system.system_type', 'CSRS')),
            and_group(rule('system.system_type', 'FERS')),
        )
        self.assertIs(evaluate_rules_v2(condition, self.facts).outcome, RuleOutcome.MATCH)

    def test_or_of_and_groups(self):
        condition = or_groups(
            and_group(
                rule('system.system_type', 'FERS'),
                rule('system.retirement_type', 'Deferred'),
            ),
            and_group(
                rule('system.system_type', 'FERS'),
                rule('system.retirement_type', 'Regular'),
            ),
        )
        self.assertIs(evaluate_rules_v2(condition, self.facts).outcome, RuleOutcome.MATCH)

    def test_no_match_takes_precedence_over_unknown_in_and(self):
        result = evaluate_rules_v2(
            and_group(
                rule('system.retirement_type', 'Regular'),
                rule('system.system_type', 'CSRS'),
            ),
            {'system': {'system_type': 'FERS'}},
        )
        self.assertIs(result.outcome, RuleOutcome.NO_MATCH)
        self.assertEqual(result.unknown_facts, ())

    def test_match_takes_precedence_over_unknown_in_or(self):
        result = evaluate_rules_v2(
            or_groups(
                and_group(rule('system.system_type', 'FERS')),
                and_group(rule('system.retirement_type', 'Regular')),
            ),
            {'system': {'system_type': 'CSRS', 'retirement_type': 'Regular'}},
        )
        self.assertIs(result.outcome, RuleOutcome.MATCH)
        self.assertEqual(result.unknown_facts, ())

    def test_unknown_fact_names_are_combined_for_final_indeterminate_result(self):
        and_result = evaluate_rules_v2(
            and_group(
                rule('system.system_type', 'FERS'),
                rule('system.retirement_type', 'Regular'),
            ),
            {},
        )
        or_result = evaluate_rules_v2(
            or_groups(
                and_group(rule('system.system_type', 'FERS')),
                and_group(rule('system.retirement_type', 'Regular')),
            ),
            {},
        )
        expected = ('system.retirement_type', 'system.system_type')
        self.assertIs(and_result.outcome, RuleOutcome.UNKNOWN)
        self.assertEqual(and_result.unknown_facts, expected)
        self.assertIs(or_result.outcome, RuleOutcome.UNKNOWN)
        self.assertEqual(or_result.unknown_facts, expected)

    def test_unknown_rule_in_or_alternative_is_rejected(self):
        condition = or_groups(
            and_group(rule('system.system_type', 'FERS')),
            and_group(rule('unapproved.fact', 'anything')),
        )
        with self.assertRaises(RuleValidationError):
            evaluate_rules_v2(condition, self.facts)

    def test_invalid_field_operator_and_value_types_are_rejected(self):
        invalid_conditions = [
            rule('unapproved.fact', 'anything'),
            rule('system.system_type', 'FERS', 'contains'),
            rule('system.system_type', True),
            rule('computed_flags.is_special_provision', 'false'),
            rule('system.system_type', ''),
        ]
        for condition in invalid_conditions:
            with self.subTest(condition=condition), self.assertRaises(RuleValidationError):
                evaluate_rules_v2(condition, self.facts)

    def test_malformed_empty_or_and_unsupported_nested_groups_are_rejected(self):
        invalid_conditions = [
            {'any': []},
            {'all': rule('system.system_type', 'FERS')},
            {'any': [{'all': [{'any': []}]}]},
            {'all': [], 'any': []},
            {'not': [rule('system.system_type', 'FERS')]},
        ]
        for condition in invalid_conditions:
            with self.subTest(condition=condition), self.assertRaises(RuleValidationError):
                evaluate_rules_v2(condition, self.facts)

    def test_empty_all_group_is_permitted_as_unconditional_match(self):
        result = evaluate_rules_v2(and_group(), {})
        self.assertIs(result.outcome, RuleOutcome.MATCH)

    def test_known_fact_type_mismatch_is_reported(self):
        with self.assertRaises(RuleEvaluationError):
            evaluate_rules_v2(
                rule('computed_flags.is_special_provision', False),
                {'computed_flags': {'is_special_provision': 0}},
            )

    def test_v1_behavior_remains_boolean_and_unchanged(self):
        self.assertIs(evaluate_rules([], {}), True)
        self.assertIs(
            evaluate_rules(
                [rule('system.system_type', 'FERS', OP_NOT_EQUALS)],
                {},
            ),
            True,
        )
        self.assertIs(
            evaluate_rules(
                [rule('system.system_type', 'FERS')],
                {'system': {'system_type': 'FERS'}},
            ),
            True,
        )
