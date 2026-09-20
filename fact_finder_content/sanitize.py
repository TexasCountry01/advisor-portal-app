"""
HTML sanitization for Fact Finder content blocks (Option A, step 5; table
support added for Phase 3's Category B "structural reference tables" work).

Per the analysis doc's Security notes (docs/FACT_FINDER_PDF_MODERNIZATION_ANALYSIS_2026-09-06.md):
"Sanitize on save, not just on render" — this stored HTML is written by
admins/content editors, reviewed by other admins, and eventually merged into a
PDF-generation pipeline consumed by benefits-software, so it's treated as
untrusted input at the trust boundary (save time), not just at render time.

Tag allow-list covers the restricted TinyMCE toolbar's output
(formatselect | bold italic underline | bullist numlist) PLUS a small
table-editing surface (table, thead, tbody, tr, th, td, span) needed to
reproduce the exact multi-column reference tables that already exist,
hardcoded, in report_pdf.blade.php (e.g. TSP fund rates, FEGLI coverage
tables) — see the "Category B" options in the analysis doc.

No attribute is allowed anywhere by default. Exactly three attributes are
permitted, each scoped to the specific tags that legitimately need them, and
each validated for content (not just name):
  - `style` on table/th/td/span — value must be a semicolon-separated list of
    `property: value` declarations where the property is on a small safe
    allow-list (SAFE_CSS_PROPERTIES) and the value contains only
    letters/digits/`#`/`%`/`.`/`,`/`-`/spaces. This blocks every known
    CSS-based attack vector (`url(...)`, `expression(...)`, `@import`, etc.)
    because none of those require characters outside that safe set — the
    parentheses alone make `url(...)`/`expression(...)` fail the regex.
  - `width` on th/td — must be a bare 1-3 digit number, optionally with a
    trailing `%`.
  - `cellpadding` on table — must be a bare 1-2 digit number.
Anything else (style on a `<p>`, any `on*` handler, `href`, `src`, `class`,
`id`, etc.) is stripped, same as before.
"""
import re

import bleach
from bleach.css_sanitizer import CSSSanitizer

TABLE_TAGS = ['table', 'thead', 'tbody', 'tr', 'th', 'td', 'span']
ALLOWED_TAGS = ['p', 'strong', 'em', 'ul', 'ol', 'li', 'br'] + TABLE_TAGS

SAFE_CSS_PROPERTIES = {
    'font-family', 'font-size', 'font-weight', 'text-align', 'color',
    'border-top', 'border-bottom', 'border-left', 'border-right',
    'width', 'line-height', 'margin', 'margin-top', 'padding',
    'page-break-after', 'page-break-before',
}
_SAFE_CSS_VALUE_RE = re.compile(r'^[A-Za-z0-9#%.,\- ]+$')
_WIDTH_ATTR_RE = re.compile(r'^\d{1,3}%?$')
_CELLPADDING_ATTR_RE = re.compile(r'^\d{1,2}$')

_STYLE_ELIGIBLE_TAGS = {'table', 'th', 'td', 'span'}
_WIDTH_ELIGIBLE_TAGS = {'th', 'td'}
_CELLPADDING_ELIGIBLE_TAGS = {'table'}

# bleach.clean() only preserves a `style` attribute's VALUE if a CSSSanitizer
# is supplied (otherwise it silently blanks it to ''), so this does the real
# CSS-level allow-listing (via tinycss2) — restricted to the exact same
# SAFE_CSS_PROPERTIES list. `_is_safe_style_value` below is a second,
# independent gate applied to the RAW attribute value before bleach even
# gets to the CSSSanitizer step — defense in depth, not a replacement for it.
CSS_SANITIZER = CSSSanitizer(allowed_css_properties=sorted(SAFE_CSS_PROPERTIES))


def _is_safe_style_value(value):
    """A `style` value is safe only if EVERY declaration in it uses an
    allow-listed property name and a value made up entirely of safe
    characters. Any single unsafe declaration rejects the whole attribute
    (no partial/rewritten style values — all or nothing)."""
    if not value:
        return False
    for declaration in value.split(';'):
        declaration = declaration.strip()
        if not declaration:
            continue
        if ':' not in declaration:
            return False
        prop, _, val = declaration.partition(':')
        prop = prop.strip().lower()
        val = val.strip()
        if prop not in SAFE_CSS_PROPERTIES:
            return False
        if not val or not _SAFE_CSS_VALUE_RE.match(val):
            return False
    return True


def _attribute_allowed(tag, name, value):
    """bleach.clean's attribute callback: return True to keep `name=value` on
    `tag`, False to strip it. Every attribute not explicitly handled here is
    rejected."""
    if name == 'style':
        return tag in _STYLE_ELIGIBLE_TAGS and _is_safe_style_value(value)
    if name == 'width':
        return tag in _WIDTH_ELIGIBLE_TAGS and bool(_WIDTH_ATTR_RE.match(value))
    if name == 'cellpadding':
        return tag in _CELLPADDING_ELIGIBLE_TAGS and bool(_CELLPADDING_ATTR_RE.match(value))
    return False


def sanitize_body_html(raw_html):
    """Strip any tag/attribute not on the allow-list. Disallowed tags are
    removed (not escaped) — their text content is kept as plain text, which
    is inert (not executable) once outside its original tag."""
    return bleach.clean(
        raw_html or '',
        tags=ALLOWED_TAGS,
        attributes=_attribute_allowed,
        css_sanitizer=CSS_SANITIZER,
        strip=True,
    )
