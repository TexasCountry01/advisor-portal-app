# Administrator Workflow & Decision Tree

## Role Overview
**Administrators** have system-wide access and responsibility. They manage configuration, user accounts, system settings, handle complex escalations, manage audit trails, and ensure system integrity and compliance.

> **📊 AUDIT TRAIL TRACKING NOTE:**  
> All system activities, including administrative actions, are automatically tracked in the comprehensive audit trail. Administrators have complete access to audit reports, activity logs, and system events for compliance, security, and performance monitoring. The audit trail itself is audited (meta-audit) to ensure integrity and accountability.

---

## Administrator Workflow Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                   ADMINISTRATOR WORKFLOW                         │
└──────────────────────────────────────────────────────────────────┘

                          START
                            │
                            ▼
                  ┌─────────────────────────┐
                  │ Access Admin Console    │
                  │ & System Dashboard      │
                  └────────┬────────────────┘
                           │
        ┌──────────┬────────┼────────┬──────────┐
        │          │        │        │          │
        ▼          ▼        ▼        ▼          ▼
    ┌────────┐ ┌─────────┐ ┌────┐ ┌──────┐ ┌──────┐
    │User    │ │System   │ │Case│ │Audit │ │Issue │
    │Mgmt    │ │Settings │ │Esc │ │Trail │ │Alert │
    │        │ │         │ │    │ │      │ │      │
    └───┬────┘ └────┬────┘ └─┬──┘ └──┬───┘ └──┬───┘
        │           │        │       │       │
        ▼           ▼        ▼       ▼       ▼
    (Manage)   (Configure) (Handle) (Review) (Respond)
        │           │        │       │       │
        └───────────┴────────┴───────┴───────┘
                    │
                    ▼
        ┌────────────────────────────┐
        │ Take System Action         │
        │ (See decision trees below) │
        └────────────┬───────────────┘
                     │
                     ▼
        ┌────────────────────────────┐
        │ Monitor & Log Changes      │
        │ Update Audit Trail         │
        │ Document Decision          │
        └────────────┬───────────────┘
                     │
                     ▼
                   END
