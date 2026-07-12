# Performance Dashboard — Analysis & Implementation Plan

**Request:** A mini reporting dashboard showing 7 team performance metrics, visible to all Techs, Managers, and Admins. Start on Admin dashboard for testing; expand to all dashboards.

**Expanded (2026-07-12):** Dashboard now includes 11 total metrics (original 7 + 4 new) plus an Advisor Submission Breakdown table. All integrated into the single Team Performance Dashboard page.

---

## Metric-by-Metric Analysis

---

### 1. REPORTS GENERATED
> *# of reports Techs "finish" — release now or schedule for later*

**Definition in the system:**
A report is "finished" when the tech clicks **Release Case** on the Pre-Completion Review page. This stamps `date_completed` and sets `status = 'completed'`, regardless of whether the release is immediate or scheduled.

**Data available:** `Case.date_completed` + `assigned_to`
**Filter field:** `date_completed` (when the tech finished, not when the member submitted)
**Per tech:** filter by `assigned_to`
**Partially exists in:** Technician Productivity Report — but filtered by `date_submitted`, not `date_completed`. New query needed with correct date field.

---

### 2. REPORTS SUBMITTED FOR REVIEW
> *# of reports any Tech "submits for review" by a Senior Tech*

**Definition in the system:**
When a Level 1 tech clicks **Submit for Review**, a `CaseReviewHistory` record is created with `review_action = 'submitted_for_review'`. The timestamp is `reviewed_at`.

**Data available:** `CaseReviewHistory` model — `review_action`, `reviewed_at`, `original_technician`
**Filter field:** `reviewed_at`
**Per tech:** filter by `original_technician` (the tech whose work was submitted)
**Partially exists in:** Technician Productivity Report — already queries this. Can be reused directly.

**Note:** A single case can generate multiple review submissions (e.g., revisions requested → resubmitted → approved). The count reflects submission *events*, not unique cases.

---

### 3. REPORT ON-TIME DELIVERY
> *# of reports delivered ÷ # of reports due = %*

**Definition in the system:**
- "Delivered" = `date_completed <= date_due`
- "Due" = completed cases whose `date_due` falls in the selected window

**Data available:** `Case.date_completed`, `Case.date_due`
**Already exists as:** Due Date Compliance Report — full implementation with date range filter and per-tech breakdown
**Action needed:** Pull the single top-level percentage into the dashboard panel. No new query required.

---

### 4. ERRORS
> *All errors reported by Members as "ProFeds errors" — generates a mod case*

**Definition in the system:**
When a member submits a modification request and checks "Is this a ProFeds error?", a new child case is created with `has_profeds_error = True` linked to the original via `original_case` FK.

**Data available:** `Case.has_profeds_error`, `Case.original_case`, `Case.assigned_to`
**Already exists as:** ProFeds Error Tracking Report — full implementation
**Action needed:** Pull the total error count into the dashboard panel. No new query required.

**Filter consideration:** The error flag is on the *modification case*, which has its own `date_submitted`. The dashboard should filter by the mod case's `date_submitted` (when the error was reported), not the original case's date.

---

### 5. PRODUCTION CYCLE TIME
> *# of days from when we receive the Member's request to when the Tech "finishes"*

**Definition in the system:**
- Start: `Case.date_submitted` (when member submitted the case)
- End: `Case.date_completed` (when tech released it)
- Metric: average of `(date_completed - date_submitted).days` across completed cases

**Data available:** Both fields exist on the `Case` model.
**Partially exists in:** Case Analytics Report — `avg_processing_time` is calculated globally across all cases. Not broken down per tech, not filterable by `date_completed`.
**Action needed:** New per-tech query filtering by `date_completed` within the date window.

**Display options:**
- Team average (single number) + per-tech average (breakdown table)
- Trend over time (optional enhancement)

---

### 6. READINESS WINDOW
> *# of days IN ADVANCE of due date that the Tech "finished" the case*

**Definition in the system:**
- `(Case.date_due - Case.date_completed).days` — positive = finished early, negative = finished late
- Average of this value across completed cases

