"""
Tests for migration 0002 (`fact_finder_content/migrations/
0002_fix_governed_content_spacing_regressions.py`), which corrects 6
governed-content blocks per benefits-software/PDF_REGRESSION_FINDINGS_2026-09-27.md's
Addendum section 12 ("Four Residual Governed-Content Defects — Experimentally
Proven").

Two kinds of coverage, per the explicit requirement:
  1. Exact-output tests for each fix function, using realistic input shaped
     exactly like the real stored (buggy) body_html for that key, asserting
     the corrected output matches precisely what the experimentally-proven
     fix requires.
  2. Sanitizer-idempotency tests proving each corrected string survives a
     real `sanitize_body_html()` round trip unchanged -- the actual
     durability guarantee against a future WYSIWYG re-save re-breaking this.
Plus one end-to-end integration test exercising the real apply_corrections()/
revert_corrections() functions against real ContentBlock/ContentBlockVersion
rows, confirming the create-new-version-and-publish (never mutate history)
lifecycle.
"""
import importlib

from django.test import TestCase

from fact_finder_content.models import ContentBlock, ContentBlockGroup, ContentBlockVersion
from fact_finder_content.sanitize import sanitize_body_html

_migration_module = importlib.import_module(
    'fact_finder_content.migrations.0002_fix_governed_content_spacing_regressions'
)


class High3PayIncludedTableFixTests(TestCase):
    def test_3_nbsp_becomes_5_nbsp(self):
        buggy = (
            '<table cellpadding="5" style="font-family:Arial, sans-serif; font-size:9.5px;">'
            '<tbody><tr><th style="width: 5%;"></th>'
            '<th style="width: 55%; font-family:Arial, sans-serif;">'
            '<span style="font-weight: bold;">Pay included in the high-3:</span><br>'
            '&nbsp;&nbsp;&nbsp; Regular pay<br>'
            '&nbsp;&nbsp;&nbsp; Locality pay<br>'
            '&nbsp;&nbsp;&nbsp; Night differential pay (for Wage Grade only)</th>'
            '<th style="width: 40%; font-family:Arial, sans-serif;">'
            '<span style="font-weight: bold;">Pay NOT included:</span><br>'
            '&nbsp;&nbsp;&nbsp; Retention pay<br>'
            '&nbsp;&nbsp;&nbsp; Relocation allowances<br></th></tr></tbody></table>'
        )
        expected = (
            '<table cellpadding="5" style="font-family:Arial, sans-serif; font-size:9.5px;">'
            '<tbody><tr><th style="width: 5%;"></th>'
            '<th style="width: 55%; font-family:Arial, sans-serif;">'
            '<span style="font-weight: bold;">Pay included in the high-3:</span><br>'
            '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; Regular pay<br>'
            '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; Locality pay<br>'
            '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; Night differential pay (for Wage Grade only)</th>'
            '<th style="width: 40%; font-family:Arial, sans-serif;">'
            '<span style="font-weight: bold;">Pay NOT included:</span><br>'
            '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; Retention pay<br>'
            '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; Relocation allowances<br></th></tr></tbody></table>'
        )
        self.assertEqual(_migration_module._high3_pay_included_table_fix(buggy), expected)

    def test_already_correct_5_nbsp_form_is_unchanged(self):
        # Function-level reapplication safety: feeding the fix function its
        # OWN already-corrected output must not add more &nbsp;.
        already_fixed = (
            '<span style="font-weight: bold;">Pay included in the high-3:</span><br>'
            '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; Regular pay<br>'
            '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; Locality pay<br>'
        )
        result = _migration_module._high3_pay_included_table_fix(already_fixed)
        self.assertEqual(result, already_fixed)

    def test_fix_fix_original_equals_fix_original_and_never_produces_7(self):
        original = (
            '<span style="font-weight: bold;">Pay included in the high-3:</span><br>'
            '&nbsp;&nbsp;&nbsp; Regular pay<br>'
            '&nbsp;&nbsp;&nbsp; Locality pay<br>'
        )
        once = _migration_module._high3_pay_included_table_fix(original)
        twice = _migration_module._high3_pay_included_table_fix(once)

        self.assertEqual(once, twice, 'fix(fix(original)) must equal fix(original)')
        for nbsp_run in ('&nbsp;' * 7, '&nbsp;' * 6):
            self.assertNotIn(nbsp_run, once)
            self.assertNotIn(nbsp_run, twice)
        self.assertEqual(once.count('&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; '), 2)
        self.assertEqual(twice.count('&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; '), 2)

    def test_idempotent_through_sanitize_body_html(self):
        fixed = (
            '<table cellpadding="5" style="font-family:Arial, sans-serif; font-size:9.5px;">'
            '<tbody><tr><th style="width: 5%;"></th>'
            '<th style="width: 55%; font-family:Arial, sans-serif;">'
            '<span style="font-weight: bold;">Pay included in the high-3:</span><br>'
            '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; Regular pay<br></th></tr></tbody></table>'
        )
        self.assertEqual(sanitize_body_html(fixed), fixed)
        # second round trip (simulated future re-save) must also be a no-op
        self.assertEqual(sanitize_body_html(sanitize_body_html(fixed)), fixed)