```

---


## Core Administrator Actions

Administrators manage system-wide configuration and integrity:

- **User Management** - Create accounts, assign roles, manage access
- **System Configuration** - Email settings, delays, case tiers
- **Escalation Handling** - Review and resolve complex cases
- **Audit & Compliance** - Monitor trails, generate reports

---

## Key Administrator Actions

### 1. **User Management**
- ✓ Create new user accounts (role-based permissions)
- ✓ Assign roles (member, tech, manager, admin)
- ✓ Reset user passwords
- ✓ **Deactivate accounts** (set inactive, preserves all data)
- ✓ **Reactivate accounts** (restore access)
- ✓ View user activity logs
- ✗ Delete accounts (use deactivate instead)

### 2. **System Settings**
- ✓ Set default case completion delay (0-24 hours CST)
- ✓ Enable/disable scheduled releases
- ✓ Enable/disable delayed email notifications
- ✓ Configure API settings
- ✓ Set batch processing schedules
- ✓ Configure email notifications
- ✓ Manage database settings
- ✓ **Column visibility settings (dashboard defaults)**
  - Configure default column visibility for all dashboards
  - Settings can be customized per-user (each user saves own preferences)
  - Control which columns appear by role/level

### 2A. **Column Visibility Management** (NEW - Admin Dashboard)
### 2B. **Notification System (Admin Scope)** (NEW)
- ✓ Have audit trail access to ALL notifications (system-wide)
- ✓ Cannot directly view member notifications in UI (member-only)
- ✓ Can access database to troubleshoot notification issues
- ✓ Can view audit trail showing:
  - When notifications created (case messages, holds, releases)
  - When members viewed notifications
  - Message content and responses
  - All messaging activity with timestamps
- ✓ Can verify notification creation is working
- ✓ Can reset/delete notifications if needed for testing
- ℹ️ **Two Systems:**
  - **Message Notifications:** Instant in-app (no email)
  - **Case Emails:** Scheduled 0-24 hours per configuration

### 2C. **Customize dashboard view:**
  - Click "Column Settings" button (gear icon)
  - Toggle columns on/off to show/hide:
    - Case ID, Member Name, Status, Created Date
    - Assigned Technician, Tier, Credit Value, Documents Count
    - Notes, Last Modified, Actions
  - Collapsible filter section (saves vertical space)
  - Filter counter showing active filters
- ✓ Preferences auto-save to your admin account
- ✓ Settings persist across login sessions
- ✓ System-wide oversight of all cases

### 3. **Workshop Delegate Management** (NEW)
- ✓ Manage delegates assigned to workshop codes
- ✓ Add delegates to specific workshops (like technicians)
- ✓ Edit delegate information (name, contact info, dates)
- ✓ Revoke delegate access to workshops
- ✓ View all active delegates across workshops
- ✓ Override/approve delegate assignments
- ✓ Audit trail for all delegate changes
- ✓ Manage delegates that technicians have added

**Access Path:** Admin Console → Management → Workshop Delegates

**Admin Permissions:**
- Full visibility of ALL workshop delegates (system-wide)
- Can manage delegates for any workshop
- Can approve delegate additions made by technicians
- Can override any delegate assignment
- Can force-remove delegates if needed for compliance

### 4. **Case Management**
- ✓ View all cases (unrestricted)
- ✓ Accept & Assign cases (Review & Accept workflow)
- ✓ Reject cases if incomplete (Request More Info)
- ✓ Release cases immediately (override delay)
- ✓ Reassign cases across any technician (audit trail maintained)
- ✓ Resolve complex escalations
- ✓ View internal tech notes
- ✓ View reassignment history for each case
- ✓ Monitor rejection rates and trends
- ✓ Delete/archive cases (if needed)
- Manage Case Holds:
  - View all cases on hold with hold reasons and duration
  - Put cases on hold (if technician hasn't)
  - Resume cases from hold
  - Monitor hold duration and end dates
  - View hold audit trail (reason, start, end, duration)
  - Override hold decisions if needed
  - Access hold metadata for all cases
  - Force-resume holds if needed for system management

### 5. **Audit & Compliance**
- ✓ View complete audit trail (including reassignments)
- ✓ Track all user actions
- ✓ Review case change history
- ✓ Export audit logs
- ✓ Generate compliance reports
- ✓ Monitor access control
- ✓ Review rejection analytics
- Track member profile changes:
  - All member profile edits logged (WHO/WHAT/WHEN/WHY)
  - Member detail updates recorded by technician
  - Delegate add/edit/revoke tracked with dates
  - Quarterly credit allowance changes logged
  - Full audit trail for compliance and verification

### 6. **System Maintenance**
- ✓ Backup & restore database
- ✓ View system health status
- ✓ Monitor performance metrics
- ✓ Clear cache/logs
- ✓ Run diagnostic checks
- ✓ Enable maintenance mode

---

### 6. **Member Collaboration & Notification System** (NEW - Jan 2026)
- ✓ **Member Post-Submission Edits:**
  - Members can add new documents/information even after case is submitted
  - Technician receives "New Info" badge on dashboard when member updates
  - `has_member_updates` flag tracks if member provided additional info
  - `member_last_update_date` timestamp records when member added updates
  - Speeds up case processing and reduces back-and-forth
  - Audit trail logs all member additions with exact timestamps
- ✓ **Hold Notification System (CaseNotification Model):**
  - When technician puts case on hold:
    - Member automatically receives email with hold reason and case link
    - In-app notification created with hold reason (stored in CaseNotification table)
    - "Cases on Hold" alert appears on member dashboard
    - Member can upload documents while case is on hold
  - CaseNotification model tracks:
    - notification_type (case_put_on_hold, member_update_received, case_released, documents_needed)
    - hold_reason (captured from technician when putting on hold)
    - is_read flag for UI tracking
    - created_at and read_at timestamps
  - ✓ View notification logs for compliance and audit purposes
  - ✓ Track notification delivery status (sent/failed/read)
  - ✓ Monitor member engagement with notifications
- ✓ **Audit Trail Integration:**
  - `document_uploaded` - Logged when member adds document post-submission
  - `member_case_updated` - Logged for member updates during submission
  - `case_held` - Logged with hold reason when case put on hold
  - `notification_created` - Logged when in-app notification created
  - `email_sent` / `email_failed` - Logged for hold notification delivery
  - Full timestamps and user tracking for compliance
- **📊 AUDIT TRACKING:**
  - CaseNotification table maintains all notification history
  - Member collaboration timeline visible to admins/managers
  - Hold decisions and member responses tracked and auditable
  - Email delivery logs preserved for compliance

---

## Role-Based User Creation & Management

✅ **Admin Controls Who Can Create & Manage What:**

| **Your Role** | **Can Create** | **Can Deactivate** | **Can Reactivate** |
|---|---|---|---|
| **Administrator** | Technician, Manager | All (except Admin) | All (except Admin) |
| **Manager** | ✗ Cannot create users | Cannot deactivate | Cannot reactivate |
| **Technician** | ✗ Cannot create users | Cannot deactivate | Cannot reactivate |
| **Member** | ✗ No user creation | Cannot deactivate | Cannot reactivate |

⚠️ **User Deactivation Model** (NOT Deletion):
- Users can be deactivated (set inactive) but NEVER deleted
- All user data, cases, and audit trail preserved
- Deactivated users can be reactivated any time
- Maintains data integrity and compliance

---

## Case Review & Acceptance Workflow (Admin Role)

As an **Administrator**, you have full authority to:

**1. Accept & Assign Cases:**
- Click "Review & Accept" on submitted cases
- Review Federal Fact Finder & documents
- Adjust credit value (0.5 to 3.0)
- Assign tier (Tier 1, 2, 3)
- Select technician
- ⚠️ Tier Warning if tier > tech level (can override)

**2. Reject Cases (Request More Info):**
- Select rejection reason (6 presets + custom)
- Add detailed notes about requirements
- Member receives email with what's needed
- Case status → "Needs Resubmission"

**3. Reassign Cases (Post-Acceptance):**
- Click "Reassign" on accepted case
- Select new technician
- Add reason
- Automatic audit trail:
  - From technician, to technician, date, reason, by admin

---

## Administrator Actions Detailed

### Action: Create New User
```
Navigate: Admin Console → User Management → Add User

