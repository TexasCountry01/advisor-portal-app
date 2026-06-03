from django.utils import timezone


class LastActiveMiddleware:
    """
    Updates User.last_active on every authenticated staff request.
    Throttled: only writes to DB if last update was > 60 seconds ago,
    so there is at most one DB UPDATE per user per minute.
    Only tracks technician, administrator, and manager roles.
    """

    THROTTLE_SECONDS = 60
    TRACKED_ROLES = {'technician', 'administrator', 'manager'}

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        self._maybe_update_last_active(request)
        return response

    def _maybe_update_last_active(self, request):
        user = getattr(request, 'user', None)
        if user is None or not user.is_authenticated:
            return
        if getattr(user, 'role', None) not in self.TRACKED_ROLES:
            return

        now = timezone.now()
        last_active = getattr(user, 'last_active', None)

        if last_active is None or (now - last_active).total_seconds() > self.THROTTLE_SECONDS:
            # Use a targeted UPDATE to avoid touching other fields or firing model signals
            from accounts.models import User
            User.objects.filter(pk=user.pk).update(last_active=now)
