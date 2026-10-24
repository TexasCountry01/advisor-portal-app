"""I-04 condition ownership, plan-year selection, and API inclusion tests."""

import json

from django.test import TestCase
from django.urls import reverse

from core.models import SystemSettings
from fact_finder_content.models import (
    ContentBlock,
    ContentBlockGroup,
    ContentBlockVersion,
)
from fact_finder_content.tests_api import _valid_data_contract


I04_RULES_BY_KEY = {
    'pension.system_type_heading_non_fers': [
        ('system.system_type', 'not_equals', 'FERS'),
    ],
    'sbp.deferred_intro': [
        ('computed_flags.is_fers_or_transfers', 'equals', True),
        ('system.retirement_type', 'equals', 'Deferred'),
    ],
    'sbp.fers_transfers_intro_not_deferred': [
        ('computed_flags.is_fers_or_transfers', 'equals', True),
        ('system.retirement_type', 'not_equals', 'Deferred'),
    ],
    'sbp.csrs_intro': [
        ('computed_flags.is_csrs_or_csrs_offset', 'equals', True),
    ],
    'srs_ss.fers_purpose': [
        ('computed_flags.is_fers_or_transfers', 'equals', True),
    ],
    'srs_ss.fers_eligibility': [
        ('computed_flags.is_fers_or_transfers', 'equals', True),
    ],
    'srs_ss.fers_eligibility_exceptions': [
        ('computed_flags.is_fers_or_transfers', 'equals', True),
    ],
    'srs_ss.fers_coverage_and_cost': [
        ('computed_flags.is_fers_or_transfers', 'equals', True),
    ],
    'srs_ss.fers_receipt_of_payment': [
        ('computed_flags.is_fers_or_transfers', 'equals', True),
    ],
    'srs_ss.fers_cola': [
        ('computed_flags.is_fers_or_transfers', 'equals', True),
    ],
    'srs_ss.ss_eligibility': [],
    'srs_ss.wep_paragraph': [
        ('system.system_type', 'not_equals', 'FERS'),
    ],
    'srs_ss.gpo_paragraph': [
        ('computed_flags.is_gpo_applicable', 'equals', True),
    ],
    'srs_ss.summary_deferred_note': [
        ('computed_flags.is_fers_or_transfers', 'equals', True),
        ('system.retirement_type', 'equals', 'Deferred'),
    ],
    'srs_ss.summary_earnings_test_note': [
        ('computed_flags.is_fers_or_transfers', 'equals', True),
        ('system.retirement_type', 'not_equals', 'Deferred'),
    ],
    'fegli.coverage_elected_intro_deferred': [
        ('system.retirement_type', 'equals', 'Deferred'),
    ],
    'fegli.coverage_elected_intro_not_deferred': [
        ('system.retirement_type', 'not_equals', 'Deferred'),
    ],
    'fegli.in_retirement_intro': [
        ('system.retirement_type', 'not_equals', 'Deferred'),
    ],
    'fehb.deferred_sentence': [
        ('computed_flags.is_deferred_retirement', 'equals', True),
    ],
    'tsp.no_agency_match_csrs': [
        ('computed_flags.is_csrs_or_csrs_offset', 'equals', True),
    ],
}


SCENARIOS = (
    ('FERS_DEFERRED', 'FERS', 'Deferred'),
    ('FERS_REGULAR', 'FERS', 'Regular'),
    ('FERS_VERA', 'FERS', 'VERA / DSR'),
    ('CSRS_DEFERRED', 'CSRS', 'Deferred'),
    ('CSRS_REGULAR', 'CSRS', 'Regular'),
    ('CSRS_OFFSET_REGULAR', 'CSRS Offset', 'Regular'),
    ('TRANSFERS_DEFERRED', 'Transfers', 'Deferred'),
    ('TRANSFERS_REGULAR', 'Transfers', 'Regular'),
)


