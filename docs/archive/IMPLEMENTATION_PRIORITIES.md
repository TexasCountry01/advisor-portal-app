# Implementation Priorities - Case Processing Workflows

## Executive Summary

Based on comprehensive analysis of 10 case processing scenarios, the advisor portal is **~65% complete** with core functionality working well, but has **8 critical/high-priority gaps** blocking full workflow implementation.

**Critical Path:** Cron job verification → Email notifications → Hold duration UI → Case reopening

**Estimated Effort:** 40-60 hours to address all priorities

---

## PRIORITY MATRIX

### 🔴 TIER 1: CRITICAL (Week 1)

These gaps completely block workflow functionality and must be fixed first.

| # | Feature | Current | Needed | Impact | Effort | Scenarios | Status |
|---|---------|---------|--------|--------|--------|-----------|--------|
| **C1** | **Cron Job for Scheduled Releases** | ❌ UNKNOWN | Verify/Build | Scheduled releases don't work | 2-8h | S5 | 🔴 BLOCKER |
| **C2** | **Email Notifications** | ⚠️ PARTIAL | Complete chain | Workflow depends on emails | 4-6h | S1,S2,S3,S4,S9 | 🔴 BLOCKER |
| **C3** | **Case Reopening** | ❌ MISSING | Build feature | Can't fix errors after completion | 6-8h | S10 | 🔴 BLOCKER |

**Total Tier 1: 12-22 hours**

---

### 🟠 TIER 2: HIGH (Week 1-2)

High-impact features that degrade UX or workflow efficiency.

| # | Feature | Current | Needed | Impact | Effort | Scenarios | Status |
|---|---------|---------|--------|--------|--------|-----------|--------|
| **H1** | **Hold Duration Options UI** | ⚠️ PARTIAL | Add time options | Tech limited to indefinite holds | 4-6h | S3,S7 | 🟠 HIGH |
| **H2** | **Hold History Tracking** | ❌ MISSING | Build tracking | Multiple holds overwrite data | 4-6h | S7 | 🟠 HIGH |
| **H3** | **Hold History Visibility** | ❌ MISSING | UI display | Members/tech can't see hold pattern | 2-3h | S3,S7 | 🟠 HIGH |
| **H4** | **Manager Review Workflow** | ⚠️ UNCLEAR | Clarify/Implement | Review process not fully defined | 2-4h | S10 | 🟠 HIGH |

**Total Tier 2: 12-19 hours**

---

### 🟡 TIER 3: MEDIUM (Week 2-3)

Medium-priority improvements that enhance UX but don't block workflows.

| # | Feature | Current | Needed | Impact | Effort | Scenarios | Status |
|---|---------|---------|--------|--------|--------|-----------|--------|
| **M1** | **Column Visibility Persistence** | ⚠️ PARTIAL | Add storage | Dashboard preferences reset on logout | 2-4h | Multiple | 🟡 MEDIUM |
| **M2** | **Hold Duration Countdown** | ❌ MISSING | Add timer | Members don't see when hold expires | 2-3h | S3,S7 | 🟡 MEDIUM |
| **M3** | **Modification Case Visibility** | ⚠️ PARTIAL | Enhance linking | Could improve case comparison UI | 2-3h | S6 | 🟡 MEDIUM |
| **M4** | **Communication Clarity** | ⚠️ PARTIAL | Improve UX | Multiple hold notifications confusing | 1-2h | S7 | 🟡 MEDIUM |

**Total Tier 3: 7-12 hours**

---

### 🟢 TIER 4: LOW (Week 3+)

Low-priority enhancements that are nice-to-have but not required.

| # | Feature | Current | Needed | Impact | Effort | Scenarios | Status |
|---|---------|---------|--------|--------|--------|-----------|--------|
| **L1** | **Reassignment Notifications** | ⚠️ UNCLEAR | Verify/enhance | Clarity on who gets notified | 1-2h | S4 | 🟢 LOW |
| **L2** | **Quality Review Email** | ⚠️ UNCLEAR | Verify/implement | Tech nice-to-know feedback | 1h | S10 | 🟢 LOW |
| **L3** | **Dashboard Analytics** | ❌ MISSING | Optional | Nice-to-have metrics | 4-6h | Multiple | 🟢 LOW |

**Total Tier 4: 6-9 hours**

---

## DETAILED SPECIFICATIONS

### 🔴 C1: CRON JOB FOR SCHEDULED RELEASES (CRITICAL)

**Status:** ❌ **UNKNOWN - Verify immediately**

