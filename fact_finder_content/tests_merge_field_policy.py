from django.core.exceptions import ValidationError
from django.test import TestCase

from cases.fact_finder_data_contract import FactFinderDataContractSerializer
from fact_finder_content.merge_field_policy import (
    extract_merge_field_tokens,
    validate_merge_field_policy,
    validate_merge_field_template,
)
from fact_finder_content.models import (
    ContentBlock,
    ContentBlockGroup,
    ContentBlockVersion,
)


def required_token(token, value_type='string', format_name='plain'):
    return {
        'token': token,
        'value_type': value_type,
        'format': format_name,
        'presence': 'required',
        'null': 'error',
        'blank': 'error',
        'omission': None,
    }


def policy(*definitions):
    return {'schema_version': 1, 'tokens': list(definitions)}


class MergeFieldPolicyValidationTests(TestCase):
    def setUp(self):
        self.group = ContentBlockGroup.objects.create(key='pension', label='Pension')
        self.block = ContentBlock.objects.create(
            key='pension.merge_policy_test',
            group=self.group,
            label='Merge Policy Test',
            required_placeholders=['pension.cola'],
        )

    def version(self, body_html, merge_field_policy=None):
        return ContentBlockVersion(
            block=self.block,
            plan_year=2026,
            body_html=body_html,
            merge_field_policy=merge_field_policy,
        )

    def test_null_policy_keeps_legacy_published_content_valid(self):
        version = self.version('<p>Legacy [[pension.cola]] wording.</p>')
        version.status = ContentBlockVersion.STATUS_PUBLISHED
        version.full_clean()
        version.save()

        loaded = ContentBlockVersion.objects.get(pk=version.pk)
        self.assertIsNone(loaded.merge_field_policy)
        self.assertEqual(loaded.status, ContentBlockVersion.STATUS_PUBLISHED)

    def test_valid_required_token_policy_matches_body_and_required_placeholders(self):
        definitions = validate_merge_field_template(
            '<p>COLA [[pension.cola]]%</p>',
            policy(required_token('pension.cola')),
            ['pension.cola'],
        )

        self.assertEqual(set(definitions), {'pension.cola'})

    def test_policy_requires_exact_top_level_properties(self):
        missing = policy(required_token('pension.cola'))
        del missing['schema_version']
        extra = policy(required_token('pension.cola'))
        extra['description'] = 'not permitted'

        for invalid in (missing, extra):
            with self.subTest(policy=invalid), self.assertRaises(ValidationError):
                validate_merge_field_policy(invalid)

    def test_token_definition_requires_exact_properties(self):
        missing = required_token('pension.cola')
        del missing['format']
        extra = required_token('pension.cola')
        extra['description'] = 'not permitted'

        for invalid in (missing, extra):
            with self.subTest(definition=invalid), self.assertRaises(ValidationError):
                validate_merge_field_policy(policy(invalid))

    def test_duplicate_token_definitions_are_rejected(self):
        with self.assertRaisesMessage(ValidationError, 'Duplicate token definition'):
            validate_merge_field_policy(
                policy(required_token('pension.cola'), required_token('pension.cola'))
            )

    def test_unknown_data_contract_token_is_rejected(self):
        with self.assertRaisesMessage(ValidationError, 'Unknown Data Contract'):
            validate_merge_field_policy(policy(required_token('pension.unknown')))

    def test_invalid_dotted_token_grammar_is_rejected(self):
        with self.assertRaisesMessage(ValidationError, 'invalid dotted token grammar'):
            validate_merge_field_policy(policy(required_token('pension.bad-name')))

    def test_optional_policy_is_rejected(self):
        definition = required_token('pension.cola')
        definition['presence'] = 'optional'

        with self.assertRaisesMessage(ValidationError, 'Only required-value'):
            validate_merge_field_policy(policy(definition))

    def test_unsupported_omission_action_is_rejected(self):
        definition = required_token('pension.cola')
        definition['omission'] = 'empty_string'

        with self.assertRaisesMessage(ValidationError, 'Omission actions'):
            validate_merge_field_policy(policy(definition))

    def test_required_policy_rejects_non_error_null_or_blank_handling(self):
        for property_name, value in (('null', 'approved_omission'), ('blank', 'allow')):
            definition = required_token('pension.cola')
            definition[property_name] = value
            with self.subTest(property=property_name), self.assertRaises(ValidationError):
                validate_merge_field_policy(policy(definition))

    def test_policy_value_type_must_match_data_contract_field_type(self):
        with self.assertRaisesMessage(ValidationError, 'must match the Data Contract type'):
            validate_merge_field_policy(
                policy(required_token('pension.cola', value_type='decimal'))
            )

    def test_unsupported_format_is_rejected(self):
        with self.assertRaisesMessage(ValidationError, 'Unsupported format'):
            validate_merge_field_policy(
                policy(required_token('pension.cola', format_name='decimal_string'))
            )

    def test_html_tokens_must_match_policy_tokens(self):
        with self.assertRaisesMessage(ValidationError, 'absent from the policy'):
            validate_merge_field_template(
                '<p>[[pension.cola]] [[system.birth_year]]</p>',
                policy(required_token('pension.cola')),
            )
        with self.assertRaisesMessage(ValidationError, 'absent from the HTML'):
            validate_merge_field_template(
                '<p>[[pension.cola]]</p>',
                policy(
                    required_token('pension.cola'),
                    required_token('system.birth_year', value_type='integer'),
                ),
            )

    def test_malformed_placeholder_delimiters_are_rejected(self):
        for html in ('<p>[[pension.cola</p>', '<p>pension.cola]]</p>', '<p>[[[]]</p>'):
            with self.subTest(html=html), self.assertRaises(ValidationError):
                extract_merge_field_tokens(html)

    def test_required_placeholders_are_preserved_and_must_have_policy(self):
        with self.assertRaisesMessage(ValidationError, 'Required template placeholders are missing'):
            validate_merge_field_template(
                '<p>No token.</p>',
                policy(required_token('pension.cola')),
                ['pension.cola'],
            )
        with self.assertRaisesMessage(ValidationError, 'must have a policy definition'):
            validate_merge_field_template(
                '<p>[[pension.cola]]</p>',
                policy(),
                ['pension.cola'],
            )

    def test_tokens_are_rejected_outside_supported_html_text_context(self):
        invalid_html = (
            '<p title="[[pension.cola]]">Text</p>',
            '<!-- [[pension.cola]] -->',
            '<script>[[pension.cola]]</script>',
        )
        for html in invalid_html:
            with self.subTest(html=html), self.assertRaisesMessage(
                ValidationError, 'only supported in HTML text nodes'
            ):
                extract_merge_field_tokens(html)

    def test_model_clean_validates_non_legacy_policy(self):
        version = self.version(
            '<p>COLA [[pension.cola]]%</p>',
            policy(required_token('pension.cola')),
        )
        version.full_clean()

    def test_cola_policy_uses_schema_string_without_numeric_restriction(self):
        validate_merge_field_policy(policy(required_token('pension.cola')))
        field = FactFinderDataContractSerializer().fields['pension'].fields['cola']
        self.assertEqual(field.__class__.__name__, 'CharField')
        self.assertEqual(field.run_validation('13.9'), '13.9')
        self.assertEqual(field.run_validation('13.90'), '13.90')
