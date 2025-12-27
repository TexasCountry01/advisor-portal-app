import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from accounts.models import User

# Update Test user role
user = User.objects.get(username='Test')
print(f"Current role: {user.role}")
user.role = 'advisor'
user.save()
print(f"Updated role: {user.role}")
print("\nUser 'Test' is now an advisor!")
