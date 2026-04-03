# Technician Workflow & Decision Tree

## Role Overview
**Benefits-Technicians** accept cases from the queue, perform validations, review documents submitted by members, upload reports generated from benefits-software, and manage case workflow from submission through completion and release.

> **📊 AUDIT TRAIL TRACKING NOTE:**  
> All technician activities are automatically tracked in the audit trail system, including case assignments, status changes, holds/resumes, tier changes, and quality reviews.

---

## Core Technician Actions

Technicians process cases through acceptance, investigation, and completion:

- **Accept Cases** - Take ownership from case queue
- **Investigate** - Perform research and documentation
- **Hold/Pause** - Temporarily pause with hold reasons
- **Complete** - Mark done with release timing

---

## Technician Actions by Case Status

### 1. **Submitted Status** (Unassigned)
- ✓ View case summary (not detailed)
- ✓ **Review & Accept** button:
  - Review Federal Fact Finder completeness
  - Review supporting documents
  - Adjust credit value (0.5 to 3.0)
  - Assign case tier (Tier 1, 2, or 3)
  - Select technician for assignment
  - Assign delegates for member (if applicable)
  - Complete pre-acceptance checklist
  - ⚠️ Tier Warning if tier > your level (can override)
- ✓ **Request More Info** (Reject):
  - Select rejection reason
  - Add detailed notes
  - Member gets email with requirements
- ✗ Cannot complete case yet (need acceptance first)

### 2. **Accepted Status** (Assigned to You)
- ✓ Full access to case details
- ✓ View all member documents
- ✓ Edit case notes internally
- ✓ Request more documents from member
- ✓ Add internal comments (not visible to member)
- ✓ Update case status/progress

### 3. **In Progress Status**
- ✓ Continue investigation
- ✓ Edit case notes
- ✓ Upload documents/reports
- ✓ Request member uploads
- ✓ Add internal findings
- ✗ Cannot complete until investigation done

### 4. **Resubmitted Status**
- ✓ Member sent new documents
- ✓ Review new submissions
- ✓ Incorporate into investigation
- ✓ Then proceed to completion

### 4A. **Hold Status** (Case Paused)
- ✓ Your ownership is **preserved**
- ✓ **Provide hold reason** (Required) - Explain why case is on hold:
  - Examples: "Waiting for Member Documents", "Awaiting Admin Decision", "Technical Issue", etc.
- ✓ **Member notification system** (Automatic):
  - Email sent to member with hold reason and case link
  - In-app notification badge appears on member dashboard
  - "Cases on Hold" alert appears on member dashboard with count
- ✓ **Member can respond** while on hold:
  - Upload additional documents or information
  - Add comments/questions
  - See the hold reason you provided
- ✓ Can still view all case documents
- ✓ Can still add internal notes
- ✓ **Resume from Hold** button available:
  - Click to resume investigation
  - Add reason for resuming
  - Status changes back to 'accepted'
  - Case returns to your active queue
  - Member gets notification that case is resuming
- ℹ️ Hold duration:
  - Case stays on hold **indefinitely** until member provides needed information
  - No automatic time-based release
  - If member doesn't respond and sits too long → Technician manually rejects case
  - Audit trail shows hold start, reason, and who initiated
- ✓ Can be placed on hold again after resuming
- **📊 AUDIT TRACKING:**  
  - `case_held` - Logged with hold reason and technician who initiated
  - `notification_created` - In-app notification created for member
  - `email_sent` - Confirmation that hold notification emailed to member
  - `document_uploaded` - Tracked if member uploads docs while on hold
  - `case_resumed` - Logged when hold is lifted with reason for resuming

### 5. **Completing Case — Pre-Completion Review Page**
When you click "Mark as Complete" from a case, you are taken to the **Pre-Completion Review** page. This single page lets you review everything, edit notes, adjust credit, and release — all without navigating away.

**Page Layout:**
- **Green header** shows Employee name, Member name, and Due Date (large `fs-4` font)
- **Left column (8-wide):**
  - **Reports section** — shows uploaded vs requested count, with inline "Upload Report" button/modal
  - **Technical Notes Preview** — rendered HTML preview of notes to member, with **"Edit Notes"** button that opens an inline TinyMCE rich text editor (same editor as case detail page). Save/Cancel without leaving the page.