class FegliCoverageAvailableFixTests(TestCase):
    def test_trailing_br_restored_on_last_cell_only(self):
        buggy = (
            '<table cellpadding="3" style="font-family:Arial, sans-serif; font-size:9px;">'
            '<thead><tr><th style="border-bottom: 1px solid #ddd;" width="20%">Coverage</th>'
            '<th style="border-bottom: 1px solid #ddd;" width="80%">Description</th></tr></thead>'
            '<tbody><tr><td width="20%">Basic: </td>'
            '<td width="80%">Salary rounded up to the nearest $1,000 &amp; add $2,000</td></tr>'
            '<tr><td width="20%">Option C (1-5 multiples): </td>'
            '<td width="80%">Spouse base of $5,000 (Children base of $2,500) &amp; multiply '
            'by the # of multiples selected (1-5)</td></tr></tbody></table>'
        )
        expected = buggy.replace(
            'multiply by the # of multiples selected (1-5)</td>',
            'multiply by the # of multiples selected (1-5)<br></td>',
        )
        self.assertEqual(_migration_module._fegli_coverage_available_fix(buggy), expected)
        self.assertIn('(1-5)<br></td></tr></tbody></table>', _migration_module._fegli_coverage_available_fix(buggy))

    def test_other_cells_unaffected(self):
        buggy = (
            '<table><tbody><tr><td width="20%">Basic: </td>'
            '<td width="80%">Salary rounded up to the nearest $1,000 &amp; add $2,000</td></tr>'
            '<tr><td width="20%">Option C (1-5 multiples): </td>'
            '<td width="80%">Spouse base of $5,000 (Children base of $2,500) &amp; multiply '
            'by the # of multiples selected (1-5)</td></tr></tbody></table>'
        )
        fixed = _migration_module._fegli_coverage_available_fix(buggy)
        self.assertIn('add $2,000</td></tr>', fixed)  # unrelated cell untouched

    def test_idempotent_through_sanitize_body_html(self):
        fixed = (
            '<table cellpadding="3" style="font-family:Arial, sans-serif; font-size:9px;">'
            '<thead><tr><th style="border-bottom: 1px solid #ddd;" width="20%">Coverage</th>'
            '<th style="border-bottom: 1px solid #ddd;" width="80%">Description</th></tr></thead>'
            '<tbody><tr><td width="20%">Option C (1-5 multiples): </td>'
            '<td width="80%">Spouse base of $5,000 (Children base of $2,500) &amp; multiply '
            'by the # of multiples selected (1-5)<br></td></tr></tbody></table>'
        )
        self.assertEqual(sanitize_body_html(fixed), fixed)
        self.assertEqual(sanitize_body_html(sanitize_body_html(fixed)), fixed)


