#!/bin/bash
cd /home/dev/advisor-portal-app
/usr/bin/python3 manage.py shell << 'DJANGO_EOF'
from accounts.models import User
from cases.models import Case

# Update Ben1
try:
    ben1 = User.objects.get(username='Ben1')
    ben1.role = 'technician'
    ben1.user_level = 'level_1'
    ben1.save()
    print("Updated Ben1: role=technician, level=level_1")
except User.DoesNotExist:
    ben1 = User.objects.create_user(
        username='Ben1',
        password='Ben1',
        first_name='Ben',
        last_name='Technician',
        email='ben1@example.com',
        role='technician',
        user_level='level_1'
    )
    print("Created Ben1: role=technician, level=level_1")

# Verify other users
for username, role in [('Member1', 'member'), ('Manager1', 'manager'), ('Admin1', 'administrator')]:
    try:
        user = User.objects.get(username=username)
        if user.role != role:
            user.role = role
            user.save()
            print(f"Updated {username}: role={role}")
    except User.DoesNotExist:
        user = User.objects.create_user(username=username, password=username, role=role)
        print(f"Created {username}: role={role}")

# Create test case for technician dashboard
try:
    member1 = User.objects.get(username='Member1')
    case = Case.objects.create(
        external_case_id='TECHTEST-001',
        workshop_code='WS-001',
        member=member1,
        employee_first_name='Jane',
        employee_last_name='Smith',
        client_email='jane.smith@example.com',
        num_reports_requested=2,
        urgency='rush',
        status='accepted',
        assigned_to=ben1,
        tier='tier_1'
    )
    print("Created test case TECHTEST-001 assigned to Ben1")
except Exception as e:
    print(f"Test case already exists or error: {e}")

print("All test server setup complete!")
DJANGO_EOF