**Problem:**
- Scheduled case releases completely depend on cron job
- When tech schedules release (e.g., "Tomorrow 9 AM"), system needs cron job to:
  1. Find cases with `scheduled_release_date <= now()`
  2. Update `actual_release_date = now()`
  3. Send email to member
  4. Log audit trail

**Verification Steps:**
1. Check if file exists: `/cases/management/commands/process_scheduled_releases.py`
2. Check if cron job is configured in system
3. Check if cron job is running (check logs)

**Current Implementation:**
```
python manage.py process_scheduled_releases  # Does this exist?
```

**If Missing - Build:**

```python
# cases/management/commands/process_scheduled_releases.py

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
                action_by=None,  # System action
                notes=f'Auto-released by cron job'
            )
        
        self.stdout.write(
            f"Released {cases_to_release.count()} cases"
        )
```

**Cron Schedule:**
```bash
# In crontab: Run daily at 3 AM CST
0 3 * * * cd /path/to/project && python manage.py process_scheduled_releases
```

**Verification After Implementation:**
- [ ] Cron job runs daily
- [ ] Scheduled releases process correctly
- [ ] Member receives email at exact scheduled time
- [ ] Audit trail captures release action
- [ ] Scenario 5 test passes

**Effort:** 2 hours to verify, 6-8 hours to build if missing
**Priority:** 🔴 **CRITICAL**

---

### 🔴 C2: EMAIL NOTIFICATIONS (CRITICAL)

**Status:** ⚠️ **Partial - Many paths unclear**

**Problem:**
Email notifications are critical to case workflow but several paths are not clearly implemented:
- Does member get email when tech asks question?
- Does tech get email when member responds during hold?
- Does tech get email when case resubmitted?
- Does admin get email on reassignments?

**Current Implementation Status:**

| Notification | Current | Status |
|--------------|---------|--------|
| Case submitted | ⚠️ | Unclear if member gets email |
| Case accepted | ⚠️ | Unclear if member gets email |
| Case rejected | ✅ | Email sent with requirements |
| Case resubmitted | ⚠️ | Unclear if tech gets email |
| Put on hold | ✅ | Email sent to member |
| Resumed from hold | ✅ | Email sent to member |
| Public comment (tech) | ⚠️ | Unclear if member gets email |
| Public comment (member) | ⚠️ | Unclear if tech gets email |
| Document upload | ⚠️ | Unclear if opposite party gets email |
| Modification created | ✅ | Email sent to tech & member |
| Case completed | ✅ | Email sent to member |
| Scheduled release | ⚠️ | Cron job dependent - verify |

**Verification Steps:**

1. Check email settings in `settings.py`:
   ```python
   EMAIL_BACKEND = '...'
   EMAIL_HOST = '...'
   DEFAULT_FROM_EMAIL = '...'
   ```

2. Search for email send calls:
   ```bash
   grep -r "send_mail\|EmailMessage" cases/
   ```

3. Check notification templates:
   ```
   cases/templates/email/
   ```

**If Missing/Incomplete - Build System:**

```python
# cases/signals.py or cases/utils/notifications.py

from django.db.models.signals import post_save
from django.core.mail import send_mail
from django.template.loader import render_to_string
from cases.models import Case, CaseMessage

@receiver(post_save, sender=Case)
def notify_on_case_update(sender, instance, created, **kwargs):
    """Send notifications when case status changes"""
    
    if instance.status == 'submitted':
        # Member submitted - tech gets notified
        notify_tech_case_submitted(instance)
        
    elif instance.status == 'accepted':
        # Tech accepted - member gets notified
        notify_member_case_accepted(instance)
        
    elif instance.status == 'needs_resubmission':
        # Tech rejected - member gets notified
        notify_member_case_rejected(instance)
        
    elif instance.status == 'hold':
        # Tech put on hold - member gets notified
        notify_member_case_on_hold(instance)
        
    elif instance.status == 'completed':
        # Case completed - member gets email
        notify_member_case_completed(instance)

@receiver(post_save, sender=CaseMessage)
def notify_on_case_message(sender, instance, created, **kwargs):
    """Send notifications when messages/comments added"""
    
    if not created:
        return
    
    if instance.message_type == 'public':
        if instance.message_from.is_technician():
            # Tech asked question - member gets notified
            notify_member_tech_question(instance)
        else:
            # Member responded - tech gets notified
            notify_tech_member_response(instance)
```

**Required Emails:**

1. **Member notifications:**
   - [ ] Case submitted → confirmation
   - [ ] Case accepted → "in progress"
   - [ ] Case rejected → requirements (already works)
   - [ ] Case on hold → reason
   - [ ] Hold resumed → "continuing"
   - [ ] Tech asked question → question content
   - [ ] Case completed → "ready to download"
   - [ ] Scheduled release → "now available" (on schedule date)
   - [ ] Modification created → "mod case #"

