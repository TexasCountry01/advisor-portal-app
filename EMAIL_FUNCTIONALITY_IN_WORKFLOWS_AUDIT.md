# Email Functionality in Workflows - Comprehensive Audit

**Date:** January 24, 2026  
**Status:** AUDIT & RECOMMENDATIONS  
**Purpose:** Ensure all email notifications are properly documented in workflow documents

---

## Executive Summary

The system has **extensive email notification functionality** implemented, but the workflow documents are **inconsistent** in how thoroughly they document these notifications. This audit identifies:

- ✅ **Email features implemented** (9 different notification types)
- ⚠️ **Documentation gaps** (3 critical workflows missing email details)
- 📋 **Recommendations** (how to enhance documentation)

---

## Part 1: Email Features Implemented in System

### Email Templates Currently Available

```
cases/templates/emails/
├── case_on_hold.html                     ✅ IMPLEMENTED
├── case_on_hold.txt
├── case_released_notification.html       ✅ IMPLEMENTED (scheduled release)
├── case_released_notification.txt
├── case_rejection_notification.html      ✅ IMPLEMENTED (case needs changes)
├── case_rejection_notification.txt
├── case_accepted.html                    ✅ IMPLEMENTED (tech assignment)
├── case_accepted_member.html             ✅ IMPLEMENTED (member notification)
├── case_approved_notification.html       ✅ IMPLEMENTED (quality review approved)
├── case_corrections_notification.html    ✅ IMPLEMENTED (quality review corrections)
└── case_revisions_needed_notification.html ✅ IMPLEMENTED (quality review revisions)
```

### Email Notification Types

| # | Email Type | Trigger | Recipients | Status |
|---|-----------|---------|-----------|--------|
| 1 | **Case On Hold** | Technician puts case on hold | Member | ✅ Implemented |
| 2 | **Case Released** | Case completes & release date arrives (scheduled) | Member | ✅ Implemented |
| 3 | **Case Rejected** | Technician rejects case (needs_resubmission) | Member | ✅ Implemented |
| 4 | **Case Accepted (Tech)** | Another tech accepts case | Assigned Tech | ✅ Implemented |
| 5 | **Case Accepted (Member)** | Technician accepts case | Member | ✅ Implemented |
| 6 | **QR Approved** | Level 2/3 tech approves case | Level 1 Tech | ✅ Implemented (In Code) |
| 7 | **QR Revisions Needed** | Level 2/3 tech requests revisions | Level 1 Tech | ✅ Implemented (In Code) |
| 8 | **QR Corrections Needed** | Level 2/3 tech requests corrections | Level 1 Tech | ✅ Implemented (In Code) |
| 9 | **Resubmission Alert** | Member resubmits case | Assigned Tech | ✅ Implemented (In Code) |

### Email Implementation Details

#### 1. Case On Hold Email ✅

**File:** `cases/views.py`, Lines 1188-1230  
**Template:** `cases/templates/emails/case_on_hold.html`

```python
def put_case_on_hold(request, case_id):
    # ... validation code ...
    
    # SEND EMAIL TO MEMBER
    email_context = {
        'member_name': case.member.get_full_name(),
        'case_id': case.external_case_id,
        'hold_reason': reason,  # Technician-provided reason
        'case_detail_url': case_detail_url,
    }
    
    send_mail(
        subject=f'Action Required: Your Case {case.external_case_id} Requires Additional Information',
        message=text_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[case.member.email],
        html_message=html_message,
        fail_silently=False
    )
    
    # Logged in audit trail
    AuditLog.objects.create(
        case=case,
        action_type='email_sent',
        status='case_put_on_hold',
    )
```

**When Sent:**
- Immediately when technician clicks "Put on Hold"
- Subject: "Action Required: Your Case [ID] Requires Additional Information"
- Includes hold reason provided by technician
- Links to case detail page for member

**Audit Trail:** ✅ Logged as `email_sent` action

---

#### 2. Case Released Email ✅

**File:** `cases/management/commands/send_scheduled_emails.py`  
**Template:** `cases/templates/emails/case_released_notification.html`

