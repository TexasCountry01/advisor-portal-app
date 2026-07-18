# Weekly Performance Report — Analysis & Implementation Plan

**Request:** A page that renders a 13-week rolling performance snapshot matching the spreadsheet mockup. Includes CSV download and PDF download using the existing app patterns.

---

## Steps 4–7 Validity Check (PERFORMANCE_DASHBOARD_ANALYSIS.md)

All four remaining steps are **valid and require no rework**. Steps 1–3 are complete, so the dependency chain is ready to continue.

| Step | Description | Valid? | Notes |
|---|---|---|---|
| 4 | Compact panel on Admin dashboard (AJAX-loaded, last-7-days) | ✅ | `get_performance_metrics()` already supports this |
| 5 | Same panel on Manager dashboard | ✅ | One template include line after Step 4 |
| 6 | Panel on Tech dashboard (tech sees only their own numbers) | ✅ | `get_performance_metrics(tech_user=user)` already handles per-tech filtering |
| 7 | Open standalone page to Managers and Techs | ✅ | Access control change + tech row highlight in template |

Steps 4–7 are deferred. No changes to the original plan are needed.

---

## Weekly Report — What It Is

A **weekly time-series snapshot** of the same metrics shown on the Performance Dashboard, broken into rolling 13-week columns with per-technician sub-rows. The primary purpose is trend visibility — are numbers improving, declining, or holding steady week over week?

The mockup spreadsheet defines the layout:
- **Columns**: 13 rolling calendar weeks, most recent on the **left**
- **Column headers**: week ranges in `Mon D – Mon D` format (e.g., `Jul 6 – Jul 12`)
- **Row structure**: Each metric is a bold section header row (team total) followed by indented sub-rows, one per active technician

---

## Metrics & Row Structure

| Section | Team Row | Per-Tech Rows | Format |
|---|---|---|---|
| Reports Submitted (Initial Submission) | Team total | None | count |
| Reports Generated | Team total | One per tech | count |
| Reports Submitted for Review | Team total | One per tech | count |
| Tech L1/L2 Accuracy Rate | Team % | One per tech | % |
| On-Time Delivery | Team % | One per tech | % |
| ProFeds Errors | Team total | One per tech | count |
| Report Accuracy | Team % | One per tech | % |
| Production Cycle Time | Team avg | One per tech | days |
| Readiness Window | Team avg | One per tech | days |

**Techs shown**: Only technicians with at least one activity in the 13-week window (no empty rows for inactive/archived techs).

---

## "Numbers Don't Change" — Requirement & Status

**User requirement (2026-07-18):** "I want to make sure that numbers are populated in this reporting tool, and then don't change." Confirmed as a **formal HR evaluation requirement** — metric data is extracted and fed into an external HR tool for technician performance reviews.

**Current implementation status:** The scorecard recalculates live from the database on every page load. This is **insufficient for a formal evaluation tool.**

**Why numbers can change under the current implementation:**
- Benefits technicians and administrators can correct cases as part of the normal L1/L2/L3 review workflow
- An admin correcting a `date_completed`, `date_due`, or `date_submitted` retroactively shifts a prior week's metrics
- Corrections submitted after a week closes but before the data is extracted will silently change already-reviewed numbers

**Decision required:** A data snapshot/lock strategy must be selected and implemented before this report is used for formal HR evaluation. Three options have been documented for user review in `docs/SCORECARD_LOCK_OPTIONS_USER.md`. Technical implementation detail is in `docs/SCORECARD_IMMUTABILITY_TECHNICAL.md`.

**This feature (data locking) is NOT yet implemented.**

---

## Data Architecture

Rather than calling `get_performance_metrics()` 13 separate times (13 × N queries), a single efficient pass is preferred:

1. Compute the 13 week boundaries upfront (Monday–Sunday, ISO week)
2. Pull all relevant records for the full 13-week window in one query per model (`Case`, `CaseReviewHistory`)
3. Group results by week in Python using the already-fetched data
4. Build a nested dict: `{week_index: {metric_key: {team: value, tech_id: value}}}`

This keeps the page load to **~5–6 DB queries total** regardless of how many weeks are shown.

---

## Export Formats — Existing App Patterns

Both export formats follow the established patterns already used throughout the app. No new libraries are needed.

### CSV Export
- Triggered by `?export=csv` query parameter on the main view
- Returns `HttpResponse(content_type='text/csv')` with `Content-Disposition: attachment`
- Flat structure: one row per metric-tech combination, one column per week
- Pattern source: `technician_productivity_report`, `due_date_compliance_report`, `review_accuracy_report`

### PDF Export
- Dedicated view at `/reports/performance/weekly/pdf/`
- Uses `weasyprint` → `render_to_string()` → `HTML(string=...).write_pdf()` → `HttpResponse(content_type='application/pdf')`
- Requires a dedicated PDF HTML template (`weekly_performance_report_pdf.html`) optimized for landscape print
- Pattern source: `technician_productivity_pdf`, `due_date_compliance_pdf`, `profeds_error_tracking_pdf`

---

## Files to Create / Modify

| File | Action | Purpose |
|---|---|---|
| `core/views_reports.py` | Add | Main view `weekly_performance_report` + PDF view `weekly_performance_pdf` |
| `core/urls.py` | Add | Two URL entries: main view + PDF view |
| `templates/core/weekly_performance_report.html` | Create | HTML page with the 13-week table + CSV/PDF download buttons |
| `templates/core/weekly_performance_report_pdf.html` | Create | Weasyprint-optimized landscape template (no nav, compact font) |

No new dependencies. No migrations.

---

## URL Structure

```
/reports/performance/weekly/               → main HTML page + ?export=csv
/reports/performance/weekly/pdf/           → PDF download
```

Accessible from the Reports & Analytics menu, admin-only to start (consistent with the rest of the Performance Dashboard).

---

## Confirmed Decisions (2026-07-18)

| Question | Decision |
|---|---|
| Week boundary | Monday–Sunday (ISO) |
| Which techs | Active techs only (`is_active=True`) — no inactive or archived techs |
| Access | Admin-only for now |
| Team total row | Bold metric header row carries the team total |
| Cycle Time / Readiness format | Whole days (`14d`) — easy to change to decimal later |
| Feature name | **Performance Scorecard** |
| Placement | Separate panel within the Performance Dashboard feature set — own page at `/reports/performance/scorecard/`, linked from the main dashboard. Existing tiles and drilldowns are untouched. |
