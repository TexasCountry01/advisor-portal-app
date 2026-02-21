# Put on Hold Case Flow - Comprehensive Analysis

**Date:** January 24, 2026  
**Status:** Complete Analysis  
**Focus:** End-to-end flow, dashboard display, enabled/disabled features

---

## 1. INITIATION FLOW

### When a Case Can Be Put on Hold

**Requirements:**
- Case status must be: `accepted` (actively being processed)
- User must be: the assigned technician (owner), manager, or administrator
- If technician: must be the case.assigned_to user
- If manager/admin: can hold any case

**Location:** Case Detail Page → "Put on Hold" button in Actions card

### The Put on Hold Process

**Step 1: Technician Initiates**
```
Case Detail Page → Status: 'accepted'
  ↓
Click "Put on Hold" button
  ↓
Modal appears with form
```

**Step 2: Fill Hold Modal**
- **Hold Reason** (required textarea)
  - Examples: "Waiting for member documents", "Awaiting admin decision", "Need clarification"
  - Free-form text, no character limit (but reasonable)
- **Hold Duration** (dropdown, optional)
  - 2 hours (0.083 days)
  - 4 hours (0.167 days)
  - 8 hours (0.333 days)
  - 1 day
  - Custom (no specific duration)
  - Immediate (resume without warning)

**Step 3: Submit**
```
Click "Place on Hold" button
  ↓
POST to /cases/{id}/put-on-hold/ endpoint
  ↓
Backend processes request
```

### Backend Processing

**File:** `cases/views.py:put_case_on_hold()` (Lines 1038-1259)

**What Happens:**

1. **Permission Validation**
   - Checks user is technician (must own case) OR manager/admin
   - Technician: case.assigned_to == request.user
   - Manager/Admin: no ownership check needed

2. **Case Status Validation**
   - Case MUST be 'accepted'
   - Error if not: "Only cases in 'Accepted' status can be put on hold"

3. **Hold Reason Validation**
   - Reason is required
   - Error if blank: "Please provide a reason for putting the case on hold"

4. **Case Model Update** (via `hold_case()` service)
   ```python
   case.status = 'hold'
   case.hold_reason = reason
   case.hold_start_date = now()
   case.hold_end_date = calculated based on duration
   case.hold_duration_days = duration in days
   case.assigned_to = UNCHANGED  # ✅ OWNERSHIP PRESERVED
   ```

5. **Audit Logging**
   - Action type: `case_held`
   - Records: who, when, why, for how long
   - Metadata includes: hold_reason, hold_duration_days, hold_start_date

6. **Member Notification (if case has member)**
   - Creates CaseNotification record (notification_type='case_put_on_hold')
   - Sends email to case.member.email with:
     - Case ID (external_case_id)
     - Employee name
     - Hold reason from technician
     - Clickable link to case detail
   - Logs notification creation in audit trail

7. **Response to User**
   ```json
   {
     "success": true,
     "message": "Case {id} has been placed on hold. Member has been notified.",
     "new_status": "hold",
     "notification_sent": true
   }
   ```

---

## 2. DASHBOARD DISPLAY

### Member Dashboard

**Display When:** case.status == 'hold'

**Badge:** 
```html
<span class="badge bg-warning">
  <i class="bi bi-pause-circle"></i> On Hold
</span>
```

**Member Sees:**
- ✅ Case ID and employee name
- ✅ Hold status (yellow "On Hold" badge)
- ✅ Current assigned technician
- ✅ Link to case detail
- ✅ Notification icon if unread hold notification
- ✅ Hold reason available in case detail page

