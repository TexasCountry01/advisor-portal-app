# Advisor Portal — Complete UI Element Inventory

> **Generated:** February 15, 2026  
> **Purpose:** Non-technical stakeholder reference for every visible button, badge, status indicator, and modal in the application.

---

## TABLE OF CONTENTS

1. [Global Navigation Bar (All Pages)](#1-global-navigation-bar)
2. [Login Page](#2-login-page)
3. [Profile Page](#3-profile-page)
4. [Member Dashboard](#4-member-dashboard)
5. [Submit New Case Page](#5-submit-new-case-page)
6. [Technician Dashboard](#6-technician-dashboard)
7. [Manager Dashboard](#7-manager-dashboard)
8. [Administrator Dashboard](#8-administrator-dashboard)
9. [Case Detail Page](#9-case-detail-page)
10. [Delete Case Confirmation Page](#10-delete-case-confirmation-page)
11. [Master Status Badge Reference](#11-master-status-badge-reference)
12. [Master Modal Dialog Reference](#12-master-modal-dialog-reference)

---

## 1. GLOBAL NAVIGATION BAR

Appears at the top of every page (sticky blue bar). Contents change based on role.

### Navbar Brand / Logo
| Element | Text | Color | Who Sees It | Description |
|---------|------|-------|-------------|-------------|
| Brand link | **Advisor Portal** | White text on blue bar | All | Navigates to the home page |

### Navbar Links — Member Role
| Element | Text | Color | When Visible | Description |
|---------|------|-------|--------------|-------------|
| Nav link | **Dashboard** | White text | Always (member) | Goes to Member Dashboard |
| Nav link | **Submit Case** | White text | Always (member) | Goes to Submit New Case page |

### Navbar Links — Technician Role
| Element | Text | Color | When Visible | Description |
|---------|------|-------|--------------|-------------|
| Nav link | **Dashboard** | White text | Always (technician) | Goes to Technician Dashboard |
| Nav link | **All Cases** | White text | Always (technician) | Goes to full case list |

### Navbar Links — Administrator Role
| Element | Text | Color | When Visible | Description |
|---------|------|-------|--------------|-------------|
| Nav link | **Admin** | White text | Always (admin) | Goes to Django admin panel |
| Nav link | **All Cases** | White text | Always (admin) | Goes to full case list |

### Navbar — User Menu Dropdown (Authenticated Users)
| Element | Text | Color | When Visible | Description |
|---------|------|-------|--------------|-------------|
| Dropdown toggle | **[User's Full Name]** | White text | Logged in | Opens user menu |
| Dropdown item | **Profile** | Dark text | Logged in | Goes to user profile page |
| Dropdown item | **Logout** | Dark text | Logged in | Logs the user out |

### Navbar — Unauthenticated
| Element | Text | Color | When Visible | Description |
|---------|------|-------|--------------|-------------|
| Nav link | **Login** | White text | Not logged in | Goes to login page |

### Alert Banners (Below Navbar)
| Element | Text | Color | When Visible | Description |
|---------|------|-------|--------------|-------------|
| Dismissible alert | *(Django message text)* | Varies by message tag (success=green, warning=yellow, error=red, info=blue) | When system messages exist | Auto-dismisses after 5 seconds |

---

## 2. LOGIN PAGE

### Form Elements
| Element | Text | Color | Description |
|---------|------|-------|-------------|
| Page heading | **Login to Advisor Portal** | Dark text | Main heading |
| Input field | **Username** | Standard | Username text input |
| Input field | **Password** | Standard | Password text input with toggle |
| Button | **Show/Hide password** (eye icon) | Gray outlined (`btn-outline-secondary`) | Toggles password visibility |
| Checkbox | **Remember me** | Standard | Remember login checkbox |
| Button | **Login** | Blue (`btn-primary`) | Submits the login form |

---

## 3. PROFILE PAGE

### Header Buttons
| Element | Text | Color | Who Sees It | Description |
|---------|------|-------|-------------|-------------|
| Button | **← Back to Dashboard** | Blue outlined (`btn-outline-primary`) | All roles | Returns to role-appropriate dashboard |
| Button | **Logout** | Red outlined (`btn-outline-danger`) | All | Logs out |

### Profile Badges
| Element | Text | Color | When Visible | Description |
|---------|------|-------|-------------|-------------|
| Badge | **[Role name]** (e.g., "Member", "Technician") | Blue (`bg-primary`) | Always | Shows user's role |
| Badge | **[Level display]** (e.g., "Level 1") | Cyan (`bg-info`) | Technicians only | Shows technician experience level |

### Preferences Section
| Element | Text | Color | Description |
|---------|------|-------|-------------|
| Dropdown | **Font Size** (75%–150%) | Standard | Changes application font size |

### Security Section
| Element | Text | Color | Description |
|---------|------|-------|-------------|
| Button | **Change Password** | Blue outlined (`btn-outline-primary`) | Opens password change |

---

## 4. MEMBER DASHBOARD

### Page Header
| Element | Text | Color | Who Sees It | Description |
|---------|------|-------|-------------|-------------|
| Heading | **Member Dashboard** | Dark | Member | Page title |
| Label | **Workshop Code: [CODE]** | Gray muted | Member | Shows user's workshop code |
| Button | **Submit New Case** | Blue (`btn-primary`) | Member | Navigates to case submission form |
| Button | **Notifications** (bell icon) | Cyan outlined (`btn-outline-info`) | Member | Opens notification sidebar |
| Badge | **(unread count)** | Red (`bg-danger`) | When unread notifications exist | Count of unread notifications |
| Button | **Logout** | Red outlined (`btn-outline-danger`) | Member | Logs out |

### Success Banner
| Element | Text | Color | When Visible | Description |
|---------|------|-------|-------------|-------------|
| Alert banner | **Case Submitted Successfully!** | Green (`alert-success`) | After case submission (URL param) | Confirms submission, auto-dismisses |

### Cases on Hold Alert (Collapsible)
| Element | Text | Color | When Visible | Description |
|---------|------|-------|-------------|-------------|
| Alert banner | **You Have Cases on Hold** | Yellow (`alert-warning`) | When member has cases on hold | Lists cases on hold with details |
| Button | **See Case Details** | Yellow (`btn-warning`) | Per held case | Navigates to specific held case |
| Close button | ✕ | Standard | Always on alert | Collapses/closes the alert |

### Draft Cases Reminder Banner
| Element | Text | Color | When Visible | Description |
|---------|------|-------|-------------|-------------|
| Alert banner | **You Have [N] Unsubmitted Draft(s)** | Red (`alert-danger`) | When draft cases exist | Lists unsubmitted drafts |
| Button | **Edit & Submit** | Red outlined (`btn-outline-danger`) | Per draft case | Navigates to draft case detail |

### Notification Offcanvas Sidebar
| Element | Text | Color | When Visible | Description |
|---------|------|-------|-------------|-------------|
| Sidebar header | **Notifications** | White on cyan background | When notifications button clicked | Notification panel title |
| Close button | ✕ | White | Always | Closes notification sidebar |
| Button | **Mark All as Read** | Cyan outlined (`btn-outline-info`) | Always in sidebar | Marks all notifications read |
| Badge | **View Response →** | Blue (`bg-primary`) | On member_update_received notifications | Indicates a response is available |
| Link | **Mark as read** | Blue link | On unread notifications | Marks individual notification read |

### Quick Stats & Filters Card
| Element | Text | Color | Description |
|---------|------|-------|-------------|
| Button | **Hide/Show** | Gray outlined (`btn-outline-secondary`) | Toggles stats section visibility |
| Stat card | **Total** | Purple gradient | Count of all cases |
| Stat card | **Draft** | Purple gradient | Count of draft cases |
| Stat card | **Submitted** | Purple gradient | Count of submitted cases |
| Stat card | **Accepted** | Purple gradient | Count of accepted cases |
| Stat card | **Resubmitted** | Cyan gradient | Count of resubmitted cases |
| Stat card | **Rush** | Red gradient | Count of rush cases |
| Stat card | **Ready** | Green gradient | Count of completed/ready cases |

### Filter Controls (Collapsed by default)
| Element | Text | Color | Description |
|---------|------|-------|-------------|
| Button | **Filters (N)** | Gray outlined (`btn-outline-secondary`) | Expands/collapses filter area |
| Checkboxes | Draft / Submitted / Accepted / On Hold / Completed / Cancelled | Standard | Multi-select status filter |
| Dropdown | **Urgency** (All / Standard / Rush) | Standard | Urgency filter |
| Text input | **Search** | Standard | Search by Case ID or Employee Name |
| Button | **Filter** | Blue (`btn-primary`) | Applies filters |
| Button | **Reset** | Gray outlined (`btn-outline-secondary`) | Clears all filters |
| Dropdown | **Columns** | Gray outlined (`btn-outline-secondary`) | Shows/hides table columns |
| Badge | **(N hidden)** | Yellow (`bg-warning`) | When columns are hidden | Count of hidden columns |

### Cases Table
| Element | Text | Color | When Visible | Description |
|---------|------|-------|-------------|-------------|
| Column headers | Code, Employee Name, Reports, Urgency, Submitted, Due Date, Completed, Status, Credit, Actions | Standard | Always | Sortable column headers (clickable) |
| Badge | **Rush** | Red (`bg-danger`) | When case urgency = rush | Urgency indicator |
| Badge | **Normal** | Gray (`bg-secondary`) | When case urgency = normal | Urgency indicator |
| Badge | **Resubmitted #N** | Cyan (`bg-info`) | When case is resubmitted and completed | Resubmission count indicator |
| Button | **View** | Blue outlined (`btn-outline-primary`) | Always per row | Opens case detail page |
| Badge | **(N)** on View button | Red (`bg-danger`) | When unread messages exist | Unread message count |

### Cases Table — Status Column Badges (Member View)
| Badge Text | Color | Meaning |
|------------|-------|---------|
| **Draft** | Red (`bg-danger`) | Case saved but not yet submitted |
| **Submitted** | Gray (`bg-secondary`) | Case submitted, awaiting initial review |
| **Resubmitted** | Cyan (`bg-info`) | Case resubmitted after revisions |
| **Accepted** | Blue (`bg-primary`) | Case accepted by Benefits Team |
| **On Hold** | Red (`bg-danger`) | Case paused, awaiting member input |
| **Completed** | Green (`bg-success`) | Case finished and released to member |
| **Cancelled** | Red (`bg-danger`) | Case was cancelled |

### Empty State
| Element | Text | Color | When Visible | Description |
|---------|------|-------|-------------|-------------|
| Message | **No cases found.** | Gray muted | When no cases match filters | Empty state message |
| Button | **Submit Your First Case** | Blue (`btn-primary`) | When no cases exist at all | Navigates to case submission |

---

## 5. SUBMIT NEW CASE PAGE

### Header
| Element | Text | Color | Description |
|---------|------|-------|-------------|
| Heading | **Submit New Case** | Blue (#0066cc) | Page title |
| Button | **← Back to Dashboard** | Gray outlined (`btn-outline-secondary`) | Returns to member dashboard |

### Form Fields
| Element | Text | Description |
|---------|------|-------------|
| Read-only input | **Advisor** (auto-filled) | Currently logged-in advisor's name |
| Read-only input | **Workshop Code** (auto-filled) | Advisor's workshop code |
| Text input | **First Name** (required) | Federal employee's first name |
| Text input | **Last Name** (required) | Federal employee's last name |
| Date input | **Due Date** (required) | Case due date (default: 7 days out) |
| Dropdown | **Number of Scenarios** (1–5) | How many report scenarios requested |
| Textarea | **Notes for the Benefits Team** | Optional special instructions |
| File upload area | **Click to upload documents or drag and drop here** | Drag-and-drop document upload zone |

### Rush Alert
| Element | Text | Color | When Visible | Description |
|---------|------|-------|-------------|-------------|
| Alert | **⚠️ Rushed Request** — $20 fee warning | Red border (`alert-danger`) | When due date < 7 days from today | Warns about rush fee |

### Form Action Buttons
| Element | Text | Color | Description |
|---------|------|-------|-------------|
| Button | **Cancel** | Gray (`btn-secondary`) | Returns to dashboard without saving |
| Button | **Save as Draft** | Blue (`btn-primary`) | Saves case as draft (not submitted) |
| Button | **Submit** | Green (`btn-success`) | Submits case for processing |

### File List
| Element | Text | Color | Description |
|---------|------|-------|-------------|
| Button | **Remove** (per file) | Red | Removes uploaded file from list |

---

## 6. TECHNICIAN DASHBOARD

### Page Header
| Element | Text | Color | Who Sees It | Description |
|---------|------|-------|-------------|-------------|
| Heading | **Benefits Technician Dashboard** | Dark | Technician | Page title |
| Dropdown button | **Management** | Blue outlined (`btn-outline-primary`) | Technician | Opens management menu |
| Dropdown item | **Workshop Delegates** | Dark | All technicians | Manage workshop delegates |
| Dropdown item | **Manage Users** | Dark | Administrators only | User management (admin only) |
| Button | **Logout** | Red outlined (`btn-outline-danger`) | Technician | Logs out |

### Quick Stats
| Stat Card | Color | Description |
|-----------|-------|-------------|
| **Total** | Blue gradient | Total cases |
| **Submitted** | Blue gradient | Awaiting initial review |
| **Accepted** | Blue gradient | Accepted for processing |
| **Resubmitted** | Cyan gradient | Resubmitted by member |
| **Pending** | Blue gradient | Awaiting quality review |
| **Needs Revision** | Yellow gradient | Returned from QA review (only shows if count > 0) |
| **Completed** | Blue gradient | Finished cases |
| **Rush** | Red gradient | Rush priority cases |

### View Toggle Buttons
| Element | Text | Color | Description |
|---------|------|-------|-------------|
| Button | **All Cases** | Blue outlined (`btn-outline-primary`), solid when active | Shows all cases |
| Button | **My Cases** | Blue outlined (`btn-outline-primary`), solid when active | Shows only cases assigned to current user |

### Filter Controls (same pattern as Member)
| Element | Text | Color | Description |
|---------|------|-------|-------------|
| Button | **Filters (N)** | Gray outlined | Expands filter area |
| Checkboxes | Submitted / Accepted / Pending Review / On Hold / Completed | Standard | Status filter |
| Dropdown | **Urgency** | Standard | Normal/Rush filter |
| Dropdown | **Tier** | Standard | Tier 1/2/3 filter |
| Dropdown | **Sort By** | Standard | Various sort options |
| Text input | **Search** | Standard | Free text search |
| Button | **Filter** | Blue (`btn-primary`) | Apply filters |
| Button | **Reset** | Gray outlined (`btn-outline-secondary`) | Clear filters |
| Dropdown | **Columns** | Gray outlined | Column visibility toggle |

### Cases Table — Special Badges
| Badge Text | Color | When Visible | Meaning |
|------------|-------|--------------|---------|
| **Our Error** | Red (`bg-danger`) | When member flagged ProFeds error | High-priority modification |
| **New Info** | Yellow (`bg-warning`) | When member provided updates | New information available |

### Cases Table — Status Badges (Technician View)
| Badge Text | Color | Meaning |
|------------|-------|---------|
| **Submitted** | Gray (`bg-secondary`) | Awaiting initial review |
| **Resubmitted** | Yellow (`bg-warning`) | Resubmitted by member |
| **Accepted** | Blue (`bg-primary`) | Case accepted |
| **Needs Revision** | Yellow (`bg-warning`) with ⚠ icon | Returned from quality review |
| **Pending Review** | Cyan (`bg-info`) | Awaiting senior tech review |
| **On Hold** | Red (`bg-danger`) | Paused for member input |
| **Needs Resubmission** | Yellow (`bg-warning`) | Member needs to resubmit |
| **Completed** | Green (`bg-success`) | Completed and released |
| **Scheduled** | Red (`bg-danger`) | Completed but release date is in future |
| **Working** | Cyan (`bg-info`) | Currently being processed |

### Cases Table — Actions
| Element | Text | Color | Description |
|---------|------|-------|-------------|
| Edit icon (pencil) | *(icon only)* | Blue link | Opens reassign modal for that case |
| Button | **View** | Blue outlined (`btn-outline-primary`) | Opens case detail |
| Badge on View | **(N)** | Red (`bg-danger`) | Unread message count |

### Reassignment Modal (per case)
| Element | Text | Color | Description |
|---------|------|-------|-------------|
| Dropdown | **Assign To** | Standard | Select technician from list |
| Textarea | **Reason (optional)** | Standard | Reason for reassignment |
| Button | **Cancel** | Gray (`btn-secondary`) | Closes modal |
| Button | **Reassign** | Blue (`btn-primary`) | Confirms reassignment |

---

## 7. MANAGER DASHBOARD

### Page Header
| Element | Text | Color | Description |
|---------|------|-------|-------------|
| Heading | **Manager Dashboard** | Dark | Page title |
| Subtitle | **Read-Only Analytics & Reporting** | Gray muted | Indicates read-only access |
| Button | **Logout** | Red outlined (`btn-outline-danger`) | Logs out |

### Quick Stats
| Stat Card | Color | Description |
|-----------|-------|-------------|
| **Total** | Blue gradient | Total cases |
| **Completed** | Blue gradient | Finished cases |
| **Rate** (%)| Blue gradient | Completion rate percentage |
| **Members** | Blue gradient | Total member count |
| **Pending** | Blue gradient | Pending review count |
| **Resubmitted** | Cyan gradient | Resubmitted count |
| **Rush** | Red gradient | Rush count |

### Filter Controls
Same pattern as Technician Dashboard, plus additional filters:
| Element | Text | Description |
|---------|------|-------------|
| Dropdown | **Date Range** | Today / This Week / This Month / All Time |
| Date input | **From Date** | Custom date range start |
| Date input | **To Date** | Custom date range end |
| Dropdown | **Member** | Filter by specific member |
| Dropdown | **Technician** | Filter by specific technician |

### Management Buttons
| Element | Text | Color | Description |
|---------|------|-------|-------------|
| Button | **Reports** | Cyan outlined (`btn-outline-info`) | View analytics reports |
| Button | **Audit** | Cyan outlined (`btn-outline-info`) | View audit log |
| Button | **Credit Trail** | Yellow outlined (`btn-outline-warning`) | Credit audit trail report |
| Button | **Refresh** | Cyan outlined (`btn-outline-info`) | Refreshes the dashboard |

### Table Header Badge
| Element | Text | Color | Description |
|---------|------|-------|-------------|
| Badge | **Read-Only** | Cyan (`bg-info`) | Indicates no edit actions available |

### Cases Table
Same columns and status badges as Technician Dashboard. Actions column has **View** button only (no delete).

---

## 8. ADMINISTRATOR DASHBOARD

### Page Header
| Element | Text | Color | Description |
|---------|------|-------|-------------|
| Heading | **Administrator Dashboard** | Dark | Page title |
| Subtitle | **Full System Visibility & Control** | Gray muted | Indicates full access |
| Button | **Logout** | Red outlined (`btn-outline-danger`) | Logs out |

### Quick Stats
| Stat Card | Color | Description |
|-----------|-------|-------------|
| **Total** | Blue gradient | Total cases |
| **Members** | Blue gradient | Total member count |
| **Techs** | Blue gradient | Total technician count |
| **Review** | Blue gradient | Cases requiring review |
| **Resubmitted** | Cyan gradient | Resubmitted count |
| **Unassigned** | Blue gradient | Unassigned cases |
| **Rush** | Red gradient | Rush priority count |

### Toggle Buttons
| Element | Text | Color | Description |
|---------|------|-------|-------------|
| Button | **Stats** | Gray outlined (`btn-outline-secondary`) | Show/hide stats section |
| Button | **Filters** | Gray outlined (`btn-outline-secondary`) | Show/hide filter section |

### Filter Controls
Same as Manager Dashboard filters, plus identical **Tier**, **Date Range**, **Member**, **Technician** dropdowns.

### Management Buttons
| Element | Text | Color | Description |
|---------|------|-------|-------------|
| Button | **Users** | Cyan outlined (`btn-outline-info`) | Manage user accounts |
| Button | **Settings** | Cyan outlined (`btn-outline-info`) | System settings |
| Button | **Reports** | Cyan outlined (`btn-outline-info`) | View reports |
| Button | **Audit** | Cyan outlined (`btn-outline-info`) | View full audit log |
| Button | **Credit Trail** | Yellow outlined (`btn-outline-warning`) | Credit audit trail |

### Cases Table — Additional Admin Columns
Beyond the standard columns, admins also see:
- **Release Date** — scheduled or actual release date
- **Reports** — number of reports requested
- **Assigned To** — technician badge
- **Scheduled** — date case is scheduled
- **Tier** — tier badge (dark)
- **Reviewed By** — reviewer badge (gray)
- **Notes** — internal note count
- **On-Time/Late** — on-time status
- **Finalized** — date case was finalized

### Admin Table — Additional Badges
| Badge Text | Color | When Visible | Meaning |
|------------|-------|--------------|---------|
| **Our Error** | Red (`bg-danger`) | ProFeds error flagged | Modification caused by internal error |
| **New Info** | Yellow (`bg-warning`) | Member provided updates | New member information |
| **Unassigned** | Light gray (`bg-light`) | No technician assigned | Case needs assignment |
| **On-Time** | Green (`bg-success`) | Completed on or before due date | Timely completion |
| **Late** | Red (`bg-danger`) | Completed after due date | Overdue completion |
| **[Tech Name]** | Cyan (`bg-info`) | Assigned technician | Shows assigned tech |
| **[Reviewer Name]** | Gray (`bg-secondary`) | Case has been reviewed | Shows reviewer |
| **[Tier display]** | Dark (`bg-dark`) | When tier is assigned | Tier level indicator |
| **[Scheduled date]** | Cyan (`bg-info`) | Scheduled release date | Release date indicator |

### Cases Table — Action Buttons
| Element | Text | Color | Description |
|---------|------|-------|-------------|
| Button | **View** | Blue outlined (`btn-outline-primary`) | Opens case detail |
| Button | **Delete** | Red outlined (`btn-outline-danger`) | Goes to delete confirmation page |

### Empty State
| Element | Text | Color | Description |
|---------|------|-------|-------------|
| Message | **No cases found matching your filters.** | Gray muted | No results |
| Button | **View All Cases** | Blue (`btn-primary`) | Clears filters |

---

## 9. CASE DETAIL PAGE

This is the largest and most complex page. Elements vary heavily by user role and case status.

### Breadcrumb Navigation
| Element | Text | Who Sees It | Description |
|---------|------|-------------|-------------|
| Link | **Dashboard** | All | Returns to role-appropriate dashboard |
| Text | **[Employee Name]** | All | Current case employee name |

### Header Status Badge (Large)
Displayed prominently next to employee name. Size: `fs-5` (large).

**Member sees:**
| Badge Text | Color | When Visible |
|------------|-------|--------------|
| **Draft** | Red (`bg-danger`) | Status = draft |
| **Submitted** | Gray (`bg-secondary`) | Status = submitted |
| **Resubmitted** | Cyan (`bg-info`) | Status = resubmitted |
| **Accepted** | Blue (`bg-primary`) | Status = accepted, pending_review, or completed-but-unreleased |
| **On Hold** | Red (`bg-danger`) | Status = hold |
| **Completed** | Green (`bg-success`) | Status = completed AND released |
| **Cancelled** | Red (`bg-danger`) | Status = cancelled |

**Technician sees:**
| Badge Text | Color | When Visible |
|------------|-------|--------------|
| **Draft** | Red (`bg-danger`) | Status = draft |
| **Submitted** | Gray (`bg-secondary`) | Status = submitted |
| **Resubmitted** | Cyan (`bg-info`) | Status = resubmitted |
| **Accepted** | Blue (`bg-primary`) | Status = accepted |
| **Pending Review** | Yellow (`bg-warning`) | Status = pending_review |
| **On Hold** | Red (`bg-danger`) | Status = hold |
| **Completed** | Green (`bg-success`) | Status = completed |
| **Cancelled** | Red (`bg-danger`) | Status = cancelled |

**Admin/Manager sees:** Same as Technician.

### Header Buttons — Member
| Element | Text | Color | When Visible | Description |
|---------|------|-------|--------------|-------------|
| Button | **Edit Case** | Yellow (`btn-warning`) | Status not in: submitted, draft, completed, hold, cancelled | Edit case details |
| Button | **← Back to Dashboard** | Blue outlined (`btn-outline-primary`) | Always | Return to member dashboard |
| Button | **Request a Mod** | Cyan outlined (`btn-outline-info`) | Completed case with release date, no existing mod, within 60 days | Opens modification request modal |
| Button | **Ask a Question** | Green outlined (`btn-outline-success`) | Completed case with release date | Opens question modal |
| Button | **Submit Case** | Green (`btn-success`) | Draft cases owned by member | Submits draft case |
| Button | **Edit Draft** | Yellow (`btn-warning`) | Draft cases owned by member | Opens edit page |
| Button | **Delete Draft** | Red outlined (`btn-outline-danger`) | Draft cases owned by member | Deletes draft (with confirmation) |
| Button | **Cancel Case** | Red outlined (`btn-outline-danger`) | Active cases (submitted/accepted/hold/pending_review/resubmitted/needs_resubmission) | Opens cancellation request modal |

### Header Buttons — Technician
| Element | Text | Color | When Visible | Description |
|---------|------|-------|--------------|-------------|
| Button | **← Back to Dashboard** | Blue outlined (`btn-outline-primary`) | Always | Return to tech dashboard |
| Badge | **You own this case** ✓ | Green (`bg-success`) | Case assigned to current tech | Ownership indicator |
| Button | **Reassign** | Yellow outlined (`btn-outline-warning`) | Case assigned to current tech | Opens reassign modal |
| Button | **Take Ownership** | Green outlined (`btn-outline-success`) | Accepted/hold/pending_review cases NOT assigned to current tech | Claims case ownership |

### Header Buttons — Manager
| Element | Text | Color | When Visible | Description |
|---------|------|-------|--------------|-------------|
| Button | **← Back to Dashboard** | Blue outlined (`btn-outline-primary`) | Always | Return to manager dashboard |
| Button | **Reassign** | Yellow outlined (`btn-outline-warning`) | Accepted/hold/pending_review cases | Opens reassign modal |

### Header Buttons — Administrator
| Element | Text | Color | When Visible | Description |
|---------|------|-------|--------------|-------------|
| Button | **← Back to Dashboard** | Blue outlined (`btn-outline-primary`) | Always | Return to admin dashboard |
| Button | **Reassign** | Yellow outlined (`btn-outline-warning`) | Accepted/hold/pending_review cases | Opens reassign modal |
| Button | **Take Ownership** | Red (`btn-danger`) | When admin is not the owner | Admin forcefully claims case |
| Badge | **You own this case** ✓ | Green (`bg-success`) | Admin is the assigned owner | Ownership indicator |

### Revision Requested Banner (Technician only)
| Element | Text | Color | When Visible | Description |
|---------|------|-------|--------------|-------------|
| Alert banner | **Revisions Requested by Senior Technician** | Yellow (`alert-warning`) | review_status = revisions_requested, assigned tech viewing | Shows reviewer feedback and prompts revision |

### Pending Change Request Banner (Tech/Manager/Admin)
| Element | Text | Color | When Visible | Description |
|---------|------|-------|--------------|-------------|
| Alert banner | **Member Cancellation Request** / **Member Due Date Extension Request** / **Member Change Request** | Yellow (`alert-warning`) | Pending change requests exist | Shows member's request details |
| Button | **Approve** | Green (`btn-success`) | On pending request | Opens approve modal |
| Button | **Deny** | Red (`btn-danger`) | On pending request | Opens deny modal |

### Member Information Card
| Element | Text | Description |
|---------|------|-------------|
| Label | **Member:** | Member name and email |
| Label | **Workshop Code:** | Workshop code |

### Linked Cases Section
| Element | Text | Color | When Visible | Description |
|---------|------|-------|--------------|-------------|
| Badge | **Modification** | Cyan (`bg-info`) | Case has original case | Indicates this is a modification |
| Button | **← [Original Employee Name]** | Cyan outlined (`btn-outline-info`) | Has original case | Link to original case |
| Badge | **Resubmissions** | Yellow (`bg-warning`) | Case has resubmitted children | Lists modifications |
| Button | **→ [Modified Employee Name]** | Yellow outlined (`btn-outline-warning`) | Per resubmission | Link to resubmitted case |

### ProFeds Error Alert (Tech/Manager/Admin only)
| Element | Text | Color | When Visible | Description |
|---------|------|-------|--------------|-------------|
| Alert | **ProFeds Error Flagged** | Red (`alert-danger`) | Case has `has_profeds_error` flag | Warns of internal error case |

### Case Information Card
| Element | Text | Color | When Visible | Description |
|---------|------|-------|--------------|-------------|
| Button | **Edit Details** | Blue outlined (`btn-outline-primary`) | Tech/Manager/Admin, case in draft/submitted/accepted/pending_review | Opens Edit Case Details modal |
| Badge | **Rush** | *(no explicit bg class)* | Urgency = rush | Rush urgency indicator |
| Badge | **Normal** | Gray (`bg-secondary`) | Urgency = normal | Standard urgency |
| Button | ✏ (pencil icon next to Credits) | Gray outlined (`btn-outline-secondary`) | Tech/Admin/Manager on accepted/pending_review/completed cases | Opens Credit Adjustment modal |

### Case Information — Status Badges (Within Case Info Card)
| Badge Text | Color | Role View | When Visible |
|------------|-------|-----------|--------------|
| **Draft** | Gray (`bg-secondary`) | All | Status = draft |
| **Submitted** | Blue (`bg-primary`) | All | Status = submitted |
| **Accepted** | Green (`bg-success`) | All | Status = accepted |
| **Pending Review** | Yellow (`bg-warning`) | All | Status = pending_review |
| **Hold** | Red (`bg-danger`) | Member | Status = hold |
| **Completed** | Green (`bg-success`) | All | Status = completed |
| **Working** | Cyan (`bg-info`) | Technician | Case assigned to current tech |

### Member Notes Section (Draft only)
| Element | Text | Color | When Visible | Description |
|---------|------|-------|--------------|-------------|
| Button | **Add Notes** | Cyan (`btn-info`) | Draft, member view, no notes yet | Opens note editing area |

### Submitted Documents Card
| Element | Text | Color | When Visible | Description |
|---------|------|-------|--------------|-------------|
| Badge | **N Total** | Cyan (`bg-info`) | Always | Document count |
| Button | **Upload Document** | Blue (`btn-primary`) | Member on active cases | Opens upload modal |
| Button | ⬇ (download icon) | Blue outlined (`btn-outline-primary`) | Per document with file | Downloads document |
| Badge | **No file** | Yellow (`bg-warning`) | Document without file | Indicates missing file |
| Button | 🗑 (trash icon) | Red outlined (`btn-outline-danger`) | Admin/Manager, status ≠ submitted | Deletes document |

### For members with no documents:
| Element | Text | Color | When Visible | Description |
|---------|------|-------|--------------|-------------|
| Button | **Upload Documents** | Blue (`btn-primary`) | Member with zero documents | Opens upload modal |

### Additional Documents Card (Tech/Admin/Manager only)
| Element | Text | Color | When Visible | Description |
|---------|------|-------|--------------|-------------|
| Button | **Upload Document** | Blue (`btn-primary`) | Can edit case | Opens upload modal |
| Button | ⬇ (download icon) | Blue outlined (`btn-outline-primary`) | Per document | Downloads document |

### Reports & Resources Card
| Element | Text | Color | When Visible | Description |
|---------|------|-------|--------------|-------------|
| Badge | **N** (report count) | Cyan (`bg-info`) | Reports exist | Report count |
| Button | **Upload Report** | Blue (`btn-primary`) | Can upload reports (tech) | Opens upload report modal |
| Badge | **[Report Status]** | Gray (`bg-secondary`) | Per report | Report status display |
| Button | ⬇ (download icon) | Blue outlined (`btn-outline-primary`) | Per report with file | Downloads report |

### Technical Notes Card
| Element | Text | Color | When Visible | Description |
|---------|------|-------|--------------|-------------|
| Button | **Download as PDF** | Cyan (`btn-info`) | Report notes exist | Downloads notes as PDF |

### Internal Notes Card (Tech/Admin/Manager only)
| Element | Text | Color | When Visible | Description |
|---------|------|-------|--------------|-------------|
| Badge | **N** (note count) | Yellow (`bg-warning`) | Notes exist | Note count |
| Badge | **Internal** | Red (`bg-danger`) | Per internal note | Marks note as internal |
| Button | 🗑 (trash icon) | Red outlined (`btn-outline-danger`) | Note author or admin | Deletes note |
| Button | **Add Internal Note** | Gray (`btn-secondary`) | Always for tech/admin/manager | Adds a new internal note |

### Case Chat Card (Right Column)
| Element | Text | Color | When Visible | Description |
|---------|------|-------|--------------|-------------|
| Badge | **N** (message count) | Cyan (`bg-info`) | Always | Total message count |
| Alert | **Messaging is available after you submit this case.** | Yellow (`alert-warning`) | Draft cases, member view | Indicates chat is unavailable |
| Badge | **Member** | Cyan (`bg-info`) | Per member message | Author role badge |
| Badge | **Technician** | Green (`bg-success`) | Per technician message | Author role badge |
| Button | **Send Message** | Blue (`btn-primary`) | Non-draft cases | Sends a chat message |

### Hold Notice Card (Member only)
| Element | Text | Color | When Visible | Description |
|---------|------|-------|--------------|-------------|
| Card | **Your Case Is on Hold** | Yellow border + header | Case status = hold, member viewing | Shows hold reason and instructions |

### Member Timeline Card (Member only)
Shows timeline event badges:
| Badge Text | Color | Event Type |
|------------|-------|------------|
| **Submitted** | Cyan (`bg-info`) | Case submitted |
| **Resubmitted** | Cyan (`bg-info`) | Case resubmitted |
| **Accepted** | Green (`bg-success`) | Case accepted |
| **Put on Hold** | Yellow (`bg-warning`) | Case held |
| **Resumed** | Cyan (`bg-info`) | Case resumed |
| **Completed** | Green (`bg-success`) | Case completed |
| **Document Uploaded** | Cyan (`bg-info`) | Member uploaded document |

### Initial Case Review Card (Tech/Admin/Manager — Submitted cases only)
| Element | Text | Color | When Visible | Description |
|---------|------|-------|--------------|-------------|
| Checkboxes | Fact Finder / Pay Stub / Social Security / TSP statement | Standard | Submitted, not yet accepted | Document verification checklist |
| Dropdown | **Assign Tier** (1/2/3) | Standard | During review | Case complexity tier |
| Dropdown | **Assign Credit Value** (0.0–3.0) | Standard | During review | Credit value assignment |
| Dropdown | **Assign Tech** | Standard | During review | Assign technician |
| Textarea | **Notes** | Standard | During review | Override notes |
| Button | **Accept Case** | Green (`btn-success`) | During review | Accepts the case |
| Button | **Put on Hold** | Yellow (`btn-warning`) | During review | Puts case on hold |

### Case Activity Card (Tech/Admin/Manager — Event Log)
Timeline event badges in the event log table:
| Badge Text | Color | Event Type |
|------------|-------|------------|
| **Submitted** | Cyan (`bg-info`) | Case submitted |
| **Resubmitted** | Cyan (`bg-info`) | Case resubmitted |
| **Accepted** | Green (`bg-success`) | Case accepted |
| **Assigned** | Gray (`bg-secondary`) | Case assigned |
| **Reassigned** | Purple (#6f42c1) | Case reassigned |
| **Tier Changed** | Gray (`bg-secondary`) | Tier level changed |
| **Put on Hold** | Yellow (`bg-warning`) | Case held |
| **Resumed** | Cyan (`bg-info`) | Case resumed |
| **Completed** | Green (`bg-success`) | Case completed |
| **Marked Incomplete** | Yellow (`bg-warning`) | Returned to active |
| **Review Approved** | Green (`bg-success`) | QA approved |
| **Revisions Requested** | Yellow (`bg-warning`) | QA returned |
| **Corrections Applied** | Cyan (`bg-info`) | Reviewer fixed |
| **Rejected** | Red (`bg-danger`) | Case rejected |
| **Cancelled** | Dark (`bg-dark`) | Case cancelled |
| **Ownership Claimed** | Blue (`bg-primary`) | Tech claimed ownership |
| **Admin Ownership** | Red (`bg-danger`) | Admin took ownership |
| **Doc Uploaded** | Cyan (`bg-info`) | Document uploaded |

### Acceptance Details (Expandable)
| Element | Text | Color | When Visible | Description |
|---------|------|-------|--------------|-------------|
| Link | **View Acceptance Details** | Blue link | Acceptance details exist | Expands acceptance info |
| Badge | **Yes** | Green (`bg-success`) | Docs verified = yes | Documents verified |
| Badge | **No** | Yellow (`bg-warning`) | Docs verified = no | Documents not fully verified |

### Notification Status Alerts (Completed cases)
| Alert Text | Color | When Visible | Meaning |
|------------|-------|--------------|---------|
| **Member Notified** — Email sent [date] | Green (`alert-success`) | Email has been sent | Confirmation of notification |
| **Notification Scheduled** — Will be sent [date] | Cyan (`alert-info`) | Email scheduled | Future notification |
| **No Notification Scheduled** | Yellow (`alert-warning`) | No email set | Warning |

### Actions Card (Tech/Admin/Manager — Right Column)
| Element | Text | Color | When Visible | Description |
|---------|------|-------|--------------|-------------|
| **Quality Review Actions (Level 2/3 reviewing another tech's work):** | | | | |
| Alert | **Quality Review Required** | Cyan (`alert-info`) | Pending review, L2/L3 tech, not assigned to them | Review prompt |
| Button | **Approve Case** | Green (`btn-success`) | During quality review | Opens approve review modal |
| Button | **Request Revisions** | Yellow (`btn-warning`) | During quality review | Opens revisions modal |
| Button | **Fix & Complete Myself** | Red (`btn-danger`) | During quality review | Opens corrections modal |
| **Standard Tech Actions (case owner):** | | | | |
| Button | **Mark as Incomplete** | Gray (`btn-secondary`) | Completed case, assigned to tech | Reverts case to active |
| Button | **Change Release Date** | Cyan (`btn-info`) | Completed but unreleased, has scheduled date | Opens date change modal |
| Button | **Resume from Hold** | Cyan (`btn-info`) | Case on hold, assigned to tech | Opens resume modal |
| Button | **Mark as Completed** | Green (`btn-success`) | Hold or accepted cases, assigned to tech | Opens release options |
| Alert | **Awaiting Quality Review** | Cyan (`alert-info`) | Pending review, L1 tech who submitted it | Informational |
| Button | **Submit for Review** | Blue (`btn-primary`) | L1 tech, accepted cases | Submits for senior review |
| Button | **Put on Hold** | Yellow (`btn-warning`) | Accepted cases, any tech level | Opens hold modal |
| Button | **Mark as Completed** | Green (`btn-success`) | L2/L3 tech, accepted cases | Direct completion |
| **Admin/Manager — Not owner:** | | | | |
| Button | **Put on Hold** | Yellow (`btn-warning`) | Admin/Manager on submitted/accepted cases | Hold without ownership |

### Floating Technical Notes Window (Tech/Admin/Manager)
| Element | Text | Color | When Visible | Description |
|---------|------|-------|--------------|-------------|
| Window | **Technical Notes to Member** | Blue header | Accepted/pending_review/completed/hold cases | Floating draggable rich-text editor |
| Button | **—** (minimize) | White on blue | Window is open | Minimizes notes window |
| Button | **✕** (close) | White on blue | Window is open | Minimizes notes window |
| Button | **Notes** (floating) | Blue outlined (`btn-outline-primary`) | Window is minimized | Restores notes window |

---

## 10. DELETE CASE CONFIRMATION PAGE

| Element | Text | Color | Description |
|---------|------|-------|-------------|
| Heading | **Delete Case — Permanent Action** | White on red header | Warning heading |
| Alert | **⚠️ Warning: This action cannot be undone.** | Red (`alert-danger`) | Permanent deletion warning |
| Button | **Cancel — Keep This Case** | Gray (`btn-secondary`) large | Returns to dashboard |
| Button | **Yes, Permanently Delete This Case** | Red (`btn-danger`) large | Deletes case with JS confirmation prompt |

---

## 11. MASTER STATUS BADGE REFERENCE

Complete reference of all status badges across the application:

| Status Value | Member View Text | Member Color | Tech/Admin View Text | Tech/Admin Color |
|-------------|-----------------|--------------|---------------------|-----------------|
| `draft` | Draft | Red (`bg-danger`) | Draft | Red (`bg-danger`) |
| `submitted` | Submitted | Gray (`bg-secondary`) | Submitted | Gray (`bg-secondary`) |
| `resubmitted` | Resubmitted | Cyan (`bg-info`) | Resubmitted | Yellow (`bg-warning`) on dashboards, Cyan on detail |
| `accepted` | Accepted | Blue (`bg-primary`) | Accepted | Blue (`bg-primary`) |
| `pending_review` | Accepted *(hidden from member)* | Blue (`bg-primary`) | Pending Review | Cyan (`bg-info`) on dashboards, Yellow (`bg-warning`) on detail |
| `hold` | On Hold | Red (`bg-danger`) | On Hold | Red (`bg-danger`) |
| `needs_resubmission` | *(not shown)* | — | Needs Resubmission | Yellow (`bg-warning`) |
| `completed` (released) | Completed | Green (`bg-success`) | Completed | Green (`bg-success`) |
| `completed` (scheduled) | Accepted *(hidden)* | Blue (`bg-primary`) | Scheduled | Red (`bg-danger`) |
| `completed` (not released) | Accepted *(hidden)* | Blue (`bg-primary`) | Working | Cyan (`bg-info`) |
| `cancelled` | Cancelled | Red (`bg-danger`) | *(not shown on tech dashboard)* | — |

### Urgency Badges
| Value | Text | Color |
|-------|------|-------|
| `rush` | Rush | Red (`bg-danger`) |
| `normal` | Normal | Gray (`bg-secondary`) |

### Other Informational Badges
| Badge Text | Color | Context | Meaning |
|------------|-------|---------|---------|
| **Our Error** | Red (`bg-danger`) | Dashboard table row | ProFeds error flagged by member |
| **New Info** | Yellow (`bg-warning`) | Dashboard table row | Member provided new information |
| **Resubmitted #N** | Cyan (`bg-info`) | Member dashboard, completed column | Case has been resubmitted N times |
| **Modification** | Cyan (`bg-info`) | Case detail linked cases | This case is a modification of another |
| **Resubmissions** | Yellow (`bg-warning`) | Case detail linked cases | This case has child modifications |
| **Internal** | Red (`bg-danger`) | Internal notes | Note is internal-only |
| **Member** | Cyan (`bg-info`) | Chat messages | Message from member |
| **Technician** | Green (`bg-success`) | Chat messages | Message from technician |
| **You own this case** ✓ | Green (`bg-success`) | Case detail header | Ownership indicator |
| **Read-Only** | Cyan (`bg-info`) | Manager dashboard header | Manager cannot modify |
| **Unassigned** | Light (`bg-light`) | Admin dashboard table | Case has no tech |
| **On-Time** | Green (`bg-success`) | Admin dashboard | Completed before due date |
| **Late** | Red (`bg-danger`) | Admin dashboard | Completed after due date |
| **(N)** on View button | Red (`bg-danger`) | Dashboard tables | Unread message count |
| **(N)** on Notifications button | Red (`bg-danger`) | Member dashboard header | Unread notification count |
| **(N hidden)** on Columns button | Yellow (`bg-warning`) | All dashboards | Hidden column count |

---

## 12. MASTER MODAL DIALOG REFERENCE

### Reassign Case Modal
- **Trigger:** "Reassign" button (yellow outlined) on case detail
- **Who can trigger:** Technician (own case), Manager, Administrator
- **Header:** Yellow background, "Reassign Case" title
- **Fields:** Technician dropdown, Reason textarea
- **Buttons:** Cancel (gray), Reassign (yellow)

### Admin Take Ownership Modal
- **Trigger:** "Take Ownership" button (red) on case detail
- **Who can trigger:** Administrator only
- **Header:** Red background, "Take Case Ownership" title
- **Content:** Shows current owner warning or "no current owner" info
- **Buttons:** Cancel (gray), Take Ownership (red)

### Upload Report Modal
- **Trigger:** "Upload Report" button on Reports card
- **Who can trigger:** Technician (case owner)
- **Fields:** Report Number dropdown, File input, Notes textarea
- **Buttons:** Cancel (gray), Upload Report (blue)

### Upload Document Modal
- **Trigger:** "Upload Document" button on Documents card
- **Who can trigger:** Member (active cases), Technician
- **Fields:** File input, Notes textarea
- **Buttons:** Cancel (gray), Upload Document (blue)

### Add Internal Note Modal
- **Trigger:** "Add Internal Note" button
- **Who can trigger:** Technician, Manager, Administrator
- **Fields:** Note textarea
- **Buttons:** Cancel (gray), Add Note (blue)

### Credit Adjustment Modal
- **Trigger:** Pencil icon next to Credits on case info card
- **Who can trigger:** Technician, Manager, Administrator
- **Fields:** Credit Value dropdown (0.0–3.0), Reason textarea
- **Buttons:** Cancel (gray), Save Credit Adjustment (blue)

### Edit Case Details Modal
- **Trigger:** "Edit Details" button on Case Information card header
- **Who can trigger:** Technician, Manager, Administrator (cases in draft/submitted/accepted/pending_review)
- **Sections:** Employee name fields, Due date, Assigned technician dropdown, Edit reason textarea, Send notification checkbox
- **Buttons:** Cancel (gray), Save Changes (blue)

### Put on Hold Modal
- **Trigger:** "Put on Hold" button (yellow)
- **Who can trigger:** Technician, Manager, Administrator
- **Header:** Yellow background, "Put Case on Hold" title
- **Fields:** Message to Member textarea (required)
- **Buttons:** Cancel (gray), Place on Hold (yellow)

### Resume from Hold Modal
- **Trigger:** "Resume from Hold" button (cyan)
- **Who can trigger:** Technician (case owner)
- **Header:** Cyan background, "Resume Case from Hold" title
- **Fields:** Reason for Resuming textarea (required)
- **Buttons:** Cancel (gray), Resume Processing (cyan)

### Release Options Modal (Mark as Completed)
- **Trigger:** "Mark as Completed" button → validation → modal opens
- **Who can trigger:** Technician (L2/L3 owner), Reviewer
- **Header:** Blue background, "When should this case be released to the member?"
- **Options:** Release Now (radio), Schedule Release (radio with date/time pickers)
- **Buttons:** Cancel (gray), Confirm Release (blue)

### Change Release Date Modal
- **Trigger:** "Change Release Date" button (cyan)
- **Who can trigger:** Technician (case owner), completed but unreleased cases
- **Header:** Cyan background, "Change Release Date" title
- **Options:** Reschedule (radio with date/time), Release Now (radio)
- **Buttons:** Cancel (gray), Confirm (cyan)

### Approve Case Review Modal (Quality Review)
- **Trigger:** "Approve Case" button (green) during quality review
- **Who can trigger:** Level 2/3 Technician reviewing another tech's work
- **Header:** Green background, "Approve Case Review"
- **Options:** Release Now (radio) or Schedule Release (radio with date/time)
- **Fields:** Review Notes textarea
- **Buttons:** Cancel (gray), Approve & Complete (green)

### Request Revisions Modal (Quality Review)
- **Trigger:** "Request Revisions" button (yellow) during quality review
- **Who can trigger:** Level 2/3 Technician reviewing another tech's work
- **Header:** Yellow background, "Request Revisions"
- **Fields:** Revision Feedback textarea (required)
- **Buttons:** Cancel (gray), Request Revisions (yellow)

### Apply Corrections Modal (Quality Review)
- **Trigger:** "Fix & Complete Myself" button (red) during quality review
- **Who can trigger:** Level 2/3 Technician reviewing another tech's work
- **Header:** Red background, "Fix & Complete Case Myself"
- **Fields:** Correction Notes textarea (required)
- **Buttons:** Cancel (gray), Apply Corrections & Complete (red)

### Cancel Case Modal (Member only)
- **Trigger:** "Cancel Case" button (red outlined) on active cases
- **Who can trigger:** Member (cases in submitted/accepted/hold/pending_review/resubmitted/needs_resubmission)
- **Header:** Red background, "Cancel Case" title
- **Fields:** Reason for Cancellation textarea (required), Additional Notes textarea (optional)
- **Buttons:** Never Mind (gray), Submit Cancellation Request (red)

### Request Modification Modal (Member only)
- **Trigger:** "Request a Mod" button (cyan outlined) on completed cases
- **Who can trigger:** Member (completed cases within 60 days of release)
- **Header:** Cyan background, "Request a Modification"
- **Fields:** Reason for Modification textarea (required), "Is this an error on ProFeds Part?" checkbox
- **Buttons:** Cancel (gray), Create New Case (cyan)

### Ask a Question Modal (Member only)
- **Trigger:** "Ask a Question" button (green outlined) on completed cases
- **Who can trigger:** Member (completed cases, no time limit)
- **Header:** Green background, "Ask a Question"
- **Fields:** Question textarea (required)
- **Buttons:** Cancel (gray), Ask Question (green)

### RUSH Alert Modal (Draft Submission)
- **Trigger:** auto-triggered when submitting a draft with a due date < 7 days
- **Who can trigger:** Member
- **Header:** Yellow background, "RUSH ALERT"
- **Content:** Informs case is now marked RUSH
- **Buttons:** Edit Case & Revise Due Date (yellow), Submit as RUSH (green)

### Approve Change Request Modal (Tech/Manager/Admin)
- **Trigger:** "Approve" button on pending change request banner
- **Who can trigger:** Technician, Manager, Administrator
- **Header:** Green background, "Approve Request"
- **Fields:** Response Notes textarea (optional)
- **Buttons:** Cancel (gray), Confirm Approval (green)

### Deny Change Request Modal (Tech/Manager/Admin)
- **Trigger:** "Deny" button on pending change request banner
- **Who can trigger:** Technician, Manager, Administrator
- **Header:** Red background, "Deny Request"
- **Fields:** Reason for Denial textarea (required)
- **Buttons:** Cancel (gray), Confirm Denial (red)

### Reassignment Modal (Technician Dashboard — per case)
- **Trigger:** Pencil icon in Assigned To column on technician dashboard
- **Who can trigger:** Any technician
- **Fields:** Assign To dropdown, Reason textarea
- **Buttons:** Cancel (gray), Reassign (blue)

---

*End of UI Element Inventory*
