# Technician Performance Dashboard — Analysis

**Request:** A mini reporting dashboard displaying 5 key technician metrics with a "last 7 days" default and a date range filter.

**Scope:** Analysis only. No code changes. All 5 metrics evaluated against the existing data model and reporting infrastructure.

---

## Summary Table

| Metric | Data Exists? | Current Report | Gaps / Questions |
|--------|-------------|----------------|-----------------|
| Reports Generated | ✅ Yes | Technician Productivity | Definition needs clarification (see below) |
| Rushed Reports | ✅ Yes | Case Analytics | Currently counts all rush cases, needs completed-only filter |
| On-Time Delivery % | ✅ Yes | Due Date Compliance | Already exists — redirect or reuse |
| Report Accuracy % | ⚠️ Partial | ProFeds Error Tracking | Denominator definition needs clarification |
| Errors (ProFeds) | ✅ Yes | ProFeds Error Tracking | Date filter alignment needed |

---

## Metric-by-Metric Analysis

---

### 1. REPORTS GENERATED
> *Counting the # of reports the Techs "finish" or "submit for review"*

**What "finish" means in the system:**
- A technician clicks **"Release Case"** on the Pre-Completion Review page → `status = 'completed'`, `date_completed` is stamped.

**What "submit for review" means in the system:**
- For technicians subject to quality review, a case is submitted to a senior tech before release. This action is logged in `AuditLog` with `action_type = 'case_submitted_for_review'`.

**Data available:**
- `Case.date_completed` — timestamp when case was finalized and released
- `AuditLog` records for `case_submitted_for_review`
- Both are already queried in `get_technician_productivity_data()` in `core/views_reports.py`

**Key question for you to answer:**

> Should "Reports Generated" count both "finished" AND "submitted for review" as a combined number, or only fully released ("finished") cases?

If a technician submits for review and the manager approves/releases it, does that count as 1 report for the technician, or 2 events? The current technician productivity report tracks them separately.

**Date filter consideration:**
All existing report infrastructure filters by **`date_submitted`** (when the case came in from the member). For this dashboard, you almost certainly want to filter by **`date_completed`** — i.e., *work finished* in the last 7 days, not *cases received* in the last 7 days. This is a distinction that needs to carry through all 5 metrics.

---

### 2. RUSHED REPORTS
> *All rushed reports completed*

**Data available:**
- `Case.urgency` field — values: `'rush'` or `'normal'`
- `Case.status` — `'completed'` when done
- `Case.date_completed` — for date range filtering

**What exists now:**
The current analytics report tracks `rush_cases = cases_qs.filter(urgency='rush').count()`, but this counts **all rush cases regardless of status** (submitted, in-progress, completed). For this dashboard, you want only **completed** rush cases within the date window.

**No gaps** — this data is straightforward to isolate. The combination `urgency='rush'` + `status='completed'` + `date_completed` within range is fully supported.

**One edge case to be aware of:**
If a case was submitted as rush but the due date passed and the tech is still working on it, it would not appear in "completed" until released. This is correct behavior for a metric measuring *finished* rush work.

---

### 3. REPORT ON-TIME DELIVERY
> *# of reports delivered ÷ # of reports due = %*

**This metric already exists as a full standalone report.**

The **Due Date Compliance Report** (`/reports/due-date-compliance/`) calculates exactly this:
- Counts completed cases where `date_completed <= date_due` (on-time)
- Counts completed cases where `date_completed > date_due` (late)
- Expresses as a percentage
- Already has a date range filter
- Already broken down by technician

**For the dashboard:** This can be surfaced as a single percentage number pulled from `get_due_date_compliance_data()`.

**One definitional question:**
The formula says "# of reports due" as the denominator. Two interpretations:

| Denominator Option | Meaning |
|---|---|
| A | Cases with `date_due` falling within the date window (regardless of when completed) |
| B | Cases **completed** within the date window |

Option B (what the existing report uses) is more actionable for a team performance dashboard. Option A is more like a service-level commitment view. Recommend confirming which is intended.

---

### 4. REPORT ACCURACY
> *Error-free reports ÷ Total reports = %*

**Data available:**
- `Case.has_profeds_error` (Boolean) — set to `True` when a member flags a completed case as a ProFeds error during a modification request
- `Case.error_modification_count` — count of error-flagged modifications on that case

**What "Error-free" means in the system:**
A case is considered error-free when `has_profeds_error = False`. Currently the only way an error is recorded is when a **member self-reports it** by checking the "Is this an error on ProFeds' Part?" checkbox during a modification/resubmission request.

**Important caveats for this metric:**

