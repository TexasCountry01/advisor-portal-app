# Put on Hold Button - Functionality Analysis

**Date:** January 18, 2026  
**Status:** Analysis Complete - Ready for Implementation  
**Scope:** Case hold/resume workflow with ownership preservation

---

## Overview

The "Put on Hold" button allows technicians/admins to temporarily pause case processing while **maintaining ownership assignment**. When a case is placed on hold:

- ✅ Status changes to 'hold'
- ✅ Current owner (assigned_to) **REMAINS THE SAME**
- ✅ Case must be completed or reassigned by current owner
- ✅ Action is logged to audit trail

---

## Current State Analysis

### What Exists
1. **Service Function** - `cases/services/case_audit_service.py:hold_case()`
   - Takes case, user, reason, hold_duration_days
   - Changes status to 'hold'
   - Logs to AuditLog with action_type='case_held'
   - Does NOT modify assigned_to (ownership)
   - ✅ Correctly preserves ownership

2. **Resume Function** - `cases/services/case_audit_service.py:resume_case()`
   - Resumes from hold back to previous_status (default 'accepted')
   - Logs to AuditLog with action_type='case_resumed'
   - Maintains current owner
   - ✅ Correctly preserves ownership

3. **UI Element** - `cases/templates/cases/case_detail.html:982`
   - "Put on Hold" button exists but is **DISABLED**
   - Shows in technician/admin case view when case is 'accepted'
   - No click handler attached
   - No modal for input

4. **Audit Trail Integration** - ✅ Already implemented
   - `case_held` action type logged
   - `case_resumed` action type logged
   - Metadata includes: reason, duration, timestamp
   - Changes tracked: status transition

### What's Missing
1. **View/URL Handler** - No view function in views.py
2. **Click Handler** - Button is disabled, no onclick action
3. **Modal Dialog** - No form to capture hold reason/duration
4. **Resume Button** - No "Resume from Hold" button for 'hold' status cases
5. **Validation** - No checks for case readiness to hold
6. **Response Handling** - No AJAX or form submission

---

## Business Rules - Put on Hold

### When Can a Case Be Put on Hold?
- ✅ Case must be 'accepted' status (currently processing)
- ✅ User must be the assigned technician/owner
- ✅ At least one report uploaded (best practice)

### What Happens on Hold?
- Status changes: 'accepted' → 'hold'
- **Ownership: UNCHANGED** (assigned_to stays same)
- Technician can add internal notes about why holding
- Case appears in "On Hold" filtered view
- Audit trail records: who, when, why, for how long

### Release Options (From Hold)
**Option 1: Resume Processing**
- Same technician clicks "Resume from Hold"
- Status: 'hold' → 'accepted'
- Ownership: unchanged (same technician)
- Audit trail: case_resumed action logged

**Option 2: Reassign While on Hold**
- Manager/admin reassigns to different technician
- New technician can then resume or continue
- Ownership changes on reassignment
- Original technician action logged

**Option 3: Complete from Hold**
- Technician marks case as completed while on hold
- Status: 'hold' → 'completed'
- Ownership: unchanged (same technician gets credit)

---

## Technical Implementation Plan

### 1. Create Put on Hold Modal (case_detail.html)
```
Modal ID: putOnHoldModal
Fields:
  - Reason (textarea) - Required
  - Hold Duration (select or number) - Optional
    Options: 2 hours, 4 hours, 8 hours, 1 day, Custom
  - Button: "Place on Hold"
```

### 2. Create Resume from Hold Modal (case_detail.html)
```
Modal ID: resumeFromHoldModal
Fields:
  - Resume Reason (textarea) - Required
  - Button: "Resume Processing"
```

### 3. Add View Function (cases/views.py)
```python
@login_required
def put_case_on_hold(request, case_id):
    """Put a case on hold - requires ownership and accepted status"""
    - Check: user is owner (assigned_to == request.user)
    - Check: case status is 'accepted'
    - Get: hold_reason, hold_duration from POST
    - Call: hold_case(case, user, reason, hold_duration_days)
    - Log: audit trail automatically via service
    - Return: JSON success or error
```

### 4. Add Resume View Function (cases/views.py)
```python
@login_required
def resume_case_from_hold(request, case_id):
    """Resume a case from hold"""
    - Check: user is owner (assigned_to == request.user)
    - Check: case status is 'hold'
    - Get: resume_reason from POST
    - Call: resume_case(case, user, reason, previous_status='accepted')
    - Log: audit trail automatically via service
    - Return: JSON success or error
```

### 5. Add URL Routes (cases/urls.py)
```python
path('<int:case_id>/put-on-hold/', views.put_case_on_hold, name='put_on_hold'),
path('<int:case_id>/resume-from-hold/', views.resume_case_from_hold, name='resume_from_hold'),
```

### 6. Update Template Logic (case_detail.html)
```
Current Button State:
- Hidden when case.status != 'accepted'
- Hidden when user != case.assigned_to
- Currently disabled

New Button Behavior:
- Enable when: status == 'accepted' AND user == owner
- On click: Show putOnHoldModal
- Data attributes: case_id for AJAX call

Resume Button (New):
- Show when: status == 'hold' AND user == owner
- On click: Show resumeFromHoldModal
```

### 7. Add AJAX Handlers (case_detail.html JavaScript)
```javascript
function putOnHold() {
    // Get modal values
    // POST to put-on-hold endpoint
    // Handle response, reload case details
}

function resumeFromHold() {
    // Get modal values
    // POST to resume-from-hold endpoint
    // Handle response, reload case details
}
```

