# Team Performance Dashboard — Status & Next Steps

---

## What Was Built

A **Team Performance Dashboard** is now live at **https://reports.profeds.com** under Reports & Analytics.

**Access:** Administrators only (for now).

**11 metrics — team totals with per-technician breakdown:**

| # | Metric | What it shows |
|---|---|---|
| 1 | Reports Generated | Cases finished and released by techs in the window |
| 2 | Submitted for Review | Times any tech submitted a case for senior review (event count) |
| 3 | On-Time Delivery % | Cases completed on or before due date ÷ total cases with a due date |
| 4 | ProFeds Errors | Member-flagged error modification cases in the window |
| 5 | Avg Production Cycle Time | Average days from member submission to tech release |
| 6 | Avg Readiness Window | Average days the tech finished ahead of (or behind) the due date |
| 7 | Report Accuracy % | Completed cases with no error flag ÷ all completed cases |
| 8 | Advisor Submissions | Total cases submitted by advisors in the window |
| 9 | L1/L2 Review Accuracy % | First-pass approval rate for L1/L2 techs going through quality review |
| 10 | Returned to Tech | Cases sent back to the tech by L3 with revisions requested |
| 11 | Corrected by L3 | Cases where L3 fixed the issue directly without returning to the tech |

**Per-technician breakdown table:** All 11 metrics shown per tech. Review Accuracy, Returned, and Corrected columns appear for techs subject to quality review; others show "Not reviewed."

**Advisor Submission Breakdown:** A separate table at the bottom shows each advisor's submissions with status breakdown (completed, in-progress, pending accept, PF errors).

**Date range:** Defaults to the last 7 days. Fully adjustable.

**Data:** Real production data. Test accounts (Devops*) are excluded from all metrics.

---

## What This Version Does NOT Include

- Visible on the Manager or Technician dashboards
- Individual tech can see only their own numbers
- PDF or CSV export

---

## Questions for You

1. Do the 11 metrics match what you were expecting to see?
2. Are the metric definitions (shown at the bottom of the page) correct?
3. Anything you'd remove, rename, or add?
4. Should techs and managers be able to see this dashboard (and their own numbers) directly from their dashboards?

---

## What Comes Next (pending your feedback)

**Approved for implementation:** Drill-down detail views — clicking each tile opens a detail page showing the individual records behind that number.

| Drill-Down Step | Tile | New code needed |
|---|---|---|
| A | On-Time Delivery %, ProFeds Errors | None — link to existing reports |
| B | Reports Generated | New shared detail view + template |
| C | Initial Submissions | Reuses pattern from B |
| D | Submitted for Review | Reuses pattern from B |
| E | Level 1/2 Accuracy Rate | Reuses pattern from B |
| F | Corrected by L3 | Reuses pattern from B |
| G | L1/L2 Review Accuracy % | Reuses pattern from B |
| H | Production Cycle Time | Reuses pattern from B |
| I | Readiness Window | Reuses pattern from B |
| J | Report Accuracy % | Reuses pattern from B |

**Also pending your feedback:**
- Panel on Admin/Manager/Tech dashboards
- Managers and techs can access the full page directly
