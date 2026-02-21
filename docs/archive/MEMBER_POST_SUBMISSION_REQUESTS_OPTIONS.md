# Member Post-Submission Requests & Cancellations - Options

**Date:** January 23, 2026  
**Context:** Currently members can delete draft cases, but submitted cases show a greyed-out locked "Delete" button. We need options for:
1. How members request different due dates
2. How members can cancel a case after submission

---

## Current State

### Delete Button Behavior (Today)
**Draft Cases:**
- ✅ Active red "Delete" button available
- Member can click to permanently delete
- Confirmation popup appears

**Submitted/In-Progress Cases:**
- ❌ Greyed-out button with lock icon: "🔒 Delete"
- Tooltip: "Cannot delete submitted or in-progress cases"
- Completely disabled, cannot be clicked

**Completed Cases:**
- ❌ Button hidden entirely (not shown)

### Why It's Locked
- Submitted cases have been reviewed/assigned to tech
- Deleting would lose audit trail data
- Business rule: Only techs/admins can remove submitted cases

---

## Problem Statement

### Current Gaps
1. **No Due Date Change Request Mechanism**
   - Member has no way to request deadline extension
   - Must contact support/advisor manually outside system
   - Tech has to manually edit via `edit_case_details()` view

2. **No Case Cancellation Mechanism**
   - Member cannot cancel submitted case
   - Greyed-out button is confusing ("why is this locked?")
   - Only admins can delete via admin backend
   - Member has no self-service option

3. **User Experience Issue**
   - Greyed-out button is cryptic
   - No clear alternative path for member action
   - Could lead to support tickets

---

## 5 Options for Member Post-Submission Actions

---

## **OPTION 1: Replace "Delete" Button with "Cancel Request"** ⭐ RECOMMENDED

### How It Works
**Draft Cases:**
- Keep existing: "Delete" button (red, active)

**Submitted/In-Progress Cases:**
- Replace greyed-out "Delete" with active "Cancel Request" button (red/warning)
- Click opens modal with:
  - "Are you sure you want to cancel this case?"
  - Reason dropdown: "No longer needed" / "Changed mind" / "Other"
  - Optional notes field
  - "Cancel Case" and "Keep Case" buttons

**On Cancellation:**
- Case status changes to: `cancelled` (new status)
- Audit log entry: `case_cancelled_by_member`
- Optional: Email tech notifying of cancellation
- Member can still view case for 90 days (read-only archive)
- After 90 days: Soft-delete (archive) or permanent delete

### Technical Changes Needed
```python
# Add to Case STATUS_CHOICES
STATUS_CHOICES = [
    ('draft', 'Draft'),
    ('submitted', 'Submitted'),
    ('cancelled', 'Cancelled'),  # NEW
    ... rest
]

# Add model field
cancellation_reason = models.CharField(max_length=50, null=True, blank=True)
cancelled_date = models.DateTimeField(null=True, blank=True)
cancellation_notes = models.TextField(null=True, blank=True)

# Create new view: cancel_case()
```

### HTML Changes
```html
{% if case.status == 'draft' %}
    <a href="{% url 'cases:delete_case' case.pk %}" 
       class="btn btn-sm btn-outline-danger"
       onclick="return confirm('Delete this draft case?')">
        <i class="bi bi-trash"></i> Delete
    </a>
{% elif case.status in 'submitted,accepted,hold,pending_review,resubmitted,needs_resubmission' %}
    <button class="btn btn-sm btn-outline-danger" 
            data-bs-toggle="modal" 
            data-bs-target="#cancelCaseModal"
            title="Cancel this case request">
        <i class="bi bi-x-circle"></i> Cancel
    </button>
{% else %}
    <!-- Hidden for completed cases -->
{% endif %}
```

### Pros
- ✅ Intuitive: Button changes from "Delete" to "Cancel" based on status
- ✅ Clear action: Member knows what button does
- ✅ Respects audit trail: Soft-delete instead of hard-delete
- ✅ Gives member agency: Can cancel anytime
- ✅ Tech still has visibility: Can see cancelled cases and why

### Cons
- ❌ Adds new database field and status
- ❌ Might confuse: Are "cancelled" and "completed" the same?
- ❌ Question: What happens to the employee's info after cancellation?

### Implementation Effort
- 1-2 weeks
- Database migration needed
- New view, template, modal, audit logging

---

## **OPTION 2: Add "Request Changes" Modal with Multiple Options**

### How It Works
**Submitted/In-Progress Cases:**
- Replace "Delete" with "Request Changes" button (warning color)
- Modal shows 3 choices:
  1. **Request Due Date Extension** - Date picker, reason
  2. **Request Case Cancellation** - Reason dropdown, notes
  3. **Add Additional Information** - Direct link to upload docs

