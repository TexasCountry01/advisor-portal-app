# Audit Log Search Bug Analysis
**Date:** May 5, 2026  
**Reported by:** Chris Kowalik  
**Case in question:** Crystal Hampton — WS000-2026-04-0449 (DB id: 681)  
**Technicians involved:** Ileana Colón-Varona (original), Tiffany Widelski (took ownership May 5)

---

## The Problem

Chris searched the global Audit Log for "hampton" expecting to see all activity on Crystal Hampton's case. Only 1 of 5 entries appeared. She then searched by the Case ID (WS000-2026-04-0449) and again only 1 entry appeared — a different one.

**Bottom line: The data is complete. The search is broken.**

---

## What's Actually in the Database (All 5 Entries)

| Timestamp | Action | By | Description |
|---|---|---|---|
| Apr 27, 2026 09:17 | Case Submitted | Elita Roberts (delegate) | "Case submitted for Crystal Hampton by delegate Elita Roberts on behalf of Anthony Roberts" |
| Apr 27, 2026 11:11 | Case Accepted | Tiffany Widelski | "Case accepted as Tier 1, assigned to Ileana Colón-Varona" |
| May 05, 2026 06:59 | Case Ownership Taken | Tiffany Widelski | "Claimed ownership of case (was: Ileana Colón-Varona)" |
| May 05, 2026 06:59 | Case Completed | Tiffany Widelski | "Case marked as completed - released immediately" |
| May 05, 2026 07:00 | Email Notification Sent | Tiffany Widelski | "Case completed email sent to [troberts@..., eroberts@..., pportell@..., kroberts@...] for case WS000-2026-04-0449" |

All 5 entries are also visible on the **case-level Audit History panel** (the "View Full History" button on the Crystal Hampton case page). That view works correctly because it queries by case ID directly — no text search involved.

---

## Bug 1 — "Search" Box Only Scans Description Text

**What it does:** Searches only the `description` text field of each log entry.

**Why this fails:** Most log descriptions do NOT include the member's name. Of the 5 entries:
- Only "Case Submitted" says *"Crystal Hampton"* in its description → only this one appeared when searching "hampton"
- The other 4 say things like *"Claimed ownership of case (was: Ileana Colón-Varona)"* — no mention of Hampton

**What it should do:** Also search the member's first/last name on the linked case, and the external case ID.

---

## Bug 2 — "Case ID" Filter Field Is Completely Non-Functional

**What it does:** Tries to convert the entered text to an integer and filter by database primary key. When you type "WS000-2026-04-0449", it fails silently (can't convert to int) and applies **no filter at all**, returning everything.

**Why only 1 entry appeared when searching the Case ID field as text (via the Search box):** Only the "Email Notification Sent" entry explicitly contains the string "WS000-2026-04-0449" in its description text.

**What it should do:** Match against the `external_case_id` field on the linked case.

---

## What About Ileana?

The audit log shows no entries for Ileana between Apr 27 (when the case was assigned to her) and May 5 (when Tiffany took over). This means either:
1. Ileana genuinely did not open or touch the case during that period, or
2. There are actions she took that the system does not log (e.g., simply viewing a case is not logged; only explicit actions like saving notes, uploading documents, changing status, etc.)

The log is not broken — this absence may reflect reality. It is a separate question from the search bugs.

---

## Fix Options

### Option A — Fix Both Search Bugs Only
1. "Search" box also queries `case__employee_last_name`, `case__employee_first_name`, and `case__external_case_id`
2. "Case ID" field matches `case__external_case_id__icontains` instead of silently failing on the integer conversion

**Result after fix:** Searching "hampton" returns all 5 entries. Searching "WS000-2026-04-0449" in the Case ID field returns all 5 entries.

### Option B — Fix Both Bugs + Improve Log Descriptions (Recommended)
Same as Option A, plus update the log description text for `case_accepted`, `case_ownership_taken`, `case_completed`, and related actions to include the external case ID and member name. Example:
- Before: *"Claimed ownership of case (was: Ileana Colón-Varona)"*
- After: *"Claimed ownership of WS000-2026-04-0449 — Crystal Hampton (was: Ileana Colón-Varona)"*

**Result:** All 5 entries found by either "hampton" or "WS000-2026-04-0449" searches. Future log entries are also discoverable by plain text search even without the search fix.

### Option C — No Code Change
Direct Chris to:
- Open the case → "View Full History" (shows all 5, works perfectly)
- Use the **User** dropdown filter to filter by Tiffany or Ileana

The global search is limited but the per-case view is accurate and complete.

---

## Recommendation

**Option B** — fixes the root cause so the global Audit Log works as expected, and improves log description quality for all future entries. Chris will be able to search by member name or case ID and see the full activity trail.
