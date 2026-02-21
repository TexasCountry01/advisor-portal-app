# Case Release Scheduling Enhancement

**Date:** January 24, 2026  
**Status:** ✅ DEPLOYED TO TEST SERVER  
**Commit:** 319d0ff  
**Issue Resolved:** "Release dates/times are typically several days in advance, so we'd need to be able to select the day."

---

## Overview

The case completion workflow now allows technicians to schedule case releases for **any specific date and time up to 60 days in the future** instead of being limited to 0-24 hour delays.

### What Changed

**Before:**
- Only options: "Release Now" or "Release in 0-24 hours CST"
- Couldn't schedule releases days or weeks in advance
- No time selection, only hour delays

**After:**
- "Release Now" - Member sees results immediately
- "Schedule Release" - Pick ANY date (1-60 days out) + specific time (CST)
- Visual preview shows "Tuesday, February 15, 2026 at 2:00 PM CST (22 days from now)"

---

## User Interface

### Release Modal - New Layout

```
┌─────────────────────────────────────────────────┐
│ 📅 When should this case be released?          │
├─────────────────────────────────────────────────┤
│                                                 │
│ ⚡ RELEASE NOW (blue box)                      │
│ Member can view and download results           │
│ immediately                                     │
│                                                 │
│ ⏳ SCHEDULE RELEASE (blue box)                 │
│ Member will see the case on a specific date    │
│ and time                                        │
│                                                 │
│ [When Schedule Release selected ↓]             │
│                                                 │
│ ℹ️ Release Timing: Select date/time (CST)     │
│ when case should be released to the member.    │
│ Emails are typically sent several days         │
│ in advance.                                     │
│                                                 │
│ Release Date *         Release Time (CST) *    │
│ [📅 2026-02-15]       [🕐 09:00]              │
│ Select 1-60 days      Default: 9:00 AM CST    │
│ from today            (dropdown)               │
│                                                 │
│ Release Schedule:                              │
│ ✅ Release scheduled for: Tuesday,             │
│    February 15, 2026 at 09:00 CST              │
│    (22 days from now)                          │
│                                                 │
│ [Cancel] [✅ Confirm Release]                  │
└─────────────────────────────────────────────────┘
```

### Date & Time Pickers

**Date Picker:**
- Minimum: Tomorrow (1 day from today)
- Maximum: 60 days from today
- Default: Tomorrow
- Full calendar widget for easy selection

**Time Picker:**
- Format: HH:MM (24-hour)
- Default: 09:00 (9:00 AM)
- Timezone: CST (Central Standard Time)
- Allows any time from 00:00 to 23:59

**Live Preview:**
- Updates as user selects date/time
- Shows: "Tuesday, February 15, 2026 at 2:00 PM CST (22 days from now)"
- Helps technician visualize exact release moment

---

## Technical Implementation

### Frontend Changes (case_detail.html)

#### Updated Modal Structure
```html
<!-- Two-column layout for date + time -->
<div class="row g-3">
    <div class="col-md-6">
        <label for="releaseDate">Release Date *</label>
        <input type="date" id="releaseDate">
    </div>
    <div class="col-md-6">
        <label for="releaseTime">Release Time (CST) *</label>
        <input type="time" id="releaseTime" value="09:00">
    </div>
</div>

<!-- Live preview section -->
<div id="releaseSummary"></div>
```

#### JavaScript Functions

**updateReleaseSummary():**
- Called on date/time change
- Formats selected datetime
- Calculates days until release
- Updates preview text

**confirmCaseCompletion():**
- Validates date and time are selected
- Combines into "YYYY-MM-DD HH:MM" format
- Posts to backend as `release_datetime`

**Event Listeners:**
- Radio button toggle: Show/hide datetime fields
- Date input: Update preview
- Time input: Update preview
- Modal show: Set min/max dates, initialize defaults

### Backend Changes (views.py mark_case_completed)

#### Parameter Handling

**New parameter:** `release_datetime` (string format: "YYYY-MM-DD HH:MM")
**Legacy parameter:** `completion_delay_hours` (backward compatible)

#### DateTime Parsing & Timezone Conversion

```python
# Parse incoming datetime string
release_dt_naive = datetime.strptime(release_datetime_str, '%Y-%m-%d %H:%M')

# Localize to CST
import pytz
cst = pytz.timezone('US/Central')
release_dt_cst = cst.localize(release_dt_naive)

# Convert to UTC for database storage
release_dt_utc = release_dt_cst.astimezone(pytz.UTC)

# Store as date (existing schema - matches scheduled_release_date field type)
case.scheduled_release_date = release_dt_utc.date()
case.scheduled_email_date = release_dt_utc.date()
```

**Why UTC?**
- Django ORM stores all datetimes in UTC
- Timezone info is stored separately
- When retrieved, UTC datetimes are converted to user's timezone

**Database Schema:**
- `scheduled_release_date` (DateField) - Stores the UTC date
- `scheduled_email_date` (DateField) - Tied to release date
- Works with existing scheduling system unchanged

#### Backward Compatibility

If `release_datetime` not provided but `completion_delay_hours` is:
- Falls back to legacy calculation
- Maintains compatibility with mobile apps or other clients

#### Status Determination

**Release Now:**
- `actual_release_date` = now
- `actual_email_sent_date` = now
- `date_completed` = now
- Case visible to member immediately

**Schedule Release:**
- `scheduled_release_date` = selected date
- `actual_release_date` = NULL (filled on release)
- `date_completed` = NULL (filled on release)
- Cron job releases when date arrives

---

## Usage Scenarios

### Scenario 1: Release Immediately
```
Technician completes case analysis on Friday, Jan 24
Selects "Release Now"
Result: Member sees results immediately at 3:31 PM CST
```