2. **Tech notifications:**
   - [ ] Case submitted → new case alert
   - [ ] Member responded → comment notification
   - [ ] Member uploaded doc → doc notification
   - [ ] Case resubmitted → resubmission alert
   - [ ] Modification case available → mod alert

3. **Manager notifications:**
   - [ ] Case ready for review → alert
   - [ ] Tech reviewed my case → optional feedback

**Testing:**
```bash
python manage.py test cases.tests.test_scenarios.TestScenario1HappyPath -v 2
# Should verify all email sends
```

**Effort:** 4-6 hours to verify and fix
**Priority:** 🔴 **CRITICAL**

---

### 🔴 C3: CASE REOPENING (CRITICAL)

**Status:** ❌ **MISSING - Feature not implemented**

**Problem:**
Managers cannot reopen completed cases if errors are found. This prevents correction of mistakes after case is released to member.

**Current State:**
- Case statuses: draft, submitted, needs_resubmission, accepted, hold, pending_review, completed
- Missing: reopen_for_correction or similar status

**Implementation:**

1. **Add status to Case model:**
   ```python
   # cases/models.py
   
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
   
   class Case(models.Model):
       # ... existing fields ...
       reopen_reason = models.TextField(blank=True)  # Why manager reopened
       reopened_date = models.DateTimeField(null=True, blank=True)
       reopened_by = models.ForeignKey(User, null=True, related_name='reopened_cases')
   ```

2. **Add manager button in template:**
   ```django
   {% if perms.cases.can_reopen and case.status == 'completed' %}
       <button class="btn btn-warning" data-toggle="modal" data-target="#reopenModal">
           Reopen for Correction
       </button>
   {% endif %}
   ```

3. **Create reopen view:**
   ```python
   # cases/views.py
   
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
       
       return redirect(case.get_absolute_url())
   ```

4. **Member sees reopening:**
   - [ ] Dashboard shows case "Reopened for Correction"
   - [ ] Can see manager's reason
   - [ ] Case shows back in active list
   - [ ] Can upload docs again if needed

5. **Tech sees reopening:**
   - [ ] Case appears in queue with "Reopened" tag
   - [ ] Gets email notification
   - [ ] Can see reopening reason
   - [ ] Case moves back to status 'accepted' after tech resumes work

**Status Transition:**
```
completed → reopen_for_correction → (tech reviews) → accepted → completed
```

**Testing:**
```python
# test_scenarios.py - Scenario 10 should verify
def test_manager_reopens_case(self):
    case = Case.objects.create(status='completed')
    case.status = 'reopen_for_correction'
    case.reopen_reason = 'Q3 calculation error found'
    case.save()
    
    self.assertEqual(case.status, 'reopen_for_correction')
    # Tech should get notified and case appears in queue
```

**Effort:** 6-8 hours
**Priority:** 🔴 **CRITICAL**

---

### 🟠 H1: HOLD DURATION OPTIONS UI (HIGH)

**Status:** ⚠️ **Partial - Model supports but UI missing**

**Problem:**
- Current: Tech can only place indefinite holds
- Required: Options for 2h, 4h, 8h, 1 day, indefinite, custom days
- Model already has `hold_duration_days` field but UI not using it

**Current Modal:**
```
[Put on Hold]
Hold reason: [text field]
Duration: [NO OPTIONS - implicit indefinite]
[Submit]
```

**Needed Modal:**
```
[Put on Hold]
Hold reason: [text field]
Duration: (radio buttons or dropdown)
  ○ 2 hours
  ○ 4 hours
  ○ 8 hours
  ○ 1 day (24 hours)
  ○ 3 days
  ○ Indefinite (no auto-release)
  ○ Custom: [___] days
[Submit]
```

**Implementation:**

1. **Model update (may already exist):**
   ```python
   class Case(models.Model):
       hold_duration_days = models.IntegerField(null=True, blank=True)
       # Duration in days (0 = indefinite, or NULL = indefinite)
   ```

