# Delayed Email Notification Feature - Analysis & Direction Confirmation

**Date**: January 16, 2026  
**Status**: Design Analysis Complete ✅  
**Confidence**: 95% (Ready for Implementation)

---

## Your Direction - CONFIRMED ✅

You want to implement **delayed email notifications** to members when a case is released/completed, mirroring the existing scheduled release delay system. This is an **excellent architectural approach**.

---

## Existing Delayed Release System (Reference Model)

Your current system already has all the components you need:

### 1. **Database Model** ✅
**File**: `cases/models.py`
```python
class Case(models.Model):
    scheduled_release_date = models.DateField(null=True, blank=True)
    actual_release_date = models.DateTimeField(null=True, blank=True)
```

**For Email**, you would add:
```python
class Case(models.Model):
    # Existing fields above...
    
    # NEW FIELDS FOR EMAIL
    scheduled_email_date = models.DateField(null=True, blank=True)
    actual_email_sent_date = models.DateTimeField(null=True, blank=True)
```

---

### 2. **System Settings** ✅
**File**: `core/models.py` - `SystemSettings`

Current settings:
```python
default_completion_delay_hours = models.IntegerField(default=0)  # 0-5 hours
enable_scheduled_releases = models.BooleanField(default=True)
```

**For Email**, add:
```python
class SystemSettings(models.Model):
    # Existing...
    
    # NEW EMAIL SETTINGS
    default_email_delay_hours = models.IntegerField(
        default=0,  # 0 = send immediately
        help_text='Hours to delay before sending member notification email (0-24 hours)'
    )
    enable_delayed_email_notifications = models.BooleanField(default=True)
    enable_immediate_email_notifications = models.BooleanField(default=True)
```

---

### 3. **Case Completion Logic** ✅
**File**: `cases/views.py` - `mark_case_completed()` function

**Current Flow:**
```
User marks case complete
→ Calculate scheduled_release_date based on delay setting
→ If 0 hours: actual_release_date = NOW, released immediately
→ If 1-5 hours: scheduled_release_date = TODAY + hours, awaits cron job
```

**Add Email Logic:**
```
When case completion delay is set (0-5 hours):
→ Calculate scheduled_email_date using SAME logic
→ If 0 hours: actual_email_sent_date = NOW, email sent immediately  
→ If 1+ hours: scheduled_email_date = TODAY, awaits cron job
```

---

### 4. **Management Command (The Batch Job)** ✅
**File**: `cases/management/commands/release_scheduled_cases.py`

**Current Command:**
```bash
python manage.py release_scheduled_cases
python manage.py release_scheduled_cases --dry-run
```

**Proposed New Command:**
```bash
# New separate command for emails
python manage.py send_scheduled_emails
python manage.py send_scheduled_emails --dry-run

# Could combine both OR keep separate - your choice
```

**What It Does:**
- Find all cases where: `status='completed'` AND `scheduled_email_date <= today` AND `actual_email_sent_date IS NULL`
- Send email to `case.member.email` with case details
- Set `actual_email_sent_date = timezone.now()`
- Log results

---

### 5. **Timezone Handling** ✅
**File**: `cases/services/timezone_service.py`

You already have:
```python
def calculate_release_time_cst(hours_delay: int) -> datetime:
    """Calculate scheduled release time in CST"""
    cst_now = get_cst_now()
    release_time_cst = cst_now + timedelta(hours=hours_delay)
    return release_time_cst
```

**Email can use the EXACT SAME function** - it's timezone-agnostic:
```python
# Same for email delay calculation
email_time_cst = calculate_release_time_cst(email_delay_hours)
```

---

### 6. **Cron Job Setup** ✅
**File**: `CRON_JOB_SETUP.md`

Current cron:
```bash
0 0 * * * cd /var/www/advisor-portal-app && python manage.py release_scheduled_cases
```

**Add for email:**
```bash
# Run email job separately (e.g., 15 mins after release job)
0 0 * * * cd /var/www/advisor-portal-app && python manage.py release_scheduled_cases
15 0 * * * cd /var/www/advisor-portal-app && python manage.py send_scheduled_emails

# OR run every hour to catch emails faster
0 * * * * cd /var/www/advisor-portal-app && python manage.py send_scheduled_emails
```

---

## Implementation Architecture

### Option A: **UNIFIED** (Recommended) ✅
Single command handles both release AND email:

```python
# cases/management/commands/release_scheduled_cases.py
def handle(self, *args, **options):
    # Release cases
    cases_to_release = Case.objects.filter(...)
    for case in cases_to_release:
        case.actual_release_date = timezone.now()
        case.save()
    
    # Send emails for cases ready for notification
    cases_to_email = Case.objects.filter(...)
    for case in cases_to_email:
        send_case_notification_email(case)
        case.actual_email_sent_date = timezone.now()
        case.save()
```

**Pros:**
- Single cron job (simpler)
- One database query batch
- Can tie release + email together

**Cons:**
- Mixed concerns (release vs email)

---

### Option B: **SEPARATED** (More Modular) ✅
Two separate commands:

