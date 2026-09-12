"""
Tests for the display-condition rule engine (Option A, step 4).
See fact_finder_content/rules.py for design notes.
"""
from django.test import SimpleTestCase

from fact_finder_content.rules import (
    AVAILABLE_FIELDS,
    coerce_value,
    evaluate_rules,
    field_value_choices,
    validate_rules,
)


class FieldValueChoicesTests(SimpleTestCase):
    def test_choice_field_returns_declared_choices(self):
        self.assertEqual(
            field_value_choices('system.system_type'),
            ['FERS', 'CSRS', 'CSRS Offset', 'Transfers'],
        )

    def test_boolean_field_returns_true_false_strings(self):
        self.assertEqual(field_value_choices('computed_flags.is_wep_applicable'), ['true', 'false'])

    def test_unknown_field_returns_empty_list(self):
        self.assertEqual(field_value_choices('not.a.real.field'), [])


class CoerceValueTests(SimpleTestCase):
    def test_boolean_field_coerces_true_string(self):
        self.assertIs(coerce_value('computed_flags.is_wep_applicable', 'true'), True)

    def test_boolean_field_coerces_false_string(self):
        self.assertIs(coerce_value('computed_flags.is_wep_applicable', 'false'), False)

    def test_choice_field_passes_through_unchanged(self):
        self.assertEqual(coerce_value('system.system_type', 'FERS'), 'FERS')


class ValidateRulesTests(SimpleTestCase):
    def test_valid_choice_rule_passes(self):
        errors = validate_rules([{'field': 'system.system_type', 'operator': 'equals', 'value': 'FERS'}])
        self.assertEqual(errors, [])

    def test_valid_boolean_rule_passes(self):
        errors = validate_rules([{'field': 'computed_flags.is_wep_applicable', 'operator': 'equals', 'value': True}])
        self.assertEqual(errors, [])

    def test_unknown_field_is_rejected(self):
        errors = validate_rules([{'field': 'not.a.real.field', 'operator': 'equals', 'value': 'x'}])
        self.assertEqual(len(errors), 1)
        self.assertIn('unknown field', errors[0])

    def test_invalid_choice_value_is_rejected(self):
        errors = validate_rules([{'field': 'system.system_type', 'operator': 'equals', 'value': 'NotARealSystem'}])
        self.assertEqual(len(errors), 1)
        self.assertIn('not a valid value', errors[0])

    def test_non_boolean_value_for_boolean_field_is_rejected(self):
        errors = validate_rules([{'field': 'computed_flags.is_wep_applicable', 'operator': 'equals', 'value': 'yes'}])
        self.assertEqual(len(errors), 1)
        self.assertIn('must be true or false', errors[0])

    def test_multiple_rules_report_multiple_errors(self):
        errors = validate_rules([
            {'field': 'bogus.field', 'operator': 'equals', 'value': 'x'},
            {'field': 'system.system_type', 'operator': 'equals', 'value': 'Nope'},
        ])
        self.assertEqual(len(errors), 2)


class EvaluateRulesTests(SimpleTestCase):
    def setUp(self):
        self.contract = {
            'system': {'system_type': 'FERS', 'retirement_type': 'Deferred'},
            'computed_flags': {
                'is_fers_or_transfers': True,
                'is_csrs_or_csrs_offset': False,
                'is_deferred_retirement': True,
                'is_wep_applicable': False,
                'is_gpo_applicable': False,
                'hit_full_tsp_match': True,
            },
        }

    def test_empty_rules_always_true(self):
        self.assertTrue(evaluate_rules([], self.contract))

    def test_single_equals_rule_matches(self):
        rules = [{'field': 'system.system_type', 'operator': 'equals', 'value': 'FERS'}]
        self.assertTrue(evaluate_rules(rules, self.contract))

    def test_single_equals_rule_does_not_match(self):
        rules = [{'field': 'system.system_type', 'operator': 'equals', 'value': 'CSRS'}]
        self.assertFalse(evaluate_rules(rules, self.contract))

    def test_not_equals_rule(self):
        rules = [{'field': 'system.system_type', 'operator': 'not_equals', 'value': 'CSRS'}]
        self.assertTrue(evaluate_rules(rules, self.contract))

    def test_boolean_field_rule(self):
        rules = [{'field': 'computed_flags.is_wep_applicable', 'operator': 'equals', 'value': False}]
        self.assertTrue(evaluate_rules(rules, self.contract))

    def test_multiple_rules_are_anded_all_true(self):
        rules = [
            {'field': 'system.system_type', 'operator': 'equals', 'value': 'FERS'},
            {'field': 'computed_flags.is_deferred_retirement', 'operator': 'equals', 'value': True},
        ]
        self.assertTrue(evaluate_rules(rules, self.contract))

    def test_multiple_rules_are_anded_one_false_fails_all(self):
        rules = [
            {'field': 'system.system_type', 'operator': 'equals', 'value': 'FERS'},
            {'field': 'computed_flags.is_wep_applicable', 'operator': 'equals', 'value': True},
        ]
        self.assertFalse(evaluate_rules(rules, self.contract))

    def test_missing_field_in_contract_treated_as_none(self):
        rules = [{'field': 'system.system_type', 'operator': 'not_equals', 'value': 'FERS'}]
        self.assertTrue(evaluate_rules(rules, {}))

    def test_real_world_gpo_scenario_pure_csrs(self):
        """Grounded in the real end-to-end validation: GPO applies only for pure CSRS."""
        csrs_contract = {'system': {'system_type': 'CSRS'}, 'computed_flags': {'is_gpo_applicable': True}}
        csrs_offset_contract = {'system': {'system_type': 'CSRS Offset'}, 'computed_flags': {'is_gpo_applicable': False}}
        rule = [{'field': 'computed_flags.is_gpo_applicable', 'operator': 'equals', 'value': True}]
        self.assertTrue(evaluate_rules(rule, csrs_contract))
        self.assertFalse(evaluate_rules(rule, csrs_offset_contract))

    def test_all_available_fields_are_evaluable(self):
        """Every field in the registry must be usable without raising."""
        for field_key in AVAILABLE_FIELDS:
            rules = [{'field': field_key, 'operator': 'equals', 'value': field_value_choices(field_key)[0]}]
            # Coerce the value the same way the view would before evaluation.
            rules[0]['value'] = coerce_value(field_key, rules[0]['value'])
            evaluate_rules(rules, self.contract)  # must not raise
