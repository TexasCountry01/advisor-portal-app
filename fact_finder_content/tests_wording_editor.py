from copy import deepcopy
from urllib.parse import parse_qs, urlsplit

from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from .models import ContentBlock, ContentBlockGroup, ContentBlockVersion


class WordingEditorSafetyTests(TestCase):
    def setUp(self):
        group = ContentBlockGroup.objects.create(key='pension', label='Pension')
        self.block = ContentBlock.objects.create(
            key='pension.wording_safety', label='Wording safety', group=group,
            required_placeholders=['pension.cola'],
        )
        self.user = User.objects.create_user(username='wording_editor', role='administrator')
        self.client.force_login(self.user)
        self.url = reverse('fact_finder_content:content_block_detail', args=[self.block.pk])
        self.policy = {
            'schema_version': 1,
            'tokens': [{
                'token': 'pension.cola', 'value_type': 'string', 'format': 'plain',
                'presence': 'required', 'null': 'error', 'blank': 'error', 'omission': None,
            }],
        }
        self.source = ContentBlockVersion.objects.create(
            block=self.block, plan_year=2026, body_html='<p>COLA [[pension.cola]]</p>',
            merge_field_policy=self.policy, status=ContentBlockVersion.STATUS_PUBLISHED,
        )

    def save_draft(self, **changes):
        payload = {
            'action': 'create_draft', 'plan_year': 2026,
            'body_html': '<p>Updated COLA [[pension.cola]]</p>',
            'source_version_id': self.source.pk, 'editor_ready': 'ready',
        }
        payload.update(changes)
        return self.client.post(self.url, payload)

    def save_and_publish(self, **changes):
        payload = {
            'action': 'save_and_publish', 'plan_year': 2026,
            'body_html': '<p>Published COLA [[pension.cola]]</p>',
            'source_version_id': self.source.pk, 'editor_ready': 'ready',
        }
        payload.update(changes)
        return self.client.post(self.url, payload)

    def test_published_source_policy_is_inherited_and_history_unchanged(self):
        before = ContentBlockVersion.objects.filter(pk=self.source.pk).values().get()
        response = self.save_draft()
        self.assertEqual(response.status_code, 302)
        draft = self.block.versions.get(status='draft')
        self.assertEqual(draft.merge_field_policy, self.policy)
        self.assertEqual(ContentBlockVersion.objects.filter(pk=self.source.pk).values().get(), before)

    def test_save_and_publish_inherits_strict_merge_policy_and_preserves_source(self):
        response = self.save_and_publish(
            body_html='<p>New report wording [[pension.cola]]</p>',
        )
        self.assertEqual(response.status_code, 302)
        self.source.refresh_from_db()
        published = self.block.versions.get(status=ContentBlockVersion.STATUS_PUBLISHED)
        self.assertEqual(published.merge_field_policy, self.policy)
        self.assertEqual(published.body_html, '<p>New report wording [[pension.cola]]</p>')
        self.assertEqual(self.source.status, ContentBlockVersion.STATUS_SUPERSEDED)
        self.assertEqual(self.source.body_html, '<p>COLA [[pension.cola]]</p>')

    def test_save_and_publish_rejects_invalid_inherited_merge_policy_without_writes(self):
        self.source.merge_field_policy = {'schema_version': 99, 'tokens': []}
        self.source.save()
        response = self.save_and_publish()
        self.assertContains(response, 'configured report fields')
        self.source.refresh_from_db()
        self.assertEqual(self.source.status, ContentBlockVersion.STATUS_PUBLISHED)
        self.assertEqual(self.block.versions.count(), 1)

    def test_editing_table_content_preserves_table_structure_and_merge_token(self):
        table = (
            '<table><tbody><tr><td>Current adjustment</td>'
            '<td>[[pension.cola]]%</td></tr></tbody></table>'
        )
        response = self.save_draft(body_html=table)
        self.assertEqual(response.status_code, 302)
        draft = self.block.versions.get(status=ContentBlockVersion.STATUS_DRAFT)
        self.assertIn('<table>', draft.body_html)
        self.assertIn('<td>Current adjustment</td>', draft.body_html)
        self.assertIn('[[pension.cola]]', draft.body_html)

    def test_omitted_blank_null_and_crafted_policy_are_ignored(self):
        for supplied in ('', 'null', '{"schema_version":99}', '{invalid json'):
            with self.subTest(supplied=supplied):
                response = self.save_draft(merge_field_policy=supplied)
                self.assertEqual(response.status_code, 302)
                self.assertEqual(self.block.versions.latest('id').merge_field_policy, self.policy)

    def test_existing_draft_preserves_policy_without_source_or_policy(self):
        self.save_draft()
        draft = self.block.versions.get(status='draft')
        response = self.save_draft(version_id=draft.pk, source_version_id='')
        self.assertEqual(response.status_code, 302)
        draft.refresh_from_db()
        self.assertEqual(draft.merge_field_policy, self.policy)
        self.assertEqual(self.block.versions.count(), 2)

    def test_existing_draft_ignores_policy_reset_and_replacement(self):
        self.save_draft()
        draft = self.block.versions.get(status='draft')
        for supplied in ('', 'null', '{"tokens": []}'):
            response = self.save_draft(
                version_id=draft.pk, source_version_id=draft.pk,
                merge_field_policy=supplied,
            )
            self.assertEqual(response.status_code, 302)
            draft.refresh_from_db()
            self.assertEqual(draft.merge_field_policy, self.policy)

    def test_legacy_null_source_remains_null(self):
        self.source.merge_field_policy = None
        self.source.save()
        self.save_draft(merge_field_policy='{"schema_version":1,"tokens":[]}')
        self.assertIsNone(self.block.versions.get(status='draft').merge_field_policy)

    def test_source_must_belong_to_block(self):
        other = ContentBlock.objects.create(key='other', label='Other', group=self.block.group)
        self.source.block = other
        self.source.save()
        response = self.save_draft()
        self.assertContains(response, 'source wording must belong to this content and plan year')
        self.assertFalse(self.block.versions.exists())

    def test_source_must_belong_to_year(self):
        response = self.save_draft(plan_year=2025)
        self.assertContains(response, 'Cross-year copying is not available')
        self.assertEqual(self.block.versions.count(), 1)

    def test_missing_source_cannot_bypass_policy(self):
        response = self.save_draft(source_version_id='')
        self.assertContains(response, 'Load a source version')
        self.assertEqual(self.block.versions.count(), 1)

    def test_unknown_and_malformed_version_identifiers_do_not_write(self):
        for changes in (
            {'source_version_id': 999999},
            {'source_version_id': 'bad'},
            {'version_id': 999999},
            {'version_id': 'bad'},
            {'plan_year': 'bad'},
            {'plan_year': 0},
        ):
            with self.subTest(changes=changes):
                response = self.save_draft(**changes)
                self.assertContains(response, 'Draft not saved')
                self.assertEqual(self.block.versions.count(), 1)

    def test_selected_year_is_loaded_without_cross_year_fallback(self):
        response = self.client.get(self.url, {'plan_year': 2025})
        form = response.context['draft_form']
        self.assertEqual(form['plan_year'].value(), 2025)
        self.assertEqual(form['body_html'].value(), '')
        self.assertEqual(form['source_version_id'].value(), '')

    def test_matching_year_loads_published_source(self):
        response = self.client.get(self.url, {'plan_year': 2026})
        self.assertEqual(response.context['draft_form']['source_version_id'].value(), self.source.pk)
        self.assertEqual(response.context['draft_form']['body_html'].value(), self.source.body_html)

    def test_historical_draft_load_and_save_keep_actual_year(self):
        draft = ContentBlockVersion.objects.create(
            block=self.block, plan_year=2025, body_html='<p>Old [[pension.cola]]</p>',
            merge_field_policy=self.policy,
        )
        response = self.client.get(self.url, {'plan_year': 2025})
        form = response.context['draft_form']
        self.assertEqual(form['version_id'].value(), draft.pk)
        self.assertEqual(form['plan_year'].value(), 2025)
        self.assertContains(response, f'data-plan-year="2025"')
        response = self.save_draft(
            version_id=draft.pk, source_version_id=draft.pk, plan_year=2025,
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn('plan_year=2025', response.url)
        draft.refresh_from_db()
        self.assertEqual(draft.plan_year, 2025)
        self.assertEqual(draft.merge_field_policy, self.policy)
        self.source.refresh_from_db()
        self.assertEqual(self.source.status, 'published')

    def test_mismatched_draft_year_or_source_is_rejected(self):
        self.save_draft()
        draft = self.block.versions.get(status='draft')
        before = deepcopy(draft.body_html)
        for changes in (
            {'version_id': draft.pk, 'source_version_id': draft.pk, 'plan_year': 2025},
            {'version_id': draft.pk, 'source_version_id': self.source.pk},
            {'version_id': self.source.pk},
        ):
            response = self.save_draft(**changes)
            self.assertContains(response, 'Draft not saved')
            draft.refresh_from_db()
            self.assertEqual(draft.body_html, before)

    def test_invalid_wording_retains_attempt_and_does_not_save(self):
        attempted = '<p>Attempted wording without its field</p>'
        response = self.save_draft(body_html=attempted)
        self.assertContains(response, 'Draft not saved')
        self.assertEqual(response.context['draft_form']['body_html'].value(), attempted)
        self.assertContains(response, '&lt;p&gt;Attempted wording')
        self.assertNotContains(response, 'schema_version')
        self.assertEqual(self.block.versions.count(), 1)

    def test_failed_update_leaves_stored_draft_and_published_source_intact(self):
        self.save_draft()
        draft = self.block.versions.get(status='draft')
        before = list(self.block.versions.order_by('id').values())
        response = self.save_draft(
            version_id=draft.pk, source_version_id=draft.pk, body_html='<p>Missing field</p>',
        )
        self.assertContains(response, 'Draft not saved')
        self.assertEqual(list(self.block.versions.order_by('id').values()), before)

    def test_unready_missing_and_empty_wording_do_not_write(self):
        for changes in (
            {'editor_ready': ''}, {'editor_ready': 'unsynchronized'},
            {'body_html': ''}, {'body_html': '   '}, {'body_html': '<p>&nbsp;<br></p>'},
        ):
            response = self.save_draft(**changes)
            self.assertContains(response, 'Draft not saved')
            self.assertEqual(self.block.versions.count(), 1)
        payload = {'action': 'create_draft', 'plan_year': 2026, 'source_version_id': self.source.pk}
        self.assertContains(self.client.post(self.url, payload), 'Draft not saved')

    def test_review_and_publish_still_reject_invalid_strict_configuration(self):
        self.save_draft()
        draft = self.block.versions.get(status='draft')
        draft.body_html = '<p>Missing required field</p>'
        draft.save()
        for action, status in (('submit_for_review', 'draft'), ('publish', 'in_review')):
            draft.status = status
            draft.save()
            response = self.client.post(self.url, {'action': action, 'version_id': draft.pk}, follow=True)
            self.assertContains(response, 'Cannot')
            draft.refresh_from_db()
            self.assertEqual(draft.status, status)
        self.source.refresh_from_db()
        self.assertEqual(self.source.status, 'published')

    def test_raw_policy_is_not_in_interface_or_history_attributes(self):
        response = self.client.get(self.url)
        for text in ('Merge-field policy JSON', 'data-merge-field-policy', 'schema_version', 'Legacy / no policy'):
            self.assertNotContains(response, text)

    def test_editor_groups_business_guidance_history_and_placeholders(self):
        response = self.client.get(self.url)
        self.assertContains(response, 'Content &amp; Wording')
        self.assertContains(response, 'When should this wording appear?')
        self.assertContains(response, 'Version History')
        self.assertContains(response, 'Currently Published')
        self.assertContains(response, 'Required Employee Information')
        self.assertContains(response, 'Cost-of-Living Adjustment')
        self.assertContains(response, 'automatically when a report is generated')
        self.assertContains(response, '[[pension.cola]]')
        self.assertNotContains(response, 'Required placeholders:')
        self.assertContains(response, 'Changes to these conditions take effect immediately')

    def test_plain_english_rule_summary_preserves_and_grouping(self):
        self.block.display_condition = {'rules': [
            {'field': 'system.system_type', 'operator': 'equals', 'value': 'FERS'},
            {'field': 'system.retirement_type', 'operator': 'equals', 'value': 'Regular'},
        ]}
        self.block.save()
        response = self.client.get(self.url)
        self.assertContains(response, 'System Type is FERS')
        self.assertContains(response, 'Retirement Type is Regular')
        self.assertContains(response, 'Additional report conditions (read-only)')

    def test_unsupported_rule_data_is_not_misrepresented_as_unconditional(self):
        self.block.display_condition = {'expression': 'unknown legacy shape'}
        self.block.save()
        response = self.client.get(self.url)
        self.assertContains(response, 'This wording has a more complex condition')
        self.assertNotContains(response, 'No additional Advisor Portal condition is set.</strong>')
        self.assertNotContains(response, 'name="action" value="remove_display_rule"')

    def test_version_history_keeps_each_workflow_status_visible(self):
        for status in (
            ContentBlockVersion.STATUS_DRAFT,
            ContentBlockVersion.STATUS_IN_REVIEW,
            ContentBlockVersion.STATUS_SUPERSEDED,
        ):
            ContentBlockVersion.objects.create(
                block=self.block, plan_year=2026,
                body_html='<p>History [[pension.cola]]</p>',
                merge_field_policy=self.policy, status=status,
            )
        response = self.client.get(self.url)
        for status_label in ('Currently Published', 'Draft', 'In Review', 'Superseded'):
            self.assertContains(response, status_label)
        self.assertContains(response, 'remains active until another version is published')

    def test_non_admin_cannot_open_editor_or_publish_through_post_handler(self):
        candidate = ContentBlockVersion.objects.create(
            block=self.block, plan_year=2026,
            body_html='<p>Reviewed [[pension.cola]]</p>',
            merge_field_policy=self.policy,
            status=ContentBlockVersion.STATUS_IN_REVIEW,
        )
        technician = User.objects.create_user(username='wording_technician', role='technician')
        self.client.force_login(technician)
        self.assertEqual(self.client.get(self.url).status_code, 403)
        response = self.client.post(self.url, {
            'action': 'publish', 'version_id': candidate.pk,
        })
        self.assertEqual(response.status_code, 403)
        candidate.refresh_from_db()
        self.source.refresh_from_db()
        self.assertEqual(candidate.status, ContentBlockVersion.STATUS_IN_REVIEW)
        self.assertEqual(self.source.status, ContentBlockVersion.STATUS_PUBLISHED)

    def test_invalid_query_year_is_actionable(self):
        response = self.client.get(self.url, {'plan_year': 'bad'})
        self.assertContains(response, 'Choose a valid plan year', status_code=400)
        self.assertNotContains(response, 'tinymce.init', status_code=400)

    def test_preview_and_legacy_edit_links_carry_year(self):
        from .views import _edit_url_for
        query = parse_qs(urlsplit(_edit_url_for(self.block.pk, 'FERS', None, 2025)).query)
        self.assertEqual(query['plan_year'], ['2025'])
        response = self.client.get(reverse('fact_finder_content:legacy_content_list'), {'plan_year': 2025})
        self.assertContains(response, self.url + '?plan_year=2025')
