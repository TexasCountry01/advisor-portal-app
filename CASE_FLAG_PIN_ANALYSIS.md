# Tech Ability to Flag or Pin a Case — Analysis

## Problem Statement

When a Tech sees an alert on a case and opens it, the alert auto-clears on page load. If the advisor asked for something the Tech can't address immediately, there's no way to:
- Re-apply the alert
- Flag the case for follow-up
- Pin it to the top of their queue

This creates a risk of alerts going unaddressed if they're cleared before action is taken.

---

## How the Current Alert System Works

### Alert Creation
- Member/delegate sends a chat message → `UnreadMessage` row created for the assigned tech
- If unassigned, creates one for every active tech+admin
- A `StaffNotification` (bell icon) is also created alongside

### Alert Clearing (the root issue)
- **Automatic on page load** — when the assigned tech opens case_detail, JavaScript fires `markMessagesAsRead()` which deletes ALL staff UnreadMessage rows for that case globally
- No explicit dismiss action is required
- The tech has no opportunity to "keep" the alert before it's gone

### Existing Infrastructure
- No pin/bookmark/star/flag mechanism exists for cases
- The only per-case flags are system-set operational flags (has_member_updates, has_profeds_error, etc.)
- These are not user-toggleable

---

## Options

### Option 1 — Personal "Flag" / Pin (per-user bookmark)

Add a per-user flag model. Techs toggle a flag on any case from case detail. Flagged cases appear as a dashboard tile.

**Pros:** Simple, personal, doesn't change alert behavior
**Cons:** New model + migration; relies on tech remembering to flag

### Option 2 — "Snooze" / Re-alert

Add a "Remind Me Later" button that re-creates the UnreadMessage row after auto-clear, restoring the alert badge.

**Pros:** No new model; directly restores the alert
**Cons:** Confusing flow (auto-clear then manual re-create); band-aid fix

### Option 3 — Delay auto-clear (require explicit dismiss)

Don't auto-clear on page load. Add an explicit "Mark as Read" button the tech clicks after addressing the issue.

**Pros:** Prevents the problem at the source; tech stays in control
**Cons:** Behavioral change for all staff; may feel noisy if alerts persist

### Option 4 — Hybrid: Auto-clear + one-click "Flag for follow-up"

Keep current auto-clear but add a "Flag for Follow-up" button on case detail. Creates a personal bookmark with optional note. A "Flagged" tile on the dashboard shows flagged cases.

**Pros:** No disruption to current flow; one-click action; dashboard visibility
**Cons:** New model + migration; two systems (alerts + flags)

---

## Recommendation

Option 4 (Hybrid) — keeps existing behavior intact, gives techs an explicit "I need to come back" action, and surfaces flagged cases on the dashboard.

---

---

## Summary for Review

**Issue:** Alerts clear automatically when a tech opens a case — no way to mark it for follow-up.

**Options:**

| # | Approach | Summary | Effort |
|---|----------|---------|--------|
| 1 | Personal Flag/Pin | Toggle button on case → "Flagged" tile on dashboard | Medium |
| 2 | Snooze/Re-alert | "Remind Me" button re-creates the cleared alert | Low |
| 3 | Explicit Dismiss | Alerts don't auto-clear; tech clicks "Mark Read" when done | Medium |
| 4 | Hybrid (recommended) | Keep auto-clear + add "Flag for Follow-up" button + dashboard tile | Medium |

**Our recommendation: Option 4** — doesn't change how alerts work today, just adds a one-click follow-up flag with dashboard visibility.