**Data available:** Both fields exist on the `Case` model.
**Partially exists in:** Due Date Compliance Report — `avg_days_early` is already calculated there, with per-tech breakdown available in `tech_stats`.
**Action needed:** Extract this value from the existing compliance data function. Minimal new work.

**Related to On-Time Delivery %:** Delivery % tells you *if* cases are on time; Readiness Window tells you *how far* in advance. Both are useful together.

---

### 7. REPORT ACCURACY
> *Percentage of new requests that are NOT due to a ProFeds error*

**Definition clarification required — two possible interpretations:**

| Interpretation | Formula | What it measures |
|---|---|---|
| **A — Mod-based** | (Mod cases where `has_profeds_error=False`) ÷ (all mod cases) | % of modifications that were member-driven, not our fault |
| **B — All cases** | (Completed cases where `has_profeds_error=False`) ÷ (all completed cases) | % of all completed work that had no error flag |

**Recommendation:** Interpretation A is more precise and actionable — it directly answers "what fraction of modification requests are due to our mistakes?"

**Data available:** `Case.has_profeds_error`, `Case.original_case` (non-null = mod case)
**Existing report:** ProFeds Error Tracking covers raw counts; accuracy % is not currently calculated.
**Action needed:** New calculation — small addition.

**Caveat (unchanged from prior analysis):** Error flags are member self-reported. A case completed last week may not receive an error flag for days or weeks. Accuracy % will always trend high and may undercount recent errors.

---

## Data Availability Summary

| Metric | Data in DB? | Existing Report | New Work Required |
|---|---|---|---|
| Reports Generated | ✅ | Partial | New date-filtered query (`date_completed`) |
| Submitted for Review | ✅ | Partial | Reuse Technician Productivity query |
| On-Time Delivery % | ✅ | ✅ Full | Extract top-level % from existing function |
| Errors | ✅ | ✅ Full | Extract count from existing function |
| Production Cycle Time | ✅ | Partial (global avg only) | New per-tech avg query |
| Readiness Window | ✅ | Partial (in compliance report) | Extract `avg_days_early` from existing function |
| Report Accuracy | ✅ | None | New calculation (~10 lines) |

---

## Implementation Options

---

### Option 1 — Dedicated Standalone Page *(Most Flexible)*
Build a new "Team Performance Dashboard" page at `/reports/performance/`.

- All 7 metrics in one view
- Shared date range filter (default: last 30 days)
- When a **Tech** visits → sees only their own numbers
- When an **Admin/Manager** visits → sees team totals + per-tech breakdown table
- Linked from the existing Reports & Analytics menu
- Can be linked from individual dashboards later

**Pros:** Clean, purpose-built, easy to share as a link
**Cons:** Requires navigating away from the dashboard to see it

---

### Option 2 — Collapsible Panel on Each Dashboard *(Embedded)*
Build a reusable Django template include and embed it in all three dashboards.

- Same panel renders differently based on the viewer's role
- Tech sees own numbers; admin/manager sees team view
- Collapsible so it doesn't dominate the dashboard

**Pros:** Always visible on the dashboard without navigating
**Cons:** Slightly more complex — three dashboards to update

---

### Option 3 — Start on Admin Dashboard, Expand Later *(Recommended — Matches User's Request)*
Build Option 1 first as a standalone page AND add a summary panel to the Admin dashboard immediately.

- Phase 1: Standalone page + embed summary panel on Admin dashboard
- Phase 2 (after validation): Add panel to Manager and Technician dashboards with one template include line each

**Implementation structure:**
1. New function `get_performance_metrics(date_from, date_to, tech_id=None)` in `core/views_reports.py`
2. New view `performance_dashboard` with date range + optional tech filter
3. New template `templates/core/performance_dashboard.html` (standalone page)
4. New partial template `templates/core/performance_metrics_panel.html` (embeddable)
5. Include panel in `admin_dashboard.html` for Phase 1 testing

**Pros:** Low risk — test on admin dashboard, validate numbers, then roll out
**Cons:** Two-phase rollout requires a second deployment

