# ProFeds Error Metrics - Codebase Confirmation and Options (2026-08-01)

## Purpose
This document confirms current ProFeds error behavior in code and provides implementation options for historical metrics integrity.

## Confirmed in Codebase

### 1. Current flag is mutable (current-state, not historical-state)
- Field: `Case.has_profeds_error` in `cases/models.py` (boolean).
- This field is set to `True` when a member/staff flags a modification as ProFeds error.
- This field can be later set back to `False` by staff.

### 2. Where the flag is set
- Member modification flow sets the flag and increments counter:
  - `cases/views.py` in `request_modification` flow
  - Sets `case.has_profeds_error = True`
  - Increments `case.error_modification_count += 1`
- Staff-created modification flow does the same:
  - `cases/views.py` in `create_modification_staff` flow
  - Sets `case.has_profeds_error = True`
  - Increments `case.error_modification_count += 1`

### 3. Where the flag is cleared
- `clear_profeds_error` in `cases/views.py`:
  - Requires technician/manager/admin role.
  - Requires a justification.
  - Sets `case.has_profeds_error = False`.
  - Also clears linked original/resubmitted case flags.
  - Writes an immutable audit event: `action_type='error_flag_disputed'`.

### 4. What current reporting uses
- ProFeds error report currently filters by live mutable flag:
  - `core/views_reports.py` in `profeds_error_tracking`
  - Query starts from `Case.objects.filter(has_profeds_error=True)`
- Result: once cleared, the case drops out of this report.

### 5. Existing historical-like field already present
- `Case.error_modification_count` exists in `cases/models.py`.
- It is incremented when error is flagged.
- It is not decremented on clear.
- This supports stable "ever flagged" style metrics if used as source.

## Impact Summary
- The current report is a "currently flagged" metric.
- It is not historically stable for evaluation snapshots.
- Clearing a disputed flag changes reported totals retroactively.
- Audit log preserves evidence, but report query does not currently use that historical evidence.

## Options

### Option 1 - Keep current behavior (current-state metric)
- Source: `has_profeds_error=True`
- Meaning: confirmed/open flags only.
- Pros: no code change.
- Cons: retroactive metric drift; weaker for performance evaluation consistency.

### Option 2 - Use audit events for historical metric
- Source: immutable events (flagged vs disputed/cleared).
- Meaning: "reported", "cleared", and optionally "net open".
- Pros: historically sound.
- Cons: medium query/report complexity.

### Option 3 - Use `error_modification_count` as metric source
- Source: `error_modification_count > 0` (or sum/count-based variants).
- Meaning: ever-flagged volume per case/tech/time window.
- Pros: smallest architecture change; stable over time.
- Cons: requires data audit and exact definition of aggregation.

### Option 4 - Dual-metric model (recommended for transparency)
- Report both:
  - Claimed/Reported errors (historical, immutable)
  - Current/Open errors (live mutable)
- Pros: avoids ambiguity and supports both operations + evaluation views.
- Cons: requires UI/report updates.

## Recommendation
Use a phased hybrid:
1. Short-term: implement Option 4 with two visible numbers in reports:
   - Reported (historical)
   - Open (current)
2. Backing source for Reported:
   - Prefer immutable event stream (Option 2), or `error_modification_count` after data validation (Option 3).
3. Keep `has_profeds_error` for operational workflow only (banner/state), not as sole evaluation metric source.

## Decision Points for Scope
- Should this change be metrics-only first (no workflow UI changes)?
- Should we include tech-level "disputed/cleared" rates in scorecards?
- Should disputed clearances require manager review for evaluation exports?

## Suggested Next Step
If approved, implement metrics-only first:
- Add "Reported", "Cleared", and "Open" columns/tiles to the ProFeds error report.
- Keep current case workflows unchanged.
- Add test validation against known flagged-and-cleared cases.
