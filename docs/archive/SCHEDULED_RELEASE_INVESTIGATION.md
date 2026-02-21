# Scheduled Release Investigation Report - 01/11/2026

## Summary
**Status**: ✅ **FEATURE EXISTS BUT NEEDS MEMBER ACCESS CONTROL FIX**

The scheduled release system is mostly implemented, but there's a critical bug: members can see technician reports and documents even before the case is released.

---

## Current Implementation

### 1. Database Fields ✅
Located in [cases/models.py](cases/models.py#L156-L170):

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

**Functionality**:
- `scheduled_release_date`: When admin/tech schedules a release (e.g., 7 days from completion)
- `actual_release_date`: When the release actually happens (set automatically or when case is completed)

---

### 2. Automatic Release Job ✅
**File**: `cases/management/commands/release_scheduled_cases.py`

**How it works**:
```bash
python manage.py release_scheduled_cases          # Runs manually
python manage.py release_scheduled_cases --dry-run # Preview mode
```

**Logic**:
- Runs once per day (should be scheduled via cron)
- Finds all cases where: `status='completed'` AND `scheduled_release_date <= today` AND `actual_release_date IS NULL`
- Sets `actual_release_date = timezone.now()` for each case
- Logs results

**Schedule Command** (should be added to crontab):
```bash
0 0 * * * cd /path/to/app && python manage.py release_scheduled_cases
```

**Status**: ✅ Command works correctly, just needs to be scheduled

---

### 3. Member Dashboard Filtering ✅
**File**: [cases/views.py](cases/views.py#L30-L95) (lines 30-95)

**Current behavior**:
```python
stats = {
    'total_cases': Case.objects.filter(member=user).count(),
    'draft': Case.objects.filter(member=user, status='draft').count(),
    'submitted': Case.objects.filter(member=user, status='submitted').count(),
    'accepted': Case.objects.filter(member=user, status='accepted').count(),
    'completed': Case.objects.filter(member=user, status='completed', actual_release_date__isnull=False).count(),
}
```

✅ Shows released completed cases only (those with `actual_release_date`)
✅ Hides unreleased completed cases from dashboard count

---

### 4. Case Detail Access Control - PARTIALLY IMPLEMENTED

**File**: [cases/views.py](cases/views.py#L623-L705) (lines 623-705)

**Member can view**:
- Their own cases (status check)
- Cannot edit submitted/accepted/completed cases
- Can upload documents to draft/completed cases

**ISSUE**: No access control to prevent viewing technician's report before release

---

### 5. Template Display - HAS BUGS ⚠️

**File**: [cases/templates/cases/case_detail.html](cases/templates/cases/case_detail.html)

#### Section 1: Release Status (lines 369-393) ✅
```html
{% if case.status == 'completed' and user.role != 'member' %}
    <!-- Shows to tech/admin/manager only -->
    Displays: scheduled_release_date OR actual_release_date
{% endif %}
```
✅ **CORRECT**: Hidden from members

#### Section 2: Submitted Documents (lines 415-542) ✅
```html
<!-- Shows member's uploaded documents -->
Members can always see this
```
✅ **CORRECT**: Shows what member submitted

#### Section 3: Reports (lines 684-738) ⚠️ **BUG**
```html
<!-- NO ROLE CHECK! -->
<div class="card mb-4">
    <h5 class="mb-0">Reports</h5>
    {% if case.reports.all %}
        <!-- ALL USERS SEE THIS -->
        Shows tech-uploaded reports
    {% endif %}
</div>
```
❌ **BUG**: Members can see technician reports even if not released!

#### Section 4: Additional Documents (lines 740-770) ⚠️ **BUG**
```html
<!-- NO ROLE CHECK! -->
<div class="card mb-4">
    <h5 class="mb-0">Additional Documents</h5>
    {% if tech_documents %}
        <!-- ALL USERS SEE THIS -->
        Shows tech-uploaded documents
    {% endif %}
</div>
```
❌ **BUG**: Members can see technician documents even if not released!

#### Section 5: Right Column Actions (lines 782+) ✅
```html
{% if user.role != 'member' %}
    <!-- Tech/admin/manager controls -->
    Assignment, review, completion buttons
{% endif %}
```
✅ **CORRECT**: Hidden from members

---

## The Problem

### Current State
1. Member submits case → Status: "submitted"
2. Technician assigns case to themselves → Status: "accepted"
3. Technician uploads report and documents → Status: "completed"
4. Admin schedules release for 7 days later
5. **PROBLEM**: Member can IMMEDIATELY see the technician's report and documents in case_detail.html

### What Should Happen
1. Case shows as "working" (or "completed" with "pending release" note)
2. Member sees their submission but NOT the technician's work
3. When release date arrives, status changes to "completed" (release visible)
4. Member can now see full case with technician's report

---

## Status Choices Issue

Current STATUS_CHOICES in [cases/models.py](cases/models.py#L36-L45):
```python
STATUS_CHOICES = [
    ('draft', 'Draft'),
    ('submitted', 'Submitted'),
    ('resubmitted', 'Resubmitted'),
    ('accepted', 'Accepted'),
    ('hold', 'Hold'),
    ('pending_review', 'Pending Review'),
    ('completed', 'Completed'),
]
```

⚠️ **Issue**: No "working" status for cases awaiting release
- Should add: `('working', 'Working')`
- OR use `completed` with `actual_release_date` check

**Recommendation**: Use existing `completed` status + `actual_release_date` check

---

## Fixes Needed

### Fix 1: Add Release Date Check to Views ⚠️ CRITICAL
**File**: `cases/views.py` (case_detail function)

After line 703, before rendering context, add:
```python
# Check if member can view released case details
can_view_report = True
if user.role == 'member' and case.member == user:
    # Members can only see tech reports after release
    if case.status == 'completed' and case.actual_release_date is None:
        can_view_report = False
        # Show "working" message instead of full case
```

Pass to context:
```python
context = {
    ...
    'can_view_report': can_view_report,
}
```

### Fix 2: Update Template to Hide Tech Documents ⚠️ CRITICAL
**File**: `cases/templates/cases/case_detail.html`

**Around line 684** (Reports section):
```html
<!-- BEFORE -->
<!-- Reports -->
<div class="card mb-4">

<!-- AFTER -->
<!-- Reports (Tech/Admin/Manager only OR member if released) -->
{% if user.role != 'member' or case.actual_release_date %}
    <div class="card mb-4">
```

**Around line 740** (Additional Documents section):
```html
<!-- BEFORE -->
<!-- Additional Documents -->
<div class="card mb-4">

<!-- AFTER -->
<!-- Additional Documents (Tech/Admin/Manager only OR member if released) -->
{% if user.role != 'member' or case.actual_release_date %}
    <div class="card mb-4">
```

### Fix 3: Add "Pending Release" Message ✅ NICE-TO-HAVE
Show members when case is completed but not yet released:
```html
{% if user.role == 'member' and case.status == 'completed' and case.actual_release_date is None %}
    <div class="alert alert-info">
        <i class="bi bi-clock"></i>
        <strong>This case is complete and scheduled to be released on {{ case.scheduled_release_date|date:"F j, Y" }}</strong>
    </div>
{% endif %}
```

### Fix 4: Schedule Cron Job ✅ DEPLOYMENT
Add to server crontab:
```bash
# Release scheduled cases daily at midnight
0 0 * * * cd /var/www/advisor-portal-app && /path/to/venv/bin/python manage.py release_scheduled_cases
```

---

## Testing Scenarios

### Test 1: Member Cannot See Unreleased Case Report
```
1. Create case as member → Status: submitted
2. Assign to technician → Status: accepted
3. Tech uploads report → Status: completed, scheduled_release_date=7 days from now
4. Member views case detail
5. Expected: See their submission, NOT tech report
6. Actual: Currently SEES tech report (BUG)
```

### Test 2: Member Can See Released Case
```
1. Same as Test 1 but release_date is past
2. Run: python manage.py release_scheduled_cases
3. actual_release_date is now set
4. Member views case detail
5. Expected: Sees full case with tech report
6. Actual: Should work after fix
```

### Test 3: Dashboard Excludes Unreleased Cases
```
1. Member has 3 completed cases
2. 2 are released, 1 is waiting
3. Dashboard shows count = 2
4. Expected: Works correctly
5. Actual: ✅ Already working
```

---

## Documentation References
- [SCHEDULED_CASE_RELEASE_SETUP.md](docs/SCHEDULED_CASE_RELEASE_SETUP.md) - Full setup guide
- [QUICK_REFERENCE.md](QUICK_REFERENCE.md#L216) - Release requirements
- [COMPLETED_CASE_RESUBMISSION.md](COMPLETED_CASE_RESUBMISSION.md#L10-L25) - Field descriptions

---

## Summary Table

| Component | Status | Notes |
|-----------|--------|-------|
| Database Fields | ✅ Working | `scheduled_release_date`, `actual_release_date` |
| Management Command | ✅ Working | Needs cron scheduling |
| Dashboard Filtering | ✅ Working | Correctly hides unreleased cases |
| View Permission Check | ❌ Missing | Needs release date check |
| Template - Reports | ❌ Bug | Shows to all roles before release |
| Template - Tech Docs | ❌ Bug | Shows to all roles before release |
| "Pending Release" Message | ⚠️ Missing | Nice-to-have for UX |
| Cron Job | ⚠️ Not Active | Needs to be scheduled |

---

## Recommended Implementation Order

1. **FIX 1**: Add member access control to case_detail view (5 min)
2. **FIX 2**: Update template to hide reports/docs before release (5 min)
3. **FIX 3**: Add pending release message (5 min)
4. **TEST**: Verify all scenarios work
5. **DEPLOY**: Schedule cron job on production server

**Total Implementation Time**: ~30 minutes + testing
