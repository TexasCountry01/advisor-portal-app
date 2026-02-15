# Advisor Portal — Buttons, Labels & Status Indicators

**Date:** February 15, 2026  
**Purpose:** Complete inventory of every button, label, and status indicator in the application, organized by page and user role.

---

## Table of Contents

1. [Member Dashboard](#1-member-dashboard)
2. [Technician Dashboard](#2-technician-dashboard)
3. [Case Detail Page — Member View](#3-case-detail-page--member-view)
4. [Case Detail Page — Technician View](#4-case-detail-page--technician-view)
5. [Case Detail Page — Manager / Administrator View](#5-case-detail-page--manager--administrator-view)
6. [Status Labels (Colored Indicators)](#6-status-labels-colored-indicators)
7. [Stat Tiles (Dashboard Summary Numbers)](#7-stat-tiles-dashboard-summary-numbers)
8. [Pop-Up Windows (Modals)](#8-pop-up-windows-modals)
9. [Notification Panel](#9-notification-panel)
10. [Alerts & Banners](#10-alerts--banners)

---

## 1. Member Dashboard

This is the home page members see after logging in. It shows their submitted cases in a table.

### Top Action Buttons

| Button | Color | What It Does |
|--------|-------|-------------|
| **Submit New Case** | Blue (solid) | Opens the case submission form to start a new Federal Fact Finder |
| **Notifications** | Cyan (outline) | Opens the notification sidebar panel showing case updates |
| **Logout** | Red (outline) | Logs the user out of the portal |

### Filter & View Controls

| Button | Color | What It Does |
|--------|-------|-------------|
| **Hide / Show** | Gray (outline) | Toggles the stats tiles and filter area open/closed |
| **Filters** | Gray (outline) | Expands the filter options (status, urgency, search) |
| **Filter** | Blue (solid, small) | Applies the selected filters to the case list |
| **Reset** | Gray (outline, small) | Clears all filters and shows all cases |
| **Columns** | Gray (outline) | Opens a dropdown to show/hide table columns |

### Case Table — Per Row

| Button | Color | What It Does |
|--------|-------|-------------|
| **View** | Blue (outline, small) | Opens the full case detail page for that case |

*Note: If a case has unread messages, a small red number badge appears on the View button.*

### Draft Cases Banner

| Button | Color | What It Does |
|--------|-------|-------------|
| **Edit & Submit** | Red (outline, small) | Opens the draft case so the member can complete and submit it |

---

## 2. Technician Dashboard

This is the home page for technicians, managers, and administrators. It shows all cases (or just assigned cases) in a detailed table.

### Top Action Buttons

| Button | Color | What It Does |
|--------|-------|-------------|
| **Management** | Blue (outline) | Opens a dropdown menu with management options |
| ↳ Workshop Delegates | — | Goes to the Workshop Delegates management page |
| ↳ Manage Users | — | Goes to the User Management page (administrators only) |
| **Logout** | Red (outline) | Logs the user out of the portal |

### View Toggle

| Button | Color | What It Does |
|--------|-------|-------------|
| **All Cases** | Blue (outline) | Shows all cases in the system |
| **My Cases** | Blue (outline) | Filters to only show cases assigned to the logged-in user |

### Filter & View Controls

| Button | Color | What It Does |
|--------|-------|-------------|
| **Hide / Show** | Gray (outline) | Toggles the stats tiles and filter area open/closed |
| **Filters** | Gray (outline) | Expands the filter options (status, urgency, tier, sort, search) |
| **Filter** | Blue (solid) | Applies the selected filters to the case list |
| **Reset** | Gray (outline) | Clears all filters and shows all cases |
| **Columns** | Gray (outline) | Opens a dropdown to show/hide table columns |

### Case Table — Per Row

| Button | Color | What It Does |
|--------|-------|-------------|
| **View** | Blue (outline, small) | Opens the full case detail page for that case |

---

## 3. Case Detail Page — Member View

This is what members see when they click "View" on a case. The buttons shown depend on the case status.

### Top Navigation Buttons (Always Visible)

| Button | Color | When It Appears | What It Does |
|--------|-------|----------------|-------------|
| **Edit Case** | Yellow (solid) | When case is editable (Submitted, Resubmitted, Accepted) | Opens the case form for editing |
| **Back to Dashboard** | Blue (outline) | Always | Returns to the Member Dashboard |

### Completed Case Buttons

| Button | Color | When It Appears | What It Does |
|--------|-------|----------------|-------------|
| **Request a Modification** | Cyan (outline) | When case is completed and released | Opens a form to request changes to a completed case |
| **Ask a Question** | Green (outline) | When case is completed and released | Opens a form to ask the technician a question |

### Draft Case Buttons

| Button | Color | When It Appears | What It Does |
|--------|-------|----------------|-------------|
| **Submit Case** | Green (solid) | When case is in Draft status | Submits the draft case for processing |
| **Edit Draft** | Yellow (solid) | When case is in Draft status | Opens the draft for editing |
| **Delete Draft** | Red (outline) | When case is in Draft status | Permanently deletes the draft case (asks for confirmation first) |

### Other Case Buttons

| Button | Color | When It Appears | What It Does |
|--------|-------|----------------|-------------|
| **Cancel Case** | Red (outline) | When case is not completed/cancelled | Opens a confirmation window to cancel the case |

### Case Chat Section

| Button | Color | What It Does |
|--------|-------|-------------|
| **Send Message** | Blue (solid) | Sends a typed message to the technician assigned to the case |

### Reports & Resources Section

| Button | Color | What It Does |
|--------|-------|-------------|
| **Download** (down arrow icon) | Blue (outline, small) | Downloads a report document |

### Technical Notes Section

| Button | Color | When It Appears | What It Does |
|--------|-------|----------------|-------------|
| **Download Notes as PDF** | Cyan (solid, small) | When case is released and notes exist | Downloads the technician's formatted notes as a PDF |

### Member Documents Section

| Button | Color | What It Does |
|--------|-------|-------------|
| **Upload Document** | Blue (solid, small) | Opens a window to upload documents to the case |
| **Download** (down arrow icon) | Blue (outline, small) | Downloads an uploaded document |

---

## 4. Case Detail Page — Technician View

This is what technicians see. It has the most buttons due to case processing actions.

### Top Navigation Buttons

| Button | Color | When It Appears | What It Does |
|--------|-------|----------------|-------------|
| **Back to Dashboard** | Blue (outline) | Always | Returns to the Technician Dashboard |
| **Reassign** | Yellow (outline) | When tech has permission | Opens a window to reassign the case to another technician |
| **Take Ownership** | Green (outline) | When case is unassigned or assigned to someone else | Assigns the case to the logged-in technician |

### Case Processing Buttons — New/Submitted Cases

| Button | Color | When It Appears | What It Does |
|--------|-------|----------------|-------------|
| **Accept Case** | Green (solid, small) | When case is Submitted or Resubmitted | Accepts the case and assigns it to the technician |
| **Put on Hold** | Yellow (solid, small) | When case is Submitted or Resubmitted | Opens a window to put the case on hold with a reason |

### Case Processing Buttons — Accepted Cases (Level 1 Technician)

| Button | Color | What It Does |
|--------|-------|-------------|
| **Submit for Review** | Blue (solid) | Sends the case to a Level 3 technician for quality review |
| **Put on Hold** | Yellow (solid) | Opens a window to put the case on hold with a reason |

### Case Processing Buttons — Accepted Cases (Level 2/3 Technician)

| Button | Color | What It Does |
|--------|-------|-------------|
| **Mark as Completed** | Green (solid) | Opens the release scheduling window to complete the case |
| **Put on Hold** | Yellow (solid) | Opens a window to put the case on hold with a reason |

### Case Processing Buttons — Pending Review (Level 3 Reviewer)

| Button | Color | What It Does |
|--------|-------|-------------|
| **Approve Case** | Green (solid) | Opens a window to approve and schedule the case for release |
| **Request Revisions** | Yellow (solid) | Opens a window to send the case back with revision notes |
| **Fix & Complete Myself** | Red (solid) | Allows the reviewer to fix issues and complete the case themselves |

### Case Processing Buttons — Completed Cases

| Button | Color | What It Does |
|--------|-------|-------------|
| **Mark as Incomplete** | Gray (solid) | Reverts the case back to "Accepted" status for further work |
| **Change Release Date** | Cyan (solid) | Opens a window to change when the case becomes visible to the member |

### Case Processing Buttons — On Hold Cases

| Button | Color | What It Does |
|--------|-------|-------------|
| **Resume from Hold** | Cyan (solid) | Removes the hold and returns case to its previous status |
| **Put on Hold** | Yellow (solid) | Can update the hold reason |

### Case Information Card

| Button | Color | What It Does |
|--------|-------|-------------|
| **Edit Details** | Blue (outline, small) | Opens a window to edit case details (urgency, due date, tier, reports requested, etc.) |
| **Adjust Credit** | Gray (outline, small) | Opens a window to change the credit value for the case |

### Internal Notes Section

| Button | Color | What It Does |
|--------|-------|-------------|
| **Add/Edit Notes** | Cyan (solid, small) | Toggles the internal notes text area for editing |
| **Save Note** | Gray (solid, small) | Saves the internal note |
| **Delete** (trash icon) | Red (outline, small) | Deletes an internal note |

### Reports & Resources Section

| Button | Color | What It Does |
|--------|-------|-------------|
| **Upload Report** | Blue (solid, small) | Opens a window to upload a report file to the case |
| **Download** (down arrow icon) | Blue (outline, small) | Downloads a report document |

### Documents Section

| Button | Color | What It Does |
|--------|-------|-------------|
| **Upload Document** | Blue (solid, small) | Opens a window to upload a document to the case |
| **Download** (down arrow icon) | Blue (outline, small) | Downloads a document |
| **Delete** (trash icon) | Red (outline, small) | Deletes a document |

### Technical Notes to Member (Floating Window)

| Button | Color | What It Does |
|--------|-------|-------------|
| **Technical Notes** | Cyan (solid) | Opens the floating notes editor window |
| **Download Notes as PDF** | Cyan (solid, small) | Downloads the formatted notes as a PDF |
| **Release Now** | Green (solid, small) | Immediately releases a completed case to the member |

### Case Chat Section

| Button | Color | What It Does |
|--------|-------|-------------|
| **Send Message** | Blue (solid) | Sends a message to the case chat visible to the member |

---

## 5. Case Detail Page — Manager / Administrator View

Managers and Administrators see everything technicians see, plus additional controls.

### Additional Buttons (Manager)

| Button | Color | What It Does |
|--------|-------|-------------|
| **Back to Dashboard** | Blue (outline) | Returns to the Manager Dashboard |
| **Reassign** | Yellow (outline) | Opens a window to reassign the case to any technician |

### Additional Buttons (Administrator)

| Button | Color | What It Does |
|--------|-------|-------------|
| **Back to Dashboard** | Blue (outline) | Returns to the Admin Dashboard |
| **Reassign** | Yellow (outline) | Opens a window to reassign the case to any technician |
| **Take Ownership** | Red (solid) | Forces ownership of the case (overrides current assignment) |

---

## 6. Status Labels (Colored Indicators)

These are **not buttons** — they are colored labels that indicate the current state of a case. They appear in dashboard tables and on the case detail page.

### Case Status Labels

| Label Text | Color | What It Means |
|-----------|-------|--------------|
| **Draft** | Red | Case has been started but not yet submitted by the member |
| **Submitted** | Gray | Case has been submitted and is waiting to be accepted by a technician |
| **Resubmitted** | Cyan | Member has resubmitted a previously completed case with updates |
| **Accepted** | Blue | Case has been accepted by a technician and is being worked on |
| **Needs Revision** | Yellow | Case was reviewed and sent back to the technician for corrections |
| **Pending Review** | Yellow | Case has been submitted for quality review by a Level 3 technician |
| **On Hold** | Red | Case is paused, usually waiting for information from the member |
| **Completed** | Green | Case has been completed and released to the member |
| **Cancelled** | Red | Case has been cancelled |
| **Scheduled** | Red | Case is completed but scheduled for future release |
| **Working** | Cyan | Case is completed but not yet released |

### Urgency Labels

| Label Text | Color | What It Means |
|-----------|-------|--------------|
| **Rush** | Red | Case has been flagged as urgent/rush priority |
| **Normal** | Gray | Case is standard priority |

### Other Information Labels

| Label Text | Color | Where It Appears | What It Means |
|-----------|-------|-----------------|--------------|
| **Our Error** | Red | Technician Dashboard | Case was resubmitted due to a technician error |
| **New Info** | Yellow | Technician Dashboard | Case was resubmitted because the member provided new information |
| **You own this case** | Green | Case Detail Page | Confirms the logged-in technician is assigned to this case |
| **Modification** | Cyan | Case Detail Page | Indicates the case originated from a modification request |
| **Resubmitted #_** | Cyan | Member Dashboard | Shows which resubmission number this case is |
| **No file** | Yellow | Case Detail Page | A document record exists but no actual file was uploaded |
| **Unread count** (number) | Red | Various | Shows the number of unread messages or notifications |

---

## 7. Stat Tiles (Dashboard Summary Numbers)

These are the colored number tiles at the top of each dashboard. They are **not buttons** — they display counts of cases in each category.

### Member Dashboard Stat Tiles

| Tile Label | Color | What It Shows |
|-----------|-------|--------------|
| **Total** | Purple gradient | Total number of cases submitted by the member |
| **Draft** | Purple gradient | Number of unsubmitted draft cases |
| **Submitted** | Purple gradient | Number of cases waiting to be accepted |
| **Accepted** | Purple gradient | Number of cases currently being worked on |
| **Resubmitted** | Cyan gradient | Number of resubmitted cases |
| **Rush** | Red gradient | Number of rush/urgent cases |
| **Ready** | Green gradient | Number of completed cases ready for download |

### Technician Dashboard Stat Tiles

| Tile Label | Color | What It Shows |
|-----------|-------|--------------|
| **Total** | Blue gradient | Total number of cases |
| **Submitted** | Blue gradient | Number of cases waiting to be accepted |
| **Accepted** | Blue gradient | Number of cases currently being worked on |
| **Resubmitted** | Cyan gradient | Number of resubmitted cases |
| **Pending** | Blue gradient | Number of cases awaiting quality review |
| **Needs Revision** | Yellow gradient | Number of cases sent back for corrections (only shown when count > 0) |
| **Completed** | Blue gradient | Number of completed cases |
| **Rush** | Red gradient | Number of rush/urgent cases |

---

## 8. Pop-Up Windows (Modals)

These are dialog windows that appear when certain buttons are clicked. They require the user to confirm an action or fill in information.

### Cancel Case

| Field | Description |
|-------|------------|
| Opens when | Member clicks "Cancel Case" |
| Confirmation text | Asks if the member is sure they want to cancel |
| **Cancel** button (gray) | Closes the window without doing anything |
| **Confirm Cancel** button (red) | Cancels the case |

### Request a Modification

| Field | Description |
|-------|------------|
| Opens when | Member clicks "Request a Modification" on a completed case |
| Description field | Text area to describe what changes are needed |
| **Cancel** button (gray) | Closes the window |
| **Submit Request** button (blue) | Submits the modification request |

### Ask a Question

| Field | Description |
|-------|------------|
| Opens when | Member clicks "Ask a Question" on a completed case |
| Question field | Text area to type the question |
| **Cancel** button (gray) | Closes the window |
| **Submit Question** button (blue) | Sends the question to the technician |

### Put on Hold

| Field | Description |
|-------|------------|
| Opens when | Technician clicks "Put on Hold" |
| Reason field | Text area to explain why the case is being put on hold |
| **Cancel** button (gray) | Closes the window |
| **Confirm** button (blue) | Puts the case on hold |

### Upload Report

| Field | Description |
|-------|------------|
| Opens when | Technician clicks "Upload Report" |
| File picker | Allows selecting a file to upload |
| Notes field | Optional notes about the report |
| **Cancel** button (gray) | Closes the window |
| **Upload** button (blue) | Uploads the report |

### Upload Document

| Field | Description |
|-------|------------|
| Opens when | Anyone clicks "Upload Document" |
| File picker | Allows selecting a file to upload |
| Description field | Optional description of the document |
| **Cancel** button (gray) | Closes the window |
| **Upload** button (blue) | Uploads the document |

### Release Scheduling (Mark as Completed)

| Field | Description |
|-------|------------|
| Opens when | Technician clicks "Mark as Completed" |
| Release option | Choose between releasing immediately (ASAP) or scheduling for a future date |
| Date picker | Select the release date (only shown for scheduled release) |
| Time picker | Select the release time (only shown for scheduled release) |
| **Cancel** button (gray) | Closes the window |
| **Confirm** button (blue) | Completes the case with the chosen release option |

### Approve Case (Quality Review)

| Field | Description |
|-------|------------|
| Opens when | Level 3 reviewer clicks "Approve Case" |
| Release option | Choose between releasing immediately (ASAP) or scheduling for a future date |
| Date picker | Select the release date (only shown for scheduled release) |
| Time picker | Select the release time (only shown for scheduled release) |
| **Cancel** button (gray) | Closes the window |
| **Approve & Complete** button (green) | Approves the case and schedules release |

### Request Revisions (Quality Review)

| Field | Description |
|-------|------------|
| Opens when | Level 3 reviewer clicks "Request Revisions" |
| Feedback field | Text area to describe what corrections are needed |
| **Cancel** button (gray) | Closes the window |
| **Send Back for Revisions** button (yellow) | Returns the case to the Level 1 technician with feedback |

### Fix & Complete Myself (Quality Review)

| Field | Description |
|-------|------------|
| Opens when | Level 3 reviewer clicks "Fix & Complete Myself" |
| Release option | Choose between releasing immediately (ASAP) or scheduling for a future date |
| Date picker | Select the release date (only shown for scheduled release) |
| Time picker | Select the release time (only shown for scheduled release) |
| **Cancel** button (gray) | Closes the window |
| **Apply Corrections & Complete** button (red) | Reviewer fixes and completes the case |

### Edit Case Details

| Field | Description |
|-------|------------|
| Opens when | Technician clicks "Edit Details" |
| Urgency | Dropdown to change urgency (Normal / Rush) |
| Due Date | Date picker to set or change the due date |
| Tier | Dropdown to change the case tier |
| Reports Requested | Number field for how many reports are needed |
| **Cancel** button (gray) | Closes the window |
| **Save Changes** button (blue) | Saves the updated case details |

### Credit Adjustment

| Field | Description |
|-------|------------|
| Opens when | Technician clicks "Adjust Credit" |
| Credit Value | Number field to enter the new credit amount |
| **Cancel** button (gray) | Closes the window |
| **Save Credit Adjustment** button (blue) | Saves the credit value |

### Reassign Case

| Field | Description |
|-------|------------|
| Opens when | Tech/Manager/Admin clicks "Reassign" |
| Technician dropdown | Select which technician to assign the case to |
| **Cancel** button (gray) | Closes the window |
| **Reassign** button (yellow) | Reassigns the case to the selected technician |

### Admin Take Ownership

| Field | Description |
|-------|------------|
| Opens when | Administrator clicks "Take Ownership" (red button) |
| Warning message | Explains that this will override the current assignment |
| **Cancel** button (gray) | Closes the window |
| **Confirm** button (red) | Forces ownership of the case |

### Approve Change Request (Modification)

| Field | Description |
|-------|------------|
| Opens when | Technician clicks "Approve" on a modification request |
| Notes field | Optional notes about the approval |
| **Cancel** button (gray) | Closes the window |
| **Approve** button (green) | Approves the modification request |

### Deny Change Request (Modification)

| Field | Description |
|-------|------------|
| Opens when | Technician clicks "Deny" on a modification request |
| Reason field | Text area to explain why the request was denied |
| **Cancel** button (gray) | Closes the window |
| **Deny** button (red) | Denies the modification request |

---

## 9. Notification Panel

The notification panel slides in from the right side of the screen.

| Element | Color | What It Does |
|---------|-------|-------------|
| **Notifications** header | Cyan (solid) | Title bar of the notification panel |
| **Close** (X icon) | White | Closes the notification panel |
| **Mark All as Read** | Cyan (outline, small) | Marks all notifications as read |
| Individual notification | — | Clicking a notification takes you to the related case |

---

## 10. Alerts & Banners

These are colored bars that appear at the top of pages to communicate important information.

### Member Dashboard Banners

| Banner | Color | When It Appears | What It Says |
|--------|-------|----------------|-------------|
| **Case Submitted Successfully** | Green | After successfully submitting a case | Confirms the case was submitted |
| **You Have Cases on Hold** | Yellow | When one or more cases are on hold | Lists which cases are on hold and need member attention |
| **Unsubmitted Drafts** | Red | When draft cases exist | Lists draft cases with an "Edit & Submit" button for each |

### Case Detail Page Banners

| Banner | Color | When It Appears | What It Says |
|--------|-------|----------------|-------------|
| **Needs Revision** | Yellow | When a Level 3 reviewer has requested changes | Shows the reviewer's name, date, and their feedback notes |
| **Awaiting Quality Review** | Blue | When case is pending review | Informs the technician that a reviewer will look at this case |
| **Completion Warning** | Yellow | When reports or documents are missing | Lists what needs to be completed before the case can be finished |
| **Override Warning** | Yellow | When a technician tries to complete without required items | Asks if they want to proceed anyway |

---

*End of Inventory*
