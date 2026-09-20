"""
Tests for HTML sanitization (Option A, step 5). See fact_finder_content/sanitize.py.
"""
from django.test import SimpleTestCase

from fact_finder_content.sanitize import sanitize_body_html


class SanitizeBodyHtmlTests(SimpleTestCase):
    def test_allowed_tags_pass_through_unchanged(self):
        html = '<p>Hello <strong>world</strong>, <em>welcome</em>.</p><ul><li>one</li></ul><br>'
        self.assertEqual(sanitize_body_html(html), html)

    def test_script_tag_is_stripped_but_stays_inert(self):
        result = sanitize_body_html('<p>Hi</p><script>alert(1)</script>')
        self.assertNotIn('<script', result)
        self.assertNotIn('</script>', result)
        # Text content survives as inert plain text (not inside a <script> element anymore).
        self.assertIn('alert(1)', result)

    def test_onclick_attribute_is_stripped_from_allowed_tag(self):
        result = sanitize_body_html('<p onclick="alert(1)">Hi</p>')
        self.assertNotIn('onclick', result)
        self.assertIn('Hi', result)

    def test_style_attribute_is_stripped(self):
        result = sanitize_body_html('<p style="color:red">Hi</p>')
        self.assertNotIn('style', result)

    def test_disallowed_tag_img_is_stripped(self):
        result = sanitize_body_html('<p>Hi</p><img src="x.png" onerror="alert(1)">')
        self.assertNotIn('<img', result)
        self.assertNotIn('onerror', result)

    def test_disallowed_tag_a_is_stripped_but_link_text_kept(self):
        result = sanitize_body_html('<p>See <a href="javascript:alert(1)">this</a></p>')
        self.assertNotIn('<a ', result)
        self.assertNotIn('javascript:', result)
        self.assertIn('this', result)

    def test_merge_field_tokens_survive_sanitization(self):
        html = '<p>You are contributing [[match_percentage]]%.</p>'
        self.assertEqual(sanitize_body_html(html), html)

    def test_none_input_returns_empty_string(self):
        self.assertEqual(sanitize_body_html(None), '')

    def test_empty_string_input(self):
        self.assertEqual(sanitize_body_html(''), '')

    def test_table_tags_with_safe_style_and_width_pass_through_unchanged(self):
        # CSSSanitizer (tinycss2) re-serializes style values (e.g. adds a
        # trailing `;`) -- harmless for PDF rendering, so this checks
        # structure/content survives rather than an exact byte match.
        html = (
            '<table cellpadding="3" style="font-family:Arial, sans-serif; font-size:9px">'
            '<thead><tr>'
            '<th style="border-bottom: 1px solid #ddd;" width="20%">Coverage</th>'
            '<th style="border-bottom: 1px solid #ddd;" width="80%">Description</th>'
            '</tr></thead>'
            '<tbody><tr><td width="20%">Basic</td><td width="80%">Flat $10,000</td></tr></tbody>'
            '</table>'
        )
        result = sanitize_body_html(html)
        self.assertIn('<table cellpadding="3"', result)
        self.assertIn('font-family:Arial, sans-serif', result)
        self.assertIn('font-size:9px', result)
        self.assertIn('<thead>', result)
        self.assertIn('border-bottom: 1px solid #ddd', result)
        self.assertIn('width="20%">Coverage</th>', result)
        self.assertIn('width="80%">Description</th>', result)
        self.assertIn('<tbody>', result)
        self.assertIn('width="20%">Basic</td>', result)
        self.assertIn('width="80%">Flat $10,000</td>', result)

    def test_span_with_safe_style_passes_through_unchanged(self):
        html = '<span style="font-size: 11px; font-weight: bold;">Heading</span>'
        self.assertEqual(sanitize_body_html(html), html)

    def test_style_with_url_is_stripped_even_on_table_tag(self):
        result = sanitize_body_html('<td style="background-image:url(javascript:alert(1))">Hi</td>')
        self.assertNotIn('style', result)
        self.assertNotIn('url(', result)

    def test_style_with_disallowed_property_is_stripped(self):
        result = sanitize_body_html('<td style="position: fixed; top: 0;">Hi</td>')
        self.assertNotIn('style', result)

    def test_style_on_p_tag_still_stripped(self):
        result = sanitize_body_html('<p style="font-size: 10px;">Hi</p>')
        self.assertNotIn('style', result)

    def test_width_attribute_rejected_on_non_table_tag(self):
        result = sanitize_body_html('<p width="50%">Hi</p>')
        self.assertNotIn('width', result)

    def test_width_attribute_must_be_numeric(self):
        result = sanitize_body_html('<td width="expression(alert(1))">Hi</td>')
        self.assertNotIn('width', result)

    def test_cellpadding_only_allowed_on_table(self):
        result = sanitize_body_html('<td cellpadding="3">Hi</td>')
        self.assertNotIn('cellpadding', result)

    def test_merge_field_tokens_survive_inside_table_cell(self):
        # html5lib's tree construction wraps a bare <tr> in an implicit
        # <tbody> (standard, harmless HTML5 normalization) -- check content
        # survives rather than an exact byte match.
        html = '<table><tr><td>[[tsp.gfund_rate]]%</td></tr></table>'
        result = sanitize_body_html(html)
        self.assertIn('[[tsp.gfund_rate]]%', result)
        self.assertIn('<table>', result)
        self.assertIn('<td>', result)
