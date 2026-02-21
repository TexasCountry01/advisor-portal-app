# Audit Trail System - Quick Reference Guide

## Overview
The comprehensive audit trail system tracks all activities in the Advisor Portal application automatically and provides advanced reporting capabilities for administrators and managers.

---

## Accessing Audit Reports

### Location
All audit reports are accessible from the admin/manager dashboard under **Audit & Compliance** section.

### Available Reports

#### 1. Activity Summary Report
**URL:** `/reports/activity-summary/`  
**Purpose:** System-wide activity overview and statistics  
**Visible To:** Managers, Administrators  
**Key Metrics:**
- Total system activities
- Activities by type (top 15)
- Top 10 most active users
- Case activity count
- User management activity count
- Quality review activity count

**How to Use:**
1. Navigate to Audit Dashboard
2. Click "Activity Summary Report"
3. (Optional) Select date range and click Filter
4. Review statistics and activity breakdown

---

#### 2. User Activity Report
**URL:** `/reports/user-activity/`  
**Purpose:** Track detailed activities for specific users  
**Visible To:** Managers, Administrators  
**Key Features:**
- Per-user activity tracking
- Activity breakdown by type
- Detailed activity log with pagination
- Filters by date range

**How to Use:**
1. Navigate to User Activity Report
2. Select a user from the dropdown
3. (Optional) Select date range
4. Click Filter
5. Review user's activities with detailed breakdown
6. Use pagination to browse through entries

---

#### 3. Case Change History Report
**URL:** `/reports/case-changes/`  
**Purpose:** View complete history of all case modifications  
**Visible To:** Managers, Administrators, Technicians  
**Key Features:**
- Filter by change type (status, tier, assignment, resubmission, hold/resume)
- Change timeline with before/after values
- Summary statistics (total changes, status changes, tier changes, reassignments)
- User attribution for each change

**How to Use:**
1. Navigate to Case Change History Report
2. (Optional) Select change type filter
3. (Optional) Select date range
4. Click Filter
5. Review case modification timeline
6. Click case ID to view full case details

---

#### 4. Quality Review Audit Report
**URL:** `/reports/quality-review-audit/`  
**Purpose:** Monitor quality review submissions and reviewer performance  
**Visible To:** Managers, Administrators  
**Key Metrics:**
- Total quality reviews submitted
- Reviews by status (approved, revisions requested, corrections needed)
- Reviewer performance metrics with approval rates
- Statistics for each reviewer

**How to Use:**
1. Navigate to Quality Review Audit Report
2. (Optional) Filter by review status
3. (Optional) Select date range
4. Click Filter
5. Review quality review statistics
6. Check reviewer performance breakdown
7. Review detailed quality review submissions

---

#### 5. System Event Audit Report
**URL:** `/reports/system-events/`  
**Purpose:** Monitor system-level events (cron jobs, credit resets, exports, etc.)  
**Visible To:** Administrators  
**Key Metrics:**
- Total system events
- Successful vs. failed events
- Success rate percentage
- Events by type breakdown

**How to Use:**
1. Navigate to System Event Audit Report
2. (Optional) Filter by event type (cron jobs, credit resets, settings, exports, reports)
3. (Optional) Select date range
4. Click Filter
5. Review system event statistics
6. Check event type breakdown
7. Review detailed system events log

---

## Automatically Tracked Activities

### Member Activities
- ✅ User Login/Logout
- ✅ Profile Updates (name, email, phone)
- ✅ Password Changes

### Case Activities
- ✅ Case Creation
- ✅ Case Submission
- ✅ Case Status Changes
- ✅ Case Reassignment
- ✅ Case Resubmission
- ✅ Case Placed on Hold
- ✅ Case Resumed from Hold
- ✅ Case Tier Changes
- ✅ Case Details Edited

### Document Activities
- ✅ Document Upload
- ✅ Document View
- ✅ Document Download
- ✅ Document Deletion

### Quality Review Activities
- ✅ Quality Review Submission
- ✅ Review Status (Approved/Revisions/Corrections)

### User Management Activities
- ✅ User Creation
- ✅ User Updates
- ✅ User Deletion
- ✅ User Role/Level Changes

### System Events
- ✅ Member Profile Changes
- ✅ Quarterly Credit Reset
- ✅ Bulk Credit Reset
- ✅ Email Notifications Sent
- ✅ Cron Job Execution
- ✅ Audit Log Access
- ✅ Bulk Data Exports
- ✅ Report Generation

---

## Using the Audit Log

### Main Audit Log
**URL:** `/audit-log/`

**Features:**
- Search and filter audit entries
- View detailed information for each entry
- Export to CSV
- View case-specific audit trails

**How to Use:**
1. Navigate to Audit Log
2. Use search to find specific entries
3. Filter by action type, user, date range
4. Click entry for detailed view
5. Export to CSV if needed

---

## Manual Audit Logging (For Developers)

The system provides a service module for manual logging in custom views:

### Importing the Service
```python
from cases.services.case_audit_service import (
    hold_case,
    resume_case,
    change_case_tier,
    log_email_notification,
    log_cron_job_execution,
    log_quarterly_credit_reset,
    log_bulk_credit_reset,
    log_audit_log_access,
    log_bulk_export,
    log_report_generation
)
```

### Example Usage

#### Hold a Case
```python
from cases.services.case_audit_service import hold_case

hold_case(
    case=case_object,
    user=request.user,
    reason="Waiting for additional documentation",
    hold_duration_days=10
)
```

