"""I-06 dynamic merge-field publication and Data Contract tests."""

import json

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from cases.fact_finder_data_contract import FactFinderDataContractSerializer
from core.models import SystemSettings
from fact_finder_content.merge_field_policy import (
    validate_merge_field_policy,
    validate_merge_field_template,
)
from fact_finder_content.models import (
    ContentBlock,
    ContentBlockGroup,
    ContentBlockVersion,
)
from fact_finder_content.sanitize import sanitize_body_html
from fact_finder_content.tests_api import _valid_data_contract


I06_TOKENS_BY_KEY = {
    'pension.mra_explanation': (
        'system.birth_year', 'pension.mra_year', 'pension.mra_month',
    ),
    'pension.your_federal_pension_deferred': ('pension.cola',),
    'pension.your_federal_pension_not_deferred': (
        'pension.retirement_date', 'pension.cola',
    ),
    'pension.planned_delayed_retirement_intro': (
        'pension.retirement_month_year',
        'pension.retirement_age_years',
        'pension.retirement_age_months',
        'pension.unused_sick_leave_hours',
        'pension.unused_sick_leave_months',
    ),
    'srs_ss.fers_earnings_test': (
        'system.current_year', 'social_security.ss_earned_income_limit',
    ),
    'srs_ss.ss_earnings_test': (
        'system.current_year', 'social_security.ss_earned_income_limit',
    ),
    'srs_ss.ss_cola': ('social_security.ss_cola',),
    'srs_ss.summary_ss_note': ('social_security.ss_cola',),
    'srs_ss.wep_sentence': ('pension.wep_penalty',),
    'fehb.projection_intro_not_deferred': ('fehb.average_premium_increase',),
    'tsp.regular_contribution_limits': (
        'tsp.year_of_contribution', 'tsp.deff_limit',
    ),
    'tsp.catchup_contribution_limits': ('tsp.catchup_limit', 'tsp.deff_limit'),
    'tsp.match_threshold_sentence': ('tsp.sal_percentage_in_contri_rounded',),
    'tsp.agency_match_explanation': (
        'tsp.sal_percentage_in_contri_rounded',
        'tsp.missing_out_amount',
        'tsp.emp_min_contri_for_full_agency_contri',
    ),
    'irs_penalty.eligible_at_59_5': (),
    'irs_penalty.special_provision_meets_rules': (),
    'irs_penalty.special_provision_not_meets_rules': (),
    'irs_penalty.regular_not_meets_age55': (),
    'irs_penalty.regular_meets_age55': (),
}
I06_KEYS = tuple(I06_TOKENS_BY_KEY)

TOKEN_SPECS = {
    'system.birth_year': ('integer', 'plain'),
    'system.current_year': ('integer', 'plain'),
    'pension.mra_year': ('integer', 'plain'),
    'pension.mra_month': ('integer', 'plain'),
    'pension.cola': ('string', 'plain'),
    'pension.retirement_date': ('string', 'display_mdy'),
    'pension.retirement_month_year': ('string', 'display_month_year'),
    'pension.retirement_age_years': ('integer', 'plain'),
    'pension.retirement_age_months': ('integer', 'plain'),
    'pension.unused_sick_leave_hours': ('integer', 'plain'),
    'pension.unused_sick_leave_months': ('decimal', 'plain'),
    'pension.wep_penalty': ('decimal', 'plain'),
    'social_security.ss_earned_income_limit': ('decimal', 'plain'),
    'social_security.ss_cola': ('string', 'plain'),
    'fehb.average_premium_increase': ('string', 'plain'),
    'tsp.year_of_contribution': ('integer', 'plain'),
    'tsp.deff_limit': ('decimal', 'plain'),
    'tsp.catchup_limit': ('decimal', 'plain'),
    'tsp.sal_percentage_in_contri_rounded': ('integer', 'plain'),
    'tsp.missing_out_amount': ('string', 'plain'),
    'tsp.emp_min_contri_for_full_agency_contri': ('string', 'plain'),
}


def _policy(tokens):
    return {
        'schema_version': 1,
        'tokens': [
            {
                'token': token,
                'value_type': TOKEN_SPECS[token][0],
                'format': TOKEN_SPECS[token][1],
                'presence': 'required',
                'null': 'error',
                'blank': 'error',
                'omission': None,
            }
            for token in tokens
        ],
    }


