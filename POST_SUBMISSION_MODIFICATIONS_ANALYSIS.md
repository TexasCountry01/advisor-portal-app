# Post-Submission Case Modifications - Investigation & Options

**Question:** How can an advisor edit a due date, or upload new docs for a case after it's been submitted (but before it's been completed)? If they do this, how does the tech know (what is the dashboard indicator that something new has come in)?

---

## Current System Architecture

### What's Already Implemented ✅

The system **already has comprehensive post-submission modification capabilities**:

#### 1. **Member/Advisor Document Upload (After Submission)**
- **Function:** `upload_member_document()` in `cases/views.py` (line 1934)
- **Allowed Statuses:** `draft`, `submitted`, `completed`, `pending_review`, `accepted`, `resubmitted`, `hold`
- **Restrictions:** Only the case owner (member) can upload
- **What Happens:**
  - Document uploaded with type `supporting` (auto-appended employee last name)
  - `has_member_updates` flag set to `True`
  - `member_last_update_date` timestamp recorded
  - Audit log entry created: `member_document_uploaded`
  - Technician/Admin notified via dashboard indicator

#### 2. **Case Details Editing (After Submission)**
- **Function:** `edit_case_details()` in `cases/views.py` (line 2749)
- **Who Can Edit:** Technician (if assigned or unassigned), Manager, Administrator
- **Allowed Statuses:** `draft`, `submitted`, `accepted`, `pending_review`
- **Fields That Can Be Edited:**
  - Employee first/last name
  - Due date
  - Assigned technician
- **What Happens:**
  - All changes tracked in detailed audit log
  - Optional email notification sent to member
  - Changes recorded with old/new values
  - Audit log entry created: `case_details_edited`

#### 3. **Dashboard Indicator System**

**Technician Dashboard:**
- Shows `🔔 New Info` badge (yellow/warning color) next to case code
- Title: "Member has provided new information"
- Visible next to case workshop code in table
- Line 341-343 in `technician_dashboard.html`

**Manager Dashboard:**
- Same `🔔 New Info` badge system
- Line 283-285 in `manager_dashboard.html`

**Admin Dashboard:**
- Not explicitly shown in grep search, but likely similar

**Reset Behavior:**
- Badge automatically clears when technician/admin views the case detail
- Line 674-678 in `cases/views.py`: Resets `has_member_updates=False` on view

---

## Database Fields Supporting This

### Case Model Fields
```python
# Member Updates Tracking (for post-submission edits/uploads)
has_member_updates = models.BooleanField(
    default=False,
    help_text='Flag indicating member has provided new information/documents after submission'
)

member_last_update_date = models.DateTimeField(
    null=True,
    blank=True,
    help_text='When the member last updated the case (after initial submission)'
)
```

### Audit Log Action Types
- `member_document_uploaded` - Tracks what documents were added, by whom, when
- `case_details_edited` - Tracks changes to case details with old/new values
- `document_uploaded` - General document upload tracking
- `member_comment_added` - If member adds comments (workflow dependent)

---

## Current Flow Example

### Scenario: Member Uploads Document After Submission

1. **Member Action:** Logs into dashboard, navigates to submitted case, uploads additional W-4 form
2. **System Response:**
   - Document saved as `CaseDocument` with type `supporting`
   - `Case.has_member_updates = True`
   - `Case.member_last_update_date = Now()`
   - Audit log entry created with filename, size, notes
3. **Technician View:**
   - Logs into dashboard, sees `🔔 New Info` badge next to case
   - Clicks case to view details
   - Badge automatically dismissed on view
   - Can see full document upload history in audit tab
4. **Manager/Admin View:**
   - Sees same `🔔 New Info` badge on dashboard
   - Can see audit trail of what was added

---

## Current Limitations & Gaps

### What's **Missing or Limited:**

1. **Email Notification to Technician**
   - ❌ No automatic email when member uploads documents
   - ✓ **Fix:** Should email assigned technician when `has_member_updates` is set
   - **Impact:** Tech might miss new docs if not actively checking dashboard

2. **Member Edit Capability**
   - ❌ Members cannot edit due dates themselves post-submission
   - ✓ **Design:** Intentional - prevents scope creep, ensures tech approval
   - **Current:** Only techs/managers/admins can edit due dates

3. **Due Date Changes Don't Trigger Urgency Recalc**
   - ⚠️ When technician changes due date via `edit_case_details()`, urgency isn't automatically recalculated
   - **Impact:** Case could change from normal to rushed (or vice versa) but urgency field stays same
   - **Fix Needed:** Add urgency recalculation in `edit_case_details()` post-save

4. **No In-App Notification to Technician**
   - ❌ Only dashboard badge indicator exists
   - ❌ No browser notification or in-app alert modal
   - **Current:** Passive indicator only - tech must actively check

5. **Limited Scope of Edit Restrictions**
   - ✓ `completed` status cannot be edited (good)
   - ⚠️ `hold` status cannot be edited (might be limiting if tech wants to reset due date during hold)
   - ⚠️ `resubmitted` status CAN be edited (might need review)

6. **No Member-Initiated Due Date Change Requests**
   - ❌ Members can't request due date extension
   - ✓ **Design:** Intentional - prevents scope creep
   - **Alternative:** Members can upload documents + notes requesting extension

---

## Options & Recommendations

### **Option 1: Keep Current System As-Is** ✓ RECOMMENDED (With Enhancements)

**Rationale:**
- System is well-designed for the workflow
- Prevents member from making unauthorized scope changes
- Audit trail is comprehensive
- Tech maintains control

**Enhancements to Add:**
1. ✅ Send email to assigned technician when `has_member_updates` is set
   - Subject: "New information added to case [CASE_ID]"
   - Include: What was added, document names, member notes