**Member Actions Available:**
- ✅ View case detail
- ✅ Upload documents to case (still enabled!)
- ✅ View hold reason (in case detail)
- ✅ Can add comments while on hold
- ❌ Cannot change case or submit new version
- ❌ Cannot change assigned technician (that's tech/admin job)

---

### Technician Dashboard

**Display When:** case.status == 'hold' AND user is assigned OR admin viewing

**Badge:**
```html
<span class="badge bg-warning">
  <i class="bi bi-pause-circle"></i> On Hold
</span>
```

**Technician Sees (if they own the case):**
- ✅ Case ID and member name
- ✅ Hold status (yellow "On Hold" badge)
- ✅ When it was placed on hold
- ✅ Expected resume date (if duration set)
- ✅ Hold reason they provided
- ✅ Ability to resume from hold
- ✅ Member upload notifications (if member uploaded while on hold)

**Available Actions (in case detail):**
- ✅ View case notes and documents
- ✅ Resume from hold (button shows)
- ✅ Add internal notes
- ✅ View member documents uploaded during hold
- ✅ Can reassign case to another tech (manager/admin only)
- ❌ Cannot mark as pending_review or completed while on hold
- ❌ Cannot mark as submitted (wrong status)

---

### Manager Dashboard

**Display When:** case.status == 'hold'

**Badge:**
```html
<span class="badge bg-warning">
  <i class="bi bi-pause-circle"></i> On Hold
</span>
```

**Manager Sees:**
- ✅ All cases on hold across team
- ✅ Which technician owns the case
- ✅ When placed on hold
- ✅ Hold reason provided
- ✅ Expected resume date (if set)

**Available Actions (in case detail):**
- ✅ Resume any case from hold
- ✅ Reassign case while on hold
- ✅ View all hold history in audit trail
- ✅ Can view member documents uploaded during hold
- ✅ Can add notes to held cases
- ❌ Cannot put on hold again (already on hold)
- ❌ Cannot mark as completed while on hold

---

### Administrator Dashboard

**Display When:** case.status == 'hold'

**Badge:**
```html
<span class="badge bg-warning">
  <i class="bi bi-pause-circle"></i> On Hold
</span>
```

**Admin Sees:**
- ✅ All cases on hold across entire system
- ✅ Which technician/manager initiated hold
- ✅ When placed on hold
- ✅ Hold reason provided
- ✅ Expected resume date
- ✅ Full audit trail of all actions
- ✅ Member contact info for follow-up

**Available Actions (in case detail):**
- ✅ Resume any case from hold
- ✅ Reassign to any technician
- ✅ View complete hold history
- ✅ Can force complete case while on hold
- ✅ Can view all member communications
- ✅ Override any restrictions

---

## 3. FUNCTIONALITY - ENABLED vs DISABLED

### Document Management (MEMBER)

**While Case is on Hold: `status == 'hold'`**

**Current Template Logic:**
```html
{% if case.status == 'draft' or case.status == 'pending_review' or case.status == 'accepted' or case.status == 'completed' %}
    <!-- Member upload section shown -->
{% endif %}
```

**Result:** 🔴 Members CANNOT upload documents while on hold

**Issue:** Hold status not included in document upload condition

**What Should Happen:** Members should be able to upload additional docs while case is on hold, especially if hold reason is "waiting for documents"

**Recommended Fix:**
```html
{% if case.status in 'draft,pending_review,accepted,completed,hold' %}
    <!-- Show upload section for hold status too -->
{% endif %}
```

---

### Case Editing & Workflow

**Technician Abilities While Case is On Hold:**

**✅ ENABLED:**
- ✅ View case details
- ✅ View member documents
- ✅ Add internal notes
- ✅ View hold reason and duration
- ✅ View member updates (if any)
- ✅ Resume from hold (special button)
- ✅ Can reassign (if admin override)

**❌ DISABLED:**
- ❌ Cannot mark as pending_review (not available in UI)
- ❌ Cannot mark as completed (not available in UI)
- ❌ Cannot put on hold again (already on hold)
- ❌ Cannot change case status directly
- ❌ Cannot submit case (wrong status)

---

### Report Notes & Internal Notes

**File:** `cases/templates/cases/case_detail.html` Line 2181

**For Technician/Admin/Manager on Hold Case:**
```html
{% if user.role in 'technician,administrator,manager' and case.status in 'accepted,pending_review,completed,hold' %}
    <!-- Floating Report Notes Window is SHOWN -->
{% endif %}
```

**Result:** ✅ **ENABLED** - Techs can add/edit report notes while case on hold

**Benefit:** Technician can prepare notes explaining hold status before resuming

---

### Role-Based Permissions on Hold Case

| Feature | Member | Technician | Manager | Admin |
|---------|--------|-----------|---------|-------|
| View case | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes |
| Upload docs | ❌ No | N/A | N/A | N/A |
| Add internal notes | N/A | ✅ Yes | ✅ Yes | ✅ Yes |
| Edit report notes | N/A | ✅ Yes | ✅ Yes | ✅ Yes |
| Resume from hold | N/A | ✅ Yes (own) | ✅ Yes (any) | ✅ Yes (any) |
| Reassign tech | N/A | ❌ No | ✅ Yes | ✅ Yes |
| View hold history | N/A | ✅ Yes | ✅ Yes | ✅ Yes |
| Force complete | N/A | ❌ No | ❌ No | ✅ Yes |

---

## 4. RESUME FROM HOLD FLOW

### When & How to Resume

**Resume Button Shows When:**
- Case status == 'hold' 
- User is: assigned technician (owner) OR manager OR admin

**Location:** Case Detail Page → Actions card

### Resume Process

**Step 1: Click "Resume from Hold" Button**
```
Case Detail Page → Status: 'hold'
  ↓
Click "Resume from Hold" button (blue button)
  ↓
Modal appears
```

**Step 2: Fill Resume Modal**
- **Resume Reason** (required textarea)
  - Examples: "Member provided documents", "Admin approved", "Decision made"
  - Explains why hold is ending

**Step 3: Submit**
```
Click "Resume Processing" button
  ↓
POST to /cases/{id}/resume-from-hold/ endpoint
  ↓
Backend processes
```

### Backend Processing

**File:** `cases/views.py:resume_case_from_hold()` (Lines 1304+)

**What Happens:**

1. **Permission Validation**
   - User must be: assigned tech (owner) OR manager OR admin
   - If technician: must own the case
   - If manager/admin: any case

2. **Status Validation**
   - Case status MUST be 'hold'
   - Error if not: "This case is not on hold"

3. **Reason Validation**
   - Resume reason required
   - Error if blank: "Please provide a reason for resuming the case"

4. **Case Model Update** (via `resume_case()` service)
   ```python
   case.status = 'accepted'  # Returns to previous status
   case.assigned_to = UNCHANGED  # ✅ OWNERSHIP PRESERVED
   # Clear hold-specific fields:
   case.hold_reason = None (or cleared)
   case.hold_start_date = None
   case.hold_end_date = None
   case.hold_duration_days = None
   ```

5. **Audit Logging**
   - Action type: `case_resumed`
   - Records: who resumed, when, why
   - Metadata includes: resume_reason, previous_status

6. **Response to User**
   ```json
   {
     "success": true,
     "message": "Case {id} has been resumed from hold.",
     "new_status": "accepted"
   }
   ```

---

## 5. CASE OWNERSHIP PRESERVATION

### Key Principle: Assigned Technician Never Changes on Hold/Resume Cycle

**On Put on Hold:**
```python
case.assigned_to = Alice (unchanged)
case.status = 'accepted' → 'hold'
```

**On Resume:**
```python
case.assigned_to = Alice (still unchanged)
case.status = 'hold' → 'accepted'
```

**Exception: Manager/Admin Reassignment**
```
Manager CAN reassign case while on hold:
Alice → Bob (while status='hold')

Then Bob resumes the case:
case.assigned_to = Bob (new owner)
case.status = 'hold' → 'accepted'
```

**Impact:**
- ✅ Technician keeps credit for the case
- ✅ No loss of work history
- ✅ Manager can reallocate without penalty
- ✅ Audit trail shows entire chain

---

## 6. AUDIT TRAIL TRACKING

### When Case Placed on Hold

**Audit Log Entry:**
```python
action_type: 'case_held'
user: [technician/manager/admin who initiated]
description: "Case #{external_case_id} placed on hold"
changes: {
    'status': ['accepted', 'hold']
}
metadata: {
    'hold_reason': "Waiting for member documents",
    'hold_duration_days': 1,
    'hold_start_date': '2026-01-24T06:15:00Z'
}
ip_address: [client IP captured]
case: [case object]
```

### When Case Resumed from Hold

**Audit Log Entry:**
```python
action_type: 'case_resumed'
user: [technician/manager/admin who resumed]
description: "Case #{external_case_id} resumed from hold"
changes: {
    'status': ['hold', 'accepted']
}
metadata: {
    'resume_reason': "Member provided documents",
    'resumed_at': '2026-01-24T08:30:00Z'
}
ip_address: [client IP captured]
case: [case object]
```

### Additional Audit Entries

**Member Notification Created:**
```python
action_type: 'notification_created'
status: 'case_put_on_hold'
description: "In-app notification created for member"
details: {
    'notification_type': 'case_put_on_hold',
    'hold_reason': "Waiting for member documents",
    'recipient': 'member@email.com'
}
```

**Email Sent to Member:**
```python
action_type: 'email_sent'
status: 'case_put_on_hold'
description: "Email sent to member about case hold"
details: {
    'recipient': 'member@email.com',
    'subject': 'Your case has been placed on hold',
    'reason': 'Hold notification'
}
```

---

## 7. MEMBER EXPERIENCE ON HOLD CASE

### Timeline for Member

**Day 1 - Case Put on Hold:**
```
1. Email arrives: "Your case has been placed on hold"
2. Email contains:
   - Hold reason from technician
   - Case ID and employee name
   - Link to case detail
   - What to expect next
3. Member logs in
4. Dashboard shows: "⏸ On Hold" badge
5. Can click case to see full details
6. Can see hold reason in case detail
```

**Day 1-2 - Member Takes Action (Example: Missing Docs)**
```
1. Member sees: "Waiting for Social Security documentation"
2. Member navigates to document upload section
3. PROBLEM: Upload section may not show (currently only shows for draft/pending/accepted/completed)
4. Member cannot upload documents
5. SOLUTION: Allow uploads for 'hold' status
```

**Day 3 - Case Resumed:**
```
1. Technician sees docs are ready
2. Clicks "Resume from Hold"
3. Provides reason: "Member provided Social Security documents"
4. Case status changes back to 'accepted'
5. Member gets notification: Case resumed
6. Technician continues processing
```

**Result:**
- ✅ Transparent communication via email
- ✅ Member knows what's blocking progress
- ✅ Can provide needed information
- ❌ Currently cannot upload while on hold
- ✅ Case preserved for same technician

---

## 8. COMMON HOLD SCENARIOS

### Scenario 1: Waiting for Member Documents

```
Status Timeline:
1. Technician reviews submitted case (status='submitted')
2. Clicks Accept Case, assigns Tier, status becomes 'accepted'
3. Reviews documents, realizes: "Missing pay stub"
4. Clicks "Put on Hold"
5. Provides reason: "Waiting for pay stub"
6. Sets duration: "4 days"
7. Member gets email with request

Member Action:
- Receives email notification
- Logs in, tries to upload pay stub
- Issue: Cannot upload (hold status not in upload conditions)
- Waits or contacts support

Technician Follows Up (Day 4):
- Receives hold duration alert
- Sees member didn't upload
- Sends follow-up message
- OR extends hold duration

Member Uploads (Day 5):
- Tech sends direct message to member
- Member then sees updated case
- Can now upload documents
- Tech resumes case

Resolution:
- Tech clicks "Resume from Hold"
- Provides reason: "Pay stub received"
- Case back to 'accepted', processing continues
```

### Scenario 2: Waiting for Admin Decision

```
Status Timeline:
1. Tech identifies unusual situation needing approval
2. Case is 'accepted'
3. Clicks "Put on Hold"
4. Reason: "Pending admin review for special circumstances"
5. Duration: "Custom" (until decision made)

Admin Review:
- Sees hold case in dashboard
- Reviews reason and documents
- Makes decision
- Contacts tech or manager

Tech/Manager Resumes:
- Gets approval/direction
- Clicks "Resume from Hold"
- Reason: "Admin approved - proceed with Tier 2 analysis"
- Case returns to 'accepted'
- Processing continues
```

### Scenario 3: Reassign While on Hold

```
Status Timeline:
1. Tech A puts case on hold (reason: complex analysis needed)
2. Duration: "Custom"
3. Case.assigned_to = Tech A

Manager Decision:
- Sees case on hold
- Tech A is overloaded
- Clicks "Reassign Case"
- Selects: Tech B (senior tech)
- Case.assigned_to changes to Tech B

Tech B Actions:
- Sees new assignment
- Reviews hold reason: "Complex analysis"
- Decides hold no longer needed
- Clicks "Resume from Hold"
- Provides reason: "Reviewed by senior tech, ready to proceed"
- Case continues under Tech B

Result:
- Case properly escalated
- Right person now owns it
- Audit trail shows full history
```

---

## 9. CURRENT LIMITATIONS & RECOMMENDATIONS

### Issue #1: Member Cannot Upload While on Hold

**Current Behavior:**
- Document upload section only shows for: draft, pending_review, accepted, completed
- On 'hold' status: upload section hidden

**Impact:**
- If hold reason is "waiting for documents", member cannot provide them
- Requires tech to manually notify member via other channel
- Workflow breaks

**Recommendation:**
```html
<!-- CURRENT -->
{% if case.status == 'draft' or case.status == 'pending_review' or case.status == 'accepted' or case.status == 'completed' %}

<!-- RECOMMENDED -->
{% if case.status in 'draft,pending_review,accepted,completed,hold' %}
    <!-- Show upload for hold too, especially useful when waiting for docs -->
{% endif %}
```

**Benefit:** Members can proactively provide missing info while case on hold

---

### Issue #2: No Auto-Resume Alert

**Current Behavior:**
- Hold duration is stored (hold_end_date)
- But no background job checks if duration passed
- No automatic notification when hold expires
- Tech must manually check and resume

**Recommendation:**
- Add cron job to check for expired holds
- Auto-notification to tech: "Your hold on case X has expired"
- Or: Auto-resume with notification

---

### Issue #3: No Hold Reason Display in Dashboard

**Current Behavior:**
- Dashboard shows "⏸ On Hold" badge
- Tech must click case to see hold reason
- Dashboard doesn't show why case is on hold

**Recommendation:**
- Add tooltip or hover showing hold reason
- Show duration on dashboard
- Example: "⏸ On Hold (Waiting for docs - Est. 4 days)"

---

### Issue #4: Member Cannot See Hold Duration on Dashboard

**Current Behavior:**
- Member sees: "⏸ On Hold" 
- Cannot see when it should resume
- Creates uncertainty

**Recommendation:**
- Display: "On Hold - Expected to resume by Jan 28, 2026"
- Show: "On Hold since Jan 24 (4 days)"
- Help member plan next steps

---

## 10. TECHNICAL FLOW DIAGRAM

```
┌─────────────────────────────────────────────────────────────┐
│ CASE LIFECYCLE: PUT ON HOLD & RESUME                        │
└─────────────────────────────────────────────────────────────┘

                    NORMAL FLOW (Accepted → Completed)
                                 │
                                 ├─→ HOLD FLOW ← ─────────┐
                                 │                         │
        ┌─ Accepted ─┐          │              ┌──────────┴──────────┐
        │ (working)  │          │              │                     │
        └────────────┘          │              ▼                     │
              │                 │         Put on Hold                │
              │                 │         Modal Shows                │
              │                 │              │                     │
              │                 │      Fill Reason & Duration        │
              │                 │              │                     │
              │                 │      Submit to Backend             │
              │                 │              │                     │
              │                 │      ┌───────▼────────┐            │
              │                 │      │ Validate Perms  │            │
              │                 │      │ Validate Status │            │
              │                 │      │ Validate Reason │            │
              │                 │      └────────┬────────┘            │
              │                 │              │                     │
              │                 │      Status → 'hold'               │
              │                 │      assigned_to → UNCHANGED       │
              │                 │      Audit Log Entry               │
              │                 │      Member Email                  │
              │                 │      CaseNotification Created      │
              │                 │              │                     │
              │                 │              ▼                     │
              │                 │         On Hold State              │
              │                 │              │                     │
              │                 │   ┌──────────┴──────────┐          │
              │                 │   │                     │          │
              │                 │   ├─→ Duration expires  │          │
              │                 │   │   (optional alert)  │          │
              │                 │   │                     │          │
              │                 │   ├─→ Member uploads    │          │
              │                 │   │   documents         │          │
              │                 │   │                     │          │
              │                 │   └─────────┬───────────┘          │
              │                 │             │                     │
              │                 │   Click "Resume from Hold"         │
              │                 │   Modal Shows Reason Field         │
              │                 │   Fill Resume Reason               │
              │                 │             │                     │
              │                 │   Submit to Backend                │
              │                 │             │                     │
              │                 │   ┌─────────▼────────┐             │
              │                 │   │ Validate Perms    │             │
              │                 │   │ Validate Status   │             │
              │                 │   │ Validate Reason   │             │
              │                 │   └────────┬──────────┘             │
              │                 │            │                      │
              │                 │   Status → 'accepted'              │
              │                 │   assigned_to → UNCHANGED           │
              │                 │   Audit Log Entry                  │
              │                 │   Clear Hold Fields                │
              │                 │             │                     │
              └─────────────────┴─────────────┴─────────────────────┘
                         Continue Processing →
                    pending_review → completed
```

---

## 11. QUICK REFERENCE - STATUS ON HOLD

| Aspect | Details |
|--------|---------|
| **When** | Case status = 'accepted' |
| **Who Can Initiate** | Assigned tech, manager, admin |
| **Reason** | Required (free-form text) |
| **Duration** | Optional (2hr, 4hr, 8hr, 1day, custom) |
| **Ownership** | ✅ PRESERVED (same assigned tech) |
| **Member Email** | ✅ Sent with hold reason & case link |
| **Member Can Upload** | ❌ Currently NO (needs fix) |
| **Tech Can Edit Notes** | ✅ YES (report notes still available) |
| **Tech Can Resume** | ✅ YES (same tech can resume) |
| **Manager Can Resume** | ✅ YES (any manager) |
| **Can Reassign While Held** | ✅ YES (manager/admin only) |
| **Audit Logging** | ✅ Full tracking (action_type='case_held/resumed') |
| **Dashboard Display** | ✅ Yellow "⏸ On Hold" badge |
| **Next Status After Resume** | 'accepted' (continues processing) |
| **Possible After Resume** | pending_review → completed |

---

## Summary

The "Put on Hold" feature provides a controlled pause in case processing while maintaining ownership and audit trail integrity. It's particularly useful for:

1. **Waiting for Member Info** - Request docs without closing case
2. **Manager Review** - Escalate for decision without full reassignment
3. **Workload Management** - Temporarily pause to prioritize other cases
4. **Complex Cases** - Senior review needed before proceeding

**Key Strengths:**
- ✅ Ownership preservation
- ✅ Comprehensive audit trail
- ✅ Member notification system
- ✅ Flexible duration tracking

**Key Gaps:**
- ❌ Member document upload disabled on hold (should be enabled)
- ❌ No hold reason visible on dashboard
- ❌ No auto-resume when duration expires
- ❌ No hold duration display to member

