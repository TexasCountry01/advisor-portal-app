import json

from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from core.models import SystemSettings
from fact_finder_content.models import ContentBlock, ContentBlockGroup, ContentBlockVersion
from fact_finder_content.tests_api import _valid_data_contract


class FehbPublicationWorkflowTests(TestCase):
    def setUp(self):
        settings_obj = SystemSettings.get_settings()
        settings_obj.benefits_software_api_key = 'fehb-test-only-key'
        settings_obj.save()

        self.group = ContentBlockGroup.objects.create(key='fehb', label='FEHB')
        self.block = ContentBlock.objects.create(
            key='fehb.purpose',
            group=self.group,
            label='FEHB Purpose (test fixture)',
        )
        self.editor = User.objects.create_user(
            username='fehb_test_editor',
            role='administrator',
        )
        self.client.force_login(self.editor)
        self.editor_url = reverse(
            'fact_finder_content:content_block_detail',
            args=[self.block.pk],
        )
        self.resolve_url = reverse('fact_finder_resolve_content')
        self.source = ContentBlockVersion.objects.create(
            block=self.block,
            plan_year=2026,
            body_html='<p>TEST ONLY: original FEHB purpose.</p>',
            status=ContentBlockVersion.STATUS_PUBLISHED,
        )

    def resolve(self, plan_year=2026, data_contract=None):
        return self.client.post(
            self.resolve_url,
            data=json.dumps({
                'plan_year': plan_year,
                'data_contract': data_contract or _valid_data_contract(),
            }),
            content_type='application/json',
            HTTP_AUTHORIZATION='Bearer fehb-test-only-key',
        )

    def editor_post(self, action, body_html, **extra):
        payload = {
            'action': action,
            'plan_year': 2026,
            'body_html': body_html,
            'source_version_id': self.source.pk,
            'editor_ready': 'ready',
        }
        payload.update(extra)
        return self.client.post(self.editor_url, payload)

    def active_body(self, response=None):
        response = response or self.resolve()
        self.assertEqual(response.status_code, 200)
        blocks = response.json()['blocks']
        matching = [block for block in blocks if block['key'] == 'fehb.purpose']
        return matching[0]['html'] if matching else None

    def test_matching_plan_year_returns_published_test_content(self):
        self.assertEqual(
            self.active_body(),
            '<p>TEST ONLY: original FEHB purpose.</p>',
        )

    def test_save_draft_does_not_change_active_published_response(self):
        response = self.editor_post(
            'create_draft',
            '<p>TEST ONLY: draft FEHB purpose.</p>',
        )

        self.assertEqual(response.status_code, 302)
        self.source.refresh_from_db()
        self.assertEqual(self.source.status, ContentBlockVersion.STATUS_PUBLISHED)
        self.assertEqual(
            self.active_body(),
            '<p>TEST ONLY: original FEHB purpose.</p>',
        )
        draft = self.block.versions.get(status=ContentBlockVersion.STATUS_DRAFT)
        self.assertEqual(draft.body_html, '<p>TEST ONLY: draft FEHB purpose.</p>')

    def test_save_and_publish_changes_response_and_preserves_prior_history(self):
        response = self.editor_post(
            'save_and_publish',
            '<p>TEST ONLY: newly published FEHB purpose.</p>',
        )

        self.assertEqual(response.status_code, 302)
        self.source.refresh_from_db()
        self.assertEqual(self.source.status, ContentBlockVersion.STATUS_SUPERSEDED)
        self.assertEqual(self.source.body_html, '<p>TEST ONLY: original FEHB purpose.</p>')
        published = self.block.versions.get(status=ContentBlockVersion.STATUS_PUBLISHED)
        self.assertEqual(
            published.body_html,
            '<p>TEST ONLY: newly published FEHB purpose.</p>',
        )
        self.assertEqual(self.block.versions.count(), 2)
        self.assertEqual(
            self.active_body(),
            '<p>TEST ONLY: newly published FEHB purpose.</p>',
        )

    def test_unauthorized_user_cannot_publish_directly(self):
        unauthorized = User.objects.create_user(
            username='fehb_test_technician',
            role='technician',
        )
        self.client.force_login(unauthorized)

        response = self.editor_post(
            'save_and_publish',
            '<p>TEST ONLY: unauthorized FEHB wording.</p>',
        )

        self.assertEqual(response.status_code, 403)
        self.source.refresh_from_db()
        self.assertEqual(self.source.status, ContentBlockVersion.STATUS_PUBLISHED)
        self.assertEqual(self.block.versions.count(), 1)
        self.assertEqual(
            self.active_body(),
            '<p>TEST ONLY: original FEHB purpose.</p>',
        )

    def test_missing_publication_is_not_returned(self):
        unpublished = ContentBlock.objects.create(
            key='fehb.coverage_available',
            group=self.group,
            label='FEHB Coverage Available (test fixture)',
        )

        response = self.resolve()
        self.assertEqual(response.status_code, 200)
        returned_keys = {block['key'] for block in response.json()['blocks']}
        self.assertNotIn(unpublished.key, returned_keys)

    def test_wrong_plan_year_is_not_returned(self):
        self.assertIsNone(self.active_body(self.resolve(plan_year=2025)))

    def test_inactive_block_is_not_returned(self):
        self.block.is_active = False
        self.block.save(update_fields=['is_active'])

        self.assertIsNone(self.active_body())

    def test_false_display_condition_is_not_returned(self):
        self.block.display_condition = {'rules': [{
            'field': 'system.system_type',
            'operator': 'equals',
            'value': 'CSRS',
        }]}
        self.block.save(update_fields=['display_condition'])

        self.assertIsNone(self.active_body())

    def test_invalid_or_missing_required_content_cannot_replace_publication(self):
        empty_after_sanitization = self.editor_post(
            'save_and_publish',
            '<p><br></p>',
        )
        self.assertEqual(empty_after_sanitization.status_code, 200)
        self.assertEqual(self.block.versions.count(), 1)
        self.assertEqual(
            self.active_body(),
            '<p>TEST ONLY: original FEHB purpose.</p>',
        )

        self.block.required_placeholders = ['fehb.average_premium_increase']
        self.block.save(update_fields=['required_placeholders'])
        missing_token = self.editor_post(
            'save_and_publish',
            '<p>TEST ONLY: wording without the required token.</p>',
        )
        self.assertEqual(missing_token.status_code, 200)
        self.assertEqual(self.block.versions.count(), 1)
        self.source.refresh_from_db()
        self.assertEqual(self.source.status, ContentBlockVersion.STATUS_PUBLISHED)
        self.assertEqual(
            self.active_body(),
            '<p>TEST ONLY: original FEHB purpose.</p>',
        )