---

## Confirmed Decisions

1. **Report Accuracy** — All-completed-cases: `(completed cases where has_profeds_error=False) ÷ (all completed cases)`

2. **Date window** — All 7 metrics share the same date window. Primary filter field: `date_completed` for case-based metrics; mod case `date_submitted` for Errors.

3. **Admin/Manager view** — Shows both: (a) team totals and (b) per-tech breakdown table below.

4. **Submitted for Review counting** — Count events. Three review submissions on one case = 3.

5. **Default date range** — Last 7 days, user-configurable.

---

## Demo Build — Pre-Implementation Prototype

**Decision (2026-07-11):** Before executing the full 7-step plan, build a demo-only version to present to the end user for concept validation. The purpose is to spark feedback and confirm intent *before* committing to full infrastructure work.

**What the demo includes:**
- Real data, real queries — no hardcoded or fake numbers
- All 7 metrics displayed on a single admin-only page
- Date range filter (default: last 7 days)
- Styled to look finished (tiles, labels, clear layout)
- Link accessible from the Reports & Analytics menu

**What the demo deliberately omits:**
- Per-tech breakdown table (Step 3)
- Reusable panel / dashboard embeds (Steps 4–6)
- AJAX async loading
- Role-based filtering (tech sees only their own numbers)
- Manager/Tech access to the standalone page

**Scope:** Steps 1 + 2 of the incremental plan only.

**Status (2026-07-11): ✅ COMPLETE — deployed to PROD at https://reports.profeds.com**
- Feature branch `feature/performance-dashboard-demo` merged into `main`
- URL: `/reports/performance/` — admin-only
- Accessible from Reports & Analytics menu

**After the demo:** User reviews and confirms, modifies, or rejects the metric definitions. Full plan resumes only after sign-off.

---

## Incremental Implementation Plan

Each step ends with a defined validation checkpoint before moving to the next step. No step should be skipped.

---

### ✅ Step 1 — Write & Validate the Backend Data Function *(COMPLETE)*
**Files:** `core/views_reports.py`
**What:** `get_performance_metrics(date_from, date_to)` function written and verified. All 7 queries run against real production data.

**Metrics and their queries:**

| Metric | Query | Filter |
|---|---|---|
| Reports Generated | `Case.filter(status='completed', date_completed__range=...)` | `date_completed` |
| Submitted for Review | `CaseReviewHistory.filter(review_action='submitted_for_review', reviewed_at__range=...)` | `reviewed_at` |
| On-Time Delivery % | Reuse `get_due_date_compliance_data()` | `date_completed` |
| Errors | `Case.filter(has_profeds_error=True, date_submitted__range=...)` | mod case `date_submitted` |
| Production Cycle Time | `Avg(date_completed - date_submitted)` on completed cases | `date_completed` |
| Readiness Window | `Avg(date_due - date_completed)` on completed cases | `date_completed` |
| Report Accuracy | `filter(status='completed', has_profeds_error=False).count() / filter(status='completed').count()` | `date_completed` |

