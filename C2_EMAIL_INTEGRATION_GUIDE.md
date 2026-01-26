# C2 Implementation: Email Notification Integration Points

## Summary
✅ Email service created with global toggle control
✅ 6 new email templates created
✅ Master toggle added to SystemSettings: `email_notifications_enabled`
✅ Migration created for database update

## Where to Add Email Calls

### 1. Case Accepted (in views.py or signals.py)
**When:** After case status changes to 'accepted'
**Code:**
```python
from cases.services.email_service import send_case_accepted_email
send_case_accepted_email(case)
```

### 2. Question Asked (in views.py when tech adds comment)
**When:** When technician clicks "Ask Question" 
**Code:**
```python
from cases.services.email_service import send_case_question_asked_email
question_text = request.POST.get('question_text')
send_case_question_asked_email(case, question_text)
```

### 3. Member Response (in views.py when member adds comment/uploads doc)
**When:** When member adds response to question while case is accepted
**Code:**
```python
from cases.services.email_service import send_member_response_email
send_member_response_email(case, case.assigned_to)
```

### 4. Case Resubmitted (in views.py when member resubmits)
**When:** After case status changes to 'submitted' (from 'needs_resubmission')
**Code:**
```python
from cases.services.email_service import send_case_resubmitted_email
# Send to original tech if exists, otherwise to unassigned queue
tech = case.assigned_to or None
if tech:
    send_case_resubmitted_email(case, tech)
```

### 5. New Case Assigned (in views.py or signals.py)
**When:** After technician is assigned to case
**Code:**
```python
from cases.services.email_service import send_new_case_assigned_email
send_new_case_assigned_email(case, case.assigned_to)
```

### 6. Modification Created (in views.py when member requests modification)
**When:** After modification case is created
**Code:**
```python
from cases.services.email_service import send_modification_created_email
modification_case = Case.objects.create(...)  # Create modification
send_modification_created_email(original_case, modification_case, original_case.assigned_to)
```

### 7. Hold Resumed (in views.py when tech resumes case)
**When:** After case status changes from 'hold' to 'accepted'
**Code:**
```python
from cases.services.email_service import send_case_hold_resumed_email
send_case_hold_resumed_email(case)
```

## Admin Configuration

In Django admin (`/admin/core/systemsettings/`):

- **Email Notifications Enabled** - Master toggle (on/off all emails)
- **Default Email Delay Hours** - When to send case completion emails
- **Batch Email Enabled** - Auto-send scheduled emails

## Testing

### Manual Test:
```bash
python manage.py shell

from cases.models import Case
from cases.services.email_service import send_case_accepted_email

case = Case.objects.first()
send_case_accepted_email(case)
# Check email arrives
```

### Check Email Toggle:
```bash
from core.models import SystemSettings
from cases.services.email_service import should_send_emails

settings = SystemSettings.get_settings()
print(settings.email_notifications_enabled)  # True/False
print(should_send_emails())  # True/False
```

## Files Modified/Created

- ✅ `core/models.py` - Added `email_notifications_enabled` field
- ✅ `core/migrations/0008_...py` - Migration for new field
- ✅ `cases/services/email_service.py` - Email service with toggle
- ✅ `cases/templates/emails/case_accepted_member.html` - Template
- ✅ `cases/templates/emails/case_question_asked.html` - Template
- ✅ `cases/templates/emails/case_hold_resumed.html` - Template
- ✅ `cases/templates/emails/member_response_notification.html` - Template
- ✅ `cases/templates/emails/case_resubmitted_notification.html` - Template
- ✅ `cases/templates/emails/new_case_assigned.html` - Template
- ✅ `cases/templates/emails/modification_created_notification.html` - Template

## Next Steps

1. Apply migration: `python manage.py migrate`
2. Identify view functions where emails should be sent
3. Add email function calls to each view
4. Test each email trigger
5. Create audit log tests to verify emails are being tracked

## Status
- Email service: ✅ Complete with global toggle
- Templates: ✅ Complete (7 total)
- Integration: ⏳ Ready for implementation in views
- Testing: ⏳ Pending