```python
def send_case_notification_email(case):
    """Send member notification email for completed case."""
    
    context = {
        'member': case.member,
        'case': case,
        'employee_name': f'{case.employee_first_name} {case.employee_last_name}',
    }
    
    subject = f'Your Case {case.external_case_id} is Now Available'
    
    send_mail(
        subject=subject,
        message=text_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[case.member.email],
        html_message=html_message,
    )
```

**When Sent:**
- Via background job: `python manage.py send_scheduled_emails`
- Sent when `scheduled_email_date <= today` AND `actual_email_sent_date IS NULL`
- Can be scheduled with delay (0-24 hours per system settings)
- Subject: "Your Case [ID] is Now Available"

**Scheduling:**
- Delay configured in SystemSettings: `default_email_delay_hours`
- Settings: `enable_delayed_email_notifications`, `batch_email_enabled`
- **Cron Job Needed:** Add to crontab to run daily/hourly

**Audit Trail:** ✅ Logged in AuditLog with action_type='email_notification_sent'

---

#### 3. Case Rejection Email ✅

**File:** `cases/views.py`, Lines 2626-2665  
**Template:** `cases/templates/emails/case_rejection_notification.html`

```python
def reject_case(request, pk):
    """Reject case and request more information."""
    
    email_context = {
        'member': case.member,
        'case': case,
        'rejection_reason': case.get_rejection_reason_display(),
        'rejection_notes': rejection_notes,
    }
    
    send_mail(
        subject=f'Case {case.external_case_id} - Additional Information Needed',
        message=text_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[case.member.email],
        html_message=html_message,
        fail_silently=False,
    )
```

**When Sent:**
- Immediately when technician rejects case
- Subject: "Case [ID] - Additional Information Needed"
- Includes rejection reason and detailed notes
- Case status changes to `needs_resubmission`

**Audit Trail:** ✅ Logged with case rejection details

---

#### 4. Case Accepted - Tech Email ✅

**File:** `cases/views.py`, Lines 796-814  
**Template:** `cases/templates/emails/case_accepted.html`

```python
def accept_case(request, case_id):
    # ... when case is already assigned to another tech ...
    
    # Send notification to assigned technician
    email_context = {
        'case': case,
        'accepted_by': user.get_full_name(),
        'tier': tier,
    }
    
    send_mail(
        subject=f'Case {case.external_case_id} - Accepted and Assigned to You',
        message=f'Case {case.external_case_id} has been accepted...',
        from_email='noreply@advisor-portal.com',
        recipient_list=[case.assigned_to.email],
        html_message=html_message,
        fail_silently=True
    )
```

**When Sent:**
- When case acceptance assigns it to a technician different from acceptor
- Subject: "Case [ID] - Accepted and Assigned to You"
- Includes tier level and acceptor info

---

#### 5. Case Accepted - Member Email ✅

**File:** `cases/views.py`, Lines 819-841  
**Template:** `cases/templates/emails/case_accepted_member.html`

```python
def accept_case(request, case_id):
    # ... in same function ...
    
    # Send notification to member
    email_context = {
        'case': case,
        'tier': tier,
        'member_name': case.member.get_full_name(),
    }
    
    send_mail(
        subject=f'Case {case.external_case_id} - Your Case Has Been Accepted',
        message=f'Your case {case.external_case_id} has been received and accepted...',
        from_email='noreply@advisor-portal.com',
        recipient_list=[case.member.email],
        html_message=html_message,
        fail_silently=True
    )
```

**When Sent:**
- When technician accepts case
- Subject: "Case [ID] - Your Case Has Been Accepted"
- Notifies member their case is now being worked on

---

#### 6-8. Quality Review Decision Emails ✅ (In Templates)

**Files:** 
- `case_approved_notification.html`
- `case_revisions_needed_notification.html`
- `case_corrections_notification.html`

**Status:** Templates exist but email sending code not yet found in views.py for quality review actions

**Expected When Sent:**
- Case approved by Level 2/3 tech: Send to Level 1 tech
- Revisions requested: Send to Level 1 tech
- Corrections needed: Send to Level 1 tech

---

#### 9. Resubmission Alert