2. ✅ Fix urgency recalculation when tech edits due date
   - Recalculate rush status after any date change
3. ✅ Add in-app notification modal on case detail view
   - Show "Member updated this case X minutes ago"
   - List what was added
4. ✅ Add "Last Member Update" timestamp visible on dashboard
   - Show in case row: "Updated: 2 hours ago"

**Implementation Effort:** Low-Medium (Email + Urgency Recalc + UI changes)

---

### **Option 2: Add Member-Initiated Due Date Change Requests**

**Scenario:** Member can submit a "request" to change due date without forcing it

**How It Works:**
1. Member can propose new due date with reasoning
2. Creates audit log entry: `member_due_date_change_request`
3. Sets flag: `member_pending_change_request = True`
4. Dashboard shows: `⚠️ Extension Requested` badge
5. Technician reviews, approves/denies, can edit if approved

**Pros:**
- ✅ Gives members agency
- ✅ Clear audit trail of requests
- ✅ Tech still controls final decision

**Cons:**
- ❌ Adds complexity to workflow
- ❌ Potential for member harassment/spam requests
- ❌ Requires new model fields

**Implementation Effort:** Medium-High

---

### **Option 3: Allow Member Self-Service Due Date Extensions** (Limited)

**Scenario:** Members can extend due date by X days (1-3 days) without tech approval

**How It Works:**
1. Member can click "Request Extension" on case detail
2. Automatically extends due date by 2 days (or configurable)
3. Must include reason in notes
4. Creates audit entry: `member_self_extended_due_date`
5. Capped at 1-2 extensions per case

**Pros:**
- ✅ Reduces member friction
- ✅ Empowers members for minor adjustments
- ✅ Self-limiting (caps prevent abuse)

**Cons:**
- ❌ Could cause business process issues
- ❌ Needs business rule validation
- ❌ Might extend rush cases unintentionally

**Implementation Effort:** Medium

---

### **Option 4: Create Notification Center** (Enhancement)

**Scenario:** Add dedicated notification/activity center separate from dashboard

**How It Works:**
1. New page: `/cases/notifications/` or sidebar widget
2. Shows all case activity for assigned cases:
   - Member uploaded docs
   - Member added comments
   - Case status changed
   - Due date approaching
3. Notifications can be marked as read/unread
4. Option to get email for certain events
5. Time-based filter: Today, This Week, All

**Pros:**
- ✅ Centralized activity view
- ✅ No need to check each case dashboard
- ✅ Can set notification preferences
- ✅ Better UX than badges alone

**Cons:**
- ❌ Additional development effort
- ❌ Could add feature creep
- ❌ Requires notification preference storage

**Implementation Effort:** Medium-High

---

### **Option 5: Automated Actions Based on Member Updates** (Advanced)

**Scenario:** System automatically triggers actions when member updates case

**Examples:**
- Member uploads docs → Auto-move case status from `submitted` to `accepted`
- Member adds comment → Auto-assign to available technician
- Member requests extension → Auto-extend by 2 days, email tech

**Pros:**
- ✅ Reduces manual tech intervention
- ✅ Faster case processing
- ✅ More responsive to member needs

**Cons:**
- ❌ Could cause unintended status changes
- ❌ Requires business rule definition
- ❌ Potential for errors
- ❌ Significant development effort

**Implementation Effort:** High

---

## Summary Table

| Option | Effort | Member Friction | Tech Awareness | Recommended |
|--------|--------|-----------------|-----------------|-------------|
| 1: Current + Enhancements | Low-Medium | Low | High ✅ | **YES** |
| 2: Change Requests | Medium-High | Medium | High | Maybe |
| 3: Self-Service Extensions | Medium | Low | Medium | Maybe |
| 4: Notification Center | Medium-High | Low | High | Maybe |
| 5: Automated Actions | High | Very Low | Very High | No |

---

## Quick Reference: Current Capabilities

### ✅ What Members CAN Do (Post-Submission)
- Upload supplementary documents
- Add notes/context to documents
- View case status and history
- View audit trail (limited)
- Provide feedback/comments (if enabled)

### ✅ What Techs/Managers CAN Do (Post-Submission)
- Edit employee name
- Edit due date
- Reassign to different technician
- Upload documents on behalf
- Add internal notes
- View complete audit trail
- See `has_member_updates` badge
- See member update timestamp

### ❌ What Members CANNOT Do (By Design)
- Edit due dates
- Change case status
- Reassign case
- Delete documents
- Edit case type/tier
- Mark case as completed

### ❌ What's NOT Automated
- Email notification when member uploads docs
- Urgency recalculation after due date edit
- In-app notification modal
- Active notification center
- Member-initiated due date requests

---

## Recommended Next Steps

If you want to implement improvements, I recommend doing them in this order:

1. **Phase 1 (High Priority):**
   - Add email notification to technician when member uploads docs
   - Fix urgency recalculation when tech edits due date
   - Add "Last Member Update" display to dashboards

2. **Phase 2 (Medium Priority):**
   - Add in-app notification modal on case view
   - Add member update details on case detail page
   - Improve audit trail visibility

3. **Phase 3 (Optional):**
   - Create notification center
   - Add member-initiated request system
   - Consider automated action rules

---

**Document Created:** January 23, 2026  
**Status:** Complete Analysis - Ready for Decision
**Files Involved:**
- `cases/views.py` - `upload_member_document()`, `edit_case_details()`
- `cases/models.py` - `Case` model with tracking fields
- `cases/templates/cases/technician_dashboard.html` - Badge indicator
- `cases/templates/cases/manager_dashboard.html` - Badge indicator
- `core/models.py` - `AuditLog` with action types