- **Right column (4-wide):**
  - **Credit Value** — adjust credit (0.0–3.0) with reason field
  - **Release Options** card:
    - **Release Now** (default, pre-selected) — Member sees results immediately
    - **Schedule Release** — Pick specific date & time (CST), minimum tomorrow, cannot exceed due date
  - **"Release Case"** button (green, large) in card footer
  - **"Back to Case"** link below

- ✓ Inline TinyMCE notes editor — edit and save notes via AJAX without leaving the page
- ✓ Upload reports directly from the review page modal
- ✓ Credit value adjustment with optional reason
- ✓ Email notification automatically scheduled with release
- ✓ Works regardless of whether Level 1 or Level 2/3 technician
- ✓ Report validation allows extra reports (only checks all requested reports are present)

### 6. **Completed Case - Awaiting Release**
- ✓ Can still add internal notes
- ✓ View scheduled release date
- ✓ Option: Release immediately (if authorized)

---

## Release Timing: How It Works

✅ **Correct Behavior:**
- On the Pre-Completion Review page, YOU select the release option:
  - **Release Now** (default) — Case released immediately, member sees report and gets email right away
  - **Schedule Release** — Pick a specific date & time (CST). Member sees report on that date.
- Email notification is TIED to release timing (sent when case is released)
- If scheduled: Cron job runs daily at noon UTC to process scheduled releases and send emails
- Release date cannot exceed the case due date (validated client-side)

**Exception**: If case is already scheduled and member needs rush processing, staff can click "Release Immediately" on the case detail page to override the schedule.

---

## Email Notification System

### How It Works:
1. **On Case Completion** (Release Case clicked on Pre-Completion Review page):
   - If **Release Now**: Case released immediately, email sent immediately
   - If **Schedule Release**: System sets `scheduled_email_date` to chosen date/time (CST)

2. **On Release Now** (immediate):
   - Both release AND email happen immediately
   - Member sees \"Member Notified\" with timestamp on case detail

3. **On Scheduled Release**:
   - Cron job runs daily at noon UTC
   - Finds all cases with `scheduled_email_date <= today`
   - Sends email notification to member
   - Sets `actual_email_sent_date` to timestamp

4. **Member Notification Card**:
   - Shows in case detail page (staff-only view)
   - Displays one of:
     - ✅ "Member Notified on [DATE TIME CST]"
     - ⏳ "Notification Scheduled for [DATE]"
     - ⚠️ "No Notification Scheduled"
     - ℹ️ "Not Yet Completed"

---

## Key Features for Technicians

### Column Visibility Management 
**Customize your dashboard view to see only the columns you need:**

```
Dashboard Column Visibility:
├─ Click "Column Settings" button (gear icon)
├─ Toggle columns on/off:
│  ├─ Case ID (always shown)
│  ├─ Member Name
│  ├─ Status
│  ├─ Created Date
│  ├─ Assigned Technician
│  ├─ Tier
│  ├─ Credit Value
│  ├─ Documents Count
│  ├─ Notes
│  ├─ Last Modified
│  └─ Actions
├─ Collapsible filter section (saves vertical space)
├─ Filter counter showing active filters
└─ Preferences auto-save (no need to click "Save")
```

**How It Works:**
1. Click **"Column Settings"** button in dashboard header
2. Checkboxes appear for all available columns
3. Check/uncheck to show/hide columns
4. Preferences saved automatically to your account
5. Next time you login: Your columns persist
6. Filters can be collapsed to reduce visual clutter
7. Active filter count displayed for quick reference

### Case Queue Management
```
My Dashboard shows:
├── Unassigned Cases (available to claim)
├── My Cases (assigned to me)
│   ├── New (just accepted)
│   ├── In Progress (actively working)
│   └── Pending Release (completed, awaiting release)
└── Completed Cases (archived view)
```

