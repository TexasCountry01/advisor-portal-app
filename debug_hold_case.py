#!/usr/bin/env python
"""
Debug script to check case and user data for hold functionality
"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from cases.models import Case
from accounts.models import User
from django.db.models import Q

# Find the technician
print("=" * 80)
print("TECHNICIAN WITH HOLD CASE")
print("=" * 80)

technician = User.objects.filter(username='Bene1', role='technician').first()
if technician:
    print(f"\nTechnician: {technician.get_full_name()} (ID: {technician.id})")
    print(f"Username: {technician.username}")
    print(f"User ID (from User object): {technician.id}")
    
    # Find their cases on hold
    hold_cases = Case.objects.filter(assigned_to=technician, status='hold')
    print(f"\nCases on hold assigned to this technician: {hold_cases.count()}")
    
    for case in hold_cases:
        print(f"\n  Case #{case.external_case_id} (ID: {case.id})")
        print(f"  Status: {case.status}")
        print(f"  Assigned To ID: {case.assigned_to_id}")
        print(f"  Assigned To: {case.assigned_to}")
        print(f"  Match test (case.assigned_to == technician): {case.assigned_to == technician}")
        print(f"  Match test (case.assigned_to_id == technician.id): {case.assigned_to_id == technician.id}")
        
        # Check if there's a hold record
        from cases.models import CaseHold
        holds = CaseHold.objects.filter(case=case)
        print(f"  Hold records: {holds.count()}")
        for hold in holds:
            print(f"    - Created: {hold.created_at}")
            print(f"    - Reason: {hold.reason}")
            print(f"    - Duration: {hold.duration}")
            print(f"    - By: {hold.created_by}")

print("\n" + "=" * 80)
