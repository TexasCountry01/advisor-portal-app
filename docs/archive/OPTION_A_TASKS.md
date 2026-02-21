# OPTION A: Tasks to Complete

## C1: VERIFY/BUILD CRON JOB FOR SCHEDULED RELEASES

### Task 1.1: Check if Cron Job Exists
```bash
find . -name "*process_scheduled_releases*"
find . -name "*cron*" -o -name "*scheduled*"
```
**Outcome:** Does the file exist?

### Task 1.2: If File Exists - Check if Active
```bash
crontab -l | grep manage
ps aux | grep process_scheduled
```
**Outcome:** Is it running?

### Task 1.3: If Missing - Create Command File
**File:** `/cases/management/commands/process_scheduled_releases.py`

```python
from django.core.management.base import BaseCommand
from django.utils import timezone
from cases.models import Case, AuditLog
from django.core.mail import send_mail

class Command(BaseCommand):
    help = 'Process scheduled case releases'
    
    def handle(self, *args, **options):
        now = timezone.now()
        
        # Find cases ready for release
        cases_to_release = Case.objects.filter(
            status='completed',
            scheduled_release_date__lte=now,
            actual_release_date__isnull=True
        )
        
        for case in cases_to_release:
            # Update release status
            case.actual_release_date = now
            case.actual_email_sent_date = now
            case.save()
            
            # Send email to member
            send_member_release_email(case)
            
            # Log audit
            AuditLog.objects.create(
                case=case,
                action='case_released',
                action_by=None,
                notes='Auto-released by cron job'
            )
        
        self.stdout.write(f"Released {cases_to_release.count()} cases")
```

### Task 1.4: Add to Cron Schedule
```bash
crontab -e
# Add line:
0 3 * * * cd /path/to/project && python manage.py process_scheduled_releases
```

### Task 1.5: Test Cron Job
```bash
python manage.py process_scheduled_releases
# Should run without errors
```

**Estimate:** 2 hours (verify) or 6-8 hours (build if missing)

---

## C2: COMPLETE EMAIL NOTIFICATION CHAIN

### Task 2.1: Verify Email Settings
**File:** `settings.py`

Check these are configured:
```python
EMAIL_BACKEND = '...'
EMAIL_HOST = '...'
EMAIL_HOST_USER = '...'
EMAIL_HOST_PASSWORD = '...'
DEFAULT_FROM_EMAIL = '...'
EMAIL_PORT = ...
```

**Outcome:** Email backend working?

### Task 2.2: Test Email Send
```bash
python manage.py shell

from django.core.mail import send_mail
send_mail(
    'Test Subject',
    'Test Body',
    'from@example.com',
    ['your-email@example.com'],
    fail_silently=False,
)
```

Check if email arrives.

**Outcome:** Email sending works?

### Task 2.3: Find Email Send Points
```bash
grep -r "send_mail\|EmailMessage" cases/
```

Find all existing email sends.

### Task 2.4: Add Missing Email Signals

Check these notifications exist. Add any missing:

**Member Gets Email On:**
- [ ] Case submitted → confirmation
- [ ] Case accepted → "in progress"
- [ ] Case rejected → requirements (should already exist)
- [ ] Case on hold → reason
- [ ] Hold resumed → "continuing"
- [ ] Tech asked question → question content
- [ ] Case completed → "ready to download"
- [ ] Scheduled release → "now available" (at scheduled time)
- [ ] Modification created → "mod case #"

**Tech Gets Email On:**
- [ ] Case submitted → new case alert
- [ ] Member responded during hold → notification
- [ ] Member uploaded doc → notification
- [ ] Case resubmitted → resubmission alert
- [ ] Modification case available → mod alert

### Task 2.5: Test Email Chain
Run tests to verify:
```bash
python manage.py test test_scenarios.TestScenario1HappyPath -v 2
```

Check TODO markers in test output - each should show if email was sent.

**Estimate:** 4-6 hours

---

## C3: IMPLEMENT CASE REOPENING

### Task 3.1: Update Case Model
**File:** `cases/models.py`

