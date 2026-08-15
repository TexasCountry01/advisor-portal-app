# Unified Case Lifecycle Report — Analysis

**Request:** Add a single all-encompassing row-per-case report alongside the existing performance dashboard, consolidating data currently scattered across 11 separate drill-down detail pages.  
**Date:** 2026-08-12  
**Status:** Proposal analysis — pending decision

---

## Context: What the User Is Referencing

The **Benefits Team Portal Metrics** dashboard (the screen with the 11 colorful metric tiles) was built as a prototype to gather feedback. The user went through each tile's drill-down detail page, catalogued every column shown across all 11 views, and assembled the mock-up spreadsheet from those columns.

The request is specifically about those 11 drill-down pages — not the broader report suite (technician productivity, due date compliance, system health, reassignment analysis, etc.), which are separate tools.

---

## Short Answer

This is **not a dumb idea**. The underlying instinct is correct: the 11 drill-down detail pages each show a narrow slice of one case's story. To understand a single case fully you currently have to click into multiple different pages. A unified row-per-case table solves that directly. However, there are real tradeoffs in readability, data gaps, and implementation scope that are worth understanding before committing.

---

## What the 11 Drill-Down Pages Currently Show

Each tile click opens a detail page with a different set of columns. A single case can appear in multiple pages:

| Tile | Columns in Drill-Down |
|---|---|
| Reports Generated | Case ID, Advisor, Employee, Technician, Submitted, Finished, Due Date, Urgency |
| Submitted for Review | Case ID, Employee, Technician, Submitted At |
| On-Time Delivery | Case ID, Employee, Technician, Due Date, Finished, Days Early/Late, Status |
| ProFeds Errors | Mod Case ID, Original Case ID, Employee, Technician, Error Reported |
| Avg Production Cycle Time | Case ID, Employee, Technician, Submitted, Finished, Cycle Time |
| Avg Readiness Window | Case ID, Employee, Technician, Due Date, Finished, Days Early/Late |
| Report Accuracy | Case ID, Employee, Technician, Finished, ProFeds Error Y/N |
| Initial Submissions | Advisor, Workshop, Submitted, Completed, In Progress, Pending Accept, PF Errors |
| L1/L2 Review Accuracy | Case ID, Technician, Reviewer, Review Date, Outcome |
| Level 1/2 Accuracy Rate | Case ID, Employee, Technician, Reviewer, Returned On |
| Corrected by L3 | Case ID, Employee, Technician, Corrected By, Corrected On, Notes |

The mock-up takes all of those columns, removes duplicates, and arranges them into three logical groups with one row per case. That is a sound consolidation.

---

## What You Have Now vs. What You're Proposing

| Current State | Proposed State |
|---|---|
| 11 drill-down pages, each showing one metric's case subset | 1 report, every data point on one row per case |
| A case that completed on time, had a review, and had an error appears in 3 different pages | That same case appears once, with all columns populated |
| Navigate between pages to trace a case lifecycle | Full case lifecycle visible in one place |
| Same date filter on each individual page | Single date filter controls everything |
| 11 separate URLs, no combined export | One page, one export |

---

## The Mock-Up — Column-by-Column Data Assessment

The mock-up shows three collapsible column groups. Here is how each column maps to the actual database:

### Core Columns (always visible)

| Mock-up Column | DB Field | Available? |
|---|---|---|
| Case ID | `external_case_id` | ✅ |
| Code | `workshop_code` | ✅ |
| Member | `member` FK → full name | ✅ |
| Employee | `employee_first_name` / `employee_last_name` | ✅ |
| Technician | `assigned_to` FK → full name | ✅ |

### REVIEWS Section (gray)

| Mock-up Column | DB Field | Available? |
|---|---|---|
| Reviewer | `CaseReviewHistory.reviewed_by` (most recent) | ✅ |
| Tech's notes to reviewer | No dedicated field exists | ⚠️ GAP |
| # Reviews | Count of `CaseReviewHistory` rows per case | ✅ |
| Reviewer action | `CaseReviewHistory.review_action` (approved / revisions requested / corrections needed) | ✅ |
| Reviewer's notes | `CaseReviewHistory.review_notes` | ✅ |