def _body(key, year):
    tokens = I06_TOKENS_BY_KEY[key]
    token_text = ' | '.join(f'[[{token}]]' for token in tokens)
    return f'<p>{year} {key}: {token_text}</p>'


def _data_contract():
    contract = _valid_data_contract()
    contract['system']['current_year'] = 2026
    contract['pension'].update({
        'mra_year': 56,
        'mra_month': 4,
        'cola': '2.50',
        'retirement_date': '12/31/2026',
        'retirement_month_year': 'December 2026',
        'retirement_age_years': 56,
        'retirement_age_months': 4,
        'unused_sick_leave_hours': 100,
        'unused_sick_leave_months': '0.57',
        'wep_penalty': '123.45',
    })
    contract['social_security'].update({
        'ss_earned_income_limit': '24480.00',
        'ss_cola': '2.50',
    })
    contract['fehb'] = {'average_premium_increase': '4.83'}
    contract['tsp'].update({
        'year_of_contribution': 2026,
        'deff_limit': '24500.00',
        'catchup_limit': '8000.00',
        'sal_percentage_in_contri_rounded': 5,
        'missing_out_amount': '1,234',
        'emp_min_contri_for_full_agency_contri': '96',
    })
    return contract


class I06DynamicMergeFieldPublicationTests(TestCase):
    """Pin key-level token policy, plan-year selection, and published API bodies."""

    def setUp(self):
        settings_obj = SystemSettings.get_settings()
        settings_obj.benefits_software_api_key = 'test-shared-secret'
        settings_obj.save()
        self.url = reverse('fact_finder_resolve_content')
        self.auth = {'HTTP_AUTHORIZATION': 'Bearer test-shared-secret'}
        self.versions = {}

        for index, key in enumerate(I06_KEYS, start=1):
            group_key = key.split('.', 1)[0]
            group, _ = ContentBlockGroup.objects.get_or_create(
                key=group_key,
                defaults={'label': group_key, 'display_order': index},
            )
            block = ContentBlock.objects.create(
                key=key,
                group=group,
                label=key,
                required_placeholders=list(I06_TOKENS_BY_KEY[key]),
            )
            policy = _policy(I06_TOKENS_BY_KEY[key])
            v2025 = self._publish(block, 2025, _body(key, 2025), policy)
            v2026 = self._publish(block, 2026, _body(key, 2026), policy)
            draft = ContentBlockVersion.objects.create(
                block=block,
                plan_year=2026,
                body_html=_body(key, 2026).replace('2026', 'DRAFT ONLY'),
                merge_field_policy=policy,
            )
            review = ContentBlockVersion.objects.create(
                block=block,
                plan_year=2026,
                body_html=_body(key, 2026).replace('2026', 'REVIEW ONLY'),
                merge_field_policy=policy,
            )
            review.submit_for_review()
            self.versions[key] = (block, v2025, v2026, draft, review)

    def _publish(self, block, year, body_html, merge_field_policy):
        version = ContentBlockVersion.objects.create(
            block=block,
            plan_year=year,
            body_html=body_html,
            merge_field_policy=merge_field_policy,
        )
        version.validate_publishable()
        version.submit_for_review()
        version.publish()
        return version

    def _post(self, year, contract=None):
        response = self.client.post(
            self.url,
            data=json.dumps({
                'plan_year': year,
                'data_contract': contract if contract is not None else _data_contract(),
            }),
            content_type='application/json',
            **self.auth,
        )
        if response.status_code == 200:
            return response.json()['blocks']
        return response

    def test_exact_nineteen_key_scope_and_plan_year_state_selection(self):
        self.assertEqual(len(I06_KEYS), 19)
        self.assertEqual(len(set(I06_KEYS)), 19)

        for year in (2025, 2026):
            with self.subTest(plan_year=year):
                blocks = self._post(year)
                actual = {item['key']: item['html'] for item in blocks}
                self.assertEqual(set(actual), set(I06_KEYS))
                for key in I06_KEYS:
                    self.assertEqual(actual[key], _body(key, year))
                    self.assertNotIn('DRAFT ONLY', actual[key])
                    self.assertNotIn('REVIEW ONLY', actual[key])

        self.assertEqual(self._post(2024), [])
        for key, (_block, v2025, v2026, draft, review) in self.versions.items():
            with self.subTest(key=key, stored_states=True):
                self.assertEqual(v2025.status, ContentBlockVersion.STATUS_PUBLISHED)
                self.assertEqual(v2026.status, ContentBlockVersion.STATUS_PUBLISHED)
                self.assertEqual(draft.status, ContentBlockVersion.STATUS_DRAFT)
                self.assertEqual(review.status, ContentBlockVersion.STATUS_IN_REVIEW)

    def test_v1_rejects_malformed_decimal_data_before_content_resolution(self):
        contract = _data_contract()
        contract['tsp']['deff_limit'] = 'not-a-number'
        response = self._post(2026, contract)
        self.assertEqual(response.status_code, 400, response.content)

    def test_every_key_token_set_has_a_valid_required_policy(self):
        seen = set()
        for key, tokens in I06_TOKENS_BY_KEY.items():
            with self.subTest(key=key):
                self.assertEqual(len(tokens), len(set(tokens)))
                seen.update(tokens)
                policy = _policy(tokens)
                definitions = validate_merge_field_policy(policy)
                self.assertEqual(set(definitions), set(tokens))
                self.assertEqual(
                    validate_merge_field_template(
                        _body(key, 2026),
                        policy,
                        list(tokens),
                    ),
                    definitions,
                )

        self.assertEqual(seen, set(TOKEN_SPECS))

    def test_each_declared_token_is_required_and_cannot_be_silently_removed(self):
        for key, tokens in I06_TOKENS_BY_KEY.items():
            for missing in tokens:
                with self.subTest(key=key, missing=missing):
                    invalid_body = _body(key, 2026).replace(f'[[{missing}]]', 'static')
                    version = ContentBlockVersion(
                        block=self.versions[key][0],
                        plan_year=2027,
                        body_html=invalid_body,
                        merge_field_policy=_policy(tokens),
                    )
                    with self.assertRaises(ValidationError):
                        version.validate_publishable()

    def test_optional_tokens_are_rejected_by_current_policy_model(self):
        definition = _policy(('pension.cola',))
        definition['tokens'][0]['presence'] = 'optional'
        with self.assertRaisesMessage(ValidationError, 'Only required-value'):
            validate_merge_field_policy(definition)

    def test_sanitizer_preserves_tokens_and_neutralizes_markup_in_templates(self):
        sanitized = sanitize_body_html(
            '<p>[[pension.retirement_date]]</p><script>run()</script>'
            '<img src="x" onerror="run()">'
        )
        self.assertIn('[[pension.retirement_date]]', sanitized)
        self.assertNotIn('<script', sanitized)
        self.assertNotIn('<img', sanitized)
        self.assertNotIn('onerror', sanitized)


