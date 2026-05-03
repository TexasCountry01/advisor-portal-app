# Pending Bug Fixes
**Date:** May 3, 2026

---

## Bug 1: PF Error Mod Cases Flagged as RUSH (Member-Visible)

**Screenshot:** Blue Blue case — Urgency shows "Rush" badge on a modification case triggered by a ProFeds error.

**Root cause** — `cases/views.py` ~line 5033:
```python
if is_profeds_error:
    mod_due_date = date.today() + timedelta(days=3)
    mod_urgency = 'rush'   # ← shows Rush badge to member
```
When a mod is requested because of a ProFeds error, the system correctly sets a 3-day due date — but also sets `urgency='rush'`, which surfaces the Rush badge to the member. ProFeds is absorbing the cost of that turnaround, so the advisor should NOT be flagged as a rush customer.

**Options:**

| | Description | Effort |
|---|---|---|
| **A** ⭐ | Set `mod_urgency = 'normal'` for PF errors. Due date stays 3 days; no Rush badge shown. Staff still see the 3-day due date as the urgency signal. | 1-line change in `views.py` |
| **B** | Keep `urgency='rush'` internally for staff filtering, but suppress the Rush badge in member-facing templates when `case.has_profeds_error=True` | Several template spots |
| **C** | Add new urgency value `'profeds_rush'` — staff see rush, members see nothing. | Migration + template + view changes |

**Recommendation: Option A** — simplest. The `date_due` already communicates urgency to staff.

---

## Bug 2: Member Sees "Completed" in Timeline Before Case is Released

**Screenshot:** Brown Brown case — Member view shows "Completed" in the Timeline even though the case is scheduled for release but not yet released (`actual_release_date` is null).

**Root cause** — `case_detail.html` member Timeline (~line 1256) shows `case_completed` audit log events with no check on `actual_release_date`. When a tech completes a case and schedules it for future release, the `case_completed` log entry is written immediately — but the case hasn't been delivered to the member yet.

**Options:**

| | Description | Effort |
|---|---|---|
| **A** ⭐ | In the member Timeline, skip rendering `case_completed` events when `case.actual_release_date` is null. | 1-line template change |
| **B** | Show a softer label (e.g., "Processing Final Steps") when `actual_release_date` is null, then switch to "Completed" once released. | Template-only, slightly more work |
| **C** | Don't show `case_completed` in member timeline at all. Instead have the `release_scheduled_cases` cron job write a separate `case_released` audit log event that the member timeline shows. | Cron job + template change |

**Recommendation: Option A** — one template condition. Member sees nothing until the case is actually in their hands.

---

## Implementation Plan (when ready)

1. **Bug 1 — Option A:** `cases/views.py` line ~5038: change `mod_urgency = 'rush'` → `mod_urgency = 'normal'`
2. **Bug 2 — Option A:** `cases/templates/cases/case_detail.html` member Timeline loop: add `and case.actual_release_date` condition to the `case_completed` check
3. Deploy to TEST, verify both fixes
