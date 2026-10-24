"""I-02 tests for the Portal publication-to-v1-API contract."""

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


class PublishedContentApiContractTests(TestCase):
    """Reusable assertions for published wording as consumed by Benefits."""

    def setUp(self):
        settings_obj = SystemSettings.get_settings()
        self.api_key = 'test-shared-secret'
        settings_obj.benefits_software_api_key = self.api_key
        settings_obj.save()
        self.url = reverse('fact_finder_resolve_content')
        self.auth = {'HTTP_AUTHORIZATION': f'Bearer {self.api_key}'}

    def _published_version(self, block, plan_year, body_html):
        version = ContentBlockVersion.objects.create(
            block=block,
            plan_year=plan_year,
            body_html=body_html,
        )
        version.submit_for_review()
        version.publish()
        return version

    def _post_for_year(self, plan_year):
        contract = _valid_data_contract()
        return self.client.post(
            self.url,
            data=json.dumps({
                'plan_year': plan_year,
                'data_contract': contract,
            }),
            content_type='application/json',
            **self.auth,
        )

    def _assert_key_contract(
        self,
        *,
        key,
        group_key,
        label,
        published_2025,
        published_2026,
    ):
        group = ContentBlockGroup.objects.create(
            key=group_key,
            label=label,
            display_order=1,
        )
        block = ContentBlock.objects.create(
            key=key,
            group=group,
            label=label,
        )

        self._published_version(block, 2025, published_2025)
        active_2026 = self._published_version(block, 2026, published_2026)

        draft = ContentBlockVersion.objects.create(
            block=block,
            plan_year=2026,
            body_html='<p>UNPUBLISHED DRAFT MUST NOT APPEAR</p>',
        )
        in_review = ContentBlockVersion.objects.create(
            block=block,
            plan_year=2026,
            body_html='<p>UNPUBLISHED REVIEW MUST NOT APPEAR</p>',
        )
        in_review.submit_for_review()

        with self.subTest(key=key, plan_year=2024):
            response = self._post_for_year(2024)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), {'blocks': []})

        with self.subTest(key=key, plan_year=2025):
            response = self._post_for_year(2025)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), {
                'blocks': [{'key': key, 'html': published_2025, 'order': 1}],
            })

        with self.subTest(key=key, plan_year=2026):
            response = self._post_for_year(2026)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), {
                'blocks': [{'key': key, 'html': published_2026, 'order': 1}],
            })
            self.assertNotIn('UNPUBLISHED', response.json()['blocks'][0]['html'])

        active_2026.refresh_from_db()
        draft.refresh_from_db()
        in_review.refresh_from_db()
        self.assertEqual(active_2026.status, ContentBlockVersion.STATUS_PUBLISHED)
        self.assertEqual(draft.status, ContentBlockVersion.STATUS_DRAFT)
        self.assertEqual(in_review.status, ContentBlockVersion.STATUS_IN_REVIEW)
        self.assertEqual(block.published_version_for(2026).pk, active_2026.pk)

        editor = User.objects.create_user(
            username=f'i02_editor_{group_key}',
            role='administrator',
        )
        self.client.force_login(editor)
        editor_response = self.client.get(
            reverse('fact_finder_content:content_block_detail', args=[block.pk]),
            {'plan_year': 2026},
        )
        self.assertEqual(editor_response.status_code, 200)
        editor_form = editor_response.context['draft_form']
        self.assertEqual(editor_form['body_html'].value(), published_2026)
        self.assertEqual(editor_form['source_version_id'].value(), active_2026.pk)
        self.assertEqual(editor_form['version_id'].value(), '')
        self.assertNotEqual(draft.body_html, editor_form['body_html'].value())

    def test_cover_title_v1_response_uses_requested_year_and_published_version(self):
        self._assert_key_contract(
            key='cover.title',
            group_key='cover',
            label='Cover title',
            published_2025='<p>Published cover wording for 2025.</p>',
            published_2026='<p>Published cover wording for 2026.</p>',
        )

    def test_fers_heading_v1_response_is_year_scoped(self):
        self._assert_key_contract(
            key='pension.system_type_heading_fers',
            group_key='pension',
            label='FERS system heading',
            published_2025='<p>Published FERS heading for 2025.</p>',
            published_2026='<p>TEST OCT 19 2 Federal Employees Retirement System</p>',
        )