class FltcipCoverageAvailableIntroFixTests(TestCase):
    def test_line_height_restored_on_heading_span_only(self):
        buggy = (
            '<table cellpadding="3" style="font-family:Arial, sans-serif; font-size:9px;">'
            '<tbody><tr><td><span style="font-size: 11px; font-weight: bold;">Coverage available</span>'
            '<br><span style="font-family:Arial, sans-serif; font-size: 10px;">The Federal Long Term '
            'Care Insurance Program offers various features to its participants:</span></td></tr>'
            '</tbody></table>'
        )
        fixed = _migration_module._fltcip_coverage_available_intro_fix(buggy)
        self.assertIn(
            '<span style="font-size: 11px; line-height: 11px; font-weight: bold;">Coverage available</span>',
            fixed,
        )
        # the second span (font-size: 10px, no line-height originally) must be untouched
        self.assertIn(
            '<span style="font-family:Arial, sans-serif; font-size: 10px;">The Federal Long Term',
            fixed,
        )

    def test_idempotent_through_sanitize_body_html(self):
        fixed = (
            '<table cellpadding="3" style="font-family:Arial, sans-serif; font-size:9px;">'
            '<tbody><tr><td><span style="font-size: 11px; line-height: 11px; font-weight: bold;">'
            'Coverage available</span><br><span style="font-family:Arial, sans-serif; font-size: 10px;">'
            'The Federal Long Term Care Insurance Program offers various features to its participants:'
            '</span></td></tr></tbody></table>'
        )
        self.assertEqual(sanitize_body_html(fixed), fixed)
        self.assertEqual(sanitize_body_html(sanitize_body_html(fixed)), fixed)


