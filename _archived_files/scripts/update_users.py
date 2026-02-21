#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'advisor_portal.settings')
django.setup()

from accounts.models import User

# Update Ben1 user
try:
    ben1 = User.objects.get(username='Ben1')
    ben1.role = 'technician'
    ben1.user_level = 'level_1'
    ben1.save()
    print(f"✓ Updated Ben1: role={ben1.role}, level={ben1.user_level}")
except User.DoesNotExist:
    print("✗ Ben1 user not found. Creating Ben1...")
    ben1 = User.objects.create_user(
        username='Ben1',
        password='Ben1',
        first_name='Ben',
        last_name='Technician',
        email='ben1@example.com',
        role='technician',
        user_level='level_1'
    )
    print(f"✓ Created Ben1: role={ben1.role}, level={ben1.user_level}")

# Verify other test users exist with correct roles
test_users = {
    'Member1': ('member', None),
    'Manager1': ('manager', None),
    'Admin1': ('administrator', None),
}

for username, (role, level) in test_users.items():
    try:
        user = User.objects.get(username=username)
        if user.role != role:
            user.role = role
            user.save()
            print(f"✓ Updated {username}: role={user.role}")
        else:
            print(f"✓ {username} already has role={user.role}")
    except User.DoesNotExist:
        user = User.objects.create_user(
            username=username,
            password=username,
            first_name=username.replace('1', ''),
            last_name='User',
            email=f'{username.lower()}@example.com',
            role=role,
        )
        print(f"✓ Created {username}: role={user.role}")

print("\nAll test users verified!")
