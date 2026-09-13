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