### Investigation Tools
- ✓ Federal Fact Finder data viewer
- ✓ Member documents (fact finder, supporting docs)
- ✓ Internal notes system (only visible to tech/admin)
- ✓ Case timeline showing all actions
- ✓ Member communication (public notes)
- ✓ Additional Resources section (tech-uploaded files, hidden from member's Submitted Documents view)

### Reporting
- ✓ Upload investigation report
- ✓ Generate case summary
- ✓ Document evidence/findings
- ✓ Attach supporting evidence

### Release Timing Settings (Technician-Controlled)

| Option | Effect | When Used |
|--------|--------|----------|
| **Release Now** | Immediate release to member | Default — member sees report right away |
| **Schedule Release** | Member sees on chosen date/time (CST) | When you want to delay delivery to a specific date |

**You select the release option on the Pre-Completion Review page.**

---

## Common Technician Workflows

### Workflow A: "New Case Review & Accept"
1. Dashboard shows new case (Submitted)
2. Click **"Review & Accept"** button
3. Review screen displays:
   - Federal Fact Finder sections (check for completeness)
   - Supporting documents (verify presence)
   - Pre-acceptance checklist (4 required items)
4. Select credit value (0.5 to 3.0)
5. Select case tier (Tier 1, 2, or 3)
6. Select technician to assign to
7. Check all 4 checklist items
8. Click **"Accept & Assign"**
   - If tier > your level: ⚠️ Warning popup (can override)
9. Case status changes to "Accepted" and moves to tech's queue
10. Continue to Workflow B (Process case)

**Alternative: If Case Incomplete**
- Click **"Request More Info"** instead
- Select reason (missing FFF section, missing documents, etc.)
- Add detailed notes about what's needed
- Click **"Send & Request Info"**
- Case status → "Needs Resubmission"
- Member receives email with requirements

### Workflow A1: "Workshop Delegate Management" 

**Important:** Delegates are now assigned at the **workshop code level**, not individual members. One delegate can submit cases for ANY member in that workshop.

#### Accessing Workshop Delegate Management
1. From Technician Dashboard, click **"Management"** (gear icon, top right)
2. Click **"Workshop Delegates"**
   - URL: `/accounts/workshop-delegates/`
3. You'll see all active delegates assigned to workshop codes

#### Viewing Workshop Delegates
1. Use filters to find delegates:
   - Filter by **Workshop Code** (optional)
   - Filter by **Status** (Active/Inactive/All)
2. Click **"Filter"** to apply
3. See table with columns:
   - Workshop Code
   - Delegate Name
   - Permission Level
   - Assigned By
   - Date Assigned
   - Status

#### Adding a New Workshop Delegate
1. Click **"Add Workshop Delegate"** button (blue, top right)
2. Fill in form:
   - **Workshop Code:** e.g., "WS-001" or "DENVER" (uppercase)
   - **Delegate:** Select staff member from dropdown
   - **Permission Level:**
     - **View Only** = read-only access
     - **Submit Cases** = can submit for any member in workshop (recommended)
     - **Edit Cases** = can submit and edit cases
     - **Approve Cases** = full admin permissions
   - **Reason for Assignment:** (optional notes about why)
3. Check **"Active"** checkbox
4. Click **"Add Delegate"**
   - System confirms: "{Name} has been assigned to workshop {CODE}"
   - Audit log records assignment with your name, date, reason
5. Delegate can now submit cases for any member in that workshop

#### Editing a Workshop Delegate
1. From Workshop Delegates list, find the delegate row
2. Click **"Edit"** button (pencil icon)
3. Modify:
   - Workshop Code (if needed)
   - Delegate user
   - Permission Level
   - Reason
   - Active status (check/uncheck)
4. Click **"Update Delegate"**
   - Changes logged in audit trail
   - Records WHO changed it, WHAT was changed, WHEN

#### Revoking Workshop Delegate Access
1. From Workshop Delegates list, find delegate to revoke
2. Click **"Revoke"** button (trash icon)
3. Confirm revocation
   - Access immediately removed
   - Audit trail recorded
   - Delegate can no longer submit for that workshop

### Workflow B: "Standard Case Processing"
1. Case is Accepted and assigned to you
2. Review fact-finder & documents
3. Perform investigation
4. Upload report(s)
5. Click "Mark as Complete" → taken to **Pre-Completion Review** page
6. Review reports, edit technical notes (inline TinyMCE editor), adjust credit if needed
7. Select release option (Release Now is default)
8. Click **"Release Case"** button
9. Case released to member based on your selection
   - Release Now: Report visible immediately
   - Scheduled: Report visible on chosen date/time (CST)

### Workflow C: "Complex Investigation"
1. Review & Accept case (see Workflow A)
2. Full investigation (8-12 hours)
3. Multiple document requests from member
4. Upload comprehensive report(s)
5. Click "Mark as Complete" → Pre-Completion Review page
6. Review all reports, finalize technical notes, adjust credit if needed
7. Select release option (Release Now or Schedule Release)
8. Click **"Release Case"**

### Workflow D: "Resubmitted Case"
1. See case with "Needs Resubmission" status
   - This is a case you previously rejected
   - Member has resubmitted with requested documents
2. Click **"Review & Accept"** again
3. Verify all previously-missing items are now present
4. Review updated documents
5. Accept again OR reject again with updated notes
6. Continue processing as normal

### Workflow E: "Member Resubmitted Documents"
1. See "Resubmitted" status
2. New documents from member (updated info)
3. Review what changed
4. Incorporate into report
5. Click "Mark as Complete" → Pre-Completion Review page
6. Select release option and click **"Release Case"**
7. Member gets updated report based on release selection

---

## Member Profile Management

**Access Member Profile Features:**
Navigate from case detail → "Member Profile" tab (if case is assigned to you)

**What You Can Do:**
1. **Edit Member Details:**
   - Update personal information
   - Modify work/membership status
   - Change contact preferences
   - All changes automatically audited

2. **Manage Delegates:**
   - Add delegates (family, power of attorney, representatives)
   - Set delegate access levels
   - Configure access dates (active date/end date)
   - Revoke delegate access anytime
   - Audit trail tracks all delegate changes

3. **Configure Quarterly Credits:**
   - Set annual or quarterly credit allowance
   - Define credit usage limits
   - Enable/disable rollover
   - Set effective periods (Q1-Q4)
   - Monitor member credit usage
   - Flag overages or unusual patterns

**Important Notes:**
- ⚠️ Edits visible to admins
- ✓ All changes logged in audit trail
- ✓ Compliance documentation created automatically
- ✓ Member cannot edit own details through portal
- ✓ Only assigned technician (or higher) can edit

**Audit Trail Integration:**
- Each edit recorded with: WHO (you), WHAT (field changed), WHEN (timestamp), WHY (optional notes)
- Viewable by admins for compliance
- Never deleted, only updated (immutable records)
- Searchable for compliance audits

### Internal Communication
- **Internal Notes**: Only visible to tech and admin (not member)
- **Public Comments**: Visible to member (use for questions/updates)
- **Audit Trail**: Shows all changes made to case

---

## Troubleshooting for Technicians

| Issue | Solution |
|-------|----------|
| Can't find case | Check filters in dashboard, use search |
| Member can't upload docs | Check case status, may need to request upload |
| Forgot to mark complete | Find case, click "Mark as Complete" |
| Want to release earlier than scheduled | Click "Release Immediately" if authorized |
| Case was resubmitted | Review new docs, incorporate, mark complete again |

---

## 📊 Audit Trail Activities (Technician Role)

All technician activities are automatically tracked in the system's audit trail. Here's what gets logged:

| Activity | Audit Code | When Logged | Details Captured |
|----------|-----------|-------------|------------------|
| **Login** | `login` | Immediate | Session start, technician ID, timestamp |
| **Logout** | `logout` | Immediate | Session end, duration, last action |
| **Accept Case** | `case_assigned` | On assignment | Case ID, reason if provided, assignment time |
| **Change Case Status** | `case_status_changed` | On status update | Previous status, new status, case ID, timestamp |
| **Upload Report** | `document_uploaded` | On upload | Report file name, case ID, document type |
| **Mark Case Complete** | `case_updated` | On completion | Completion time, release date, delay duration |
| **Request Member Upload** | `case_details_edited` | When requesting | Case ID, member notified, document types requested |
| **Add Case Notes** | `note_added` | On post | Note text, case ID, visibility level (tech/all) |
| **Place Case on Hold** | `case_held` | Immediate | Case ID, reason, hold duration, release date |
| **Resume from Hold** | `case_resumed` | Immediate | Case ID, hold duration, reason for resumption |
| **Change Case Tier** | `case_tier_changed` | On change | Previous tier, new tier, case ID, reason |
| **Profile Update** | `member_profile_updated` | On save | Which fields changed, old/new values (if applicable) |

---

## Technician Support Resources

**Need Help?**
- Dashboard has "Help" for technicians
- Email: tech-support@company.com
- Slack: #technician-support
- Manager on-call for escalations
- Training videos in knowledge base

**Common Training Topics:**
- How to use Fact Finder viewer
- Report writing best practices
- Member communication standards
- Case completion process
- Document submission procedures

---

## Reference Diagrams

## Decision Tree: "What Should I Do Next?"

```
              START: I have a case assigned to me
                            │
                            ▼
                ┌──────────────────────────┐
                │ What's the case status?  │
                └────────┬─────────────────┘
                         │
    ┌────────┬───────────┼───────────┬────────┐
    │        │           │           │        │
SUBMITTED ACCEPTED  IN-PROGRESS COMPLETED RESUBMITTED
    │        │           │           │        │
    ▼        ▼           ▼           ▼        ▼
  NEW     REVIEW    CONTINUE    REVIEW   NEW
  CASE    PROGRESS  WORK        FOR      UPLOADS
          NOTES                 ISSUES
    │        │           │           │        │
    ├────────┴───────────┴───────────┴────────┤
    │                                          │
    ▼                                          ▼
 INVESTIGATE                            ┌──────────┐
 CASE                                   │ Has new  │
                                        │ docs     │
                                        │ from     │
                                        │ member?  │
                                        └────┬─────┘
                                             │
                                    ┌────────┴────────┐
                                    │                 │
                                   YES               NO
                                    │                 │
                                    ▼                 ▼
                            ┌────────────┐    ┌──────────────┐
                            │ Review New │    │ Complete Case│
                            │ Docs       │    │ Now (Select  │
                            │            │    │ Release Time)│
                            └────┬───────┘    └──────────────┘
                                 │
                                 ▼
                        ┌──────────────────┐
                        │ Use Docs in      │
                        │ Investigation    │
                        └────┬─────────────┘
                             │
                             ▼
                        ┌──────────────────┐
                        │ Complete Case    │
                        │ (Select Release  │
                        │ Time)            │
                        └──────────────────┘
```

---

## Decision Tree: "Is This Case Ready to Complete?"

```
                START: Ready to mark case complete?
                            │
                            ▼
                ┌──────────────────────────┐
                │ Have I completed all     │
                │ required investigation?  │
                └────────┬─────────────────┘
                         │
                    ┌────┴────┐
                    │          │
                   NO         YES
                    │          │
                    ▼          ▼
              ┌────────┐  ┌──────────────┐
              │ Keep   │  │ Is report    │
              │ Working│  │ written &    │
              │        │  │ uploaded?    │
              └────────┘  └────┬─────────┘
                               │
                          ┌────┴────┐
                          │          │
                         NO         YES
                          │          │
                          ▼          ▼
                    ┌────────┐  ┌──────────────┐
                    │ Upload │  │ Has member   │
                    │ Report │  │ received     │
                    │ First  │  │ everything?  │
                    └────────┘  └────┬─────────┘
                                    │
                               ┌────┴────┐
                               │          │
                              NO         YES
                               │          │
                               ▼          ▼
                        ┌─────────┐  ┌──────────────────┐
                        │ Request │  │ Do I need to     │
                        │ More    │  │ pause work on    │
                        │ Docs    │  │ this case?       │
                        │ First   │  └────┬─────────────┘
                        └─────────┘       │
                                     ┌────┴────┐
                                     │          │
                                    NO         YES
                                     │          │
                                     ▼          ▼
                               ┌────────┐  ┌──────────────┐
                               │Complete│  │ Put Case on  │
                               │ Case   │  │ Hold         │
                               │ Now    │  │              │
                               └────┬───┘  └────┬─────────┘
                                    │           │
                                    │    ┌──────┴──────┐
                                    │    │             │
                                    │    ▼             ▼
                                    │ SELECT:      SELECT:
                                    │ • Reason    • Duration
                                    │ • Notes     (Immediate
                                    │              2h, 4h, 8h,
                                    │              1 day, custom)
                                    │    │             │
                                    │    └──────┬──────┘
                                    │           │
                                    │           ▼
                                    │    Case Placed
                                    │    on Hold
                                    │    (Status = hold)
                                    │           │
                                    │    ┌──────┴──────┐
                                    │    │             │
                                    │    ▼             ▼
                                    │  Continue   Resume Later
                                    │  When Ready (When time
                                    │  (Click     comes)
                                    │  "Resume")
                                    │    │             │
                                    └────┴─────────────┘
                                         │
                                         ▼
                                  ┌──────────────────┐
                                  │ Select Release   │
                                  │ Timing:          │
                                  │ • 0 hrs: Now     │
                                  │ • 1-5 hrs: Later │
                                  └──────────────────┘
```

---

## Decision Tree: "Should I Put This Case on Hold?"

```
                START: Need to pause work on case?
                            │
                            ▼
                ┌──────────────────────────┐
                │ Why pause work?          │
                └────────┬─────────────────┘
                         │
    ┌─────────┬──────────┬┴──────────┬──────────┐
    │         │          │           │          │
WAITING   AWAITING   TECHNICAL   MEMBER      ESCALATION
MEMBER    DECISION   ISSUE       INFO        PENDING
DOCS      FROM ADMIN             PENDING
    │         │          │           │          │
    ▼         ▼          ▼           ▼          ▼
 SELECT:  SELECT:    SELECT:     SELECT:    SELECT:
 "Waiting "Awaiting  "Technical  "Waiting "Escalation
 for      Decision"  Issue"      for      Pending"
 Member"                         Member"
    │         │          │           │          │
    └─────────┴──────────┴───────────┴──────────┘
                    │
                    ▼
        ┌───────────────────────────┐
        │ SELECT Hold Duration:     │
        ├───────────────────────────┤
        │ • Immediate (No Duration) │
        │   (hold indefinitely)     │
        │                           │
        │ • 2 Hours                 │
        │   (auto-resume in 2h)     │
        │                           │
        │ • 4 Hours                 │
        │   (auto-resume in 4h)     │
        │                           │
        │ • 8 Hours                 │
        │   (auto-resume in 8h)     │
        │                           │
        │ • 1 Day                   │
        │   (auto-resume tomorrow)  │
        │                           │
        │ • Custom Duration         │
        │   (future: specify days)  │
        └───────┬───────────────────┘
                │
                ▼
    ┌───────────────────────────┐
    │ Click "Put on Hold"       │
    │ • Case ownership preserved│
    │ • Status changes to 'hold'│
    │ • Duration tracked       │
    │ • Reason logged          │
    └───────┬───────────────────┘
            │
            ▼
    ┌───────────────────────────┐
    │ Case is Now on Hold       │
    │ • Resume button appears   │
    │ • Your ownership stays    │
    │ • Notes still accessible  │
    │ • Hold timestamp set      │
    └───────┬───────────────────┘
            │
            ▼
    ┌───────────────────────────┐
    │ When Ready to Resume:     │
    │ • Click "Resume from Hold"│
    │ • Add resume reason       │
    │ • Status changes to       │
    │   'accepted'              │
    │ • Continue with case      │
    └───────────────────────────┘
```

---

## Technician Workflow Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                    TECHNICIAN WORKFLOW                           │
└──────────────────────────────────────────────────────────────────┘

                          START
                            │
                            ▼
                  ┌─────────────────────────┐
                  │ Access Technician       │
                  │ Dashboard               │
                  └────────┬────────────────┘
                           │
                           ▼
                  ┌─────────────────────────┐
                  │ View Case Queue/        │
                  │ Available Cases         │
                  └────────┬────────────────┘
                           │
                           ▼
                  ┌─────────────────────────┐
                  │ Find Case to Work       │
                  │ (Filter by Status/      │
                  │  Urgency)               │
                  └────────┬────────────────┘
                           │
              ┌────────────┴────────────┐
              │                         │
           UNASSIGNED             ASSIGNED TO ME
         (Available Cases)        (My Cases)
              │                         │
              ▼                         ▼
    ┌─────────────────────┐   ┌─────────────────────┐
    │ Take Ownership      │   │ Click Case to       │
    │ (Click Button)      │   │ Open Details        │
    └────────┬────────────┘   └────────┬────────────┘
             │                         │
             ▼                         ▼
    ┌─────────────────────┐   ┌─────────────────────┐
    │ Assigned to You     │   │ Review Case Files   │
    │ Now                 │   │ & Fact Finder       │
    └────────┬────────────┘   │ Data                │
             │                └────────┬────────────┘
             │                         │
             └────────┬────────────────┘
                      │
                      ▼
            ┌──────────────────────────┐
            │ Perform Investigation    │
            │ (External research,      │
            │  Verification, etc)      │
            └────────┬─────────────────┘
                     │
                     ▼
            ┌──────────────────────────┐
            │ Document Findings        │
            │ in Case                  │
            │ (Add notes/comments)     │
            └────────┬─────────────────┘
                     │
                     ▼
            ┌──────────────────────────┐
            │ Need Member Documents?   │
            └────────┬─────────────────┘
                     │
         ┌───────────┴───────────┐
         │                       │
        YES                      NO
         │                       │
         ▼                       ▼
    ┌────────────┐         ┌─────────────┐
    │ Request    │         │ Proceed to  │
    │ Upload     │         │ Report      │
    │ from Member│         │ Writing     │
    └────────────┘         └─────────────┘
         │                       │
         ▼                       │
    ┌────────────┐               │
    │ Wait for   │               │
    │ Member to  │               │
    │ Upload     │               │
    └─────┬──────┘               │
          │                      │
          └──────────┬───────────┘
                     │
                     ▼
            ┌──────────────────────────┐
            │ Create/Upload Report(s)  │
            │ (Analysis Document)      │
            └────────┬─────────────────┘
                     │
                     ▼
            ┌──────────────────────────┐
            │ Mark Case as Complete    │
            │ (w/ delay option 0-24hr) │
            └────────┬─────────────────┘
                     │
                     ▼
            ┌──────────────────────────┐
            │ Select Release Timing:   │
            │ 0-24 hours               │
            └────────┬─────────────────┘
                     │
         ┌───────────┴───────────────────┐
         │                               │
       0 hrs                           1-24 hrs
    (Immediate)                      (Delayed)
         │                               │
         ▼                               ▼
    ┌────────────┐              ┌──────────────────┐
    │ Released   │              │ Scheduled        │
    │ Immediately│              │ for Future       │
    │            │              │ Release (w/ Email│
    │ Email Sent │              │ Notification)    │
    │ Immediately│              │                  │
    └─────┬──────┘              └────┬─────────────┘
          │                          │
          ▼                          ▼
    ┌──────────────┐         ┌──────────────────┐
    │ Member Sees  │         │ Member Scheduled │
    │ Report Now   │         │ to Receive Email │
    │ Gets Email   │         │ on Release Date  │
    │ Notification │         │                  │
    └──────────────┘         └──────────────────┘
                                    │
                                    ▼
                            ┌──────────────────┐
                            │ Cron Job Sends   │
                            │ Email & Releases │
                            │ on Scheduled Date│
                            └──────────────────┘
                                    │
                                    ▼
                                  END
```

## Responding to Member Messages (NEW - Jan 31, 2026)

### Member Questions During Case Processing

Members can ask questions and provide updates while your case is being processed. Respond promptly to clarify requirements and provide status updates.

### How to Respond

1. **Open Case Detail Page** - Click case from your queue
2. **Scroll to Messages Section** - Bottom of page shows all member messages
3. **Type Your Response** - Click text area and type response
4. **Send Message** - Click **Send Message** button
5. **Member Notified Instantly** - Member sees notification within seconds

### What Happens Automatically

When you send a response:

1. **CaseMessage Created** - Your message stored permanently
2. **UnreadMessage Created** - Member sees unread badge on dashboard
3. **CaseNotification Created** - In-app notification for member with:
   - **Title:** "Response from [Your First Name]" (e.g., "Response from Monica")
   - **Preview:** First 1-2 sentences of your response (max 200 chars)
   - **Badge:** Blue "View Response " indicator
   - **Timestamp:** When you posted (e.g., "Jan 31, 2026 01:26 PM")

### Member Sees Your Response

1. Member gets notification bell badge
2. Member clicks notification  Case detail opens
3. Page auto-scrolls to messages section
4. Member sees your full response
5. Notification auto-marked as read
6. On next refresh, notification disappears

### Response Best Practices

 **DO:**
- Be clear and specific ("2021 tax return" not "documents")
- Respond within 24 hours
- Use professional, helpful tone
- Provide actionable next steps

 **DON'T:**
- Send vague responses
- Leave member waiting unnecessarily
- Share sensitive information in messages

### Notification Timing

- **Message Notifications:** Instant (no delay)
- **Member Email:** NOT sent for message responses (different from case emails)
- **Member Must Check:** Dashboard to see notifications
- **Frequency:** Every response triggers notification