2. **Form:**
   ```python
   # cases/forms.py
   
   class PutOnHoldForm(forms.Form):
       DURATION_CHOICES = [
           ('2h', '2 hours'),
           ('4h', '4 hours'),
           ('8h', '8 hours'),
           ('1d', '1 day'),
           ('3d', '3 days'),
           ('indefinite', 'Indefinite (no auto-release)'),
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

3. **View:**
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

4. **Auto-release (if duration set):**
   - Add check: If hold_end_date < now(), auto-resume case
   - Or: Create cron job to auto-resume expired holds

**UI Template:**
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

**Effort:** 4-6 hours
**Priority:** 🟠 **HIGH**

---

### 🟠 H2: HOLD HISTORY TRACKING (HIGH)

**Status:** ❌ **MISSING - Data overwritten on 2nd hold**

**Problem:**
- Scenario 7 has multiple holds but data fields overwrite each other
- Can't see full hold history (hold1, resume1, hold2, resume2)

**Solution: Create HoldHistory table**

```python
# cases/models.py

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
    
    @property
    def duration(self):
        if self.ended_at:
            return self.ended_at - self.started_at
        return None
```

**Update Case model:**
```python
class Case(models.Model):
    # Remove old fields:
    # hold_start_date = ... DELETE
    # hold_end_date = ... DELETE
    # hold_reason = ... DELETE (moved to HoldHistory)
    # hold_duration_days = ... DELETE (moved to HoldHistory)
    
    # Add convenience methods:
    def get_current_hold(self):
        """Get current hold if case is on hold"""
        if self.status != 'hold':
            return None
        return self.hold_history.filter(action='placed').last()
    
    def get_hold_history(self):
        """Get full hold history"""
        return self.hold_history.all()
```

**Migration:**
```python
# cases/migrations/XXXX_create_hold_history.py

# Create HoldHistory table
# Migrate existing hold data to new table
# Drop old fields from Case
```

**Effort:** 4-6 hours
**Priority:** 🟠 **HIGH**

---

### 🟠 H3: HOLD HISTORY VISIBILITY (HIGH)

**Status:** ❌ **MISSING - Not visible in UI**

**Problem:**
- Tech/member can't see full hold history
- Only current hold displayed
- Scenario 7: Multiple holds confusing to member

**Solution: Add hold history section to case detail**

**Member View:**
```
Case Status: On Hold

Hold Information:
┌─────────────────────────────────────────┐
│ Hold #1 Started: Jan 15, 2:30 PM        │
│ Reason: Waiting for employment docs     │
│ Duration: 24 hours                      │
│ Ended: Jan 16, 2:30 PM                  │
│ Reason for resume: Docs received        │
│                                         │
│ Hold #2 Started: Jan 16, 3:00 PM        │
│ Reason: Manager approval needed         │
│ Duration: 2 hours                       │
│ Ended: Jan 16, 5:00 PM                  │
│ Reason for resume: Manager approved     │
│                                         │
│ Currently: Active/Reviewing              │
└─────────────────────────────────────────┘

Next Steps: Your case is being reviewed...
```

**Tech View (same as member plus internal notes)**

**Template:**
```django
{% if case.status == 'hold' or case.hold_history.exists %}
<div class="hold-history-section">
    <h4>Hold History</h4>
    <table class="table table-sm">
        <thead>
            <tr>
                <th>Status</th>
                <th>Date/Time</th>
                <th>Reason</th>
                <th>Duration</th>
            </tr>
        </thead>
        <tbody>
            {% for hold in case.get_hold_history %}
                <tr>
                    <td>{{ hold.get_action_display }}</td>
                    <td>{{ hold.started_at }}</td>
                    <td>{{ hold.reason }}</td>
                    <td>
                        {% if hold.duration %}
                            {{ hold.duration|duration }}
                        {% else %}
                            (ongoing)
                        {% endif %}
                    </td>
                </tr>
            {% endfor %}
        </tbody>
    </table>
