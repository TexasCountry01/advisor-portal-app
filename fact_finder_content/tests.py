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


class WiringStatusTests(TestCase):
    """
    Grounded in a direct scan of benefits-software/resources/views/admin/employee/
    report_pdf.blade.php on 2026-09-19 — see fact_finder_content/wiring_status.py's
    module docstring for the full rationale and maintenance burden.
    """

    def test_known_wired_block_is_wired(self):
        from fact_finder_content.wiring_status import is_wired
        self.assertTrue(is_wired('fltcip.what_is_ltc'))

    def test_never_wired_cover_title_is_not_wired(self):
        from fact_finder_content.wiring_status import is_wired
        self.assertFalse(is_wired('cover.title'))

    def test_deferred_structural_block_is_not_wired(self):
        from fact_finder_content.wiring_status import is_wired
        self.assertFalse(is_wired('pension.high3_pay_included_table'))

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

    def test_content_list_loads_for_admin(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('fact_finder_content:content_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'TSP Agency Match Explanation')

    def test_content_block_detail_requires_admin(self):
        self.client.force_login(self.technician)
        response = self.client.get(reverse('fact_finder_content:content_block_detail', args=[self.block.id]))
        self.assertEqual(response.status_code, 403)

    def test_detail_page_shows_live_badge_for_wired_block(self):
        # tsp.agency_match_explanation is a real, wired key (see wiring_status.py).
        self.client.force_login(self.admin)
        response = self.client.get(reverse('fact_finder_content:content_block_detail', args=[self.block.id]))
        self.assertContains(response, 'Live in PDF')
        self.assertNotContains(response, 'Not yet connected to PDF')

    def test_detail_page_shows_not_connected_badge_for_unwired_block(self):
        unwired_block = ContentBlock.objects.create(
            key='cover.title', group=self.group, label='Cover Page Title',
        )
        self.client.force_login(self.admin)
        response = self.client.get(reverse('fact_finder_content:content_block_detail', args=[unwired_block.id]))
        self.assertContains(response, 'Not yet connected to PDF')
        self.assertContains(response, 'no effect')

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

    def test_create_draft_via_post_sanitizes_html(self):
        self.client.force_login(self.admin)
        self.client.post(
            reverse('fact_finder_content:content_block_detail', args=[self.block.id]),
            {'action': 'create_draft', 'plan_year': 2026, 'body_html': '<p onclick="alert(1)">[[match_percentage]]</p><script>alert(2)</script>'},
        )
        version = ContentBlockVersion.objects.get(block=self.block, plan_year=2026)
        self.assertNotIn('onclick', version.body_html)
        self.assertNotIn('<script', version.body_html)
        self.assertIn('[[match_percentage]]', version.body_html)

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
        self.assertContains(response, "toolbar: 'formatselect | bold italic underline | bullist numlist'")
        self.assertContains(response, 'id="body_html_hidden"')
        # The textarea TinyMCE mounts on must NOT have a name attribute — only the hidden
        # input should be POSTed, per the pattern used for SystemSettings.technical_notes_template.
        self.assertNotContains(response, 'id="body_html" name="body_html"')

    def test_detail_page_shows_golden_master_gate_matching_all_24_when_no_rules(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('fact_finder_content:content_block_detail', args=[self.block.id]))
        self.assertContains(response, 'Test Against Sample Cases')
        self.assertContains(response, 'Will appear for 24 of 24 sample cases')

    def test_detail_page_golden_master_gate_reflects_display_condition(self):
        self.block.display_condition = {'rules': [
            {'field': 'computed_flags.is_wep_applicable', 'operator': 'equals', 'value': True},
        ]}
        self.block.save()
        self.client.force_login(self.admin)
        response = self.client.get(reverse('fact_finder_content:content_block_detail', args=[self.block.id]))
        # Grounded in the same real-data fact verified in fact_finder_content/tests_golden_master.py:
        # exactly 3 of the 24 golden-master cases have is_wep_applicable == True.
        self.assertContains(response, 'Will appear for 3 of 24 sample cases')


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
        self.client.post(
            reverse('fact_finder_content:content_block_detail', args=[self.block.id]),
            {'action': 'remove_display_rule', 'rule_index': '0'},
        )
        self.block.refresh_from_db()
        self.assertEqual(len(self.block.display_condition['rules']), 1)
        self.assertEqual(self.block.display_condition['rules'][0]['field'], 'computed_flags.is_wep_applicable')

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