class ChecklistTopicListFixTests(TestCase):
    def test_nbsp_prefix_added_to_every_top_level_li_only(self):
        buggy = (
            '<ul style="font-family:Arial, sans-serif; font-size: 10px; color: #2e2e2e; '
            'font-weight: bold; padding-left: 18px; list-style-type:img|svg|3|3|images/rectangle.svg;">'
            '<li style="font-family:Arial, sans-serif; font-size: 11px; line-height: 20px; '
            'color: #285FBF;">Pension (FERS)'
            '<ul style="font-family:Arial, sans-serif; list-style-type:img|svg|3|3|images/circle.svg; '
            'font-size: 10px; color: #2e2e2e; font-weight: normal; padding-left: 18px;">'
            '<li style="font-family:Arial, sans-serif; line-height: 17px;">'
            '<em>What is the best date for me to retire from federal service?</em></li></ul></li>'
            '<li style="font-family:Arial, sans-serif; font-size: 11px; line-height: 20px; '
            'color: #285FBF;">Survivor Benefit Plan (SBP)'
            '<ul style="font-family:Arial, sans-serif; list-style-type:img|svg|3|3|images/circle.svg; '
            'font-size: 10px; color: #2e2e2e; font-weight: normal; padding-left: 18px;">'
            '<li style="font-family:Arial, sans-serif; line-height: 17px;">'
            '<em>How do I secure enough survivor benefit?</em></li></ul></li></ul>'
        )
        fixed = _migration_module._checklist_topic_list_fix(buggy)

        # both top-level headings get the prefix
        self.assertIn('color: #285FBF;">&nbsp;&nbsp;Pension (FERS)', fixed)
        self.assertIn('color: #285FBF;">&nbsp;&nbsp;Survivor Benefit Plan (SBP)', fixed)
        self.assertEqual(fixed.count('color: #285FBF;">&nbsp;&nbsp;'), 2)

        # nested sub-item <li> question text (no #285FBF in its style) is untouched
        self.assertIn(
            '<li style="font-family:Arial, sans-serif; line-height: 17px;">'
            '<em>What is the best date for me to retire from federal service?</em></li>',
            fixed,
        )
        self.assertNotIn('&nbsp;&nbsp;<em>', fixed)

    def test_already_correct_2_nbsp_headings_are_unchanged(self):
        # Function-level reapplication safety: feeding the fix function its
        # OWN already-corrected output must not add more &nbsp;.
        already_fixed = (
            '<li style="font-family:Arial, sans-serif; font-size: 11px; line-height: 20px; '
            'color: #285FBF;">&nbsp;&nbsp;Pension (FERS)'
            '<ul style="font-family:Arial, sans-serif; list-style-type:img|svg|3|3/images/circle.svg;">'
            '<li style="font-family:Arial, sans-serif; line-height: 17px;">'
            '<em>What is the best date for me to retire from federal service?</em></li></ul></li>'
        )
        result = _migration_module._checklist_topic_list_fix(already_fixed)
        self.assertEqual(result, already_fixed)

    def test_fix_fix_original_equals_fix_original_and_never_produces_4(self):
        original = (
            '<li style="font-family:Arial, sans-serif; font-size: 11px; line-height: 20px; '
            'color: #285FBF;">Pension (FERS)'
            '<ul style="font-family:Arial, sans-serif; list-style-type:img|svg|3|3/images/circle.svg;">'
            '<li style="font-family:Arial, sans-serif; line-height: 17px;">'
            '<em>What is the best date for me to retire from federal service?</em></li></ul></li>'
        )
        once = _migration_module._checklist_topic_list_fix(original)
        twice = _migration_module._checklist_topic_list_fix(once)

        self.assertEqual(once, twice, 'fix(fix(original)) must equal fix(original)')
        self.assertNotIn('&nbsp;&nbsp;&nbsp;&nbsp;', once)
        self.assertNotIn('&nbsp;&nbsp;&nbsp;&nbsp;', twice)
        self.assertEqual(once.count('color: #285FBF;">&nbsp;&nbsp;'), 1)
        self.assertEqual(twice.count('color: #285FBF;">&nbsp;&nbsp;'), 1)

        # nested <li> markup must remain byte-identical throughout
        nested_li = (
            '<li style="font-family:Arial, sans-serif; line-height: 17px;">'
            '<em>What is the best date for me to retire from federal service?</em></li>'
        )
        self.assertIn(nested_li, once)
        self.assertIn(nested_li, twice)


    def test_idempotent_through_sanitize_body_html(self):
        fixed = (
            '<ul style="font-family:Arial, sans-serif; font-size: 10px; color: #2e2e2e; '
            'font-weight: bold; padding-left: 18px; list-style-type:img|svg|3|3|images/rectangle.svg;">'
            '<li style="font-family:Arial, sans-serif; font-size: 11px; line-height: 20px; '
            'color: #285FBF;">&nbsp;&nbsp;Pension (FERS)'
            '<ul style="font-family:Arial, sans-serif; list-style-type:img|svg|3|3|images/circle.svg; '
            'font-size: 10px; color: #2e2e2e; font-weight: normal; padding-left: 18px;">'
            '<li style="font-family:Arial, sans-serif; line-height: 17px;">'
            '<em>What is the best date for me to retire from federal service?</em></li></ul></li></ul>'
        )
        self.assertEqual(sanitize_body_html(fixed), fixed)
        self.assertEqual(sanitize_body_html(sanitize_body_html(fixed)), fixed)

    def test_applies_identically_to_srs_topic_sibling_block(self):
        # checklist.srs_topic (1 top-level item) shares the exact same
        # generic fix function as checklist.topics_before_srs -- confirmed
        # by construction (same CORRECTIONS mapping entry), spot-checked
        # here with a realistic fragment. checklist.topics_after_srs does
        # NOT share this generic-only behavior -- see
        # ChecklistTopicsAfterSrsFixTests below for its block-specific
        # exceptions (FEHB heading, TSP's 3rd nested item).
        srs_topic = (
            '<ul style="...color: #285FBF;">Social Security and the FERS Special Retirement '
            'Supplement<ul>...</ul></li></ul>'
        )
        self.assertEqual(
            _migration_module._checklist_topic_list_fix(srs_topic).count('&nbsp;&nbsp;'), 1
        )