</div>
{% endif %}
```

**Effort:** 2-3 hours (after H2 implemented)
**Priority:** 🟠 **HIGH**

---

## IMPLEMENTATION ROADMAP

### Week 1: Critical Path (24-30 hours)

**Monday:**
- [ ] Verify/build Cron job (C1) - 2-8h
- [ ] Start email notifications (C2) - 4-6h

**Wednesday:**
- [ ] Complete email notifications - ongoing
- [ ] Start case reopening (C3) - 4-6h

**Friday:**
- [ ] Verify all critical features working
- [ ] Run Scenario tests 1-10
- [ ] Documentation update

**Week 1 Complete:** All critical features working ✅

---

### Week 2: High Priority (20-25 hours)

**Monday:**
- [ ] Hold duration UI (H1) - 4-6h
- [ ] Hold history tracking (H2) - 4-6h

**Wednesday:**
- [ ] Hold history visibility (H3) - 2-3h
- [ ] Manager review workflow (H4) - 2-4h

**Friday:**
- [ ] Testing and bug fixes
- [ ] User acceptance testing

**Week 2 Complete:** Holds fully functional ✅

---

### Week 3: Medium Priority (12-17 hours)

**Monday:**
- [ ] Column visibility persistence (M1) - 2-4h
- [ ] Hold countdown timer (M2) - 2-3h

**Wednesday:**
- [ ] Modification visibility (M3) - 2-3h
- [ ] Communication clarity (M4) - 1-2h

**Friday:**
- [ ] Final testing
- [ ] Deploy to TEST server
- [ ] User training

**Week 3 Complete:** All features working ✅

---

## TESTING CHECKLIST

### Scenario Tests (Must Pass)
- [ ] Test Scenario 1: Happy Path ✅
- [ ] Test Scenario 2: Resubmission ✅
- [ ] Test Scenario 3: Hold/Resume 🟠 (depends on C2, H1)
- [ ] Test Scenario 4: Reassignment ✅
- [ ] Test Scenario 5: Scheduled Release 🔴 (depends on C1)
- [ ] Test Scenario 6: Modification ✅
- [ ] Test Scenario 7: Multiple Holds 🟠 (depends on H2)
- [ ] Test Scenario 8: 60-day Window ✅
- [ ] Test Scenario 9: Iterative Requests 🟠 (depends on C2)
- [ ] Test Scenario 10: Quality Review 🔴 (depends on C3)

### Manual Testing
- [ ] Create and submit case as member
- [ ] Accept and place on hold as tech
- [ ] Verify hold emails sent
- [ ] Upload doc during hold
- [ ] Resume from hold
- [ ] Verify resume email
- [ ] Schedule release
- [ ] Request modification
- [ ] Verify modification email
- [ ] Complete and release

### Database Testing
- [ ] Verify all fields populated correctly
- [ ] Test with sqlite locally
- [ ] Test with MySQL on TEST server
- [ ] Run migrations cleanly
- [ ] Check data persistence

---

## SUCCESS CRITERIA

All items must be complete before production release:

- [ ] All 10 scenarios pass TestCase tests
- [ ] All critical features working (C1, C2, C3)
- [ ] All high-priority features complete (H1-H4)
- [ ] Email notifications verified for all paths
- [ ] Cron job running and verified
- [ ] Hold duration options available
- [ ] Case reopening functional
- [ ] Manager review workflow clear
- [ ] Zero bugs in Scenario tests
- [ ] USER ACCEPTANCE TESTING PASSED

---

## EFFORT SUMMARY

| Tier | Items | Hours | Week |
|------|-------|-------|------|
| 🔴 Critical | 3 | 12-22 | Week 1 |
| 🟠 High | 4 | 12-19 | Week 1-2 |
| 🟡 Medium | 4 | 7-12 | Week 2-3 |
| 🟢 Low | 3 | 6-9 | Week 3+ |
| **TOTAL** | **14** | **37-62 hours** | **3 weeks** |

**Most Likely Timeline:** 45-55 hours over 3 weeks with experienced Django developer

---

## DEPENDENCIES

```
C1 (Cron Job)
├─ S5 Tests depend on this
└─ Email send needs to work

C2 (Email Notifications)
├─ Required by S1, S2, S3, S4, S9
└─ C1 depends on email working

C3 (Case Reopening)
├─ S10 tests depend on this
└─ Manager workflow requires this

H1 (Hold Duration)
├─ H3 depends on this
└─ S3, S7 need this for full testing

H2 (Hold History Tracking)
├─ H3 depends on this
└─ S7 needs this

H4 (Manager Review)
├─ S10 tests depend on this
└─ C3 might depend on manager workflow

M1-M4 (Medium priority)
├─ No blocking dependencies
└─ Can work in parallel
```

**Suggested Implementation Order:**
1. C1 (Cron) - Verify first, might already exist
2. C2 (Email) - Many things depend on this
3. H1 (Hold Duration) - UI work, independent
4. H2 (Hold History) - Backend, builds on holds
5. C3 (Case Reopening) - Manager feature
6. H3 (Hold History Visibility) - UI, builds on H2
7. H4 (Manager Review) - Clarify and complete
8. M1-M4 (Medium) - Polish and nice-to-haves

---

## NEXT STEPS

1. **Verify C1 (Cron Job):**
   ```bash
   find . -name "*scheduled*release*" -o -name "*cron*"
   ps aux | grep process_scheduled
   crontab -l | grep case
   ```

2. **Audit C2 (Email):**
   ```bash
   grep -r "send_mail\|EmailMessage" cases/
   ```

3. **Prioritize based on findings**

4. **Assign to developer sprint**

5. **Run tests after each feature**

6. **Deploy to TEST server weekly**

---

This roadmap provides clear priorities and actionable steps for the next 3 weeks of development.