```bash
# 1. cases/management/commands/release_scheduled_cases.py
# Handles ONLY case release

# 2. cases/management/commands/send_scheduled_emails.py
# Handles ONLY email sending
```

**Pros:**
- Clean separation of concerns
- Can run emails more frequently (every hour)
- Easier to test/debug
- Can disable one without affecting the other

**Cons:**
- Two cron jobs

---

## Timing Options for Email Delay

Based on your existing 0-5 hour model, I recommend:

```python
EMAIL_DELAY_OPTIONS = [
    (0, 'Immediately - Send notification right away'),
    (1, '1 Hour Delay - Brief review window'),
    (2, '2 Hours Delay - Standard notification'),
    (3, '3 Hours Delay - Extended review'),
    (4, '4 Hours Delay - Extended review'),
    (5, '5 Hours Delay - Maximum delay'),
    # Optional: Allow custom delays up to 24 hours
    (24, '24 Hours Delay - Next day notification'),
]
```

**Question for You:** Should the email delay be:
1. **Tied to case release delay?** (Email sent when case is released)
2. **Independent?** (Can delay email separately from release)
3. **Always with case release?** (No separate control)

---

## Configuration UI Changes

**File**: `templates/core/system_settings.html`

Add section:
```html
<!-- Email Notification Settings -->
<div class="card mb-4">
    <div class="card-header">
        <h5>Email Notification Settings</h5>
    </div>
    <div class="card-body">
        <div class="form-check form-switch mb-3">
            <input class="form-check-input" 
                   type="checkbox" 
                   id="enable_delayed_email" 
                   name="enable_delayed_email_notifications"
                   {% if settings.enable_delayed_email_notifications %}checked{% endif %}>
            <label class="form-label">Enable Delayed Email Notifications</label>
        </div>
        
        <div class="mb-3">
            <label for="email_delay" class="form-label">Default Email Delay</label>
            <select class="form-select" id="email_delay" name="default_email_delay_hours">
                <option value="0">Immediately</option>
                <option value="1">1 Hour</option>
                <option value="2">2 Hours</option>
                <!-- etc -->
            </select>
        </div>
    </div>
</div>
```

---

## Email Template Design

**New File**: `cases/templates/emails/case_released_notification.txt` (and .html)

```text
Subject: Your Case {{case.external_case_id}} is Now Available

Dear {{member.first_name}},

Your case {{case.external_case_id}} has been completed and is now available for review.

Employee: {{case.employee_first_name}} {{case.employee_last_name}}
Completion Date: {{case.date_completed|date:"F j, Y"}}
Status: {{case.get_status_display}}

You can view your case and download the report by logging into your account:
[Link to case detail]

Best regards,
Benefits Portal Team
```

---

## Files to Create/Modify

### CREATE:
- [ ] `cases/management/commands/send_scheduled_emails.py` - New command
- [ ] `cases/templates/emails/case_released_notification.txt` - Email template
- [ ] `cases/templates/emails/case_released_notification.html` - HTML email
- [ ] `cases/services/email_service.py` - Email helper functions

### MODIFY:
- [ ] `cases/models.py` - Add `scheduled_email_date`, `actual_email_sent_date` to Case model
- [ ] `core/models.py` - Add email settings to SystemSettings
- [ ] `cases/views.py` - Update `mark_case_completed()` to calculate email schedule
- [ ] `cases/management/commands/release_scheduled_cases.py` - Add email sending (if unified approach)
- [ ] `templates/core/system_settings.html` - Add email configuration UI
- [ ] Create migration for new fields

---

## Database Migration Strategy

```bash
# Create migration
python manage.py makemigrations

# Test migration locally
python manage.py migrate

# Deploy to test server
# Then to production
```

---

## Testing Strategy

```python
# Test 1: Email scheduling works
case.mark_completed(email_delay_hours=2)
assert case.scheduled_email_date is not None
assert case.actual_email_sent_date is None

# Test 2: Immediate email
case.mark_completed(email_delay_hours=0)
# Verify email sent

# Test 3: Cron job finds and sends scheduled emails
# Create test case with past scheduled_email_date
# Run management command
# Verify email sent and actual_email_sent_date set
```

---

## Your Confirmation Questions

1. **Email Delay Independence**: Should email delay be independent from case release delay, or tied together?
2. **Email Recipient**: Member's email only, or also notify technician/manager?
3. **Command Approach**: Unified (one command does both) or Separated (two commands)?
4. **Email Frequency**: How often should cron job run?
   - Nightly? (0 0 * * * - matches current)
   - Hourly? (0 * * * * - faster notifications)
   - Every 30 mins? (*/30 * * * * - near real-time)
5. **Max Delay**: Should email delay go beyond 5 hours? (e.g., 24 hours for next-day notification?)

---

## Your Direction - CONFIRMED ✅

**YES, this approach is solid.** You're leveraging:
- ✅ Existing timezone service
- ✅ Existing scheduled system architecture
- ✅ Existing cron/management command pattern
- ✅ Existing settings UI structure
- ✅ Configurable delays (admin control)
- ✅ Audit trail (scheduled vs actual timestamps)

This is a **consistent, maintainable, and scalable** approach.

Ready to implement? Let me know your answers to the confirmation questions above!
