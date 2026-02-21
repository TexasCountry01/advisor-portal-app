# Scheduled Case Release System - Setup Guide

## Overview

The Advisor Portal now includes a scheduled case release system that allows technicians to control when completed cases become visible to members. This feature provides flexibility in case handling and prevents members from seeing cases before technicians are ready to release them.

## How It Works

### Technician Workflow

1. **Mark Case as Complete**: When a technician completes their work on a case, they click "Mark as Completed"
2. **Choose Release Option**:
   - **Release Now**: Case becomes visible to member immediately
   - **Schedule Release**: Case will be released on a specific date (default is 7 days from completion)
3. **Confirmation**: The case status changes to "Completed" and release date is stored

### Member Visibility

Members can only see completed cases after the `actual_release_date` is set:
- Cases with **Draft, Submitted, Accepted** status are always visible
- Cases with **Completed** status are only visible after they've been released
- The member dashboard filters automatically exclude unreleased completed cases
- When viewing a completed case, members see the release date

### Automatic Release

Scheduled cases are automatically released via a daily batch job:
- Runs once per day (recommended time: midnight)
- Finds all cases where `scheduled_release_date <= today` and `actual_release_date IS NULL`
- Sets `actual_release_date` to current timestamp
- Can be run manually or via cron job

## Database Schema

Two new fields added to the `Case` model:

```python
scheduled_release_date = models.DateField(
    null=True, blank=True,
    help_text='Date when completed case will be released to member'
)

actual_release_date = models.DateTimeField(
    null=True, blank=True,
    help_text='Actual date/time when case was released to member'
)
```

## Batch Job Command

### Running the Release Job

#### Manual Execution

```bash
# Release all eligible scheduled cases
python manage.py release_scheduled_cases

# Preview what would be released (dry-run mode)
python manage.py release_scheduled_cases --dry-run
```

#### Via Cron Job (Recommended)

Add to your crontab to run daily at midnight:

```bash
0 0 * * * cd /home/dev/advisor-portal-app && /home/dev/advisor-portal-app/venv/bin/python manage.py release_scheduled_cases
```

**To add to crontab:**
```bash
crontab -e
# Add the line above
# Save and exit
```

**To verify cron is set up:**
```bash
crontab -l
```

#### Via Systemd Timer (Alternative)

Create `/etc/systemd/system/release-cases.service`:

```ini
[Unit]
Description=Release scheduled cases in Advisor Portal
After=network.target

[Service]
Type=oneshot
User=www-data
WorkingDirectory=/home/dev/advisor-portal-app
ExecStart=/home/dev/advisor-portal-app/venv/bin/python manage.py release_scheduled_cases
```

Create `/etc/systemd/system/release-cases.timer`:

```ini
[Unit]
Description=Daily release scheduled cases timer

[Timer]
OnCalendar=daily
OnCalendar=*-*-* 00:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

Enable the timer:
```bash
sudo systemctl daemon-reload
sudo systemctl enable release-cases.timer
sudo systemctl start release-cases.timer
sudo systemctl list-timers release-cases.timer
```

## File Changes

### 1. Model Changes
**File**: `cases/models.py`
- Added `scheduled_release_date` field (DateField)
- Added `actual_release_date` field (DateTimeField)

### 2. Views
**File**: `cases/views.py`
- Updated `mark_case_completed()` to accept `release_option` and `release_date` parameters
- Updated `member_dashboard()` to filter out unreleased completed cases
- Uses `release_option='now'` for immediate release
- Uses `release_option='schedule'` with `release_date` for scheduled release

### 3. Templates
**File**: `cases/templates/cases/case_detail.html`
- Added release options modal with date picker
- Updated `markCaseCompleted()` JavaScript function
- Added `confirmCaseCompletion()` function to handle modal submission
- Added release status display for members

### 4. Management Command
**File**: `cases/management/commands/release_scheduled_cases.py`
- Batch job to release scheduled cases
- Supports dry-run mode (`--dry-run` flag)
- Updates `actual_release_date` when cases are released
- Provides status reporting

### 5. Database Migration
**File**: `cases/migrations/0013_case_actual_release_date_case_scheduled_release_date.py`
- Adds the two new fields to the cases_case table

## User Interface Changes

### For Technicians

When marking a case as complete, they now see a modal with options:

```
┌─────────────────────────────────────────────────────────────┐
│ When should this case be released to the member?            │
├─────────────────────────────────────────────────────────────┤
│ ◉ Release Now                                               │
│   Member can view the completed case immediately            │
│                                                             │
│ ○ Schedule Release                                          │
│   Member will see the case on a specific date              │
│   [Date picker appears when selected]                      │
│                                                             │
│ [Cancel]  [Confirm Release]                                │
└─────────────────────────────────────────────────────────────┘
```

**Default behavior**: 
- If "Schedule Release" is selected without a date, defaults to 7 days from now
- Minimum date is always 7 days in the future (can be extended with custom date picker)

### For Members

Completed cases now show release status:

```
┌─────────────────────────────────────────────────────────────┐
│ Release Status                                              │
├─────────────────────────────────────────────────────────────┤
│ ✓ This case was released on:                               │
│   November 15, 2024 at 3:30 PM                             │
│                                                             │
│ OR (if still scheduled)                                     │
│                                                             │
│ ℹ This case is scheduled to be released on:                │
│   November 20, 2024                                         │
└─────────────────────────────────────────────────────────────┘
```

## Testing

### Test Workflow

1. **As Technician**:
   ```
   1. Create/Find a case with status "accepted"
   2. Click "Mark as Completed"
   3. Choose "Schedule Release" and select date 5 days from now
   4. Verify case shows in completed cases (not visible to member yet)
   ```

2. **As Member**:
   ```
   1. Cannot see the completed case in dashboard
   2. Cannot access via direct URL (permission check)
   ```

3. **Run Batch Job**:
   ```bash
   # Dry-run first to see what would happen
   python manage.py release_scheduled_cases --dry-run
   
   # Actually release (after moving system date or changing test data)
   python manage.py release_scheduled_cases
   ```

4. **Verify Release**:
   ```
   1. As Member, refresh dashboard - case now appears
   2. View case detail - shows release date and time
   3. Check database: SELECT * FROM cases_case WHERE id=X;
   ```

### Manual Testing with Test Data

```bash
# 1. Create a completed case scheduled for release
python manage.py shell
>>> from cases.models import Case
>>> from datetime import date, timedelta
>>> case = Case.objects.create(
...     member_id=1,
...     external_case_id='TEST-001',
...     status='completed',
...     scheduled_release_date=date.today() - timedelta(days=1),  # Past date
...     urgency='normal'
... )

