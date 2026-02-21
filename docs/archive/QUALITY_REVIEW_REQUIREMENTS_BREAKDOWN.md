# Quality Review Requirements Breakdown
## Junior Level (Level 1) Technician Review Workflow

**Date:** January 17, 2026  
**Status:** ⚠️ PARTIALLY IMPLEMENTED - Review Functionality Missing

---

## Executive Summary

The **Quality Review workflow is DEFINED in the requirements** but **NOT FULLY IMPLEMENTED** in the codebase:

✅ **Defined:**
- Case model has `reviewed_by` field (FK to Level 2/3 technicians)
- `requires_review` property on Case model (checks if assigned_to.user_level == 'level_1')
- `pending_review` status exists for cases
- Admin dashboard tracks "Review" count stat
- Technician models have three levels: Level 1, Level 2, Level 3

❌ **Missing/Incomplete:**
- No workflow to actually TRIGGER review (when to set status to 'pending_review')
- No Level 2/3 technician "review queue" interface in current dashboards
- No "approve/reject" review action functionality
- No automatic completion after review approval
- Limited audit trail for review actions

---

## Technical Breakdown

### 1. User Levels (Implemented)

**File:** [accounts/models.py](accounts/models.py#L7-L20)

```python
USER_LEVEL_CHOICES = [
    ('level_1', 'Level 1 - New Technician'),      # Requires quality review
    ('level_2', 'Level 2 - Technician'),          # Can perform quality reviews
    ('level_3', 'Level 3 - Senior Technician'),   # Can perform quality reviews
]
```

### 2. Case Model - Review Fields (Implemented)

**File:** [cases/models.py](cases/models.py#L121-L129)

**Field: `reviewed_by`** (ForeignKey)
```python
reviewed_by = models.ForeignKey(
    settings.AUTH_USER_MODEL,
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name='reviewed_cases',
    limit_choices_to={'role': 'technician', 'user_level__in': ['level_2', 'level_3']}
)
```

**Property: `requires_review`** (Check if Level 1 assigned)
```python
@property
def requires_review(self):
    """Check if case requires quality review (Level 1 technician)"""
    if self.assigned_to and self.assigned_to.user_level == 'level_1':
        return True
    return False
```

### 3. Case Statuses (Partially Implemented)

**File:** [cases/models.py](cases/models.py#L60-L80)

Defined statuses include:
- `submitted` - Initial state
- `accepted` - Manager/Admin/Tech accepted case
- `pending_review` - ⚠️ **Defined but not used in workflow**
- `completed` - Case work finished

**Problem:** There's no logic to transition a Level 1 technician's completed case to `pending_review` for senior tech approval.

### 4. Dashboard Stat Tracking (Partially Implemented)

**Admin Dashboard** [cases/templates/cases/admin_dashboard.html](cases/templates/cases/admin_dashboard.html#L51-L60)

```html
<div class="stat-mini">
    <div class="stat-mini-value">{{ stats.requiring_review }}</div>
    <div class="stat-mini-label">Review</div>
</div>
```

**File:** [cases/views.py](cases/views.py#L176-L210) - Admin dashboard view calculates:
```python
'pending_review': cases.filter(status='pending_review').count(),
```

**Note:** Stat is tracked but no way to actually create cases with this status.

---

## Current Implementation vs Requirements

### What the Requirements Say (From Workflow Docs)

#### 1. **When Review is Triggered** (MISSING)
**From:** [TECHNICIAN_WORKFLOW.md](TECHNICIAN_WORKFLOW.md#L439-L465)

```
### Workflow: "Junior Technician Case Processing"
When a Level 1 technician completes a case:
1. Case completion submitted by Level 1 tech
2. System automatically sets case status → "pending_review"
3. Case appears in Level 2/3 "Review Queue"
4. Level 2/3 tech reviews completed work
5. Option A: Approve → Status changes to "completed" → Release to member
6. Option B: Request Changes → Status back to "accepted" → Tech makes revisions
```

**Current Reality:** ❌ This workflow DOES NOT EXIST in the code

#### 2. **Senior Tech Review Queue** (MISSING)

**From:** [TECHNICIAN_WORKFLOW.md](TECHNICIAN_WORKFLOW.md#L261-L290)

```
## Technician Actions by Case Status

### When User Level = Level 2 or Level 3
- ✓ See "Cases Pending Quality Review" section
- ✓ View all Level 1 technician cases needing approval
- ✓ One-click approve/reject review
- ✓ Add review notes
```

**Partial Implementation Found:** [_archived_files/webform_views_old.py](/_archived_files/webform_views_old.py#L830-L860)

```python
# Get cases pending review (for Level 2 and Level 3 only)
review_queue = Case.objects.none()
if user.user_level in ['level_2', 'level_3']:
    review_queue = Case.objects.filter(
        status='pending_review',
        reviewed_by__isnull=True
    ).select_related('member', 'assigned_to')
```

**Note:** This view is ARCHIVED and not used in current dashboard!

#### 3. **Review & Approval Actions** (MISSING)

**From Requirements:**
- Level 2/3 tech clicks "Review" button on case
- Can see:
  - Original investigation by Level 1 tech
  - Report uploaded
  - Member documents
- Options:
  - ✅ **APPROVE** - Sets status to 'completed', releases to member
  - ❌ **REQUEST CHANGES** - Sends back to Level 1 tech with notes
  - 💬 **ADD REVIEW NOTES** - Comments on quality/findings

**Current Reality:** ❌ None of these actions exist

---

## Database/Model Evidence

### What EXISTS in Database

```
Case Model Fields:
├── assigned_to (FK to User)
├── reviewed_by (FK to User - EMPTY for Level 1 cases)
├── status (choices: submitted, accepted, pending_review, completed)
└── [other fields]

User Model Fields:
├── role ('technician', 'administrator', 'manager', 'member')
└── user_level ('level_1', 'level_2', 'level_3')
```

### What's MISSING

```
❌ No "review_action" or "review_approval" status indicator
❌ No "reviewed_at" timestamp field
❌ No "review_notes" field for senior tech comments
❌ No "review_reject_reason" if changes requested
❌ No "requires_review_by_date" deadline field
```

---

## Views/Functions Analysis

### Current Case Completion Flow

**File:** [cases/views.py](cases/views.py#L1250-L1370)

```python
@login_required
def mark_case_complete(request, pk):
    # Current flow:
    case.status = 'completed'  # ❌ DIRECTLY to completed!
    case.save()
    # Should check: if case.assigned_to.user_level == 'level_1'
    # Then: set status = 'pending_review' instead
```

**Problem:** No check for Level 1 technician → No review queue creation

### Admin Dashboard View

**File:** [cases/views.py](cases/views.py#L66-L210)

Current stats calculation:
```python
stats = {
    'pending_review': cases.filter(status='pending_review').count(),
    'requiring_review': cases.filter(assigned_to__user_level='level_1', status='completed').count(),
}
```

**Note:** `pending_review` count will always be 0 because nothing sets status to 'pending_review'!

---

## Specific Gaps vs Requirements

| Feature | Requirement | Current Status | Location |
|---------|-------------|---|---|
| **Level 1 Trigger** | When Level 1 tech completes case, auto-set pending_review | ❌ Missing | cases/views.py |
| **Review Queue UI** | Level 2/3 see review queue in dashboard | ❌ Missing/Archived | archived webform_views_old.py |
| **Approval Action** | Click "Approve" button, case becomes completed | ❌ Missing | N/A |
| **Rejection Action** | Click "Request Changes" button, case goes back to assigned tech | ❌ Missing | N/A |
| **Review Notes** | Senior tech can add comments during review | ❌ Missing | N/A |
| **Audit Trail** | Track who reviewed, when, and decision | ⚠️ Partial | core/models.py has AuditLog |
| **Reviewed_by Field** | Record which senior tech did review | ✅ Exists | cases/models.py |
| **Time Tracking** | When was case reviewed | ❌ Missing | Need reviewed_at field |

---

## Requirements Summary

### When Review Should Happen

1. **Trigger:** Level 1 technician clicks "Mark as Complete"
2. **Action:** System checks `assigned_to.user_level == 'level_1'`
3. **Result:** Case status → `pending_review` (NOT `completed`)
4. **Queue:** Appears in "Cases Pending Review" for Level 2/3 techs

### What Level 2/3 Can Do

1. **View Review Queue:**
   - See all cases with status='pending_review' assigned to Level 1 techs
   - Sort by date, urgency, etc.

2. **Review Case:**
   - Click case to view full details
   - See Level 1 tech's investigation
   - See uploaded reports
   - See member documents

3. **Take Action:**
   - **APPROVE:** Case → `completed`, automatically release schedule starts
   - **REQUEST CHANGES:** Case → `accepted`, send back to Level 1 tech with revision notes
   - **ADD NOTES:** Quality feedback (visible to manager/admin/original tech)

### Audit Trail

- When review action taken: log WHO (which L2/L3 tech), WHAT (approve/reject), WHEN, WHY
- If rejection: log reason and revision notes
- Update `reviewed_by` field with Level 2/3 tech's user ID

---

## Workflow Scenarios (From Requirements)

### Scenario 1: Happy Path (Approve)

```
Level 1 Tech - Case XYZ123
├─ Completes investigation ✓
├─ Uploads report ✓
├─ Clicks "Mark Complete"
└─ System sets status → "pending_review"

Level 2/3 Tech - Review Queue
├─ Sees XYZ123 in pending_review list
├─ Clicks to review
├─ Reads Level 1 findings (looks good!)
├─ Clicks "APPROVE CASE"
└─ System:
   ├─ Sets reviewed_by = Level 2/3 tech ID
   ├─ Sets status = "completed"
   ├─ Starts release timer (admin delay setting)
   └─ Logs review action to audit trail

Member
├─ Sees case status: "Ready" (or "Completed")
└─ Receives report at scheduled release time
```

### Scenario 2: Request Changes (Reject)

```
Level 2/3 Tech - Review Queue
├─ Reviews XYZ123
├─ Investigation seems incomplete
├─ Clicks "REQUEST CHANGES"
├─ Selects reason: "Need more investigation"
├─ Adds notes: "Please verify employment dates..."
└─ System:
   ├─ Sets status = "accepted" (back to working state)
   ├─ Sets reviewed_by = Level 2/3 tech ID
   ├─ Sends notification to Level 1 tech
   └─ Logs review rejection to audit trail

Level 1 Tech
├─ Gets notification: "Revision needed"
├─ Reviews feedback
├─ Does additional work
├─ Uploads new report
├─ Clicks "Mark Complete" AGAIN
└─ Case goes back to Level 2/3 review queue
```

---

## Current Test Evidence

**File:** [core/views_reports.py](core/views_reports.py#L91-L105)

Report data TRIES to calculate review metrics:

```python
# Quality review metrics - approval rates
level_1_cases = cases_qs.filter(assigned_to__user_level='level_1')
level_1_completed = level_1_cases.filter(status='completed').count()
level_1_pending_review = level_1_cases.filter(status='pending_review').count()
level_1_total = level_1_cases.count()

if level_1_total > 0:
    approval_rate = (level_1_completed / level_1_total) * 100
else:
    approval_rate = 0
```

**Problem:** `level_1_pending_review` will ALWAYS be 0 because cases never enter pending_review!

---

## What's Actually Needed

### Models (Add Fields)

```python
# cases/models.py - Case model
reviewed_at = models.DateTimeField(
    null=True, blank=True,
    help_text='When the case was reviewed by Level 2/3 tech'
)
review_notes = models.TextField(
    blank=True,
    help_text='Quality review notes from senior technician'
)
review_status = models.CharField(
    max_length=20,
    choices=[
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('changes_requested', 'Changes Requested'),
    ],
    default='pending',
    null=True, blank=True
)
```

### Views (Add Functions)

```python
# cases/views.py

def mark_case_complete(request, pk):
    # Check if Level 1
    if case.assigned_to.user_level == 'level_1':
        case.status = 'pending_review'  # NEW!
    else:
        case.status = 'completed'
    case.save()

def review_queue(request):
    # NEW! Show all pending_review cases for Level 2/3 techs
    cases = Case.objects.filter(
        status='pending_review',
        assigned_to__isnull=False
    ).select_related('assigned_to', 'member')

def approve_case_review(request, pk):
    # NEW! Level 2/3 tech approves Level 1 case
    case.status = 'completed'
    case.reviewed_by = request.user
    case.review_status = 'approved'
    case.reviewed_at = timezone.now()
    case.save()

def request_review_changes(request, pk):
    # NEW! Level 2/3 tech requests revisions
    case.status = 'accepted'
    case.reviewed_by = request.user
    case.review_status = 'changes_requested'
    case.review_notes = request.POST.get('notes')
    case.reviewed_at = timezone.now()
    case.save()
```

### Templates (Add UI)

```html
<!-- For Level 2/3 Technicians -->
{% if user.user_level in 'level_2,level_3' %}
  <div class="card">
    <h5>Cases Pending Quality Review</h5>
    {% for case in pending_review_cases %}
      <div class="case-card">
        <a href="{% url 'review_case' case.id %}">{{ case.external_case_id }}</a>
        <small>L1 Tech: {{ case.assigned_to.get_full_name }}</small>
        <button onclick="approve_review({{ case.id }})">✓ Approve</button>
        <button onclick="request_changes({{ case.id }})">✗ Request Changes</button>
      </div>
    {% endfor %}
  </div>
{% endif %}
```

---

## Recommendation

**Priority:** HIGH (Quality Control Feature)

The review functionality exists in the **data model** and **workflow documentation**, but is **NOT IMPLEMENTED in the views/templates**. 

To complete this feature, you need to:

1. ✅ Add model fields for review metadata (reviewed_at, review_notes)
2. ✅ Modify case completion to trigger pending_review for Level 1 techs
3. ✅ Create review queue view for Level 2/3 techs
4. ✅ Implement approve/reject review actions
5. ✅ Add review queue to dashboard templates
6. ✅ Add audit logging for all review actions
7. ✅ Add email notifications for review decisions

---

## Files Involved

**Already Implemented:**
- [accounts/models.py](accounts/models.py) - User levels defined
- [cases/models.py](cases/models.py) - reviewed_by field, requires_review property
- [core/views_reports.py](core/views_reports.py) - Review metrics attempted

**Partially Implemented:**
- [_archived_files/webform_views_old.py](/_archived_files/webform_views_old.py#L830-L860) - Old review queue (archived)
- [cases/templates/cases/technician_workbench.html](cases/templates/cases/technician_workbench.html#L56-L80) - UI template structure (old)

**Missing:**
- Review trigger logic in mark_case_complete
- Review queue view
- Review action endpoints (approve/reject)
- Review queue template for dashboard
- Review decision email notifications

---

**End of Breakdown**
