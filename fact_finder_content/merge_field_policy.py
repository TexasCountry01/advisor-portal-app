"""Validation primitives for versioned merge-field policies.

These helpers are deliberately separate from content resolution and rendering.
Legacy content with a null policy remains unvalidated and readable.
"""
import re
from html.parser import HTMLParser

from django.core.exceptions import ValidationError
from rest_framework import serializers

from cases.fact_finder_data_contract import FactFinderDataContractSerializer


POLICY_SCHEMA_VERSION = 1
_POLICY_PROPERTIES = {'schema_version', 'tokens'}
_TOKEN_PROPERTIES = {
    'token',
    'value_type',
    'format',
    'presence',
    'null',
    'blank',
    'omission',
}
_TOKEN_RE = re.compile(r'\[\[([A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)+)\]\]')
_DELIMITER_RE = re.compile(r'\[\[|\]\]')
_TOKEN_NAME_RE = re.compile(r'^[A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)+$')
_VALUE_TYPES = {'string', 'integer', 'decimal', 'boolean', 'date', 'datetime'}
_FORMATS = {'plain', 'display_mdy', 'display_month_year'}
_FORMAT_TOKEN_COMPATIBILITY = {
    'display_mdy': ('pension.retirement_date', 'string'),
    'display_month_year': ('pension.retirement_month_year', 'string'),
}
_SERIALIZER_VALUE_TYPES = (
    (serializers.BooleanField, 'boolean'),
    (serializers.IntegerField, 'integer'),
    (serializers.DecimalField, 'decimal'),
    (serializers.DateTimeField, 'datetime'),
    (serializers.DateField, 'date'),
    (serializers.ChoiceField, 'string'),
    (serializers.CharField, 'string'),
)


def _contract_field_types():
    """Return supported scalar dotted paths from the canonical Data Contract."""
    field_types = {}

    def visit(fields, prefix=''):
        for name, field in fields.items():
            path = f'{prefix}.{name}' if prefix else name
            if isinstance(field, serializers.ListSerializer):
                continue
            if isinstance(field, serializers.BaseSerializer):
                visit(field.fields, path)
                continue
            for field_class, value_type in _SERIALIZER_VALUE_TYPES:
                if isinstance(field, field_class):
                    field_types[path] = value_type
                    break

    visit(FactFinderDataContractSerializer().fields)
    return field_types


def validate_merge_field_policy(policy):
    """Validate policy structure and return token definitions keyed by token.

    Only required-value policies are supported. Optional/omission semantics are
    intentionally rejected until an approved omission model is implemented.
    """
    if not isinstance(policy, dict):
        raise ValidationError('Policy must be an object.')
    if set(policy) != _POLICY_PROPERTIES:
        raise ValidationError('Policy must contain exactly schema_version and tokens.')
    if type(policy['schema_version']) is not int or policy['schema_version'] != POLICY_SCHEMA_VERSION:
        raise ValidationError('Unsupported merge-field policy schema_version.')
    if not isinstance(policy['tokens'], list):
        raise ValidationError('Policy tokens must be a list.')

    field_types = _contract_field_types()
    definitions = {}
    for index, definition in enumerate(policy['tokens']):
        if not isinstance(definition, dict) or set(definition) != _TOKEN_PROPERTIES:
            raise ValidationError(
                f'Token definition {index} must contain exactly the supported token properties.'
            )

        token = definition['token']
        if not isinstance(token, str) or not _TOKEN_NAME_RE.fullmatch(token):
            raise ValidationError(f'Token definition {index} has invalid dotted token grammar.')
        if token in definitions:
            raise ValidationError(f'Duplicate token definition: {token}.')
        if token not in field_types:
            raise ValidationError(f'Unknown Data Contract merge token: {token}.')

        value_type = definition['value_type']
        if not isinstance(value_type, str) or value_type not in _VALUE_TYPES:
            raise ValidationError(f'Unsupported value_type for {token}.')
        if field_types[token] != value_type:
            raise ValidationError(
                f'value_type for {token} must match the Data Contract type {field_types[token]}.'
            )

        format_name = definition['format']
        if not isinstance(format_name, str) or format_name not in _FORMATS:
            raise ValidationError(f'Unsupported format for {token}.')
        if format_name != 'plain' and _FORMAT_TOKEN_COMPATIBILITY.get(format_name) != (
            token,
            value_type,
        ):
            raise ValidationError(f'Format {format_name} is incompatible with {token}.')

        if definition['presence'] != 'required':
            raise ValidationError('Only required-value policies are currently supported.')
        if definition['null'] != 'error' or definition['blank'] != 'error':
            raise ValidationError('Required tokens must reject null and blank values.')
        if definition['omission'] is not None:
            raise ValidationError('Omission actions are not currently supported.')

        definitions[token] = definition

    return definitions


