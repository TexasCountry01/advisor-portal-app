"""
Tests for the resolve-content API (Option A "Integration contract").
See fact_finder_content/views_api.py.
"""
import json

from django.test import TestCase
from django.urls import reverse

from core.models import SystemSettings
from fact_finder_content.models import ContentBlockGroup, ContentBlock, ContentBlockVersion


def _valid_data_contract(**overrides):
    """A minimal-but-schema-valid Fact Finder Data Contract, matching the shape
    validated in cases/tests_fact_finder_contract.py."""
    contract = {
        "schema_version": "2026.1",
        "employee_id": 12345,
        "generated_at": "2026-09-12T00:00:00Z",
        "system": {"system_type": "FERS", "retirement_type": "Deferred", "birth_year": 1968},
        "pension": {
            "scenarios": [{
                "scenario_number": 1, "gross_annual_pension": "48210.00",
            }],
        },
        "fegli": {
            "current_fegli": {"basic": True, "optionA": True, "optionB": 3, "optionC": 2},
            "is_married": True, "has_dependents": False,
            "fegli_arr": [{
                "age": 58, "years_in_retirement": 0, "annual_sal": "95000.00",
                "basic_coverage": "95000.00", "optionA_coverage": "10000.00",
                "optionB_coverage": "285000.00", "optionC_coverage": "10000.00",
                "total_coverage": "400000.00", "totalBiWeekly": "42.10",
                "totalMonthly": "91.22", "totalYearly": "1094.60", "runningTotalCost": "1094.60",
            }],
        },
        "social_security": {
            "ss_cola": "2.500", "ss_earned_income_limit": "23400.00",
            "ss_details": [{
                "years_in_ret": 1, "age": 63, "monthly_pension": "4020.00",
                "fers_srs": "900.00", "ss_benefits": "0.00", "total": "4920.00",
            }],
        },
        "tsp": {
            "funds": [{"fund_code": "GFund", "balance": "102000.00"}],
            "sal_percentage_in_contri": "5.000",
        },
        "computed_flags": {
            "is_fers_or_transfers": True, "is_csrs_or_csrs_offset": False,
            "is_deferred_retirement": True, "is_wep_applicable": False,
            "is_gpo_applicable": False, "hit_full_tsp_match": True,
        },
    }
    contract.update(overrides)
    return contract


class ResolveContentAuthTests(TestCase):
    def setUp(self):
        self.settings_obj = SystemSettings.get_settings()
        self.settings_obj.benefits_software_api_key = 'test-shared-secret'
        self.settings_obj.save()
        self.url = reverse('fact_finder_resolve_content')

    def _post(self, body, auth_header=None):
        extra = {}
        if auth_header is not None:
            extra['HTTP_AUTHORIZATION'] = auth_header
        return self.client.post(self.url, data=json.dumps(body), content_type='application/json', **extra)

    def test_missing_auth_header_rejected(self):
        response = self._post({'plan_year': 2026, 'data_contract': _valid_data_contract()})
        self.assertEqual(response.status_code, 403)

    def test_wrong_api_key_rejected(self):
        response = self._post(
            {'plan_year': 2026, 'data_contract': _valid_data_contract()},
            auth_header='Bearer wrong-key',
        )
        self.assertEqual(response.status_code, 403)

    def test_placeholder_key_never_authenticates(self):
        self.settings_obj.benefits_software_api_key = 'placeholder-api-key-change-in-production'
        self.settings_obj.save()
        response = self._post(
            {'plan_year': 2026, 'data_contract': _valid_data_contract()},
            auth_header='Bearer placeholder-api-key-change-in-production',
        )
        self.assertEqual(response.status_code, 403)

    def test_valid_key_is_accepted(self):
        response = self._post(
            {'plan_year': 2026, 'data_contract': _valid_data_contract()},
            auth_header='Bearer test-shared-secret',
        )
        self.assertEqual(response.status_code, 200)

    def test_get_method_not_allowed(self):
        response = self.client.get(self.url, HTTP_AUTHORIZATION='Bearer test-shared-secret')
        self.assertEqual(response.status_code, 405)