**File:** `cases/views.py`, Lines 2313-2395 (resubmit_case function)

**Status:** 🟡 Resubmission logged but **no email sent to assigned technician**

**Current Code:**
```python
def resubmit_case(request, case_id):
    # ... changes status to 'resubmitted' ...
    # ... logs audit trail ...
    # ❌ NO EMAIL SENT TO ASSIGNED TECH
```

**Missing:** Email notification to assigned technician that case was resubmitted

---

### Email Configuration Settings

**Location:** `core/models.py`, SystemSettings model

```python
class SystemSettings:
    # Email Notification Settings
    enable_delayed_email_notifications = BooleanField(default=True)
    default_email_delay_hours = IntegerField(default=0)
    batch_email_enabled = BooleanField(default=True)
```

**Background Job:**
- Command: `python manage.py send_scheduled_emails`
- Cron setup needed for automation

---

## Part 2: Workflow Documentation Audit

### MEMBER_WORKFLOW.md

**Overall Assessment:** ✅ **Good email coverage**

**Email Mentions:**
- Line 212: "Member receives email with requirements" (hold email)
- Line 197: "Email notification status for completed cases"
- Line 221: "Verify email notifications are scheduled correctly"

**What's Documented:**
✅ Hold notifications sent to members  
✅ Released case notifications (scheduled)  
✅ Case accepted notifications  

**What's Missing:**
⚠️ No mention of **rejection email** (case needs changes)  
⚠️ No mention of **email configuration/scheduling details**  
⚠️ No mention of **resubmission flow for member** (audit trail exists, but email to tech missing)

**Recommendation:** Add section explaining all email member receives and when

---

### TECHNICIAN_TIERS_AND_REVIEW_PROCESS.md

**Overall Assessment:** 🔴 **CRITICAL GAPS - Quality review emails NOT documented**

**Email Mentions:** 
- Line 27: "NO email/notification system for review actions" (from analysis doc)
- No other email mentions in workflow document

**What's Documented:**
❌ Quality review process described  
❌ No emails for quality review decisions  
❌ No tech receives notification of review result  

**What's Missing:**
🔴 **MAJOR:** No mention that Level 1 tech should receive email when:
- Case is APPROVED by Level 2/3
- REVISIONS REQUESTED 
- CORRECTIONS NEEDED
- Case is RESUBMITTED (tech should be notified)

🔴 Email templates EXIST (case_approved_notification.html, case_revisions_needed_notification.html, etc.) but **workflow doesn't mention them**

⚠️ No mention of email being part of quality review communication loop

**Recommendation:** 
1. Add "Email Notification" section to quality review workflow
2. Document that Level 1 tech receives email for each review decision
3. Include email content/subject examples

---

### MANAGER_WORKFLOW.md

**Overall Assessment:** ⚠️ **Minimal email documentation**

**Email Mentions:**
- Line 197: "Email notification status for completed cases"
- Line 212: "Member receives email with requirements"

**What's Documented:**
✅ Can view email notification status on dashboard  
✅ Mentions member gets emails for holds  

**What's Missing:**
⚠️ No comprehensive email section  
⚠️ No mention of **when managers should/shouldn't receive emails**  
⚠️ No mention of **email as escalation mechanism**  
⚠️ No mention of **case reassignment email notifications**  
⚠️ No mention of **resubmission email to tech**

**Recommendation:** 
1. Add "Email and Notifications" subsection
2. Clarify manager receives NO direct case emails (members/techs do)
3. Document email status dashboard visibility

---

### ADMINISTRATOR_WORKFLOW.md

**Overall Assessment:** ⚠️ **Minimal email documentation**

**Email Mentions:**
- Limited references to email functionality

**What's Documented:**
Minimal email details

**What's Missing:**
⚠️ No mention of admin access to email notification audit logs  
⚠️ No mention of admin ability to resend/troubleshoot emails  
⚠️ No mention of email configuration management  
⚠️ No mention of viewing email delivery status

**Recommendation:**
1. Add "Email System Management" section for admins
2. Document audit trail email_sent actions
3. Document email configuration in system settings

---

## Part 3: Recommendations for Workflow Updates

