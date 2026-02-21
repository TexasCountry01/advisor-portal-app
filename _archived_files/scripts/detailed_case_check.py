#!/usr/bin/env python
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from cases.models import Case

# Find the case
case = Case.objects.get(external_case_id='WS000-2026-01-0005')

print("="*70)
print("CASE STATUS AUDIT - WS000-2026-01-0005")
print("="*70)
print()
print(f"Employee: {case.employee_first_name} {case.employee_last_name}")
print(f"Workshop: {case.workshop_code}")
print(f"Member: {case.member}")
print()
print("DATABASE STATUS:")
print(f"  Status: {case.status}")
print(f"  Assigned To: {case.assigned_to}")
print()
print("RELEASE INFORMATION:")
print(f"  Scheduled Release Date: {case.scheduled_release_date}")
print(f"  Actual Release Date: {case.actual_release_date}")
print(f"  Completion Delay Hours: {case.completion_delay_hours if hasattr(case, 'completion_delay_hours') else 'N/A'}")
print()
print("OTHER FIELDS:")
print(f"  Date Submitted: {case.date_submitted}")
print(f"  Date Due: {case.date_due}")
print(f"  Date Completed: {case.date_completed if hasattr(case, 'date_completed') else 'N/A'}")
print()
print("NOTES:")
print("- Database status is: ACCEPTED")
print("- If you see 'Completed' in case details, it's likely a caching issue")
print("- Try: Hard refresh (Ctrl+Shift+R) or clear browser cache")
print("="*70)
