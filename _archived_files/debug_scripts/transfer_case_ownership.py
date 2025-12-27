import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from cases.models import Case
from accounts.models import User

# Get Case #27 and the Test user
case = Case.objects.get(id=27)
test_user = User.objects.get(username='Test')

print(f"Case #27 Current Owner: {case.member.username}")
print(f"Changing owner to: {test_user.username}")

# Transfer ownership
case.member = test_user
case.save()

print(f"\n✓ Case #27 (CASE-3D0DE689) now owned by '{test_user.username}'")
print(f"  Employee: John Michael Testman")
print(f"  You should now see it in your Member Dashboard!")
