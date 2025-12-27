"""
Complete field mapping verification - compares clean form fields against views.py
"""
import re

# Read clean form fields
with open('clean_form_fields.txt', 'r', encoding='utf-8') as f:
    form_fields = [line.strip() for line in f if line.strip()]

# Remove array notation for comparison
form_fields_clean = [f.replace('[]', '') for f in form_fields]

# Read views.py to find all request.POST.get() calls
with open('cases/views.py', 'r', encoding='utf-8') as f:
    views_content = f.read()

# Extract all field names from request.POST.get() calls
post_get_pattern = r"request\.POST\.get\(['\"]([^'\"]+)['\"]"
captured_fields = re.findall(post_get_pattern, views_content)
captured_fields_set = set(captured_fields)

# Find missing fields
form_fields_set = set(form_fields_clean)
missing_fields = form_fields_set - captured_fields_set
extra_fields = captured_fields_set - form_fields_set

print(f"=== FIELD MAPPING ANALYSIS ===\n")
print(f"Total form fields: {len(form_fields_clean)}")
print(f"Fields captured in views.py: {len(captured_fields_set)}")
print(f"Missing fields: {len(missing_fields)}")
print(f"Extra fields (in views but not form): {len(extra_fields)}")

if missing_fields:
    print(f"\n=== MISSING FIELDS ({len(missing_fields)}) ===")
    for field in sorted(missing_fields):
        print(f"  - {field}")

if extra_fields:
    print(f"\n=== EXTRA FIELDS ({len(extra_fields)}) ===")
    for field in sorted(extra_fields):
        print(f"  - {field}")

# Group missing fields by prefix
if missing_fields:
    print(f"\n=== MISSING FIELDS BY SECTION ===")
    sections = {}
    for field in missing_fields:
        if '_' in field:
            prefix = field.split('_')[0]
        else:
            prefix = 'other'
        
        if prefix not in sections:
            sections[prefix] = []
        sections[prefix].append(field)
    
    for section, fields in sorted(sections.items()):
        print(f"\n{section.upper()} ({len(fields)} fields):")
        for field in sorted(fields):
            print(f"  - {field}")

# Calculate completion percentage
completion_pct = (len(captured_fields_set) / len(form_fields_clean)) * 100
print(f"\n=== COMPLETION ===")
print(f"Field capture completion: {completion_pct:.1f}%")
print(f"Fields to add: {len(missing_fields)}")