When `tech_id` is provided, all queries additionally filter by `assigned_to=tech_id` (except Errors, which filters by the mod case's `assigned_to`).

**Validation checkpoint:**
- Call the function from the Django shell with a known date range
- Cross-check Reports Generated count against the existing Case list filtered manually
- Cross-check On-Time Delivery % against the Due Date Compliance Report for the same period
- Cross-check Errors count against the ProFeds Error Tracking Report
- Confirm Production Cycle Time is reasonable (should be near the existing `avg_processing_time` in Case Analytics)
- ✅ All 7 numbers make sense before any UI is built

---

### ✅ Step 2 — Build the Standalone Admin-Only Page *(COMPLETE)*
**Files:** `core/views_reports.py` (view), `core/urls.py`, `templates/core/performance_dashboard.html`
**What:** Page built at `/reports/performance/`. All 7 metrics, date range filter, color-coded tiles, metric definitions footer. Deployed to PROD 2026-07-11.

**Page layout:**
- Date range filter bar at top
- 7 metric tiles in a row (similar to existing report pages)
- No charts, no breakdown table yet

**Validation checkpoint:**
- Load the page with no date filter — numbers should match Step 1 shell output for the same default range
- Change date range — numbers should update correctly
- Confirm page is accessible to admins and returns 403 for other roles
- ✅ All 7 numbers display correctly and update with date filter

---

### ✅ Step 3 — Add Per-Tech Breakdown Table + Expand with 4 New Metrics *(COMPLETE)*
**Files:** `templates/core/performance_dashboard.html`, `core/views_reports.py`
**What (original):** `get_performance_metrics()` extended with `tech_user` parameter. View loops over all active techs. Breakdown table added below team tiles. Deployed to PROD 2026-07-11.

**Expansion (2026-07-12):** Three additional data helper functions added. Dashboard expanded with:
- 4 new team-total tiles: Advisor Submissions, L1/L2 Review Accuracy %, Returned to Tech, Corrected by L3
- 3 new columns in per-tech table: Review Accuracy %, Returned to Tech, Corrected by L3
- New Advisor Submission Breakdown section at bottom (per-advisor table)
- Standalone reports for the 3 new metrics removed from Reports menu — all data now lives in the dashboard

**New data helpers added:**
- `_get_review_accuracy_by_tech(date_from_obj, date_to_obj)` — first-pass approval rate per tech from `CaseReviewHistory`
- `_get_returns_corrections_by_tech(date_from_obj, date_to_obj)` — revisions requested vs corrections made by L3
- `_get_advisor_submissions(date_from_obj, date_to_obj)` — cases submitted per advisor from `Case`

**New metric definitions:**
- **Advisor Submissions** — all non-draft cases submitted by advisors filtered by `date_submitted`
- **L1/L2 Review Accuracy %** — `approved` outcomes ÷ all outcomes (approved + revisions_requested + corrections_needed) from `CaseReviewHistory` where `original_technician.user_level` in L1/L2
- **Returned to Tech** — count of `revisions_requested` outcomes
- **Corrected by L3** — count of `corrections_needed` outcomes (L3 fixed it without returning)

**Deployed to TEST:** 2026-07-12. PROD pending.

---

### Step 4 — Create the Reusable Panel Include
**Files:** `templates/core/performance_metrics_panel.html` (new), `cases/templates/cases/admin_dashboard.html`
**What:** Extract the 7 tiles (team totals only, no breakdown table) into a standalone includeable template. Embed it on the Admin dashboard.

**Panel behavior:**
- Compact version: 7 tiles with last-7-days numbers by default
- Link to the full page (Step 2) for the breakdown and date filter
- Loads data via an AJAX endpoint so it doesn't slow dashboard page load

**Validation checkpoint:**
- Admin dashboard loads at normal speed (panel data loads async)
- Numbers in the panel match the standalone page for the same default date range
- Panel link navigates to the full performance dashboard page
- ✅ Panel works on admin dashboard without breaking existing functionality

---

### Step 5 — Add Panel to Manager Dashboard
**Files:** `cases/templates/cases/manager_dashboard.html`
**What:** One template include line. Manager sees same team-total panel. Link goes to same standalone page.

**Validation checkpoint:**
- Panel renders identically on manager dashboard as on admin dashboard
- Manager can reach the full standalone page
- ✅ No regressions on manager dashboard

---

### Step 6 — Add Panel to Technician Dashboard (Tech-Filtered)
**Files:** `cases/templates/cases/technician_dashboard.html`, AJAX endpoint
**What:** Same panel include, but when a technician views it, the AJAX endpoint receives their user ID and returns only their own metrics — not team totals.

**Logic:**
- AJAX endpoint checks `request.user.role`
- If `technician` → filter all queries by `assigned_to=request.user`
- If `manager` or `administrator` → return team totals

**Validation checkpoint:**
- Log in as a tech — panel shows only their own numbers
- Log in as admin — panel shows team totals
- Cross-check tech's panel numbers against the per-tech breakdown row on the standalone page
- ✅ Role-based data separation works correctly

---

### Step 7 — Open to Manager and Tech on Standalone Page
**Files:** `core/views_reports.py` (access control), `templates/core/performance_dashboard.html`
**What:** Expand access to the full standalone page so Managers and Techs can visit it directly.

- **Manager view:** Same as Admin — team totals + per-tech breakdown
- **Tech view:** Team totals + per-tech breakdown, but their own row is highlighted

**Validation checkpoint:**
- Tech can load the page and sees full team view (with their row highlighted)
- Manager sees full team view
- No 403 errors for either role
- ✅ All roles have appropriate access

---

## Step Dependency Map

```
Step 1 (backend function)
  └── Step 2 (standalone page)
        ├── Step 3 (per-tech table on standalone page)
        └── Step 4 (panel on admin dashboard)
              ├── Step 5 (panel on manager dashboard)
              └── Step 6 (panel on tech dashboard — role-filtered)
                    └── Step 7 (open standalone page to all roles)
```

Steps 3 and 4 are independent of each other and can be done in either order after Step 2.

---

## SQL Reference

All queries run against the production MySQL database. Replace `'DATE_FROM'` and `'DATE_TO'` with ISO dates (`YYYY-MM-DD`).

**Key tables:**
- `cases_case` — all cases
- `cases_casereviewhistory` — quality review events (submitted for review, approved, etc.)

---

### 1. Reports Generated
```sql
SELECT COUNT(*) AS reports_generated
FROM cases_case
WHERE status = 'completed'
  AND DATE(date_completed) >= 'DATE_FROM'
  AND DATE(date_completed) <= 'DATE_TO';
```

---

### 2. Submitted for Review
```sql
SELECT COUNT(*) AS submitted_for_review
FROM cases_casereviewhistory
WHERE review_action = 'submitted_for_review'
  AND DATE(reviewed_at) >= 'DATE_FROM'
  AND DATE(reviewed_at) <= 'DATE_TO';
```

---

### 3. On-Time Delivery %
```sql
SELECT
  COUNT(*)                                                                AS total_with_due_date,
  SUM(CASE WHEN DATE(date_completed) <= date_due THEN 1 ELSE 0 END)      AS on_time_count,
  ROUND(
    SUM(CASE WHEN DATE(date_completed) <= date_due THEN 1 ELSE 0 END)
    * 100.0 / COUNT(*),
  1)                                                                      AS on_time_pct
FROM cases_case
WHERE status = 'completed'
  AND date_due       IS NOT NULL
  AND date_completed IS NOT NULL
  AND DATE(date_completed) BETWEEN 'DATE_FROM' AND 'DATE_TO';
```

---

### 4. ProFeds Errors
```sql
-- Counts modification cases where the member flagged it as a ProFeds error.
-- Filtered by when the error mod was submitted, not the original case.
SELECT COUNT(*) AS errors_count
FROM cases_case
WHERE has_profeds_error = 1
  AND original_case_id  IS NOT NULL
  AND DATE(date_submitted) >= 'DATE_FROM'
  AND DATE(date_submitted) <= 'DATE_TO';
```

---

### 5. Avg Production Cycle Time
```sql
-- Days from member submission to tech release, averaged across completed cases.
SELECT ROUND(
  AVG(TIMESTAMPDIFF(DAY, date_submitted, date_completed)),
1) AS avg_cycle_days
FROM cases_case
WHERE status          = 'completed'
  AND date_submitted  IS NOT NULL
  AND date_completed  IS NOT NULL
  AND DATE(date_completed) BETWEEN 'DATE_FROM' AND 'DATE_TO';
```

---

### 6. Avg Readiness Window
```sql
-- Positive = finished early; negative = finished late.
SELECT ROUND(
  AVG(DATEDIFF(date_due, DATE(date_completed))),
1) AS avg_readiness_days
FROM cases_case
WHERE status          = 'completed'
  AND date_due        IS NOT NULL
  AND date_completed  IS NOT NULL
  AND DATE(date_completed) BETWEEN 'DATE_FROM' AND 'DATE_TO';
```

---

### 7. Report Accuracy %
```sql
SELECT
  COUNT(*)                                                              AS total_completed,
  SUM(CASE WHEN has_profeds_error = 0 THEN 1 ELSE 0 END)              AS error_free,
  ROUND(
    SUM(CASE WHEN has_profeds_error = 0 THEN 1 ELSE 0 END)
    * 100.0 / NULLIF(COUNT(*), 0),
  1)                                                                    AS accuracy_pct
FROM cases_case
WHERE status = 'completed'
  AND DATE(date_completed) BETWEEN 'DATE_FROM' AND 'DATE_TO';
```

---

### All 7 Metrics — Single Combined Query
```sql
SELECT
  -- 1. Reports Generated
  COUNT(*)                                                                        AS reports_generated,

  -- 3. On-Time Delivery
  SUM(CASE WHEN date_due IS NOT NULL
            AND DATE(date_completed) <= date_due THEN 1 ELSE 0 END)              AS on_time_count,
  COUNT(CASE WHEN date_due IS NOT NULL THEN 1 END)                               AS on_time_total,
  ROUND(
    SUM(CASE WHEN date_due IS NOT NULL
              AND DATE(date_completed) <= date_due THEN 1 ELSE 0 END)
    * 100.0 / NULLIF(COUNT(CASE WHEN date_due IS NOT NULL THEN 1 END), 0),
  1)                                                                              AS on_time_pct,

  -- 5. Production Cycle Time
  ROUND(AVG(TIMESTAMPDIFF(DAY, date_submitted, date_completed)), 1)              AS avg_cycle_days,

  -- 6. Readiness Window
  ROUND(AVG(DATEDIFF(date_due, DATE(date_completed))), 1)                        AS avg_readiness_days,

  -- 7. Report Accuracy
  SUM(CASE WHEN has_profeds_error = 0 THEN 1 ELSE 0 END)                        AS error_free,
  ROUND(
    SUM(CASE WHEN has_profeds_error = 0 THEN 1 ELSE 0 END)
    * 100.0 / NULLIF(COUNT(*), 0),
  1)                                                                              AS accuracy_pct

FROM cases_case
WHERE status          = 'completed'
  AND date_submitted  IS NOT NULL
  AND date_completed  IS NOT NULL
  AND DATE(date_completed) BETWEEN 'DATE_FROM' AND 'DATE_TO';

-- Metrics 2 and 4 require separate queries (different source tables):

-- 2. Submitted for Review
SELECT COUNT(*) AS submitted_for_review
FROM cases_casereviewhistory
WHERE review_action = 'submitted_for_review'
  AND DATE(reviewed_at) BETWEEN 'DATE_FROM' AND 'DATE_TO';

-- 4. ProFeds Errors
SELECT COUNT(*) AS errors_count
FROM cases_case
WHERE has_profeds_error = 1
  AND original_case_id IS NOT NULL
  AND DATE(date_submitted) BETWEEN 'DATE_FROM' AND 'DATE_TO';
```

---

### 8. Advisor Submissions
```sql
-- All non-draft cases submitted by advisors in the window.
-- Filter: date_submitted (when member submitted, not when tech finished).
SELECT
  u.first_name, u.last_name, c.workshop_code,
  COUNT(*)                                                              AS total_submitted,
  SUM(CASE WHEN c.status = 'completed' THEN 1 ELSE 0 END)             AS completed,
  SUM(CASE WHEN c.status IN ('accepted','pending_review','hold') THEN 1 ELSE 0 END) AS in_progress,
  SUM(CASE WHEN c.status IN ('submitted','resubmitted') THEN 1 ELSE 0 END)          AS pending_accept,
  SUM(CASE WHEN c.has_profeds_error = 1 THEN 1 ELSE 0 END)            AS pf_errors
FROM cases_case c
JOIN accounts_user u ON u.id = c.member_id
WHERE c.status != 'draft'
  AND c.member_id IS NOT NULL
  AND u.is_test_account = 0
  AND DATE(c.date_submitted) BETWEEN 'DATE_FROM' AND 'DATE_TO'
GROUP BY u.id, u.first_name, u.last_name, c.workshop_code
ORDER BY total_submitted DESC;
```

---

### 9. L1/L2 Review Accuracy %
```sql
-- First-pass approval rate: approved outcomes ÷ all outcomes for L1/L2 techs.
-- Outcome actions: 'approved', 'revisions_requested', 'corrections_needed'
SELECT
  u.first_name, u.last_name, u.user_level,
  COUNT(*)                                                                   AS total_reviews,
  SUM(CASE WHEN rh.review_action = 'approved' THEN 1 ELSE 0 END)           AS approved,
  SUM(CASE WHEN rh.review_action = 'revisions_requested' THEN 1 ELSE 0 END) AS revisions,
  SUM(CASE WHEN rh.review_action = 'corrections_needed' THEN 1 ELSE 0 END)  AS corrected_by_l3,
  ROUND(
    SUM(CASE WHEN rh.review_action = 'approved' THEN 1 ELSE 0 END)
    * 100.0 / NULLIF(COUNT(*), 0),
  1) AS accuracy_pct
FROM cases_casereviewhistory rh
JOIN accounts_user u ON u.id = rh.original_technician_id
WHERE rh.review_action IN ('approved', 'revisions_requested', 'corrections_needed')
  AND u.user_level IN ('level_1', 'level_2')
  AND u.is_test_account = 0
  AND DATE(rh.reviewed_at) BETWEEN 'DATE_FROM' AND 'DATE_TO'
GROUP BY u.id, u.first_name, u.last_name, u.user_level
ORDER BY u.first_name;

-- Team total:
SELECT
  COUNT(*)                                                                   AS total_reviews,
  ROUND(SUM(CASE WHEN review_action = 'approved' THEN 1 ELSE 0 END) * 100.0 / NULLIF(COUNT(*), 0), 1) AS team_accuracy_pct
FROM cases_casereviewhistory rh
JOIN accounts_user u ON u.id = rh.original_technician_id
WHERE rh.review_action IN ('approved', 'revisions_requested', 'corrections_needed')
  AND u.user_level IN ('level_1', 'level_2')
  AND u.is_test_account = 0
  AND DATE(rh.reviewed_at) BETWEEN 'DATE_FROM' AND 'DATE_TO';
```

---

### 10. Returned to Tech & 11. Corrected by L3
```sql
-- Returned to Tech  = review_action = 'revisions_requested'
-- Corrected by L3   = review_action = 'corrections_needed'
SELECT
  u.first_name, u.last_name,
  SUM(CASE WHEN rh.review_action = 'revisions_requested' THEN 1 ELSE 0 END) AS returned_to_tech,
  SUM(CASE WHEN rh.review_action = 'corrections_needed'  THEN 1 ELSE 0 END) AS corrected_by_l3
FROM cases_casereviewhistory rh
JOIN accounts_user u ON u.id = rh.original_technician_id
WHERE rh.review_action IN ('revisions_requested', 'corrections_needed')
  AND u.is_test_account = 0
  AND DATE(rh.reviewed_at) BETWEEN 'DATE_FROM' AND 'DATE_TO'
GROUP BY u.id, u.first_name, u.last_name
ORDER BY u.first_name;

-- Team totals:
SELECT
  SUM(CASE WHEN review_action = 'revisions_requested' THEN 1 ELSE 0 END) AS team_returned,
  SUM(CASE WHEN review_action = 'corrections_needed'  THEN 1 ELSE 0 END) AS team_corrected_by_l3
FROM cases_casereviewhistory rh
JOIN accounts_user u ON u.id = rh.original_technician_id
WHERE rh.review_action IN ('revisions_requested', 'corrections_needed')
  AND u.is_test_account = 0
  AND DATE(rh.reviewed_at) BETWEEN 'DATE_FROM' AND 'DATE_TO';
```
