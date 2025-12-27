import os
import django
import json
import re

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from cases.models import Case

# Load the case data
case = Case.objects.get(id=24)
data = case.fact_finder_data

# Load the PDF template
with open('cases/templates/cases/fact_finder_pdf_template_v2.html', 'r', encoding='utf-8') as f:
    template_content = f.read()

# Find all template variables ({{ something }})
template_vars = re.findall(r'\{\{\s*([a-zA-Z0-9_.]+)(?:\|[^}]+)?\s*\}\}', template_content)
template_vars = list(set(template_vars))  # Remove duplicates

# Find all conditional checks ({% if something %})
if_conditions = re.findall(r'\{%\s*if\s+([a-zA-Z0-9_.]+)', template_content)
if_conditions = list(set(if_conditions))

all_refs = list(set(template_vars + if_conditions))
all_refs.sort()

print("=" * 80)
print("PDF TEMPLATE FIELD MAPPING VERIFICATION")
print("=" * 80)

# Group by section
sections = {}
for ref in all_refs:
    if '.' in ref:
        section, field = ref.split('.', 1)
        if section not in sections:
            sections[section] = []
        sections[section].append(field)

print(f"\nTotal template references: {len(all_refs)}")
print(f"Total sections: {len(sections)}")

# Check each section
missing_fields = []
empty_fields = []
populated_fields = []

for section_name in sorted(sections.keys()):
    print(f"\n### {section_name.upper()} ###")
    section_data = data.get(section_name, {})
    
    if not section_data:
        print(f"  ⚠️  WARNING: Section '{section_name}' not found in case data!")
        for field in sections[section_name]:
            missing_fields.append(f"{section_name}.{field}")
        continue
    
    if not isinstance(section_data, dict):
        print(f"  ℹ️  Section is not a dictionary: {type(section_data)}")
        continue
    
    for field in sorted(sections[section_name]):
        if field in section_data:
            value = section_data[field]
            if value in [None, '', [], {}, 0, 0.0, False]:
                empty_fields.append(f"{section_name}.{field}")
                print(f"  ⚪ {field}: (empty/zero/false)")
            else:
                populated_fields.append(f"{section_name}.{field}")
                # Truncate long values
                str_value = str(value)
                if len(str_value) > 50:
                    str_value = str_value[:47] + "..."
                print(f"  ✅ {field}: {str_value}")
        else:
            missing_fields.append(f"{section_name}.{field}")
            print(f"  ❌ {field}: MISSING FROM DATA")

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print(f"✅ Populated fields: {len(populated_fields)}")
print(f"⚪ Empty/Zero fields: {len(empty_fields)}")
print(f"❌ Missing fields: {len(missing_fields)}")

if missing_fields:
    print(f"\n### MISSING FIELDS ({len(missing_fields)}) ###")
    for field in missing_fields[:20]:  # Show first 20
        print(f"  - {field}")
    if len(missing_fields) > 20:
        print(f"  ... and {len(missing_fields) - 20} more")

print("\n" + "=" * 80)
