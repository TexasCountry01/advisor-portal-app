# Alert Routing Redesign — Implementation Spec

Generated: 2026-08-09  
Status: Approved for implementation  

---

## Objective

Eliminate Tiffany and Becky's confusion of receiving an alert, opening a case, and finding nothing actionable.  
Root cause: multiple non-chat notification types were being routed into the same alert surfaces as chat messages, with no visual distinction between them.

**Core fix:** Separate alert surfaces by what they signal.  Chat goes to the nav bell and row badge (you open the case, the chat is right there). Modifications get their own persistent visual badge on the case row — visible at a glance without opening the case. Everything else is removed from the alert system entirely (the yellow review banners, assignment confirmation, etc. already handle those).

---

## Two Alert Surfaces After Redesign

### Surface 1 — Nav bar bell + case row badge number
**Driver:** `StaffNotification` (bell) + `UnreadMessage` (row badge number)  
**Signal:** There is a chat message waiting. Open the case — the message is in the chat.  
**Scope:** Chat only.

### Surface 2 — Left-side case row label badge
**Driver:** Derived from existing `Case` model fields — no new DB fields required  
**Signal:** This case has a structural flag requiring awareness. Visible in the list without opening the case.  
**Scope:** Modification types only.

| Badge | Condition | Color | Label |
|---|---|---|---|
| ProFeds Error | `case.has_profeds_error == True` | Red | `PF ERR` |
| Standard Modification | `case.original_case is not null AND case.has_profeds_error == False` | Amber/yellow | `MOD` |

Both badges appear on the **new modification case row**, not the original.  
Both badges are already derivable from existing model data — `has_profeds_error` is copied to the new case at creation, and `original_case` FK is set. No migration required.

---

## Per-Notification Routing Table (After Redesign)

| Notification | Currently Goes To | After Redesign | Change |
|---|---|---|---|
| `case_chat_message` | Nav bell + row badge | Nav bell + row badge | **No change** |
| `case_modification_error` (ProFeds error) | Nav bell (tech + all managers/admins) | Left-side `PF ERR` badge on new case row | Remove `StaffNotification` creation; remove `UnreadMessage` for modification system message; badge is template-derived |
| `case_assigned` | Nav bell (new tech) | Removed | Remove `StaffNotification` creation |
| `quality_review_feedback` | Nav bell (L1 tech) | Removed | Remove `StaffNotification` creation — yellow review banner handles this |
| `review_requested` | Nav bell (reviewer or all eligible L2/L3+admins) | Removed | Remove all `StaffNotification` creation — yellow review banner handles this |
| `review_action_taken` | Nav bell (original submitter) | Removed | Remove `StaffNotification` creation — yellow review banner handles this |
| `case_on_hold` | Member `CaseNotification` only (already staff-silent) | No change | Already correct — was never a staff alert |
| `member_document_uploaded` — case NOT on hold | Nav bell (assigned tech) | Removed | Add `if case.status == 'hold':` guard to all 3 creation sites |
| `member_document_uploaded` — case IS on hold | Nav bell (assigned tech) | Nav bell (assigned tech) | **No change** — existing behavior preserved |
| `member_change_request` | Nav bell (assigned tech) + UnreadMessage | Removed | Remove `StaffNotification` creation and `UnreadMessage` |
| **NEW: standard mod badge** | Not built | Left-side `MOD` badge on new case row | Template change only — derived from `original_case is not null AND has_profeds_error == False` |

---

## Implementation Tasks

### Task 1 — Remove `case_assigned` StaffNotification
**File:** `cases/views.py` line ~3391  
**Change:** Delete the `StaffNotification.objects.create(notification_type='case_assigned', ...)` block inside the reassign success handler.

---

### Task 2 — Remove `quality_review_feedback` StaffNotifications (3 sites)
**File:** `cases/views.py`  
- Line ~7161: approve review path → remove  
- Line ~7247: revisions requested path → remove  
- Line ~7368: corrections applied path → remove  

All three notify `case.assigned_to` (L1 tech). Yellow banner handles this.

---

### Task 3 — Remove `review_requested` StaffNotifications (4 sites)
**File:** `cases/views.py`  
- Line ~7485: `submit_for_review` — specific reviewer → remove  
- Line ~7502: `submit_for_review` — broadcast to all eligible → remove entire loop  
- Line ~7615: `request_case_review` — specific reviewer → remove  
- Line ~7631: `request_case_review` — broadcast loop → remove  

