import os
import django
import re

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from cases.models import Case

print("="*100)
print("COMPLETE NOTES FIELDS AUDIT - ALL SECTIONS")
print("="*100)

# Get Case #28 to check what's actually saved
case = Case.objects.get(id=28)
data = case.fact_finder_data or {}

# Define every notes field we expect based on the form structure
all_notes_fields = {
    'FEGLI': {
        'section': 'fegli',
        'field': 'notes',
        'form_name': 'fegli_notes',
        'expected_in_form': True
    },
    'FEHB': {
        'section': 'fehb',
        'field': 'notes',
        'form_name': 'fehb_notes',
        'expected_in_form': True
    },
    'FLTCIP': {
        'section': 'fltcip',
        'field': 'notes',
        'form_name': 'fltcip_notes',
        'expected_in_form': True
    },
    'TSP': {
        'section': 'tsp',
        'field': 'comments',  # Note: TSP uses 'comments' not 'notes'
        'form_name': 'tsp_comments',
        'expected_in_form': True
    },
    'ADDITIONAL NOTES': {
        'section': 'add_info',
        'field': 'additional_notes',
        'form_name': 'additional_notes',
        'expected_in_form': True
    },
    'Military Service (MAD)': {
        'section': 'mad',
        'field': 'notes',
        'form_name': 'mad_notes',
        'expected_in_form': True
    },
    'Reserves/Guard': {
        'section': 'reserves',
        'field': 'notes',
        'form_name': 'reserves_notes',
        'expected_in_form': True
    },
    'Academy Service': {
        'section': 'academy',
        'field': 'notes',
        'form_name': 'academy_notes',
        'expected_in_form': True
    },
    'Non-Deduction Service': {
        'section': 'non_deduction',
        'field': 'notes',
        'form_name': 'non_deduction_notes',
        'expected_in_form': True
    },
    'Break in Service': {
        'section': 'break_service',
        'field': 'notes',
        'form_name': 'break_service_notes',
        'expected_in_form': True
    },
    'Part-Time Service': {
        'section': 'part_time',
        'field': 'notes',
        'form_name': 'part_time_notes',
        'expected_in_form': True
    },
    'Retirement/Pay/Leave': {
        'section': 'retirement_pay_leave',
        'field': 'notes',
        'form_name': 'retirement_notes',
        'expected_in_form': True
    },
    'Add\'l Info - Page 1 Notes': {
        'section': 'add_info',
        'field': 'page1_notes',
        'form_name': 'page1_notes',
        'expected_in_form': True
    },
    'Add\'l Info - Other Details': {
        'section': 'add_info',
        'field': 'other_pertinent_details',
        'form_name': 'other_pertinent_details',
        'expected_in_form': True
    },
}

print("\n" + "="*100)
print("NOTES FIELD INVENTORY")
print("="*100)

populated = 0
missing = 0
empty = 0

for name, info in sorted(all_notes_fields.items()):
    section_data = data.get(info['section'], {})
    value = section_data.get(info['field'], 'MISSING')
    
    print(f"\n{name}:")
    print(f"  Database path: data['{info['section']}']['{info['field']}']")
    print(f"  Form field name: {info['form_name']}")
    print(f"  Value in DB: {repr(value)[:80]}")
    
    if value == 'MISSING':
        print(f"  Status: ❌ NOT IN DATABASE")
        missing += 1
    elif value == '' or value is None:
        print(f"  Status: ⚠️  EMPTY")
        empty += 1
    else:
        print(f"  Status: ✅ POPULATED")
        populated += 1

print("\n" + "="*100)
print("SUMMARY STATISTICS")
print("="*100)
print(f"Total notes fields expected: {len(all_notes_fields)}")
print(f"Populated with data:         {populated}")
print(f"Empty (blank):               {empty}")
print(f"Missing from DB:             {missing}")
print(f"Success rate:                {populated}/{len(all_notes_fields)} = {100*populated//len(all_notes_fields)}%")

print("\n" + "="*100)
print("WHY COMPREHENSIVE TESTING IS DIFFICULT")
print("="*100)

difficulties = """
1. INCONSISTENT FIELD NAMING:
   - Some fields use 'notes' (FEGLI, FEHB, FLTCIP, MAD, reserves, etc.)
   - TSP uses 'comments' instead of 'notes'
   - Additional notes uses 'additional_notes'
   - Add_info has 'page1_notes' and 'other_pertinent_details'
   
   Problem: No consistent pattern. Must manually map each section.

2. NESTED JSON STRUCTURE:
   - FEGLI notes: data['fegli']['notes']
   - TSP notes: data['tsp']['comments']
   - Additional notes: data['add_info']['additional_notes']
   
   Problem: Different sections use different key names. Hard to iterate programmatically.

3. FORM FIELD NAME VARIATIONS:
   - Military service form field: 'mad_notes' (but section is 'mad')
   - Reserves form field: 'reserves_notes' (but section is 'reserves')
   - Academy form field: 'academy_notes' (but section is 'academy')
   
   Problem: Form field names don't always match section names. Must explicitly map each one.

4. OPTIONAL VS REQUIRED FIELDS:
   - Some notes are required in the form
   - Some are optional
   - Some don't appear on certain form versions
   
   Problem: Can't assume all fields exist in all cases.

5. PDF TEMPLATE INCONSISTENCY:
   - Some notes use {{ section.notes }}
   - Some use {{ section.comments }}
   - Some use complex custom paths
   
   Problem: Can't create a generic template. Each section needs custom handling.

6. CHECKBOX GROUPS:
   - Y/N/Unsure checkboxes use: fieldname_yes, fieldname_no, fieldname_unsure
   - But database stores: 'Yes', 'No', or 'Unsure'
   - No standard way to know which checkboxes go with which field
   
   Problem: Must manually identify checkbox groups and conversion logic for each.

7. FORM EVOLUTION:
   - New sections added over time
   - Old sections renamed
   - Field names change between versions
   
   Problem: Test script breaks when form changes. No version tracking.

8. NO SCHEMA DEFINITION:
   - Form HTML is the source of truth (not documented)
   - views.py does the mapping (hidden from form)
   - Database schema (FederalFactFinder model) doesn't match JSON structure
   
   Problem: Three different representations of the same data. Hard to keep synchronized.

SOLUTION RECOMMENDATIONS:
"""

print(difficulties)

print("\n" + "="*100)
print("PROPOSED FIX: Create Form Schema Definition")
print("="*100)

schema_example = """
Instead of manually testing each field, create a SCHEMA file that defines:

forms/schema.json:
{
  "fegli": {
    "premiums": ["premium_1", "premium_2", "premium_3", "premium_4"],
    "yes_no_unsure": [
      {"field": "five_year_requirement", "form_names": ["fegli_5yr_yes", "fegli_5yr_no", "fegli_5yr_unsure"]},
      {"field": "keep_in_retirement", "form_names": ["fegli_keep_yes", "fegli_keep_no", "fegli_keep_unsure"]}
    ],
    "notes": "fegli_notes"
  },
  "fehb": {
    "currencies": ["health_premium", "dental_premium", "vision_premium", "dental_vision_premium"],
    "checkboxes": ["coverage_self_only", "coverage_self_one", ...],
    "yes_no_unsure": [
      {"field": "five_year_requirement", "form_names": ["fehb_health_5yr_yes", ...]},
      ...
    ],
    "notes": "fehb_notes"
  },
  ...
}

Then test script can:
1. Loop through schema
2. For each field, check if it exists in database
3. For each form_name, check if it would be submitted
4. Verify checkbox conversions
5. Validate field types (currency, yes/no/unsure, etc.)
"""

print(schema_example)