#### Resume a Case
```python
from cases.services.case_audit_service import resume_case

resume_case(
    case=case_object,
    user=request.user,
    reason="Documentation received",
    previous_status="on_hold"
)
```

#### Change Case Tier
```python
from cases.services.case_audit_service import change_case_tier

change_case_tier(
    case=case_object,
    user=request.user,
    new_tier="high_complexity",
    reason="Additional issues identified during review"
)
```

#### Log Cron Job Execution
```python
from cases.services.case_audit_service import log_cron_job_execution

log_cron_job_execution(
    job_name="daily_case_status_update",
    records_processed=156,
    status="success",
    error_msg=None
)
```

#### Log Bulk Export
```python
from cases.services.case_audit_service import log_bulk_export

log_bulk_export(
    user=request.user,
    export_type="cases_csv",
    record_count=500,
    filters="status=completed, date_range=2026-01-01 to 2026-01-31"
)
```

---

## Action Types Reference

### Case Actions (13)
- case_created
- case_updated
- case_submitted
- case_assigned
- case_reassigned
- case_status_changed
- case_details_edited
- case_resubmitted
- case_held
- case_resumed
- case_tier_changed
- (Plus old actions)

### Document Actions (4)
- document_uploaded
- document_viewed
- document_downloaded
- document_deleted

### Review Actions (2)
- review_submitted
- review_updated

### User Actions (5)
- user_created
- user_updated
- user_deleted
- user_role_changed
- member_profile_updated

### System Actions (8)
- cron_job_executed
- quarterly_credit_reset
- bulk_credit_reset
- email_notification_sent
- audit_log_accessed
- bulk_export
- report_generated
- alert_dismissed

### Session Actions (2)
- login
- logout

### Other Actions (2)
- settings_updated
- other

---

## Audit Log Fields

Each audit entry contains:

| Field | Description |
|-------|-------------|
| **Timestamp** | When the activity occurred (UTC) |
| **User** | Who performed the action |
| **Action Type** | Type of activity (37 options) |
| **Case** | Related case (if applicable) |
| **Object ID** | ID of affected object |
| **Description** | Details about what happened |
| **Metadata** | Additional structured data (JSON) |

---

## Access Control

### Who Can Access What

| Report | Member | Technician | Manager | Admin |
|--------|--------|-----------|---------|-------|
| Activity Summary | ✗ | ✗ | ✓ | ✓ |
| User Activity | ✗ | ✗ | ✓ | ✓ |
| Case Changes | ✗ | ✓ | ✓ | ✓ |
| Quality Review | ✗ | ✗ | ✓ | ✓ |
| System Events | ✗ | ✗ | ✗ | ✓ |
| Audit Log | ✗ | ✓ | ✓ | ✓ |

**Note:** Members can only view their own activity through member dashboard

---

## Best Practices

### For Administrators
1. **Regular Review:** Check System Event Report weekly for failed cron jobs
2. **User Monitoring:** Use User Activity Report to identify unusual patterns
3. **Compliance:** Export audit logs monthly for compliance records
4. **Performance:** Archive old entries (>1 year) to keep database performant

### For Managers
1. **Case Tracking:** Use Case Change History to audit case workflow
2. **Quality Assurance:** Monitor Quality Review Report for review trends
3. **Activity Analysis:** Use Activity Summary for team productivity insights
4. **User Performance:** Track individual user activity with User Activity Report

### For Technicians
1. **Case Audit:** Use case audit trail when investigating case issues
2. **Documentation:** Ensure all case changes are properly documented
3. **Quality:** Monitor quality review feedback for improvements

---

## Troubleshooting

### No Data Appearing in Reports
1. Check date range (default is last 30 days)
2. Verify user has activities in selected period
3. Clear browser cache and refresh
4. Contact administrator if issue persists

### Report Loading Slowly
1. Use narrower date range
2. Filter by specific criteria if available
3. Try accessing during off-peak hours
4. Contact system administrator for database optimization

### Missing Entries in Audit Log
- Note: There may be a brief delay (1-2 seconds) before entries appear
- Refresh the page to see latest entries
- Contact administrator if systematic gaps noticed

---

## API Integration (For Developers)

All audit data is accessible via the Django ORM:

```python
from core.models import AuditLog
from django.utils import timezone
from datetime import timedelta

# Get all case-related activities in last 7 days
recent_activities = AuditLog.objects.filter(
    action_type__startswith='case_',
    timestamp__gte=timezone.now() - timedelta(days=7)
).order_by('-timestamp')

# Get activities by specific user
user_activities = AuditLog.objects.filter(
    user=request.user
).order_by('-timestamp')

# Get all failed cron jobs
failed_jobs = AuditLog.objects.filter(
    action_type='cron_job_executed',
    description__icontains='failed'
)
```

---

## Support & Documentation

- **Complete Implementation Guide:** See `AUDIT_TRAIL_IMPLEMENTATION_COMPLETE.md`
- **Activity Analysis:** See `AUDIT_TRAIL_ACTIVITY_ANALYSIS.md`
- **For Technical Details:** Review code in `cases/services/case_audit_service.py`
- **For Questions:** Contact the development team

---

## Version Information

- **Implementation Date:** January 17, 2026
- **Last Updated:** January 17, 2026
- **System:** Django-based Advisor Portal
- **Status:** Production Ready

