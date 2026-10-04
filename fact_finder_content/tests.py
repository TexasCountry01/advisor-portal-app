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
        self.assertContains(response, "toolbar: 'formatselect | bold italic underline | bullist numlist | styleselect | table tableprops tabledelete | tableinsertrowbefore tableinsertrowafter tabledeleterow | tableinsertcolbefore tableinsertcolafter tabledeletecol'")
        self.assertContains(response, 'id="body_html_hidden"')
        # The textarea TinyMCE mounts on must NOT have a name attribute — only the hidden
        # input should be POSTed, per the pattern used for SystemSettings.technical_notes_template.
        self.assertNotContains(response, 'id="body_html" name="body_html"')

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
        self.assertContains(response, 'Live in PDF')
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
            {'action': 'create_draft', 'plan_year': expected_year, 'body_html': '<p>[[match_percentage]]%</p>'},
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
