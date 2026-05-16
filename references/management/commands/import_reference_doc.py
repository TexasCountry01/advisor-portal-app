"""
Management command to import (or re-import) the Report Notes Template .docx
into the ReferenceClause table.

Usage:
    python manage.py import_reference_doc <path/to/file.docx>
    python manage.py import_reference_doc <path/to/file.docx> --replace

Document heading hierarchy used for parsing:
    Title     -> top-level category label (e.g. "VERA", "OPERATIONAL ITEMS")
    Heading 1 -> major section (falls under current category)
    Heading 2 -> sub-section  (falls under current category + section)
    Heading 3 -> sub-sub-section (treated same as Heading 2 for sub-category)
    Heading 4 -> clause title  (the named verbiage snippet)
    Normal    -> clause body text (accumulated until next heading 4+)

Body paragraphs are converted to HTML preserving:
  - Bold, italic, underline, text color
  - Yellow highlights → <mark> tags (the "update me" cue)
  - Hyperlinks → <a href="..." target="_blank"> tags
  - List Bullet* paragraphs → <ul><li>
  - List Number* paragraphs → <ol><li>

When --replace is supplied all existing clauses are deleted before import.
"""

import io
from html import escape as html_escape

from django.core.management.base import BaseCommand, CommandError
from references.models import ReferenceClause


HEADING_STYLES = {'Heading 1', 'Heading 2', 'Heading 3', 'Heading 4', 'Heading 5', 'Title'}
SEPARATOR_TEXTS = {'---', '-------------------', '--------------------------', '-------------------------'}

LIST_BULLET_STYLES = {'List Bullet', 'List Bullet 2', 'List Bullet 3', 'List Paragraph'}
LIST_NUMBER_STYLES = {'List Number', 'List Number 2', 'List Number 3'}

# OOXML namespace URIs
W_NS = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
R_NS = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'

# Map Word highlight color names to CSS background values
HIGHLIGHT_CSS = {
    'yellow': '#FFFF00',
    'cyan': '#00FFFF',
    'green': '#00FF00',
    'magenta': '#FF00FF',
    'red': '#FF0000',
    'blue': '#0000FF',
    'darkBlue': '#00008B',
    'darkCyan': '#008B8B',
    'darkGray': '#A9A9A9',
    'darkGreen': '#006400',
    'darkMagenta': '#8B008B',
    'darkRed': '#8B0000',
    'darkYellow': '#808000',
    'lightGray': '#D3D3D3',
}


def _is_separator(text):
    stripped = text.strip('-').strip()
    return stripped == '' and '-' in text


def _wq(tag):
    """Return the Clark-notation qualified name for a w: tag."""
    return f'{{{W_NS}}}{tag}'


def _run_elem_to_html(r_elem):
    """Convert a <w:r> XML element to an HTML fragment."""
    texts = r_elem.findall(_wq('t'))
    text = ''.join(t.text or '' for t in texts)
    if not text:
        return ''

    escaped = html_escape(text)

    rpr = r_elem.find(_wq('rPr'))
    if rpr is None:
        return escaped

    # Highlight — checked first, as it affects background (outermost wrapper)
    highlight = rpr.find(_wq('highlight'))
    if highlight is not None:
        color_val = highlight.get(_wq('val'), '')
        if color_val == 'yellow':
            escaped = f'<mark>{escaped}</mark>'
        elif color_val in HIGHLIGHT_CSS:
            bg = HIGHLIGHT_CSS[color_val]
            escaped = f'<span style="background-color:{bg};">{escaped}</span>'

    # Text color (skip auto and pure black — those are defaults)
    color_el = rpr.find(_wq('color'))
    if color_el is not None:
        val = color_el.get(_wq('val'), 'auto')
        if val and val.lower() not in ('auto', '000000') and len(val) == 6:
            escaped = f'<span style="color:#{val};">{escaped}</span>'

    # Bold
    b_el = rpr.find(_wq('b'))
    if b_el is not None:
        b_val = b_el.get(_wq('val'), '1')
        if b_val not in ('0', 'false', 'off'):
            escaped = f'<strong>{escaped}</strong>'

    # Italic
    i_el = rpr.find(_wq('i'))
    if i_el is not None:
        i_val = i_el.get(_wq('val'), '1')
        if i_val not in ('0', 'false', 'off'):
            escaped = f'<em>{escaped}</em>'

    # Underline
    u_el = rpr.find(_wq('u'))
    if u_el is not None:
        u_val = u_el.get(_wq('val'), '')
        if u_val and u_val not in ('none', 'None'):
            escaped = f'<u>{escaped}</u>'

    return escaped


def _para_to_html(para, doc):
    """
    Convert a body paragraph to an HTML fragment string.
    Walks para._p children to handle hyperlinks inline with regular runs.
    """
    parts = []
    for child in para._p:
        tag_local = child.tag.split('}')[-1] if '}' in child.tag else child.tag

        if tag_local == 'r':
            parts.append(_run_elem_to_html(child))

        elif tag_local == 'hyperlink':
            # Resolve relationship target URL
            r_id = child.get(f'{{{R_NS}}}id')
            url = ''
            if r_id:
                try:
                    url = doc.part.rels[r_id].target_ref
                except (KeyError, AttributeError):
                    pass

            link_inner = ''.join(
                _run_elem_to_html(r_el)
                for r_el in child.findall(_wq('r'))
            )

            if url and link_inner:
                parts.append(f'<a href="{html_escape(url)}" target="_blank">{link_inner}</a>')
            else:
                parts.append(link_inner)

    return ''.join(parts)


