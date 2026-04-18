# Local Testing Guide — Case Review Workflow

**Date:** April 14, 2026 | **Commit:** `c227c48`

---

## Scenario 1: L1 Tech Submits → Senior Reviews → Admin Verifies Audit

**Case:** TEST-L1-TIER1-001 (Case 44) — L1 tech, Tier 1

---

### Step 1 — Log in as `tech_l1` / `testpass123`

**Testing:** L1 tech submits a case for quality review  
**→ Open Case 44**

1. Open Case 44 from the dashboard or case list
2. In the Actions panel on the right, click **"Submit for Review"**
3. **Expected:**
   - Green success banner
   - Status changes to **Pending Review**
   - Actions panel now says _"Awaiting Quality Review"_ — no further actions available
4. Log out

---

### Step 2 — Log in as `Bene1` / `testpass123`

**Testing:** Senior tech (L3) reviews and approves the submitted case  
**→ Open Case 44**

1. Open Case 44
2. Blue banner at top: _"Quality Review Required"_ with three buttons
3. Click **"Approve Case"** (green)
4. In the modal: select **"Release Now (ASAP)"**, optionally add review notes
5. Click **"Approve & Complete"**
6. **Expected:**
   - Case status → **Completed**
   - Success message confirms release
7. Log out

---

### Step 3 — Log in as `admin` / `testpass123`

**Testing:** Admin verifies the audit trail captured both actions  
**→ Open Case 44 → Audit History, then Global Audit Log**

1. Open Case 44 → Audit History tab
2. **Expected entries (newest first):**
   - `case_review_approved` — Bene1 approved the case
   - `case_submitted_for_review` — tech_l1 submitted for review
3. Go to the Global Audit Log page
4. **Expected:** Same entries visible here
5. Log out

---
---

## Scenario 2: L2 Tech Completes Without Review

**Case:** TEST-L2-TIER1-001 (Case 46) — L2 tech, Tier 1

---

### Step 1 — Log in as `tech_l2` / `testpass123`

**Testing:** L2 tech completes a case — should skip review and go straight to completed  
**→ Open Case 46**

1. Open Case 46
2. In the Actions panel, click **"Mark as Completed"** (green)
3. Pre-Completion Review page loads
4. Scroll to bottom, select **"Release Now"**, click **"Mark as Completed"**
5. **Expected:**
   - Case status → **Completed** (NOT Pending Review)
   - Success message confirms immediate release
6. Log out

---

### Step 2 — Log in as `admin` / `testpass123`

**Testing:** Admin verifies audit shows direct completion, no review step  
**→ Open Case 46 → Audit History**

1. Open Case 46 → Audit History tab
2. **Expected:** `case_completed` entry from tech_l2
3. **No** `case_submitted_for_review` entry — L2 at Tier 1 doesn't require review
4. Log out

---
---

## Scenario 3: Ad-hoc Review Request → Response

**Case:** TEST-L2-ADHOC-001 (Case 47) — L2 tech, Tier 1

---

### Step 1 — Log in as `tech_l2` / `testpass123`

**Testing:** Tech requests a review from a specific senior tech  
**→ Open Case 47**

1. Open Case 47
2. Click **"Request Ad-hoc Review"**
3. Modal pops up:
   - **"Request Review From"** → select **Bene1**
   - **"What do you need reviewed?"** → type: `Can you check if the credit is correct?`
4. Click **"Submit Request"**
5. **Expected:**
   - Modal closes, green success banner
   - **"Review Requests"** card appears in sidebar with yellow **Pending** badge
6. Log out

---

### Step 2 — Log in as `Bene1` / `testpass123`

**Testing:** Senior tech responds to the review request  
**→ Open Case 47**

1. Check the **notification bell** in the nav bar — should show new notification
2. Open Case 47
3. In the **"Review Requests"** card, click **"Respond"** on the pending request
4. Modal opens with request details
5. Type response notes: `Credit looks correct. Good work.`
6. Click the green **"Approve"** button
7. **Expected:** Status changes to green **Approved** badge
8. Log out

---

### Step 3 — Log in as `admin` / `testpass123`

**Testing:** Admin verifies the review request appears in audit  
**→ Open Case 47 → Audit History, then Global Audit Log**

1. Open Case 47 → Audit History tab
2. **Expected:** `review_requested` entry from tech_l2
3. Check global Audit Log for the same entry
4. Log out

---
---

## Scenario 4: Review Request Gets Escalated

**Case:** TEST-L1-ADHOC-001 (Case 48) — L1 tech, Tier 1

---

### Step 1 — Log in as `tech_l1` / `testpass123`

**Testing:** L1 tech requests an ad-hoc review without picking a specific reviewer  
**→ Open Case 48**

