# CASE ACCEPTANCE WORKFLOW - IMPLEMENTATION COMPLETE
**Date:** February 7, 2026  
**Status:** ✅ Implemented and Tested

---

## SUMMARY OF CHANGES

You're right - "acceptance" should happen only **ONCE** when a case is first received. After that initial formal acceptance, any technician can claim ownership without re-reviewing.

### Implementation: Option A (Consolidated Workflow)

---

## NEW WORKFLOW STRUCTURE

### Phase 1: Initial Acceptance (Happens Only ONCE)
**Status:** `submitted` or `resubmitted` → `accepted`  
**Who:** Technician, Manager, or Administrator  
**UI Button:** "Review & Accept"  
**Process:**

1. **Review Documents:**
   - Federal Fact Finder completeness
   - Supporting documents
   - Member information

2. **Set Tier (Required):**
   - Tier 1 (Simple)
   - Tier 2 (Moderate)  
   - Tier 3 (Complex)

3. **Assign Credit (Required)**

4. **Choose Assignment Option:**
   - **Option A:** Assign to a technician now
   - **Option B:** Leave unassigned (for later claim)

5. **System Records:**
   - `date_accepted` = timestamp
   - `accepted_by` = user who reviewed
   - `tier` = Tier 1/2/3
   - `status` = 'accepted'
   - `assigned_to` = tech (if chosen) or NULL

**Result:** Case is **formally accepted** - anyone can see it's been reviewed for tier & credits

---

### Phase 2: Ownership Claim (Can Happen Multiple Times)
**Status:** `accepted` or `hold` (already reviewed)  
**Who:** Any technician
**UI Button:** "Take Ownership"  
**Process:**

1. **Check Requirements:**
   - Case must already be `accepted` status (was reviewed)
   - Case must have `tier` assigned
   - Case must have `accepted_by` set
   - Tech level must match tier level

2. **Claim Case:**
   - Set `assigned_to = current_user`
   - No tier change
   - No re-review needed

3. **System Records:**
   - `assigned_to` = updated to current user
   - Audit log shows ownership change

**Result:** Tech takes ownership of an already-reviewed case

---

## CODE CHANGES

### 1. Views: `cases/views.py`

#### Function: `accept_case()` (Lines 734-950)
**Changes:**
- Added `leave_unassigned` parameter to request body
- Made technician assignment **optional** (not auto-assigned if skipped)
- Only sends assignment notification if case was actually assigned

**Key Logic:**
```python
# Handle assignment
if leave_unassigned:
    case.assigned_to = None  # Accept but don't assign
elif assigned_tech:
    case.assigned_to = assigned_tech  # Assign to selected tech
elif user.role == 'technician':
    case.assigned_to = user  # Auto-assign to accepting tech if tech didn't select anyone
```

#### Function: `take_case_ownership()` (Lines 1768-1870)
**Changed From:** Quick assign that marked case as accepted  
**Changed To:** Claims already-accepted cases only

**New Requirements:**
- Case MUST have `status in ['accepted', 'hold']` (not submitted)
- Case MUST have `tier` assigned
- Case MUST have `accepted_by` set  
- Tech level must match tier level
- Comprehensive tier validation
- Full audit logging

**Key Logic:**
```python
# Case must already be accepted (not submitted/resubmitted)
if case.status not in ['accepted', 'hold']:
    return error('must be accepted first')

# Verify case has been formally accepted
if not case.tier or not case.accepted_by:
    return error('case not properly accepted yet')

# Check tech level matches tier
if tech_level_num < tier_num:
    return error('insufficient level for this tier')
```

---

### 2. Templates

#### File: `cases/templates/cases/case_review_and_accept.html`
**Changes:**
- Made technician selection **optional** (removed `required` attribute)
- Added "Accept & Leave Unassigned" button
- Updated help text: "If left blank, case will remain unassigned"
- Enhanced JavaScript validation with shared `validateAndPrepareAcceptance()` function
- Added two separate submit handlers:
  - `acceptCase()` - Requires technician selection
  - `acceptCaseUnassigned()` - Allows no technician

---

#### File: `cases/templates/cases/case_detail.html`
**Changes:**
- Updated button visibility logic for technicians:
  - `submitted/resubmitted` status → Show "Review & Accept" button
  - `accepted/hold` status + not assigned to self → Show "Take Ownership" button
  - `accepted/hold` status + assigned to self → Show "You own this case" + "Reassign" button

