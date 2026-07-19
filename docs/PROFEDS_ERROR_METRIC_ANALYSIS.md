# ProFeds Error Flag — Metric Integrity Analysis

**Date:** 2026-07-19  
**Question from user:** "How will the ProFeds Errors reporting work if someone says it's a ProFed error, but Tiffany clears it (because it was really the advisor's error)?"

---

## How the ProFeds Error Flag Currently Works

### When an error is reported
A member submits a modification request and checks "Is this a ProFeds error?" A mod case is created with `has_profeds_error = True` on both the mod case and the original case. The case immediately appears in the ProFeds Errors count.

### When a tech clears the flag
The `clear_profeds_error` function is available to **all three roles** — technician, manager, and administrator. When triggered:

1. `has_profeds_error` is set to `False` on the mod case, the original case, and any resubmitted cases
2. A **mandatory justification** is required before the clearance is accepted
3. The action is permanently recorded in the **AuditLog** under `action_type = 'error_flag_disputed'`, including who cleared it and the justification text

---

## What Happens to the Metrics When a Flag Is Cleared

When Tiffany clears the flag, **two metrics change retroactively and immediately**:

| Metric | Before clearance | After clearance |
|---|---|---|
| ProFeds Errors (dashboard tile + scorecard) | Case counted (flag = True) | Case disappears (flag = False) |
| Report Accuracy % (dashboard tile + scorecard) | Original case counted as "has error" | Original case becomes "error-free" — % improves |

**Example:** A week that showed **3 ProFeds Errors** drops to **2** after one clearance. Tiffany's Report Accuracy % rises at the same time. If the scorecard week has already been reviewed, the number the manager saw is no longer what the page shows.

---

## The Core Problem

The `has_profeds_error` field is **mutable** — it represents the *current* state of the flag ("is this believed to be a ProFeds error right now?"), not the *historical* state ("was a ProFeds error ever claimed?").

This creates two legitimate concerns for a formal evaluation tool:

### 1. Metric instability
A closed week's ProFeds Errors count can decrease retroactively any time a clearance happens — even weeks or months later. This compounds the data immutability issue described in `SCORECARD_LOCK_OPTIONS_USER.md`. Even a locked snapshot would be frozen at a moment in time before a later clearance, making the snapshot and the live count disagree.

### 2. Potential for influencing evaluation metrics
A technician can clear their own error flag. The clearance requires a justification and is logged, but the performance metric number decreases immediately. For a formal HR evaluation, a tech should not be able to directly change the numbers they are being evaluated on.

---

## An Unused Field Worth Noting

The `Case` model has a separate field: `error_modification_count`, described as:

> "Count of modification requests flagged as ProFeds errors — used for metrics"

This field **increments when an error is reported** but is **never decremented** when a flag is cleared. It appears to have been designed as a permanent immutable accumulator. However, it is **not currently used in any performance metric query** — all metrics read from `has_profeds_error` instead.

---

## Options

### Option 1 — Keep current behavior (mutable flag)
Cleared errors disappear from the count. The audit log captures all disputes with justification text. The metric reflects *confirmed* errors only (errors not yet disputed).

**Risk:** Numbers change retroactively. Techs can influence their own evaluation metrics. Does not meet the "numbers don't change" requirement.

---

### Option 2 — Count claimed errors, not confirmed errors
Change the ProFeds Errors metric to count all cases where an error was *ever* claimed, regardless of whether it was later cleared. Use the AuditLog's `error_flag_disputed` events to show a separate "disputed" count alongside the total.

**Result:** The count never decreases. The scorecard could show "3 claimed / 1 disputed" for full transparency. Techs cannot reduce their own count by clearing flags.

**Code change required:** Medium — metrics must query `error_flag_disputed` audit events or a new immutable field, rather than the live `has_profeds_error` flag.

---

### Option 3 — Activate `error_modification_count` as the metric source *(Recommended)*
Switch the ProFeds Errors metric to read from `error_modification_count` instead of `has_profeds_error`. This field already exists, is already incremented on every error report, and is never decremented.

**Result:**
- The count is permanently stable once set
- Tiffany clearing a flag does not change the metric — it stays as evidence of how many errors were reported
- Clearances are still fully logged and visible on the case detail page
- Satisfies the "numbers don't change" requirement from the Performance Scorecard

**Code change required:** Small — swap the filter in 4–5 metric queries from `has_profeds_error=True` to use `error_modification_count > 0` (or a variant). No model changes or migrations needed.

**Caveat:** `error_modification_count` must be verified to be correctly populated in all cases before switching. This needs a data audit against known cases.

---

### Option 4 — Split into two sub-metrics
Show both "Claimed" (all errors ever reported) and "Confirmed" (errors not cleared) as separate rows or tiles, giving the manager visibility into both the volume of claims and the outcome.

**Result:** Maximum transparency. Managers see whether clearances are common or rare.

**Code change required:** Medium-high — new metrics, new UI rows, new scorecard columns.

---

## Recommendation

**Option 3** (activate `error_modification_count`) best matches the evaluation use case:

| Criterion | Option 1 | Option 2 | Option 3 | Option 4 |
|---|---|---|---|---|
| Numbers don't change retroactively | ❌ | ✅ | ✅ | Partial |
| Tech cannot influence own metric | ❌ | ✅ | ✅ | ✅ |
| Field already exists | ✅ | ❌ | ✅ | ❌ |
| Small code change | ✅ | ❌ | ✅ | ❌ |
| Full audit trail preserved | ✅ | ✅ | ✅ | ✅ |

Option 3 requires a **data audit** to confirm `error_modification_count` is correctly populated before switching. That audit should be completed before any code change.

---

## Status

**Decision required from user.** No code changes have been made. The current live metrics use `has_profeds_error` (Option 1 behavior).

Related documents:
- `docs/SCORECARD_LOCK_OPTIONS_USER.md` — data locking strategy for the Performance Scorecard
- `docs/SCORECARD_IMMUTABILITY_TECHNICAL.md` — technical implementation of the lock approach
