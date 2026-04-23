# Tech/Manager/Admin Fast Filter Analysis

Date: 2026-04-22

## Request Interpreted

The user request appears to be:

1. Make the dashboard count/status badges clickable.
2. When clicked, each badge acts as a fast filter for the queue list.
3. Keep behavior consistent across Technician, Manager, and Admin views.
4. Include quick person filters at top (All Cases, Tiffany, Monica, Ileana, Chris).

## Current State (What Exists Today)

1. Dashboards currently show quick stats and full filter forms, but the status tiles are not implemented as a unified fast-filter system across all 3 roles.
2. Manager/Admin already have technician dropdown filters, but no dedicated top-row quick person buttons.
3. Technician dashboard has view toggles (All Cases/My Cases), but not the same named-tech quick buttons.
4. "Scheduled" currently appears as a row-level status badge (completed + scheduled release), not as a top fast-filter tile.
5. Data needed for fast-filter tiles exists:
   - Due dates (today/tomorrow)
   - Scheduled release state
   - New Info / Our Error flags
   - Unread badge counts (chat/unread)

## Options Considered

### Option 1: Fast Temporary UI Patch

Add clickable tiles and person buttons directly in each template with per-view query logic.

Pros:
- Fastest delivery.
- Minimal backend refactor.

Cons:
- Logic duplicated in multiple files.
- High chance of behavior drift between dashboards over time.

### Option 2: Shared Fast-Filter Logic (Recommended)

Implement one shared backend helper for queue tile definitions and reuse it in Technician, Manager, and Admin dashboards.

Proposed shared definitions:

1. Submitted: status = submitted.
2. Pending: status != completed (includes submitted, accepted, hold, pending_review, etc.).
3. Scheduled: status = completed AND actual_release_date is null AND scheduled_release_date is not null.
4. Need Review: status = pending_review.
5. On Hold: status = hold.
6. Alerts: has_member_updates OR has_profeds_error OR unread indicators.
7. Due Today: date_due = today AND not completed.
8. Due Tomorrow: date_due = tomorrow AND not completed.

Pros:
- One source of truth.
- Consistent behavior for Tech/Manager/Admin.
- Lower maintenance risk as tiles evolve.

Cons:
- More implementation effort than Option 1.

### Option 3: Config-Driven Queue Definitions

Store tile definitions and quick buttons in admin-configurable settings/model.

Pros:
- Future-proof and highly flexible.

Cons:
- Highest effort and complexity right now.

## Recommendation

Proceed with Option 2.

Reason:
- It delivers the requested clickable fast-filter behavior now.
- It keeps all three dashboards aligned.
- It avoids template-by-template logic duplication that will likely create regressions later.

## Implementation Outline (Option 2)

1. Add shared queue filter helper (service or view-level helper) for tile definitions.
2. Add quick-filter query params (for both status tiles and person buttons).
3. Render clickable tile row in all 3 dashboards.
4. Wire active state styling for selected tile/button.
5. Keep existing advanced filter form in place (tile filters should compose with existing filters or clearly reset, based on final product decision).
6. Add light tests for tile definitions and filtering behavior.

## Clarification to Lock Before Build

Decide whether tile clicks should:

1. Replace existing filters, or
2. Layer on top of existing filters.

Default recommendation: Replace existing tile filter while preserving person filter, then allow advanced filters to layer after.

## MEMBER View Tie-In

The MEMBER request follows the same fast-filter pattern as staff dashboards, but with a role-specific tile set and definitions.

Requested MEMBER tiles:

1. Ready (14d)
2. Pending
3. On Hold
4. Alerts
5. Drafts

### How This Fits Option 2

Use the same shared quick-filter architecture, but load MEMBER-specific definitions rather than the Tech/Manager/Admin definition set.

This keeps:

1. A single implementation pattern for clickable tiles.
2. Role-specific queue semantics where needed.
3. Long-term consistency and lower maintenance risk.

### Proposed MEMBER Definitions

1. Ready (14d):
   - status = completed
   - actual_release_date is not null
   - actual_release_date >= (today - 14 days)
   - when active, default sort = -date_completed (or -actual_release_date)

2. Pending:
   - member-visible not-complete queue
   - include submitted, accepted, hold, pending_review, resubmitted (if present in member queue)
   - exclude completed, scheduled-for-release completed, and cancelled

3. On Hold:
   - status = hold

4. Alerts:
   - cases with unread alert indicator on the View button (red bubble)
   - implementation source: unread_message_count > 0 (including member lifecycle unread logic already computed)

5. Drafts:
   - status = draft

### Current Behavior vs Requested Behavior (Member)

1. Current member stats and filters exist, but tiles are not the dedicated clickable fast-filter set requested.
2. Current "Ready" stat counts released completed cases without a 14-day window.
3. Current status filtering exists via checkbox filters; requested behavior is tile-first quick filtering.

### Implementation Notes for Member

1. Keep existing advanced filter form below the tiles.
2. Add a tile query param (example: quick_filter=ready_14d|pending|hold|alerts|drafts).
3. Make tile click behavior replace only the quick_filter selection while preserving other intentional context (for example, active view mode for delegate/my cases).
4. Apply the same active-state styling pattern used by staff quick filters.

### Recommendation for MEMBER

Proceed with Option 2 for MEMBER as well, using a member-specific definition pack.

Reason:

1. Exact alignment with the mockup intent (clickable fast filters).
2. Reuses the same architecture as staff dashboards.
3. Avoids fragmented one-off logic between roles.