1. **Self-reported only.** Errors are not auto-detected. If a member never submits a modification, no error is ever recorded — even if the report was wrong. This means the accuracy percentage will always trend high and may not reflect true accuracy.

2. **Timing gap.** The error flag is set when the member *requests a modification*, which may happen days or weeks after the report was delivered. A case completed in the last 7 days may not show an error until much later.

3. **The denominator "Total reports"** needs definition:
   - Option A: All completed cases in the date window (by `date_completed`)
   - Option B: All cases with `has_profeds_error` evaluated in the date window (by when the error was flagged — but this date is not currently stored separately)
   - Option C: Completed cases + any errors flagged on older cases during the window

   **Option A is the cleanest and most consistent** with the other metrics, but it will undercount errors on recently completed cases.

4. **Quality review relationship.** Cases that go through quality review and receive `'corrections_requested'` represent an *internal* accuracy signal (senior tech caught an error before the member ever saw it). This is tracked in `CaseReviewHistory` but is **not currently connected to the `has_profeds_error` flag**. Should internal corrections count as "errors" for this metric?

**Recommendation before building:** Confirm that this metric is intentionally based only on member-reported errors, and that the team understands its inherent lag.

---

### 5. ERRORS
> *All errors reported by Members as "ProFeds errors"*

**This metric already exists as a full standalone report.**

The **ProFeds Error Tracking Report** (`/reports/profeds-error-tracking/`) covers:
- Total error cases flagged
- Errors broken down by technician
- Error trends over time (weekly)
- Full detail table with case IDs, members, and technicians

**For the dashboard:** This becomes a single count number — cases flagged as `has_profeds_error = True` within the date window.

**Date filter alignment issue:**
The existing error tracking report filters by **`date_submitted`** (when the original case was submitted). For this dashboard, the more relevant filter would be by **when the error was flagged** (i.e., when the member submitted the modification request). That timestamp is not currently stored as its own field on the case — the modification case has a `date_submitted` that represents when the error mod was created, which is the closest proxy.

**Relationship to Metric 4:**
Metrics 4 and 5 draw from the same data source (`has_profeds_error`). They are complementary:
- Metric 4 = a rate (accuracy %)
- Metric 5 = a raw count (how many errors total)

---

## Date Range Consistency

All 5 metrics need to agree on **what date field drives the "last 7 days" window**. The recommended approach:

| Metric | Recommended Date Field |
|--------|----------------------|
| Reports Generated | `date_completed` |
| Rushed Reports | `date_completed` |
| On-Time Delivery % | `date_completed` (cases finished in window) |
| Report Accuracy % | `date_completed` (of the underlying completed case) |
| Errors | `date_submitted` of the modification case (closest to "when error was flagged") |

**Current state of existing reports:** Most existing reports filter by `date_submitted` of the primary case. A new dashboard would need `date_completed`-based filtering, which the existing infrastructure supports but does not currently default to.

---

## Technician Breakdown

The request does not explicitly ask for per-technician breakdowns on this dashboard, but the data supports it for all 5 metrics. The system has no hardcoded technician names — all queries use `assigned_to` foreign key lookups, so any technician hired in the future is automatically included.

If a per-technician view is desired later, a dropdown filter could be layered on top of the date range filter without redesigning the underlying queries.

---

## Questions to Resolve Before Building

1. **Reports Generated:** Does this count (a) only fully released cases, (b) only submitted-for-review events, or (c) both combined?

2. **On-Time Delivery %:** Is the denominator cases *due* in the window or cases *completed* in the window?

3. **Report Accuracy %:** Should internal quality review corrections count as errors, or only member-reported errors?

4. **Report Accuracy %:** Is the team comfortable with the inherent lag in this metric (errors may surface weeks after the report was delivered)?

5. **Errors count:** Should this count the number of **cases** with errors, or the number of **error events** (a case with 3 modification corrections counts as 1 case but 3 events)?

6. **Dashboard audience:** Is this for admin/manager only, or will technicians see their own stats in a self-service view?

---

## Existing Reports That Can Be Leveraged

| New Dashboard Metric | Existing Report to Reuse/Mirror |
|---|---|
| Reports Generated | Technician Productivity Report |
| Rushed Reports | Case Analytics Report |
| On-Time Delivery % | Due Date Compliance Report ✅ (fully built) |
| Report Accuracy % | ProFeds Error Tracking Report (partial reuse) |
| Errors | ProFeds Error Tracking Report ✅ (fully built) |

Two of the five metrics are effectively surfacing numbers that already exist in standalone reports. The dashboard would primarily be a consolidated view with a shared date range filter.