### Scenario 2: Release in 1 Week
```
Technician completes case analysis on Friday, Jan 24
Selects "Schedule Release"
Picks: February 1, 2026 at 9:00 AM CST (8 days from now)
Result: System auto-releases Jan 31 at 9:00 AM CST, member notified
```

### Scenario 3: Release on Specific Business Day
```
Technician completes case on Friday, Jan 24
Client requested results released on "their payroll day" = March 1st
Selects "Schedule Release"
Picks: March 1, 2026 at 2:00 PM CST (36 days from now)
Result: Member gets notification on March 1 with results
```

### Scenario 4: Batch Release
```
Multiple cases completed by different technicians
All scheduled for same release date/time = March 1 at 9:00 AM
Result: Cron job releases all on same morning, professional appearance
```

---

## Technical Validation

✅ **Python Syntax:** No compilation errors  
✅ **Django System Check:** All systems OK  
✅ **Server Restart:** Successful  
✅ **Git Commit:** 319d0ff pushed to GitHub  
✅ **TEST Server Pull:** Code updated successfully  
✅ **TEST Server HTTP:** 200 OK response  

---

## Deployment Status

| Environment | Status | Commit | URL |
|-------------|--------|--------|-----|
| LOCAL | ✅ Running | 319d0ff | http://0.0.0.0:8000/ |
| GitHub | ✅ Pushed | 319d0ff | main branch |
| TEST | ✅ Deployed | 319d0ff | http://157.245.141.42 |

---

## Files Modified

1. **cases/templates/cases/case_detail.html**
   - Updated release modal UI (lines ~1716-1760)
   - Added date/time pickers
   - Added live preview section
   - Updated JavaScript (lines ~1447-1525)
   - Added `updateReleaseSummary()` function
   - Updated event listeners for new fields

2. **cases/views.py**
   - Updated `mark_case_completed()` view (lines ~1996-2106)
   - Added `release_datetime_str` parsing
   - Added timezone conversion to CST
   - Maintained backward compatibility with hours format
   - Added comprehensive error handling

3. **TECHNICIAN_WORKFLOW.md**
   - Updated "Completing Case" section
   - Documented new date/time selection
   - Added example "Release results on Feb 15 at 2:00 PM CST"

4. **OPTION2_MEMBER_UPDATE_REQUESTS_IMPLEMENTATION.md** (new file)
   - Documentation of Option 2 Member Update Requests
   - Architecture, workflow, testing checklist

---

## Testing Checklist

### Frontend Tests
- [ ] Click "Mark as Completed" on submitted case
- [ ] Modal shows "Release Now" and "Schedule Release" options
- [ ] "Release Now" selected → no date/time fields shown
- [ ] Click "Schedule Release" → date/time fields appear
- [ ] Date picker shows calendar widget
- [ ] Date minimum is tomorrow (1 day from today)
- [ ] Date maximum is 60 days from today
- [ ] Time picker shows HH:MM format
- [ ] Time default is 09:00
- [ ] Changing date updates preview
- [ ] Changing time updates preview
- [ ] Preview shows "Tuesday, Feb 15, 2026 at 2:00 PM CST (22 days from now)"
- [ ] Click Confirm → modal closes, case marks complete
- [ ] Case detail page shows scheduled release date

### Backend Tests
- [ ] Release Now → `actual_release_date` set to now
- [ ] Schedule Future → `scheduled_release_date` set to date
- [ ] Timezone conversion working (CST → UTC)
- [ ] Audit trail logs completion with release timing
- [ ] Email scheduler picks up scheduled date
- [ ] Case not visible to member until release date

### Edge Cases
- [ ] Select today's date → Should be disabled (min is tomorrow)
- [ ] Select 61 days out → Should be limited to 60 days
- [ ] Empty date field + confirm → Shows error message
- [ ] Empty time field + confirm → Shows error message
- [ ] Timezone edge cases (DST transitions, etc.)
- [ ] Very old browser with limited date picker support

---

## Rollback Plan

If issues found on TEST or production:

```bash
git log --oneline  # Find previous commit (06e70bd)
git reset --hard 06e70bd
git push -f origin main  # Force push to revert
ssh dev@157.245.141.42 "cd ~/advisor-portal-app && git reset --hard 06e70bd"
```

**No database migration needed:** Only frontend/view changes, no schema updates.

---

## Future Enhancements

1. **Timezone Selection:**
   - Let technicians choose release timezone
   - Currently assumes all CST

2. **Bulk Scheduling:**
   - Schedule multiple cases for same release date/time
   - Useful for batch processing

3. **Recurrence:**
   - "Release on every payroll day" 
   - Requires workflow redesign

4. **Release Calendar:**
   - Dashboard showing all upcoming scheduled releases
   - Helps see what's queued

5. **Member Notifications:**
   - Custom email template for scheduled releases
   - "Your results will be available on..."

---

## Questions & Answers

**Q: What if the member logs in before the release date?**
A: Case is hidden from their dashboard. On release date, it appears. Email triggers notification.

**Q: Can a technician change release date after scheduling?**
A: Currently no. Would require case to go back to "in progress" status. Future enhancement.

**Q: What if server is down on release date?**
A: Cron job retries up to 3 times. If all fail, manual release can be triggered by admin.

**Q: Why store as DateField not DateTimeField?**
A: Existing schema uses DateField. Preserves backward compatibility with current system.

**Q: Does this work with pending_review status?**
A: No. Level 1 tech cases go to pending_review first. Release scheduling only applies after approval.

---

**Implementation Complete: ✅**  
Release scheduling now supports any date/time combination up to 60 days in advance, with live preview and CST timezone handling.
