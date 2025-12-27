#!/usr/bin/env python
"""
Comprehensive Field Audit - Form vs PDF Template
Identifies naming mismatches between HTML form and PDF template
"""

import re
from collections import defaultdict

# Read form HTML
with open('cases/templates/cases/fact_finder_form.html', 'r', encoding='utf-8') as f:
    form_html = f.read()

# Read PDF template HTML
with open('cases/templates/cases/fact_finder_pdf_template_v2.html', 'r', encoding='utf-8') as f:
    pdf_html = f.read()

# Extract form field names
form_fields_raw = re.findall(r'name="([^"]+)"', form_html)
form_fields = [f for f in form_fields_raw if f not in ['csrfmiddlewaretoken', 'action', 'document_type[]', 'documents[]']]
form_fields_set = set(form_fields)

# Extract PDF template variables ({{ ... }})
pdf_vars_raw = re.findall(r'\{\{\s*([^}]+?)\s*\}\}', pdf_html)
pdf_vars = []
for var in pdf_vars_raw:
    # Remove filters and whitespace
    var = re.sub(r'\|[^}]+', '', var).strip()
    # Filter out system variables and data. prefix
    if var and not any(skip in var for skip in ['now', 'member_name', 'date_submitted', 'workshop_code', 'data.', 'fact_finder.', 'add_info.']):
        pdf_vars.append(var)

pdf_vars_set = set(pdf_vars)

# Categorize fields by section/prefix
def categorize_fields(fields):
    categories = defaultdict(list)
    for field in fields:
        # Determine section based on prefix
        if field.startswith('tsp_'):
            categories['tsp'].append(field)
        elif field.startswith('fegli_'):
            categories['fegli'].append(field)
        elif field.startswith('fehb_'):
            categories['fehb'].append(field)
        elif field.startswith('fltcip_'):
            categories['fltcip'].append(field)
        elif field.startswith('military_') or field.startswith('reserve_') or field.startswith('academy_') or any(x in field for x in ['active_duty', 'lwop']):
            categories['military'].append(field)
        elif any(x in field for x in ['non_deduction', 'break_', 'part_time', 'special']):
            categories['special_service'].append(field)
        elif any(x in field for x in ['retirement_', 'leave_scd', 'sick_leave', 'annual_leave', 'ss_', 'social']):
            categories['retirement_pay'].append(field)
        elif any(x in field for x in ['employee_', 'spouse_', 'address', 'city', 'state', 'zip', 'cbpo']):
            categories['basic_info'].append(field)
        else:
            categories['other'].append(field)
    return categories

form_by_section = categorize_fields(form_fields_set)
pdf_by_section = categorize_fields(pdf_vars_set)

# Generate comprehensive report
print("=" * 80)
print("COMPREHENSIVE FIELD AUDIT REPORT")
print("Form vs PDF Template Field Name Comparison")
print("=" * 80)
print()

all_sections = sorted(set(list(form_by_section.keys()) + list(pdf_by_section.keys())))

for section in all_sections:
    section_upper = section.upper().replace('_', ' ')
    print(f"\n{'='*80}")
    print(f"SECTION: {section_upper}")
    print(f"{'='*80}")
    
    form_section_fields = sorted(form_by_section.get(section, []))
    pdf_section_fields = sorted(pdf_by_section.get(section, []))
    
    # Find mismatches
    mismatches = []
    matches = []
    
    # Fields in form but not in PDF (potential mismatches)
    for form_field in form_section_fields:
        if form_field not in pdf_section_fields:
            # Look for similar PDF fields
            similar = []
            form_base = form_field.replace(f'{section}_', '').replace('_', '')
            for pdf_field in pdf_section_fields:
                pdf_base = pdf_field.replace(f'{section}_', '').replace('_', '')
                # Check if field names are similar
                if form_base in pdf_base or pdf_base in form_base:
                    similar.append(pdf_field)
            
            if similar:
                mismatches.append({
                    'form': form_field,
                    'pdf': similar[0] if len(similar) == 1 else similar,
                    'type': 'potential_mismatch'
                })
            else:
                mismatches.append({
                    'form': form_field,
                    'pdf': None,
                    'type': 'missing_in_pdf'
                })
        else:
            matches.append(form_field)
    
    # Fields in PDF but not in form
    for pdf_field in pdf_section_fields:
        if pdf_field not in form_section_fields:
            mismatches.append({
                'form': None,
                'pdf': pdf_field,
                'type': 'missing_in_form'
            })
    
    # Print mismatches
    if mismatches:
        print("\nMISMATCHES:")
        for i, mismatch in enumerate(mismatches, 1):
            if mismatch['type'] == 'potential_mismatch':
                print(f"  {i}. Form: {mismatch['form']} -> PDF: {mismatch['pdf']}")
            elif mismatch['type'] == 'missing_in_pdf':
                print(f"  {i}. Form: {mismatch['form']} -> PDF: [NOT FOUND]")
            elif mismatch['type'] == 'missing_in_form':
                print(f"  {i}. Form: [NOT FOUND] -> PDF: {mismatch['pdf']}")
    else:
        print("\nMISMATCHES: None")
    
    # Print matches
    if matches:
        print(f"\nMATCHES ({len(matches)}):")
        for match in matches:
            print(f"  OK {match}")
    else:
        print("\nMATCHES: None")

# Summary statistics
print(f"\n\n{'='*80}")
print("SUMMARY STATISTICS")
print(f"{'='*80}")
print(f"Total Form Fields: {len(form_fields_set)}")
print(f"Total PDF Variables: {len(pdf_vars_set)}")
print(f"Exact Matches: {len(form_fields_set & pdf_vars_set)}")
print(f"Only in Form: {len(form_fields_set - pdf_vars_set)}")
print(f"Only in PDF: {len(pdf_vars_set - form_fields_set)}")

# List all fields that are ONLY in form (not in PDF)
form_only = sorted(form_fields_set - pdf_vars_set)
if form_only:
    print(f"\n\nFIELDS ONLY IN FORM (NOT IN PDF) - {len(form_only)} total:")
    for i, field in enumerate(form_only, 1):
        print(f"  {i}. {field}")

# List all fields that are ONLY in PDF (not in form)
pdf_only = sorted(pdf_vars_set - form_fields_set)
if pdf_only:
    print(f"\n\nFIELDS ONLY IN PDF (NOT IN FORM) - {len(pdf_only)} total:")
    for i, field in enumerate(pdf_only, 1):
        print(f"  {i}. {field}")

print("\n" + "="*80)
print("END OF REPORT")
print("="*80)