Fill in:
├─ Email: john.smith@company.com
├─ First Name: John
├─ Last Name: Smith
├─ Role: Technician
├─ User Level: Level 1 (if technician)
├─ Department: Benefits
└─ Status: Active

Click: Send Invite
Result: User receives email with login link
```

### Action: Reset User Password
```
Navigate: Admin Console → User Management

Find user: alice@company.com
Click: "Reset Password"
Options:
├─ Send reset link to email
├─ Generate temporary password
└─ Force change on next login

Send: Confirmation to user
Result: User receives reset/temp password instructions
```

### Action: Change User Role
```
Navigate: Admin Console → User Management

Find user: bob@company.com
Current Role: Technician
Click: "Change Role"

Select new role:
├─ Member (downgrade)
├─ Manager (upgrade)
└─ Administrator (promote)

Confirm: Save change
Result: User's permissions updated immediately
```

### Action: Release Case Immediately
```
Navigate: Admin Console → Case Management

Find case: #1234
Status: Completed, scheduled for release in 2 hours

Click: "Release Immediately"
Options:
├─ Reason: [Rush request/Member request/etc]
├─ Notes: Add any notes
└─ Send notification to member

Confirm: Release
Result: Case available to member now, tech notified
```

### Action: Resolve Complex Escalation
```
Navigate: Admin Console → Escalations

View escalated case: #1042
Issue: "System limitation - can't process this scenario"
Tech notes: [detailed explanation]

Decision options:
├─ Approve workaround: [describe workaround]
├─ Modify system to support: [technical change]
├─ Return to tech with guidance: [instructions]
└─ Create special case handling: [process]

Click: "Resolve Escalation"
Notify: Tech and manager of decision
Result: Escalation closed, action item created
```

### Action: Manage Case Holds (NEW)
```
Navigate: Admin Console → Case Management → On Hold Cases

View all holds:
├─ Filter by: tech, duration, start date
├─ See hold reason and start date
├─ View hold end date (if timed duration)
└─ View hold duration remaining

Put Case on Hold:
├─ Open case detail
├─ Click "Put on Hold" button
├─ Select reason: "Waiting for Member", "Technical Issue", etc
├─ Select duration: Immediate, 2h, 4h, 8h, 1 day, custom
├─ Click "Confirm"
Result: Status → 'hold'
        Technician ownership preserved
        Hold timestamp recorded
        Audit trail updated

Resume Case from Hold:
├─ Open case on hold
├─ Click "Resume from Hold" button
├─ Add reason: "Member sent docs", etc
├─ Click "Confirm"
Result: Status → 'accepted'
        Case returns to tech's active queue
        Resume timestamp recorded
        Audit trail updated

