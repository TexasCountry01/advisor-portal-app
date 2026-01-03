#!/usr/bin/env python
"""Validate Manager Dashboard statistics"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from cases.models import Case
from accounts.models import User

# Get all the statistics
all_cases = Case.objects.all()
total_cases = all_cases.count()
completed_cases = all_cases.filter(status='completed').count()
pending_review_cases = all_cases.filter(status='pending_review').count()

active_members = User.objects.filter(role='member', is_active=True).count()
active_technicians = User.objects.filter(role='technician', is_active=True).count()

completion_rate = round((completed_cases / total_cases * 100) if total_cases > 0 else 0, 1)

print("=" * 60)
print("MANAGER DASHBOARD STATISTICS VALIDATION")
print("=" * 60)
print(f"Total Cases:              {total_cases}")
print(f"Completed:                {completed_cases}")
print(f"Completion Rate:          {completion_rate}%")
print(f"Pending Review:           {pending_review_cases}")
print(f"Active Members:           {active_members}")
print(f"Active Technicians:       {active_technicians}")
print("=" * 60)

# Show breakdown by status
print("\nCases by Status:")
print("-" * 60)
for status in ['draft', 'submitted', 'accepted', 'hold', 'pending_review', 'completed']:
    count = all_cases.filter(status=status).count()
    print(f"  {status:20} {count}")

print("\n" + "=" * 60)
