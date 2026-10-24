"""
Display-condition rule engine for Fact Finder content blocks (Option A, step 4).

Structured, non-code rules — a list of {field, operator, value} rows, ANDed
together — evaluated against the Fact Finder Data Contract (see
cases/fact_finder_data_contract.py and docs/FACT_FINDER_PDF_MODERNIZATION_ANALYSIS_2026-09-06.md).

Deliberately NOT a free-text expression box and NOT eval()'d: the field list is
a fixed registry below, the operator list is fixed, and values for 'choice'
fields must be one of the field's declared choices. This is what the analysis
doc calls out as removing "an entire class of syntax-error bugs a non-engineer
... can introduce."
"""
from dataclasses import dataclass
from enum import Enum
import math

OP_EQUALS = 'equals'
OP_NOT_EQUALS = 'not_equals'

OPERATORS_BY_TYPE = {
    'choice': [(OP_EQUALS, 'is'), (OP_NOT_EQUALS, 'is not')],
    'boolean': [(OP_EQUALS, 'is'), (OP_NOT_EQUALS, 'is not')],
}

# Registry of fields a display_condition rule may reference, grounded in the
# Fact Finder Data Contract schema (cases/fact_finder_data_contract.py).
# Dotted paths match the contract's nested JSON shape exactly.
AVAILABLE_FIELDS = {
    'system.system_type': {
        'label': 'System Type',
        'type': 'choice',
        'choices': ['FERS', 'CSRS', 'CSRS Offset', 'Transfers'],
    },
    'system.retirement_type': {
        'label': 'Retirement Type',
        'type': 'choice',
        # Matches cases.fact_finder_data_contract.SystemSerializer.RETIREMENT_TYPE_CHOICES
        # exactly — verified 2026-09-13 against benefits-software's real RetirementType
        # lookup table. Only these 3 values exist in real data (no "Optional"/"Disability").
        'choices': ['Regular', 'VERA / DSR', 'Deferred'],
    },
    'computed_flags.is_fers_or_transfers': {
        'label': 'Is FERS or Transfers',
        'type': 'boolean',
    },
    'computed_flags.is_csrs_or_csrs_offset': {
        'label': 'Is CSRS or CSRS Offset',
        'type': 'boolean',
    },
    'computed_flags.is_deferred_retirement': {
        'label': 'Is Deferred Retirement',
        'type': 'boolean',
    },
    'computed_flags.is_wep_applicable': {
        'label': 'WEP Applies',
        'type': 'boolean',
    },
    'computed_flags.is_gpo_applicable': {
        'label': 'GPO Applies',
        'type': 'boolean',
    },
    'computed_flags.hit_full_tsp_match': {
        'label': 'Hit Full TSP Match',
        'type': 'boolean',
    },
    'computed_flags.is_penalty_free_at_59_5': {
        'label': 'Penalty-Free at Age 59.5+ (IRS Early Withdrawal)',
        'type': 'boolean',
    },
    'computed_flags.is_special_provision': {
        'label': 'Is Special Provision (IRS Early Withdrawal)',
        'type': 'boolean',
    },
    'computed_flags.meets_sp_age_service_rules': {
        'label': 'Meets Special Provision Age/Service Rules (IRS Early Withdrawal)',
        'type': 'boolean',
    },
    'computed_flags.meets_age_55_rule': {
        'label': 'Meets Age 55 Rule (IRS Early Withdrawal)',
        'type': 'boolean',
    },
}


def field_value_choices(field_key):
    """Return the list of valid values for a field, for populating a <select>.
    Booleans render as the literal strings 'true'/'false' (form values are always
    strings; callers coerce back to bool via `coerce_value`)."""
    field_def = AVAILABLE_FIELDS.get(field_key)
    if not field_def:
        return []
    if field_def['type'] == 'boolean':
        return ['true', 'false']
    return list(field_def['choices'])


def coerce_value(field_key, raw_value):
    """Coerce a raw (string, e.g. from a form POST) value into the type a
    field expects, so evaluate_rules() can compare it against real Python
    values (booleans, not the strings 'true'/'false')."""
    field_def = AVAILABLE_FIELDS.get(field_key)
    if not field_def:
        return raw_value
    if field_def['type'] == 'boolean':
        if isinstance(raw_value, bool):
            return raw_value
        return str(raw_value).strip().lower() == 'true'
    return raw_value