Monitor Holds:
├─ Dashboard shows: "Cases on Hold: X"
├─ Alert if hold duration exceeded
├─ View hold audit trail for compliance
└─ Export hold reports for analysis
```

### Action: Configure System Settings
```
Navigate: Admin Console → System Settings → Release Settings

Current setting:
├─ Default Completion Delay: 2 Hours (CST)
└─ Scheduled Releases: Enabled

Make changes:
├─ Default Completion Delay: Select from 0-5 hours
├─ Scheduled Releases: Toggle on/off
├─ Batch Release Time: Set time for auto-release
└─ Release Date Picker: Enable/disable

Save: Changes take effect immediately
Log: Change recorded in audit trail
Notify: Managers/technicians if relevant
```

### Action: Manage Workshop Delegates (NEW)
```
Navigate: Admin Console → Management → Workshop Delegates

View all delegates:
├─ See all workshop delegate assignments
├─ Filter by workshop code
├─ Filter by delegate name
└─ View effective date range

Add Delegate:
├─ Click "Add Delegate"
├─ Select workshop code
├─ Enter delegate name
├─ Enter delegate email/contact
├─ Set effective date range (from/to)
├─ Click "Save"
├─ Delegate can now submit cases for that workshop

Edit Delegate:
├─ Click "Edit" on existing delegate
├─ Update name, contact, or date range
├─ Changes logged to audit trail
├─ Delegate retains permissions unless dates expire

Revoke Delegate:
├─ Click "Revoke" on delegate
├─ Option: Temporary (dates expire) or Immediate
├─ Confirm revocation
├─ Delegate access removed, audit logged

Admin Override:
├─ Can force-remove delegate if needed
├─ Can override technician decisions
├─ Full system-wide visibility and control
```
```

---

## Administrator Scenarios

### Scenario A: "New technician onboarding"
1. HR sends notification: "New tech Alice hired"
2. Admin creates user: alice@company.com, role=Technician, level=Level 1
3. Email sent with setup link
4. Alice logs in and sets password
5. Admin verifies account is active
6. Manager can now assign cases to Alice
7. Alice appears in assignment dropdown

### Scenario B: "Rush case - release immediately"
1. Tech calls: "Case #1234 needs immediate release (priority request)"
2. Admin checks case #1234
3. Status: Completed, scheduled for release in 2 hours
4. Admin clicks "Release Immediately"
5. Case becomes visible to member now
6. Tech and member both notified
7. Case released successfully

### Scenario C: "System needs maintenance - disable temporarily"
1. Database needs update (planned maintenance window)
2. Admin goes to System Settings
3. Clicks "Enable Maintenance Mode"
4. System shows message: "System under maintenance"
5. Users can't submit new cases or access system
6. Maintenance work completed
7. Admin disables Maintenance Mode
8. System back online

### Scenario D: "Security issue - reset password for multiple users"
1. Security check: "Some passwords might be compromised"
2. Admin selects: All technicians + managers
3. Bulk action: "Reset passwords"
4. Email sent to all affected users
5. Users get reset links
6. They set new passwords
7. Forced re-login on next access

### Scenario E: "Escalation from manager - system can't handle scenario"
1. Escalation received: "Case #1041 - special circumstance"
2. Tech can't process normally (system limitation)
3. Manager escalates to admin
4. Admin reviews: "This requires manual override"
5. Admin approves special handling method
6. Tech executes workaround (with admin approval)
7. Case completes successfully
8. Feature request logged for system update

---

## System Settings Admin Can Control

### Case Processing Settings
| Setting | Options | Impact |
|---------|---------|--------|
| Default Delay | 0-5 hours (CST) | When members get reports |
| Scheduled Releases | On/Off | Auto-release enabled? |
| Batch Release Time | Any time | When cron job runs |
| Release Date Picker | Enabled/Disabled | Can tech set custom dates? |

### User & Access Settings
| Setting | Options | Impact |
|---------|---------|--------|
| Allow Member Uploads | Yes/No | Can members attach docs? |
| Require Manager Approval | Yes/No | Manager must approve releases? |
| Multi-factor Auth | Required/Optional | Extra security layer |
| Session Timeout | 30 min - 8 hours | How long before logout |

### Integration Settings
| Setting | Options | Impact |
|---------|---------|--------|
| API Enabled | Yes/No | External systems can connect |
| Email Notifications | On/Off | Users get emails |
| Audit Logging | Standard/Verbose | How much to log |
| Database Backup | Auto/Manual | Data protection |

