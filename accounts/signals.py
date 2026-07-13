from django.contrib.auth.signals import user_logged_out
from django.dispatch import receiver


@receiver(user_logged_out)
def clear_last_active_on_logout(sender, request, user, **kwargs):
    """
    Clear last_active when a user explicitly logs out so their status
    dot goes grey immediately instead of waiting for the 30-minute timeout.
    """
    if user is None:
        return
    if getattr(user, 'role', None) not in ('technician', 'administrator', 'manager'):
        return
    from accounts.models import User
    User.objects.filter(pk=user.pk).update(last_active=None)