class ChecklistTopicsAfterSrsFixTests(TestCase):
    """Tests for `_checklist_topics_after_srs_fix()` -- the
    checklist.topics_after_srs-specific correction, which layers 2 narrow,
    explicit exceptions on top of the generic top-level fix:
      1. The FEHB heading must NOT receive the &nbsp;&nbsp; prefix (PROD's
         original had zero leading whitespace there, unlike its 4 siblings).
      2. TSP's 3rd nested <li> ("How do withdrawal options...") must lose
         its style attribute entirely (PROD's original was a bare <li>),
         while every other nested <li> keeps its style attribute untouched.
    See PDF_REGRESSION_FINDINGS_2026-09-27.md Addendum section 14 for the
    full experimental evidence (256/256 words, all 22 lines, exact block
    height reproduced vs. true PROD).
    """

    # A realistic fragment shaped like the real stored (post Category-D,
    # pre-0002) body_html: 5 top-level headings, no top-level nbsp yet, and
    # the TSP section's 3 real nested items with the 3rd one WITH a style
    # attribute (matching the current, buggy CMS content -- real PROD had no
    # style there at all, which is exactly the defect being corrected).
    BUGGY_INPUT = (
        '<ul style="font-family:Arial, sans-serif; font-size: 10px; color: #2e2e2e; '
        'font-weight: bold; padding-left: 18px; list-style-type:img|svg|3|3|images/rectangle.svg;">'
        '<li style="font-family:Arial, sans-serif; font-size: 11px; line-height: 20px; '
        'color: #285FBF;">Thrift Savings Plan (TSP)'
        '<ul style="font-family:Arial, sans-serif; list-style-type:img|svg|3|3|images/circle.svg; '
        'font-size: 10px; color: #2e2e2e; font-weight: normal; padding-left: 18px;">'
        '<li style="font-family:Arial, sans-serif; line-height: 17px;">'
        '<em>Am I putting the right amount into TSP, and how should I be invested between now '
        'and retirement?</em></li>'
        '<li style="font-family:Arial, sans-serif; line-height: 17px;">'
        '<em>Should I consider the Roth TSP or other tax-free options?</em></li>'
        '<li style="font-family:Arial, sans-serif; line-height: 17px;">'
        '<em>How do withdrawal options from TSP compare to withdrawal options from a private '
        'account?</em></li>'
        '<li style="font-family:Arial, sans-serif; line-height: 17px;">'
        '<em>How can I make the funds I currently have in TSP last for my lifetime once I '
        'retire?</em></li></ul></li>'
        '<li style="font-family:Arial, sans-serif; font-size: 11px; line-height: 20px; '
        'color: #285FBF;">Federal Employees Group Life Insurance (FEGLI)'
        '<ul style="font-family:Arial, sans-serif; list-style-type:img|svg|3|3|images/circle.svg; '
        'font-size: 10px; color: #2e2e2e; font-weight: normal; padding-left: 18px;">'
        '<li style="font-family:Arial, sans-serif; line-height: 17px;">'
        '<em>How do FEGLI options compare to private life insurance options?</em></li></ul></li>'
        '<li style="font-family:Arial, sans-serif; font-size: 11px; line-height: 20px; '
        'color: #285FBF;">Federal Employees Health Benefits (FEHB)'
        '<ul style="font-family:Arial, sans-serif; list-style-type:img|svg|3|3|images/circle.svg; '
        'font-size: 10px; color: #2e2e2e; font-weight: normal; padding-left: 18px;">'
        '<li style="font-family:Arial, sans-serif; line-height: 17px;">'
        '<em>Should I enroll in Medicare at age 65, and what should I do with my FEHB '
        'coverage?</em></li></ul></li>'
        '<li style="font-family:Arial, sans-serif; font-size: 11px; line-height: 20px; '
        'color: #285FBF;">Federal Long Term Care Insurance Program (FLTCIP)'
        '<ul style="font-family:Arial, sans-serif; list-style-type:img|svg|3|3|images/circle.svg; '
        'font-size: 10px; color: #2e2e2e; font-weight: normal; padding-left: 18px;">'
        '<li style="font-family:Arial, sans-serif; line-height: 17px;">'
        '<em>How does FLTCIP compare to private long-term care insurance programs?</em></li>'
        '</ul></li>'
        '<li style="font-family:Arial, sans-serif; font-size: 11px; line-height: 20px; '
        'color: #285FBF;">General Concerns for Retirement'
        '<ul style="font-family:Arial, sans-serif; list-style-type:img|svg|3|3|images/circle.svg; '
        'font-size: 10px; color: #2e2e2e; font-weight: normal; padding-left: 18px;">'
        '<li style="font-family:Arial, sans-serif; line-height: 17px;">'
        '<em>How do I keep from running out of money?</em></li></ul></li></ul>'
    )

    def test_nbsp_added_to_headings_that_historically_require_it(self):
        fixed = _migration_module._checklist_topics_after_srs_fix(self.BUGGY_INPUT)
        self.assertIn('color: #285FBF;">&nbsp;&nbsp;Thrift Savings Plan (TSP)', fixed)
        self.assertIn(
            'color: #285FBF;">&nbsp;&nbsp;Federal Employees Group Life Insurance (FEGLI)', fixed,
        )
        self.assertIn(
            'color: #285FBF;">&nbsp;&nbsp;Federal Long Term Care Insurance Program (FLTCIP)', fixed,
        )
        self.assertIn('color: #285FBF;">&nbsp;&nbsp;General Concerns for Retirement', fixed)
        self.assertEqual(fixed.count('color: #285FBF;">&nbsp;&nbsp;'), 4)

    def test_fehb_heading_receives_no_nbsp_prefix(self):
        fixed = _migration_module._checklist_topics_after_srs_fix(self.BUGGY_INPUT)
        self.assertIn('color: #285FBF;">Federal Employees Health Benefits (FEHB)', fixed)
        self.assertNotIn('&nbsp;&nbsp;Federal Employees Health Benefits (FEHB)', fixed)

    def test_only_tsp_third_nested_item_loses_style_attribute(self):
        fixed = _migration_module._checklist_topics_after_srs_fix(self.BUGGY_INPUT)
        self.assertIn(
            '<li><em>How do withdrawal options from TSP compare to withdrawal options from '
            'a private account?</em></li>',
            fixed,
        )
        # the style attribute must be gone from THIS line specifically, not
        # merely moved/duplicated elsewhere
        self.assertNotIn(
            'style="font-family:Arial, sans-serif; line-height: 17px;">'
            '<em>How do withdrawal',
            fixed,
        )

    def test_other_nested_li_elements_retain_their_style_attribute(self):
        fixed = _migration_module._checklist_topics_after_srs_fix(self.BUGGY_INPUT)
        # every other nested question in BUGGY_INPUT keeps its style attribute
        for question_start in (
            'Am I putting the right amount into TSP',
            'Should I consider the Roth TSP',
            'How can I make the funds I currently have in TSP',
            'How do FEGLI options compare',
            'Should I enroll in Medicare',
            'How does FLTCIP compare',
            'How do I keep from running out of money',
        ):
            self.assertIn(
                f'<li style="font-family:Arial, sans-serif; line-height: 17px;"><em>{question_start}',
                fixed,
                f'expected style attribute preserved before: {question_start!r}',
            )
        # exactly 1 of the 8 nested questions in this fragment lost its style
        self.assertEqual(fixed.count('<li style="font-family:Arial, sans-serif; line-height: 17px;">'), 7)
        self.assertEqual(fixed.count('<li><em>'), 1)

    def test_nested_question_content_receives_no_additional_nbsp(self):
        fixed = _migration_module._checklist_topics_after_srs_fix(self.BUGGY_INPUT)
        # nbsp only ever appears immediately after the 4 top-level
        # 'color: #285FBF;">' markers -- never directly before <em> (nested
        # question text starts with <em>, never gets prefixed)
        self.assertNotIn('&nbsp;<em>', fixed)
        self.assertNotIn('&nbsp;&nbsp;<em>', fixed)

    def test_idempotent_through_two_sanitize_body_html_round_trips(self):
        fixed = _migration_module._checklist_topics_after_srs_fix(self.BUGGY_INPUT)
        once = sanitize_body_html(fixed)
        twice = sanitize_body_html(once)
        self.assertEqual(once, fixed)
        self.assertEqual(twice, once)

    def test_applying_fix_twice_is_idempotent_at_the_function_level(self):
        # The idempotency guard inside _checklist_topics_after_srs_fix()
        # detects the fully-corrected end state and returns it unchanged,
        # so re-invoking the function against its own output (as
        # apply_corrections() would effectively require for a true no-op)
        # does not double-prepend nbsp or otherwise drift.
        once = _migration_module._checklist_topics_after_srs_fix(self.BUGGY_INPUT)
        twice = _migration_module._checklist_topics_after_srs_fix(once)
        self.assertEqual(once.count('color: #285FBF;">&nbsp;&nbsp;'), 4)
        self.assertEqual(once, twice)