**Gap note:** "Tech's notes to reviewer" is not currently a named field. The closest available data is `Case.notes` (internal) or `Case.review_notes` (reviewer's notes on the case). If you want tech-authored notes-to-reviewer to be captured separately and appear in this column, a new field would need to be added to the model.

### MODS & ERRORS Section (blue)

| Mock-up Column | DB Field | Available? |
|---|---|---|
| Mod? | Derived: `Case.original_case` is not null = modification | ✅ |
| Error reason | `Case.resubmission_notes` on the mod case — member's reason text is required at submission and stored there | ✅ |
| Disputed by Tech (Y/N) | No dispute tracking field exists | ❌ MISSING |
| Disputed justification | No dispute text field exists | ❌ MISSING |

**Gap notes:**
- The system tracks *whether* there was a ProFeds error (`has_profeds_error`) and the *count* (`error_modification_count`). The member's reason text is stored in `resubmission_notes` on the modification case — it is a required field, so it is always populated when a mod is submitted.
- Tech dispute tracking (did the tech push back on the error call, and with what justification?) does not exist in the current model at all. This would require new fields.

### DATES Section (yellow)

| Mock-up Column | DB Field | Available? |
|---|---|---|
| Submitted | `date_submitted` | ✅ |
| Accepted | `date_accepted` | ✅ |
| Finished | `date_completed` | ✅ |
| Released | `actual_release_date` | ✅ |
| Due | `date_due` | ✅ |
| Urgency | `urgency` (Rush / Normal) | ✅ |
| Days on hold | `hold_duration_days` | ✅ |
| Prod Cycle | Calculated: `date_completed − date_accepted` | ✅ (derived) |
| Readiness Window | Calculated: `date_due − date_completed` | ✅ (derived) |
| Status | Calculated: `date_completed ≤ date_due` → On Time / Late | ✅ (derived) |

The DATES section is the most complete. All data either exists directly or is a simple subtraction of two stored dates.

---

## Answers to Your Specific Questions

### "Is this one giant continuous ever-growing report with a date filter at the top?"

Yes, and that is the correct mental model. The report would be filtered by either `date_submitted` or `date_completed` (you would need to decide which makes more sense for your use case — `date_completed` is better for "work done in this period," `date_submitted` is better for "cases received in this period"). As more cases complete, the report grows. The date filter constrains what period you're viewing.

### "Does this report feel too big / hard to read / hard to interpret?"

Honestly — **yes, without the collapsible sections**. The mock-up has ~20 columns. At normal screen width, you cannot see all of them at once without horizontal scrolling. This is a readiness concern.

**With the collapsible sections**, this becomes workable because:
- A manager checking on-time delivery only needs Case ID, Employee, Technician, and the DATES section
- A quality reviewer only needs the REVIEWS section
- A dispute reviewer only needs MODS & ERRORS

The collapsible design is achievable in the portal (Bootstrap 5 JavaScript-based column group show/hide). It just has to actually work well — the sections need to collapse cleanly and the state should persist for the user's session so they don't have to re-collapse on every page load.

### "Should we keep the main reporting dashboard?"

Yes. The two things serve different purposes:
- **Dashboard** = big-picture aggregate numbers for a period ("how many reports, what's the on-time rate, how many errors")
- **Unified report** = per-case detail to investigate specific cases, spot patterns, and answer "what actually happened with case X"

They are complementary, not redundant. Do not replace the dashboard.

---

## Data Gaps Summary

| Column | Gap Type | Effort to Fill |
|---|---|---|
| Tech's notes to reviewer | New `Case` field required | Low — one field, one migration |
| Disputed by Tech (Y/N) | New `Case` field required | Low — one boolean field |
| Disputed justification | New `Case` field required | Low — one text field |

All three gaps are small schema additions. The error reason text is already available via `resubmission_notes` on the mod case — no new work required for that column.

---

## Implementation Options

### Option A — Build the web report with collapsible sections (full implementation)
Build a new Django view that queries `Case` + `CaseReviewHistory`, renders a Bootstrap table with JavaScript-toggled column group collapse, and exports to CSV. This is the full version of what you described.

- **Effort:** Medium (2–3 days backend + frontend)
- **Data gaps:** Would show blanks for the 4 missing fields until they are added to the model
- **Result:** A live filterable report in the portal

### Option B — CSV/Excel export only (quick win first)
Build a single CSV export that produces all available columns per case. No web UI, just a download button on the Reports page.

- **Effort:** Low (half a day)
- **Data gaps:** Same — missing fields would be blank
- **Result:** A spreadsheet your user can open in Excel/Sheets, apply their own column grouping, and filter themselves

### Option C — Build Option B first, then Option A
Start with the CSV export to validate the column set with your user. Once the columns are confirmed correct (and the data gaps are decided on), build the web view.

- **Effort:** Low → Medium
- **Risk:** Lowest — user validates before full build

---

## Recommendation

**Option C** is the right approach:

1. Build the CSV export first — one endpoint, all case data, all available columns
2. User opens it in Google Sheets, confirms the column set is correct
3. Decide which of the 4 gap fields are actually needed and add them
4. Build the web view with collapsible column sections once the data model is locked

The mock-up is a Google Sheet, which suggests the user is already comfortable working with it in that format. A good CSV export may satisfy 80% of the use case with 20% of the effort, and the web view becomes a polish layer on top.

---

## What Should NOT Change

- **The performance dashboard tile view stays.** The 11 aggregate numbers (Reports Generated, On-Time %, L1/L2 Accuracy, etc.) are the executive summary. The unified report is the case-level detail layer beneath it. They serve different purposes.
- **The broader report suite is out of scope for this request** (technician productivity, due date compliance, system health, reassignment analysis). Those are separate tools for separate workflows.
- **The date filter should default to the current period, not "all time".** "All time" on a growing dataset will be slow and visually overwhelming. Default to last 30 days or current quarter, with an option to expand.

---

## How This Fits the User's Explicit Requests

The user said:
> *"We keep the main reporting dashboard (with all of the colorful stats) to tell us the big numbers for the reporting period."*

That is the 11-tile aggregate view. It stays unchanged.

> *"We have a SINGLE all encompassing report that has a row for each case and all of the data points that we were trying to capture in the individual metric reports."*

The "individual metric reports" = the 11 drill-down detail pages. This unified report replaces the need to navigate through them individually.

> *"Is this one giant continuous (and ever growing) report that can be date constrained with a filter at the top?"*

Yes. Filtered by `date_completed` (work finished in the period). Same pattern as the existing drill-downs.

> *"Does this report feel too big (or hard to read/interpret)?"*

Honestly, yes — without the collapsible sections. With them, it is workable because users only expand what they need. This is the critical design requirement. If the collapse behavior does not work well, the report will be abandoned.
