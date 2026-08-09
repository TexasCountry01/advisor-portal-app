# Alert Rules Analysis — Chris's Decisions & Gap Assessment

Generated: 2026-08-09
Validated against codebase: 2026-08-09

---

## Chris's Core Rules (extracted from responses)

1. **All staff views show identical alert counts** — no per-user variation
2. **Alerts shown for ALL cases regardless of status** — terminal cases included
3. **Quick-tech filter narrows to that tech's owned cases with alerts** — clicking a tech name + alerts tile shows their cases
4. **Only the owning tech clears an alert** — visiting the case clears it for everyone
5. **Badge number = count of member/delegate actions** (chat messages, doc uploads, etc.) — NOT count of staff who haven't seen it

---

## How the Current System Actually Works (Code-Verified)

### Badge (red number on View button)

- Driven by `UnreadMessage` model rows in the database
- One member action (e.g., one chat message) creates **one UnreadMessage row per active staff user** (assigned tech, or all techs if unassigned)
- Badge count = `COUNT(UnreadMessage rows)` across ALL active staff for that case
- Result: 1 message can show badge "3" if 3 staff each have an unread row
- Badge is filtered to active statuses only: submitted, resubmitted, accepted, hold, pending_review, needs_resubmission
- Terminal statuses (completed, cancelled, declined) are **excluded** from badge counting

### Clearing (mark_messages_as_read)

- When ANY staff user opens a case detail page, the system deletes **only that user's** UnreadMessage rows for that case
- Other staff retain their own rows — badge decreases only by that user's portion
- There is NO ownership check — any staff member clearing affects only themselves
- Members and delegates also clear independently of each other

### Alerts Tile

- Counts active cases only — explicitly excludes completed, cancelled, declined, draft
- Includes cases where `has_member_updates=True` OR where any active staff user has UnreadMessage rows
- When a specific tech is selected via quick-tech button, scopes to that tech's assigned cases with alerts

### What Creates UnreadMessage Rows

| Trigger | Created For | Notes |
|---|---|---|
| Member posts chat message | Assigned tech (or ALL active techs if unassigned) | Primary alert source |
| Tech posts chat message | Case member | Member-facing alert |
| Modification request system message | Assigned tech on original case | System-generated |
| Case declined system message | Case member | System-generated |
| Case cancellation system message | Previously assigned tech | System-generated |

### What Creates has_member_updates Flag

- Member/delegate uploads a document to an active case
- Member/delegate posts chat on an active case
- Reset when the assigned tech views the case

### Notification Types (CaseNotification — member-facing only)

- case_put_on_hold
- case_resumed
- case_released
- documents_needed
- case_declined
- member_update_received

### Staff Notification Types (StaffNotification — staff-facing)

- case_modification_error
- case_assigned
- quality_review_feedback
- case_on_hold
- member_document_uploaded
- case_chat_message
- member_change_request
- review_requested
- review_action_taken
- system_alert

---

## Gap Analysis: Current vs Desired

| Area | Current Behavior (verified) | Chris's Desired Behavior | Gap Severity |
|---|---|---|---|
| Badge number meaning | COUNT of UnreadMessage rows across all active staff — one message can inflate to N (one per staff user) | Count of distinct member/delegate actions that triggered the alert | **Major** — fundamentally different semantics |
| Who can clear | Any staff visiting the case clears ONLY their own UnreadMessage rows — badge decreases per user independently | Only the assigned/owning tech visiting the case clears the alert for ALL staff | **Major** — requires rewrite of `mark_messages_as_read()` to check ownership and delete globally |
| Terminal case alerts | Excluded from badge counts AND alerts tile (completed, cancelled, declined filtered out) | Include ALL statuses — terminal cases with alerts should still show | **Medium** — requires removing `case__status__in=[...]` filter from 3 locations |
| Cross-view consistency | Different staff see different badge numbers for the same case (each has their own unread count) | All staff see the same number on the same case | **Major** — follows from badge = distinct actions, not per-user state |
| Alerts tile scope | Active cases only (excludes completed/cancelled/declined/draft) | All cases with alerts regardless of status | **Medium** — filter change in 2 functions |

---

## Answers to Chris's Inline Questions

### Q: Why would some views count additional update flags, but others don't?

Current code: technician/admin/manager views check `has_member_updates` flag in the alerts tile. Member view checks unread notifications instead. This was a design inconsistency, not intentional differentiation.

### Q: What are the types of notifications in the "notifications" list?

Member-facing (CaseNotification): case_put_on_hold, case_resumed, case_released, documents_needed, case_declined, member_update_received.

