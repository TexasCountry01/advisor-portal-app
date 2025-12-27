#!/usr/bin/env python
"""
Identify all PDF template variable mismatches that need fixing.
"""

import re
from pathlib import Path

pdf_path = Path('cases/templates/cases/fact_finder_pdf_template_v2.html')
pdf_content = pdf_path.read_text()

print("="*120)
print("PDF TEMPLATE VARIABLE MISMATCH ANALYSIS")
print("="*120)

# Find all template variables
template_refs = re.findall(r'\{\{\s*([a-zA-Z_][a-zA-Z0-9_.]*)\s*[\|\}]', pdf_content)

# Analyze each reference
print(f"\nFound {len(set(template_refs))} unique template variables:")
print("\nMismatches (fact_finder.* that should be section.*):")

mismatches = {}
for var in sorted(set(template_refs)):
    if var.startswith('fact_finder.'):
        # This is wrong - should be section.field
        field = var.replace('fact_finder.', '')
        
        # Map to correct section based on field name
        if field.startswith('fegli_'):
            correct = f"fegli.{field.replace('fegli_', '')}"
        elif field.startswith('fehb_'):
            correct = f"fehb.{field.replace('fehb_', '')}"
        elif field.startswith('fltcip_'):
            correct = f"fltcip.{field.replace('fltcip_', '')}"
        elif field.startswith('tsp_'):
            correct = f"tsp.{field.replace('tsp_', '')}"
        elif field.startswith('active_duty_'):
            correct = f"mad.{field.replace('active_duty_', '')}"
        elif field.startswith('reserves_'):
            correct = f"reserves.{field.replace('reserves_', '')}"
        elif field in ['additional_notes', 'page1_notes', 'other_pertinent_details']:
            correct = f"add_info.{field}"
        else:
            correct = f"??? (unknown mapping for {field})"
        
        mismatches[var] = correct

print(f"\nTotal mismatches to fix: {len(mismatches)}")
for old_var, new_var in sorted(mismatches.items()):
    print(f"  {{ old_var }} → {{ new_var }}")
    
# Count occurrences of each mismatch
print("\n" + "="*120)
print("MISMATCH FREQUENCY (how many times each appears in template)")
print("="*120)

for old_var in sorted(mismatches.keys()):
    count = pdf_content.count(f"{{ {old_var} }}")
    if count == 0:
        count = pdf_content.count(old_var)
    if count > 0:
        print(f"{count:3d}x  {old_var:40s} → {mismatches[old_var]}")

print("\n" + "="*120)
print("SUMMARY")
print("="*120)
print(f"""
Total mismatches: {len(mismatches)}

Action items:
1. Replace all 'fact_finder.' references with correct section names
2. Key mappings:
   - fact_finder.fegli_* → fegli.*
   - fact_finder.fehb_* → fehb.*
   - fact_finder.fltcip_* → fltcip.*
   - fact_finder.tsp_* → tsp.*
   - fact_finder.active_duty_* → mad.*
   - fact_finder.reserves_* → reserves.*
   - fact_finder.additional_notes → add_info.additional_notes
   - fact_finder.page1_notes → add_info.page1_notes

Run: python fix_template_variables.py
To automatically generate all the replacements needed.
""")
