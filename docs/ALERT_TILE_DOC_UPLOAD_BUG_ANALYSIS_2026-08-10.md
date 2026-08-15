# Alert Tile — Doc Upload False Positive Bug Analysis

Date: 2026-08-10  
Reporter: Chris Kowalik (TEST server screenshot)  
Related commits: `3fac0fb`, `0bbef1d`

---

## Symptom

On the Technician Dashboard (TEST), cases with the "New Info" badge were incorrectly appearing in the **Active Alerts** tile even when the case was NOT on hold (e.g., status = Submitted, Unassigned).

Screenshot reference: Test3 Portal case (Submitted, Unassigned) appeared in the alerts tile with a New Info badge even though no actual alert should have fired.

---

## Root Cause — Two Independent Causes

### Cause 1: `has_member_updates=True` drives the alerts tile directly

Every document upload sets `has_member_updates = True` and `has_member_new_info = True` on the case regardless of case status (any non-draft case). The alerts tile query uses:

```python
alert_qs.filter(Q(has_member_updates=True) | _has_assigned_tech_unread)
```

This means `has_member_updates=True` alone is sufficient to pull a case into the alerts tile — even if there is no assigned tech and no `UnreadMessage` row. This is why the **unassigned submitted** Test3 case appeared in the tile.

### Cause 2: Commit `0bbef1d` created `CaseMessage` + `UnreadMessage` for ALL doc uploads, not gated to hold

Commit `0bbef1d` ("Doc uploads increment row badge") added `📎 system CaseMessage` + `UnreadMessage` creation in the three doc upload paths. However, this creation was NOT gated to hold-only — it ran for all non-draft statuses, including `submitted`, `accepted`, `pending_review`.

For cases WITH an assigned tech in a non-hold status:
- A `📎` CaseMessage was created
- An `UnreadMessage` row was created for the assigned tech
- These drove the alerts tile via `_has_assigned_tech_unread`

Commit `3fac0fb` had already gated `StaffNotification` to hold-only, but `0bbef1d` introduced a new alert signal (UnreadMessage) that bypassed that gate.

---

## Data Flow — Before Fix

| Scenario | `has_member_updates` | StaffNotification | CaseMessage + UnreadMessage | Alerts Tile |
|---|---|---|---|---|
| Doc upload on **hold** case (assigned) | ✅ Set | ✅ Created | ✅ Created | ✅ Correct — should alert |
| Doc upload on **submitted** case (assigned) | ✅ Set | ❌ Not created (3fac0fb gate) | ❌ Created (0bbef1d bug) | ❌ Wrong — in tile via UnreadMessage |
| Doc upload on **submitted** case (unassigned) | ✅ Set | ❌ Not created | ❌ Not created (no assigned_to) | ❌ Wrong — in tile via has_member_updates |
| Doc upload on **accepted** case (assigned) | ✅ Set | ❌ Not created | ❌ Created (0bbef1d bug) | ❌ Wrong — in tile via UnreadMessage |

---

## Options

### Option A — Full Fix (Recommended)
Two changes, two commits:

1. **Remove `Q(has_member_updates=True)` from alerts tile and quick filter.**  
   The alerts tile becomes driven purely by `UnreadMessage` rows — consistent with the row badge.  
   Affected: `_apply_staff_quick_filter()` and `_build_staff_quick_tiles()` in `cases/views.py`.

2. **Gate the `CaseMessage` + `UnreadMessage` creation from `0bbef1d` to hold-status only.**  
   Wrap the `📎 system message + UnreadMessage` block with `if case.status == 'hold':` in all three upload paths.

**Result:**
- Non-hold doc uploads → `has_member_new_info=True` (New Info badge on row) only. Zero alerts tile activity.
- Hold doc uploads → full alert chain: StaffNotification + CaseMessage + UnreadMessage → row badge + alerts tile.

### Option B — Partial Fix (`0bbef1d` gating only)
Gate `CaseMessage` + `UnreadMessage` to hold-only. Eliminates alerts for **assigned** non-hold cases. However, `has_member_updates=True` still drives the alerts tile — unassigned submitted/accepted cases STILL incorrectly appear.

### Option C — Partial Fix (alerts tile only)
Remove `has_member_updates` from the tile only. `0bbef1d` still creates `UnreadMessage` for assigned non-hold uploads → those cases still appear in tile via `_has_assigned_tech_unread`. Does not fully resolve the assigned non-hold scenario.

---

## Decision

**Option A selected** — both changes implemented together.

---

## Implementation Plan

| Commit | Change |
|---|---|
| 1 | Remove `has_member_updates` from alerts tile filter and quick filter in `cases/views.py` |
| 2 | Gate `CaseMessage` + `UnreadMessage` in doc upload paths to `case.status == 'hold'` only |

Deploy: TEST only until PROD approval.