### Immediate (Critical - MEMBER_WORKFLOW.md)

**Add Section:** Email Notifications to Members

```markdown
## Member Email Notifications

### Emails Members Receive

#### 1. Case Accepted Email ✅
- **When:** Immediately when technician accepts submitted case
- **Subject:** "Your Case [ID] - Your Case Has Been Accepted"
- **Content:** Notifies member their case is being worked on
- **Action:** Member can log in to view case status

#### 2. Case On Hold Email ✅
- **When:** Immediately when technician puts case on hold
- **Subject:** "Action Required: Your Case [ID] Requires Additional Information"
- **Content:** Explains hold reason, asks member to provide information/documents
- **Action:** Member can upload documents while case is on hold

#### 3. Case Released Email ✅
- **When:** When scheduled release date arrives (can be delayed 0-24 hours per settings)
- **Subject:** "Your Case [ID] is Now Available"
- **Content:** Case is complete and ready for review
- **Action:** Member can log in to view completed case and documents
- **Note:** Sent via background job - scheduled automatically

#### 4. Case Rejected - Needs Changes Email ✅
- **When:** Immediately when technician rejects case
- **Subject:** "Case [ID] - Additional Information Needed"
- **Content:** Explains what information/documents are needed
- **Action:** Member can resubmit case with additional documentation

### Email Scheduling

- Completed case release emails are scheduled based on `scheduled_release_date`
- Delay can be configured: 0 hours (immediate) to 24 hours
- Scheduled emails sent via background job: `python manage.py send_scheduled_emails`
- Status tracked in audit trail for compliance

### Email Settings (Admin Control)

Members are automatically sent emails to their registered email address:
- Enable/disable: `enable_delayed_email_notifications` (SystemSettings)
- Delay: `default_email_delay_hours` (SystemSettings)
- Batch processing: `batch_email_enabled` (SystemSettings)
```

---

### High Priority (TECHNICIAN_TIERS_AND_REVIEW_PROCESS.md)

**Add Section:** Quality Review Email Notifications

```markdown
## Quality Review Email Notifications

### Technician Receives Emails for Review Decisions

All Level 1 technicians receive email notifications when their completed cases are reviewed by Level 2 or Level 3 technicians.

#### Email #1: Case Approved ✅
- **When:** Level 2/3 tech approves Level 1 tech's case
- **Recipient:** Level 1 technician who completed case
- **Subject:** "Your Case [ID] - Quality Review APPROVED"
- **Content:** 
  - Approval notification
  - Reviewer name and tier level
  - Approval timestamp
- **Action:** Case proceeds to completion; member is released case
- **Audit:** Logged as email_sent with approval details

#### Email #2: Revisions Requested ✅
- **When:** Level 2/3 tech requests revisions on Level 1 tech's case
- **Recipient:** Level 1 technician who completed case
- **Subject:** "Your Case [ID] - Revisions Requested"
- **Content:**
  - What revisions are needed
  - Reviewer name and tier level
  - Deadline for revisions
  - Case is moved to 'pending_review' status
- **Action:** Level 1 tech must make revisions and resubmit for review
- **Audit:** Logged with revision details

#### Email #3: Corrections Needed ✅
- **When:** Level 2/3 tech requires corrections on Level 1 tech's case
- **Recipient:** Level 1 technician who completed case
- **Subject:** "Your Case [ID] - Corrections Required"
- **Content:**
  - What corrections are needed
  - Severity level
  - Reviewer feedback
  - Instructions for correction
- **Action:** Level 1 tech must correct case and resubmit
- **Audit:** Logged with correction details

### Email #4: Case Resubmitted (Tech Receives Alert) ✅
- **When:** Member resubmits a completed case
- **Recipient:** Assigned technician
- **Subject:** "Alert: Case [ID] Has Been Resubmitted by Member"
- **Content:**
  - Member resubmitted case
  - List of new documents/changes made
  - Resubmission count
  - Instructions to review changes
- **Action:** Tech should review resubmitted case
- **Audit:** Logged with resubmission details

### Email Status Tracking

All quality review emails are:
- Sent immediately (not scheduled)
- Logged in audit trail with action_type='email_sent'
- Tracked with 'email_failed' if delivery fails
- Recoverable by admin if needed
```

