"""
Tests for fact_finder_content/views.py::pdf_order_preview (Phase 2B).

These are focused tests for the new, read-only PDF-order preview screen
only. They use Django's isolated test database (created/destroyed by the
test runner) via standard ContentBlockGroup/ContentBlock/ContentBlockVersion
fixtures, the same pattern already used in fact_finder_content/tests.py and
fact_finder_content/tests_pdf_structure_map.py. No writes occur against the
developer's real local db.sqlite3, and no migrations are run here beyond the
test runner's own normal isolated-test-database setup.
"""
import re
from html.parser import HTMLParser

from django.conf import settings
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import User
from core.models import SystemSettings
from fact_finder_content import pdf_structure_map as sm
from fact_finder_content.models import ContentBlock, ContentBlockGroup, ContentBlockVersion

GROUP_LABELS = {
    "cover": "Cover",
    "pension": "Federal Pension",
    "sbp": "Survivor Benefit Plan",
    "srs_ss": "SRS & Social Security",
    "fegli": "FEGLI",
    "fehb": "FEHB",
    "fltcip": "FLTCIP",
    "tsp": "TSP",
    "irs_penalty": "IRS Early Withdrawal Penalty",
    "checklist": "Checklist",
}


class PdfOrderPreviewTests(TestCase):
    def setUp(self):
        self.groups = {}
        for order, group_key in enumerate(sm.group_keys(), start=1):
            self.groups[group_key] = ContentBlockGroup.objects.create(
                key=group_key, label=GROUP_LABELS[group_key], display_order=order,
            )

        self.blocks = {}
        for key, (section, _entry) in sm.flatten_governed_keys().items():
            self.blocks[key] = ContentBlock.objects.create(
                key=key, group=self.groups[section.group_key], label=key,
            )
        # Active-but-unwired blocks, so the "Not currently connected" area has real data.
        for group_key, unwired_keys in sm.unwired_keys_by_group().items():
            for key in unwired_keys:
                self.blocks[key] = ContentBlock.objects.create(
                    key=key, group=self.groups[group_key], label=key,
                )
        # The one known-inactive block — must never be queryable/shown by this view.
        self.inactive_block = ContentBlock.objects.create(
            key='fegli.basic_description', group=self.groups['fegli'],
            label='FEGLI Basic Coverage Description', is_active=False,
        )

        self.admin = User.objects.create_user(
            username='preview_admin', password='Password123!', role='administrator',
            first_name='Preview', last_name='Admin',
        )
        self.technician = User.objects.create_user(
            username='preview_tech', password='Password123!', role='technician',
            first_name='Preview', last_name='Tech',
        )

        self.published_key = 'tsp.eligibility'
        ContentBlockVersion.objects.create(
            block=self.blocks[self.published_key], plan_year=2026, body_html='<p>Published body.</p>',
            created_by=self.admin, status=ContentBlockVersion.STATUS_PUBLISHED,
        )
        self.draft_key = 'checklist.intro'
        ContentBlockVersion.objects.create(
            block=self.blocks[self.draft_key], plan_year=2026, body_html='<p>Draft body.</p>',
            created_by=self.admin, status=ContentBlockVersion.STATUS_DRAFT,
        )

    def _get(self, params=None):
        return self.client.get(reverse('fact_finder_content:pdf_order_preview'), params or {})

    def _row(self, response, key_or_placeholder):
        for section in response.context['sections']:
            for row in section['rows']:
                entry = row.get('entry')
                if entry and key_or_placeholder in (entry.key, entry.placeholder_id):
                    return row
        self.fail(f'No preview row found for {key_or_placeholder!r}')

    # --- Access control ---

    def test_administrator_access_returns_200(self):
        self.client.force_login(self.admin)
        response = self._get()
        self.assertEqual(response.status_code, 200)

    def test_non_administrator_access_returns_403(self):
        self.client.force_login(self.technician)
        response = self._get()
        self.assertEqual(response.status_code, 403)

    def test_anonymous_access_follows_existing_login_requirement(self):
        response = self._get()
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(settings.LOGIN_URL))

    def test_post_returns_405_without_mutation(self):
        self.client.force_login(self.admin)
        before_version_count = ContentBlockVersion.objects.count()
        before_block_count = ContentBlock.objects.count()
        response = self.client.post(reverse('fact_finder_content:pdf_order_preview'), {'system_type': 'FERS'})
        self.assertEqual(response.status_code, 405)
        self.assertEqual(ContentBlockVersion.objects.count(), before_version_count)
        self.assertEqual(ContentBlock.objects.count(), before_block_count)

    # --- Section ordering ---

    def test_all_10_sections_appear_in_pdf_order(self):
        self.client.force_login(self.admin)
        content = self._get().content.decode()
        # Each section card's collapse-target id (e.g. id="section-pension") is a unique,
        # unambiguous anchor — unlike the plain section label text, which can also appear
        # inside unrelated prose (e.g. the ungoverned-section descriptions below mention
        # "Federal Pension" and "Data Used in Preparation of This Report" by name).
        anchors = [f'id="section-{section.group_key}"' for section in sm.PDF_STRUCTURE_MAP]
        positions = [content.find(anchor) for anchor in anchors]
        self.assertTrue(all(p != -1 for p in positions), "Every one of the 10 section anchors must appear on the page")
        self.assertEqual(positions, sorted(positions), "Sections must render in PDF_STRUCTURE_MAP order")

    def test_page_heading_explanation_and_obsolete_banner(self):
        self.client.force_login(self.admin)
        content = self._get().content.decode()

        self.assertIn('<h1>Fact Finder Content — PDF Order</h1>', content)
        self.assertIn(
            'Find and manage report wording in PDF order. The inventory includes content for every scenario.',
            content,
        )
        self.assertIn('All Content', content)
        self.assertIn('Preview Scenario', content)
        self.assertIn('name="mode" value="all"', content)
        self.assertNotIn('Read-only preview.', content)
        self.assertNotIn('pdf_structure_map.py', content)
        self.assertNotIn('display_condition', content)

    def test_ungoverned_sections_appear_between_cover_and_pension(self):
        self.client.force_login(self.admin)
        content = self._get().content.decode()
        cover_pos = content.find('id="section-cover"')
        disclaimer_pos = content.find('<strong>Disclaimer &amp; Release</strong>')
        data_used_pos = content.find('<strong>Data Used in Preparation of This Report</strong>')
        pension_pos = content.find('id="section-pension"')
        self.assertTrue(cover_pos != -1 and disclaimer_pos != -1 and data_used_pos != -1 and pension_pos != -1)
        self.assertTrue(cover_pos < disclaimer_pos < pension_pos)
        self.assertTrue(cover_pos < data_used_pos < pension_pos)
        self.assertIn('Existing report content', content)
        self.assertIn(
            'The disclaimer is currently maintained separately. Administrator editing through this screen is planned.',
            content,
        )
        self.assertIn('Automatically generated', content)
        self.assertIn(
            'This section is populated automatically with employee information and calculated retirement benefits. '
            'No manual editing is required.',
            content,
        )
        self.assertNotIn('Managed outside the Fact Finder Content Editor.', content)
        self.assertNotIn('Ungoverned — not editable', content)
        for section_label, next_anchor in (
            ('Disclaimer &amp; Release', 'Data Used in Preparation of This Report'),
            ('Data Used in Preparation of This Report', 'id="section-pension"'),
        ):
            section_start = content.find(f'<strong>{section_label}</strong>')
            section_end = content.find(next_anchor, section_start + 1)
            section_html = content[section_start:section_end]
            self.assertNotIn('>Edit<', section_html)
            self.assertNotIn('content_block_detail', section_html)
        self.assertNotIn('PDF_CONTENT_ARCHITECTURE_AUDIT.md', content)
        self.assertNotIn('lines 281-420', content)

    # --- Scenario switching ---

    def test_scenario_switching_changes_srs_ss_outline(self):
        self.client.force_login(self.admin)
        fers_content = self._get({'system_type': 'FERS'}).content.decode()
        csrs_offset_content = self._get({'system_type': 'CSRS Offset'}).content.decode()
        pure_csrs_content = self._get({'system_type': 'CSRS'}).content.decode()

        self.assertIn('FERS SRS Purpose', fers_content)
        self.assertIn('FERS SRS Purpose', csrs_offset_content)
        self.assertTrue(self._row(
            self._get({'mode': 'preview', 'system_type': 'FERS'}), 'srs_ss.fers_purpose',
        )['scenario_applicability'])
        self.assertFalse(self._row(
            self._get({'mode': 'preview', 'system_type': 'CSRS Offset'}), 'srs_ss.fers_purpose',
        )['scenario_applicability'])

        for system_type, expected in (('FERS', False), ('CSRS Offset', False), ('CSRS', True)):
            response = self._get({'mode': 'preview', 'system_type': system_type})
            self.assertEqual(
                self._row(response, 'srs_ss.gpo_paragraph')['scenario_applicability'],
                expected,
            )
        for system_type, expected in (('FERS', False), ('CSRS Offset', True), ('CSRS', True)):
            response = self._get({'mode': 'preview', 'system_type': system_type})
            self.assertEqual(
                self._row(response, 'srs_ss.wep_paragraph')['scenario_applicability'],
                expected,
            )

    def test_default_all_content_keeps_b4_discoverable_and_searchable(self):
        self.client.force_login(self.admin)
        response = self._get({'system_type': 'Transfers'})
        content = response.content.decode()
        self.assertIn('B4', content)
        self.assertIn('Minimum Retirement Age (MRA) explanation', content)
        self.assertEqual(response.context['mode'], 'all')

        for query in ('mRa', 'Minimum Retirement Age', 'B4'):
            with self.subTest(query=query):
                result = self._get({'q': query, 'system_type': 'Transfers'})
                self.assertEqual(result.status_code, 200)
                self.assertIn('Minimum Retirement Age (MRA) explanation', result.content.decode())
                self.assertNotIn('No content matched', result.content.decode())

        computed = self._get({'q': 'B3'})
        self.assertContains(computed, 'Full Eligibility Requirements table')
        self.assertContains(computed, 'Automatically generated — not editable here')
        cola = self._get({'q': 'B12'})
        self.assertContains(cola, 'Cost of Living Adjustments (COLAs)')

    def test_preview_marks_mra_nonapplicable_without_hiding_it(self):
        self.client.force_login(self.admin)
        for system_type, expected in (('FERS', True), ('Transfers', False)):
            response = self._get({
                'mode': 'preview', 'system_type': system_type, 'retirement_type': 'Regular',
            })
            row = self._row(response, 'pension.mra_explanation')
            self.assertEqual(row['scenario_applicability'], expected)
            content = response.content.decode()
            self.assertIn('Minimum Retirement Age (MRA) explanation', content)
            self.assertIn(
                'Matches documented conditions' if expected else 'Does not match documented conditions',
                content,
            )

    def test_b4_rule_explanation_and_csrs_or_group_are_plain_english(self):
        self.client.force_login(self.admin)
        mra = self.blocks['pension.mra_explanation']
        response = self.client.get(reverse('fact_finder_content:content_block_detail', args=[mra.pk]))
        self.assertContains(response, 'B4')
        self.assertContains(response, 'Applies when retirement system is FERS.')

        csrs_alternative = self.blocks['pension.system_type_heading_non_fers']
        response = self.client.get(reverse(
            'fact_finder_content:content_block_detail', args=[csrs_alternative.pk],
        ))
        self.assertContains(
            response,
            'Applies when retirement system is CSRS or CSRS Offset or Transfers.',
        )

    def test_all_views_include_active_records_outside_the_structure_map(self):
        self.client.force_login(self.admin)
        ContentBlock.objects.create(
            key='local.extra_editor_content',
            group=self.groups['pension'],
            label='Additional local wording',
        )
        response = self._get()
        self.assertContains(response, 'Additional active content not in the verified PDF structure')
        self.assertContains(response, 'Additional local wording')
        self.assertContains(response, 'No verified PDF position')
        preview = self._get({'mode': 'preview', 'system_type': 'Transfers'})
        self.assertContains(preview, 'Additional local wording')
        self.assertContains(preview, 'Applicability not determined')

    def test_search_shows_an_actionable_empty_result(self):
        self.client.force_login(self.admin)
        response = self._get({'q': 'no-such-report-content'})
        self.assertContains(response, 'No content matched “no-such-report-content”.')

    def test_tsp_and_irs_variant_order_for_required_scenarios(self):
        self.client.force_login(self.admin)
        scenarios = (
            ('FERS', 'Regular', [
                'Matching Funds - at-threshold sentence',
                'Matching Funds - below-threshold explanation',
            ]),
            ('FERS', 'Deferred', [
                'Matching Funds - at-threshold sentence',
                'Matching Funds - below-threshold explanation',
            ]),
            ('CSRS', 'Regular', ['No Agency Match (CSRS)']),
            ('CSRS Offset', 'Regular', ['No Agency Match (CSRS)']),
        )
        irs_labels = [
            'Already 59.5+ / penalty-free wording',
            'Special Provision — meets age/service rules wording',
            'Special Provision — does not meet rules wording',
            'Regular employee — does not meet age 55 rule wording',
            'Regular employee — meets age 55 rule wording',
        ]

        for system_type, retirement_type, expected_tsp_labels in scenarios:
            with self.subTest(system_type=system_type, retirement_type=retirement_type):
                content = self._get({
                    'mode': 'preview',
                    'system_type': system_type,
                    'retirement_type': retirement_type,
                }).content.decode()
                tsp_start = content.find('id="section-tsp"')
                irs_start = content.find('id="section-irs_penalty"')
                checklist_start = content.find('id="section-checklist"')
                self.assertTrue(tsp_start < irs_start < checklist_start)
                tsp_section = content[tsp_start:irs_start]
                irs_section = content[irs_start:checklist_start]

                tsp_positions = [tsp_section.find(label) for label in expected_tsp_labels]
                self.assertTrue(all(position >= 0 for position in tsp_positions))
                self.assertEqual(tsp_positions, sorted(tsp_positions))
                irs_positions = [irs_section.find(label) for label in irs_labels]
                self.assertTrue(all(position >= 0 for position in irs_positions))
                self.assertEqual(irs_positions, sorted(irs_positions))

    # --- Calculated placeholders ---

    def test_calculated_placeholders_are_non_editable(self):
        self.client.force_login(self.admin)
        content = self._get().content.decode()
        self.assertIn('Per-fund current-balance/allocation/projected-ending-balance table', content)
        self.assertIn('Automatically generated — not editable here', content)
        self.assertIn("Generated automatically using the employee's report information.", content)
        for _section, entry in sm.computed_entries():
            self.assertNotIn(entry.placeholder_id, content)
            self.assertNotIn(entry.description, content)
        self.assertNotIn('Placeholder ID:', content)

    def test_sbp_calculated_variants_remain_mutually_exclusive(self):
        self.client.force_login(self.admin)
        fers = self._get({'mode': 'preview', 'system_type': 'FERS', 'retirement_type': 'Regular'})
        csrs = self._get({'mode': 'preview', 'system_type': 'CSRS', 'retirement_type': 'Regular'})
        fers_rows = [row for section in fers.context['sections'] for row in section['rows']]
        csrs_rows = [row for section in csrs.context['sections'] for row in section['rows']]
        fers_statuses = {
            row['entry'].label: row['scenario_applicability']
            for row in fers_rows if row['kind'] == 'computed'
        }
        csrs_statuses = {
            row['entry'].label: row['scenario_applicability']
            for row in csrs_rows if row['kind'] == 'computed'
        }
        self.assertTrue(any('Full (55%)' in label and status is True for label, status in fers_statuses.items()))
        self.assertTrue(any('Full (50%) / partial (25%)' in label and status is False for label, status in fers_statuses.items()))
        self.assertTrue(any('Full (50%) / partial (25%)' in label and status is True for label, status in csrs_statuses.items()))
        self.assertTrue(any('Full (55%)' in label and status is False for label, status in csrs_statuses.items()))

    # --- Unwired / inactive content ---

    def test_unwired_content_shown_separately_not_as_governed(self):
        self.client.force_login(self.admin)
        content = self._get().content.decode()
        self.assertIn('Content not currently connected to the PDF', content)
        self.assertNotIn('checklist.next_steps', content)
        self.assertNotIn('fltcip.coverage_description', content)

    def test_inactive_content_is_excluded_entirely(self):
        self.client.force_login(self.admin)
        content = self._get().content.decode()
        self.assertNotIn('fegli.basic_description', content)
        self.assertNotIn('FEGLI Basic Coverage Description', content)

    # --- Status badges (reused content_list logic) ---

    def test_published_and_draft_badges_reflect_plan_year_status(self):
        self.client.force_login(self.admin)
        content = self._get({'plan_year': '2026'}).content.decode()
        self.assertIn('Published', content)
        self.assertIn('Draft', content)

    # --- Invalid input handling ---

    def test_invalid_scenario_parameters_handled_safely(self):
        self.client.force_login(self.admin)
        response = self._get({
            'mode': 'preview', 'system_type': 'NotARealType; DROP TABLE',
            'retirement_type': 'NotARealRetirementType',
        })
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        # Falls back to the first known system type and "Any" retirement type,
        # rather than trusting/echoing the arbitrary submitted string as selected.
        self.assertIn(f'<option value="{sm.SYSTEM_TYPES[0]}" selected>', content)
        self.assertIn('<option value="" selected>', content)
        self.assertNotIn('NotARealType', content)
        self.assertNotIn('NotARealRetirementType', content)

    def test_missing_scenario_parameters_default_safely(self):
        self.client.force_login(self.admin)
        response = self._get({'mode': 'preview'})
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn(f'<option value="{sm.SYSTEM_TYPES[0]}" selected>', content)

    # --- Phase 2C-1: expandable published content ---

    def test_published_html_appears_in_expandable_panel_unescaped(self):
        self.client.force_login(self.admin)
        content = self._get({'plan_year': '2026'}).content.decode()
        # tsp.eligibility's published body (set in setUp) must render as real,
        # unescaped HTML — not as escaped entities like &lt;p&gt;.
        self.assertIn('<p>Published body.</p>', content)
        self.assertNotIn('&lt;p&gt;Published body.&lt;/p&gt;', content)

    def test_draft_html_does_not_replace_published_html(self):
        self.client.force_login(self.admin)
        ContentBlockVersion.objects.create(
            block=self.blocks[self.published_key], plan_year=2026,
            body_html='<p>DRAFT-ONLY-MARKER</p>', created_by=self.admin,
            status=ContentBlockVersion.STATUS_DRAFT,
        )
        content = self._get({'plan_year': '2026'}).content.decode()
        self.assertIn('Published body.', content)
        self.assertNotIn('DRAFT-ONLY-MARKER', content)
        # The existing "Draft" badge still reflects the draft's existence — only its
        # body_html must never be rendered as page content.
        self.assertIn('Draft', content)

    def test_missing_published_content_shows_placeholder_message(self):
        self.client.force_login(self.admin)
        content = self._get().content.decode()
        self.assertIn('No published content for this plan year.', content)

    def test_multiple_rows_have_independent_non_accordion_collapse_targets(self):
        self.client.force_login(self.admin)
        content = self._get().content.decode()
        dom_ids = re.findall(r'id="(content-[^"]+)"', content)
        self.assertGreater(len(dom_ids), 1, "Expected multiple governed content rows on the default scenario")
        self.assertEqual(len(dom_ids), len(set(dom_ids)), "All governed row collapse ids must be unique")
        # Bootstrap's accordion-style auto-closing of sibling panels is driven by a
        # data-bs-parent attribute; its absence confirms rows expand/collapse independently,
        # and that opening one can never automatically close another.
        self.assertNotIn('data-bs-parent', content)

    def test_duplicate_structural_occurrences_produce_unique_ids(self):
        """srs_ss.ss_eligibility has two real BranchPositions (FERS/Transfers and
        CSRS/CSRS Offset). Confirm that whichever branch renders for a given
        scenario still produces a page with no duplicate collapse ids."""
        self.client.force_login(self.admin)
        for system_type in ('FERS', 'CSRS Offset'):
            content = self._get({'system_type': system_type}).content.decode()
            dom_ids = re.findall(r'id="(content-[^"]+)"', content)
            self.assertEqual(len(dom_ids), len(set(dom_ids)), f"Duplicate ids found for system_type={system_type}")

    def test_html_tables_and_formatting_remain_intact_through_sanitizer(self):
        self.client.force_login(self.admin)
        rich_block = self.blocks['pension.day_of_month_to_retire']
        ContentBlockVersion.objects.create(
            block=rich_block, plan_year=2026,
            body_html=(
                '<p>Intro <strong>bold</strong> and <em>italic</em> text.</p>'
                '<ul><li>First item</li><li>Second item</li></ul>'
                '<table><tbody><tr><th>Header</th></tr><tr><td>Cell value</td></tr></tbody></table>'
            ),
            created_by=self.admin, status=ContentBlockVersion.STATUS_PUBLISHED,
        )
        content = self._get({'plan_year': '2026'}).content.decode()
        self.assertIn('<strong>bold</strong>', content)
        self.assertIn('<em>italic</em>', content)
        self.assertIn('<li>First item</li>', content)
        self.assertIn('<table>', content)
        self.assertIn('<th>Header</th>', content)
        self.assertIn('Cell value', content)

    def test_computed_placeholders_have_no_collapse_or_edit_controls(self):
        self.client.force_login(self.admin)
        content = self._get().content.decode()
        for _section, entry in sm.computed_entries():
            self.assertNotIn(entry.placeholder_id, content)

        class CalculatedRowParser(HTMLParser):
            def __init__(self):
                super().__init__()
                self.depth = 0
                self.text = []
                self.interactive = False
                self.calculated_rows = []

            def handle_starttag(self, tag, attrs):
                attributes = dict(attrs)
                if tag == 'div' and self.depth == 0:
                    classes = attributes.get('class', '').split()
                    if 'list-group-item' in classes and 'text-muted' in classes:
                        self.depth = 1
                        self.text = []
                        self.interactive = False
                elif self.depth and tag == 'div':
                    self.depth += 1
                if self.depth and (tag == 'a' or 'data-bs-toggle' in attributes):
                    self.interactive = True

            def handle_data(self, data):
                if self.depth:
                    self.text.append(data)

            def handle_endtag(self, tag):
                if self.depth and tag == 'div':
                    self.depth -= 1
                    if not self.depth:
                        row_text = ''.join(self.text)
                        if 'Automatically generated — not editable here' in row_text:
                            self.calculated_rows.append(self.interactive)

        parser = CalculatedRowParser()
        parser.feed(content)
        calculated_rows = parser.calculated_rows
        self.assertTrue(calculated_rows, "Expected rendered calculated placeholder rows")
        self.assertFalse(any(calculated_rows), "Calculated placeholder rows must not be links or expandable controls")

    def test_sanitizer_boundary_blocks_script_injection_in_preview(self):
        """Security test: content dangerous if rendered raw is sanitized at SAVE
        time (fact_finder_content/sanitize.py, unmodified by this phase) before
        it ever reaches this preview's |safe render path — confirming the
        existing sanitization boundary (not a new one introduced here) protects
        this new consumer too."""
        self.client.force_login(self.admin)
        malicious_block = self.blocks['cover.title']
        ContentBlockVersion.objects.create(
            block=malicious_block, plan_year=2026,
            body_html=(
                '<p onclick="alert(1)">Safe text</p>'
                '<script>alert("xss")</script>'
                '<img src="x" onerror="alert(1)">'
            ),
            created_by=self.admin, status=ContentBlockVersion.STATUS_PUBLISHED,
        )
        content = self._get({'plan_year': '2026'}).content.decode()
        self.assertIn('Safe text', content)
        # The page legitimately contains its own <script> tags and may contain
        # other onclick=/onerror= attributes elsewhere in base.html's chrome —
        # target the specific injected payload, not every occurrence anywhere
        # on the page, to avoid a false-positive/false-negative on unrelated
        # page chrome.
        self.assertNotIn('<script>alert', content)
        self.assertNotIn('onerror="alert', content)
        self.assertNotIn('onclick="alert', content)
        self.assertNotIn('<img src="x"', content)