class ApplyAndRevertCorrectionsIntegrationTests(TestCase):
    """End-to-end test of the migration's actual apply/revert functions,
    against real ContentBlock/ContentBlockVersion rows (using the real,
    non-historical model classes via django.apps.apps -- equivalent to the
    frozen historical models for this data-only migration, since no schema
    changes are involved)."""

    def setUp(self):
        from django.apps import apps as real_apps
        self.real_apps = real_apps
        self.group = ContentBlockGroup.objects.create(key='pension', label='Pension', display_order=1)

    def test_apply_creates_new_published_version_and_supersedes_old(self):
        block = ContentBlock.objects.create(
            key='pension.high3_pay_included_table', group=self.group, label='High-3 table',
        )
        original = ContentBlockVersion.objects.create(
            block=block, plan_year=2026,
            body_html='<table><tbody><tr><th>x</th><th>&nbsp;&nbsp;&nbsp; Regular pay<br></th></tr></tbody></table>',
        )
        original.publish()

        _migration_module.apply_corrections(self.real_apps, None)

        original.refresh_from_db()
        self.assertEqual(original.status, ContentBlockVersion.STATUS_SUPERSEDED)

        new_version = block.published_version_for(2026)
        self.assertNotEqual(new_version.pk, original.pk)
        self.assertIn('&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; Regular pay', new_version.body_html)

    def test_apply_is_a_no_op_when_content_already_fixed(self):
        block = ContentBlock.objects.create(
            key='fegli.coverage_available', group=self.group, label='FEGLI coverage table',
        )
        already_fixed = ContentBlockVersion.objects.create(
            block=block, plan_year=2026,
            body_html='<table><tbody><tr><td>multiply by the # of multiples selected (1-5)<br></td></tr></tbody></table>',
        )
        already_fixed.publish()

        _migration_module.apply_corrections(self.real_apps, None)

        self.assertEqual(ContentBlockVersion.objects.filter(block=block).count(), 1)
        already_fixed.refresh_from_db()
        self.assertEqual(already_fixed.status, ContentBlockVersion.STATUS_PUBLISHED)

    def test_apply_skips_missing_block_without_error(self):
        # No ContentBlock with this key exists in this test's DB at all --
        # must not raise.
        _migration_module.apply_corrections(self.real_apps, None)

    def test_revert_republishes_prior_version(self):
        block = ContentBlock.objects.create(
            key='checklist.srs_topic', group=self.group, label='Checklist SRS topic',
        )
        original = ContentBlockVersion.objects.create(
            block=block, plan_year=2026,
            body_html='<ul><li style="color: #285FBF;">Social Security and the FERS SRS<ul></ul></li></ul>',
        )
        original.publish()

        _migration_module.apply_corrections(self.real_apps, None)
        fixed_version = block.published_version_for(2026)
        self.assertNotEqual(fixed_version.pk, original.pk)

        _migration_module.revert_corrections(self.real_apps, None)

        original.refresh_from_db()
        fixed_version.refresh_from_db()
        self.assertEqual(original.status, ContentBlockVersion.STATUS_PUBLISHED)
        self.assertEqual(fixed_version.status, ContentBlockVersion.STATUS_SUPERSEDED)

    def test_apply_on_topics_after_srs_applies_both_exceptions_end_to_end(self):
        block = ContentBlock.objects.create(
            key='checklist.topics_after_srs', group=self.group, label='Checklist topics after SRS',
        )
        original = ContentBlockVersion.objects.create(
            block=block, plan_year=2026, body_html=ChecklistTopicsAfterSrsFixTests.BUGGY_INPUT,
        )
        original.publish()

        _migration_module.apply_corrections(self.real_apps, None)

        new_version = block.published_version_for(2026)
        self.assertNotEqual(new_version.pk, original.pk)
        self.assertEqual(new_version.body_html.count('color: #285FBF;">&nbsp;&nbsp;'), 4)
        self.assertIn('color: #285FBF;">Federal Employees Health Benefits (FEHB)', new_version.body_html)
        self.assertIn(
            '<li><em>How do withdrawal options from TSP compare to withdrawal options from '
            'a private account?</em></li>',
            new_version.body_html,
        )

    def test_apply_on_topics_after_srs_is_a_no_op_when_already_corrected(self):
        block = ContentBlock.objects.create(
            key='checklist.topics_after_srs', group=self.group, label='Checklist topics after SRS',
        )
        already_corrected = ContentBlockVersion.objects.create(
            block=block, plan_year=2026,
            body_html=_migration_module._checklist_topics_after_srs_fix(
                ChecklistTopicsAfterSrsFixTests.BUGGY_INPUT
            ),
        )
        already_corrected.publish()

        _migration_module.apply_corrections(self.real_apps, None)

        self.assertEqual(ContentBlockVersion.objects.filter(block=block).count(), 1)
        already_corrected.refresh_from_db()
        self.assertEqual(already_corrected.status, ContentBlockVersion.STATUS_PUBLISHED)

    def test_revert_on_topics_after_srs_republishes_prior_version(self):
        block = ContentBlock.objects.create(
            key='checklist.topics_after_srs', group=self.group, label='Checklist topics after SRS',
        )
        original = ContentBlockVersion.objects.create(
            block=block, plan_year=2026, body_html=ChecklistTopicsAfterSrsFixTests.BUGGY_INPUT,
        )
        original.publish()

        _migration_module.apply_corrections(self.real_apps, None)
        fixed_version = block.published_version_for(2026)
        self.assertNotEqual(fixed_version.pk, original.pk)

        _migration_module.revert_corrections(self.real_apps, None)

        original.refresh_from_db()
        fixed_version.refresh_from_db()
        self.assertEqual(original.status, ContentBlockVersion.STATUS_PUBLISHED)
        self.assertEqual(fixed_version.status, ContentBlockVersion.STATUS_SUPERSEDED)
