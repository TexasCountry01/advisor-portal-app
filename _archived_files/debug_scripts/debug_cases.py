import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from cases.models import Case
from accounts.models import User

# Check Test user's cases
test_user = User.objects.get(username='Test')
print(f"User: {test_user.username} (role: {test_user.role})")
print(f"\nCases owned by Test:")
for case in Case.objects.filter(member=test_user).order_by('id'):
    print(f"  Case #{case.id}: {case.external_case_id}")
    print(f"    Employee: {case.employee_first_name} {case.employee_last_name}")
    print(f"    Status: {case.status}")
    print(f"    Created: {case.created_at}")
    print()

# Check if Case #27 exists
print("="*50)
case27 = Case.objects.filter(id=27).first()
if case27:
    print(f"Case #27 EXISTS:")
    print(f"  External ID: {case27.external_case_id}")
    print(f"  Owner: {case27.member.username}")
    print(f"  Employee First: '{case27.employee_first_name}'")
    print(f"  Employee Last: '{case27.employee_last_name}'")
    print(f"  Status: {case27.status}")
else:
    print("Case #27 DOES NOT EXIST in database")

# Check all cases
print("\n" + "="*50)
print("ALL CASES IN DATABASE:")
for case in Case.objects.all().order_by('id'):
    print(f"  #{case.id}: {case.external_case_id} - {case.employee_first_name} {case.employee_last_name} - Owner: {case.member.username}")