**Request Flow:**
- Member selects option and fills form
- Creates a `CaseChangeRequest` record in database
- Sets flag: `has_member_change_request = True`
- Tech sees "⚠️ Member Change Request" badge on dashboard
- Tech can approve/deny in case detail page

### Technical Changes
```python
# New model: CaseChangeRequest
class CaseChangeRequest(models.Model):
    REQUEST_TYPES = [
        ('due_date_extension', 'Due Date Extension'),
        ('cancellation', 'Case Cancellation'),
        ('additional_docs', 'Additional Information'),
    ]
    
    case = ForeignKey(Case)
    request_type = CharField(choices=REQUEST_TYPES)
    requested_due_date = DateField(null=True)
    cancellation_reason = CharField(null=True)
    notes = TextField()
    created_date = DateTimeField(auto_now_add=True)
    status = CharField(choices=[('pending', 'Pending'), ('approved', 'Approved'), ('denied', 'Denied')])
    tech_response = TextField(null=True)
    tech_response_date = DateTimeField(null=True)
```

### Modal Example
```
┌──────────────────────────────────┐
│ Request Changes to Case ABC123   │
├──────────────────────────────────┤
│ What would you like to do?       │
│                                  │
│ ○ Request Due Date Extension     │
│   "I need more time to prepare"  │
│                                  │
│ ○ Cancel This Case               │
│   "No longer need this report"   │
│                                  │
│ ○ Upload Additional Info         │
│   "I have more documents"        │
│                                  │
│     [Submit Request] [Cancel]    │
└──────────────────────────────────┘
```

### Pros
- ✅ One button for multiple request types
- ✅ Clear what member is requesting
- ✅ Tech must actively approve/deny
- ✅ Creates audit trail of requests
- ✅ Prevents accidental cancellations (needs approval)

### Cons
- ❌ Adds complexity (approval workflow)
- ❌ Might delay cancellations (if immediate needed)
- ❌ Tech has to review each request
- ❌ Could create backlogs if many requests

### Implementation Effort
- 2-3 weeks
- New model, migration, views
- Dashboard badge system
- Approval workflow UI

---

## **OPTION 3: Separate Buttons for Each Action**

### How It Works
Replace the single greyed-out "Delete" with two distinct buttons:

**Button 1: "Request Extension"** (Warning color)
- Opens date picker modal
- Member selects new due date + reason
- Immediately approved (or sent to tech for approval)

**Button 2: "Cancel Case"** (Danger color)
- Opens confirmation modal
- Asks: "Are you sure? This cannot be undone."
- Cancels immediately (or sent to tech)

### HTML
```html
{% elif case.status in 'submitted,accepted,hold,pending_review,resubmitted,needs_resubmission' %}
    <button class="btn btn-sm btn-outline-warning" 
            data-bs-toggle="modal" 
            data-bs-target="#extensionModal"
            title="Request a due date extension">
        <i class="bi bi-calendar-event"></i> Extend
    </button>
    <button class="btn btn-sm btn-outline-danger" 
            data-bs-toggle="modal" 
            data-bs-target="#cancelModal"
            title="Cancel this case">
        <i class="bi bi-x-circle"></i> Cancel
    </button>
{% endif %}
```

### Pros
- ✅ Very clear: Each button has one purpose
- ✅ Prevents accidents: Separate modals
- ✅ Easy to discover: Right on dashboard
- ✅ Straightforward: No approval workflow

### Cons
- ❌ Takes more dashboard space (2 buttons)
- ❌ Could look cluttered if many buttons
- ❌ No approval mechanism (might cancel wrong case)

### Implementation Effort
- 1-2 weeks
- Two separate views/endpoints
- Two modals

---

## **OPTION 4: Add "Request" Section to Case Detail View**

### How It Works
- **Keep member dashboard as-is** (no button changes)
- **Add new tab/section in case detail page:** "Member Requests"
- Section shows:
  - Form to request due date extension (date picker + reason)
  - Form to request case cancellation (reason + notes)
  - History of all requests (pending/approved/denied)

### Workflow
1. Member clicks "View" on case
2. Navigates to new "Requests" tab
3. Fills out extension or cancellation form
4. Submit creates request record
5. Tech reviews in case detail dashboard indicator

### Pros
- ✅ Doesn't clutter dashboard
- ✅ Organized all in one place
- ✅ Can show request history
- ✅ Member has space to explain needs
- ✅ Tech sees full context

### Cons
- ❌ Not discoverable: Hidden in case detail tab
- ❌ Member might not know feature exists
- ❌ Extra click required

