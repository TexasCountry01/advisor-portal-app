# Pre-Completion Review

**Release Date:** March 31, 2026

## Overview

A new **Pre-Completion Review** page has been added to the case completion workflow. When a technician clicks **"Mark as Completed"**, they are now taken to a full-page review screen where they must verify all case details before the case can be finalized. This ensures accuracy and quality before the member sees the results.

## What Changed

- The **"Mark as Completed"** button now opens a **Pre-Completion Review** page instead of immediately completing the case
- Technicians must review and confirm all items on a checklist before the case can be completed
- Credit value can be adjusted directly from the review page without going back to the case

## Pre-Completion Review Page

### Case Summary Header
- Displays employee name, case ID, member (advisor), tier, assigned technician, acceptance date, report counts, and current status at a glance

### Reports Section
- Lists all uploaded reports with their status and attached files
- Shows a count comparison (e.g., "3 of 3 uploaded") with a green or yellow badge
- Warns if there is a report count mismatch (fewer uploaded than requested)
- Reports can be viewed/downloaded directly from the review page

### Technical Notes Preview
- Displays a rendered preview of the technical notes exactly as the member will see them
- Alerts the technician if **no technical notes have been written**
- Includes an **"Edit Notes"** link to go back and add or update notes before completing

### Case Documents
- Lists all documents attached to the case (reports, PDFs, etc.)
- Documents can be viewed/downloaded directly from the review page

### Pre-Completion Checklist (Required)
All four items must be checked before the case can be completed:

- **Credit value is accurate** — Shows the current credit and the default for the number of reports requested
- **All reports uploaded and verified** — Shows upload count vs. requested count; allows override if there is a mismatch
- **Technical notes reviewed and complete** — Flags if no notes have been written
- **Overall quality verified and ready for member** — Final quality confirmation

### Credit Value Adjustment
- A dropdown to adjust the credit value (0.0 to 3.0) directly from the review page
- If changed, a **reason field** appears to document why the credit was adjusted
- The credit change is saved atomically with case completion (no extra steps)

### Release Options
- **Release Now** — Member can view results immediately upon completion
- **Schedule Release** — Pick a specific date and time (CST) for the member to see the results
  - Includes a date picker (future dates only) and time selector
  - Shows a summary of the scheduled release date/time

### Action Buttons
- **Complete Case** — Validates the checklist, gathers all inputs, and completes the case in a single action
- **Back to Case** — Returns to the case detail page without completing

## Who Is Affected

- **Level 2 and Level 3 Technicians** — The review page appears when completing any accepted or on-hold case
- **Administrators and Managers** — Can also access the review page for cases they manage
- **Level 1 Technicians** — Not affected; the "Submit for Review" workflow remains unchanged

## Audit Trail

- The completion audit log now includes the full checklist state, credit adjustment details, report counts, and whether technical notes were present at time of completion
