# ProFeds Error Metric - Option C Change Summary

## Problem statement
Right now, the ProFeds error metric can change after the fact.

If a case is flagged as a ProFeds error and later cleared, that case disappears from the current count. This means past totals can go down, even for periods already reviewed.

## Current behavior (today)
- Metric counts only cases currently marked as ProFeds error.
- If a flag is cleared later, past totals drop retroactively.

## Options

### Option A: Keep current behavior
What it means: Count only open/current ProFeds errors.

### Option B: Use stable historical count
What it means: Count cases that were ever flagged (even if later cleared).

### Option C: Show both numbers (recommended)
What it means:
- Reported Errors (historical, stable)
- Open Errors (current, live)

## Option C - changes involved

### 1. Report structure changes
- Add two visible metrics in the ProFeds error report:
  - Reported Errors (Historical)
  - Open Errors (Current)
- Optional but recommended: add a third companion metric:
  - Cleared/Disputed Errors

### 2. Definition changes
- Reported Errors (Historical): cases that were ever flagged as ProFeds error.
- Open Errors (Current): cases currently marked as ProFeds error and not cleared.
- Cleared/Disputed Errors (if shown): cases previously flagged and later cleared.

### 3. Data/query changes
- Keep current live flag logic for Open Errors.
- Add a historical source for Reported Errors (immutable history source).
- Keep clear/dispute workflow unchanged; only reporting logic changes.

### 4. UI/label changes
- Update report labels so users understand each number at a glance.
- Add short helper text describing the difference between Historical and Current.

### 5. Testing/validation changes
- Validate with known scenarios:
  - Case flagged and never cleared.
  - Case flagged then cleared.
  - Multiple flagged events over time.
- Confirm historical count does not decrease after clearance.
- Confirm open count does decrease after clearance.

### 6. Impact summary
- Better transparency for managers and evaluators.
- Preserves day-to-day operational view (open issues now).
- Prevents confusion from retroactive drops in historical totals.

## Decision requested
If approved, implement Option C as a metrics/reporting change only (no workflow change for end users).