class PdfOrderPreviewNavigationTests(TestCase):
    """Phase 2C-2: the canonical route now serving the PDF-ordered preview,
    the legacy route preserving the original list, and the Edit ->
    content_block_detail -> "Back to list" round trip restoring the exact
    scenario and content row."""

    def setUp(self):
        self.groups = {}
        for order, group_key in enumerate(sm.group_keys(), start=1):
            self.groups[group_key] = ContentBlockGroup.objects.create(
                key=group_key, label=GROUP_LABELS[group_key], display_order=order,
            )
        self.blocks = {}
        for key, (section, _entry) in sm.flatten_governed_keys().items():
            self.blocks[key] = ContentBlock.objects.create(
                key=key, group=self.groups[section.group_key], label=key,
            )
        self.admin = User.objects.create_user(
            username='nav_admin', password='Password123!', role='administrator',
            first_name='Nav', last_name='Admin',
        )
        self.technician = User.objects.create_user(
            username='nav_tech', password='Password123!', role='technician',
            first_name='Nav', last_name='Tech',
        )

    @staticmethod
    def _extract_back_to_list_url(detail_html):
        match = re.search(
            r'<a href="([^"]+)" class="btn btn-outline-secondary">← Back to list</a>', detail_html,
        )
        return match.group(1).replace('&amp;', '&') if match else None

    def test_canonical_url_is_the_pdf_ordered_preview(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('fact_finder_content:content_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Fact Finder Content — PDF Order')

    def test_legacy_route_still_serves_original_list_admin_only(self):
        self.client.force_login(self.technician)
        self.assertEqual(self.client.get(reverse('fact_finder_content:legacy_content_list')).status_code, 403)

        self.client.force_login(self.admin)
        response = self.client.get(reverse('fact_finder_content:legacy_content_list'))
        self.assertEqual(response.status_code, 200)
        # The legacy template is the original alphabetical list, not the new preview.
        self.assertNotContains(response, 'Fact Finder Content — PDF Order')

    def test_edit_link_round_trip_restores_scenario_and_scrolls_to_same_row(self):
        """Full round trip: open the PDF-ordered preview for a specific scenario,
        follow a governed row's Edit link, confirm it opens the real
        content_block_detail page for that exact block, then follow that page's
        "Back to list" link and confirm the canonical preview is reopened with
        the same scenario and the same row flagged to scroll to/expand."""
        self.client.force_login(self.admin)
        key = 'pension.day_of_month_to_retire'
        scenario = {'system_type': 'FERS', 'retirement_type': 'Deferred', 'plan_year': '2026'}

        preview_response = self.client.get(reverse('fact_finder_content:content_list'), scenario)
        self.assertEqual(preview_response.status_code, 200)
        content = preview_response.content.decode()

        # Locate this row's Edit link: an href to the real content_block_detail
        # route for this exact block, carrying a validated `next` back to the
        # canonical preview with the scenario + this row's stable block id.
        block_id = self.blocks[key].id
        edit_href_match = re.search(r'href="(/fact-finder-content/%d/\?next=[^"]+)"' % block_id, content)
        self.assertIsNotNone(edit_href_match, "Expected an Edit link for this block on the preview page")
        edit_url = edit_href_match.group(1).replace('&amp;', '&')

        detail_response = self.client.get(edit_url)
        self.assertEqual(detail_response.status_code, 200)
        detail_content = detail_response.content.decode()
        self.assertIn(key, detail_content)  # the real content-detail page for exactly this block loaded

        back_url = self._extract_back_to_list_url(detail_content)
        self.assertIsNotNone(back_url, "Expected a 'Back to list' link on the content-detail page")

        # It must point back at the canonical preview (not the legacy list),
        # carrying the original scenario and this row's stable block id forward.
        self.assertTrue(back_url.startswith(reverse('fact_finder_content:content_list')))
        self.assertIn('system_type=FERS', back_url)
        self.assertIn('retirement_type=Deferred', back_url)
        self.assertIn('plan_year=2026', back_url)
        self.assertIn(f'row_block_id={block_id}', back_url)

        return_response = self.client.get(back_url)
        self.assertEqual(return_response.status_code, 200)
        return_content = return_response.content.decode()
        self.assertIn('Fact Finder Content — PDF Order', return_content)
        # The specific row is flagged (server-side, via scroll_to_dom_id) to be
        # re-expanded/scrolled to — confirmed by the presence of the scroll script.
        self.assertIn('scrollIntoView', return_content)

    def test_edit_link_preserved_from_unwired_row_also_round_trips(self):
        """Unwired rows get the same scenario-preserving edit_url treatment
        (without a specific row to scroll to, since they are not part of the
        rendered PDF outline)."""
        self.client.force_login(self.admin)
        unwired_key = 'checklist.next_steps'
        unwired_block = ContentBlock.objects.create(
            key=unwired_key, group=self.groups['checklist'], label='Checklist Next Steps',
        )
        content = self.client.get(
            reverse('fact_finder_content:content_list'), {'system_type': 'CSRS'},
        ).content.decode()
        edit_href_match = re.search(r'href="(/fact-finder-content/%d/\?next=[^"]+)"' % unwired_block.id, content)
        self.assertIsNotNone(edit_href_match)
        edit_url = edit_href_match.group(1).replace('&amp;', '&')
        self.assertIn('next=', edit_url)
        detail_response = self.client.get(edit_url)
        self.assertEqual(detail_response.status_code, 200)
        back_url = self._extract_back_to_list_url(detail_response.content.decode())
        self.assertIn('system_type=CSRS', back_url)
        # No specific row/section to restore for an unwired key.
        self.assertNotIn('row=', back_url)

    def test_invalid_next_parameter_falls_back_to_canonical_list_safely(self):
        """An unsafe/external `next` value must never be trusted as a redirect
        target (open-redirect guard) — content_block_detail must fall back to
        the plain canonical list URL instead."""
        self.client.force_login(self.admin)
        key = 'cover.title'
        response = self.client.get(
            reverse('fact_finder_content:content_block_detail', args=[self.blocks[key].id]),
            {'next': 'https://evil.example.com/phish'},
        )
        self.assertEqual(response.status_code, 200)
        back_url = self._extract_back_to_list_url(response.content.decode())
        self.assertIsNotNone(back_url)
        self.assertFalse(back_url.startswith('http'), "An external 'next' must never be used as the back-to-list target")
        self.assertTrue(back_url.startswith(reverse('fact_finder_content:content_list')))

    def test_missing_or_invalid_section_row_params_handled_safely(self):
        """If the requested section/row combination doesn't exist (e.g. a stale
        link, or a key no longer present for the current scenario), the preview
        must render normally with no error and no scroll/expand behavior."""
        self.client.force_login(self.admin)
        response = self.client.get(reverse('fact_finder_content:content_list'), {
            'system_type': 'FERS', 'section': 'not_a_real_section', 'row': 'not.a.real.key',
        })
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('scrollIntoView', response.content.decode())

        # A real inventory row remains discoverable even when its documented
        # conditions do not match the selected scenario.
        response = self.client.get(reverse('fact_finder_content:content_list'), {
            'mode': 'preview', 'system_type': 'FERS',
            'section': 'srs_ss', 'row': 'srs_ss.gpo_paragraph',
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('scrollIntoView', response.content.decode())
        self.assertContains(response, 'Government Pension Offset (GPO) paragraph')
        self.assertContains(response, 'Does not match documented conditions')

    def test_non_admin_cannot_access_either_management_list(self):
        self.client.force_login(self.technician)
        self.assertEqual(self.client.get(reverse('fact_finder_content:content_list')).status_code, 403)
        self.assertEqual(self.client.get(reverse('fact_finder_content:legacy_content_list')).status_code, 403)


class PdfOrderPreviewSuperDevTests(TestCase):
    def setUp(self):
        self.settings = SystemSettings.get_settings()
        self.settings.super_dev_email = ' SuperDev@example.com '
        self.settings.save(update_fields=['super_dev_email'])

        self.super_dev = User.objects.create_user(
            username='configured_super_dev', password='Password123!',
            email='SUPERDEV@example.com', role='administrator',
        )
        self.admin = User.objects.create_user(
            username='ordinary_admin', password='Password123!',
            email='chris@example.com', role='administrator',
        )
        self.superuser = User.objects.create_user(
            username='ordinary_superuser', password='Password123!',
            email='superuser@example.com', role='administrator',
        )
        self.assertTrue(self.superuser.is_superuser)
        self.local_dev_admin = User.objects.create_user(
            username='admin', password='Password123!',
            email='local-admin@example.com', role='administrator',
        )
        cover_group = ContentBlockGroup.objects.create(
            key='cover', label='Cover', display_order=1,
        )
        self.cover_block = ContentBlock.objects.create(
            key='cover.title', group=cover_group, label='Cover Title',
        )
        srs_group = ContentBlockGroup.objects.create(
            key='srs_ss', label='SRS & Social Security', display_order=4,
        )
        self.srs_block = ContentBlock.objects.create(
            key='srs_ss.wep_paragraph', group=srs_group, label='WEP paragraph',
        )

    def _url(self):
        return reverse('fact_finder_content:content_list')

    def _set_show_identifiers(self, enabled, **params):
        data = {
            'system_type': params.get('system_type', 'FERS'),
            'retirement_type': params.get('retirement_type', ''),
            'plan_year': params.get('plan_year', '2026'),
            'section': params.get('section', ''),
            'row_block_id': params.get('row_block_id', ''),
            'mode': params.get('mode', 'preview'),
        }
        if enabled:
            data['show_technical_identifiers'] = '1'
        response = self.client.post(self._url(), data)
        self.assertEqual(response.status_code, 302)
        return response

    def test_configured_super_dev_sees_toggle(self):
        self.client.force_login(self.super_dev)
        response = self.client.get(self._url())
        self.assertContains(response, 'Show technical identifiers')
        self.assertNotContains(response, 'SuperDev@example.com')

    @override_settings(ENVIRONMENT='local')
    def test_designated_local_admin_can_use_toggle(self):
        self.client.force_login(self.local_dev_admin)
        response = self.client.get(self._url())
        self.assertContains(response, 'Show technical identifiers')

        self._set_show_identifiers(True)
        content = self.client.get(self._url()).content.decode()
        self.assertIn('Content key: <code>cover.title</code>', content)
        self.assertIn('computed:pension.full_eligibility_requirements_table', content)

    @override_settings(ENVIRONMENT='local')
    def test_other_local_administrators_do_not_qualify_automatically(self):
        self.client.force_login(self.admin)
        response = self.client.get(self._url())
        self.assertNotContains(response, 'Show technical identifiers')

        crafted = self.client.post(self._url(), {'show_technical_identifiers': '1'})
        self.assertEqual(crafted.status_code, 405)
        self.assertNotIn('cover.title', self.client.get(self._url()).content.decode())

    @override_settings(ENVIRONMENT='test')
    def test_username_admin_does_not_qualify_on_test_environment(self):
        self.client.force_login(self.local_dev_admin)
        response = self.client.get(self._url())
        self.assertNotContains(response, 'Show technical identifiers')
        self.assertNotContains(response, 'cover.title')

    @override_settings(ENVIRONMENT='production')
    def test_username_admin_does_not_qualify_on_production_environment(self):
        self.client.force_login(self.local_dev_admin)
        response = self.client.get(self._url())
        self.assertNotContains(response, 'Show technical identifiers')
        self.assertNotContains(response, 'cover.title')

    @override_settings(ENVIRONMENT=None)
    def test_username_admin_does_not_qualify_when_environment_is_unidentified(self):
        self.client.force_login(self.local_dev_admin)
        response = self.client.get(self._url())
        self.assertNotContains(response, 'Show technical identifiers')
        self.assertNotContains(response, 'cover.title')

    @override_settings(ENVIRONMENT='production')
    def test_configured_email_still_qualifies_outside_local(self):
        self.client.force_login(self.super_dev)
        response = self.client.get(self._url())
        self.assertContains(response, 'Show technical identifiers')

    def test_other_administrator_does_not_see_toggle_or_identifiers(self):
        self.client.force_login(self.admin)
        content = self.client.get(self._url()).content.decode()
        self.assertNotIn('Show technical identifiers', content)
        self.assertNotIn('cover.title', content)
        self.assertNotIn('computed:pension.full_eligibility_requirements_table', content)

    def test_django_superuser_with_different_email_is_not_eligible(self):
        self.client.force_login(self.superuser)
        response = self.client.get(self._url())
        self.assertNotContains(response, 'Show technical identifiers')
        self.assertNotContains(response, 'cover.title')

    def test_blank_or_missing_super_dev_email_disables_toggle(self):
        self.client.force_login(self.super_dev)
        self.settings.super_dev_email = ''
        self.settings.save(update_fields=['super_dev_email'])
        self.assertNotContains(self.client.get(self._url()), 'Show technical identifiers')

        self.settings.delete()
        response = self.client.get(self._url())
        self.assertNotContains(response, 'Show technical identifiers')
        self.assertNotContains(response, 'cover.title')

    def test_super_dev_default_is_off_and_hides_all_technical_identifiers(self):
        self.client.force_login(self.super_dev)
        content = self.client.get(self._url()).content.decode()
        self.assertIn('Show technical identifiers', content)
        self.assertNotIn('checked>', content)
        for key in list(sm.flatten_governed_keys()) + list(sm.all_unwired_keys()):
            self.assertNotIn(key, content)
        for _section, entry in sm.computed_entries():
            self.assertNotIn(entry.placeholder_id, content)

        restored = self.client.get(self._url(), {'section': 'cover', 'row': 'cover.title'}).content.decode()
        self.assertNotIn('cover.title', restored)
        self.assertIn(f'name="row_block_id" value="{self.cover_block.id}"', restored)

    def test_super_dev_can_show_identifiers_without_exposing_configuration_email(self):
        self.client.force_login(self.super_dev)
        response = self._set_show_identifiers(True)
        content = self.client.get(response.url).content.decode()
        self.assertIn('checked', content)
        self.assertIn('Content key: <code>cover.title</code>', content)
        self.assertIn('computed:pension.full_eligibility_requirements_table', content)
        self.assertNotIn('SuperDev@example.com', content)

    def test_super_dev_can_turn_identifiers_back_off(self):
        self.client.force_login(self.super_dev)
        self._set_show_identifiers(True)
        self.assertIn(
            'computed:pension.full_eligibility_requirements_table',
            self.client.get(self._url()).content.decode(),
        )

        self._set_show_identifiers(False)
        content = self.client.get(self._url()).content.decode()
        self.assertNotIn('cover.title', content)
        self.assertNotIn('computed:pension.full_eligibility_requirements_table', content)

    def test_request_parameters_cannot_grant_other_admins_identifier_access(self):
        self.client.force_login(self.admin)
        response = self.client.get(self._url(), {'show_technical_identifiers': '1'})
        content = response.content.decode()
        self.assertNotIn('Show technical identifiers', content)
        self.assertNotIn('cover.title', content)

        response = self.client.post(self._url(), {'show_technical_identifiers': '1'})
        self.assertEqual(response.status_code, 405)
        self.assertNotIn('fact_finder_content_show_technical_identifiers', self.client.session)
        self.assertNotIn('cover.title', self.client.get(self._url()).content.decode())

    def test_noneligible_response_excludes_governed_computed_and_unwired_keys(self):
        self.client.force_login(self.admin)
        content = self.client.get(self._url(), {'show_technical_identifiers': '1'}).content.decode()
        for identifier in (
            'cover.title',
            'srs_ss.wep_paragraph',
            'computed:pension.full_eligibility_requirements_table',
            'checklist.next_steps',
            'fltcip.coverage_description',
        ):
            self.assertNotIn(identifier, content)

    def test_toggle_preserves_scenario_and_return_to_record(self):
        self.client.force_login(self.super_dev)
        response = self._set_show_identifiers(
            True,
            system_type='CSRS Offset',
            retirement_type='Deferred',
            plan_year='2026',
            section='srs_ss',
            row_block_id=str(self.srs_block.id),
        )
        self.assertIn('system_type=CSRS+Offset', response.url)
        self.assertIn('retirement_type=Deferred', response.url)
        self.assertIn(f'row_block_id={self.srs_block.id}', response.url)
        returned = self.client.get(response.url).content.decode()
        self.assertIn('<option value="CSRS Offset" selected>', returned)
        self.assertIn('<option value="Deferred" selected>', returned)
        self.assertIn('scrollIntoView', returned)
        self.assertIn('Content key: <code>srs_ss.wep_paragraph</code>', returned)

    def test_operational_count_exclusion_policy_is_unchanged(self):
        from cases.views import _exclude_super_dev_users

        configured_user = User.objects.create_user(
            username='excluded_monitor', password='Password123!',
            email='superdev@example.com', role='technician',
        )
        regular_user = User.objects.create_user(
            username='included_technician', password='Password123!',
            email='tech@example.com', role='technician',
        )
        included_ids = set(_exclude_super_dev_users(User.objects.all()).values_list('id', flat=True))
        self.assertNotIn(configured_user.id, included_ids)
        self.assertIn(regular_user.id, included_ids)
