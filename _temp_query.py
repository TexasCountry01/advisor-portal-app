import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from cases.models import Case, UnreadMessage
for c in Case.objects.filter(status__in=['cancelled','declined'])[:10]:
    ums = list(UnreadMessage.objects.filter(case=c).values_list('user__username','user__role'))
    if ums:
        print(c.external_case_id, c.status, ums)
