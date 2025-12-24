#!/usr/bin/env python
"""Analyze field mapping between form data and PDF template."""

import os
import django
import re

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from cases.models import Case
import json

# Get the actual data structure from Case #9
case = Case.objects.get(id=9)
fact_finder_data = case.fact_finder_data

print("="*80)
print("FACT FINDER DATA STRUCTURE ANALYSIS")
print("="*80)
print("\nData sections in fact_finder_data JSON:")
print(json.dumps(list(fact_finder_data.keys()), indent=2))

print("\n" + "="*80)
print("DETAILED FIELD MAPPING")
print("="*80)

for section_key, section_data in fact_finder_data.items():
    print(f"\n[{section_key.upper()}]")
    if isinstance(section_data, dict):
        for field_key, field_value in section_data.items():
            print(f"  - {field_key}: {type(field_value).__name__} = {repr(field_value)[:60]}")
    else:
        print(f"  (non-dict value: {type(section_data).__name__})")

# Now check what fields the PDF template uses
print("\n" + "="*80)
print("PDF TEMPLATE FIELD USAGE")
print("="*80)

template_path = 'cases/templates/cases/fact_finder_pdf_template_v2.html'
with open(template_path, 'r', encoding='utf-8') as f:
    template_content = f.read()

# Find all {{ data.something }} patterns
data_refs = re.findall(r'{{\s*data\.([a-zA-Z0-9_\.]+?)\s*[|}]', template_content)
unique_refs = sorted(set(data_refs))

print(f"\nFields referenced in PDF template ({len(unique_refs)} unique):")
for ref in unique_refs:
    print(f"  - data.{ref}")

# Find mismatches
print("\n" + "="*80)
print("POTENTIAL MAPPING ISSUES")
print("="*80)

# Build list of all available paths in the data
def get_all_paths(d, prefix=''):
    paths = []
    if isinstance(d, dict):
        for key, value in d.items():
            current_path = f"{prefix}.{key}" if prefix else key
            paths.append(current_path)
            if isinstance(value, dict):
                paths.extend(get_all_paths(value, current_path))
    return paths

available_paths = set(get_all_paths(fact_finder_data))
used_paths = set(unique_refs)

print("\nFields used in template but NOT in data structure:")
missing = used_paths - available_paths
if missing:
    for path in sorted(missing):
        print(f"  ❌ data.{path}")
else:
    print("  ✓ All template fields exist in data structure")

print("\nFields in data structure but NOT used in template:")
unused = available_paths - used_paths
if unused:
    for path in sorted(unused):
        print(f"  ⚠️  data.{path}")
else:
    print("  ✓ All data fields are used in template")

print("\n" + "="*80)
print("SUMMARY")
print("="*80)
print(f"Data sections: {len(fact_finder_data)}")
print(f"Template field references: {len(unique_refs)}")
print(f"Available data paths: {len(available_paths)}")
print(f"Missing mappings: {len(missing)}")
print(f"Unused data fields: {len(unused)}")