def validate_rules(rules):
    """Validate a list of rule dicts against AVAILABLE_FIELDS/OPERATORS_BY_TYPE.
    Returns a list of human-readable error strings; empty list = valid."""
    errors = []
    for i, rule in enumerate(rules, start=1):
        field_key = rule.get('field')
        operator = rule.get('operator')
        value = rule.get('value')

        field_def = AVAILABLE_FIELDS.get(field_key)
        if not field_def:
            errors.append(f"Rule {i}: unknown field '{field_key}'.")
            continue

        allowed_ops = [op for op, _ in OPERATORS_BY_TYPE[field_def['type']]]
        if operator not in allowed_ops:
            errors.append(f"Rule {i}: operator '{operator}' is not valid for field '{field_key}'.")

        if field_def['type'] == 'choice' and value not in field_def['choices']:
            errors.append(f"Rule {i}: '{value}' is not a valid value for '{field_key}'.")
        if field_def['type'] == 'boolean' and value not in (True, False):
            errors.append(f"Rule {i}: value for '{field_key}' must be true or false.")

    return errors


def _get_nested(data, dotted_path):
    """Look up a dotted path (e.g. 'computed_flags.is_wep_applicable') in a
    nested dict. Returns None if any segment is missing."""
    value = data
    for part in dotted_path.split('.'):
        if isinstance(value, dict) and part in value:
            value = value[part]
        else:
            return None
    return value


def evaluate_rules(rules, data_contract):
    """Evaluate a list of {field, operator, value} rules (already validated —
    see validate_rules) against a Fact Finder Data Contract dict. All rules are
    ANDed together; an empty rule list evaluates to True (always shown)."""
    for rule in rules:
        actual = _get_nested(data_contract, rule['field'])
        expected = rule['value']
        if rule['operator'] == OP_EQUALS:
            if actual != expected:
                return False
        elif rule['operator'] == OP_NOT_EQUALS:
            if actual == expected:
                return False
        else:
            raise ValueError(f"Unknown operator: {rule['operator']}")
    return True


class RuleOutcome(str, Enum):
    MATCH = 'match'
    NO_MATCH = 'no_match'
    UNKNOWN = 'unknown'


@dataclass(frozen=True)
class RuleEvaluation:
    outcome: RuleOutcome
    unknown_facts: tuple[str, ...] = ()


class RuleValidationError(ValueError):
    """Raised when a v2 condition uses unsupported structure or rule values."""


class RuleEvaluationError(ValueError):
    """Raised when supplied known facts do not conform to their registered types."""


def _validate_v2_rule(rule):
    if not isinstance(rule, dict) or set(rule) != {'field', 'operator', 'value'}:
        raise RuleValidationError('Each rule must contain exactly field, operator, and value.')

    field_key = rule['field']
    if not isinstance(field_key, str) or field_key not in AVAILABLE_FIELDS:
        raise RuleValidationError(f'Unknown rule field: {field_key!r}.')

    field_def = AVAILABLE_FIELDS[field_key]
    field_type = field_def['type']
    operator = rule['operator']
    allowed_operators = OPERATORS_BY_TYPE.get(field_type)
    if not isinstance(operator, str) or allowed_operators is None:
        raise RuleValidationError(f'Unsupported rule field type for {field_key!r}.')
    if operator not in {name for name, _label in allowed_operators}:
        raise RuleValidationError(f'Unsupported operator {operator!r} for {field_key!r}.')

    value = rule['value']
    if field_type == 'choice':
        valid_value = type(value) is str and value in field_def['choices']
    elif field_type == 'boolean':
        valid_value = type(value) is bool
    elif field_type in ('number', 'numeric'):
        valid_value = (
            type(value) in (int, float)
            and (type(value) is int or math.isfinite(value))
        )
    else:
        valid_value = False
    if not valid_value:
        raise RuleValidationError(f'Invalid value type or value for rule field {field_key!r}.')