class ResolveContentBehaviorTests(TestCase):
    def setUp(self):
        settings_obj = SystemSettings.get_settings()
        settings_obj.benefits_software_api_key = 'test-shared-secret'
        settings_obj.save()
        self.url = reverse('fact_finder_resolve_content')
        self.auth = {'HTTP_AUTHORIZATION': 'Bearer test-shared-secret'}

        self.group = ContentBlockGroup.objects.create(key='tsp', label='TSP', display_order=1)

    def _post(self, body):
        return self.client.post(self.url, data=json.dumps(body), content_type='application/json', **self.auth)

    def test_malformed_json_returns_400(self):
        response = self.client.post(self.url, data='not json', content_type='application/json', **self.auth)
        self.assertEqual(response.status_code, 400)

    def test_missing_fields_returns_400(self):
        response = self._post({'plan_year': 2026})
        self.assertEqual(response.status_code, 400)

    def test_invalid_data_contract_returns_400_with_details(self):
        bad_contract = _valid_data_contract()
        bad_contract['system']['system_type'] = 'NotARealSystem'
        response = self._post({'plan_year': 2026, 'data_contract': bad_contract})
        self.assertEqual(response.status_code, 400)
        self.assertIn('details', response.json())

    def test_no_published_version_returns_empty_blocks(self):
        ContentBlock.objects.create(key='tsp.no_version', group=self.group, label='No Version')
        response = self._post({'plan_year': 2026, 'data_contract': _valid_data_contract()})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['blocks'], [])

    def test_published_block_with_no_condition_is_included(self):
        block = ContentBlock.objects.create(key='tsp.always_shown', group=self.group, label='Always Shown')
        version = ContentBlockVersion.objects.create(block=block, plan_year=2026, body_html='<p>Always visible.</p>')
        version.submit_for_review()
        version.publish()

        response = self._post({'plan_year': 2026, 'data_contract': _valid_data_contract()})
        data = response.json()
        self.assertEqual(len(data['blocks']), 1)
        self.assertEqual(data['blocks'][0]['key'], 'tsp.always_shown')
        self.assertEqual(data['blocks'][0]['html'], '<p>Always visible.</p>')
        self.assertEqual(data['blocks'][0]['order'], 1)

    def test_block_excluded_when_display_condition_fails(self):
        block = ContentBlock.objects.create(
            key='tsp.csrs_only', group=self.group, label='CSRS Only',
            display_condition={'rules': [{'field': 'system.system_type', 'operator': 'equals', 'value': 'CSRS'}]},
        )
        version = ContentBlockVersion.objects.create(block=block, plan_year=2026, body_html='<p>CSRS text.</p>')
        version.submit_for_review()
        version.publish()

        # data_contract has system_type=FERS, so this CSRS-only block must be excluded.
        response = self._post({'plan_year': 2026, 'data_contract': _valid_data_contract()})
        self.assertEqual(response.json()['blocks'], [])

    def test_block_included_when_display_condition_matches(self):
        block = ContentBlock.objects.create(
            key='tsp.fers_only', group=self.group, label='FERS Only',
            display_condition={'rules': [{'field': 'system.system_type', 'operator': 'equals', 'value': 'FERS'}]},
        )
        version = ContentBlockVersion.objects.create(block=block, plan_year=2026, body_html='<p>FERS text.</p>')
        version.submit_for_review()
        version.publish()

        response = self._post({'plan_year': 2026, 'data_contract': _valid_data_contract()})
        data = response.json()
        self.assertEqual(len(data['blocks']), 1)
        self.assertEqual(data['blocks'][0]['key'], 'tsp.fers_only')

    def test_wrong_plan_year_excludes_block(self):
        block = ContentBlock.objects.create(key='tsp.year_2025_only', group=self.group, label='2025 Only')
        version = ContentBlockVersion.objects.create(block=block, plan_year=2025, body_html='<p>2025 text.</p>')
        version.submit_for_review()
        version.publish()

        response = self._post({'plan_year': 2026, 'data_contract': _valid_data_contract()})
        self.assertEqual(response.json()['blocks'], [])

    def test_inactive_block_is_excluded(self):
        block = ContentBlock.objects.create(
            key='tsp.inactive', group=self.group, label='Inactive Block', is_active=False,
        )
        version = ContentBlockVersion.objects.create(block=block, plan_year=2026, body_html='<p>Hidden.</p>')
        version.submit_for_review()
        version.publish()

        response = self._post({'plan_year': 2026, 'data_contract': _valid_data_contract()})
        self.assertEqual(response.json()['blocks'], [])

    def test_multiple_included_blocks_are_ordered(self):
        block_a = ContentBlock.objects.create(key='tsp.a', group=self.group, label='A')
        block_b = ContentBlock.objects.create(key='tsp.b', group=self.group, label='B')
        for block, text in [(block_a, 'A text'), (block_b, 'B text')]:
            v = ContentBlockVersion.objects.create(block=block, plan_year=2026, body_html=f'<p>{text}</p>')
            v.submit_for_review()
            v.publish()

        response = self._post({'plan_year': 2026, 'data_contract': _valid_data_contract()})
        data = response.json()
        self.assertEqual(len(data['blocks']), 2)
        self.assertEqual([b['order'] for b in data['blocks']], [1, 2])
