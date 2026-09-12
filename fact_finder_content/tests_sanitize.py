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
