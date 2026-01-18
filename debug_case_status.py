#!/usr/bin/env python
"""
Debug script to check case status and ownership for technician reassignment
"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from cases.models import Case
from accounts.models import User
from django.db.models import Count

# Find all cases assigned to benefits technicians with 'accepted' status
print("=" * 80)
print("CASES ASSIGNED TO TECHNICIANS WITH 'ACCEPTED' STATUS")
print("=" * 80)

technicians = User.objects.filter(role='technician', is_active=True)
print(f"\nFound {technicians.count()} active technicians:\n")

for tech in technicians:
    print(f"  - {tech.get_full_name()} (ID: {tech.id}, Username: {tech.username})")
    
    # Find their cases with 'accepted' status
    owned_cases = Case.objects.filter(assigned_to=tech, status='accepted')
    print(f"    Cases with 'accepted' status: {owned_cases.count()}")
    
    for case in owned_cases:
        print(f"      - Case #{case.external_case_id} (ID: {case.id}, Status: {case.status})")
        print(f"        Member: {case.member_name if hasattr(case, 'member_name') else 'N/A'}")

print("\n" + "=" * 80)
print("ALL ACTIVE CASES WITH STATUS BREAKDOWN")
print("=" * 80)

from django.db.models import Count

status_breakdown = Case.objects.values('status').annotate(count=Count('id'))
for item in status_breakdown:
    print(f"  {item['status']:20s}: {item['count']:3d} cases")

print("\n" + "=" * 80)
print("RECENT TECHNICIAN CASES (LAST 10)")
print("=" * 80)

for tech in technicians:
    recent_cases = Case.objects.filter(assigned_to=tech).order_by('-created_at')[:5]
    if recent_cases.exists():
        print(f"\n{tech.get_full_name()}:")
        for case in recent_cases:
            print(f"  - Case #{case.external_case_id}: Status={case.status}, Created={case.created_at.strftime('%Y-%m-%d %H:%M')}")
