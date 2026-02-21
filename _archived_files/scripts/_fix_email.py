from core.models import SystemSettings
s = SystemSettings.get_settings()
print('Current email_notifications_enabled:', s.email_notifications_enabled)
s.email_notifications_enabled = False
s.save()
print('Updated email_notifications_enabled:', s.email_notifications_enabled)