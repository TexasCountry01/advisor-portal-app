"""
HTML sanitization for Fact Finder content blocks (Option A, step 5).

Per the analysis doc's Security notes (docs/FACT_FINDER_PDF_MODERNIZATION_ANALYSIS_2026-09-06.md):
"Sanitize on save, not just on render" — this stored HTML is written by
admins/content editors, reviewed by other admins, and eventually merged into a
PDF-generation pipeline consumed by benefits-software, so it's treated as
untrusted input at the trust boundary (save time), not just at render time.

Allow-list is deliberately restricted to exactly the tags the restricted
TinyMCE toolbar (formatselect | bold italic underline | bullist numlist) is
meant to produce for headings/paragraphs/emphasis/lists — no attributes at
all (no `style`, no `on*` handlers, no `href`/`src`), so there is no
attribute-based XSS surface regardless of what a future toolbar change might
emit.
"""
import bleach

ALLOWED_TAGS = ['p', 'strong', 'em', 'ul', 'ol', 'li', 'br']
ALLOWED_ATTRIBUTES = {}


def sanitize_body_html(raw_html):
    """Strip any tag/attribute not on the allow-list. Disallowed tags are
    removed (not escaped) — their text content is kept as plain text, which
    is inert (not executable) once outside its original tag."""
    return bleach.clean(
        raw_html or '',
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        strip=True,
    )