Staff-facing (StaffNotification): case_modification_error, case_assigned, quality_review_feedback, case_on_hold, member_document_uploaded, case_chat_message, member_change_request, review_requested, review_action_taken, system_alert.

### Q: Are notifications specific to the tech and cases they own?

StaffNotifications are targeted to specific staff users. UnreadMessage (chat alerts) rows are created for the assigned tech or, if unassigned, all active techs/admins.

### Q: What are "unread lifecycle notifications" for members?

CaseNotification records: case on hold, case resumed, case released/completed, case declined, documents needed.

### Q: Do members and delegates alerts operate independently?

Yes — currently independent. Each user has their own UnreadMessage rows. A delegate clearing does not clear the member's, and vice versa.

### Q: Does "aggregate" just mean we all see the same alerts?

No. "Aggregate" currently means the badge sums ALL staff UnreadMessage rows for that case. So if 3 staff each have 1 unread row, the badge shows 3 — not 1. Staff do NOT all see the same number; they see a team sum that differs after individuals clear their own rows.

### Q: System-generated chat messages that create unread?

- Modification requests (new mod case linked to original)
- Case declined messages (system posts to chat)
- Case cancellation messages (system posts to chat)

### Q: "Active cases can still show a badge higher than visible message count"?

This means: 1 new chat message from member → system creates 3 UnreadMessage rows (one per active staff user) → badge shows 3 even though there is only 1 message bubble in the chat. The badge counts recipients who haven't seen it, not distinct messages.

---

## Chris's Decision Summary (Option B + ownership-based clear)

Chris chose a hybrid closest to **Option B** with ownership-based clear semantics:

- Badge = count of distinct unread member/delegate actions on that case (not per-staff-user rows)
- Clear = owning tech visits case → clears for everyone
- Scope = all statuses (not just active)
- Consistency = all staff see the same number

---

## Implementation Changes Required

1. **Badge calculation** — rewrite from `COUNT(UnreadMessage rows for all staff)` to `COUNT(DISTINCT CaseMessage/action records that haven't been cleared by the owning tech)`. This likely requires either a new model field (e.g., `is_cleared` on CaseMessage) or a separate tracking table, because UnreadMessage rows are currently per-user.

2. **Clear mechanism** — rewrite `mark_messages_as_read()` to:
   - Check if current user is the assigned tech (owner)
   - If yes: delete ALL staff UnreadMessage rows for that case (global clear)
   - If no: do nothing (or optionally still mark as "seen" for personal UI, but badge stays)

3. **Terminal case inclusion** — remove `case__status__in=[...]` active-status filter from:
   - `_unread_map` in technician_dashboard (line ~870)
   - `_unread_map` in admin_dashboard (line ~1125)
   - `_unread_map` in manager_dashboard (line ~1350)
   - `get_unread_message_count` polling endpoint (line ~5650)

4. **Alerts tile** — remove `exclude(status__in=['completed','cancelled','declined','draft'])` from:
   - `_apply_staff_quick_filter('alerts')` (line ~158)
   - `_build_staff_quick_tiles()` alerts calculation (line ~250)

5. **Polling endpoint** — align `get_unread_message_count` with new badge semantics (distinct actions, not per-user rows)

---

## Risk Assessment

| Change | Complexity | Why |
|---|---|---|
| Terminal case inclusion | Medium | 3 filter sets + polling endpoint need matching updates |
| Global clear by owner | **High** | Requires architectural change to clear logic — must determine ownership at clear time, fetch all staff rows, delete globally. Edge cases: unassigned cases, reassigned cases |
| Badge semantics change | **High** | Current UnreadMessage model stores per-user state. New semantics need per-case/per-action state. May require schema change or query restructuring |
| Cross-view consistency | Automatic | Falls out naturally from the badge semantics + global clear changes |

### Affected Code Locations

- `cases/views.py` — `_apply_staff_quick_filter('alerts')` (~line 158)
- `cases/views.py` — `_build_staff_quick_tiles()` (~line 250)
- `cases/views.py` — technician_dashboard `_unread_map` (~line 870)
- `cases/views.py` — admin_dashboard `_unread_map` (~line 1125)
- `cases/views.py` — manager_dashboard `_unread_map` (~line 1350)
- `cases/views.py` — `mark_messages_as_read()` (~line 5562)
- `cases/views.py` — `get_unread_message_count()` (~line 5590)

### Recommendation

- Implement on TEST first
- Have Tiffany and Becky validate before PROD
- Consider phasing: terminal inclusion first (lower risk), then badge semantics + global clear (higher risk)