class I06DataContractValueTests(SimpleTestCase):
    """Verify selected source-field types and validation boundaries."""

    def test_malformed_decimal_values_are_rejected_by_data_contract(self):
        for section, field in (
            ('pension', 'wep_penalty'),
            ('social_security', 'ss_earned_income_limit'),
            ('tsp', 'deff_limit'),
            ('tsp', 'catchup_limit'),
        ):
            contract = _data_contract()
            contract[section][field] = 'not-a-number'
            serializer = FactFinderDataContractSerializer(data=contract)
            with self.subTest(field=f'{section}.{field}'):
                self.assertFalse(serializer.is_valid())

    def test_source_nullable_merge_fields_remain_optional_in_contract(self):
        contract = _data_contract()
        contract['pension']['mra_year'] = None
        contract['pension']['mra_month'] = None
        contract['pension']['retirement_date'] = None
        contract['pension']['retirement_month_year'] = None
        serializer = FactFinderDataContractSerializer(data=contract)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_current_string_fields_accept_markup_and_unvalidated_display_dates(self):
        contract = _data_contract()
        contract['pension']['retirement_date'] = '<script>marker()</script>'
        contract['pension']['retirement_month_year'] = 'not a month/year'
        serializer = FactFinderDataContractSerializer(data=contract)
        self.assertTrue(serializer.is_valid(), serializer.errors)
