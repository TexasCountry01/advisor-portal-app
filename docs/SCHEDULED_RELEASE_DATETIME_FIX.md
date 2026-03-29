# Fix: Same-Day Scheduled Release Now Supports Time

**Date:** March 17, 2026  
**Commit:** `36ff299`  
**Status:** Deployed to TEST

---

## Problem

Staff could not schedule a same-day email/case release for later in the day. The system only supported "immediately" or "next day and beyond." The UI showed a time picker, but the selected time was silently discarded.

**Root cause:** Two model fields (`scheduled_release_date` and `scheduled_email_date`) were `DateField` — storing only the date with no time component. The cron jobs compared against `date.today()`, so anything scheduled for "today" would either fire at the next midnight run or not at all depending on timing.

---

## What Changed

### 1. Model Fields — DateField → DateTimeField

**File:** `cases/models.py`

| Field | Before | After |
|-------|--------|-------|
| `scheduled_release_date` | `DateField` | `DateTimeField` |
| `scheduled_email_date` | `DateField` | `DateTimeField` |

**Migration:** `cases/migrations/0034_scheduled_release_datetime.py`

### 2. Views — Store Full Datetime

**File:** `cases/views.py`

**Completion view (~line 2960):**
```python
# Before
case.scheduled_release_date = release_dt_utc.date()
case.scheduled_email_date = release_dt_utc.date()

# After
case.scheduled_release_date = release_dt_utc
case.scheduled_email_date = release_dt_utc
```

**Reschedule view (~line 1618):** Same change — stores full UTC datetime instead of `.date()`.

### 3. Cron Commands — DateTime Comparison

**Files:**
- `cases/management/commands/release_scheduled_cases.py`
- `cases/management/commands/send_scheduled_emails.py`

```python
# Before
today = date.today()
cases_to_release = Case.objects.filter(scheduled_release_date__lte=today, ...)

# After
now = timezone.now()
cases_to_release = Case.objects.filter(scheduled_release_date__lte=now, ...)
```

### 4. Templates — Display Time in Scheduled Dates

Updated date format from `m/d/Y` to `m/d/Y g:i A` (includes time) in:

| Template | Location |
|----------|----------|
| `case_detail.html` | Scheduled release display (3 locations) |
| `admin_dashboard.html` | Release date column |
| `manager_dashboard.html` | Release date column |

---

## Cron Job Frequency Change Required

For same-day releases to work properly, the cron jobs need to run **hourly** instead of daily:

```cron
# Before (daily at midnight UTC)
0 0 * * * cd /var/www/advisor-portal && python manage.py release_scheduled_cases
0 0 * * * cd /var/www/advisor-portal && python manage.py send_scheduled_emails

# After (hourly)
0 * * * * cd /var/www/advisor-portal && python manage.py release_scheduled_cases
0 * * * * cd /var/www/advisor-portal && python manage.py send_scheduled_emails
```

This change needs to be applied on both TEST and PROD crontabs when deploying to those environments.

---

## Backward Compatibility

- Any existing `scheduled_release_date` / `scheduled_email_date` values stored as dates are automatically converted to datetimes at midnight by the database migration
- These will still match correctly with `__lte=now` since midnight is always in the past
- No data loss or manual intervention required

---

## Files Changed

| File | Change |
|------|--------|
| `cases/models.py` | 2 fields: DateField → DateTimeField |
| `cases/views.py` | 2 views: removed `.date()` calls |
| `cases/management/commands/release_scheduled_cases.py` | `date.today()` → `timezone.now()` |
| `cases/management/commands/send_scheduled_emails.py` | `date.today()` → `timezone.now()` |
| `cases/templates/cases/case_detail.html` | 3 date displays include time |
| `cases/templates/cases/admin_dashboard.html` | 1 date display includes time |
| `cases/templates/cases/manager_dashboard.html` | 1 date display includes time |
| `cases/migrations/0034_scheduled_release_datetime.py` | New migration |
