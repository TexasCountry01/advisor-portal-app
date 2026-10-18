import json

from django.test import RequestFactory, TestCase
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.db import OperationalError, close_old_connections
from django.test import TransactionTestCase
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import patch
from django.contrib import admin

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

    def test_version_admin_is_read_only(self):
        version_admin = admin.site._registry[ContentBlockVersion]
        request = RequestFactory().get('/admin/')
        self.assertFalse(version_admin.has_add_permission(request))
        self.assertFalse(version_admin.has_delete_permission(request))
        self.assertEqual(
            set(version_admin.readonly_fields),
            {field.name for field in ContentBlockVersion._meta.fields},
        )

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
            block=self.block, plan_year=2026,
            body_html='<p>Draft [[match_percentage]] text.</p>', created_by=self.editor,
        )
        self.assertEqual(version.status, ContentBlockVersion.STATUS_DRAFT)
        self.assertIsNone(version.published_at)

        version.submit_for_review()
        version.refresh_from_db()
        self.assertEqual(version.status, ContentBlockVersion.STATUS_IN_REVIEW)
        version.publish(by_user=self.editor)

        version.refresh_from_db()
        self.assertEqual(version.status, ContentBlockVersion.STATUS_PUBLISHED)
        self.assertIsNotNone(version.published_at)
        self.assertEqual(version.reviewed_by, self.editor)

    def test_draft_cannot_be_published_directly(self):
        version = ContentBlockVersion.objects.create(
            block=self.block,
            plan_year=2026,
            body_html='<p>Draft [[match_percentage]] text.</p>',
            created_by=self.editor,
        )
        with self.assertRaisesMessage(ValidationError, 'Only versions in review'):
            version.publish(by_user=self.editor)
        version.refresh_from_db()
        self.assertEqual(version.status, ContentBlockVersion.STATUS_DRAFT)

    def test_publish_supersedes_previous_published_version_same_plan_year(self):
        v1 = ContentBlockVersion.objects.create(
            block=self.block, plan_year=2026, body_html='<p>v1 [[match_percentage]]</p>',
        )
        v1.submit_for_review()
        v1.publish()
        v1.refresh_from_db()
        self.assertEqual(v1.status, ContentBlockVersion.STATUS_PUBLISHED)

        v2 = ContentBlockVersion.objects.create(
            block=self.block, plan_year=2026, body_html='<p>v2 [[match_percentage]]</p>',
        )
        v2.submit_for_review()
        v2.publish()

        v1.refresh_from_db()
        v2.refresh_from_db()
        self.assertEqual(v1.status, ContentBlockVersion.STATUS_SUPERSEDED)
        self.assertEqual(v2.status, ContentBlockVersion.STATUS_PUBLISHED)
        self.assertEqual(v1.body_html, '<p>v1 [[match_percentage]]</p>')
        self.assertIsNone(v1.merge_field_policy)

    def test_publish_does_not_affect_other_plan_years(self):
        v_2025 = ContentBlockVersion.objects.create(
            block=self.block, plan_year=2025, body_html='<p>2025 [[match_percentage]]</p>',
        )
        v_2025.submit_for_review()
        v_2025.publish()

        v_2026 = ContentBlockVersion.objects.create(
            block=self.block, plan_year=2026, body_html='<p>2026 [[match_percentage]]</p>',
        )
        v_2026.submit_for_review()
        v_2026.publish()

        v_2025.refresh_from_db()
        v_2026.refresh_from_db()
        self.assertEqual(v_2025.status, ContentBlockVersion.STATUS_PUBLISHED)
        self.assertEqual(v_2026.status, ContentBlockVersion.STATUS_PUBLISHED)

    def test_legacy_null_policy_remains_publishable(self):
        version = ContentBlockVersion.objects.create(
            block=self.block,
            plan_year=2026,
            body_html='<p>Legacy [[match_percentage]] text.</p>',
            merge_field_policy=None,
        )
        version.submit_for_review()
        version.publish(by_user=self.editor)
        version.refresh_from_db()
        self.assertEqual(version.status, ContentBlockVersion.STATUS_PUBLISHED)
        self.assertIsNone(version.merge_field_policy)

    def test_valid_policy_is_published_and_historical_version_is_preserved(self):
        policy = {
            'schema_version': 1,
            'tokens': [{
                'token': 'pension.cola',
                'value_type': 'string',
                'format': 'plain',
                'presence': 'required',
                'null': 'error',
                'blank': 'error',
                'omission': None,
            }],
        }
        block = ContentBlock.objects.create(
            key='pension.policy_publication_test',
            group=self.group,
            label='Policy publication test',
            required_placeholders=['pension.cola'],
        )
        prior = ContentBlockVersion.objects.create(
            block=block,
            plan_year=2026,
            body_html='<p>Prior [[pension.cola]]%</p>',
        )
        prior.submit_for_review()
        prior.publish()
        candidate = ContentBlockVersion.objects.create(
            block=block,
            plan_year=2026,
            body_html='<p>New [[pension.cola]]%</p>',
            merge_field_policy=policy,
        )
        candidate.submit_for_review()
        candidate.publish(by_user=self.editor)
        prior.refresh_from_db()
        candidate.refresh_from_db()
        self.assertEqual(prior.status, ContentBlockVersion.STATUS_SUPERSEDED)
        self.assertEqual(prior.body_html, '<p>Prior [[pension.cola]]%</p>')
        self.assertIsNone(prior.merge_field_policy)
        self.assertEqual(candidate.status, ContentBlockVersion.STATUS_PUBLISHED)
        self.assertEqual(candidate.merge_field_policy, policy)
        self.assertEqual(candidate.reviewed_by, self.editor)

    def test_invalid_policy_is_rejected_before_review(self):
        invalid_policy = {
            'schema_version': 1,
            'tokens': [{
                'token': 'system.unknown',
                'value_type': 'string',
                'format': 'plain',
                'presence': 'required',
                'null': 'error',
                'blank': 'error',
                'omission': None,
            }],
        }
        self.block.required_placeholders = ['system.unknown']
        self.block.save()
        version = ContentBlockVersion.objects.create(
            block=self.block,
            plan_year=2026,
            body_html='<p>[[system.unknown]]</p>',
            merge_field_policy=invalid_policy,
        )
        with self.assertRaises(ValidationError):
            version.submit_for_review()
        version.refresh_from_db()
        self.assertEqual(version.status, ContentBlockVersion.STATUS_DRAFT)

    def test_missing_legacy_required_placeholder_is_rejected_before_review(self):
        version = ContentBlockVersion.objects.create(
            block=self.block,
            plan_year=2026,
            body_html='<p>No merge token.</p>',
        )
        with self.assertRaisesMessage(ValidationError, 'Missing required placeholder'):
            version.submit_for_review()
        version.refresh_from_db()
        self.assertEqual(version.status, ContentBlockVersion.STATUS_DRAFT)

    def test_invalid_policy_at_publication_preserves_existing_publication(self):
        prior = ContentBlockVersion.objects.create(
            block=self.block,
            plan_year=2026,
            body_html='<p>Prior [[match_percentage]] text.</p>',
        )
        prior.submit_for_review()
        prior.publish()
        invalid_policy = {
            'schema_version': 1,
            'tokens': [{
                'token': 'system.unknown',
                'value_type': 'string',
                'format': 'plain',
                'presence': 'required',
                'null': 'error',
                'blank': 'error',
                'omission': None,
            }],
        }
        candidate = ContentBlockVersion.objects.create(
            block=self.block,
            plan_year=2026,
            body_html='<p>[[system.unknown]]</p>',
            merge_field_policy=invalid_policy,
        )
        candidate.status = ContentBlockVersion.STATUS_IN_REVIEW
        candidate.save()
        with self.assertRaises(ValidationError):
            candidate.publish()
        prior.refresh_from_db()
        candidate.refresh_from_db()
        self.assertEqual(prior.status, ContentBlockVersion.STATUS_PUBLISHED)
        self.assertEqual(candidate.status, ContentBlockVersion.STATUS_IN_REVIEW)

    def test_publication_failure_rolls_back_supersession(self):
        prior = ContentBlockVersion.objects.create(
            block=self.block,
            plan_year=2026,
            body_html='<p>Prior [[match_percentage]] text.</p>',
        )
        prior.submit_for_review()
        prior.publish()
        candidate = ContentBlockVersion.objects.create(
            block=self.block,
            plan_year=2026,
            body_html='<p>New [[match_percentage]] text.</p>',
        )
        candidate.submit_for_review()
        with patch.object(
            ContentBlockVersion,
            'save',
            side_effect=RuntimeError('simulated save failure'),
        ):
            with self.assertRaisesMessage(RuntimeError, 'simulated save failure'):
                candidate.publish()
        prior.refresh_from_db()
        candidate.refresh_from_db()
        self.assertEqual(prior.status, ContentBlockVersion.STATUS_PUBLISHED)
        self.assertEqual(candidate.status, ContentBlockVersion.STATUS_IN_REVIEW)

    def test_published_version_for_returns_correct_plan_year(self):
        v_2025 = ContentBlockVersion.objects.create(
            block=self.block, plan_year=2025, body_html='<p>2025 [[match_percentage]]</p>',
        )
        v_2025.submit_for_review()
        v_2025.publish()
        v_2026 = ContentBlockVersion.objects.create(
            block=self.block, plan_year=2026, body_html='<p>2026 [[match_percentage]]</p>',
        )
        v_2026.submit_for_review()
        v_2026.publish()

        self.assertEqual(self.block.published_version_for(2025), v_2025)
        self.assertEqual(self.block.published_version_for(2026), v_2026)
        self.assertIsNone(self.block.published_version_for(2027))

    def test_content_block_group_protected_on_delete(self):
        from django.db.models import ProtectedError
        with self.assertRaises(ProtectedError):
            self.group.delete()

    def test_save_sanitizes_body_html_on_create(self):
        version = ContentBlockVersion.objects.create(
            block=self.block, plan_year=2026,
            body_html='<p>Hi</p><script>alert(1)</script>',
        )
        self.assertNotIn('<script', version.body_html)

    def test_save_sanitizes_body_html_on_update(self):
        version = ContentBlockVersion.objects.create(
            block=self.block, plan_year=2026, body_html='<p>Clean</p>',
        )
        version.body_html = '<p onclick="alert(1)">Edited</p>'
        version.save()
        version.refresh_from_db()
        self.assertNotIn('onclick', version.body_html)
        self.assertIn('Edited', version.body_html)


class ContentBlockVersionConcurrentPublicationTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        self.group = ContentBlockGroup.objects.create(key='concurrent', label='Concurrent')
        self.block = ContentBlock.objects.create(
            key='concurrent.publication',
            group=self.group,
            label='Concurrent publication',
        )
        self.prior = ContentBlockVersion.objects.create(
            block=self.block,
            plan_year=2026,
            body_html='<p>Prior wording.</p>',
        )
        self.prior.submit_for_review()
        self.prior.publish()
        self.candidates = []
        for text in ('First candidate', 'Second candidate'):
            candidate = ContentBlockVersion.objects.create(
                block=self.block,
                plan_year=2026,
                body_html=f'<p>{text}.</p>',
            )
            candidate.submit_for_review()
            self.candidates.append(candidate.pk)

    def test_competing_publications_leave_at_most_one_published_version(self):
        barrier = Barrier(2)

        def publish_candidate(version_id):
            close_old_connections()
            try:
                version = ContentBlockVersion.objects.get(pk=version_id)
                barrier.wait(timeout=10)
                version.publish()
                return 'published'
            except OperationalError:
                return 'database_busy'
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(publish_candidate, self.candidates))

        self.assertIn('published', results)
        self.assertEqual(
            ContentBlockVersion.objects.filter(
                block=self.block,
                plan_year=2026,
                status=ContentBlockVersion.STATUS_PUBLISHED,
            ).count(),
            1,
        )
        self.prior.refresh_from_db()
        self.assertIn(
            self.prior.status,
            (ContentBlockVersion.STATUS_SUPERSEDED, ContentBlockVersion.STATUS_PUBLISHED),
        )


