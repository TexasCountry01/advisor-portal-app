"""
Debug script to test Put on Hold functionality
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from cases.models import Case

User = get_user_model()

# List all users
print("=" * 60)
print("ALL USERS IN SYSTEM:")
print("=" * 60)
for user in User.objects.all():
    print(f"Username: {user.username}, ID: {user.id}, Role: {user.role if hasattr(user, 'role') else 'N/A'}")

# Check case 19
print("\n" + "=" * 60)
print("CASE 19 DETAILS:")
print("=" * 60)
case = Case.objects.filter(id=19).first()
if case:
    print(f"Case ID: {case.id}")
    print(f"Status: {case.status}")
    print(f"Assigned To: {case.assigned_to} (ID: {case.assigned_to.id if case.assigned_to else 'None'})")
    print(f"Member: {case.member} (ID: {case.member.id if case.member else 'None'})")
else:
    print("Case not found!")

# Try to login and check session
print("\n" + "=" * 60)
print("TESTING LOGIN:")
print("=" * 60)

from django.test import Client
from django.test.utils import override_settings

with override_settings(ALLOWED_HOSTS=['localhost', 'testserver']):
    client = Client()
    
    # Try logging in with different users
    users_to_try = ['admin', 'ProFed', 'technician']
    
    for username in users_to_try:
        user_obj = User.objects.filter(username=username).first()
        if user_obj:
            print(f"\nUser '{username}' exists:")
            print(f"  - ID: {user_obj.id}")
            print(f"  - Role: {user_obj.role if hasattr(user_obj, 'role') else 'N/A'}")
            print(f"  - Is case assigned to this user? {case.assigned_to == user_obj if case else 'N/A'}")