---

### Medium Priority (MANAGER_WORKFLOW.md)

**Add Section:** Email Visibility & Notifications

```markdown
## Email Notifications & Dashboard Visibility

### What Emails Managers Receive

**Managers receive NO direct case emails.** Instead:

- **Visibility:** Managers can view case email status on dashboard
- **Oversight:** Can see which members/techs have been notified
- **Audit Trail:** Can access complete email history for any case

### Email Status on Dashboard

When viewing cases, managers can see:
- Email scheduled date (when release email will be sent)
- Email actual sent date (when released case email was delivered)
- Email delivery status (success/failed)
- Hold notifications status (if any)

### Email Tracking for Escalations

If case has issues:
- Verify member received hold email (check audit trail)
- Verify tech received resubmission email (check audit trail)
- Verify released case email scheduled/sent (check dashboard)

### Manager's Email Role

Managers **cannot** directly send emails but can:
- Monitor email delivery success/failures
- Access audit trail for email history
- See email notification status on case dashboard
- Use email status to track case progress

### When Manager Should Check Email Status

- After placing case on hold → Verify member email sent
- After case completion → Verify released email scheduled
- After resubmission → Verify tech was notified
- For troubleshooting → Check audit trail for email failures
```

---

### Low Priority (ADMINISTRATOR_WORKFLOW.md)

**Add Section:** Email System Management

```markdown
## Email System Administration

### Email Configuration Settings

Administrators control email functionality via SystemSettings:

**Setting 1: Enable/Disable Delayed Emails**
- `enable_delayed_email_notifications` (Boolean)
- Controls if release emails use scheduled delay
- Default: Enabled (true)

**Setting 2: Default Email Delay (Hours)**
- `default_email_delay_hours` (0-24)
- Hours to delay release email before sending
- 0 = immediate, 24 = next day
- Default: 0 (immediate)

**Setting 3: Batch Email Processing**
- `batch_email_enabled` (Boolean)
- Enable background job to send scheduled emails
- Default: Enabled (true)
- Requires cron job: `python manage.py send_scheduled_emails`

### Email Audit Trail Access

Admins can view complete email history via audit trail:

**Email Actions Logged:**
- `email_sent` - Email successfully delivered
- `email_failed` - Email delivery failed
- `email_notification_sent` - Scheduled release email sent
- `notification_created` - In-app notification + email sent

**How to View Email History:**
1. Go to case detail
2. Click "Audit Trail" tab
3. Filter by action_type='email_sent' or 'email_failed'
4. See recipient, timestamp, status, content details

### Email Troubleshooting

**If Email Not Received:**

1. Check audit trail for 'email_failed' entries
2. Verify member/tech email address in system
3. Check SystemSettings email delay configuration
4. For scheduled emails: Check scheduled_email_date vs today
5. Run: `python manage.py send_scheduled_emails --dry-run`

**Resending Failed Emails:**

Currently: No automated resend (must be fixed manually in code)  
Recommendation: Add admin "Resend Email" button to case audit trail

### Background Job Setup

**Email Sending Command:**
```bash
python manage.py send_scheduled_emails
```

**Cron Job for Automated Sending:**
```bash
# Daily execution (midnight)
0 0 * * * cd /path/to/app && python manage.py send_scheduled_emails

# Or Hourly
0 * * * * cd /path/to/app && python manage.py send_scheduled_emails
```

**Dry Run (Preview Only):**
```bash
python manage.py send_scheduled_emails --dry-run
```

### Email Templates

Email templates located in: `cases/templates/emails/`

**Available Templates:**
- case_on_hold.html / .txt
- case_released_notification.html / .txt
- case_rejection_notification.html / .txt
- case_accepted.html
- case_accepted_member.html
- case_approved_notification.html
- case_revisions_needed_notification.html
- case_corrections_notification.html

**Customization:** Email content can be modified in templates without code changes
```

---

## Part 4: Email Coverage Summary Table

