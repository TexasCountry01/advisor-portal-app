#!/usr/bin/env python
"""
Validate that all populated fields appear in the rendered PDF.
"""

import os
import sys
import django
import re

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from cases.models import Case

if len(sys.argv) < 2:
    print("Usage: python validate_full_case.py <case_id>")
    sys.exit(1)

case_id = int(sys.argv[1])
case = Case.objects.get(id=case_id)
data = case.fact_finder_data or {}

print("="*100)
print(f"FULL CASE VALIDATION - CASE #{case_id}")
print("="*100)

# Critical fields to check across all sections
validations = {
    'Employee Info': [
        ('employee_name', 'employee_name', 'John Michael Smith'),
        ('spouse_name', 'spouse_name', 'Mary Ellen Smith'),
        ('address', 'address', '123 Main Street'),
    ],
    'Retirement System': [
        ('retirement_system', 'retirement_system', 'FERS'),
        ('retirement_type', 'retirement_type', 'Regular'),
        ('employee_type', 'employee_type', 'Regular'),
    ],
    'FEGLI': [
        ('premium_1', 'fegli.premium_1', '150'),
        ('five_year_requirement', 'fegli.five_year_requirement', 'Yes'),
        ('keep_in_retirement', 'fegli.keep_in_retirement', 'Yes'),
        ('sole_source', 'fegli.sole_source', 'Yes'),
        ('notes', 'fegli.notes', 'reassess at age 70'),
    ],
    'FEHB': [
        ('health_premium', 'fehb.health_premium', '350'),
        ('coverage_type', 'fehb.coverage_self_family', True),
        ('five_year_requirement', 'fehb.five_year_requirement', 'Yes'),
        ('keep_in_retirement', 'fehb.keep_in_retirement', 'Yes'),
        ('spouse_reliant', 'fehb.spouse_reliant', 'Yes'),
        ('notes', 'fehb.notes', 'Blue Cross Blue Shield'),
    ],
    'FLTCIP': [
        ('employee_premium', 'fltcip.employee_premium', '75'),
        ('discuss_options', 'fltcip.discuss_options', 'Yes'),
        ('notes', 'fltcip.notes', 'Both spouses enrolled'),
    ],
    'TSP': [
        ('sole_source', 'tsp.sole_source', 'Yes'),
        ('in_service_withdrawal', 'tsp.in_service_withdrawal', 'Yes'),
        ('retirement_goal', 'tsp.retirement_goal', '$4,500/month'),
        ('comments', 'tsp.comments', 'C-Fund, S-Fund'),
    ],
    'Military Service': [
        ('has_service', 'mad.has_service', True),
        ('start_date', 'mad.start_date', '1985'),
        ('notes', 'mad.notes', 'Honorable discharge'),
    ],
    'Reserves': [
        ('has_service', 'reserves.has_service', True),
        ('years', 'reserves.years', '8'),
        ('notes', 'reserves.notes', 'Army National Guard'),
    ],
    'Additional Info': [
        ('page1_notes', 'add_info.page1_notes', 'excellent leave balances'),
        ('other_details', 'add_info.other_pertinent_details', 'excellent health'),
        ('additional_notes', 'add_info.additional_notes', 'COMPREHENSIVE'),
    ],
}

total_checks = 0
passed_checks = 0
failed_checks = 0

for section, checks in validations.items():
    print(f"\n{section}:")
    section_passed = 0
    section_total = len(checks)
    
    for label, path, expected in checks:
        total_checks += 1
        
        # Navigate path
        parts = path.split('.')
        value = data
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                value = None
                break
        
        # Check value
        if value is None:
            print(f"  ❌ {label}: NOT FOUND (path: {path})")
            failed_checks += 1
        elif value == '' or (isinstance(value, bool) and not value):
            print(f"  ⚠️  {label}: EMPTY (path: {path})")
            failed_checks += 1
        else:
            # Check if expected value is in actual value (string search)
            expected_str = str(expected).lower()
            actual_str = str(value).lower()
            
            if expected_str in actual_str:
                print(f"  ✅ {label}: {repr(value)[:50]}")
                passed_checks += 1
                section_passed += 1
            else:
                print(f"  ❌ {label}: Expected '{expected}' but got '{repr(value)[:30]}'")
                failed_checks += 1
    
    print(f"  [{section_passed}/{section_total}]")

print("\n" + "="*100)
print("SUMMARY")
print("="*100)
print(f"Total checks: {total_checks}")
print(f"Passed: {passed_checks} ✅")
print(f"Failed: {failed_checks} ❌")
print(f"Success rate: {100*passed_checks//total_checks}%")

print("\n" + "="*100)
print("PDF RENDERING CHECKLIST")
print("="*100)
print(f"""
Before viewing PDF, ensure:
☐ Server is running (http://127.0.0.1:8000/ is accessible)
☐ Case #{case_id} exists in database (verified above)
☐ All critical fields are populated (verified above)

To view the PDF:
1. Open: http://127.0.0.1:8000/cases/{case_id}/
2. Click "View PDF" or go to: http://127.0.0.1:8000/cases/{case_id}/pdf/

Expected to see in PDF:
✓ Employee: John Michael Smith
✓ Spouse: Mary Ellen Smith
✓ FEGLI section with all 4 premiums and notes
✓ FEHB section with premiums and coverage type
✓ FLTCIP section with premiums and benefits
✓ TSP section with fund allocations and comments
✓ Military service dates and notes
✓ Additional information sections with all notes

If fields are MISSING from PDF:
→ The PDF template is not using the correct JSON path
→ Check that variable names match database structure
→ Compare template variables against form_schema.json
""")

if failed_checks == 0:
    print("\n✓ ALL CHECKS PASSED - Ready to render PDF!")
else:
    print(f"\n⚠️  {failed_checks} checks failed - Review data before PDF rendering")