def validate_condition_v2(condition: object) -> None:
    """Validate a single rule, an AND group, or an OR of AND groups.

    Empty AND groups are permitted as the identity condition (always true),
    consistent with existing ContentSlotVersion configurations. Empty OR
    groups are rejected because they can never match.
    """
    if isinstance(condition, dict) and set(condition) == {'field', 'operator', 'value'}:
        _validate_v2_rule(condition)
        return

    if not isinstance(condition, dict):
        raise RuleValidationError('A condition must be a rule or an all/any object.')

    if set(condition) == {'all'}:
        rules = condition['all']
        if not isinstance(rules, list):
            raise RuleValidationError('"all" must contain a list of rules.')
        for rule in rules:
            _validate_v2_rule(rule)
        return

    if set(condition) == {'any'}:
        alternatives = condition['any']
        if not isinstance(alternatives, list) or not alternatives:
            raise RuleValidationError('"any" must contain at least one AND group.')
        for alternative in alternatives:
            if not isinstance(alternative, dict) or set(alternative) != {'all'}:
                raise RuleValidationError('Each "any" alternative must contain only an "all" list.')
            rules = alternative['all']
            if not isinstance(rules, list):
                raise RuleValidationError('Each "all" group must contain a list of rules.')
            for rule in rules:
                _validate_v2_rule(rule)
        return

    raise RuleValidationError('A condition must contain exactly one supported rule group.')


def _validate_known_fact(field_key, value):
    if value is None:
        return

    field_type = AVAILABLE_FIELDS[field_key]['type']
    if field_type == 'choice':
        is_valid = type(value) is str and value in AVAILABLE_FIELDS[field_key]['choices']
    elif field_type == 'boolean':
        is_valid = type(value) is bool
    elif field_type in ('number', 'numeric'):
        is_valid = (
            type(value) in (int, float)
            and (type(value) is int or math.isfinite(value))
        )
    else:
        is_valid = False
    if not is_valid:
        raise RuleEvaluationError(f'Known fact {field_key!r} has an invalid value type or value.')


def _evaluate_v2_rule(rule, data_contract):
    field_key = rule['field']
    actual = _get_nested(data_contract, field_key)
    if actual is None:
        return RuleEvaluation(RuleOutcome.UNKNOWN, (field_key,))

    _validate_known_fact(field_key, actual)
    expected = rule['value']
    if rule['operator'] == OP_EQUALS:
        matched = actual == expected
    else:
        matched = actual != expected
    outcome = RuleOutcome.MATCH if matched else RuleOutcome.NO_MATCH
    return RuleEvaluation(outcome)


def _combine_and(results):
    if any(result.outcome is RuleOutcome.NO_MATCH for result in results):
        return RuleEvaluation(RuleOutcome.NO_MATCH)
    unknown_facts = tuple(sorted({
        fact
        for result in results
        if result.outcome is RuleOutcome.UNKNOWN
        for fact in result.unknown_facts
    }))
    if unknown_facts:
        return RuleEvaluation(RuleOutcome.UNKNOWN, unknown_facts)
    return RuleEvaluation(RuleOutcome.MATCH)


def _combine_or(results):
    if any(result.outcome is RuleOutcome.MATCH for result in results):
        return RuleEvaluation(RuleOutcome.MATCH)
    unknown_facts = tuple(sorted({
        fact
        for result in results
        if result.outcome is RuleOutcome.UNKNOWN
        for fact in result.unknown_facts
    }))
    if unknown_facts:
        return RuleEvaluation(RuleOutcome.UNKNOWN, unknown_facts)
    return RuleEvaluation(RuleOutcome.NO_MATCH)


def evaluate_rules_v2(condition: dict, data_contract: dict) -> RuleEvaluation:
    """Evaluate a validated v2 condition using MATCH/NO_MATCH/UNKNOWN logic.

    ``condition`` accepts one rule, ``{"all": [rules...]}``, or the stored
    slot format ``{"any": [{"all": [rules...]}...]}``. Unknown-fact names
    are returned only when the final result remains indeterminate.
    """
    validate_condition_v2(condition)
    if not isinstance(data_contract, dict):
        raise RuleEvaluationError('Facts must be supplied as a nested object.')

    if set(condition) == {'field', 'operator', 'value'}:
        return _evaluate_v2_rule(condition, data_contract)
    if set(condition) == {'all'}:
        return _combine_and([
            _evaluate_v2_rule(rule, data_contract)
            for rule in condition['all']
        ])
    return _combine_or([
        _combine_and([
            _evaluate_v2_rule(rule, data_contract)
            for rule in alternative['all']
        ])
        for alternative in condition['any']
    ])