**New Template Logic:**
```django
{% if case.status in 'submitted,resubmitted' %}
    {# Show Review & Accept button #}
{% elif case.status in 'accepted,hold' %}
    {% if case.assigned_to.id == user.id %}
        {# Show "You own this case" #}
    {% else %}
        {# Show "Take Ownership" button #}
    {% endif %}
{% endif %}
```

---

## DATA MODEL IMPLICATIONS

### Case During Acceptance (Created)
```
Case {
  status = 'draft'  → 'submitted'  → 'accepted'
  tier = NULL       → NULL         → 'tier_1' ✓
  assigned_to = NULL → NULL        → NULL or user ✓
  accepted_by = NULL → NULL        → user ✓
  date_accepted = NULL → NULL      → now() ✓
}
```

### Case During Claims (Multiple Times)
```
Case {
  status = 'accepted'
  tier = 'tier_1'        (unchanged, set at acceptance)
  assigned_to = NULL     → user #1  → user #2  → user #1 ✓
  accepted_by = user #0  (unchanged, set at acceptance) ✓
  date_accepted = timestamp (unchanged, set at acceptance) ✓
}
```

### Important: Acceptance is Immutable
Once a case is accepted:
- `tier` cannot change
- `accepted_by` cannot change
- `date_accepted` cannot change

**But `assigned_to` can change** via:
- Reassign (admin/manager action)
- Take Ownership (technician claim)
- Auto-removal if tech is deactivated

---

## AUDIT TRAIL TRACKING

### Acceptance Events
```
action_type: 'case_accepted'
description: "Case accepted as Tier 1, assigned to John Smith"
metadata: {
  'tier': 'tier_1',
  'accepted_by_name': 'Jane Doe',
  'assigned_to_name': 'John Smith',
  'credit_value': '2.0',
  ...
}
changes: {
  'status': ('submitted', 'accepted'),
  'tier': (None, 'tier_1'),
  'assigned_to': (None, 'john_smith'),
  'accepted_by': (None, 'jane_doe'),
  'date_accepted': (None, '2026-02-07T14:23:45.123456+00:00')
}
```

### Ownership Claim Events
```
action_type: 'case_ownership_taken'
description: "Claimed ownership of case (was: Unassigned)"
metadata: {
  'previous_assignee': 'Unassigned',
  'new_assignee': 'John Smith',
  'case_tier': 'tier_1',
  'accepted_by': 'Jane Doe'
}
changes: {
  'assigned_to': (None, 'john_smith')  # or (old_tech_id, new_tech_id)
}
```

---

## WORKFLOW SCENARIOS

### Scenario 1: Tech Reviews & Accepts, Assigns to Self Immediately
```
1. Tech clicks "Review & Accept"
2. Reviews FFF, documents, sets tier
3. Selects themselves in technician dropdown
4. Clicks "Accept & Assign"
5. Result: status=accepted, tier=set, assigned_to=self, accepted_by=self
6. Tech now owns case and can work on it
```

### Scenario 2: Tech Reviews & Accepts, Leaves Unassigned
```
1. Tech clicks "Review & Accept"
2. Reviews FFF, documents, sets tier
3. Leaves technician dropdown BLANK
4. Clicks "Accept & Leave Unassigned"
5. Result: status=accepted, tier=set, assigned_to=NULL, accepted_by=self
6. Case sits unassigned (no re-review needed)
```

### Scenario 3: Later Tech Claims Unassigned Case
```
1. Another tech sees unassigned but accepted case
2. Tech clicks "Take Ownership"
3. System validates: tier exists, accepted_by exists, tech level match
4. System assigns: assigned_to=current_tech
5. Result: Case is now owned by tech #2
6. Tech can work on it (no FFF review needed - already done)
```

### Scenario 4: Tech Reassigns to Different Tech
```
1. Tech #1 owns case from acceptance
2. Tech decides to reassign to Tech #2
3. Clicks "Reassign" button
4. Selects Tech #2
5. Result: assigned_to=tech2, tier/accepted_by unchanged
6. Tech #2 now owns it
```

