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

    def test_published_source_policy_is_inherited_and_history_unchanged(self):
        before = ContentBlockVersion.objects.filter(pk=self.source.pk).values().get()
        response = self.save_draft()
        self.assertEqual(response.status_code, 302)
        draft = self.block.versions.get(status='draft')
        self.assertEqual(draft.merge_field_policy, self.policy)
        self.assertEqual(ContentBlockVersion.objects.filter(pk=self.source.pk).values().get(), before)

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