Add to STATUS_CHOICES:
```python
STATUS_CHOICES = [
    ('draft', 'Draft'),
    ('submitted', 'Submitted'),
    ('needs_resubmission', 'Needs Resubmission'),
    ('accepted', 'Accepted'),
    ('hold', 'On Hold'),
    ('pending_review', 'Pending Review'),
    ('reopen_for_correction', 'Reopened for Correction'),  # NEW
    ('completed', 'Completed'),
]
```

Add fields to Case model:
```python
reopen_reason = models.TextField(blank=True)
reopened_date = models.DateTimeField(null=True, blank=True)
reopened_by = models.ForeignKey(User, null=True, related_name='reopened_cases')
```

### Task 3.2: Create Migration
```bash
python manage.py makemigrations
python manage.py migrate
```

### Task 3.3: Add Manager Button to Template
**File:** Case detail template

```django
{% if perms.cases.can_reopen and case.status == 'completed' %}
    <button class="btn btn-warning" data-toggle="modal" data-target="#reopenModal">
        Reopen for Correction
    </button>
{% endif %}
```

### Task 3.4: Create Reopen Modal
**File:** Case detail template

```django
<div class="modal" id="reopenModal">
    <div class="modal-dialog">
        <div class="modal-content">
            <div class="modal-header">
                <h4>Reopen Case for Correction</h4>
            </div>
            <form method="POST" action="{% url 'reopen_case' case.id %}">
                {% csrf_token %}
                <div class="modal-body">
                    <label>Reason for reopening:</label>
                    <textarea name="reason" class="form-control" required></textarea>
                </div>
                <div class="modal-footer">
                    <button type="submit" class="btn btn-danger">Reopen</button>
                    <button type="button" class="btn btn-secondary" data-dismiss="modal">Cancel</button>
                </div>
            </form>
        </div>
    </div>
</div>
```

### Task 3.5: Create Reopen View
**File:** `cases/views.py`

```python
@require_POST
@permission_required('cases.can_reopen')
def reopen_case(request, case_id):
    case = get_object_or_404(Case, id=case_id)
    reopen_reason = request.POST.get('reason')
    
    case.status = 'reopen_for_correction'
    case.reopen_reason = reopen_reason
    case.reopened_date = timezone.now()
    case.reopened_by = request.user
    case.save()
    
    # Notify tech
    notify_tech_case_reopened(case)
    
    # Audit
    AuditLog.objects.create(
        case=case,
        action='case_reopened',
        action_by=request.user,
        notes=reopen_reason
    )
    
    messages.success(request, 'Case reopened for correction')
    return redirect(case.get_absolute_url())
```

### Task 3.6: Add URL
**File:** `urls.py`

```python
path('case/<int:case_id>/reopen/', views.reopen_case, name='reopen_case'),
```

### Task 3.7: Create Permission
**File:** Django admin or migrations

Create permission: `cases.can_reopen`

Assign to: Manager group

### Task 3.8: Test Reopening
```bash
python manage.py test test_scenarios.TestScenario10QualityReview -v 2
```

**Estimate:** 6-8 hours

---

## H1: ADD HOLD DURATION UI OPTIONS

### Task 4.1: Update Model Field
**File:** `cases/models.py`

Verify field exists:
```python
hold_duration_days = models.IntegerField(null=True, blank=True)
```

### Task 4.2: Create Form
**File:** `cases/forms.py`

```python
class PutOnHoldForm(forms.Form):
    DURATION_CHOICES = [
        ('2h', '2 hours'),
        ('4h', '4 hours'),
        ('8h', '8 hours'),
        ('1d', '1 day'),
        ('3d', '3 days'),
        ('indefinite', 'Indefinite'),
        ('custom', 'Custom days'),
    ]
    
    hold_reason = forms.CharField(
        widget=forms.Textarea,
        label='Why is case on hold?'
    )
    duration = forms.ChoiceField(
        choices=DURATION_CHOICES,
        widget=forms.RadioSelect,
        label='Duration'
    )
    custom_days = forms.IntegerField(
        required=False,
        min_value=1,
        max_value=30,
        label='Custom duration (days)'
    )
```

### Task 4.3: Update View
**File:** `cases/views.py`