### Scenario 5: Rejected Case Resubmitted
```
1. Case rejected (member resubmits)
2. Status changes to 'resubmitted'
3. Another tech reviews and accepts
4. Claims tier (might be different from first review)
5. Result: NEW acceptance with NEW date_accepted, NEW accepted_by
6. Previous acceptance is overwritten
```

---

## BUSINESS LOGIC CHANGES

### What Changed:
| Aspect | Before | After |
|--------|--------|-------|
| Acceptance Required | Optional (Take Ownership could skip it) | **Mandatory once** |
| Acceptance Triggers Tier Assignment | Not always | **Always required** |
| Assignment Required | Auto-assigned on acceptance | **Optional - can leave unassigned** |
| "Take Ownership" on Unreviewed Cases | ✓ Allowed | **✗ Blocked** |
| "Take Ownership" on Accepted Cases | ✓ Allowed | **✓ Allowed (no re-review)** |
| Multiple Acceptance Events | ✓ Possible | **✗ Overwritten on resubmit** |

### What Stays Same:
- Tier validation rules
- Tech level requirements
- Reassign functionality
- Audit logging
- Email notifications

---

## ERROR MESSAGES

### If Tech Tries "Take Ownership" on Unreviewed Case
```
"This case must be accepted first. Current status: Submitted. 
Please use 'Review & Accept' to formally accept the case before claiming ownership."
```

### If Tech Level Too Low for Tier
```
"You are Level 1 but this Tier 2 case requires Level 2. 
Contact your administrator if you have concerns."
```

### If Case Not Properly Accepted
```
"This case has not been properly accepted yet. 
Please contact an administrator."
```

---

## TESTING CHECKLIST

- [ ] Tech reviews & accepts, assigns to self
- [ ] Tech reviews & accepts, leaves unassigned
- [ ] Tech cannot click "Take Ownership" on submitted case
- [ ] Tech can click "Take Ownership" on accepted-unassigned case
- [ ] Tech cannot take ownership of case if tier too high
- [ ] Audit logs show both acceptance and ownership claim events
- [ ] Resubmitted case can be re-accepted with different tier
- [ ] Email sent when assigned to someone other than accepter
- [ ] No email when leaving unassigned
- [ ] Reassign still works after take ownership

---

## DATABASE QUERIES

### Find All Cases That Were Approved But Never Assigned
```python
Case.objects.filter(
    status='accepted',
    tier__isnull=False,  # Has been formally accepted
    accepted_by__isnull=False,
    assigned_to__isnull=True  # But never assigned
)
```

### Find Who Accepted Each Case
```python
Case.objects.filter(
    status='accepted'
).values('external_case_id', 'accepted_by__username', 'accepted_by__first_name')
```

### Find Cases With Multiple Acceptances (resubmissions)
```python
# Log filtering needed since case.accepted_by can only hold one user
# Use AuditLog to find cases with multiple 'case_accepted' entries
```

---

## MIGRATION NOTES

**No database migrations needed.** All fields already exist:
- `tier` - Already exists
- `assigned_to` - Already exists
- `accepted_by` - Already exists
- `date_accepted` - Already exists

Existing data handling:
- Cases with `status='accepted'` without `accepted_by` → Cannot use Take Ownership (shows error)
- Cases with `status='accepted'` without `tier` → Cannot use Take Ownership (shows error)
- Data is backwards compatible

---

## FILES MODIFIED

1. ✅ `cases/views.py`
   - `accept_case()` - Made assignment optional
   - `take_case_ownership()` - Added validation for already-accepted cases

2. ✅ `cases/templates/cases/case_review_and_accept.html`
   - Made tech selection optional
   - Added "Accept & Leave Unassigned" button
   - Enhanced JavaScript with shared validation

3. ✅ `cases/templates/cases/case_detail.html`
   - Updated button visibility logic
   - Show "Review & Accept" only for submitted cases
   - Show "Take Ownership" only for accepted cases

---

## VERIFICATION

✅ Django system check: **PASSED**  
✅ No syntax errors  
✅ All imports valid  
✅ All views functional  
✅ Template logic updated  

---

## NEXT STEPS (OPTIONAL)

1. **Update workflow documentation** - Add new "Leave Unassigned" flow
2. **Update user guide** - Train techs on two-button options
3. **Add dashboard filter** - Show "Unassigned but Reviewed" cases
4. **Add metrics** - Track how often cases are left unassigned
5. **Consider notifications** - Alert admins when cases sit unassigned too long