---

## Audit Trail Access

### What Gets Logged
- ✓ User logins (who, when, from where)
- ✓ Case changes (what, who changed it, when)
- ✓ User account changes (role updates, resets)
- ✓ System settings changes (what was changed)
- ✓ Document uploads/downloads
- ✓ Case releases and reassignments
- ✓ Escalations and resolutions
- ✓ Admin actions (any admin action)
- Member profile changes:
  - Profile edits (who edited, what changed, when)
  - Delegate management (add, edit, revoke with dates)
  - Quarterly credit allowance updates
  - Credit configuration changes
  - All changes traceable to specific technician/admin

### How to View Audit Trail
```
Admin Console → Audit & Compliance → Audit Trail
Filter by:
├─ Date Range
├─ User
├─ Action Type
├─ Case ID
└─ Status

View Details:
├─ Timestamp
├─ User
├─ Action
├─ Change (before/after)
└─ Notes

Export: PDF or CSV
```

---

## Emergency Procedures

### Scenario: User Account Compromised
1. Immediately deactivate user account
2. Force password reset for that user
3. Review audit trail for unauthorized actions
4. Check if any cases were modified
5. Contact user to verify legitimacy
6. If compromised: Check for data exposure
7. Reactivate when secure
8. Document incident

### Scenario: System Under Attack
1. Enable Maintenance Mode immediately
2. All traffic redirected to maintenance page
3. No case submissions possible
4. Existing users can view only (no changes)
5. Investigate security logs
6. Address vulnerability
7. Disable Maintenance Mode when safe
8. Document incident and changes

### Scenario: Database Corruption Detected
1. Stop all system processes
2. Enable Maintenance Mode
3. Run diagnostic: `python manage.py check`
4. Attempt restore from backup
5. If restore succeeds: Verify data integrity
6. If restore fails: Contact technical support
7. Disable Maintenance Mode when safe
8. Review how corruption occurred
9. Implement preventive measures

---

## Performance Monitoring for Admins

### Key Metrics
- **Database Performance**: Query time, disk usage
- **Application Performance**: Response time, error rate
- **User Activity**: Concurrent users, active sessions
- **Case Processing**: Cases/hour, completion rate
- **System Health**: Memory usage, CPU, storage

### Alerts to Watch For
- ⚠️ Database >85% full
- ⚠️ API response time >1 second
- ⚠️ Error rate >0.1%
- ⚠️ Failed cron jobs
- ⚠️ SSL certificate expiring
- ⚠️ Unusual access patterns

---

## Administrative Support & Escalation

### When to Escalate to External Support
- Database corruption can't be fixed
- Security breach requires forensics
- System outage needs infrastructure support
- Performance issues are hardware-related
- Backup/restore not working
- Disaster recovery needed

### Documentation & Training
- Keep detailed change logs
- Document system configurations
- Train backup admin on procedures
- Create runbooks for common tasks
- Maintain disaster recovery plan

---

## Administrator Best Practices

### Daily Tasks
- [ ] Monitor system health
- [ ] Check for escalations
- [ ] Review error logs
- [ ] Verify backup completed
- [ ] Check user account requests

### Weekly Tasks
- [ ] Review audit trail
- [ ] Generate performance report
- [ ] Test backup/restore
- [ ] Check for security updates
- [ ] Review user access

### Monthly Tasks
- [ ] Detailed system audit
- [ ] Capacity planning review
- [ ] Security assessment
- [ ] Vendor/license check
- [ ] Training needs assessment

---

## Email System Administration

### Email Configuration Settings

Administrators control all email functionality through SystemSettings model:

**Setting 1: Enable/Disable Email Notifications**
- **Field:** `enable_delayed_email_notifications`
- **Type:** Boolean (true/false)
- **Purpose:** Master switch for email notification feature
- **Default:** true (enabled)
- **Effect:** When false, no release/hold emails sent

**Setting 2: Email Delay Duration**
- **Field:** `default_email_delay_hours`
- **Type:** Integer (0-24)
- **Purpose:** Hours to delay sending release emails after case completion
- **Default:** 0 (immediate)
- **Examples:** 0=immediate, 1=next hour, 24=next day

**Setting 3: Batch Processing**
- **Field:** `batch_email_enabled`
- **Type:** Boolean (true/false)
- **Purpose:** Enable/disable background email job
- **Default:** true (enabled)