# 2. Test the batch job in dry-run mode
python manage.py release_scheduled_cases --dry-run

# 3. Run for real
python manage.py release_scheduled_cases

# 4. Verify in member dashboard (the case now appears)
```

## Troubleshooting

### Batch Job Not Running

**Check if cron is active**:
```bash
ps aux | grep cron
```

**View cron logs** (on Linux):
```bash
sudo tail -f /var/log/syslog | grep CRON
```

**Manually test the command**:
```bash
cd /home/dev/advisor-portal-app
./venv/bin/python manage.py release_scheduled_cases
```

### Cases Not Releasing

**Check scheduled cases**:
```bash
python manage.py shell
>>> from cases.models import Case
>>> from datetime import date
>>> Case.objects.filter(
...     status='completed',
...     scheduled_release_date__lte=date.today(),
...     actual_release_date__isnull=True
... ).values('external_case_id', 'scheduled_release_date')
```

**Manually run the job**:
```bash
python manage.py release_scheduled_cases --dry-run
python manage.py release_scheduled_cases
```

### Member Can't See Released Cases

**Check if case is marked as released**:
```bash
python manage.py shell
>>> from cases.models import Case
>>> case = Case.objects.get(external_case_id='CASE-ID')
>>> print(f"Status: {case.status}")
>>> print(f"Actual Release: {case.actual_release_date}")
```

**Check member dashboard filtering**:
- Member dashboard uses: `status='completed' AND actual_release_date IS NOT NULL`
- Verify `actual_release_date` is set in database

## Default Configuration

- **Default Release Period**: 7 days from completion
- **Batch Job Frequency**: Daily (recommended midnight)
- **Minimum Scheduled Date**: 7 days from completion
- **Timezone**: Uses Django's `timezone.now()` for `actual_release_date`

## Future Enhancements

### Planned Features

1. **Email Notifications**: Send member an email when case is released
2. **Celery Integration**: Real-time release without waiting for cron job
3. **Release Notes**: Allow technician to add notes visible only after release
4. **Conditional Release**: Release based on custom conditions (e.g., after payment)
5. **Release History**: Track all release events and who triggered them
6. **Bulk Operations**: Release multiple cases at once
7. **Release Reminders**: Notify technician before auto-release date
8. **Admin Override**: Allow admins to manually release scheduled cases early

### Implementation Steps (Future)

To add email notifications:
```python
# In mark_case_completed view
if actual_release_date:
    send_case_released_email(case, case.member)
```

To add Celery:
```python
# Instead of batch job, schedule async task
from celery import shared_task
@shared_task
def release_case(case_id):
    # Release logic
```

## API Integration

If external systems need to release cases programmatically:

```bash
# Future API endpoint (not yet implemented)
POST /api/cases/{case_id}/release/
{
    "release_option": "now",  # or "schedule"
    "release_date": "2024-12-25"  # optional
}
```

## Support and Monitoring

### Key Metrics to Monitor

1. **Cases Released Daily**: 
   ```bash
   python manage.py shell
   >>> from cases.models import Case
   >>> from datetime import date
   >>> Case.objects.filter(
   ...     actual_release_date__date=date.today()
   ... ).count()
   ```

2. **Pending Releases**:
   ```bash
   >>> from datetime import date
   >>> Case.objects.filter(
   ...     status='completed',
   ...     scheduled_release_date__isnull=False,
   ...     actual_release_date__isnull=True
   ... ).count()
   ```

3. **Average Release Delay**:
   ```bash
   >>> from django.db.models import F, ExpressionWrapper, DurationField
   >>> from datetime import datetime
   >>> cases = Case.objects.filter(
   ...     actual_release_date__isnull=False
   ... ).annotate(
   ...     delay=ExpressionWrapper(
   ...         F('actual_release_date') - F('date_completed'),
   ...         output_field=DurationField()
   ...     )
   ... )
   ```

## Contact and Questions

For questions about the scheduled release system, refer to:
- Technical Requirements: `docs/technical-requirements.md`
- Development Plan: `docs/development-plan.md`
- Admin Dashboard Documentation: `docs/ADMIN_DASHBOARD_IMPLEMENTATION.md`
