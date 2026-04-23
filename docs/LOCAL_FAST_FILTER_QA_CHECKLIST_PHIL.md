# LOCAL Fast Filter QA Checklist (Phil)

Date: 2026-04-22
Scope: Validate local implementation of clickable fast-filter tiles and quick tech buttons for Admin, Manager, Technician, and Member dashboards.

## Pre-Check

1. Start local app and log in successfully.
2. Confirm you can access dashboards for required roles/accounts.

## Admin Dashboard QA

1. Open Admin Dashboard.
2. In the top quick tech button row, click each and confirm table updates:
   - All Cases
   - Tiffany
   - Monica
   - Ileana
   - Chris
3. Click each fast-filter tile and confirm the queue narrows correctly:
   - Submitted: status submitted only
   - Pending: not completed
   - Scheduled: completed with scheduled release date and not actually released
   - Need Review: pending_review only
   - On Hold: hold only
   - Alerts: rows with New Info, Our Error, or unread bubble
   - Due Today: due date today and not completed
   - Due Tomorrow: due date tomorrow and not completed
4. With a tile active, apply a secondary filter (search, status, date, member, or technician) and confirm expected combined result.
5. Click Reset and confirm quick filters and form filters are cleared.

## Manager Dashboard QA

1. Open Manager Dashboard.
2. Repeat quick tech button checks:
   - All Cases
   - Tiffany
   - Monica
   - Ileana
   - Chris
3. Repeat all 8 tile checks:
   - Submitted
   - Pending
   - Scheduled
   - Need Review
   - On Hold
   - Alerts
   - Due Today
   - Due Tomorrow
4. Confirm filter composition and Reset behavior.

## Technician Dashboard QA

1. Open Technician Dashboard.
2. Confirm view toggles still work:
   - All Cases
   - My Cases
3. Confirm quick tech buttons work:
   - All Cases
   - Tiffany
   - Monica
   - Ileana
   - Chris
4. Confirm all 8 tiles work:
   - Submitted
   - Pending
   - Scheduled
   - Need Review
   - On Hold
   - Alerts
   - Due Today
   - Due Tomorrow
5. Confirm tile + view toggle combinations behave correctly (for example, My Cases + On Hold).
6. Confirm Reset clears tile state and form filters.

## Member Dashboard QA

1. Open Member Dashboard.
2. Click each member tile and verify behavior:
   - Ready (14d): completed + released in last 14 days, newest completed first
   - Pending: excludes completed, cancelled, and drafts
   - On Hold: hold only
   - Alerts: cases with unread red bubble on View button
   - Drafts: draft only
3. Confirm advanced filters still work while a tile is active.
4. If the account has delegate views, verify tile filtering still works in:
   - My Cases
   - Delegate Cases
   - All Cases

## Regression Spot Checks

1. Open a case from filtered list and return to dashboard; verify filter state remains.
2. Confirm unread red bubbles still appear and update as expected.
3. Confirm no template/layout break on a narrow viewport.
4. Confirm no console/template errors during role switching and tile clicks.

## Sign-Off

Tester: Phil
Date tested: __________________
Result: Pass / Fail
Notes:

- 
- 
- 