### Implementation Effort
- 1.5-2 weeks
- New tab section on case detail
- Forms + backend handling

---

## **OPTION 5: Email-Based Requests (No UI Change)**

### How It Works
- Keep dashboard as-is (greyed-out Delete button)
- Add help text: "Contact your advisor to request changes"
- Add link to email template with pre-filled subject
- Member's email client opens with:
  ```
  To: support@advisor-portal.com
  Subject: Request Changes to Case ABC123
  Body:
  Type of request:
  ☐ Due date extension to: ___________
  ☐ Cancel case
  
  Reason:
  [member types here]
  ```

### Pros
- ✅ No code changes needed (mostly UI text)
- ✅ Keeps all records in email system (external)
- ✅ Human review of requests
- ✅ Minimal UX confusion

### Cons
- ❌ Not in system (audit trail gap)
- ❌ Slow: Email back-and-forth
- ❌ No tracking in dashboard
- ❌ Defeats purpose of web app
- ❌ Members might not know feature exists

### Implementation Effort
- Low (2-3 days)
- Just text link changes

---

## Comparison Matrix

| Factor | Option 1 | Option 2 | Option 3 | Option 4 | Option 5 |
|--------|----------|----------|----------|----------|----------|
| **Clear to User** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐ |
| **In System** | ✅ | ✅ | ✅ | ✅ | ❌ |
| **Discoverable** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐ |
| **Member Approval** | No | Tech Approves | No | Tech Approves | No |
| **Space on Dashboard** | Low | Low | Medium | None | Low |
| **Impl. Effort** | 1-2 wks | 2-3 wks | 1-2 wks | 1.5-2 wks | 2-3 days |
| **Accident Prevention** | Low | High | Low | Medium | N/A |
| **Recommended** | **YES** ⭐ | Maybe | Yes | Maybe | No |

---

## Recommendation

### **Primary: OPTION 1 (Replace Delete with Cancel)**

**Why:**
- Solves the UX confusion (what's this locked button for?)
- Intuitive: Button changes based on what you can do
- Gives member clear self-service option
- Simple to implement (1-2 weeks)
- Clear audit trail of cancellations

**Then Consider: Add "Request Due Date Extension" in Phase 2**
- Separate feature from cancellation
- Can be added later if needed
- Tech might handle via email initially

### **Alternative: OPTION 3 (Separate Buttons)**

**If you want:**
- More flexibility (both cancel AND extend)
- Very clear separate actions
- Less confusion between actions

---

## Implementation Order (Recommended)

### Phase 1: Solve the "Delete" Button UX (Week 1-2)
- Change locked "Delete" → active "Cancel" button
- New status: `cancelled`
- Simple cancellation flow (no approval needed)
- Soft-delete with 90-day archive

### Phase 2: Add Due Date Extension Request (Week 3-4)
- Separate "Request Extension" button
- Tech gets dashboard notification
- Tech can approve/deny
- If approved, auto-updates due date + urgency

### Phase 3: Advanced Features (Optional)
- Reason tracking
- Email notifications
- Request history
- Stats on cancellation reasons

---

## Questions to Answer Before Starting

1. **Should members be able to cancel immediately, or does tech need to approve?**
   - Immediate = simpler, faster
   - Tech approval = more control, audit trail

2. **What should happen to cancelled cases?**
   - Archive for 90 days then delete
   - Keep forever as historical record
   - Hide from member view

3. **What if tech has already started work?**
   - Allow cancellation anyway (with refund?)
   - Deny cancellation if work started
   - Manual approval required

4. **Should cancelled cases be recoverable?**
   - Yes (restore from archive)
   - No (permanent deletion only)

5. **Do you want to offer due date extensions separate from cancellations?**
   - Yes (separate feature)
   - No (cancellation only for now)

---

## Current Button Location & Code

**File:** [member_dashboard.html](cases/templates/cases/member_dashboard.html#L326-L331)

**Current Code:**
```html
{% if case.status == 'draft' %}
    <a href="{% url 'cases:delete_case' case.pk %}" class="btn btn-sm btn-outline-danger">
        <i class="bi bi-trash"></i> Delete
    </a>
{% else %}
    <button class="btn btn-sm btn-outline-secondary" disabled title="Cannot delete submitted or in-progress cases">
        <i class="bi bi-lock"></i> Delete
    </button>
{% endif %}
```

---

## Next Steps

1. **Decide:** Which option(s) to implement
2. **Answer:** The 5 questions above
3. **Timeline:** Estimate based on phase-out
4. **Build:** Implement Phase 1 first

---

**Document Status:** Complete Analysis - Ready for Decision  
**Last Updated:** January 23, 2026
