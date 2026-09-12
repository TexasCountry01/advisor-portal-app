from django.test import TestCase
from django.urls import reverse

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


class ContentPanelViewTests(TestCase):
    def setUp(self):
        self.group = ContentBlockGroup.objects.create(key='tsp', label='TSP', display_order=8)
        self.block = ContentBlock.objects.create(
            key='tsp.agency_match_explanation',
            group=self.group,
            label='TSP Agency Match Explanation',
            required_placeholders=['match_percentage'],
        )
        self.admin = User.objects.create_user(
            username='ff_admin', password='Password123!', role='administrator',
            first_name='Admin', last_name='User',
        )
        self.technician = User.objects.create_user(
            username='ff_tech', password='Password123!', role='technician',
            first_name='Tech', last_name='User',
        )

    def test_content_list_requires_admin(self):
        self.client.force_login(self.technician)
        response = self.client.get(reverse('fact_finder_content:content_list'))
        self.assertEqual(response.status_code, 403)

    def test_content_list_loads_for_admin(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('fact_finder_content:content_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'TSP Agency Match Explanation')

    def test_content_block_detail_requires_admin(self):
        self.client.force_login(self.technician)
        response = self.client.get(reverse('fact_finder_content:content_block_detail', args=[self.block.id]))
        self.assertEqual(response.status_code, 403)

    def test_create_draft_via_post(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse('fact_finder_content:content_block_detail', args=[self.block.id]),
            {'action': 'create_draft', 'plan_year': 2026, 'body_html': '<p>You are contributing [[match_percentage]]%.</p>'},
        )
        self.assertRedirects(response, reverse('fact_finder_content:content_block_detail', args=[self.block.id]))
        version = ContentBlockVersion.objects.get(block=self.block, plan_year=2026)
        self.assertEqual(version.status, ContentBlockVersion.STATUS_DRAFT)
        self.assertEqual(version.created_by, self.admin)

    def test_create_draft_missing_placeholder_warns_but_still_saves(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse('fact_finder_content:content_block_detail', args=[self.block.id]),
            {'action': 'create_draft', 'plan_year': 2026, 'body_html': '<p>No token here.</p>'},
            follow=True,
        )
        self.assertContains(response, 'missing required placeholder')
        self.assertTrue(ContentBlockVersion.objects.filter(block=self.block, plan_year=2026).exists())

    def test_publish_blocked_when_placeholder_missing(self):
        self.client.force_login(self.admin)
        version = ContentBlockVersion.objects.create(
            block=self.block, plan_year=2026, body_html='<p>No token.</p>', created_by=self.admin,
        )
        response = self.client.post(
            reverse('fact_finder_content:content_block_detail', args=[self.block.id]),
            {'action': 'publish', 'version_id': version.id},
            follow=True,
        )
        version.refresh_from_db()
        self.assertEqual(version.status, ContentBlockVersion.STATUS_DRAFT)
        self.assertContains(response, 'Cannot publish')

    def test_publish_succeeds_when_placeholder_present(self):
        self.client.force_login(self.admin)
        version = ContentBlockVersion.objects.create(
            block=self.block, plan_year=2026, body_html='<p>[[match_percentage]]%</p>', created_by=self.admin,
        )
        response = self.client.post(
            reverse('fact_finder_content:content_block_detail', args=[self.block.id]),
            {'action': 'publish', 'version_id': version.id},
            follow=True,
        )
        version.refresh_from_db()
        self.assertEqual(version.status, ContentBlockVersion.STATUS_PUBLISHED)
        self.assertEqual(version.reviewed_by, self.admin)
        self.assertContains(response, 'Published')

    def test_submit_for_review(self):
        self.client.force_login(self.admin)
        version = ContentBlockVersion.objects.create(
            block=self.block, plan_year=2026, body_html='<p>[[match_percentage]]%</p>', created_by=self.admin,
        )
        self.client.post(
            reverse('fact_finder_content:content_block_detail', args=[self.block.id]),
            {'action': 'submit_for_review', 'version_id': version.id},
        )
        version.refresh_from_db()
        self.assertEqual(version.status, ContentBlockVersion.STATUS_IN_REVIEW)