def _flush_body(body_parts):
    """
    Convert a list of (style_type, html_fragment) tuples into a final HTML string.
    Consecutive list items of the same type are grouped into <ul> or <ol>.
    """
    result = []
    i = 0
    while i < len(body_parts):
        ptype, phtml = body_parts[i]

        if ptype == 'li_bullet':
            items = []
            while i < len(body_parts) and body_parts[i][0] == 'li_bullet':
                if body_parts[i][1].strip():
                    items.append(f'<li>{body_parts[i][1]}</li>')
                i += 1
            if items:
                result.append(f'<ul>{"".join(items)}</ul>')

        elif ptype == 'li_number':
            items = []
            while i < len(body_parts) and body_parts[i][0] == 'li_number':
                if body_parts[i][1].strip():
                    items.append(f'<li>{body_parts[i][1]}</li>')
                i += 1
            if items:
                result.append(f'<ol>{"".join(items)}</ol>')

        else:
            if phtml.strip():
                result.append(f'<p>{phtml}</p>')
            i += 1

    return ''.join(result)


class Command(BaseCommand):
    help = 'Import Reference Notes Template .docx into ReferenceClause table'

    def add_arguments(self, parser):
        parser.add_argument('docx_path', type=str, help='Path to the .docx file')
        parser.add_argument(
            '--replace',
            action='store_true',
            default=False,
            help='Delete all existing clauses before importing',
        )

    def handle(self, *args, **options):
        try:
            from docx import Document
        except ImportError:
            raise CommandError('python-docx is not installed. Run: pip install python-docx')

        path = options['docx_path']
        try:
            with open(path, 'rb') as f:
                data = f.read()
            doc = Document(io.BytesIO(data))
        except FileNotFoundError:
            raise CommandError(f'File not found: {path}')
        except Exception as e:
            raise CommandError(f'Could not open document: {e}')

        if options['replace']:
            count, _ = ReferenceClause.objects.all().delete()
            self.stdout.write(f'Deleted {count} existing clauses.')

        clauses = _parse_document(doc)
        self.stdout.write(f'Parsed {len(clauses)} clauses from document.')

        created = ReferenceClause.objects.bulk_create([
            ReferenceClause(**c) for c in clauses
        ])
        self.stdout.write(self.style.SUCCESS(
            f'Successfully imported {len(created)} reference clauses.'
        ))
        self.stdout.write(self.style.WARNING(
            'Remember to re-mark featured clauses in Django admin after a --replace import.'
        ))


def _parse_document(doc):
    """
    Walk all paragraphs and group them into clause records.

    State machine:
      current_category    -- updated on Title / Heading 1
      current_subcategory -- updated on Heading 2 / Heading 3
      current_title       -- set on Heading 4 / Heading 5, and also temporarily
                             on Heading 1/2/3 to capture any body text directly
                             under that section heading as its own standalone clause
      body_parts          -- list of (type, html) tuples accumulated after a heading
                             type: 'p' | 'li_bullet' | 'li_number'

    Body paragraphs are converted to HTML preserving:
      - Bold, italic, underline, text color
      - Yellow highlights → <mark> tags (the "update me" cue)
      - Hyperlinks → <a href="..." target="_blank"> tags
      - List Bullet* paragraphs → <ul><li>
      - List Number* paragraphs → <ol><li>
    """
    clauses = []
    sort_order = 0

    current_category = 'GENERAL'
    current_subcategory = ''
    current_title = None
    body_parts = []

    def flush():
        nonlocal current_title, body_parts, sort_order
        if current_title and body_parts:
            body = _flush_body(body_parts)
            if body.strip():
                clauses.append({
                    'category': current_category,
                    'subcategory': current_subcategory,
                    'title': current_title,
                    'body': body,
                    'sort_order': sort_order,
                    'is_active': True,
                })
                sort_order += 1
        current_title = None
        body_parts = []

    for para in doc.paragraphs:
        style = para.style.name
        text = para.text.strip()

        # Skip blank paragraphs and pure separator lines
        if not text or _is_separator(text):
            continue

        if style == 'Title':
            flush()
            if len(text) <= 120 and text not in ('TITLE', 'Subtitle', '-------------------------', '--------------------------'):
                current_category = text
                current_subcategory = ''
                current_title = text  # capture any body text directly under this heading
            elif current_title:
                para_html = _para_to_html(para, doc)
                if para_html.strip():
                    body_parts.append(('p', para_html))

        elif style == 'Heading 1':
            flush()
            current_category = text
            current_subcategory = ''
            current_title = text  # capture any body text directly under this heading

        elif style in ('Heading 2', 'Heading 3'):
            flush()
            current_subcategory = text
            current_title = text  # capture any body text directly under this heading

        elif style in ('Heading 4', 'Heading 5'):
            flush()
            current_title = text

        elif style in LIST_BULLET_STYLES:
            if current_title:
                para_html = _para_to_html(para, doc)
                body_parts.append(('li_bullet', para_html))

        elif style in LIST_NUMBER_STYLES:
            if current_title:
                para_html = _para_to_html(para, doc)
                body_parts.append(('li_number', para_html))

        elif style == 'Normal':
            if current_title:
                para_html = _para_to_html(para, doc)
                if para_html.strip():
                    body_parts.append(('p', para_html))
            # Normal text before any heading is skipped (it's preamble/instructions)

    flush()  # catch last pending clause

    return clauses