EXPECTED_INCLUSION = {
    'pension.system_type_heading_non_fers': {
        'FERS_DEFERRED': False, 'FERS_REGULAR': False, 'FERS_VERA': False,
        'CSRS_DEFERRED': True, 'CSRS_REGULAR': True, 'CSRS_OFFSET_REGULAR': True,
        'TRANSFERS_DEFERRED': True, 'TRANSFERS_REGULAR': True,
    },
    'sbp.deferred_intro': {
        'FERS_DEFERRED': True, 'FERS_REGULAR': False, 'FERS_VERA': False,
        'CSRS_DEFERRED': False, 'CSRS_REGULAR': False, 'CSRS_OFFSET_REGULAR': False,
        'TRANSFERS_DEFERRED': True, 'TRANSFERS_REGULAR': False,
    },
    'sbp.fers_transfers_intro_not_deferred': {
        'FERS_DEFERRED': False, 'FERS_REGULAR': True, 'FERS_VERA': True,
        'CSRS_DEFERRED': False, 'CSRS_REGULAR': False, 'CSRS_OFFSET_REGULAR': False,
        'TRANSFERS_DEFERRED': False, 'TRANSFERS_REGULAR': True,
    },
    'sbp.csrs_intro': {
        'FERS_DEFERRED': False, 'FERS_REGULAR': False, 'FERS_VERA': False,
        'CSRS_DEFERRED': True, 'CSRS_REGULAR': True, 'CSRS_OFFSET_REGULAR': True,
        'TRANSFERS_DEFERRED': False, 'TRANSFERS_REGULAR': False,
    },
    'srs_ss.fers_purpose': {
        'FERS_DEFERRED': True, 'FERS_REGULAR': True, 'FERS_VERA': True,
        'CSRS_DEFERRED': False, 'CSRS_REGULAR': False, 'CSRS_OFFSET_REGULAR': False,
        'TRANSFERS_DEFERRED': True, 'TRANSFERS_REGULAR': True,
    },
    'srs_ss.fers_eligibility': {
        'FERS_DEFERRED': True, 'FERS_REGULAR': True, 'FERS_VERA': True,
        'CSRS_DEFERRED': False, 'CSRS_REGULAR': False, 'CSRS_OFFSET_REGULAR': False,
        'TRANSFERS_DEFERRED': True, 'TRANSFERS_REGULAR': True,
    },
    'srs_ss.fers_eligibility_exceptions': {
        'FERS_DEFERRED': True, 'FERS_REGULAR': True, 'FERS_VERA': True,
        'CSRS_DEFERRED': False, 'CSRS_REGULAR': False, 'CSRS_OFFSET_REGULAR': False,
        'TRANSFERS_DEFERRED': True, 'TRANSFERS_REGULAR': True,
    },
    'srs_ss.fers_coverage_and_cost': {
        'FERS_DEFERRED': True, 'FERS_REGULAR': True, 'FERS_VERA': True,
        'CSRS_DEFERRED': False, 'CSRS_REGULAR': False, 'CSRS_OFFSET_REGULAR': False,
        'TRANSFERS_DEFERRED': True, 'TRANSFERS_REGULAR': True,
    },
    'srs_ss.fers_receipt_of_payment': {
        'FERS_DEFERRED': True, 'FERS_REGULAR': True, 'FERS_VERA': True,
        'CSRS_DEFERRED': False, 'CSRS_REGULAR': False, 'CSRS_OFFSET_REGULAR': False,
        'TRANSFERS_DEFERRED': True, 'TRANSFERS_REGULAR': True,
    },
    'srs_ss.fers_cola': {
        'FERS_DEFERRED': True, 'FERS_REGULAR': True, 'FERS_VERA': True,
        'CSRS_DEFERRED': False, 'CSRS_REGULAR': False, 'CSRS_OFFSET_REGULAR': False,
        'TRANSFERS_DEFERRED': True, 'TRANSFERS_REGULAR': True,
    },
    'srs_ss.ss_eligibility': {
        'FERS_DEFERRED': True, 'FERS_REGULAR': True, 'FERS_VERA': True,
        'CSRS_DEFERRED': True, 'CSRS_REGULAR': True, 'CSRS_OFFSET_REGULAR': True,
        'TRANSFERS_DEFERRED': True, 'TRANSFERS_REGULAR': True,
    },
    'srs_ss.wep_paragraph': {
        'FERS_DEFERRED': False, 'FERS_REGULAR': False, 'FERS_VERA': False,
        'CSRS_DEFERRED': True, 'CSRS_REGULAR': True, 'CSRS_OFFSET_REGULAR': True,
        'TRANSFERS_DEFERRED': True, 'TRANSFERS_REGULAR': True,
    },
    'srs_ss.gpo_paragraph': {
        'FERS_DEFERRED': False, 'FERS_REGULAR': False, 'FERS_VERA': False,
        'CSRS_DEFERRED': True, 'CSRS_REGULAR': True, 'CSRS_OFFSET_REGULAR': False,
        'TRANSFERS_DEFERRED': False, 'TRANSFERS_REGULAR': False,
    },
    'srs_ss.summary_deferred_note': {
        'FERS_DEFERRED': True, 'FERS_REGULAR': False, 'FERS_VERA': False,
        'CSRS_DEFERRED': False, 'CSRS_REGULAR': False, 'CSRS_OFFSET_REGULAR': False,
        'TRANSFERS_DEFERRED': True, 'TRANSFERS_REGULAR': False,
    },
    'srs_ss.summary_earnings_test_note': {
        'FERS_DEFERRED': False, 'FERS_REGULAR': True, 'FERS_VERA': True,
        'CSRS_DEFERRED': False, 'CSRS_REGULAR': False, 'CSRS_OFFSET_REGULAR': False,
        'TRANSFERS_DEFERRED': False, 'TRANSFERS_REGULAR': True,
    },
    'fegli.coverage_elected_intro_deferred': {
        'FERS_DEFERRED': True, 'FERS_REGULAR': False, 'FERS_VERA': False,
        'CSRS_DEFERRED': True, 'CSRS_REGULAR': False, 'CSRS_OFFSET_REGULAR': False,
        'TRANSFERS_DEFERRED': True, 'TRANSFERS_REGULAR': False,
    },
    'fegli.coverage_elected_intro_not_deferred': {
        'FERS_DEFERRED': False, 'FERS_REGULAR': True, 'FERS_VERA': True,
        'CSRS_DEFERRED': False, 'CSRS_REGULAR': True, 'CSRS_OFFSET_REGULAR': True,
        'TRANSFERS_DEFERRED': False, 'TRANSFERS_REGULAR': True,
    },
    'fegli.in_retirement_intro': {
        'FERS_DEFERRED': False, 'FERS_REGULAR': True, 'FERS_VERA': True,
        'CSRS_DEFERRED': False, 'CSRS_REGULAR': True, 'CSRS_OFFSET_REGULAR': True,
        'TRANSFERS_DEFERRED': False, 'TRANSFERS_REGULAR': True,
    },
    'fehb.deferred_sentence': {
        'FERS_DEFERRED': True, 'FERS_REGULAR': False, 'FERS_VERA': False,
        'CSRS_DEFERRED': True, 'CSRS_REGULAR': False, 'CSRS_OFFSET_REGULAR': False,
        'TRANSFERS_DEFERRED': True, 'TRANSFERS_REGULAR': False,
    },
    'tsp.no_agency_match_csrs': {
        'FERS_DEFERRED': False, 'FERS_REGULAR': False, 'FERS_VERA': False,
        'CSRS_DEFERRED': True, 'CSRS_REGULAR': True, 'CSRS_OFFSET_REGULAR': True,
        'TRANSFERS_DEFERRED': False, 'TRANSFERS_REGULAR': False,
    },
}


