# Option 2: Due Date Urgency Warning - Implementation Complete

**Date:** January 24, 2026  
**Status:** ✅ DEPLOYED TO TEST SERVER  
**Commit:** aa8008a

---

## Overview

Successfully implemented **Option 2: Show Warning but Allow Submission** for handling due date urgency changes when submitting draft cases.

**What it does:**
- When a member attempts to submit a draft case, the system checks if the urgency has changed
- If urgency changed from **normal** to **rush** (due date now within 7 days), a warning dialog is shown
- User can proceed with submission (urgency updates) or cancel to revise the due date
- Submission completes successfully even if urgency is marked as rush

---

## Implementation Details

### Backend Changes

**File:** `cases/views.py` - `submit_case_final()` view

**What was added:**

```python
# OPTION 2: Check if urgency has changed since draft was created
# Calculate current urgency based on today's date
from datetime import timedelta, date
today = date.today()
default_due_date = today + timedelta(days=7)

# Calculate what the urgency should be based on current date
current_urgency = 'rush' if case.date_due < default_due_date else 'normal'
stored_urgency = case.urgency

# Check if urgency changed from normal to rush
urgency_changed = (stored_urgency == 'normal' and current_urgency == 'rush')

# If this is a check-only request (from frontend), return urgency status
check_only = request.POST.get('check_only') == 'true'
if check_only:
    return JsonResponse({
        'success': True,
        'urgency_changed': urgency_changed,
        'stored_urgency': stored_urgency,
        'current_urgency': current_urgency,
        'message': 'This case is now marked as RUSH. Your due date is within 7 days. Continue?'
    })

# Update case urgency to current value
if current_urgency != stored_urgency:
    case.urgency = current_urgency
```

**Key features:**
- Calculates urgency based on **current date** (not draft creation date)
- Returns urgency change status for frontend to process
- Automatically updates urgency when saving
- Supports "check-only" requests from frontend

### Frontend Changes

**File:** `cases/templates/cases/member_dashboard.html` - `submitCaseFinal()` function

**What was added:**

```javascript
// OPTION 2: Check if urgency has changed before submission
function submitCaseFinal(caseId) {
    const formData = new FormData();
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || getCookie('csrftoken');
    
    // First, check if urgency has changed
    formData.append('check_only', 'true');
    
    fetch(`/cases/${caseId}/submit-final/`, {
        method: 'POST',
        body: formData,
        headers: {
            'X-CSRFToken': csrfToken
        }
    })
    .then(response => response.json())
    .then(checkData => {
        if (checkData.urgency_changed) {
            // Urgency changed from normal to rush - show warning modal
            const message = `⚠️ RUSH ALERT\n\nThis case is now marked as RUSH. Your due date is within 7 days.\n\nYou can proceed with submission or cancel to revise the due date.`;
            
            if (confirm(message)) {
                // User confirmed - proceed with actual submission
                performActualSubmission(caseId, csrfToken);
            }
            // If user cancels, do nothing
        } else {
            // Urgency hasn't changed - proceed with submission
            performActualSubmission(caseId, csrfToken);
        }
    })
    .catch(error => {
        console.error('Error checking urgency:', error);
        // Fallback to original behavior with simple confirmation
        if (!confirm('Are you sure you want to submit this case? It will be sent to the technician queue.')) {
            return;
        }
        performActualSubmission(caseId, csrfToken);
    });
}
```

**Key features:**
- Two-phase submission: check first, then submit
- Shows clear warning dialog when urgency changed
- User choice: proceed or cancel
- Fallback behavior if check fails
- No hard blocking - submission is allowed

---

## User Experience Flow

### Scenario 1: Normal Case (no urgency change)
```
1. Member clicks "Submit" on draft case
2. Frontend checks urgency
3. Backend returns: urgency_changed = false
4. Frontend proceeds directly to submission
5. Case submitted successfully
```