Yellow banner handles review awareness for all parties.

---

### Task 4 — Remove `review_action_taken` StaffNotifications (2 sites)
**File:** `cases/views.py`  
- Line ~7730: escalation path `review_action_taken` to original requester → remove  
- Line ~7739: all other actions `review_action_taken` to original requester → remove  

Yellow banner handles feedback to original submitter.

---

### Task 5 — Gate `member_document_uploaded` on hold status (3 sites)
**File:** `cases/views.py`  
- Line ~4016 (upload_case_document view)  
- Line ~4657 (upload_case_document_v2 or similar)  
- Line ~8866 (member upload endpoint)  

**Change at each site:** Wrap the `StaffNotification.objects.create(notification_type='member_document_uploaded', ...)` with `if case.status == 'hold':`.

---

### Task 6 — Remove `member_change_request` StaffNotification (2 sites)
**File:** `cases/views.py`  
- Line ~8512: cancellation path → remove `StaffNotification` creation  
- Line ~8577: change request path → remove `StaffNotification` creation  

Note: the `CaseMessage` and `UnreadMessage` created for the cancellation system message (also around line 8512) are chat-driven and belong to Surface 1 — they stay.

---

### Task 7 — Remove `case_modification_error` StaffNotifications and modification UnreadMessage (4+ sites)
**File:** `cases/views.py`  
- Line ~5847: member modification path — remove `StaffNotification` for tech  
- Line ~5862: member modification path — remove `StaffNotification` broadcast loop (managers/admins)  
- Line ~5840: member modification path — remove `UnreadMessage.objects.get_or_create` for modification system message  
- Line ~6024: staff modification path — remove `StaffNotification` for tech  
- Line ~6038: staff modification path — remove `StaffNotification` broadcast loop  

The `CaseMessage` posted to the original case chat ("MODIFICATION REQUEST REASON") is retained for audit/history — only the `UnreadMessage` row creation that drives the badge is removed.

---

### Task 8 — Add left-side badge display to staff dashboard templates
**Files:** `cases/templates/cases/technician_dashboard.html`, `admin_dashboard.html`, `manager_dashboard.html`

For each case row, add a badge element before the employee name or in a dedicated column:

```
if case.has_profeds_error:
    → red badge: "PF ERR"
elif case.original_case_id is not None and not case.has_profeds_error:
    → amber badge: "MOD"
```

No view changes needed — `original_case_id` is already on the queryset. Verify `select_related('original_case')` is present or use `original_case_id` (the FK integer) to avoid extra queries — presence of a non-null value is sufficient.

---

## Files Affected

| File | Change Type |
|---|---|
| `cases/views.py` | Remove/gate ~10 `StaffNotification.objects.create` calls; remove 1 `UnreadMessage` creation |
| `cases/templates/cases/technician_dashboard.html` | Add left-side badge |
| `cases/templates/cases/admin_dashboard.html` | Add left-side badge |
| `cases/templates/cases/manager_dashboard.html` | Add left-side badge |

---

## What Does NOT Change

- `case_chat_message` path — untouched  
- `case_on_hold` — was already member-only; no staff notification existed  
- `member_document_uploaded` when case is on hold — existing behavior preserved  
- `CaseNotification` (member-facing) — entirely separate system, untouched  
- Cancellation `CaseMessage` + `UnreadMessage` for the cancellation system chat message — stays (chat-driven, Surface 1)  
- Yellow review banners — those are a separate template-level feature; not touched here  

---

## No Database Migration Required

Both left-side badges are derived from fields that already exist:
- `Case.has_profeds_error` — already on model, already set on new mod cases  
- `Case.original_case_id` — already on model, already set on all modification cases  

---

## Commit Plan (incremental)

| # | Commit message | Tasks |
|---|---|---|
| 1 | `Remove case_assigned StaffNotification — yellow banner not needed` | Task 1 |
| 2 | `Remove review-workflow StaffNotifications — review banners handle awareness` | Tasks 2, 3, 4 |
| 3 | `Gate member_document_uploaded alert to hold-status cases only` | Task 5 |
| 4 | `Remove member_change_request StaffNotification` | Task 6 |
| 5 | `Remove case_modification_error StaffNotifications and mod UnreadMessage` | Task 7 |
| 6 | `Add PF ERR and MOD left-side badges to staff dashboard case rows` | Task 8 |
