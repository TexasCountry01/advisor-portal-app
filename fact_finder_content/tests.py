from django.test import TestCase

from accounts.models import User
from fact_finder_content.models import ContentBlockGroup, ContentBlock, ContentBlockVersion


class ContentBlockModelTests(TestCase):
    def setUp(self):
        self.group = ContentBlockGroup.objects.create(key='tsp', label='TSP', display_order=8)
        self.block = ContentBlock.objects.create(
            key='tsp.agency_match_explanation',
            group=self.group,
            label='TSP Agency Match Explanation',
            required_placeholders=['match_percentage'],
        )
        self.editor = User.objects.create_user(
            username='content_editor',
            password='Password123!',
            role='administrator',
            first_name='Content',
            last_name='Editor',
        )

    def test_group_and_block_str(self):
        self.assertEqual(str(self.group), 'TSP')
        self.assertEqual(str(self.block), 'TSP — TSP Agency Match Explanation')

    def test_missing_placeholders_detects_absent_token(self):
        version = ContentBlockVersion.objects.create(
            block=self.block,
            plan_year=2026,
            body_html='<p>You are contributing enough to get the full match.</p>',
            created_by=self.editor,
        )
        self.assertEqual(version.missing_placeholders(), ['match_percentage'])

    def test_missing_placeholders_empty_when_token_present(self):
        version = ContentBlockVersion.objects.create(
            block=self.block,
            plan_year=2026,
            body_html='<p>You are contributing [[match_percentage]]% and receiving the full match.</p>',
            created_by=self.editor,
        )
        self.assertEqual(version.missing_placeholders(), [])

    def test_publish_sets_status_and_published_at(self):
        version = ContentBlockVersion.objects.create(
            block=self.block, plan_year=2026, body_html='<p>Draft text.</p>', created_by=self.editor,
        )
        self.assertEqual(version.status, ContentBlockVersion.STATUS_DRAFT)
        self.assertIsNone(version.published_at)

        version.publish(by_user=self.editor)

        version.refresh_from_db()
        self.assertEqual(version.status, ContentBlockVersion.STATUS_PUBLISHED)
        self.assertIsNotNone(version.published_at)
        self.assertEqual(version.reviewed_by, self.editor)

    def test_publish_supersedes_previous_published_version_same_plan_year(self):
        v1 = ContentBlockVersion.objects.create(block=self.block, plan_year=2026, body_html='<p>v1</p>')
        v1.publish()
        v1.refresh_from_db()
        self.assertEqual(v1.status, ContentBlockVersion.STATUS_PUBLISHED)

        v2 = ContentBlockVersion.objects.create(block=self.block, plan_year=2026, body_html='<p>v2</p>')
        v2.publish()

        v1.refresh_from_db()
        v2.refresh_from_db()
        self.assertEqual(v1.status, ContentBlockVersion.STATUS_SUPERSEDED)
        self.assertEqual(v2.status, ContentBlockVersion.STATUS_PUBLISHED)

    def test_publish_does_not_affect_other_plan_years(self):
        v_2025 = ContentBlockVersion.objects.create(block=self.block, plan_year=2025, body_html='<p>2025</p>')
        v_2025.publish()

        v_2026 = ContentBlockVersion.objects.create(block=self.block, plan_year=2026, body_html='<p>2026</p>')
        v_2026.publish()

        v_2025.refresh_from_db()
        v_2026.refresh_from_db()
        self.assertEqual(v_2025.status, ContentBlockVersion.STATUS_PUBLISHED)
        self.assertEqual(v_2026.status, ContentBlockVersion.STATUS_PUBLISHED)

    def test_published_version_for_returns_correct_plan_year(self):
        v_2025 = ContentBlockVersion.objects.create(block=self.block, plan_year=2025, body_html='<p>2025</p>')
        v_2025.publish()
        v_2026 = ContentBlockVersion.objects.create(block=self.block, plan_year=2026, body_html='<p>2026</p>')
        v_2026.publish()

        self.assertEqual(self.block.published_version_for(2025), v_2025)
        self.assertEqual(self.block.published_version_for(2026), v_2026)
        self.assertIsNone(self.block.published_version_for(2027))

    def test_content_block_group_protected_on_delete(self):
        from django.db.models import ProtectedError
        with self.assertRaises(ProtectedError):
            self.group.delete()
