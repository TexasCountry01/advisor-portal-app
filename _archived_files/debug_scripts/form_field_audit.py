#!/usr/bin/env python
"""
Comprehensive Form Field Audit
Analyzes every field in the form and traces it through the pipeline.
"""

import re
from pathlib import Path

print("="*120)
print("COMPREHENSIVE FORM FIELD AUDIT")
print("="*120)

# STEP 1: Extract all form field names from HTML
print("\n[1/4] SCANNING HTML FORM FOR ALL FIELD NAMES...")
form_path = Path('cases/templates/cases/fact_finder_form.html')
form_content = form_path.read_text()

# Find all input/select/textarea with name attributes
form_fields = set(re.findall(r'name=["\']([^"\']+)["\']', form_content))
form_fields = {f for f in form_fields if f not in ['action']}  # exclude hidden action field

print(f"✓ Found {len(form_fields)} form fields in HTML")

# STEP 2: Extract all mapped fields from views.py
print("\n[2/4] SCANNING VIEWS.PY FOR MAPPED FIELDS...")
views_path = Path('cases/views.py')
views_content = views_path.read_text()

# Find all request.POST.get() calls
views_fields = set(re.findall(r"request\.POST\.get\(['\"]([^'\"]+)['\"]", views_content))
print(f"✓ Found {len(views_fields)} fields referenced in views.py")

# STEP 3: Extract all template variables from PDF template
print("\n[3/4] SCANNING PDF TEMPLATE FOR VARIABLES...")
pdf_path = Path('cases/templates/cases/fact_finder_pdf_template_v2.html')
pdf_content = pdf_path.read_text()

# Find all {{ variable }} references
template_vars = set(re.findall(r'\{\{\s*([a-zA-Z_][a-zA-Z0-9_.]*)\s*\}\}', pdf_content))
template_vars = {v for v in template_vars if not v.startswith('forloop')}

print(f"✓ Found {len(template_vars)} template variables in PDF")

# STEP 4: Compare and identify gaps
print("\n[4/4] ANALYZING GAPS...")

form_not_in_views = sorted(form_fields - views_fields)
views_not_in_template = sorted(views_fields - {v.split('.')[0] for v in template_vars})

print("\n" + "="*120)
print("FORM → VIEWS.PY MAPPING STATUS")
print("="*120)
print(f"\nFields in form: {len(form_fields)}")
print(f"Fields mapped in views.py: {len(views_fields)}")
print(f"Form fields NOT in views.py: {len(form_not_in_views)}")

if form_not_in_views:
    print(f"\n❌ UNMAPPED FORM FIELDS ({len(form_not_in_views)}):")
    for field in form_not_in_views[:30]:  # Show first 30
        print(f"  - {field}")
    if len(form_not_in_views) > 30:
        print(f"  ... and {len(form_not_in_views) - 30} more")

print("\n" + "="*120)
print("VIEWS.PY → PDF TEMPLATE RENDERING STATUS")
print("="*120)
print(f"\nFields in views.py: {len(views_fields)}")
print(f"Template variables in PDF: {len(template_vars)}")

# Check which top-level sections are in template
sections_in_template = {v.split('.')[0] for v in template_vars if '.' in v}
print(f"Sections in template: {len(sections_in_template)}")
print(f"  Sections: {sorted(sections_in_template)}")

# Find views.py sections not in template
nested_sections = set(re.findall(r"'([a-z_]+)':\s*\{", views_content))

print(f"\nSections in views.py JSON: {sorted(nested_sections)}")

missing_sections = nested_sections - sections_in_template
if missing_sections:
    print(f"\n❌ SECTIONS NOT IN PDF TEMPLATE ({len(missing_sections)}):")
    for section in sorted(missing_sections):
        print(f"  - {section}")

print("\n" + "="*120)
print("CHECKBOX PATTERN ANALYSIS")
print("="*120)

# Find checkbox trios (field_yes, field_no, field_unsure)
checkbox_trios = {}
for field in form_fields:
    if field.endswith('_yes'):
        base = field[:-4]
        if f"{base}_no" in form_fields and f"{base}_unsure" in form_fields:
            checkbox_trios[base] = [f"{base}_yes", f"{base}_no", f"{base}_unsure"]

print(f"Found {len(checkbox_trios)} checkbox trio patterns (Y/N/Unsure):")
for base in sorted(checkbox_trios.keys())[:15]:
    in_views = all(f in views_fields for f in checkbox_trios[base])
    status = "✓ in views" if in_views else "❌ NOT in views"
    print(f"  - {base}: {status}")

if len(checkbox_trios) > 15:
    print(f"  ... and {len(checkbox_trios) - 15} more")

print("\n" + "="*120)
print("NOTES FIELDS ANALYSIS")
print("="*120)

notes_fields = {f for f in form_fields if 'note' in f.lower() or 'comment' in f.lower()}
print(f"Found {len(notes_fields)} notes/comment fields:")
for field in sorted(notes_fields):
    in_views = field in views_fields
    in_template = any(field in var or field.replace('_', '.') in var for var in template_vars)
    status = "✓" if (in_views and in_template) else "❌"
    print(f"  {status} {field}: views={in_views}, template={in_template}")

print("\n" + "="*120)
print("RECOMMENDED FIXES")
print("="*120)

print(f"""
1. FORM FIELDS NOT MAPPED IN VIEWS.PY ({len(form_not_in_views)} fields):
   → Add these to the fact_finder_data dictionary in views.py

2. SECTIONS NOT RENDERING IN PDF ({len(missing_sections)} sections):
   → Add template blocks for: {', '.join(sorted(missing_sections))}
   → Use correct variable paths like: {{{{ section_name.field_name }}}}

3. NOTES FIELDS ({len([f for f in notes_fields if f not in views_fields])} not mapped):
   → Check if notes fields are using correct form_name → db_path mapping
   → Verify template references match database structure

4. CHECKBOX TRIOS:
   → Ensure conversion logic is: 'Yes' if yes_field else ('No' if no_field else ('Unsure' if unsure_field else ''))
   → Verify these are all in views.py with proper conversion

NEXT STEP:
Run: python detailed_field_audit.py
This will show EVERY field with its mapping status.
""")

print("\n" + "="*120)
print("SAMPLE OUTPUT - FIRST 20 FORM FIELDS")
print("="*120)
for field in sorted(form_fields)[:20]:
    in_views = "✓" if field in views_fields else "❌"
    in_template = "✓" if field in template_vars else ("?" if any(field in v for v in template_vars) else "❌")
    print(f"{in_views} {in_template}  {field}")