class WiringStatusTests(TestCase):
    """
    Grounded in a direct scan of benefits-software/resources/views/admin/employee/
    report_pdf.blade.php on 2026-09-19 — see fact_finder_content/wiring_status.py's
    module docstring for the full rationale and maintenance burden.
    """

    def test_known_wired_block_is_wired(self):
        from fact_finder_content.wiring_status import is_wired
        self.assertTrue(is_wired('fltcip.what_is_ltc'))

    def test_cover_title_is_wired(self):
        # cover.title was wired 2026-09-20 (Option A from the "Options for the 14
        # not-yet-connected blocks" section) -- previously the canonical "never wired"
        # example in this test file; now it's wired, so it moved to this test instead.
        from fact_finder_content.wiring_status import is_wired
        self.assertTrue(is_wired('cover.title'))

    def test_deferred_structural_block_is_not_wired(self):
        from fact_finder_content.wiring_status import is_wired
        self.assertFalse(is_wired('checklist.next_steps'))

    def test_unknown_key_is_not_wired(self):
        from fact_finder_content.wiring_status import is_wired
        self.assertFalse(is_wired('not_a_real_key.anything'))


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

    def test_content_list_now_shows_pdf_ordered_preview(self):
        """Phase 2C-2: the canonical fact_finder_content:content_list URL is
        reused by the Admin Dashboard's existing button and is now expected
        to serve the PDF-ordered preview (views.pdf_order_preview) rather
        than the original alphabetical list."""
        self.client.force_login(self.admin)
        response = self.client.get(reverse('fact_finder_content:content_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Fact Finder PDF — Report Order Preview')

    def test_legacy_content_list_requires_admin(self):
        self.client.force_login(self.technician)
        response = self.client.get(reverse('fact_finder_content:legacy_content_list'))
        self.assertEqual(response.status_code, 403)

    def test_legacy_content_list_loads_for_admin(self):
        """The original alphabetical-by-label list is preserved, unmodified,
        behind a separate, administrator-only legacy URL (Phase 2C-2)."""
        self.client.force_login(self.admin)
        response = self.client.get(reverse('fact_finder_content:legacy_content_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'TSP Agency Match Explanation')

    def test_dashboard_button_url_is_unaffected_by_the_canonical_route_swap(self):
        """The Admin Dashboard's existing 'Fact Finder Content' button reverses
        'fact_finder_content:content_list' by name — since only the view behind
        that name changed (not the name itself or its URL path), the button's
        href is identical before and after Phase 2C-2."""
        self.assertEqual(reverse('fact_finder_content:content_list'), '/fact-finder-content/')

    def test_content_block_detail_requires_admin(self):
        self.client.force_login(self.technician)
        response = self.client.get(reverse('fact_finder_content:content_block_detail', args=[self.block.id]))
        self.assertEqual(response.status_code, 403)

    def test_detail_page_shows_live_badge_for_wired_block(self):
        # tsp.agency_match_explanation is a real, wired key (see wiring_status.py).
        self.client.force_login(self.admin)
        response = self.client.get(reverse('fact_finder_content:content_block_detail', args=[self.block.id]))
        self.assertContains(response, 'Connected report section')
        self.assertNotContains(response, 'Live in PDF')
        self.assertNotContains(response, 'Not yet connected to PDF')

    def test_detail_page_shows_not_connected_badge_for_unwired_block(self):
        unwired_block = ContentBlock.objects.create(
            key='checklist.next_steps', group=self.group, label='Checklist Next Steps',
        )
        self.client.force_login(self.admin)
        response = self.client.get(reverse('fact_finder_content:content_block_detail', args=[unwired_block.id]))
        self.assertContains(response, 'Not yet connected to PDF')
        self.assertContains(response, 'no effect')

    def test_create_draft_via_post(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse('fact_finder_content:content_block_detail', args=[self.block.id]),
            {'action': 'create_draft', 'plan_year': 2026, 'editor_ready': 'ready', 'body_html': '<p>You are contributing [[match_percentage]]%.</p>'},
        )
        self.assertRedirects(response, reverse('fact_finder_content:content_block_detail', args=[self.block.id]) + '?plan_year=2026')
        version = ContentBlockVersion.objects.get(block=self.block, plan_year=2026)
        self.assertEqual(version.status, ContentBlockVersion.STATUS_DRAFT)
        self.assertEqual(version.created_by, self.admin)

    def test_create_draft_via_post_sanitizes_html(self):
        self.client.force_login(self.admin)
        self.client.post(
            reverse('fact_finder_content:content_block_detail', args=[self.block.id]),
            {'action': 'create_draft', 'plan_year': 2026, 'editor_ready': 'ready', 'body_html': '<p onclick="alert(1)">[[match_percentage]]</p><script>alert(2)</script>'},
        )
        version = ContentBlockVersion.objects.get(block=self.block, plan_year=2026)
        self.assertNotIn('onclick', version.body_html)
        self.assertNotIn('<script', version.body_html)
        self.assertIn('[[match_percentage]]', version.body_html)

    def test_create_draft_missing_placeholder_warns_but_still_saves(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse('fact_finder_content:content_block_detail', args=[self.block.id]),
            {'action': 'create_draft', 'plan_year': 2026, 'editor_ready': 'ready', 'body_html': '<p>No token here.</p>'},
            follow=True,
        )
        self.assertContains(response, 'missing required placeholder')
        self.assertTrue(ContentBlockVersion.objects.filter(block=self.block, plan_year=2026).exists())

    def test_publish_blocked_when_placeholder_missing(self):
        self.client.force_login(self.admin)
        version = ContentBlockVersion.objects.create(
            block=self.block, plan_year=2026, body_html='<p>No token.</p>', created_by=self.admin,
        )
        version.status = ContentBlockVersion.STATUS_IN_REVIEW
        version.save()
        response = self.client.post(
            reverse('fact_finder_content:content_block_detail', args=[self.block.id]),
            {'action': 'publish', 'version_id': version.id},
            follow=True,
        )
        version.refresh_from_db()
        self.assertEqual(version.status, ContentBlockVersion.STATUS_IN_REVIEW)
        self.assertContains(response, 'Missing required placeholder')

    def test_content_editor_rejects_direct_draft_publication(self):
        self.client.force_login(self.admin)
        version = ContentBlockVersion.objects.create(
            block=self.block,
            plan_year=2026,
            body_html='<p>[[match_percentage]]%</p>',
            created_by=self.admin,
        )
        response = self.client.post(
            reverse('fact_finder_content:content_block_detail', args=[self.block.id]),
            {'action': 'publish', 'version_id': version.id},
            follow=True,
        )
        version.refresh_from_db()
        self.assertEqual(version.status, ContentBlockVersion.STATUS_DRAFT)
        self.assertContains(response, 'Only versions in review')

    def test_publish_succeeds_when_placeholder_present(self):
        self.client.force_login(self.admin)
        version = ContentBlockVersion.objects.create(
            block=self.block, plan_year=2026, body_html='<p>[[match_percentage]]%</p>', created_by=self.admin,
        )
        version.submit_for_review()
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

    def test_submit_for_review_rejects_invalid_merge_policy(self):
        self.client.force_login(self.admin)
        block = ContentBlock.objects.create(
            key='pension.invalid_policy_review',
            group=self.group,
            label='Invalid policy review',
            required_placeholders=['system.unknown'],
        )
        version = ContentBlockVersion.objects.create(
            block=block,
            plan_year=2026,
            body_html='<p>[[system.unknown]]</p>',
            merge_field_policy={'schema_version': 1, 'tokens': []},
            created_by=self.admin,
        )
        response = self.client.post(
            reverse('fact_finder_content:content_block_detail', args=[block.id]),
            {'action': 'submit_for_review', 'version_id': version.id},
            follow=True,
        )
        version.refresh_from_db()
        self.assertEqual(version.status, ContentBlockVersion.STATUS_DRAFT)
        self.assertContains(response, 'Cannot submit for review')

    def test_wording_editor_inherits_policy_and_preserves_it_on_draft_update(self):
        self.client.force_login(self.admin)
        block = ContentBlock.objects.create(
            key='pension.policy_editor',
            group=self.group,
            label='Policy editor',
            required_placeholders=['pension.cola'],
        )
        policy = {
            'schema_version': 1,
            'tokens': [{
                'token': 'pension.cola',
                'value_type': 'string',
                'format': 'plain',
                'presence': 'required',
                'null': 'error',
                'blank': 'error',
                'omission': None,
            }],
        }
        url = reverse('fact_finder_content:content_block_detail', args=[block.id])
        source = ContentBlockVersion.objects.create(
            block=block, plan_year=2026, body_html='<p>[[pension.cola]]%</p>',
            merge_field_policy=policy, status=ContentBlockVersion.STATUS_PUBLISHED,
        )
        self.client.post(
            url,
            {
                'action': 'create_draft',
                'plan_year': 2026,
                'editor_ready': 'ready',
                'source_version_id': source.id,
                'body_html': '<p>COLA [[pension.cola]]%</p>',
                'merge_field_policy': json.dumps(policy),
            },
        )
        draft = ContentBlockVersion.objects.get(block=block, status=ContentBlockVersion.STATUS_DRAFT)
        self.assertEqual(draft.merge_field_policy, policy)

        response = self.client.get(url)
        self.assertNotContains(response, 'Merge-field policy JSON')
        self.assertNotContains(response, 'data-merge-field-policy')

        updated_policy = dict(policy)
        updated_policy['tokens'] = [dict(policy['tokens'][0], format='plain')]
        self.client.post(
            url,
            {
                'action': 'create_draft',
                'version_id': draft.id,
                'plan_year': 2026,
                'editor_ready': 'ready',
                'body_html': '<p>Updated COLA [[pension.cola]]%</p>',
                'merge_field_policy': json.dumps(updated_policy),
            },
        )
        draft.refresh_from_db()
        self.assertEqual(
            ContentBlockVersion.objects.filter(block=block, plan_year=2026).count(),
            2,
        )
        self.assertEqual(draft.body_html, '<p>Updated COLA [[pension.cola]]%</p>')
        self.assertEqual(draft.merge_field_policy, updated_policy)

    def test_client_policy_input_is_not_used(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse('fact_finder_content:content_block_detail', args=[self.block.id]),
            {
                'action': 'create_draft',
                'plan_year': 2026,
                'editor_ready': 'ready',
                'body_html': '<p>[[match_percentage]]%</p>',
                'merge_field_policy': '{invalid json',
            },
            follow=True,
        )
        self.assertContains(response, 'Draft saved')
        self.assertIsNone(ContentBlockVersion.objects.get(block=self.block).merge_field_policy)

    def test_detail_page_renders_merge_field_picker_from_required_placeholders(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('fact_finder_content:content_block_detail', args=[self.block.id]))
        self.assertContains(response, 'id="merge_field_picker"')
        self.assertContains(response, '<option value="match_percentage">match_percentage</option>')

    def test_detail_page_hides_merge_field_picker_when_no_placeholders_required(self):
        plain_block = ContentBlock.objects.create(
            key='cover.title', group=self.group, label='Cover Title', required_placeholders=[],
        )
        self.client.force_login(self.admin)
        response = self.client.get(reverse('fact_finder_content:content_block_detail', args=[plain_block.id]))
        self.assertNotContains(response, 'id="merge_field_picker"')

    def test_detail_page_renders_tinymce_editor_with_restricted_toolbar(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('fact_finder_content:content_block_detail', args=[self.block.id]))
        self.assertContains(response, 'tinymce.min.js')
        self.assertContains(response, "toolbar: 'formatselect | bold italic underline | bullist numlist | styleselect | table tableprops tabledelete | tableinsertrowbefore tableinsertrowafter tabledeleterow | tableinsertcolbefore tableinsertcolafter tabledeletecol'")
        self.assertNotContains(response, 'id="body_html_hidden"')
        self.assertContains(response, 'id="body_html" name="body_html"')
        self.assertContains(response, 'id="save-draft-btn" class="btn btn-primary" disabled')

    def test_detail_page_shows_golden_master_gate_matching_all_24_when_no_rules(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('fact_finder_content:content_block_detail', args=[self.block.id]))
        self.assertContains(response, 'Preview when this content appears')
        self.assertContains(response, 'Included in 24 of 24 representative reports')

    def test_detail_page_golden_master_gate_reflects_display_condition(self):
        self.block.display_condition = {'rules': [
            {'field': 'computed_flags.is_wep_applicable', 'operator': 'equals', 'value': True},
        ]}
        self.block.save()
        self.client.force_login(self.admin)
        response = self.client.get(reverse('fact_finder_content:content_block_detail', args=[self.block.id]))
        # Grounded in the same real-data fact verified in fact_finder_content/tests_golden_master.py:
        # exactly 3 of the 24 golden-master cases have is_wep_applicable == True.
        self.assertContains(response, 'Included in 3 of 24 representative reports')

    def test_detail_page_preview_case_detail_collapsed_but_accessible(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('fact_finder_content:content_block_detail', args=[self.block.id]))
        self.assertContains(response, 'View representative cases')
        # The full 24-case breakdown is still rendered (accessible on demand) but
        # not an enforced publication gate, and not expanded by default.
        self.assertContains(response, '✓ Included')
        self.assertContains(response, '✗ Not included')
        self.assertNotContains(response, '<details open')

    def test_detail_page_distinguishes_wording_status_from_pdf_wiring_status(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('fact_finder_content:content_block_detail', args=[self.block.id]))
        self.assertContains(response, 'Connected report section')
        self.assertContains(response, 'Report Content — ')
        self.assertContains(response, 'Version History')

    def test_detail_page_does_not_prominently_show_raw_content_key(self):
        # The raw dotted content key must not sit next to the title/section label
        # during normal editing; it's still available, just de-emphasized below
        # a "Technical details" disclosure — never removed from the model/URL.
        self.client.force_login(self.admin)
        response = self.client.get(reverse('fact_finder_content:content_block_detail', args=[self.block.id]))
        self.assertNotContains(response, '&middot;')
        self.assertContains(response, 'Technical details')
        self.assertContains(response, 'Content key: <code>tsp.agency_match_explanation</code>')

    def test_plan_year_not_presented_as_an_editable_field(self):
        from fact_finder_content.views import _default_plan_year
        self.client.force_login(self.admin)
        response = self.client.get(reverse('fact_finder_content:content_block_detail', args=[self.block.id]))
        expected_year = _default_plan_year()
        self.assertContains(response, f'id="plan_year" name="plan_year" value="{expected_year}"')
        self.assertNotContains(response, 'type="number" id="plan_year"')
        self.assertNotContains(response, 'for="plan_year" class="form-label"')

    def test_plan_year_submission_behavior_is_unchanged(self):
        # The hidden field's value round-trips through the exact same POST
        # handling (views.content_block_detail's create_draft branch) as before.
        from fact_finder_content.views import _default_plan_year
        self.client.force_login(self.admin)
        expected_year = _default_plan_year()
        self.client.post(
            reverse('fact_finder_content:content_block_detail', args=[self.block.id]),
            {'action': 'create_draft', 'plan_year': expected_year, 'editor_ready': 'ready', 'body_html': '<p>[[match_percentage]]%</p>'},
        )
        version = ContentBlockVersion.objects.get(block=self.block, plan_year=expected_year)
        self.assertEqual(version.status, ContentBlockVersion.STATUS_DRAFT)

    def test_report_wording_label_and_concise_editing_instructions(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('fact_finder_content:content_block_detail', args=[self.block.id]))
        self.assertContains(response, '<label for="body_html" class="form-label">Report wording</label>')
        self.assertNotContains(response, '>Body</label>')
        self.assertContains(response, 'Edit the wording that appears in the Fact Finder report.')
        self.assertContains(response, 'Your changes will not appear in the PDF until they are published.')

    def test_editor_uses_small_autosizing_height_instead_of_fixed_large_box(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('fact_finder_content:content_block_detail', args=[self.block.id]))
        self.assertContains(response, "plugins: 'lists table autoresize'")
        self.assertContains(response, 'min_height: 120')
        self.assertContains(response, 'max_height: 450')
        self.assertNotContains(response, 'height: 250')
        self.assertContains(response, 'rows="3"')


class DisplayConditionRuleBuilderViewTests(TestCase):
    def setUp(self):
        self.group = ContentBlockGroup.objects.create(key='tsp', label='TSP', display_order=8)
        self.block = ContentBlock.objects.create(
            key='tsp.agency_match_explanation', group=self.group, label='TSP Agency Match Explanation',
        )
        self.admin = User.objects.create_user(
            username='rule_admin', password='Password123!', role='administrator',
            first_name='Admin', last_name='User',
        )

    def test_detail_page_renders_field_dropdown_and_value_registry(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('fact_finder_content:content_block_detail', args=[self.block.id]))
        self.assertContains(response, 'id="rule_field"')
        self.assertContains(response, '<option value="system.system_type">System Type</option>')
        self.assertContains(response, 'FIELD_VALUE_OPTIONS')

    def test_zero_conditions_shows_business_language_and_hides_builder_by_default(self):
        # Business decision: an empty display_condition is plain-language "always
        # included", and the System Type/FERS rule-builder must not be visible by
        # default — only revealed if the admin opts in via progressive disclosure.
        self.client.force_login(self.admin)
        response = self.client.get(reverse('fact_finder_content:content_block_detail', args=[self.block.id]))
        self.assertContains(response, 'When should this content appear in the report?')
        self.assertContains(response, 'Always include this content')
        self.assertContains(response, 'Change when this content appears')
        # The builder is present in the DOM (so it can be revealed without a page
        # reload) but collapsed — i.e. no <details open> anywhere on the page.
        self.assertContains(response, '<details>')
        self.assertNotContains(response, '<details open')
        # Empty-rule semantics are unchanged: still null/no persisted condition.
        self.block.refresh_from_db()
        self.assertIsNone(self.block.display_condition)

    def test_single_condition_shown_immediately_in_business_terms_not_raw_schema_path(self):
        self.block.display_condition = {'rules': [
            {'field': 'system.system_type', 'operator': 'equals', 'value': 'FERS'},
        ]}
        self.block.save()
        self.client.force_login(self.admin)
        response = self.client.get(reverse('fact_finder_content:content_block_detail', args=[self.block.id]))
        self.assertContains(response, 'Include this content in the report only when')
        self.assertContains(response, '<td>System Type</td>')
        self.assertContains(response, '<td>FERS</td>')
        self.assertContains(response, 'Remove condition')
        # The raw dotted schema path must not be the visible condition label.
        self.assertNotContains(response, '<td>system.system_type</td>')
        # Evaluator/stored data are unaffected by the presentation layer.
        self.block.refresh_from_db()
        self.assertEqual(
            self.block.display_condition,
            {'rules': [{'field': 'system.system_type', 'operator': 'equals', 'value': 'FERS'}]},
        )

    def test_multiple_conditions_all_displayed_with_all_must_match_language(self):
        self.block.display_condition = {'rules': [
            {'field': 'system.system_type', 'operator': 'equals', 'value': 'FERS'},
            {'field': 'system.retirement_type', 'operator': 'equals', 'value': 'Regular'},
        ]}
        self.block.save()
        self.client.force_login(self.admin)
        response = self.client.get(reverse('fact_finder_content:content_block_detail', args=[self.block.id]))
        self.assertContains(response, '<td>System Type</td>')
        self.assertContains(response, '<td>Retirement Type</td>')
        self.assertContains(response, 'All conditions must be met')
        self.assertContains(response, '+ Add another condition')
        self.block.refresh_from_db()
        self.assertEqual(len(self.block.display_condition['rules']), 2)

    def test_boolean_condition_shown_as_yes_not_python_true(self):
        self.block.display_condition = {'rules': [
            {'field': 'computed_flags.is_wep_applicable', 'operator': 'equals', 'value': True},
        ]}
        self.block.save()
        self.client.force_login(self.admin)
        response = self.client.get(reverse('fact_finder_content:content_block_detail', args=[self.block.id]))
        self.assertContains(response, '<td>WEP Applies</td>')
        self.assertContains(response, '<td>Yes</td>')

    def test_add_valid_choice_rule(self):
        self.client.force_login(self.admin)
        self.client.post(
            reverse('fact_finder_content:content_block_detail', args=[self.block.id]),
            {'action': 'add_display_rule', 'rule_field': 'system.system_type', 'rule_operator': 'equals', 'rule_value': 'FERS'},
        )
        self.block.refresh_from_db()
        self.assertEqual(
            self.block.display_condition,
            {'rules': [{'field': 'system.system_type', 'operator': 'equals', 'value': 'FERS'}]},
        )

    def test_add_boolean_rule_coerces_value(self):
        self.client.force_login(self.admin)
        self.client.post(
            reverse('fact_finder_content:content_block_detail', args=[self.block.id]),
            {'action': 'add_display_rule', 'rule_field': 'computed_flags.is_wep_applicable', 'rule_operator': 'equals', 'rule_value': 'true'},
        )
        self.block.refresh_from_db()
        self.assertIs(self.block.display_condition['rules'][0]['value'], True)

    def test_add_invalid_rule_is_rejected_with_message(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse('fact_finder_content:content_block_detail', args=[self.block.id]),
            {'action': 'add_display_rule', 'rule_field': 'system.system_type', 'rule_operator': 'equals', 'rule_value': 'NotARealSystem'},
            follow=True,
        )
        self.block.refresh_from_db()
        self.assertIsNone(self.block.display_condition)
        self.assertContains(response, 'Could not add rule')

    def test_remove_rule(self):
        self.block.display_condition = {'rules': [
            {'field': 'system.system_type', 'operator': 'equals', 'value': 'FERS'},
            {'field': 'computed_flags.is_wep_applicable', 'operator': 'equals', 'value': True},
        ]}
        self.block.save()
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse('fact_finder_content:content_block_detail', args=[self.block.id]),
            {'action': 'remove_display_rule', 'rule_index': '0'},
            follow=True,
        )
        self.block.refresh_from_db()
        self.assertEqual(len(self.block.display_condition['rules']), 1)
        self.assertEqual(self.block.display_condition['rules'][0]['field'], 'computed_flags.is_wep_applicable')
        # The remaining condition renders in business terms; the removed one is gone.
        self.assertContains(response, '<td>WEP Applies</td>')
        self.assertNotContains(response, '<td>System Type</td>')

    def test_rule_builder_requires_admin(self):
        technician = User.objects.create_user(
            username='rule_tech', password='Password123!', role='technician',
            first_name='Tech', last_name='User',
        )
        self.client.force_login(technician)
        response = self.client.post(
            reverse('fact_finder_content:content_block_detail', args=[self.block.id]),
            {'action': 'add_display_rule', 'rule_field': 'system.system_type', 'rule_operator': 'equals', 'rule_value': 'FERS'},
        )
        self.assertEqual(response.status_code, 403)
        self.block.refresh_from_db()
        self.assertIsNone(self.block.display_condition)
