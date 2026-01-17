# Technician Workflow & Decision Tree

## Role Overview
**Technicians** (Benefits-Technicians) are the core workforce processing cases. They accept cases from the queue, perform investigations, complete fact-finding, upload reports, and manage case workflow from submission through completion and release.

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

---

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
                        ┌─────────┐  ┌──────────────┐
                        │ Request │  │ Ready to     │
                        │ More    │  │ Complete!    │
                        │ Docs    │  │              │
                        │ First   │  └────┬─────────┘
                        └─────────┘       │
                                          ▼
                                  ┌──────────────────┐
                                  │ Select Release   │
                                  │ Timing:          │
                                  │ • 0 hrs: Now     │
                                  │ • 1-5 hrs: Later │
                                  └──────────────────┘
```

---

## Technician Actions by Case Status

### 1. **Submitted Status** (Unassigned)
- ✓ View case summary (not detailed)
- ✓ **Review & Accept** button (NEW):
  - Review Federal Fact Finder completeness
  - Review supporting documents
  - Adjust credit value (0.5 to 3.0)
  - Assign case tier (Tier 1, 2, or 3)
  - Select technician for assignment
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
- ℹ️ Reassignment: Manager/Admin can reassign to another tech

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

### 5. **Completing Case**
- ✓ Mark as "Completed"
- ✓ Select release timing (0-24 hours CST)
- ✓ Set actual_release_date (if 0 hrs)
- ✓ Set scheduled_release_date & scheduled_email_date (if 1-24 hrs)
- ✓ Email notification automatically scheduled with release

### 6. **Completed Case - Awaiting Release**
- ✓ Can still add internal notes
- ✓ View scheduled release date
- ✓ Option: Release immediately (if authorized)

---

## Release Timing: Admin-Controlled (NOT Technician-Controlled)

✅ **Correct Behavior:**
- Admin sets default delay in System Settings (0-24 hours CST)
- When YOU mark a case "Complete", system AUTOMATICALLY uses that default
- You do NOT select the delay - admin controls it
- Email notification is TIED to release delay (sent same time as release)
- If immediate (0 hrs): Member sees report NOW and gets email immediately
- If delayed (1-24 hrs): System schedules both release AND email notification for same date/time
- Cron job processes both release and email sending on scheduled date

**Exception**: If case is already scheduled and member needs urgent access, you/admin can click "Release Immediately" to override the schedule and trigger email immediately.

---

## Email Notification System

### How It Works:
1. **On Case Completion** (marked as Completed):
   - System sets `scheduled_email_date` = completion delay date/time (CST)
   - System sets `actual_email_sent_date` = NULL (awaiting send)

2. **On Release** (if 0 hrs delay):
   - Both release AND email happen immediately
   - Member sees "Member Notified" with timestamp on case detail

3. **On Scheduled Release** (if 1-24 hrs delay):
   - Cron job runs daily (configured time)
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

### Column Visibility Management (NEW)
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

**Benefits:**
- ✓ Faster scanning of cases you care about
- ✓ Reduce horizontal scrolling
- ✓ Focus on relevant information
- ✓ Personalized dashboard layout
- ✓ Settings remember your preferences

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

### Reporting
- ✓ Upload investigation report
- ✓ Generate case summary
- ✓ Document evidence/findings
- ✓ Attach supporting evidence

### Release Timing Settings (Configured by Admin)

| Setting | Effect | When Used |
|---------|--------|----------|
| **0 hours** | Immediate release to member | For quick turnaround cases |
| **1 hour** | Member sees in 1 hour (CST) | Minimal delay |
| **2 hours** | Member sees in 2 hours (CST) | Standard (common default) |
| **3 hours** | Member sees in 3 hours (CST) | Quality review window |
| **4 hours** | Member sees in 4 hours (CST) | Extended review |
| **5 hours** | Member sees in 5 hours (CST) | Maximum delay window |

**You do NOT select these - Admin configures once for entire team.**

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

### Workflow A1: "Workshop Delegate Management" (NEW)
*Available to Benefits Technicians and Administrators*

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

#### Member Profile Management (Basic Info Only)
1. From a case detail view, click member name
2. Or navigate directly to member profile
3. As Benefits Technician, you can edit:
   - Personal information (name, email, phone)
   - Workshop code
   - Active status
4. **Note:** Delegate management is NO LONGER here
   - Delegates are now managed via Workshop Delegates interface
   - Members cannot assign their own delegates

#### Configuring Quarterly Credit Allowance
1. In member profile, click **"Quarterly Credits"**
2. View current credit configuration
3. **Set or Update Credit Allowance:**
   - Credit amount per quarter (typically $0-$500+)
   - Effective quarter (Q1/Q2/Q3/Q4)
   - Special notes or conditions
4. **Set Usage Limits:**
   - Monthly cap if applicable
   - Rollover settings (yes/no)
   - Restrictions or conditions
5. Click **"Save Configuration"**
   - System validates credit amounts
   - Audit log records who set what amount when
   - Member notified of new credit limits (optional)
6. **Monitor Credit Usage:**
   - View quarterly utilization
   - See member's usage status
   - Flag overages if applicable

**All Member Profile Changes:**
- ✓ Fully audited (AuditLog entry for each change)
- ✓ Tracked by technician/admin name
- ✓ Timestamped for compliance
- ✓ Visible to managers and admins
- ✓ No direct member access (technician-only feature)

### Workflow B: "Standard Case Processing"
1. Case is Accepted and assigned to you
2. Review fact-finder & documents
3. Perform investigation
4. Upload report
5. Click "Mark as Complete"
6. System automatically uses Admin's configured delay
7. Case released to member based on admin setting
   - If admin set 0 hrs: Report visible now
   - If admin set 2 hrs: Report visible in 2 hours (CST)

### Workflow C: "Complex Investigation"
1. Review & Accept case (see Workflow A)
2. Full investigation (8-12 hours)
3. Multiple document requests from member
4. Upload comprehensive report
5. Click "Mark as Complete"
6. System applies Admin's default delay automatically
7. Member sees report when scheduled (no additional action needed)

### Workflow D: "Resubmitted Case"
1. See case with "Needs Resubmission" status
   - This is a case you previously rejected
   - Member has resubmitted with requested documents
2. Click **"Review & Accept"** again
3. Verify all previously-missing items are now present
4. Review updated documents
5. Accept again OR reject again with updated notes
6. Continue processing as normal

### Workflow D: "Member Resubmitted Documents"
1. See "Resubmitted" status
2. New documents from member (updated info)
3. Review what changed
4. Incorporate into report
5. Click "Mark as Complete"
6. System applies Admin's default delay
7. Member gets updated report at scheduled release time

---

## Technician Tools & Features

### Technician Tools & Features

### Member Profile Management System (NEW)

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
- ⚠️ Edits visible to managers and admins
- ✓ All changes logged in audit trail
- ✓ Compliance documentation created automatically
- ✓ Member cannot edit own details through portal
- ✓ Only assigned technician (or higher) can edit

**Audit Trail Integration:**
- Each edit recorded with: WHO (you), WHAT (field changed), WHEN (timestamp), WHY (optional notes)
- Viewable by managers/admins for compliance
- Never deleted, only updated (immutable records)
- Searchable for compliance audits

### Internal Communication
- **Internal Notes**: Only visible to tech, manager, admin (not member)
- **Public Comments**: Visible to member (use for questions/updates)
- **Audit Trail**: Shows all changes made to case

### Performance Tracking
- Cases completed per day
- Average completion time
- Quality metrics (if tracked)
- Member satisfaction (if available)

### Management Commands
- Take ownership of unassigned cases
- Reassign cases (manager can do this)
- Flag for escalation
- Bulk operations (if applicable)

---

## Release Timing Considerations

**CST = Central Standard Time (America/Chicago)**

### Immediate Release (0 hours)
- ✓ Member sees report now
- ✓ Good for urgent cases
- ✓ Good for simple cases
- ✗ No quality review window

### Delayed Release (1-5 hours)
- ✓ Time for quality review
- ✓ Time for management check
- ✓ Predictable member experience
- ✓ Can release early if needed (admin/case-owner only)

**Admin can also:**
- Set default delay (2 hours default)
- Release scheduled cases immediately via "Release Now" button
- Override delays if needed

---

## Quality Review Workflow (By Technician Level)

### Understanding Technician Levels

The system uses a **three-level technician hierarchy** to ensure quality and manage expertise:

**Level 1 (New Technician):**
- New or less experienced
- Can complete standard cases (Tier 1, 2)
- **Cases automatically require senior review** before release
- Status changes to `pending_review` (not `completed`)
- Must wait for Level 2/3 technician approval

**Level 2 (Technician):**
- Standard experience level
- Can handle complex cases (all tiers)
- **Can review and approve Level 1 technician work**
- Can handle complex escalations
- Cases release directly to member (no review needed)

**Level 3 (Senior Technician):**
- Advanced expertise
- Can handle most complex cases
- **Can review and approve Level 1 technician work**
- Handles system-critical escalations
- Cases release directly to member (no review needed)

### Quality Review Process for Level 1 Technicians

**When you (Level 1) complete a case:**

1. **Investigation Complete:** Finish all work on the case
2. **Mark Complete:** Click "Mark Complete" button
3. **Select Release Delay:** Choose 1-4 hours CST
4. **Submit:** Click "Submit"
5. **Status Change:** System sets status to `pending_review` (NOT `completed`)
6. **Case Entered Review Queue:** Level 2/3 techs can see it waiting for review
7. **Waiting for Review:** Your case sits on the Level 2/3 technician's review dashboard
8. **Level 2/3 Review Options:**
   - ✓ **Approve** → Case moves to `completed` status, releases to member at scheduled time
   - 🔄 **Request Revisions** → Case returns to you with feedback, you make changes and resubmit
   - ✏️ **Apply Corrections** → Senior tech makes corrections, case releases to member as-is
9. **After Approval/Correction:** Case is released to member according to your delay setting

### Quality Review Process for Level 2/3 Technicians

**When you receive Level 1 cases for review:**

1. **Review Queue:** Dashboard shows "Cases Pending Review"
2. **Select Case:** Click on a case to review
3. **Review Details:**
   - Read case investigation and notes
   - Review attached documents
   - Check work quality and completeness
   - Verify credit value assignment
4. **Take Action:**
   - **Approve:** Case is good, mark for release
     - Click "Approve" button
     - Case moves to `completed` status
     - Member sees case at scheduled release time
   - **Request Revisions:** Changes needed
     - Click "Request Revisions"
     - Add detailed feedback
     - Case returns to Level 1 tech for rework
     - Level 1 tech can see feedback and notes
     - Level 1 tech resubmits when ready for re-review
   - **Correct Case:** Fix issues directly
     - Click "Apply Corrections"
     - Make edits to investigation, notes, credit value
     - Case marked `completed` and released to member
     - Your name added to audit trail as corrector

### For Level 2/3 Cases (Your Own Work)

**When you complete a case (Level 2 or 3):**

1. Mark Complete → Select release delay
2. Status → `completed` (no review needed)
3. Case releases to member at scheduled time
4. No additional approval required

---

## Quality Assurance Workflow

### For High-Complexity Cases:
1. Complete investigation as normal
2. Mark Complete → Select "3-4 hours" delay
3. Internal note to manager: "Please review before member sees"
4. Manager reviews during delay window
5. Manager approves or requests changes
6. Case releases to member at scheduled time

### For Standard Cases:
1. Complete investigation
2. Mark Complete → Select "1-2 hours"
3. Automatic release (no review needed)

---

## Troubleshooting for Technicians

| Issue | Solution |
|-------|----------|
| Can't find case | Check filters in dashboard, use search |
| Case reassigned to someone else | Contact manager - may be load balancing |
| Member can't upload docs | Check case status, may need to request upload |
| Forgot to mark complete | Find case, click "Mark as Complete" |
| Want to release earlier than scheduled | Contact admin or wait for "Release Immediately" feature |
| Case was resubmitted | Review new docs, incorporate, mark complete again |

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
- Quality standards & expectations