class _MergeTokenHTMLParser(HTMLParser):
    """Collect text-node tokens and reject tokens in non-text HTML contexts."""

    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.tokens = []
        self.context_errors = []
        self._raw_text_tags = []

    def _check_text(self, data):
        if _DELIMITER_RE.search(_TOKEN_RE.sub('', data)):
            raise ValidationError('Malformed merge-field placeholder delimiter.')
        found = _TOKEN_RE.findall(data)
        if found and self._raw_text_tags:
            self.context_errors.extend(found)
        else:
            self.tokens.extend(found)

    def handle_data(self, data):
        self._check_text(data)

    def handle_starttag(self, tag, attrs):
        for _name, value in attrs:
            if value and _DELIMITER_RE.search(value):
                self.context_errors.extend(_TOKEN_RE.findall(value))
                if not _TOKEN_RE.search(value):
                    raise ValidationError('Malformed merge-field placeholder delimiter.')
        if tag.lower() in {'script', 'style'}:
            self._raw_text_tags.append(tag.lower())

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in self._raw_text_tags:
            self._raw_text_tags = self._raw_text_tags[:self._raw_text_tags.index(tag)]

    def handle_comment(self, data):
        if _DELIMITER_RE.search(data):
            self.context_errors.extend(_TOKEN_RE.findall(data))
            if not _TOKEN_RE.search(data):
                raise ValidationError('Malformed merge-field placeholder delimiter.')

    def handle_decl(self, decl):
        if _DELIMITER_RE.search(decl):
            raise ValidationError('Merge-field placeholders are not allowed in declarations.')


def extract_merge_field_tokens(body_html):
    """Return distinct text-node tokens; reject malformed or unsupported contexts."""
    if not isinstance(body_html, str):
        raise ValidationError('Content HTML must be a string.')

    parser = _MergeTokenHTMLParser()
    parser.feed(body_html)
    parser.close()

    if parser.context_errors:
        raise ValidationError(
            'Merge-field placeholders are only supported in HTML text nodes.'
        )

    all_tokens = _TOKEN_RE.findall(body_html)
    if len(all_tokens) != len(parser.tokens):
        raise ValidationError(
            'Merge-field placeholders are only supported in HTML text nodes.'
        )
    if _DELIMITER_RE.search(_TOKEN_RE.sub('', body_html)):
        raise ValidationError('Malformed merge-field placeholder delimiter.')
    return set(parser.tokens)


def validate_merge_field_template(body_html, policy, required_placeholders=()):
    """Validate HTML tokens against policy and legacy required placeholders."""
    definitions = validate_merge_field_policy(policy)
    html_tokens = extract_merge_field_tokens(body_html)
    policy_tokens = set(definitions)

    missing_required = {
        token for token in required_placeholders
        if f'[[{token}]]' not in body_html
    }
    if missing_required:
        raise ValidationError(
            'Required template placeholders are missing: '
            + ', '.join(sorted(missing_required))
        )
    if not set(required_placeholders).issubset(policy_tokens):
        raise ValidationError(
            'Every required template placeholder must have a policy definition.'
        )

    unknown_tokens = html_tokens - policy_tokens
    if unknown_tokens:
        raise ValidationError(
            'HTML contains tokens absent from the policy: '
            + ', '.join(sorted(unknown_tokens))
        )
    unused_tokens = policy_tokens - html_tokens
    if unused_tokens:
        raise ValidationError(
            'Policy contains tokens absent from the HTML: '
            + ', '.join(sorted(unused_tokens))
        )

    return definitions