1. Open Case 48
2. Click **"Request Ad-hoc Review"**
3. Modal:
   - **Reviewer:** Leave as "Any Senior Technician / Admin" (don't select anyone)
   - **Notes:** `Need a second opinion on the report format before I submit`
4. Click **"Submit Request"**
5. **Expected:** Success banner, Review Requests panel shows **Pending** badge
6. Log out

---

### Step 2 — Log in as `Bene1` / `testpass123`

**Testing:** Senior tech isn't sure, escalates the review to admin  
**→ Open Case 48**

1. Check notification bell — should have a notification about the review request
2. Open Case 48
3. Click **"Respond"** on the pending request
4. Type notes: `Not sure about the report format. Escalating to admin.`
5. Click the blue **"Escalate"** button
6. **"Escalate To"** dropdown appears — select **admin (Administrator)**
7. Click **"Escalate"** again
8. **Expected:**
   - Original request → blue **Escalated** badge
   - NEW request appears → yellow **Pending** badge targeting admin
9. Log out

---

### Step 3 — Log in as `admin` / `testpass123`

**Testing:** Admin handles the escalated request and verifies the full chain  
**→ Open Case 48, then Case 48 → Audit History**

1. Check notification bell — should have escalation notification
2. Open Case 48
3. Review Requests panel should show TWO entries:
   - `tech_l1 → Any Senior` — **Escalated** (blue)
   - `Bene1 → admin` — **Pending** (yellow)
4. Click **"Respond"** on the pending request
5. Notes: `Report format is fine as-is. Approved.`
6. Click **"Approve"**
7. **Expected:** Second request → green **Approved** badge
8. Open Case 48 → Audit History tab
9. **Expected entries (newest first):**
   - `review_requested` — Bene1 escalated (new request created)
   - `review_escalated` — Bene1 escalated the original
   - `review_requested` — tech_l1 created the original request
10. Log out

---
---

## Scenario 5: Admin Configures Review Settings

**Case:** No specific case — testing the admin settings page

---

### Step 1 — Log in as `admin` / `testpass123`

**Testing:** Admin can toggle per-tech per-tier review requirements  
**→ Open Review Settings page, then Global Audit Log**

1. Go to the **Review Settings** page (Cases menu → Review Settings)
2. **Expected:** Table of all technicians with toggle switches for Tier 1, 2, 3
3. **Default states:** Tier 1 = ON for all, Tier 2 and 3 = OFF, labels say "Default"
4. Find the **tech_l2** row
5. Turn Tier 2 **ON** for tech_l2
6. **Expected:** Toggle saves instantly, label changes to "Set by admin"
7. Go to the **Global Audit Log**
8. **Expected:** `review_setting_changed` entry from admin
9. Log out

---
---

## Scenario 6: Permission-Based Access Control

**Case:** No specific case — testing permission flags

---

### Step 1 — Log in as `admin` / `testpass123`

**Testing:** Admins always have full access  
**→ Open Delegate Management, then Review Settings**

1. Go to **Delegate Management** page
2. **Expected:** Page loads
3. Go to **Review Settings** page
4. **Expected:** Page loads
5. Log out

---

### Step 2 — Log in as `Bene1` / `testpass123`

**Testing:** Tech WITH `can_manage_delegates` and `can_manage_review_settings` permissions  
**→ Open Delegate Management, then Review Settings**

1. Go to **Delegate Management** page
2. **Expected:** Page loads
3. Go to **Review Settings** page
4. **Expected:** Page loads
5. Log out

---

### Step 3 — Log in as `ben2` / `testpass123`

**Testing:** Tech WITHOUT permissions gets blocked  
**→ Try Delegate Management, then Review Settings**

1. Go to **Delegate Management** page
2. **Expected:** Redirected to dashboard with error: _"You do not have permission to manage delegates."_
3. Go to **Review Settings** page
4. **Expected:** 403 Forbidden
5. Log out

---
---

## Final Verification: Global Audit Log

### Log in as `admin` / `testpass123`

**Testing:** All activity from every scenario is captured in the global audit  
**→ Open Global Audit Log**

Go to the **Global Audit Log** page. Expected entries:

| Action | Scenario | Who |
|---|---|---|
| `review_setting_changed` | 5 | admin |
| `review_requested` (escalation) | 4 | Bene1 |
| `review_escalated` | 4 | Bene1 |
| `review_requested` | 4 | tech_l1 |
| `review_requested` | 3 | tech_l2 |
| `case_completed` | 2 | tech_l2 |
| `case_review_approved` | 1 | Bene1 |
| `case_submitted_for_review` | 1 | tech_l1 |

---

## Resetting Test Data

Run this to start all scenarios over:

```
python manage.py shell -c "
from cases.models import Case, CaseReviewRequest, TechReviewSetting, CaseReviewHistory
from core.models import AuditLog, StaffNotification
Case.objects.filter(external_case_id__startswith='TEST-').update(
    status='accepted', review_status=None, reviewed_by=None,
    reviewed_at=None, review_notes='', date_completed=None,
    actual_release_date=None, scheduled_release_date=None
)
CaseReviewRequest.objects.filter(case__external_case_id__startswith='TEST-').delete()
CaseReviewHistory.objects.filter(case__external_case_id__startswith='TEST-').delete()
AuditLog.objects.filter(case__external_case_id__startswith='TEST-').delete()
StaffNotification.objects.filter(case__external_case_id__startswith='TEST-').delete()
TechReviewSetting.objects.all().delete()
print('Reset complete')
"
```
