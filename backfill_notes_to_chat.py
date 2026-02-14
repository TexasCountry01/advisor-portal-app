"""
Backfill: Add special_notes as first chat message for existing cases.
Only adds a message if special_notes exists and no messages exist yet.
"""
import os, sys, django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from cases.models import Case, CaseMessage

cases_with_notes = Case.objects.exclude(special_notes__isnull=True).exclude(special_notes='')
print(f'Cases with special_notes: {cases_with_notes.count()}')

backfilled = 0
for c in cases_with_notes:
    msg_count = CaseMessage.objects.filter(case=c).count()
    has_note_msg = CaseMessage.objects.filter(case=c, message=c.special_notes.strip()).exists()
    print(f'  {c.external_case_id} | {c.employee_first_name} {c.employee_last_name} | msgs={msg_count} | already_has_note_msg={has_note_msg} | notes={repr(c.special_notes[:60])}')
    
    if not has_note_msg and c.member:
        CaseMessage.objects.create(
            case=c,
            author=c.member,
            message=c.special_notes.strip()
        )
        # Backdate to submission time if available
        if c.date_submitted:
            CaseMessage.objects.filter(case=c, message=c.special_notes.strip()).update(created_at=c.date_submitted)
        backfilled += 1
        print(f'    -> Created chat message (backdated to {c.date_submitted})')

print(f'\nBackfilled {backfilled} cases.')