**How to Modify:** Admin Dashboard → System Settings → Email Section → Save

### Email Audit Trail Access

Administrators have full access to all email-related audit entries:

**Finding Email History:**
1. Case Detail → Audit Trail tab
2. Filter by action_type='email_sent', 'email_failed', 'email_notification_sent'
3. View complete email metadata: recipient, subject, timestamp, status

**Email Actions Logged:**
- `email_sent` = Email successfully delivered
- `email_failed` = Email delivery failed
- `email_notification_sent` = Scheduled release email sent
- `notification_created` = In-app notification + email created

### Background Email Job Management

**Command:** `python manage.py send_scheduled_emails`

**How It Works:**
1. Finds all completed cases where scheduled_email_date <= today
2. Checks if actual_email_sent_date IS NULL (not yet sent)
3. Sends email to member
4. Records actual_email_sent_date = NOW
5. Logs action in audit trail

**Running Manually:**
```bash
# Dry run (preview, no emails sent)
python manage.py send_scheduled_emails --dry-run

# Live execution (sends emails)
python manage.py send_scheduled_emails
```

**Cron Job Setup (Recommended):**

Add one of these to your server crontab:

```bash
# Daily at midnight (UTC)
0 0 * * * cd /path/to/advisor-portal-app && python manage.py send_scheduled_emails >> /var/log/emails.log 2>&1

# Or Hourly
0 * * * * cd /path/to/advisor-portal-app && python manage.py send_scheduled_emails >> /var/log/emails.log 2>&1
```

### Email Troubleshooting & Recovery

**Problem: Email Not Received**
1. Check audit trail for `email_failed` entries
2. Verify member email address correct in User profile
3. Check SystemSettings email configuration
4. Run: `python manage.py send_scheduled_emails --dry-run`

**Problem: Scheduled Email Not Sent**
1. Verify case status = 'completed'
2. Check scheduled_email_date is in past or today
3. Verify batch_email_enabled = true in SystemSettings
4. Check if cron job is running

**Recovery Options:**
- Cannot currently resend individual failed emails
- Must manually edit case.actual_email_sent_date = NULL and rerun job
- Or create custom admin command to resend specific emails

### Email Template Management

**Email Templates Location:** `cases/templates/emails/`

**Available Templates:**
- case_on_hold.html / .txt (member hold notification)
- case_released_notification.html / .txt (member release)
- case_rejection_notification.html / .txt (member rejection)
- case_accepted.html (tech assignment)
- case_accepted_member.html (member accepted)
- case_approved_notification.html (QR approved)
- case_revisions_needed_notification.html (QR revisions)
- case_corrections_notification.html (QR corrections)

**Modifying Templates:**
1. Edit .html or .txt file in cases/templates/emails/
2. Changes take effect immediately
3. Variables available: case, member, tech, reason, etc.
4. Keep HTML responsive for mobile

### System Maintenance & Email

**During Maintenance:**
- Set `batch_email_enabled = false` to prevent sending during downtime
- Set `enable_delayed_email_notifications = false` if critical issues
- Restore settings when maintenance complete

### Email Compliance & Audit

**Compliance Features:**
- All emails logged in audit trail
- Timestamps recorded for all send attempts
- Failed emails tracked with error reasons
- Email content archived in audit trail

**Audit Reports:**
- All emails sent to specific member (date range)
- All emails sent on specific date range
- Email delivery failure report
- Email delay compliance report

---

## 📊 Audit Trail Activities (Administrator Role)

All administrator activities are automatically tracked in the system's audit trail. Here's what gets logged:

| Activity | Audit Code | When Logged | Details Captured |
|----------|-----------|-------------|------------------|
| **Login** | `login` | Immediate | Session start, admin ID, IP, timestamp |
| **Logout** | `logout` | Immediate | Session end, duration, last action |
| **Create User** | `user_created` | On creation | New user ID, role, level, email, creator ID |
| **Update User** | `user_updated` | On save | User ID, fields changed, old/new values, admin ID |
| **Change User Role** | `user_role_changed` | On change | User ID, previous role, new role, admin ID, reason |
| **Delete/Deactivate User** | `user_deleted` | On deactivation | User ID, reason, admin ID, date deactivated |
| **Reset User Password** | `user_updated` | On reset | User ID, reset by admin, timestamp |
| **Bulk Credit Reset** | `bulk_credit_reset` | On execution | Member count, new allowance, admin ID, timestamp |
| **Individual Credit Reset** | `quarterly_credit_reset` | Per member | Member ID, old allowance, new allowance, admin ID |
| **Place Case on Hold** | `case_held` | On hold | Case ID, reason, hold duration, admin ID |
| **Resume Case** | `case_resumed` | On resumption | Case ID, hold duration, reason, admin ID |
| **Change Case Tier** | `case_tier_changed` | On change | Case ID, previous/new tier, reason, admin ID |
| **Force Assign Case** | `case_assigned` | On assignment | Case ID, technician, reason, admin override, admin ID |
| **Force Reassign Case** | `case_reassigned` | On reassignment | Case ID, from/to tech, reason, admin override, admin ID |
| **Force Release Case** | `case_status_changed` | On release | Case ID, release time, reason override, admin ID |
| **Update System Setting** | `settings_updated` | On change | Setting name, old/new values, admin ID, impact |
| **Delegate Management** | `user_role_changed` | On add/remove | Delegate type, permissions, tech ID, admin ID |
| **Export Audit Log** | `bulk_export` | On export | Export type, date range, record count, admin ID, filters |
| **Access Audit Trail** | `audit_log_accessed` | On access | Report type, filters, admin ID, purpose (meta-audit) |
| **Generate System Report** | `report_generated` | On generation | Report type, parameters, admin ID, timestamp |
| **Execute Cron Job** | `cron_job_executed` | On execution | Job name, records processed, status, error log, timestamp |
| **Dismiss Alert** | `alert_dismissed` | On dismiss | Alert ID, severity, reason dismissed, admin ID |

### Key Audit Activities

**User & Role Management:**
- All user creation, updates, and role changes logged with admin authority
- Password resets documented with admin ID
- User deactivation preserves data and audit trail
- Role/permission changes tracked for compliance

**System Configuration:**
- All settings changes logged with before/after values
- System-wide events (cron jobs, batch operations) documented
- Configuration changes impact documented
- System alerts and dismissals tracked

**Compliance & Auditing:**
- Admin access to audit logs itself logged (meta-audit)
- Export operations documented with scope and date range
- Report generation tracked for compliance verification
- Bulk operations logged with record counts

**Case Administration:**
- Force assignments/reassignments documented with override reason
- Force releases tracked with business justification
- Hold/resume decisions by admins logged
- Tier changes and escalations documented

### Comprehensive Audit Trail Coverage

**All Activities Tracked:**
- Login/logout for security
- User management operations
- Case operations and overrides
- System configuration changes
- Report generation
- Bulk operations and exports
- Quality review submissions
- Credit resets and adjustments

**Access Controls:**
- Only admins can view complete audit trails
- Managers can view team-specific activities
- Technicians can view personal activities
- Members can view personal activity summary
- All access is itself logged

### Audit Trail Uses for Administrators
- **System Compliance:** Complete record for audit requirements
- **Security Monitoring:** Track unusual access patterns
- **Dispute Resolution:** Evidence of administrative decisions
- **Performance Analysis:** System usage and load patterns
- **Incident Investigation:** Complete activity history for any user/case
- **Regulatory Requirements:** Full audit trail for compliance verification

### Accessing Administrator Audit Information
- **Activity Summary Report** - System-wide overview (top activity types, users)
- **User Activity Report** - Individual user/admin activity tracking
- **Case Change History Report** - All case modifications with who/when/why
- **Quality Review Audit Report** - QA metrics and reviewer performance
- **System Event Audit Report** - Cron jobs, bulk operations, system events
- **Raw Audit Log** - Complete database with advanced filtering and search

---

## Admin Support Resources

**Resources Available:**
- System documentation in knowledge base
- Django admin guide
- Database administration manual
- Security protocols & procedures
- Disaster recovery playbook
- Contact info for technical support

**Emergency Support:**
- 24/7 on-call support line
- Emergency escalation procedures
- Technical support contact
- Security incident hotline

---

## Reference Diagrams

## Admin Dashboard Overview

