#!/usr/bin/env python
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from cases.models import Case
cases = Case.objects.all().order_by('-id').values('id', 'external_case_id', 'employee_first_name', 'employee_last_name', 'fact_finder_data')[:5]

print("Recent cases in database:")
for c in cases:
    has_data = bool(c['fact_finder_data'])
    print(f"  ID: {c['id']:3d} | External: {str(c['external_case_id']):20s} | {str(c['employee_first_name']):10s} {str(c['employee_last_name']):10s} | Has Data: {has_data}")

# Find the case with Test data
print("\nLooking for 'Test' or 'John Smith' case...")
test_case = Case.objects.filter(employee_first_name__icontains='John').first()
if test_case:
    print(f"Found: ID={test_case.id}, Name={test_case.employee_first_name} {test_case.employee_last_name}")
