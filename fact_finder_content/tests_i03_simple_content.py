"""Data-driven I-03 plan-year and v1 API contract tests."""

import json

from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from core.models import SystemSettings
from fact_finder_content.models import (
    ContentBlock,
    ContentBlockGroup,
    ContentBlockVersion,
)
from fact_finder_content.tests_api import _valid_data_contract


I03_KEYS_BY_SECTION = {
    'FF-04': (
        'pension.eligibility_to_retire',
        'pension.day_of_month_to_retire',
        'pension.calculating_the_federal_pension',
        'pension.high3_average_salary',
        'pension.applying_unused_sick_leave',
        'pension.selling_back_annual_leave',
        'pension.part_time_service',
        'pension.cost_of_living_adjustments',
    ),
    'FF-05': (
        'sbp.eligibility',
        'sbp.coverage_and_cost',
        'sbp.changes_in_retirement',
        'sbp.connection_to_fehb_current_spouse',
        'sbp.spouse_passes_away_first',
        'sbp.considerations_federal_couples',
        'sbp.retiring_under_deferred_scenario',
    ),
    'FF-07': (
        'fegli.purpose',
        'fegli.extra_benefit_under_45',
        'fegli.adding_coverage',
        'fegli.open_seasons',
        'fegli.postal_workers',
        'fegli.keeping_fegli_in_retirement',
        'fegli.choices_in_retirement',
    ),
    'FF-08': (
        'fehb.purpose',
        'fehb.coverage_available',
        'fehb.taxes_on_premiums',
        'fehb.eligibility_to_keep_in_retirement',
        'fehb.dual_federal_couples',
        'fehb.changes_in_retirement',
        'fehb.current_cost_intro',
    ),
    'FF-09': (
        'fltcip.what_is_ltc',
        'fltcip.purpose',
        'fltcip.cost_of_ltc_services',
        'fltcip.program_structure',
        'fltcip.eligibility',
        'fltcip.proof_of_insurability',
        'fltcip.state_partnership_plans',
        'fltcip.discounts',
        'fltcip.coverage_elected_intro',
    ),
    'FF-10': (
        'tsp.eligibility',
        'tsp.agency_contributions_and_matching',
        'tsp.tax_advantages_traditional',
        'tsp.tax_advantages_roth',
        'tsp.loans',
        'tsp.new_contributions_intro',
        'tsp.current_balance_growth_intro',
    ),
    'FF-12': (
        'checklist.intro',
        'checklist.mark_areas_prompt',
    ),
}


class I03SimpleContentApiTests(TestCase):
    """One test per report section; subtests identify each governed key."""

    def setUp(self):
        settings_obj = SystemSettings.get_settings()
        self.api_key = 'test-shared-secret'
        settings_obj.benefits_software_api_key = self.api_key
        settings_obj.save()
        self.url = reverse('fact_finder_resolve_content')
        self.auth = {'HTTP_AUTHORIZATION': f'Bearer {self.api_key}'}
        self.editor = User.objects.create_user(
            username='i03_content_editor',
            role='administrator',
        )

    def _publish(self, block, plan_year, body_html):
        version = ContentBlockVersion.objects.create(
            block=block,
            plan_year=plan_year,
            body_html=body_html,
        )
        version.submit_for_review()
        version.publish()
        return version

    def _post(self, plan_year):
        return self.client.post(
            self.url,
            data=json.dumps({
                'plan_year': plan_year,
                'data_contract': _valid_data_contract(),
            }),
            content_type='application/json',
            **self.auth,
        )

    def _assert_section_contract(self, section_id, keys):
        group_key = keys[0].split('.', 1)[0]
        group = ContentBlockGroup.objects.create(
            key=group_key,
            label=section_id,
            display_order=1,
        )
        expected_2025 = []
        expected_2026 = []
        versions_by_key = {}

        for key in keys:
            with self.subTest(section=section_id, key=key, stage='fixtures'):
                block = ContentBlock.objects.create(
                    key=key,
                    group=group,
                    label=key,
                )
                body_2025 = f'<p>Published 2025 wording for {key}.</p>'
                body_2026 = f'<p>Published 2026 wording for {key}.</p>'
                version_2025 = self._publish(block, 2025, body_2025)
                version_2026 = self._publish(block, 2026, body_2026)
                draft = ContentBlockVersion.objects.create(
                    block=block,
                    plan_year=2026,
                    body_html=f'<p>Unpublished draft for {key}.</p>',
                )
                in_review = ContentBlockVersion.objects.create(
                    block=block,
                    plan_year=2026,
                    body_html=f'<p>Unpublished review for {key}.</p>',
                )
                in_review.submit_for_review()

                expected_2025.append({
                    'key': key,
                    'html': body_2025,
                    'order': len(expected_2025) + 1,
                })
                expected_2026.append({
                    'key': key,
                    'html': body_2026,
                    'order': len(expected_2026) + 1,
                })
                versions_by_key[key] = (
                    block, version_2026, draft, in_review, body_2026,
                )

        self.assertEqual(self._post(2024).status_code, 200)
        self.assertEqual(self._post(2024).json(), {'blocks': []})
        response_2025 = self._post(2025)
        self.assertEqual(response_2025.status_code, 200)
        self.assertEqual(response_2025.json(), {'blocks': expected_2025})
        response_2026 = self._post(2026)
        self.assertEqual(response_2026.status_code, 200)
        self.assertEqual(response_2026.json(), {'blocks': expected_2026})

        for key, (block, published, draft, in_review, published_body) in versions_by_key.items():
            with self.subTest(section=section_id, key=key):
                published.refresh_from_db()
                draft.refresh_from_db()
                in_review.refresh_from_db()
                self.assertEqual(published.status, ContentBlockVersion.STATUS_PUBLISHED)
                self.assertEqual(draft.status, ContentBlockVersion.STATUS_DRAFT)
                self.assertEqual(in_review.status, ContentBlockVersion.STATUS_IN_REVIEW)
                self.assertEqual(block.published_version_for(2026).pk, published.pk)

                self.client.force_login(self.editor)
                editor_response = self.client.get(
                    reverse(
                        'fact_finder_content:content_block_detail',
                        args=[block.pk],
                    ),
                    {'plan_year': 2026},
                )
                self.assertEqual(editor_response.status_code, 200)
                form = editor_response.context['draft_form']
                self.assertEqual(form['body_html'].value(), published_body)
                self.assertEqual(form['source_version_id'].value(), published.pk)
                self.assertEqual(form['version_id'].value(), '')

    def test_i03_ff04_federal_pension(self):
        self._assert_section_contract('FF-04', I03_KEYS_BY_SECTION['FF-04'])

    def test_i03_ff05_sbp(self):
        self._assert_section_contract('FF-05', I03_KEYS_BY_SECTION['FF-05'])

    def test_i03_ff07_fegli(self):
        self._assert_section_contract('FF-07', I03_KEYS_BY_SECTION['FF-07'])

    def test_i03_ff08_fehb(self):
        self._assert_section_contract('FF-08', I03_KEYS_BY_SECTION['FF-08'])

    def test_i03_ff09_fltcip(self):
        self._assert_section_contract('FF-09', I03_KEYS_BY_SECTION['FF-09'])

    def test_i03_ff10_tsp(self):
        self._assert_section_contract('FF-10', I03_KEYS_BY_SECTION['FF-10'])

    def test_i03_ff12_checklist(self):
        self._assert_section_contract('FF-12', I03_KEYS_BY_SECTION['FF-12'])
