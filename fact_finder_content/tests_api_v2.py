import json
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from core.models import SystemSettings
from fact_finder_content.models import (
    ContentBlock,
    ContentBlockGroup,
    ContentBlockVersion,
    ContentSlot,
    ContentSlotVersion,
)
from fact_finder_content.tests_api import _valid_data_contract


def content_variant(variant_id, content_key, *rules):
    return {
        'variant_id': variant_id,
        'action': 'content',
        'content_key': content_key,
        'when': {'any': [{'all': list(rules)}]},
    }


def suppress_variant(variant_id, *rules):
    return {
        'variant_id': variant_id,
        'action': 'suppress',
        'when': {'any': [{'all': list(rules)}]},
    }


def rule(field, value, operator='equals'):
    return {'field': field, 'operator': operator, 'value': value}


def required_merge_token(token, value_type='string', format_name='plain'):
    return {
        'token': token,
        'value_type': value_type,
        'format': format_name,
        'presence': 'required',
        'null': 'error',
        'blank': 'error',
        'omission': None,
    }


def merge_policy(*tokens):
    return {'schema_version': 1, 'tokens': list(tokens)}


class ResolveContentV2Tests(TestCase):
    def setUp(self):
        settings_obj = SystemSettings.get_settings()
        settings_obj.benefits_software_api_key = 'test-shared-secret'
        settings_obj.save()
        self.url = reverse('fact_finder_resolve_content_v2')
        self.auth = {'HTTP_AUTHORIZATION': 'Bearer test-shared-secret'}
        self.group = ContentBlockGroup.objects.create(key='pension', label='Pension')
        self.fers = self.create_block('pension.fers_text', '<p>FERS approved.</p>')
        self.csrs = self.create_block('pension.csrs_text', '<p>CSRS approved.</p>')

    def create_block(self, key, html, years=(2026,)):
        block = ContentBlock.objects.create(key=key, group=self.group, label=key)
        for year in years:
            version = ContentBlockVersion.objects.create(
                block=block,
                plan_year=year,
                body_html=html,
            )
            version.submit_for_review()
            version.publish()
        return block

    def create_strict_block(self, key, body_html, tokens, policy_tokens=None, validate=True):
        block = ContentBlock.objects.create(
            key=key,
            group=self.group,
            label=key,
            required_placeholders=list(tokens),
        )
        version = ContentBlockVersion.objects.create(
            block=block,
            plan_year=2026,
            body_html=body_html,
            merge_field_policy=merge_policy(
                *(
                    policy_tokens
                    if policy_tokens is not None
                    else [required_merge_token(token) for token in tokens]
                )
            ),
        )
        if validate:
            version.validate_publishable()
            version.submit_for_review()
            version.publish()
        else:
            # Deliberately corrupt publication fixture for resolver fail-closed tests.
            version.status = ContentBlockVersion.STATUS_PUBLISHED
            version.save()
        return block, version

    def create_slot(self, key, variants, requirement=ContentSlot.REQUIREMENT_REQUIRED, year=2026):
        slot = ContentSlot.objects.create(
            key=key,
            label=key,
            group=self.group,
            requirement=requirement,
        )
        config = ContentSlotVersion.objects.create(
            slot=slot,
            plan_year=year,
            configuration={'variants': variants},
        )
        config.submit_for_review()
        config.publish()
        return slot, config

    def create_c1_slot(self, years=(2025, 2026)):
        deferred_key = 'pension.your_federal_pension_deferred'
        non_deferred_key = 'pension.your_federal_pension_not_deferred'
        blocks = {}
        for key in (deferred_key, non_deferred_key):
            block, _created = ContentBlock.objects.get_or_create(
                key=key,
                defaults={'group': self.group, 'label': key},
            )
            blocks[key] = block

        slot = ContentSlot.objects.create(
            key='pension.c1_resolver_test',
            label='C1 Resolver Test',
            group=self.group,
        )
        for year in years:
            for key, block in blocks.items():
                version = ContentBlockVersion.objects.create(
                    block=block,
                    plan_year=year,
                    body_html=f'<p>{key} {year}</p>',
                )
                version.submit_for_review()
                version.publish()

            config = ContentSlotVersion.objects.create(
                slot=slot,
                plan_year=year,
                configuration={
                    'variants': [
                        content_variant(
                            'deferred',
                            deferred_key,
                            rule('system.retirement_type', 'Deferred'),
                        ),
                        content_variant(
                            'non_deferred',
                            non_deferred_key,
                            rule(
                                'system.retirement_type',
                                'Deferred',
                                operator='not_equals',
                            ),
                        ),
                    ],
                },
            )
            config.submit_for_review()
            config.publish()
        return slot

    def post(self, slots, contract=None, **overrides):
        body = {
            'api_version': 2,
            'plan_year': 2026,
            'slots': slots,
            'data_contract': contract if contract is not None else _valid_data_contract(),
        }
        body.update(overrides)
        return self.client.post(
            self.url,
            data=json.dumps(body),
            content_type='application/json',
            **self.auth,
        )

    def test_selects_fers_wording(self):
        self.create_slot('pension.system_intro', [
            content_variant(
                'fers',
                self.fers.key,
                rule('system.system_type', 'FERS'),
            ),
            content_variant(
                'csrs',
                self.csrs.key,
                rule('system.system_type', 'CSRS'),
            ),
        ])
        response = self.post(['pension.system_intro'])
        result = response.json()['slots'][0]
        self.assertEqual(response.status_code, 200)
        self.assertEqual(result['status'], 'selected')
        self.assertEqual(result['variant_id'], 'fers')
        self.assertEqual(result['content_key'], self.fers.key)
        self.assertEqual(result['html'], '<p>FERS approved.</p>')
        self.assertTrue(result['content_version'])
        self.assertTrue(result['slot_config_version'])

    def test_selects_csrs_wording(self):
        self.create_slot('pension.system_intro', [
            content_variant('fers', self.fers.key, rule('system.system_type', 'FERS')),
            content_variant('csrs', self.csrs.key, rule('system.system_type', 'CSRS')),
        ])
        contract = _valid_data_contract()
        contract['system']['system_type'] = 'CSRS'
        result = self.post(['pension.system_intro'], contract).json()['slots'][0]
        self.assertEqual(result['status'], 'selected')
        self.assertEqual(result['variant_id'], 'csrs')
        self.assertEqual(result['html'], '<p>CSRS approved.</p>')

    def test_c1_supported_retirement_types_follow_existing_blade_branch(self):
        self.create_c1_slot()
        expected = {
            'Regular': 'pension.your_federal_pension_not_deferred',
            'VERA / DSR': 'pension.your_federal_pension_not_deferred',
            'Deferred': 'pension.your_federal_pension_deferred',
        }
        for retirement_type, expected_key in expected.items():
            with self.subTest(retirement_type=retirement_type):
                contract = _valid_data_contract()
                contract['system']['retirement_type'] = retirement_type
                result = self.post(['pension.c1_resolver_test'], contract).json()['slots'][0]
                self.assertEqual(result['status'], 'selected')
                self.assertEqual(result['content_key'], expected_key)
                self.assertNotEqual(result['status'], 'ambiguous')

    def test_c1_missing_or_invalid_retirement_type_fails_before_slot_resolution(self):
        self.create_c1_slot()
        invalid_values = ('missing', None, '', 'Optional')
        with patch('fact_finder_content.views_api.ContentSlot.objects.filter') as slot_filter:
            for retirement_type in invalid_values:
                with self.subTest(retirement_type=retirement_type):
                    contract = _valid_data_contract()
                    if retirement_type == 'missing':
                        del contract['system']['retirement_type']
                    else:
                        contract['system']['retirement_type'] = retirement_type
                    response = self.post(['pension.c1_resolver_test'], contract)
                    self.assertEqual(response.status_code, 400)
                    self.assertEqual(response.json()['error'], 'invalid_data_contract')
            slot_filter.assert_not_called()

    def test_c1_selection_uses_published_content_for_requested_plan_year(self):
        self.create_c1_slot(years=(2025, 2026))
        contract = _valid_data_contract()
        contract['system']['retirement_type'] = 'Deferred'
        for year in (2025, 2026):
            with self.subTest(plan_year=year):
                result = self.post(
                    ['pension.c1_resolver_test'],
                    contract,
                    plan_year=year,
                ).json()
                selected = result['slots'][0]
                self.assertEqual(result['plan_year'], year)
                self.assertEqual(selected['status'], 'selected')
                self.assertEqual(selected['content_key'], 'pension.your_federal_pension_deferred')
                self.assertEqual(
                    selected['html'],
                    f'<p>pension.your_federal_pension_deferred {year}</p>',
                )

    def test_explicit_optional_suppression_returns_no_html(self):
        self.create_slot(
            'pension.optional_note',
            [suppress_variant('not_applicable', rule('computed_flags.is_special_provision', True))],
            ContentSlot.REQUIREMENT_OPTIONAL,
        )
        contract = _valid_data_contract()
        contract['computed_flags']['is_special_provision'] = True
        result = self.post(['pension.optional_note'], contract).json()['slots'][0]
        self.assertEqual(result['status'], 'suppressed')
        self.assertEqual(result['reason_code'], 'explicit_suppression_variant')
        self.assertNotIn('html', result)

    def test_no_matching_variant_is_explicit(self):
        self.create_slot('pension.csrs_only', [
            content_variant('csrs', self.csrs.key, rule('system.system_type', 'CSRS')),
        ])
        result = self.post(['pension.csrs_only']).json()['slots'][0]
        self.assertEqual(result['status'], 'no_match')
        self.assertEqual(result['reason_code'], 'no_variant_matched')

    def test_multiple_matching_variants_are_ambiguous(self):
        self.create_slot('pension.overlap', [
            content_variant('fers_a', self.fers.key, rule('system.system_type', 'FERS')),
            content_variant('fers_b', self.csrs.key, rule('system.system_type', 'FERS')),
        ])
        result = self.post(['pension.overlap']).json()['slots'][0]
        self.assertEqual(result['status'], 'ambiguous')
        self.assertEqual(result['variant_ids'], ['fers_a', 'fers_b'])
        self.assertNotIn('html', result)

    def test_unknown_required_fact_is_reported_without_value(self):
        self.create_slot('pension.special', [
            content_variant(
                'special',
                self.fers.key,
                rule('computed_flags.is_special_provision', True),
            ),
        ])
        contract = _valid_data_contract()
        contract['computed_flags'].pop('is_special_provision', None)
        result = self.post(['pension.special'], contract).json()['slots'][0]
        self.assertEqual(result['status'], 'unknown_facts')
        self.assertEqual(result['unknown_facts'], ['computed_flags.is_special_provision'])

    def test_known_match_plus_unknown_variant_is_indeterminate(self):
        self.create_slot('pension.match_and_unknown', [
            content_variant('known_fers', self.fers.key, rule('system.system_type', 'FERS')),
            content_variant(
                'unknown_special',
                self.csrs.key,
                rule('computed_flags.is_special_provision', True),
            ),
        ])
        contract = _valid_data_contract()
        contract['computed_flags'].pop('is_special_provision', None)
        result = self.post(['pension.match_and_unknown'], contract).json()['slots'][0]
        self.assertEqual(result['status'], 'unknown_facts')
        self.assertEqual(result['unknown_facts'], ['computed_flags.is_special_provision'])

    def test_matching_variant_without_published_wording_is_missing_publication(self):
        unpublished = ContentBlock.objects.create(
            key='pension.unpublished',
            group=self.group,
            label='Unpublished',
        )
        slot = ContentSlot.objects.create(
            key='pension.missing_wording',
            label='Missing wording',
            group=self.group,
        )
        config = ContentSlotVersion.objects.create(
            slot=slot,
            plan_year=2026,
            configuration={
                'variants': [
                    content_variant('fers', unpublished.key, rule('system.system_type', 'FERS')),
                ],
            },
            status=ContentSlotVersion.STATUS_PUBLISHED,
        )
        config.save()
        result = self.post(['pension.missing_wording']).json()['slots'][0]
        self.assertEqual(result['status'], 'missing_publication')
        self.assertEqual(result['content_key'], unpublished.key)
        self.assertEqual(result['plan_year'], 2026)

    def test_missing_published_slot_configuration(self):
        ContentSlot.objects.create(key='pension.unpublished_config', label='Missing', group=self.group)
        result = self.post(['pension.unpublished_config']).json()['slots'][0]
        self.assertEqual(result['status'], 'configuration_missing')
        self.assertEqual(result['reason_code'], 'no_published_slot_configuration')

    def test_configuration_published_only_for_another_year_is_missing(self):
        slot = ContentSlot.objects.create(key='pension.year_2025_only', label='2025 only', group=self.group)
        config = ContentSlotVersion.objects.create(
            slot=slot,
            plan_year=2025,
            configuration={'variants': [content_variant('always', self.fers.key)]},
            status=ContentSlotVersion.STATUS_PUBLISHED,
        )
        config.save()
        result = self.post(['pension.year_2025_only']).json()['slots'][0]
        self.assertEqual(result['status'], 'configuration_missing')
        self.assertEqual(result['reason_code'], 'no_published_slot_configuration')

    def test_missing_slot_definition(self):
        result = self.post(['pension.does_not_exist']).json()['slots'][0]
        self.assertEqual(result['status'], 'configuration_missing')
        self.assertEqual(result['reason_code'], 'slot_not_found')

    def test_inactive_slot_is_not_resolved(self):
        slot, _config = self.create_slot(
            'pension.inactive',
            [content_variant('fers', self.fers.key, rule('system.system_type', 'FERS'))],
        )
        slot.is_active = False
        slot.save()
        result = self.post(['pension.inactive']).json()['slots'][0]
        self.assertEqual(result['status'], 'configuration_missing')
        self.assertEqual(result['reason_code'], 'slot_inactive')

    def test_calculation_driven_slot_does_not_return_content_or_suppression(self):
        self.create_slot(
            'pension.calculated',
            [],
            ContentSlot.REQUIREMENT_CALCULATION_DRIVEN,
        )
        result = self.post(['pension.calculated']).json()['slots'][0]
        self.assertEqual(result['status'], 'no_match')
        self.assertEqual(result['reason_code'], 'calculation_driven_slot')
        self.assertNotIn('html', result)
        self.assertNotIn('variant_id', result)

    def test_plan_years_are_isolated(self):
        block = self.create_block('pension.both_years', '<p>Year wording.</p>', years=(2025, 2026))
        slot = ContentSlot.objects.create(key='pension.yearly', label='Yearly', group=self.group)
        for year in (2025, 2026):
            config = ContentSlotVersion.objects.create(
                slot=slot,
                plan_year=year,
                configuration={
                    'variants': [
                        content_variant('always', block.key),
                    ],
                },
            )
            config.submit_for_review()
            config.publish()
        body = {
            'api_version': 2,
            'plan_year': 2025,
            'slots': ['pension.yearly'],
            'data_contract': _valid_data_contract(),
        }
        result = self.client.post(
            self.url,
            data=json.dumps(body),
            content_type='application/json',
            **self.auth,
        ).json()
        self.assertEqual(result['plan_year'], 2025)
        self.assertEqual(result['slots'][0]['status'], 'selected')

    def test_unconditional_variant_can_be_selected(self):
        self.create_slot('pension.unconditional', [
            content_variant('always', self.fers.key),
        ])
        result = self.post(['pension.unconditional']).json()['slots'][0]
        self.assertEqual(result['status'], 'selected')
        self.assertEqual(result['variant_id'], 'always')

    def test_unconditional_variant_overlapping_other_match_is_ambiguous(self):
        self.create_slot('pension.unconditional_overlap', [
            content_variant('always', self.fers.key),
            content_variant('fers', self.csrs.key, rule('system.system_type', 'FERS')),
        ])
        result = self.post(['pension.unconditional_overlap']).json()['slots'][0]
        self.assertEqual(result['status'], 'ambiguous')

    def test_invalid_published_configuration_is_server_error_without_employee_data(self):
        _slot, config = self.create_slot(
            'pension.invalid_configuration',
            [content_variant('fers', self.fers.key, rule('system.system_type', 'FERS'))],
        )
        config.configuration = {'variants': [{'action': 'execute', 'expression': 'unsafe'}]}
        config.save()
        response = self.post(['pension.invalid_configuration'])
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()['error'], 'invalid_published_configuration')
        self.assertNotIn('12345', response.content.decode())

    def test_invalid_employee_fact_type_is_request_error_without_echoing_value(self):
        contract = _valid_data_contract()
        contract['system']['system_type'] = 'private-invalid-value'
        response = self.post([], contract)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'invalid_data_contract')
        self.assertNotIn('private-invalid-value', response.content.decode())

    def test_invalid_optional_boolean_fact_is_rejected_without_echoing_value(self):
        self.create_slot('pension.strict_boolean', [
            content_variant(
                'not_special',
                self.fers.key,
                rule('computed_flags.is_special_provision', False),
            ),
        ])
        contract = _valid_data_contract()
        contract['computed_flags']['is_special_provision'] = 'false'
        response = self.post(['pension.strict_boolean'], contract)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'invalid_data_contract')
        self.assertNotIn('false', response.content.decode())

    def test_duplicate_slot_keys_are_rejected(self):
        response = self.post(['pension.x', 'pension.x'])
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'duplicate_slots')

    def test_malformed_json_and_missing_request_fields_are_rejected(self):
        malformed = self.client.post(
            self.url,
            data='{',
            content_type='application/json',
            **self.auth,
        )
        missing_fields = self.client.post(
            self.url,
            data=json.dumps({'api_version': 2}),
            content_type='application/json',
            **self.auth,
        )
        self.assertEqual(malformed.status_code, 400)
        self.assertEqual(malformed.json()['error'], 'invalid_request')
        self.assertEqual(missing_fields.status_code, 400)
        self.assertEqual(missing_fields.json()['error'], 'invalid_request')

    def test_invalid_api_version_is_rejected(self):
        response = self.post([], api_version=3)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'unsupported_api_version')

    def test_invalid_plan_year_is_rejected(self):
        for year in (True, 0, '2026'):
            with self.subTest(year=year):
                response = self.post([], plan_year=year)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json()['error'], 'invalid_request')

    def test_invalid_data_contract_is_rejected(self):
        contract = _valid_data_contract()
        contract['system']['system_type'] = 'invalid-private-value'
        response = self.post([], contract)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'invalid_data_contract')
        self.assertNotIn('invalid-private-value', response.content.decode())

    def test_unauthorized_request_is_rejected(self):
        response = self.client.post(
            self.url,
            data=json.dumps({
                'api_version': 2,
                'plan_year': 2026,
                'slots': [],
                'data_contract': _valid_data_contract(),
            }),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['error'], 'unauthorized')

    def test_multiple_slots_have_independent_outcomes_and_preserve_request_order(self):
        self.create_slot('pension.selected', [
            content_variant('fers', self.fers.key, rule('system.system_type', 'FERS')),
        ])
        self.create_slot('pension.suppressed', [
            suppress_variant('suppress', rule('computed_flags.is_special_provision', True)),
        ], ContentSlot.REQUIREMENT_OPTIONAL)
        self.create_slot('pension.no_match', [
            content_variant('csrs', self.csrs.key, rule('system.system_type', 'CSRS')),
        ])
        contract = _valid_data_contract()
        contract['computed_flags']['is_special_provision'] = True
        result = self.post(
            ['pension.no_match', 'pension.suppressed', 'pension.selected'],
            contract,
        ).json()
        self.assertEqual(
            [entry['slot_key'] for entry in result['slots']],
            ['pension.no_match', 'pension.suppressed', 'pension.selected'],
        )
        self.assertEqual(
            [entry['status'] for entry in result['slots']],
            ['no_match', 'suppressed', 'selected'],
        )
        self.assertIn('resolution_id', result)
        self.assertEqual(result['api_version'], 2)

    def test_merge_substitution_preserves_html_and_unresolved_tokens(self):
        block = self.create_block(
            'pension.merge',
            '<p><strong>Born [[system.birth_year]]</strong> [[unknown.token]]</p>',
        )
        self.create_slot('pension.merge_slot', [
            content_variant('always', block.key),
        ])
        result = self.post(['pension.merge_slot']).json()['slots'][0]
        self.assertEqual(
            result['html'],
            '<p><strong>Born 1968</strong> [[unknown.token]]</p>',
        )

    def test_merge_substitution_preserves_existing_boolean_and_numeric_formatters(self):
        block = self.create_block(
            'pension.formatted_merge',
            '<p>[[computed_flags.is_special_provision]] [[tsp.deff_limit]]</p>',
        )
        self.create_slot('pension.formatted_merge_slot', [
            content_variant('always', block.key),
        ])
        contract = _valid_data_contract()
        contract['computed_flags']['is_special_provision'] = False
        contract['tsp']['deff_limit'] = '1234.00'
        result = self.post(['pension.formatted_merge_slot'], contract).json()['slots'][0]
        self.assertEqual(result['html'], '<p> 1,234</p>')

    def test_html_is_not_sanitized_or_reformatted_during_resolution(self):
        raw_html = '<table><tr><td width="50%">A &amp; B</td></tr></table>'
        block = self.create_block('pension.literal_html', raw_html)
        stored_html = block.published_version_for(2026).body_html
        self.create_slot('pension.literal_html_slot', [
            content_variant('always', block.key),
        ])
        result = self.post(['pension.literal_html_slot']).json()['slots'][0]
        self.assertEqual(result['html'], stored_html)

    def test_v1_api_route_and_response_shape_remain_unchanged(self):
        self.assertEqual(reverse('fact_finder_resolve_content'), '/api/fact-finder/resolve-content/')
        block = ContentBlock.objects.create(
            key='pension.v1_compat',
            group=self.group,
            label='V1 compatibility',
        )
        version = ContentBlockVersion.objects.create(
            block=block,
            plan_year=2026,
            body_html='<p>Legacy response.</p>',
        )
        version.submit_for_review()
        version.publish()
        response = self.client.post(
            reverse('fact_finder_resolve_content'),
            data=json.dumps({
                'plan_year': 2026,
                'data_contract': _valid_data_contract(),
            }),
            content_type='application/json',
            **self.auth,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            set(response.json()),
            {'blocks'},
        )
        self.assertIn(
            'pension.v1_compat',
            [entry['key'] for entry in response.json()['blocks']],
        )

    def create_strict_c1_slot(self):
        deferred_key = 'pension.strict_c1_deferred'
        non_deferred_key = 'pension.strict_c1_not_deferred'
        self.create_strict_block(
            deferred_key,
            '<p>Deferred COLA [[pension.cola]]%</p>',
            ['pension.cola'],
        )
        self.create_strict_block(
            non_deferred_key,
            '<p>Date [[pension.retirement_date]]; COLA [[pension.cola]]%</p>',
            ['pension.retirement_date', 'pension.cola'],
            [
                required_merge_token('pension.retirement_date', format_name='display_mdy'),
                required_merge_token('pension.cola'),
            ],
        )
        return self.create_slot('pension.strict_c1', [
            content_variant(
                'deferred',
                deferred_key,
                rule('system.retirement_type', 'Deferred'),
            ),
            content_variant(
                'not_deferred',
                non_deferred_key,
                rule('system.retirement_type', 'Deferred', operator='not_equals'),
            ),
        ])

    def test_supported_capability_is_echoed_and_missing_policy_fails_without_html(self):
        self.create_slot('pension.strict_legacy_block', [
            content_variant('always', self.fers.key),
        ])
        response = self.post(
            ['pension.strict_legacy_block'],
            capabilities=['merge_field_validation_v1'],
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['capabilities'], ['merge_field_validation_v1'])
        decision = payload['slots'][0]
        self.assertEqual(decision['status'], 'invalid_published_content')
        self.assertEqual(decision['reason_code'], 'merge_policy_missing')
        self.assertNotIn('html', decision)

    def test_unsupported_and_malformed_capability_declarations_fail_safely(self):
        for capabilities, expected_error in (
            (['future_capability'], 'unsupported_capability'),
            ('merge_field_validation_v1', 'invalid_request'),
            ([1], 'invalid_request'),
            (['merge_field_validation_v1', 'merge_field_validation_v1'], 'invalid_request'),
        ):
            with self.subTest(capabilities=capabilities):
                response = self.post([], capabilities=capabilities)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json()['error'], expected_error)

    def test_strict_policy_substitutes_and_html_escapes_values_preserving_entities(self):
        block, _version = self.create_strict_block(
            'pension.strict_escape',
            '<p>[[pension.cola]] &amp; fixed</p>',
            ['pension.cola'],
        )
        self.create_slot('pension.strict_escape_slot', [
            content_variant('always', block.key),
        ])
        contract = _valid_data_contract()
        contract['pension']['cola'] = '<13 & 90>'

        response = self.post(
            ['pension.strict_escape_slot'],
            contract,
            capabilities=['merge_field_validation_v1'],
        )
        decision = response.json()['slots'][0]

        self.assertEqual(response.status_code, 200)
        self.assertEqual(decision['status'], 'selected')
        self.assertEqual(decision['html'], '<p>&lt;13 &amp; 90&gt; &amp; fixed</p>')

    def test_strict_cola_preserves_textual_precision(self):
        block, _version = self.create_strict_block(
            'pension.strict_cola_precision',
            '<p>[[pension.cola]]%</p>',
            ['pension.cola'],
        )
        self.create_slot('pension.strict_cola_precision_slot', [
            content_variant('always', block.key),
        ])

        for cola in ('13.9', '13.90'):
            contract = _valid_data_contract()
            contract['pension']['cola'] = cola
            with self.subTest(cola=cola):
                decision = self.post(
                    ['pension.strict_cola_precision_slot'],
                    contract,
                    capabilities=['merge_field_validation_v1'],
                ).json()['slots'][0]
                self.assertEqual(decision['status'], 'selected')
                self.assertEqual(decision['html'], f'<p>{cola}%</p>')

    def test_strict_missing_null_blank_and_invalid_values_return_typed_failures(self):
        block, _version = self.create_strict_block(
            'pension.strict_required_value',
            '<p>COLA [[pension.cola]]%</p>',
            ['pension.cola'],
        )
        self.create_slot('pension.strict_required_value_slot', [
            content_variant('always', block.key),
        ])
        cases = []

        missing = _valid_data_contract()
        missing['pension']['cola'] = '13.9'
        del missing['pension']['cola']
        cases.append((missing, 'missing_required_merge_value'))
        null_value = _valid_data_contract()
        null_value['pension']['cola'] = None
        cases.append((null_value, 'null_required_merge_value'))
        empty_value = _valid_data_contract()
        empty_value['pension']['cola'] = ''
        cases.append((empty_value, 'blank_required_merge_value'))
        whitespace_value = _valid_data_contract()
        whitespace_value['pension']['cola'] = '   '
        cases.append((whitespace_value, 'blank_required_merge_value'))
        invalid_type = _valid_data_contract()
        invalid_type['pension']['cola'] = 13.9
        cases.append((invalid_type, 'invalid_merge_value'))

        for contract, reason in cases:
            with self.subTest(reason=reason):
                response = self.post(
                    ['pension.strict_required_value_slot'],
                    contract,
                    capabilities=['merge_field_validation_v1'],
                )
                decision = response.json()['slots'][0]
                self.assertEqual(response.status_code, 200)
                self.assertEqual(decision['status'], 'merge_field_error')
                self.assertEqual(decision['reason_code'], reason)
                self.assertNotIn('html', decision)
                self.assertEqual(decision['merge_field_errors'], [
                    {'token': 'pension.cola', 'reason_code': reason},
                ])

        integer_block, _version = self.create_strict_block(
            'system.strict_integer_type',
            '<p>Birth year [[system.birth_year]]</p>',
            ['system.birth_year'],
            [required_merge_token('system.birth_year', value_type='integer')],
        )
        self.create_slot('system.strict_integer_type_slot', [
            content_variant('always', integer_block.key),
        ])
        string_integer = _valid_data_contract()
        string_integer['system']['birth_year'] = '1968'
        integer_decision = self.post(
            ['system.strict_integer_type_slot'],
            string_integer,
            capabilities=['merge_field_validation_v1'],
        ).json()['slots'][0]
        self.assertEqual(integer_decision['status'], 'merge_field_error')
        self.assertEqual(integer_decision['reason_code'], 'invalid_merge_value')
        self.assertNotIn('html', integer_decision)

        blank_block, _version = self.create_strict_block(
            'fltcip.strict_blank_value',
            '<p>Waiting [[fltcip.waiting_period]]</p>',
            ['fltcip.waiting_period'],
        )
        self.create_slot('fltcip.strict_blank_value_slot', [
            content_variant('always', blank_block.key),
        ])
        blank = _valid_data_contract()
        blank['fltcip'] = {'waiting_period': '   '}
        blank_decision = self.post(
            ['fltcip.strict_blank_value_slot'],
            blank,
            capabilities=['merge_field_validation_v1'],
        ).json()['slots'][0]
        self.assertEqual(blank_decision['status'], 'merge_field_error')
        self.assertEqual(blank_decision['reason_code'], 'blank_required_merge_value')
        self.assertNotIn('html', blank_decision)

    def test_strict_retirement_date_blank_and_malformed_values_fail_without_html(self):
        block, _version = self.create_strict_block(
            'pension.strict_required_retirement_date',
            '<p>Retirement date [[pension.retirement_date]]</p>',
            ['pension.retirement_date'],
            [required_merge_token('pension.retirement_date', format_name='display_mdy')],
        )
        self.create_slot('pension.strict_required_retirement_date_slot', [
            content_variant('always', block.key),
        ])

        cases = (
            ('', 'blank_required_merge_value'),
            ('   ', 'blank_required_merge_value'),
            ('not-a-date', 'invalid_merge_value'),
        )
        for value, reason in cases:
            contract = _valid_data_contract()
            contract['pension']['retirement_date'] = value
            with self.subTest(value=value):
                response = self.post(
                    ['pension.strict_required_retirement_date_slot'],
                    contract,
                    capabilities=['merge_field_validation_v1'],
                )
                decision = response.json()['slots'][0]
                self.assertEqual(response.status_code, 200)
                self.assertEqual(decision['status'], 'merge_field_error')
                self.assertEqual(decision['reason_code'], reason)
                self.assertNotIn('html', decision)

        valid = _valid_data_contract()
        valid['pension']['retirement_date'] = '12/31/2026'
        valid_decision = self.post(
            ['pension.strict_required_retirement_date_slot'],
            valid,
            capabilities=['merge_field_validation_v1'],
        ).json()['slots'][0]
        self.assertEqual(valid_decision['status'], 'selected')
        self.assertEqual(valid_decision['html'], '<p>Retirement date 12/31/2026</p>')

    def test_blank_pension_values_remain_rejected_without_strict_capability(self):
        block, _version = self.create_strict_block(
            'pension.blank_compatibility',
            '<p>COLA [[pension.cola]]; date [[pension.retirement_date]]</p>',
            ['pension.cola', 'pension.retirement_date'],
            [
                required_merge_token('pension.cola'),
                required_merge_token('pension.retirement_date', format_name='display_mdy'),
            ],
        )
        self.create_slot('pension.blank_compatibility_slot', [
            content_variant('always', block.key),
        ])
        v1_url = reverse('fact_finder_resolve_content')

        for field in ('cola', 'retirement_date'):
            for value in ('', '   '):
                contract = _valid_data_contract()
                contract['pension']['cola'] = '13.90'
                contract['pension']['retirement_date'] = '12/31/2026'
                contract['pension'][field] = value
                with self.subTest(field=field, value=value):
                    legacy_v2 = self.post(
                        ['pension.blank_compatibility_slot'],
                        contract,
                    )
                    self.assertEqual(legacy_v2.status_code, 400)
                    self.assertEqual(legacy_v2.json()['error'], 'invalid_data_contract')

                    legacy_v1 = self.client.post(
                        v1_url,
                        data=json.dumps({'plan_year': 2026, 'data_contract': contract}),
                        content_type='application/json',
                        **self.auth,
                    )
                    self.assertEqual(legacy_v1.status_code, 400)
                    self.assertEqual(legacy_v1.json()['error'], 'Invalid data_contract')

    def test_strict_blank_acceptance_does_not_relax_other_contract_validation(self):
        malformed_nested = _valid_data_contract()
        malformed_nested['pension'] = []
        malformed_response = self.post(
            [],
            malformed_nested,
            capabilities=['merge_field_validation_v1'],
        )
        self.assertEqual(malformed_response.status_code, 400)
        self.assertEqual(malformed_response.json()['error'], 'invalid_data_contract')

        invalid_unrelated_field = _valid_data_contract()
        invalid_unrelated_field['system']['retirement_type'] = 'Unknown'
        invalid_response = self.post(
            [],
            invalid_unrelated_field,
            capabilities=['merge_field_validation_v1'],
        )
        self.assertEqual(invalid_response.status_code, 400)
        self.assertEqual(invalid_response.json()['error'], 'invalid_data_contract')

    def test_strict_false_boolean_cannot_become_an_implicit_empty_string(self):
        block, _version = self.create_strict_block(
            'pension.strict_boolean_value',
            '<p>Special provision: [[computed_flags.is_special_provision]]</p>',
            ['computed_flags.is_special_provision'],
            [
                required_merge_token(
                    'computed_flags.is_special_provision',
                    value_type='boolean',
                ),
            ],
        )
        self.create_slot('pension.strict_boolean_value_slot', [
            content_variant('always', block.key),
        ])
        contract = _valid_data_contract()
        contract['computed_flags']['is_special_provision'] = False

        decision = self.post(
            ['pension.strict_boolean_value_slot'],
            contract,
            capabilities=['merge_field_validation_v1'],
        ).json()['slots'][0]

        self.assertEqual(decision['status'], 'merge_field_error')
        self.assertEqual(decision['reason_code'], 'invalid_merge_value')
        self.assertNotIn('html', decision)

    def test_strict_unknown_and_malformed_tokens_fail_without_html(self):
        unknown, _version = self.create_strict_block(
            'pension.strict_unknown_token',
            '<p>[[pension.cola]] [[system.unknown_fact]]</p>',
            ['pension.cola'],
            validate=False,
        )
        malformed = ContentBlock.objects.create(
            key='pension.strict_malformed_token',
            group=self.group,
            label='Malformed token',
            required_placeholders=['pension.cola'],
        )
        malformed_version = ContentBlockVersion.objects.create(
            block=malformed,
            plan_year=2026,
            body_html='<p>[[pension.cola</p>',
            merge_field_policy=merge_policy(required_merge_token('pension.cola')),
        )
        malformed_version.status = ContentBlockVersion.STATUS_PUBLISHED
        malformed_version.save()
        self.create_slot('pension.strict_token_errors', [
            content_variant('unknown', unknown.key, rule('system.system_type', 'FERS')),
        ])
        self.create_slot('pension.strict_malformed_slot', [
            content_variant('malformed', malformed.key),
        ])

        cases = (
            ('pension.strict_token_errors', 'unknown_merge_token'),
            ('pension.strict_malformed_slot', 'invalid_published_content'),
        )
        for slot_key, reason in cases:
            with self.subTest(slot=slot_key):
                decision = self.post(
                    [slot_key],
                    capabilities=['merge_field_validation_v1'],
                ).json()['slots'][0]
                self.assertEqual(decision['status'], 'invalid_published_content')
                self.assertEqual(decision['reason_code'], reason)
                self.assertNotIn('html', decision)

    def test_strict_rejects_tokens_in_unsupported_html_context(self):
        block, _version = self.create_strict_block(
            'pension.strict_attribute_token',
            '<p title="[[pension.cola]]">Value</p>',
            ['pension.cola'],
            validate=False,
        )
        self.create_slot('pension.strict_attribute_slot', [
            content_variant('always', block.key),
        ])
        # The fixture bypasses model validation to exercise the runtime guard
        # against corrupt or historically published content.
        decision = self.post(
            ['pension.strict_attribute_slot'],
            capabilities=['merge_field_validation_v1'],
        ).json()['slots'][0]
        self.assertEqual(decision['status'], 'invalid_published_content')
        self.assertNotIn('html', decision)

    def test_strict_c1_regular_vera_and_deferred_selection_require_only_selected_tokens(self):
        self.create_strict_c1_slot()
        scenarios = (
            ('Regular', 'not_deferred', 'pension.strict_c1_not_deferred'),
            ('VERA / DSR', 'not_deferred', 'pension.strict_c1_not_deferred'),
            ('Deferred', 'deferred', 'pension.strict_c1_deferred'),
        )
        for retirement_type, variant_id, content_key in scenarios:
            contract = _valid_data_contract()
            contract['system']['retirement_type'] = retirement_type
            contract['pension']['cola'] = '13.90'
            contract['pension']['retirement_date'] = '12/31/2026'
            decision = self.post(
                ['pension.strict_c1'],
                contract,
                capabilities=['merge_field_validation_v1'],
            ).json()['slots'][0]
            with self.subTest(retirement_type=retirement_type):
                self.assertEqual(decision['status'], 'selected')
                self.assertEqual(decision['variant_id'], variant_id)
                self.assertEqual(decision['content_key'], content_key)
                self.assertIn('13.90%', decision['html'])
                self.assertEqual(
                    '12/31/2026' in decision['html'],
                    retirement_type != 'Deferred',
                )

        deferred = _valid_data_contract()
        deferred['system']['retirement_type'] = 'Deferred'
        deferred['pension']['cola'] = '13.9'
        deferred_decision = self.post(
            ['pension.strict_c1'],
            deferred,
            capabilities=['merge_field_validation_v1'],
        ).json()['slots'][0]
        self.assertEqual(deferred_decision['status'], 'selected')
        self.assertNotIn('retirement_date', deferred_decision['html'])

    def test_strict_multislot_results_keep_independent_success_failure_and_suppression(self):
        selected, _version = self.create_strict_block(
            'pension.strict_multi_success',
            '<p>COLA [[pension.cola]]</p>',
            ['pension.cola'],
        )
        legacy = self.create_block('pension.strict_multi_legacy', '<p>legacy</p>')
        self.create_slot('pension.strict_multi_selected', [
            content_variant('always', selected.key),
        ])
        self.create_slot('pension.strict_multi_failed', [
            content_variant('always', legacy.key),
        ])
        self.create_slot('pension.strict_multi_suppressed', [
            suppress_variant('not_applicable'),
        ], ContentSlot.REQUIREMENT_OPTIONAL)
        self.create_slot('pension.strict_multi_no_match', [
            content_variant(
                'csrs_only',
                selected.key,
                rule('system.system_type', 'CSRS'),
            ),
        ])

        contract = _valid_data_contract()
        contract['pension']['cola'] = '13.9'
        payload = self.post(
            [
                'pension.strict_multi_selected',
                'pension.strict_multi_failed',
                'pension.strict_multi_suppressed',
                'pension.strict_multi_no_match',
            ],
            contract,
            capabilities=['merge_field_validation_v1'],
        ).json()
        self.assertEqual(payload['capabilities'], ['merge_field_validation_v1'])
        self.assertEqual(
            [decision['status'] for decision in payload['slots']],
            ['selected', 'invalid_published_content', 'suppressed', 'no_match'],
        )
        self.assertIn('html', payload['slots'][0])
        self.assertNotIn('html', payload['slots'][1])
        self.assertNotIn('html', payload['slots'][2])
        self.assertNotIn('html', payload['slots'][3])
