from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.db import DatabaseError
from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from .models import ContentBlock, ContentBlockGroup, ContentBlockVersion


class FehbSaveAndPublishTests(TestCase):
    def setUp(self):
        group = ContentBlockGroup.objects.create(key='fehb', label='FEHB')
        self.block = ContentBlock.objects.create(
            key='fehb.purpose',
            label='FEHB Purpose',
            group=group,
            required_placeholders=['fehb.average_premium_increase'],
        )
        self.publisher = User.objects.create_user(
            username='fehb_publisher',
            role='administrator',
        )
        self.client.force_login(self.publisher)
        self.url = reverse(
            'fact_finder_content:content_block_detail',
            args=[self.block.pk],
        )
        self.published = ContentBlockVersion.objects.create(
            block=self.block,
            plan_year=2026,
            body_html='<p>Baseline [[fehb.average_premium_increase]]</p>',
            status=ContentBlockVersion.STATUS_PUBLISHED,
        )

    def post_editor(self, action, body_html):
        return self.client.post(self.url, {
            'action': action,
            'plan_year': 2026,
            'version_id': '',
            'source_version_id': self.published.pk,
            'body_html': body_html,
            'editor_ready': 'ready',
        })

    def test_save_draft_does_not_change_published_content(self):
        response = self.post_editor(
            'create_draft',
            '<p>Draft [[fehb.average_premium_increase]]</p>',
        )

        self.assertEqual(response.status_code, 302)
        self.published.refresh_from_db()
        self.assertEqual(self.published.status, ContentBlockVersion.STATUS_PUBLISHED)
        self.assertEqual(
            self.published.body_html,
            '<p>Baseline [[fehb.average_premium_increase]]</p>',
        )
        self.assertEqual(
            self.block.versions.get(status=ContentBlockVersion.STATUS_DRAFT).body_html,
            '<p>Draft [[fehb.average_premium_increase]]</p>',
        )

    def test_save_and_publish_activates_new_version_and_preserves_history(self):
        response = self.post_editor(
            'save_and_publish',
            '<p>Updated [[fehb.average_premium_increase]]</p>',
        )

        self.assertEqual(response.status_code, 302)
        self.published.refresh_from_db()
        active = self.block.versions.get(status=ContentBlockVersion.STATUS_PUBLISHED)
        self.assertEqual(
            active.body_html,
            '<p>Updated [[fehb.average_premium_increase]]</p>',
        )
        self.assertEqual(self.published.status, ContentBlockVersion.STATUS_SUPERSEDED)
        self.assertTrue(
            self.block.versions.filter(
                pk=self.published.pk,
                body_html='<p>Baseline [[fehb.average_premium_increase]]</p>',
            ).exists()
        )

    def test_required_merge_field_and_sanitization_are_enforced(self):
        response = self.post_editor(
            'save_and_publish',
            '<p>Missing required field</p><script>alert(1)</script>',
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Cannot publish')
        self.published.refresh_from_db()
        self.assertEqual(self.published.status, ContentBlockVersion.STATUS_PUBLISHED)
        self.assertEqual(self.block.versions.count(), 1)

    def test_save_and_publish_sanitizes_valid_wording(self):
        response = self.post_editor(
            'save_and_publish',
            '<p>Safe [[fehb.average_premium_increase]]</p><script>alert(1)</script>',
        )

        self.assertEqual(response.status_code, 302)
        active = self.block.versions.get(status=ContentBlockVersion.STATUS_PUBLISHED)
        self.assertEqual(
            active.body_html,
            '<p>Safe [[fehb.average_premium_increase]]</p>alert(1)',
        )
        self.assertNotIn('<script>', active.body_html)

    def test_direct_publish_remains_admin_only(self):
        technician = User.objects.create_user(
            username='fehb_technician',
            role='technician',
        )
        self.client.force_login(technician)

        response = self.post_editor(
            'save_and_publish',
            '<p>Unauthorized [[fehb.average_premium_increase]]</p>',
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.block.versions.count(), 1)
        self.published.refresh_from_db()
        self.assertEqual(self.published.status, ContentBlockVersion.STATUS_PUBLISHED)

    def test_database_failure_rolls_back_new_version_and_publication(self):
        original_publish = ContentBlockVersion.publish

        def publish_then_fail(version, *args, **kwargs):
            original_publish(version, *args, **kwargs)
            raise DatabaseError('simulated failure after publication')

        with patch.object(
            ContentBlockVersion,
            'publish',
            autospec=True,
            side_effect=publish_then_fail,
        ):
            response = self.post_editor(
                'save_and_publish',
                '<p>Attempted [[fehb.average_premium_increase]]</p>',
            )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'database error')
        self.assertEqual(self.block.versions.count(), 1)
        self.published.refresh_from_db()
        self.assertEqual(self.published.status, ContentBlockVersion.STATUS_PUBLISHED)

    def test_publication_requires_opt_in_to_draft_status(self):
        draft = ContentBlockVersion.objects.create(
            block=self.block,
            plan_year=2026,
            body_html='<p>Draft [[fehb.average_premium_increase]]</p>',
        )

        with self.assertRaises(ValidationError):
            draft.publish()

        self.assertEqual(draft.status, ContentBlockVersion.STATUS_DRAFT)

    def test_editor_exposes_both_actions_and_clear_confirmation(self):
        response = self.client.get(self.url)

        self.assertContains(response, 'Save Draft')
        self.assertContains(response, 'Save &amp; Publish')
        self.assertContains(response, 'This wording will become active in generated reports.')
        self.assertContains(
            response,
            'previous published version will remain in Version History',
        )
