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

When --replace is supplied all existing clauses are deleted before import.
"""

import io
from django.core.management.base import BaseCommand, CommandError
from references.models import ReferenceClause


HEADING_STYLES = {'Heading 1', 'Heading 2', 'Heading 3', 'Heading 4', 'Heading 5', 'Title'}
SEPARATOR_TEXTS = {'---', '-------------------', '--------------------------', '-------------------------'}


def _is_separator(text):
    stripped = text.strip('-').strip()
    return stripped == '' and '-' in text


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


def _parse_document(doc):
    """
    Walk all paragraphs and group them into clause records.

    State machine:
      current_category    -- updated on Title / Heading 1
      current_subcategory -- updated on Heading 2 / Heading 3
      current_title       -- set on Heading 4 / Heading 5
      body_lines          -- Normal paragraphs accumulated after a title
    """
    clauses = []
    sort_order = 0

    current_category = 'GENERAL'
    current_subcategory = ''
    current_title = None
    body_lines = []

    def flush():
        nonlocal current_title, body_lines, sort_order
        if current_title and body_lines:
            body = '\n'.join(line for line in body_lines if line.strip())
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
        body_lines = []

    for para in doc.paragraphs:
        style = para.style.name
        text = para.text.strip()

        # Skip blank paragraphs and pure separator lines
        if not text or _is_separator(text):
            continue

        if style == 'Title':
            flush()
            # Only treat as a category if it's a short label (not a body paragraph mis-styled as Title)
            if len(text) <= 120 and text not in ('TITLE', 'Subtitle', '-------------------------', '--------------------------'):
                current_category = text
                current_subcategory = ''
            elif current_title:
                # Long Title-styled paragraph is actually body text
                body_lines.append(text)

        elif style == 'Heading 1':
            flush()
            # Heading 1 that looks like a sub-topic becomes the category
            current_category = text
            current_subcategory = ''

        elif style in ('Heading 2', 'Heading 3'):
            flush()
            current_subcategory = text[:495]  # guard against MySQL column limit

        elif style in ('Heading 4', 'Heading 5'):
            flush()
            current_title = text

        elif style == 'Normal':
            if current_title:
                body_lines.append(text)
            # Normal text before any Heading 4 is skipped (it's preamble/instructions)

    flush()  # catch last pending clause

    return clauses