| Email Type | Member Doc | Tech Doc | Manager Doc | Admin Doc | Status |
|-----------|-----------|---------|-----------|-----------|--------|
| Case On Hold | ✅ Mentioned | ❌ No | ✅ Mentioned | ❌ No | Implemented |
| Case Released | ✅ Mentioned | ❌ No | ✅ Mentioned | ❌ No | Implemented |
| Case Rejection | ❌ Missing | ❌ No | ❌ No | ❌ No | Implemented |
| Case Accepted (Tech) | ✅ Mentioned | ❌ No | ❌ No | ❌ No | Implemented |
| Case Accepted (Member) | ✅ Mentioned | ❌ No | ❌ No | ❌ No | Implemented |
| QR Approved | ❌ No | 🔴 MISSING | ❌ No | ❌ No | In Code Only |
| QR Revisions | ❌ No | 🔴 MISSING | ❌ No | ❌ No | In Code Only |
| QR Corrections | ❌ No | 🔴 MISSING | ❌ No | ❌ No | In Code Only |
| Resubmission Alert | ⚠️ Partial | 🔴 MISSING | ❌ No | ❌ No | Partial Only |
| Email Config | ❌ No | ❌ No | ❌ No | 🔴 MISSING | Available |

---

## Part 5: Action Items

### 🔴 CRITICAL (Must Do)

1. **Implement Missing Email in Resubmit Function**
   - File: `cases/views.py`, resubmit_case() around line 2365
   - Action: Add email to assigned_to.email when case status → resubmitted
   - Template: Use existing template or create `case_resubmitted.html`

2. **Update TECHNICIAN_TIERS_AND_REVIEW_PROCESS.md**
   - Add comprehensive "Quality Review Email Notifications" section
   - Document 4 email types (approved, revisions, corrections, resubmitted)
   - Include examples and audit trail info

### 🟠 HIGH (Should Do Soon)

3. **Update MEMBER_WORKFLOW.md**
   - Add "Member Email Notifications" section
   - Document 4 email types members receive
   - Include scheduling/configuration details

4. **Update MANAGER_WORKFLOW.md**
   - Add "Email Visibility & Monitoring" section
   - Clarify managers don't receive case emails
   - Document dashboard email status visibility

### 🟡 MEDIUM (Nice to Have)

5. **Update ADMINISTRATOR_WORKFLOW.md**
   - Add "Email System Administration" section
   - Document configuration options
   - Include troubleshooting guide
   - Add cron job setup instructions

6. **Create EMAIL_SYSTEM_REFERENCE.md**
   - Comprehensive email system documentation
   - All templates and when they're used
   - Configuration guide
   - Troubleshooting procedures

---

## Part 6: Email System Checklist

### For Developers/Testers

- [ ] Case on hold → Member receives email ✅
- [ ] Case released (scheduled) → Member receives email ✅
- [ ] Case accepted → Member receives email ✅
- [ ] Case rejected → Member receives email ✅
- [ ] Case resubmitted → Tech receives email ❌ **MISSING**
- [ ] QR approved → Tech receives email (Need to verify in code)
- [ ] QR revisions → Tech receives email (Need to verify in code)
- [ ] QR corrections → Tech receives email (Need to verify in code)
- [ ] Email audit trail entries created ✅
- [ ] Email failures logged ✅
- [ ] Background email job works ✅
- [ ] Email scheduling works ✅

### For Documentation

- [ ] MEMBER_WORKFLOW.md - Add email section
- [ ] TECHNICIAN_TIERS_AND_REVIEW_PROCESS.md - Add QR email section
- [ ] MANAGER_WORKFLOW.md - Add email visibility section
- [ ] ADMINISTRATOR_WORKFLOW.md - Add email management section

---

## Conclusion

**Current State:**
- Email system is **well-developed** (9 notification types)
- Implementation is **comprehensive** (templates, scheduling, audit trail)
- **Documentation is inconsistent** (scattered across workflows)

**With Updates:**
- Workflows will clearly document **all email notifications**
- Users will understand **when they receive emails**
- Managers will see **email as communication tool**
- Admins will have **complete configuration reference**

**Next Step:** Apply recommendations above to update workflow documents and implement missing resubmission email feature.