```python
def put_on_hold(request, case_id):
    form = PutOnHoldForm(request.POST)
    duration = form.cleaned_data['duration']
    
    if duration == 'indefinite':
        duration_days = None
    elif duration == 'custom':
        duration_days = form.cleaned_data['custom_days']
    else:
        duration_map = {'2h': 0.083, '4h': 0.167, '8h': 0.333, '1d': 1, '3d': 3}
        duration_days = duration_map[duration]
    
    case.hold_duration_days = duration_days
    case.hold_start_date = now()
    if duration_days:
        case.hold_end_date = now() + timedelta(days=duration_days)
    case.save()
```

### Task 4.4: Update Template
**File:** Case detail template

```django
<div class="form-group">
    <label>Hold Duration</label>
    <div class="duration-options">
        <label><input type="radio" name="duration" value="2h"> 2 hours</label>
        <label><input type="radio" name="duration" value="4h"> 4 hours</label>
        <label><input type="radio" name="duration" value="8h"> 8 hours</label>
        <label><input type="radio" name="duration" value="1d"> 1 day</label>
        <label><input type="radio" name="duration" value="indefinite" checked> Indefinite</label>
        <label><input type="radio" name="duration" value="custom"> Custom: 
            <input type="number" name="custom_days" min="1" max="30"> days
        </label>
    </div>
</div>
```

### Task 4.5: Test Hold Duration
```bash
python manage.py test test_scenarios.TestScenario3CaseHold -v 2
```

**Estimate:** 4-6 hours

---

## H2: BUILD HOLD HISTORY TRACKING

### Task 5.1: Create HoldHistory Model
**File:** `cases/models.py`

```python
class HoldHistory(models.Model):
    HOLD_ACTIONS = [
        ('placed', 'Put on Hold'),
        ('resumed', 'Resumed from Hold'),
    ]
    
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name='hold_history')
    action = models.CharField(max_length=20, choices=HOLD_ACTIONS)
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    reason = models.TextField()
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    duration_days = models.IntegerField(null=True, blank=True)
    
    class Meta:
        ordering = ['-started_at']
```

### Task 5.2: Create Migration
```bash
python manage.py makemigrations
python manage.py migrate
```

### Task 5.3: Add Helper Methods to Case Model
```python
def get_current_hold(self):
    if self.status != 'hold':
        return None
    return self.hold_history.filter(action='placed').last()

def get_hold_history(self):
    return self.hold_history.all()
```

### Task 5.4: Update Put on Hold Logic
When case put on hold, create HoldHistory entry:

```python
HoldHistory.objects.create(
    case=case,
    action='placed',
    reason=hold_reason,
    created_by=tech_user,
    duration_days=duration_days
)
```

### Task 5.5: Update Resume Logic
When case resumed, update HoldHistory:

```python
hold = case.get_current_hold()
if hold:
    hold.ended_at = timezone.now()
    hold.save()
```

### Task 5.6: Test Hold History
```bash
python manage.py test test_scenarios.TestScenario7MultipleHolds -v 2
```

**Estimate:** 4-6 hours

---

## VALIDATION & TESTING

### Task 6.1: Run All Tests
```bash
python manage.py test test_scenarios -v 2
```

All 10 should pass.

### Task 6.2: Manual Workflow Test

1. Create case as member
2. Submit case
3. Accept as tech
4. Put on hold (test new duration options)
5. Upload doc, comment
6. Resume from hold
7. Complete case
8. Schedule release
9. Verify scheduled release triggers
10. Request modification
11. Verify bidirectional linking

### Task 6.3: Email Verification

For each email sent:
- Verify arrived
- Verify content correct
- Verify timing correct (especially scheduled release)

### Task 6.4: Database Check

```bash
python manage.py dbshell
SELECT * FROM cases_case WHERE id=[test_case_id] \G
```

Verify all fields populated correctly.

**Estimate:** 2-4 hours

---

## SUMMARY

| Task | Item | Hours | Status |
|------|------|-------|--------|
| C1 | Cron Job | 2-8 | Verify first |
| C2 | Email Notifications | 4-6 | Complete chain |
| C3 | Case Reopening | 6-8 | Build feature |
| H1 | Hold Duration UI | 4-6 | Add options |
| H2 | Hold History | 4-6 | Track cycles |
| Test | Validation | 2-4 | Verify all |
| **TOTAL** | | **22-38 hours** | |

**Timeline:** 3 weeks (assuming 8-12 hours/week)

Start with C1 (quick verify or build). If missing, that's first build task. Then C2, then C3. H1 and H2 can be parallel.