```
┌──────────────────────────────────────────────────────────┐
│ ADMINISTRATOR CONSOLE                                    │
├──────────────────────────────────────────────────────────┤
│                                                          │
│ SYSTEM STATUS                CRITICAL ALERTS           │
│ ├─ Users Online: 42          ├─ Database: 89% full    │
│ ├─ Cases in System: 2,847    ├─ API Rate: Normal      │
│ ├─ Uptime: 99.7%             ├─ Failed Jobs: 1        │
│ └─ Last Backup: 2 hrs ago    └─ SSL Certificate: OK   │
│                                                          │
│ USER MANAGEMENT              ESCALATIONS               │
│ ├─ Total Users: 142          ├─ Pending: 5            │
│ ├─ Admins: 2                 ├─ Complex: 3            │
│ ├─ Managers: 8               ├─ Rush: 1               │
│ ├─ Technicians: 45           └─ Waiting Approval: 2   │
│ └─ Members: 87                                         │
│                                                          │
│ SYSTEM SETTINGS              AUDIT ACTIVITY           │
│ ├─ Case Delay: 2 hours       ├─ Changes Today: 23     │
│ ├─ Release Date: Auto         ├─ User Logins: 156    │
│ ├─ Batch Processing: On       ├─ Case Updates: 847    │
│ └─ Cron Job Status: Running   └─ Deletions: 2         │
│                                                          │
│ PERFORMANCE                  RECENT ACTIONS            │
│ ├─ Avg Response: 234ms        ├─ User Created: Alice  │
│ ├─ Database: Healthy          ├─ Settings Changed     │
│ ├─ API: Normal                ├─ Case Escalated: 1038 │
│ └─ Storage: 156 GB / 500 GB   └─ Report Generated     │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

---

## Decision Tree: "What Needs Admin Attention?"

```
              START: Check admin console for tasks
                            │
                            ▼
                ┌──────────────────────────┐
                │ What type of action?     │
                └────────┬─────────────────┘
                         │
    ┌──────┬────────┬────┴────┬───────┬────────┐
    │      │        │         │       │        │
   USER  SYSTEM   CASE     AUDIT   SECURITY  MAINTENANCE
   MGMT  CONFIG   ESCALATE REVIEW  ALERT    TASK
    │      │        │         │       │        │
    ▼      ▼        ▼         ▼       ▼        ▼
 [See     [See     [See      [See    [See    [See
  Below]  Below]   Below]    Below]  Below]  Below]
```

---

## Decision Tree 1: User Management Actions

```
              START: Need to manage users?
                            │
                            ▼
                ┌──────────────────────────┐
                │ What action needed?      │
                └────────┬─────────────────┘
                         │
    ┌────────┬──────────┬┴─────┬──────────┐
    │        │          │      │          │
  CREATE  UPDATE     RESET   DEACTIVATE REACTIVATE
  USER    ROLE       PASSWORD ACCOUNT    ACCOUNT
    │      │          │        │         │
    ▼      ▼          ▼        ▼         ▼
   Fill   Change    Send     Mark     Mark
  Form    Role      Reset    Inactive  Active
  →       → Save    Link    → Confirm  → Confirm
 Confirm           → Send    (Preserves (Restore
    │              Email      Data)     Access)
    ▼                │          │        │
 User          ┌─────┴──────┐   │        ▼
 Created       │            │   │    User
 & Notified   User Updates  │   │  Reactivated
              Password      │   │
                   │        │   ▼
                   ▼        ▼
              Login &   Cases & Data
              Proceed   Fully Preserved
```

**⚠️ NO DELETE OPTION:** Users are deactivated (not deleted) to preserve all case data and audit trails.

---

## Decision Tree 2: System Configuration

```
                START: Modify system settings?
                            │
                            ▼
                ┌──────────────────────────┐
                │ What setting to change?  │
                └────────┬─────────────────┘
                         │
    ┌────────┬──────────┬┴──────┬────────┐
    │        │          │       │        │
 RELEASE  API CRON    DATABASE FEATURE MAINTENANCE
 TIMING   CONFIG  SCHEDULING   CONFIG   MODE
    │        │       │          │        │
    ▼        ▼       ▼          ▼        ▼
 Open    Update   Enable/   Backup   Toggle
 Release Update   Disable   Settings Maintenance
 Setting Config   Schedule  Update   Mode
    │        │       │          │        │
    ▼        ▼       ▼          ▼        ▼
 Select  Test    Verify    Execute   Status
 Delay   Config  Cron      Change    Change
    │        │       │       Works    │
    ▼        ▼       ▼        │       ▼
 Save    Deploy   Schedule   │      Done
    │        │       │       │
    └────────┴───────┴───────┘
            │
            ▼
    Log Change & Audit
```

---