class I04ConditionalContentApiTests(TestCase):
    """Verify Portal rule evaluation separately from Benefits Blade branches."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.keys = tuple(I04_RULES_BY_KEY)

    def setUp(self):
        settings_obj = SystemSettings.get_settings()
        settings_obj.benefits_software_api_key = 'test-shared-secret'
        settings_obj.save()
        self.url = reverse('fact_finder_resolve_content')
        self.auth = {'HTTP_AUTHORIZATION': 'Bearer test-shared-secret'}
        self.blocks = {}
        for index, key in enumerate(self.keys, start=1):
            group_key = key.split('.', 1)[0]
            group, _ = ContentBlockGroup.objects.get_or_create(
                key=group_key,
                defaults={'label': group_key, 'display_order': index},
            )
            group.display_order = index
            group.save(update_fields=['display_order'])
            condition = {
                'rules': [
                    {'field': field, 'operator': operator, 'value': value}
                    for field, operator, value in I04_RULES_BY_KEY[key]
                ],
            }
            block = ContentBlock.objects.create(
                key=key,
                group=group,
                label=key,
                display_condition=condition,
            )
            self._publish(block, 2025, f'<p>Published 2025 wording for {key}.</p>')
            active_2026 = self._publish(
                block, 2026, f'<p>Published 2026 wording for {key}.</p>',
            )
            draft = ContentBlockVersion.objects.create(
                block=block,
                plan_year=2026,
                body_html=f'<p>Draft must not appear for {key}.</p>',
            )
            in_review = ContentBlockVersion.objects.create(
                block=block,
                plan_year=2026,
                body_html=f'<p>Review must not appear for {key}.</p>',
            )
            in_review.submit_for_review()
            self.blocks[key] = (block, active_2026, draft, in_review)

    def _publish(self, block, plan_year, body_html):
        version = ContentBlockVersion.objects.create(
            block=block,
            plan_year=plan_year,
            body_html=body_html,
        )
        version.submit_for_review()
        version.publish()
        return version

    def _contract(self, system_type, retirement_type):
        contract = _valid_data_contract()
        contract['system']['system_type'] = system_type
        contract['system']['retirement_type'] = retirement_type
        flags = contract['computed_flags']
        flags['is_fers_or_transfers'] = system_type in ('FERS', 'Transfers')
        flags['is_csrs_or_csrs_offset'] = system_type in ('CSRS', 'CSRS Offset')
        flags['is_deferred_retirement'] = retirement_type == 'Deferred'
        flags['is_gpo_applicable'] = system_type == 'CSRS'
        return contract

    def _post(self, plan_year, contract):
        return self.client.post(
            self.url,
            data=json.dumps({'plan_year': plan_year, 'data_contract': contract}),
            content_type='application/json',
            **self.auth,
        )

    def test_i04_scope_rules_plan_years_and_draft_exclusion(self):
        self.assertEqual(len(I04_RULES_BY_KEY), 20)
        self.assertEqual(set(I04_RULES_BY_KEY), set(EXPECTED_INCLUSION))

        for scenario_name, system_type, retirement_type in SCENARIOS:
            with self.subTest(scenario=scenario_name):
                expected = []
                for key in self.keys:
                    if EXPECTED_INCLUSION[key][scenario_name]:
                        expected.append({
                            'key': key,
                            'html': f'<p>Published 2026 wording for {key}.</p>',
                            'order': len(expected) + 1,
                        })

                response = self._post(
                    2026, self._contract(system_type, retirement_type),
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json(), {'blocks': expected})

        year_2025 = self._post(2025, self._contract('FERS', 'Regular'))
        self.assertEqual(year_2025.status_code, 200)
        self.assertEqual(
            [item['key'] for item in year_2025.json()['blocks']],
            [
                key for key in self.keys
                if EXPECTED_INCLUSION[key]['FERS_REGULAR']
            ],
        )
        self.assertTrue(all(
            'Published 2025 wording' in item['html']
            for item in year_2025.json()['blocks']
        ))

        no_year = self._post(2024, self._contract('FERS', 'Regular'))
        self.assertEqual(no_year.status_code, 200)
        self.assertEqual(no_year.json(), {'blocks': []})

        for key, (block, published, draft, in_review) in self.blocks.items():
            with self.subTest(key=key, publication_state='versions'):
                published.refresh_from_db()
                draft.refresh_from_db()
                in_review.refresh_from_db()
                self.assertEqual(published.status, ContentBlockVersion.STATUS_PUBLISHED)
                self.assertEqual(draft.status, ContentBlockVersion.STATUS_DRAFT)
                self.assertEqual(in_review.status, ContentBlockVersion.STATUS_IN_REVIEW)
                self.assertEqual(block.published_version_for(2026).pk, published.pk)
