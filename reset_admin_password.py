import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from accounts.models import User

# Reset Admin1's password
admin = User.objects.get(username='Admin1')
admin.set_password('admin123')
admin.save()
print("✅ Password reset successful!")
print(f"Username: Admin1")
print(f"Password: admin123")