---

## Ownership Preservation

### Current Owner Assignment
- Case.assigned_to = Technician ID
- When put on hold: assigned_to **NOT MODIFIED**
- Resume: Same technician sees case in workbench
- Reassignment: Manager/admin can reassign to different tech

### Workflow Example
```
1. Tech1 takes ownership (assigned_to = Tech1)
2. Tech1 uploads reports
3. Tech1 needs break → "Put on Hold"
   - Status: 'accepted' → 'hold'
   - Ownership: Tech1 (unchanged)
   
4. 4 hours later → "Resume from Hold"
   - Status: 'hold' → 'accepted'
   - Ownership: Tech1 (unchanged)
   - Tech1 continues work

5. Alternative: Manager reassigns while on hold
   - Manager assigns to Tech2
   - assigned_to = Tech2
   - Tech2 sees case in workbench
   - Status still 'hold'
   
6. Tech2 can now:
   - Resume (status: 'hold' → 'accepted')
   - Complete (status: 'hold' → 'completed')
   - Or request manager to reassign again
```

---

## Data Audit Trail

### AuditLog Entries (Auto-Generated)
**When Case Placed on Hold:**
```python
Action Type: case_held
Description: "Case #WS001-2025-001 placed on hold"
User: Technician or Manager
Changes: {'status': {'from': 'accepted', 'to': 'hold'}}
Metadata: {
    'reason': 'Waiting for member clarification',
    'held_at': '2026-01-18T10:30:00Z',
    'duration_days': 1
}
```

**When Case Resumed from Hold:**
```python
Action Type: case_resumed
Description: "Case #WS001-2025-001 resumed from hold"
User: Same technician (owner)
Changes: {'status': {'from': 'hold', 'to': 'accepted'}}
Metadata: {
    'reason': 'Member clarification received',
    'resumed_at': '2026-01-18T14:30:00Z',
    'hold_duration': 4.0  # hours
}
```

---

## Role Permissions

### Technician
- ✅ Can put assigned case on hold
- ✅ Can resume own case from hold
- ✅ Cannot hold/resume unassigned cases
- ✅ Cannot hold cases they don't own

### Manager
- ✅ Can put any case on hold (override)
- ✅ Can resume any case from hold
- ✅ Can reassign case while on hold
- ✅ Full visibility of hold/resume history

### Administrator
- ✅ Can put any case on hold
- ✅ Can resume any case from hold
- ✅ Can reassign case while on hold
- ✅ Full system audit trail access

### Member
- ❌ Cannot hold cases
- ❌ Cannot resume cases
- ℹ️ Can see hold status in case timeline

---

## State Transitions

### Valid Status Transitions with Hold

```
SUBMITTED → ACCEPTED → HOLD → ACCEPTED → PENDING REVIEW → COMPLETED
                    ↓
                  COMPLETED (can complete directly from hold)

ACCEPTED → HOLD → ACCEPTED → HOLD → ACCEPTED → ... (multiple holds allowed)
```

### Invalid Transitions
- Cannot hold: 'submitted', 'draft', 'pending_review', 'completed'
- Cannot hold: unassigned cases
- Cannot hold: if not owner

---

## Edge Cases & Validation

### Edge Case 1: Manager Reassigns While Held
```
Tech1 case on hold
Manager reassigns to Tech2
- Status: stays 'hold'
- assigned_to: Tech1 → Tech2
- Tech2 can: resume OR complete OR request reassignment
```

### Edge Case 2: Hold Expires
```
Not currently auto-managed by system
Recommendation: Add scheduled task to auto-resume if needed
Or: Manager/Tech must manually resume
```

### Edge Case 3: Multiple Holds
```
Case can be held multiple times:
- Hold #1: 2 hours
- Resume → Complete part of work
- Hold #2: 4 hours
- Resume → Complete rest
All holds logged to audit trail
```

### Edge Case 4: Hold During Quality Review
```
Current: Cases in 'pending_review' cannot be held
Recommended: Stay this way (prevents workflow breakage)
Manager can reassign if needed
```

---

## Testing Checklist

- [ ] Put case on hold - status changes to 'hold'
- [ ] Ownership unchanged after hold
- [ ] Audit log entry created (case_held)
- [ ] Resume from hold - status returns to 'accepted'
- [ ] Resume audit log entry created (case_resumed)
- [ ] Cannot hold unassigned cases
- [ ] Cannot hold non-'accepted' cases
- [ ] Manager can hold any case
- [ ] Can hold case multiple times
- [ ] Hold reason logged in audit
- [ ] Hold duration logged in audit
- [ ] Resume reason logged in audit
- [ ] Case appears in "On Hold" filtered view
- [ ] History shows all hold/resume events

---

## Implementation Priority

**Phase 1 (IMMEDIATE):**
1. Enable "Put on Hold" button (remove disabled)
2. Add modal form for reason/duration
3. Add view function for put_on_hold
4. Add AJAX handler
5. Add resume button and modal
6. Add resume view function

**Phase 2 (OPTIONAL):**
1. Auto-resume scheduled task
2. Hold duration notifications
3. Manager override indicators

---

## Summary

The infrastructure for case holds already exists via the audit service. What needs to be implemented:

1. **UI:** Enable button, add modals for reason/duration
2. **Views:** Create 2 view functions (hold/resume)
3. **URLs:** Add 2 routes
4. **JavaScript:** Add AJAX handlers
5. **Permissions:** Owner-only access with manager override

**Key Principle:** Ownership (assigned_to) is preserved throughout entire hold/resume cycle. Only the status changes.