### Scenario 2: Case Becomes Rushed
```
1. Member created case on Jan 10 with due date Jan 20 (normal - 10 days out)
2. Member returns on Jan 18 to submit
3. Due date is now Jan 20 (2 days away - should be rush)
4. Member clicks "Submit"
5. Frontend checks urgency
6. Backend detects: stored='normal', current='rush'
7. Backend returns: urgency_changed = true
8. Frontend shows warning dialog:
   
   ⚠️ RUSH ALERT
   
   This case is now marked as RUSH. Your due date is within 7 days.
   
   You can proceed with submission or cancel to revise the due date.
   
   [OK] [Cancel]
   
9. If member clicks OK: Case submitted with urgency updated to 'rush'
10. If member clicks Cancel: Returns to case, no changes made
```

---

## Testing Results

All tests passed locally:

```
============================================================
OPTION 2 URGENCY IMPLEMENTATION TEST SUITE
============================================================

✅ TEST 1: Urgency Calculation Logic
   ✓ Due date 2026-02-03 (10 days away): Is rushed = False
   ✓ Due date 2026-01-29 (5 days away): Is rushed = True
   ✓ Due date 2026-01-31 (7 days away): Is rushed = False

✅ TEST 2: Urgency Change Detection
   ✓ Scenario 1: Normal case stays normal
   ✓ Scenario 2: Case becomes rush is detected

✅ ALL TESTS PASSED!
```

---

## Deployment Status

**Git:**
- ✅ Commit: aa8008a
- ✅ Pushed to GitHub (main branch)
- ✅ Pulled on TEST server

**TEST Server:**
- ✅ Gunicorn workers: 3 running
- ✅ Web: HTTP 200 OK
- ✅ Code: Latest commit aa8008a

**Migrations:**
- ✅ No new migrations needed
- ✅ No database schema changes

---

## Key Design Decisions

### Why Option 2?
- **✅ Transparency:** User knows urgency has changed
- **✅ Flexibility:** User can choose to proceed or revise
- **✅ Non-blocking:** Submission not prevented by urgency
- **✅ Good UX:** Clear warning without frustration

### Urgency Calculation
- Based on **current date**, not creation date
- Threshold: **7 days from today**
- Trigger: Due date < 7 days from today
- Updates automatically when saving

### Two-Phase Submission
1. **Check Phase:** Lightweight POST with `check_only=true` to get urgency status
2. **Submit Phase:** Full submission with status and date updates
3. **Benefits:** Minimal latency, clear separation of concerns

---

## Files Modified

1. **cases/views.py**
   - Modified: `submit_case_final()` function
   - Lines: ~1595-1664
   - Changes: Added urgency change detection and check-only request handling

2. **cases/templates/cases/member_dashboard.html**
   - Modified: `submitCaseFinal()` and new `performActualSubmission()` functions
   - Lines: ~368-441
   - Changes: Added two-phase submission with urgency checking

3. **test_option2_urgency.py** (new)
   - Created comprehensive test suite
   - Tests urgency calculation and change detection
   - Tests both normal and rush cases

---

## Next Steps / Future Enhancements

1. **Enhanced UI Modal:** Replace `confirm()` with Bootstrap modal for better UX
2. **Email Notification:** Notify user when saved draft becomes rushed
3. **Audit Logging:** Log when urgency auto-updated (compliance/audit trail)
4. **Edge Cases:** Handle when due date is in the past
5. **Fee Display:** Show rush fee prominently in warning dialog

---

## Rollback Plan

If issues occur on TEST server:
```bash
git log --oneline  # Find previous commit
git reset --hard eadfc10  # Rollback to previous known-good state
# No database changes needed - no migrations
```

---

## Questions & Answers

**Q: What if the user ignores the warning and clicks OK?**
A: Submission proceeds normally with urgency updated to 'rush' and case submitted successfully.

**Q: Can the user still submit if they click Cancel?**
A: Yes - they can either revise the due date or click Submit again.

**Q: Does this charge differently for rush cases?**
A: This implementation only detects and warns about urgency changes. Billing is handled separately by the system settings.

**Q: What about cases that become rush multiple times?**
A: Each time they try to submit, the check runs. If urgency is already 'rush', no warning is shown (no change to detect).

**Q: Is this backward compatible?**
A: Yes - if check fails, fallback to original simple confirmation dialog.

---

**Implementation Status: ✅ COMPLETE**  
**Deployed to TEST Server: ✅ YES**  
**Ready for Production: ✅ YES (pending final testing)**

