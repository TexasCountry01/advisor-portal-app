# ProFeds Error Metric - Decision Brief (User-Facing)

## Why this decision matters
Right now, the ProFeds error metric can change after the fact.

If a case is flagged as a ProFeds error and later cleared, that case disappears from the current count. This means past totals can go down, even for periods already reviewed.

## Current behavior (today)
- Metric counts only cases currently marked as ProFeds error.
- If a flag is cleared later, past totals drop retroactively.
- Good for operations (what is still open now).
- Not ideal for performance evaluation (numbers are not stable over time).

## Decision options

### Option A: Keep current behavior
- What it means: Count only open/current ProFeds errors.
- Benefit: No changes needed.
- Risk: Historical totals can change later.

### Option B: Use stable historical count
- What it means: Count cases that were ever flagged (even if later cleared).
- Benefit: Totals do not go down later.
- Risk: A case can still count as "reported" even when later disputed.

### Option C: Show both numbers (recommended)
- What it means:
  - Reported Errors (historical, stable)
  - Open Errors (current, live)
- Benefit: Clear and fair. You can see both history and current workload.
- Risk: Slightly more report UI work.

## Recommendation
Choose Option C (dual metric):
- It gives the clearest picture.
- It avoids confusion about changing historical totals.
- It supports both management reporting and day-to-day operations.

## Suggested display labels
- Reported Errors (Historical)
- Cleared/Disputed Errors
- Open Errors (Current)

## Final decision to make
Pick one:
1. Keep a single live metric (current/open only)
2. Switch to a single historical metric (ever reported)
3. Show both historical and current metrics (recommended)

If you choose option 3, implementation can be done without changing the case workflow users already know.
