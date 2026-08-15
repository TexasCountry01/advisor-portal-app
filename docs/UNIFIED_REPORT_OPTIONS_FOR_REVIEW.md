# Unified Case Report — Options for Review

**Your idea is a good one.** Here is a summary of what it means in practice and three ways we could build it.

---

## What You Asked For — Confirmed

> *"We keep the main reporting dashboard (with all of the colorful stats) to tell us the big numbers for the reporting period."*

✅ **Yes — the dashboard stays exactly as it is.** The 11 metric tiles are the high-level summary. Nothing about that changes.

> *"We have a SINGLE all-encompassing report that has a row for each case and all of the data points."*

✅ **Yes — this is buildable.** Almost all the data already exists in the system. A handful of columns from your mock-up (the dispute tracking fields) do not have a place to live yet, but everything else is there.

> *"Is this one giant continuous (and ever-growing) report that can be date-constrained with a filter at the top?"*

✅ **Yes.** Filtered by when the case was finished. The same date filter you use on the dashboard today.

> *"Does this report feel too big or hard to read?"*

**Honestly, yes — but only if the collapsible sections do not work well.** The three colored sections (Reviews, Mods & Errors, Dates) need to collapse and stay collapsed so the table is not overwhelming. If those work the way your mock-up shows, the report is very usable. If they don't, it will be hard to navigate. That collapse behavior is the single most important design detail.

---

## What Data Is Already Available

| Section | Status |
|---|---|
| Core columns — Case ID, Code, Member, Employee, Technician | ✅ Ready |
| DATES — Submitted, Accepted, Finished, Released, Due, Urgency, Days on Hold, Cycle Time, Readiness Window, On Time/Late | ✅ Ready |
| REVIEWS — Reviewer, # of Reviews, Review Outcome, Reviewer Notes | ✅ Ready |
| Mod? (was this a modification case) | ✅ Ready |
| Error reason — what the member said when flagging the error | ✅ Ready |
| Tech's notes to reviewer | ⚠️ Not currently captured — small addition if needed |
| Disputed by Tech (Y/N) and justification | ⚠️ Not currently captured — small addition if needed |

The gap items are small. They only matter if you want those specific columns. If you do, they can be added before or after the first build — they do not block getting started.

---

## Three Ways to Build This

---

### Option A — Full Portal Report (Web View with Collapsible Sections)

Build the report directly inside the portal. Rows for every case, three collapsible column sections, date filter at the top, export to CSV button.

**What you get:**
- Live report accessible to any admin/manager in the portal
- Collapsible sections work the way your mock-up shows
- Same date filter already on the dashboard
- One-click CSV export

**Effort:** 2–3 days of development  
**Risk:** If the column set turns out to need changes after you see real data, adjustments take another round of development

---

### Option B — CSV Export Only

Add a single "Download Unified Case Report" button to the Reports page. Clicking it downloads a spreadsheet with every case and all available columns. No changes to the web UI.

**What you get:**
- All the same data as Option A, in spreadsheet form
- You can open it in Google Sheets, apply your own column grouping, filter, sort, and highlight exactly the way your mock-up already works
- Much faster to deliver

**Effort:** Half a day of development  
**Risk:** Very low — if the columns aren't right, it's easy to adjust

---

### Option C — CSV Export First, Then Portal View *(Recommended)*

Start with Option B. Use the downloaded spreadsheet to confirm the column set is correct and the data looks right. Once you're satisfied, build the full web view (Option A) on top of the confirmed foundation.

**What you get:**
- Fast first delivery — you have something usable within days
- You validate the real data before we invest in the full web build
- The portal view is built on a column set you've already approved
- If you decide the CSV is good enough on its own, you stop there

**Effort:** Low first, medium second  
**Risk:** Lowest of the three options

---

## Recommendation

**Option C.**

Your mock-up was built in Google Sheets, which means you already know how to work with the data in that format. A CSV export gets the data in front of you fast, lets you verify it looks right, and gives you a chance to decide whether the full portal view is worth the extra build time — or whether the spreadsheet already does what you need.

The portal view is a worthwhile addition, but it should be built on a column set you've already validated, not guessed at.

---

## One Thing to Decide Before We Start

**Do you want the dispute tracking columns?**

The mock-up includes:
- *Disputed by Tech (Y/N)* — did the technician push back on an error call?
- *Disputed justification* — what was their reason?

These fields do not exist in the system today. Adding them is straightforward, but it also means technicians would need a way to fill them in when they dispute an error. That is a small workflow addition.

If you want those columns in the report, we add them first. If you're comfortable leaving them blank for now and adding them later, we can start the build immediately.
