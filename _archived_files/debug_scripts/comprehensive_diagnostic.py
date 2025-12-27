import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from cases.models import Case

# Get Case #27
case = Case.objects.get(id=27)
data = case.fact_finder_data or {}

print("="*90)
print("COMPREHENSIVE FORM-TO-DATABASE-TO-PDF DIAGNOSTIC")
print("="*90)

# Critical fields that MUST be there
critical_fields = {
    'FEHB Y/N/Unsure Checkboxes': {
        'section': 'fehb',
        'fields': [
            ('five_year_requirement', 'Should be: Yes/No/Unsure'),
            ('keep_in_retirement', 'Should be: Yes/No/Unsure'),
            ('spouse_reliant', 'Should be: Yes/No/Unsure'),
        ]
    },
    'FLTCIP': {
        'section': 'fltcip',
        'fields': [
            ('discuss_options', 'Should be: Yes/No/Unsure'),
        ]
    },
    'TSP Questions': {
        'section': 'tsp',
        'fields': [
            ('sole_source', 'Should be: Yes/No (checkbox value)'),
            ('in_service_withdrawal', 'Should be: Yes/No (checkbox value)'),
            ('employee_risk_tolerance', 'Should be: Conservative/Moderate/Aggressive'),
            ('spouse_risk_tolerance', 'Should be: Conservative/Moderate/Aggressive'),
        ]
    },
    'FEGLI': {
        'section': 'fegli',
        'fields': [
            ('premium_1', 'Should be: currency value'),
            ('premium_2', 'Should be: currency value'),
            ('premium_3', 'Should be: currency value'),
            ('premium_4', 'Should be: currency value'),
            ('five_year_requirement', 'Should be: Yes/No/Unsure'),
            ('keep_in_retirement', 'Should be: Yes/No/Unsure'),
        ]
    }
}

print("\n" + "="*90)
print("CHECKING CRITICAL MISSING FIELDS:")
print("="*90)

missing_count = 0
for category, info in critical_fields.items():
    section_data = data.get(info['section'], {})
    print(f"\n{category} (section: {info['section']}):")
    print("-" * 90)
    
    for field_name, expected_format in info['fields']:
        actual_value = section_data.get(field_name, 'MISSING')
        
        if actual_value == 'MISSING' or actual_value == '' or actual_value is None:
            print(f"  ✗ {field_name}")
            print(f"    Expected: {expected_format}")
            print(f"    Actual: {repr(actual_value)}")
            print(f"    Status: NOT IN DATABASE - Form didn't submit or views.py didn't capture")
            missing_count += 1
        else:
            print(f"  ✓ {field_name}: {repr(actual_value)}")

print("\n" + "="*90)
print(f"SUMMARY: {missing_count} critical fields missing from database")
print("="*90)

print("\nNEXT STEPS TO DIAGNOSE:")
print("-" * 90)
print("1. CHECK WEBFORM:")
print("   - Open the Federal Fact Finder form")
print("   - Find the FEHB section (Y/N/Unsure checkboxes)")
print("   - Check browser Developer Tools (F12) → Network tab")
print("   - Submit the form and look at the POST request payload")
print("   - Search for: 'fehb_five_year_requirement', 'kehb_keep_in_retirement', etc.")
print("   - Do these fields appear in the form submission?")
print()
print("2. CHECK VIEWS.PY MAPPING:")
print("   - Look at lines where these fields are captured in case_submit()")
print("   - Example: request.POST.get('fehb_five_year_requirement')")
print("   - Are the field names in views.py matching the form's field names?")
print()
print("3. FORM VS VIEWS MISMATCH:")
print("   - Form field name: name='fehb_five_year_requirement'")
print("   - Views.py capture: request.POST.get('fehb_five_year_requirement')")
print("   - These MUST match exactly (case-sensitive)")
print()
print("4. COMMON ISSUES:")
print("   - Checkbox fields send 'on' if checked, nothing if unchecked")
print("   - Radio buttons need proper name/value attributes")
print("   - Y/N/Unsure groups need unique field names (radio name must be different for each group)")
print()
print("="*90)
print("ACTION ITEMS:")
print("="*90)
print("A) Check form HTML field names")
print("B) Check views.py request.POST.get() calls")
print("C) Verify they match exactly")
print("D) Re-run test_complete_form.py with debug output")
print("="*90)
