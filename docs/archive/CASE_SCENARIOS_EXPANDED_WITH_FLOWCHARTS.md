# Case Scenarios - Expanded with Flowcharts & Implementation Status

## Overview

This document provides detailed expansion of each case processing scenario with visual flowcharts, database state changes, and implementation verification status.

---

# SCENARIO 1: Happy Path - Standard Processing

## Description
A member creates and submits a case, a technician accepts it, investigates, completes the case, and releases it immediately to the member. No holds, rejections, or reassignments.

## Flowchart

```
┌─────────────────────────────────────────────────────────────────┐
│ SCENARIO 1: Happy Path - Standard Processing                    │
└─────────────────────────────────────────────────────────────────┘

START: Member logs in
        │
        ▼
Create Draft Case (FFF form + docs)
Status: draft
        │
        ▼
Submit Case (validation check)
Status: draft → submitted
        │ (Email to member: "Submitted successfully")
        ▼
Appears in Unassigned Queue
        │
        ▼
Tech: Review & Accept
Decision: Tier=1, Credit=1.5
Status: submitted → accepted
        │ (Email to member: "Accepted & in progress")
        │ (Audit: case_accepted logged)
        ▼
Tech: Investigates (4-12 hours)
        ├─ Reviews FFF data ✅
        ├─ Checks documents ✅
        ├─ External research ✅
        └─ Status: accepted (no change)
        │
        ▼
Tech: Optional - Add Internal Notes
(Memo for self, not visible to member)
        │
        ▼
Tech: Optional - Ask Member Question
Public comment: "Can you clarify X?"
        ├─ (Email to member: Question notification)
        ├─ (Member sees badge on dashboard)
        │
        ▼
Member: Responds to Question
Comment + possible doc upload
        ├─ (Tech sees: has_member_updates = True)
        │
        ▼
Tech: Reviews Member Response
Reads comment & docs
        │
        ▼
Tech: Completes Investigation
        │
        ▼
Tech: Uploads Report
Document type: 'report'
Status: accepted (no change)
        │ (Audit: document_uploaded logged)
        ▼
Tech: Marks Case Complete
Selects: "Release Now"
Status: accepted → completed
        │ (Audit: case_updated logged)
        ▼
SET DATABASE FIELDS:
├─ status = 'completed'
├─ date_completed = now()
├─ actual_release_date = now()
├─ scheduled_release_date = NULL
└─ assigned_to = technician (unchanged)
        │
        ▼
Member: Receives Report
        ├─ Email: "Your case is ready"
        ├─ In-app: Badge "Case Ready"
        ├─ Dashboard: "Cases - Completed" section
        │
        ▼
Member: Downloads Report & Notes
        │
        ▼
END: Case Archived
Status: completed
All documents accessible

TOTAL TIME: ~24 hours
COMMUNICATIONS: 3-4 (submit, accept, question, completion)
STATUS CHANGES: draft → submitted → accepted → completed
HOLDS: 0
REJECTIONS: 0
```

## Database State Changes

| Phase | Field | Before | After | Triggered By |
|-------|-------|--------|-------|--------------|
| 1 | status | NULL | draft | Member creates |
| 2 | status | draft | submitted | Member submits |
| 2 | date_submitted | NULL | now() | Member submits |
| 2 | submitted_by | NULL | member | Member submits |
| 3 | status | submitted | accepted | Tech accepts |
| 3 | assigned_to | NULL | technician | Tech accepts |
| 3 | date_accepted | NULL | now() | Tech accepts |
| 3 | accepted_by | NULL | technician | Tech accepts |
| 4 | status | accepted | completed | Tech marks complete |
| 4 | date_completed | NULL | now() | Tech marks complete |
| 4 | actual_release_date | NULL | now() | Tech marks complete (immediate) |
| 4 | actual_email_sent_date | NULL | now() | Email sent to member |

## Communications

| To | From | Trigger | Type | Current Status |
|----|------|---------|------|----------------|
| Member | System | Submit | Email | ⚠️ **UNCLEAR** - Does system email? |
| Member | System | Accept | Email | ⚠️ **UNCLEAR** - Does system email? |
| Member | Tech | Question | Email+In-app | ⚠️ **UNCLEAR** - Does system email member? |
| Tech | System | Member Responds | Email | ⚠️ **UNCLEAR** - Does tech get notified? |
| Member | System | Complete | Email | ✅ **WORKS** - Completion email sent |
| Audit | System | All actions | Log | ✅ **WORKS** - All logged |

## Implementation Status

| Feature | Status | Notes |
|---------|--------|-------|
| Draft creation | ✅ WORKS | Member can create & save drafts |
| Case submission | ✅ WORKS | Validation works, moves to submitted |
| Unassigned queue | ✅ WORKS | Cases appear in tech dashboard |
| Case acceptance | ✅ WORKS | Tech can accept with tier/assignment |
| Internal notes | ✅ WORKS | Tech-only, hidden from member |
| Public comments | ✅ WORKS | Member-visible communication |
| Member responses | ✅ WORKS | Member can comment back |
| has_member_updates flag | ✅ WORKS | Flag set when member responds |
| Report upload | ✅ WORKS | Documents can be uploaded |
| Case completion | ✅ WORKS | Tech can mark complete |
| Immediate release | ✅ WORKS | Member gets report instantly |
| Email notifications | ⚠️ PARTIAL | Verify all email triggers |
| Audit trail | ✅ WORKS | All actions logged |

## Gaps to Address

1. **Email Notification Chain**
   - Need to verify member gets email on submit/accept
   - Need to verify tech gets email when member comments
   - **Impact:** Member/tech may not know case progressed
   - **Priority:** HIGH
   - **Test:** See test_scenario_1.py

---

# SCENARIO 2: Information Request & Resubmission

## Description
Member submits incomplete case. Technician reviews and finds missing information. Tech requests more info (rejects case). Member receives requirements email, uploads additional documents, and resubmits. Tech accepts on second review.

## Flowchart

```
┌─────────────────────────────────────────────────────────────────┐
│ SCENARIO 2: Information Request & Resubmission                  │
└─────────────────────────────────────────────────────────────────┘

START: Member submits incomplete case
Status: submitted
        │
        ▼
Tech: Reviews Case
Finds: FFF missing Q3-Q4 employment history
        │
        ▼
Tech: Clicks "Request More Info"
Modal: Select rejection reason
Selection: "Federal Fact Finder incomplete - missing required sections"
Add notes: "Need Q3-Q4 employment history & pay stubs"
        │
        ▼
SET DATABASE FIELDS:
├─ status = submitted → needs_resubmission
├─ rejection_reason = 'incomplete_fff'
└─ rejection_notes = "Need Q3-Q4..."
        │
        ▼
Member: Receives Rejection Email
        ├─ Subject: "Additional information needed for case [ID]"
        ├─ Body: Requirements, what's missing, link to case
        │ (Email to member: ✅ or ⚠️ VERIFY)
        │
        ▼
Member: Sees Case Status
Dashboard: Case shows "Needs Resubmission"
Action: Uploads missing documents (pay stubs, employment letters)
Status: still needs_resubmission (no change)
        │ (Audit: document_uploaded logged)
        │ (Tech notified? ⚠️ UNCLEAR)
        │
        ▼
Member: Clicks "Resubmit Case"
Status: needs_resubmission → submitted (or resubmitted)
        │ (Email to member: ✅ "Resubmitted for review")
        │ (Tech notified? ⚠️ UNCLEAR)
        │ (Audit: case_resubmitted logged)
        │
        ▼
Case: Back in Tech's Queue
Tech sees: "Resubmitted case - review required"
        │
        ▼
Tech: Re-Reviews Case
Checks: New documents present
Verifies: Missing info now complete
        │
        ▼
Tech: Reviews & Accepts
Same as Scenario 1 Phase 3
Status: resubmitted → accepted
        │
        ▼
Tech: Investigates
Status: accepted
        │
        ▼
Tech: Completes & Releases
Status: accepted → completed
        │
        ▼
Member: Gets Report (resubmitted case complete)
        │
        ▼
END: Case Archived

TOTAL TIME: ~36 hours
COMMUNICATIONS: 4-5 (submit, rejection, resubmit, complete)
STATUS CHANGES: submitted → needs_resubmission → submitted → accepted → completed
HOLDS: 0
REJECTIONS: 1
```

## Database State Changes

| Phase | Field | Before | After | Triggered By |
|-------|-------|--------|-------|--------------|
| 1 | status | submitted | needs_resubmission | Tech rejects |
| 1 | rejection_reason | NULL | incomplete_fff | Tech rejects |
| 1 | rejection_notes | NULL | reason text | Tech rejects |
| 1 | date_rejected | NULL | now() | Tech rejects |
| 2 | status | needs_resubmission | submitted | Member resubmits |
| 2 | resubmission_count | 0 | 1 | Member resubmits |
| 2 | date_resubmitted | NULL | now() | Member resubmits |
| 2 | is_resubmitted | False | True | Member resubmits |
| 3 | status | submitted | accepted | Tech accepts resubmission |

## Communications

| To | From | Trigger | Type | Current Status |
|----|------|---------|------|----------------|
| Member | System | Rejection | Email | ✅ **WORKS** - Rejection email sent |
| Tech | System | Resubmission | Email/Badge | ⚠️ **UNCLEAR** - Does tech get notified? |
| Member | System | Resubmit Confirm | Email | ⚠️ **UNCLEAR** - Does member get confirm? |

## Implementation Status

| Feature | Status | Notes |
|---------|--------|-------|
| Rejection modal | ✅ WORKS | Tech can select reason & add notes |
| Rejection reasons | ✅ WORKS | Predefined list available |
| Rejection email | ✅ WORKS | Member gets requirements email |
| Document upload after rejection | ✅ WORKS | Member can upload new docs |
| Resubmit button | ✅ WORKS | Member can resubmit |
| Resubmission tracking | ✅ WORKS | resubmission_count incremented |
| Tech notified of resubmit | ⚠️ UNCLEAR | Check if email sent or badge shown |

## Gaps to Address

1. **Resubmission Notification**
   - Tech should get notification that case was resubmitted
   - Currently unclear if this happens
   - **Priority:** MEDIUM

---

# SCENARIO 3: Case Put on Hold

## Description
Tech places case on hold with reason. Member is notified and can upload docs/comments while on hold. Tech reviews member's response and resumes case processing. Case continues to completion.

## Flowchart

```
┌─────────────────────────────────────────────────────────────────┐
│ SCENARIO 3: Case Put on Hold                                    │
└─────────────────────────────────────────────────────────────────┘

START: Tech is investigating case
Status: accepted
        │
        ▼
Tech: Encounters Issue
Problem: Need employment verification from employer
Decision: Can't reject (most info is OK), need to pause
        │
        ▼
Tech: Clicks "Put on Hold"
Modal appears: Select hold reason
Duration options: ⚠️ **NOT AVAILABLE** - Only indefinite
Selection: Reason = "Waiting for employment verification"
        │
        ▼
SET DATABASE FIELDS:
├─ status = accepted → hold
├─ assigned_to = technician (PRESERVED ✅)
├─ hold_reason = "Waiting for employment verification"
├─ hold_start_date = now()
├─ hold_end_date = NULL (indefinite)
└─ hold_duration_days = NULL
        │
        ▼
SEND MEMBER NOTIFICATION:
├─ Email: Subject "Your case has been placed on hold"
│  Body: "We're waiting for: employment verification"
│        "Please upload when available"
│ ✅ WORKS - Email sent
├─ In-app notification: Badge "Case on Hold"
│ ✅ WORKS - Notification created
└─ Dashboard: "Cases on Hold" section shows count
   ✅ WORKS - Section visible
        │
        ▼
Member: Sees "Case on Hold"
        ├─ Dashboard badge
        ├─ Email notification
        └─ Case detail shows hold reason
        │
        ▼
Member: Uploads Employment Verification
Action: Clicks "Upload Documents" button
Uploads: Employment verification letter
Status: still hold (no change)
        │ (Audit: document_uploaded logged)
        │ (Tech notified? ⚠️ UNCLEAR)
        │
        ▼
Member: Adds Comment
Text: "I've uploaded the employment verification letter"
Status: still hold (no change)
        │ (Audit: member_comment_added logged)
        │ (Tech notified? ⚠️ UNCLEAR)
        │
        ▼
Tech: Sees Member Update
Dashboard badge: "has_member_updates = True"
Status: accepted → ? (How does tech know it's during hold?)
        │
        ▼
Tech: Reviews Member Upload
Opens case, sees: New docs + member comment
Verifies: Employment verification is acceptable
        │
        ▼
Tech: Clicks "Resume Processing"
Modal: "Add reason for resuming (optional)"
Entry: "Employment verification received and accepted"
        │
        ▼
SET DATABASE FIELDS:
├─ status = hold → accepted
├─ assigned_to = technician (unchanged)
├─ hold_end_date = now()
├─ hold_resume_reason = "Employment verification received..."
└─ has_member_updates = False
        │
        ▼
SEND MEMBER NOTIFICATION:
├─ Email: "Your case processing has resumed"
└─ In-app: Badge updated
   ✅ WORKS
        │
        ▼
Tech: Continues Investigation
Status: accepted
        │
        ▼
Tech: Completes Case
Status: accepted → completed
        │
        ▼
Member: Receives Report
        │
        ▼
END: Case Archived

TOTAL TIME: ~48 hours
COMMUNICATIONS: 3-5 (hold, resume, complete)
STATUS CHANGES: submitted → accepted → HOLD → accepted → completed
HOLDS: 1 (indefinite, ~24 hrs)
REJECTIONS: 0
```

## Database State Changes

| Phase | Field | Before | After | Triggered By |
|-------|-------|--------|-------|--------------|
| 1 | status | accepted | hold | Tech puts on hold |
| 1 | assigned_to | technician | technician | Preserved |
| 1 | hold_reason | NULL | reason text | Tech specifies |
| 1 | hold_start_date | NULL | now() | Tech puts on hold |
| 1 | hold_end_date | NULL | NULL | Indefinite (no duration UI) |
| 1 | hold_duration_days | NULL | NULL | Indefinite (no duration UI) |
| 2 | has_member_updates | False | True | Member uploads/comments |
| 3 | status | hold | accepted | Tech resumes |
| 3 | hold_end_date | NULL | now() | Tech resumes |
| 3 | hold_resume_reason | NULL | reason text | Tech specifies |

## Communications

| To | From | Trigger | Type | Current Status |
|----|------|---------|------|----------------|
| Member | System | Put on hold | Email | ✅ **WORKS** - Hold email sent |
| Member | System | Put on hold | In-app | ✅ **WORKS** - Notification badge |
| Tech | System | Member uploads | Email/Badge | ⚠️ **UNCLEAR** - Does tech get notified? |
| Tech | System | Member comments | Email/Badge | ⚠️ **UNCLEAR** - Does tech get notified? |
| Member | System | Resume | Email | ✅ **WORKS** - Resume email sent |

## Implementation Status

| Feature | Status | Notes |
|---------|--------|-------|
| Put case on hold | ✅ WORKS | Tech can place on hold |
| Hold reason required | ✅ WORKS | Modal requires reason |
| Hold duration options | ❌ **MISSING** | Should offer 2h/4h/8h/1d/indefinite/custom |
| Member notification email | ✅ WORKS | Email sent with hold reason |
| Member in-app notification | ✅ WORKS | Notification badge appears |
| Member can upload during hold | ✅ WORKS | Upload button available |
| Member can comment during hold | ✅ WORKS | Comment field available |
| Tech notified of member update | ⚠️ UNCLEAR | has_member_updates flag exists |
| has_member_updates visible to tech | ✅ WORKS | Badge on dashboard |
| Resume from hold | ✅ WORKS | Tech can resume |
| Resume reason optional | ✅ WORKS | Reason tracked when provided |
| Member notified of resume | ✅ WORKS | Email sent |
| Ownership preserved | ✅ WORKS | assigned_to unchanged |
| Hold indefinitely | ✅ WORKS | No auto-release |

## Gaps to Address

1. **Hold Duration Options - CRITICAL**
   - Currently only indefinite possible
   - Should offer: 2h, 4h, 8h, 1 day, custom days
   - **Impact:** Can't set short holds
   - **Priority:** HIGH
   - **Effort:** 4-6 hours

2. **Tech Notifications During Hold**
   - When member uploads doc, does tech get email?
   - When member comments, does tech get email?
   - **Impact:** Tech may miss member responses
   - **Priority:** HIGH
   - **Effort:** 2-3 hours to verify/fix

---

# SCENARIO 4: Case Reassignment

## Description
A technician reassigns a case to another technician mid-processing. Case remains in accepted status but with new owner. New tech can see full history and continues investigation.

## Flowchart

```
┌─────────────────────────────────────────────────────────────────┐
│ SCENARIO 4: Case Reassignment                                   │
└─────────────────────────────────────────────────────────────────┘

START: Case is being worked by Tech A
Status: accepted
assigned_to: Tech A
        │
        ▼
Tech A: Cannot Continue
Reason: Going on vacation, sick, overwhelmed
        │
        ▼
Tech A: Clicks "Reassign" Button
Modal: Select new technician
Filters: Only active techs of appropriate level
        ├─ If Tier=2, only show Level 2+ techs
        └─ If Tier=3, only show Level 3 techs
Selection: Tech B (Level 2)
Optional: Add reason: "Taking vacation"
        │
        ▼
SET DATABASE FIELDS:
├─ assigned_to = Tech A → Tech B
├─ reassignment_date = now()
├─ previously_assigned_to = Tech A (if tracked)
└─ reassignment_reason = "Taking vacation"
        │
        ▼
SEND NOTIFICATIONS:
├─ Email to Tech B:
│  "Case [ID] has been reassigned to you"
│  "Reason: Taking vacation"
│  "All previous notes visible in case detail"
│ ✅ WORKS (or ⚠️ VERIFY)
│
├─ Email to Tech A:
│  "Reassignment confirmed"
│ ⚠️ UNCLEAR
│
└─ Email to Member (optional):
   "Your case has been reassigned to Tech B"
   ⚠️ UNCLEAR
        │
        ▼
Tech B: Logs In
Dashboard: Case now appears in "My Cases"
Status: accepted
        │
        ▼
Tech B: Opens Case Detail
Sees: All previous notes, documents, FFF data
No context loss ✅
        │
        ▼
Tech B: Continues Investigation
Status: accepted
        │
        ▼
Tech B: Completes Case
Status: accepted → completed
        │
        ▼
Member: Receives Report from Tech B
        │
        ▼
END: Case Archived

VARIANT: Reassignment During Hold

START: Case on hold assigned to Tech A
Status: hold
        │
        ▼
Tech A: Reassigns to Tech B
        │
        ▼
SET DATABASE FIELDS:
├─ assigned_to = Tech A → Tech B
├─ status = hold (preserved)
└─ hold_reason = preserved
        │
        ▼
Tech B: Can either:
├─ Resume from hold (continue investigation)
└─ Keep on hold longer (if needed)
        │
        ▼
Rest of workflow continues...

TOTAL TIME: Variable
COMMUNICATIONS: 2-3 (Tech B notified, member optional)
STATUS CHANGES: None (just reassignment)
HOLDS: 0 or 1 (if already on hold)
```

## Database State Changes

| Phase | Field | Before | After | Triggered By |
|-------|-------|--------|-------|--------------|
| 1 | assigned_to | Tech A | Tech B | Tech A reassigns |
| 1 | reassignment_date | NULL | now() | Tech A reassigns |
| 1 | reassignment_reason | NULL | reason text | Tech A provides |
| 1 | previously_assigned_to | NULL | Tech A | Tracking |

## Communications

| To | From | Trigger | Type | Current Status |
|----|------|---------|------|----------------|
| Tech B | System | Reassignment | Email | ✅ **WORKS** (or ⚠️ VERIFY) |
| Member | System | Reassignment | Email | ⚠️ **UNCLEAR** - Optional notification |
| Tech A | System | Reassignment | Email | ⚠️ **UNCLEAR** - Confirmation? |

## Implementation Status

| Feature | Status | Notes |
|---------|--------|-------|
| Reassign button | ✅ WORKS | Available on case detail |
| Tech level validation | ✅ WORKS | Only shows compatible techs |
| Tier constraint | ✅ WORKS | Filters by tier level |
| Reassignment reason | ✅ WORKS | Can add optional reason |
| New tech notified | ✅ WORKS (VERIFY) | Email sent |
| Case history visible | ✅ WORKS | All notes/docs accessible |
| Hold preserved on reassign | ⚠️ UNCLEAR | If case on hold, check if status preserved |
| Member notification | ⚠️ UNCLEAR | Optional - clarify if needed |

## Gaps to Address

1. **Member Notification on Reassignment**
   - Should member be notified?
   - If yes, implement notification
   - **Priority:** MEDIUM

2. **Hold Preservation Verification**
   - If case on hold when reassigned, verify hold preserved
   - **Priority:** MEDIUM

---

# SCENARIO 5: Scheduled Release

## Description
Tech completes case but schedules release for future date (tomorrow to 60 days out). Cron job processes release and sends email at scheduled time. Member receives report.

## Flowchart

```
┌─────────────────────────────────────────────────────────────────┐
│ SCENARIO 5: Scheduled Release                                   │
└─────────────────────────────────────────────────────────────────┘

START: Tech completes investigation
Status: accepted
        │
        ▼
Tech: Uploads Report
Status: accepted (no change)
        │
        ▼
Tech: Marks Case Complete
Modal: Release timing options
        ├─ Option A: Release Now (0 hours)
        ├─ Option B: Use Admin Default (e.g., 2 hours)
        └─ Option C: Schedule Release (future date/time)
Selection: Option C - Schedule Release
        │
        ▼
Tech: Date/Time Picker
Constraint: Tomorrow to 60 days from now
Selection: "Tomorrow at 9:00 AM CST"
        │ (60-day validation: ✅ VERIFY)
        │
        ▼
SET DATABASE FIELDS:
├─ status = accepted → completed
├─ date_completed = now()
├─ scheduled_release_date = Tomorrow 9:00 AM CST
├─ actual_release_date = NULL (not released yet)
├─ scheduled_email_date = Tomorrow 9:00 AM CST
└─ actual_email_sent_date = NULL
        │
        ▼
Member: CANNOT SEE CASE YET
Dashboard: No case notification (not released)
Status: completed (internal only)
        │
        ▼
Tech: Sees "Pending Release"
Dashboard: "My Cases" → "Pending Release" section
Shows: Scheduled release time
Can still: Add notes, "Release Immediately" override
        │
        ▼
TIME PASSES: Tomorrow 9:00 AM CST arrives
        │
        ▼
CRON JOB: process_scheduled_releases
Finds: Cases where scheduled_release_date <= now()
        │ (❌ CRITICAL - VERIFY CRON JOB EXISTS)
        │
        ▼
FOR EACH CASE:
├─ UPDATE Database:
│  ├─ actual_release_date = now()
│  ├─ actual_email_sent_date = now()
│  └─ Status: completed (unchanged)
│
├─ SEND EMAIL:
│  ├─ To: member email
│  ├─ Subject: "Your case report is ready"
│  └─ Body: Report link, download link
│  ✅ (or ⚠️ VERIFY)
│
└─ AUDIT:
   └─ email_notification_sent logged
        │
        ▼
Member: Receives Email
        ├─ Notification arrives at exact scheduled time
        ├─ Member clicks "Download Report"
        └─ Can now view all case details
        │
        ▼
Member: Downloads Report
Status: completed
        │
        ▼
END: Case Archived

TOTAL TIME: 24+ hours (includes scheduled delay)
COMMUNICATIONS: 1 (completion email at exact time)
STATUS CHANGES: submitted → accepted → completed (with scheduled release)
HOLDS: 0
SPECIAL: Cron job dependency
```

## Database State Changes

| Phase | Field | Before | After | Triggered By |
|-------|-------|--------|-------|--------------|
| 1 | status | accepted | completed | Tech marks complete |
| 1 | date_completed | NULL | now() | Tech marks complete |
| 1 | scheduled_release_date | NULL | Tomorrow 9:00 AM | Tech schedules |
| 1 | scheduled_email_date | NULL | Tomorrow 9:00 AM | Tech schedules |
| 1 | actual_release_date | NULL | NULL | Not released yet |
| 1 | actual_email_sent_date | NULL | NULL | Not sent yet |
| 2 | actual_release_date | NULL | now() | Cron job executes |
| 2 | actual_email_sent_date | NULL | now() | Cron job sends email |

## Communications

| To | From | Trigger | Type | Current Status |
|----|------|---------|------|----------------|
| Member | System | Cron release | Email | ⚠️ **CRITICAL** - VERIFY WORKS |

## Implementation Status

| Feature | Status | Notes |
|---------|--------|-------|
| Scheduled release option | ✅ WORKS | Available on completion |
| Date/time picker | ✅ WORKS | CST timezone |
| 60-day max validation | ⚠️ VERIFY | Should prevent dates > 60 days |
| Cron job exists | ❌ **CRITICAL** | Process scheduled releases |
| Cron processes releases | ❌ **CRITICAL** | Updates actual_release_date |
| Cron sends emails | ❌ **CRITICAL** | Sends member notification |
| Cron runs on schedule | ❌ **CRITICAL** | Runs daily at configured time |
| Member can't see before release | ✅ WORKS | Not visible in dashboard |
| Tech sees pending release | ✅ WORKS | Appears in "Pending Release" |
| Release Immediately override | ✅ WORKS | Tech can release early |

## Gaps to Address

1. **CRITICAL: Cron Job Verification**
   - **Issue:** Scheduled releases completely depend on cron job
   - **Status:** Need to verify cron job exists and is active
   - **Location:** Check for /cases/management/commands/process_scheduled_releases.py
   - **If Missing:** Must build scheduled release processor
   - **Impact:** Without this, scheduled releases don't work at all
   - **Priority:** CRITICAL
   - **Effort:** 2 hours to verify, 6-8 hours to build if missing

2. **60-Day Validation**
   - Verify that date picker prevents selection > 60 days
   - **Priority:** HIGH

---

# SCENARIO 6: Member Requests Modification

## Description
Member receives completed case report, reviews it, and requests modification within 60 days. New case created and linked to original. Auto-assigned back to original technician when completed. Member can compare original and modified case.

## Flowchart

```
┌─────────────────────────────────────────────────────────────────┐
│ SCENARIO 6: Member Requests Modification                        │
└─────────────────────────────────────────────────────────────────┘

START: Member has completed case
Status: completed
Days since release: < 60 days
        │
        ▼
Member: Reviews Report
Downloaded technical notes
Identifies: Error in Q3-Q4 calculations
        │
        ▼
Member: Checks "Request a Mod" Button
Status: ✅ Button visible and enabled
Time remaining: 58 days (within 60-day window)
        │
        ▼
Member: Clicks "Request a Mod"
Modal: "Request a Modification"
Field: Reason for modification (required)
Input: "Q3-Q4 credit calculations appear incorrect"
Optional: Upload supporting documents
        │
        ▼
Member: Submits Request
Validation: Reason provided ✅
        │ (Audit: member_comment_added or case_message_created)
        │
        ▼
NEW CASE CREATED:
├─ external_case_id = Auto-generated (new ID)
├─ status = submitted
├─ original_case = FK to original case ✅
├─ member = same member ✅
├─ workshop_code = same code ✅
├─ employee_first_name = copied
├─ employee_last_name = copied
├─ client_email = same
├─ created_by = member
├─ date_submitted = now()
├─ tier = copied from original
└─ credit_value = copied from original
        │
        ▼
SET DATABASE FIELDS (Original Case):
├─ Message created: "Modification requested: Q3-Q4 calculations..."
├─ Message author = member
├─ Message visible to tech ✅
└─ Audit: case_message_created logged
        │
        ▼
SEND NOTIFICATIONS:
├─ Email to Member:
│  "New modification case [ID] created"
│  "Assigned case: [ID]"
│ ✅ WORKS
│
└─ Email to Original Tech:
   "Member requested modification for case [ID]"
   "New case [ID] created"
   "Reason: Q3-Q4 calculations..."
   ✅ WORKS
        │
        ▼
Tech: Sees Modification Notification
Dashboard: Shows badge "Modification case available"
        │
        ▼
Tech: Reviews New Case Detail
Sees: Bidirectional link to original case
Option: "Original Case: [Link]" button visible
Can compare: Original report vs modification request
        │
        ▼
Tech: Reviews Modification Reason
Notes: "Q3-Q4 calculations appear incorrect"
        │
        ▼
Tech: Accepts Modification Case
Status: submitted → accepted
        │
        ▼
Tech: Investigates Modification
Recalculates Q3-Q4 credits
Reviews: Finds member is correct
Corrects: Updates credit projection
        │
        ▼
Tech: Marks Modification Complete
Status: accepted → completed
        │
        ▼
AUTO-ASSIGNMENT LOGIC:
Check: Was original case assigned to Tech A?
If yes: Auto-assign new case to Tech A
IF: Tech A still available
THEN: Assign
ELSE: Assign to available tech of same level
        │
        ▼
SEND NOTIFICATION:
├─ Audit: case_assigned (auto-assignment reason)
└─ Message: "[Tech A] has been auto-assigned this modification"
        │
        ▼
Member: Receives Modification Report
Status: completed
        │
        ▼
Member: Can Switch Between Cases
Dashboard: Original case link + Modification case link
Or: In case detail, "Modifications: [List]" section
Can compare: Reports side-by-side (if UI available)
        │
        ▼
Member: Has Original + Correction
Original report: Shows initial calculation
Modified report: Shows corrected calculation
        │
        ▼
END: Both cases archived
Original: completed (unchanged)
Modification: completed (new)
Linked: ✅ bidirectional

TOTAL TIME: 24-48 hours
COMMUNICATIONS: 3 (mod created, tech notified, completion)
STATUS CHANGES (Original): None (stays completed)
STATUS CHANGES (Mod): submitted → accepted → completed
HOLDS: Possibly (if mod case needs info)
SPECIAL: Bidirectional linking, auto-assignment
```

## Database State Changes

| Phase | Field | Original | Modification | Triggered By |
|-------|-------|----------|--------------|--------------|
| 1 | original_case | - | original_case_fk | Member requests |
| 1 | status (mod) | - | submitted | Mod case created |
| 1 | created_by (mod) | - | member | Member creates mod |
| 1 | date_submitted (mod) | - | now() | Member creates mod |
| 2 | Message created | visible | - | Member reason stored |
| 3 | status (mod) | - | submitted→accepted | Tech accepts mod |
| 4 | status (mod) | - | accepted→completed | Tech completes mod |
| 4 | assigned_to (mod) | - | original_tech | Auto-assignment |

## Communications

| To | From | Trigger | Type | Current Status |
|----|------|---------|------|----------------|
| Member | System | Mod created | Email | ✅ **WORKS** |
| Tech | System | Mod available | Email | ✅ **WORKS** |
| Tech | System | Mod assigned | In-app | ✅ **WORKS** |
| Member | System | Mod complete | Email | ✅ **WORKS** |

## Implementation Status

| Feature | Status | Notes |
|---------|--------|-------|
| Request modification button | ✅ WORKS | Visible on completed cases |
| 60-day limit | ✅ WORKS | Button disabled after 60 days |
| Modification modal | ✅ WORKS | Reason required |
| New case creation | ✅ WORKS | Mod case created as submitted |
| Original case linked | ✅ WORKS | original_case FK |
| Original tech notified | ✅ WORKS | Email sent |
| Auto-assignment on completion | ✅ WORKS | Returns to original tech |
| Bidirectional linking in UI | ✅ **RECENTLY ADDED** | Links show original↔mod |
| Member can compare | ✅ WORKS | Both cases accessible |

## Gaps to Address

None identified - **Modification workflow complete!** ✅

---

# SCENARIO 7: Complex Hold & Resume Cycle

## Description
Case is placed on hold multiple times for different reasons. Technician resumes, continues investigation, then places on hold again when another issue arises. Multiple hold/resume cycles before completion.

## Flowchart

```
┌─────────────────────────────────────────────────────────────────┐
│ SCENARIO 7: Complex Hold & Resume Cycle                         │
└─────────────────────────────────────────────────────────────────┘

START: Tech is investigating
Status: accepted
        │
        ▼
FIRST HOLD:
Tech: "Need employment verification"
Click: "Put on Hold"
Reason: "Waiting for employment verification from employer"
Duration: Indefinite ❌ (Should allow custom)
        │
        ▼
Member: Notified ✅
        │
        ▼
Member: Uploads employment verification letter
Status: still hold (no change)
        │ (Tech notified? ⚠️)
        │
        ▼
Tech: Reviews uploaded doc
Verification looks good
        │
        ▼
Tech: Resumes from Hold
Reason: "Employment verification received and acceptable"
Status: hold → accepted
        │
        ▼
Member: Notified of resume ✅
        │
        ▼
CONTINUE INVESTIGATION:
Tech: Continues research
Status: accepted (no change)
        │
        ▼
SECOND HOLD:
Tech: "Need manager approval on credit limit exception"
Click: "Put on Hold" (AGAIN)
Reason: "Awaiting manager approval for credit limit exception"
Status: accepted → hold (SECOND TIME)
        │
        ▼
Member: Notified AGAIN ✅
Member sees: Case back on hold (confusing?)
        │ (Communication clarity: ⚠️)
        │
        ▼
Manager: Reviews and approves exception
Tech: Gets approval
        │
        ▼
Tech: Resumes from Hold (AGAIN)
Reason: "Manager approved credit limit exception"
Status: hold → accepted (SECOND RESUME)
        │
        ▼
Member: Notified of resume AGAIN ✅
        │
        ▼
CONTINUE INVESTIGATION:
Tech: Completes final research
Status: accepted (no change)
        │
        ▼
COMPLETION:
Status: accepted → completed
        │
        ▼
Member: Receives Report
        │
        ▼
END: Case Archived
HOLD HISTORY: 2 holds, 2 resumes

QUESTIONS:
├─ Is hold history visible to tech?
│  ⚠️ UNCLEAR - Audit logged but not UI visible
├─ Is hold history visible to member?
│  ⚠️ UNCLEAR
├─ Does UI show: "Case on hold (2nd time)"?
│  ⚠️ UNCLEAR
└─ Can cases loop hold/resume indefinitely?
   ✅ SHOULD WORK (no limit)

TOTAL TIME: ~72+ hours
COMMUNICATIONS: 5+ (hold, resume, hold, resume, complete)
STATUS CHANGES: accepted → HOLD → accepted → HOLD → accepted → completed
HOLDS: 2 (back-to-back)
RESUMES: 2
```

## Database State Changes

| Phase | Field | Change | Count |
|-------|-------|--------|-------|
| 1 | status | accepted→hold | 1st hold |
| 1 | hold_start_date | NULL→now() | 1st hold |
| 1 | hold_reason | NULL→reason1 | 1st hold |
| 2 | status | hold→accepted | 1st resume |
| 2 | hold_end_date | NULL→now() | 1st resume |
| 3 | status | accepted→hold | 2nd hold |
| 3 | hold_start_date | now()→now() | 2nd hold (overwritten?) |
| 3 | hold_reason | reason1→reason2 | 2nd hold (overwritten?) |
| 4 | status | hold→accepted | 2nd resume |
| 4 | hold_end_date | now()→now() | 2nd resume (overwritten?) |

## Implementation Status

| Feature | Status | Notes |
|---------|--------|-------|
| Multiple holds possible | ⚠️ UNCLEAR | Should work but not tested |
| Hold history preserved | ⚠️ UNCLEAR | Fields overwritten each hold? |
| Hold history visible | ❌ NO | Not in UI or audit trail view |
| Multiple resumes | ⚠️ UNCLEAR | Should work but not tested |
| Resume reason tracked | ✅ WORKS | Fields exist |
| Member confusion | ⚠️ CONCERN | Multiple hold/resume cycles confusing |

## Gaps to Address

1. **Hold History Tracking**
   - Current model may overwrite hold_reason and dates on 2nd hold
   - Should track: hold_1, resume_1, hold_2, resume_2 separately
   - **Solution:** Create HoldHistory table or use audit trail better
   - **Priority:** MEDIUM

2. **Hold History Visibility**
   - Techs & members should see full hold history
   - **Priority:** MEDIUM

3. **Communication Clarity**
   - Multiple hold/resume notifications may confuse member
   - **Priority:** LOW (nice to have: "Case on hold #2")

---

# SCENARIO 8: Case Completion Outside 60-Day Window

## Description
Member tries to request modification after 60 days have passed since case release. Button is disabled with explanation. Member instead uses "Ask a Question" to communicate with tech.

## Flowchart

```
┌─────────────────────────────────────────────────────────────────┐
│ SCENARIO 8: Modification Outside 60-Day Window                  │
└─────────────────────────────────────────────────────────────────┘

START: Case was completed & released
Status: completed
Days since release: 65 days
        │
        ▼
Member: Reviews old case
Notices: Potential issue with calculations
Wants: To request modification
        │
        ▼
Member: Looks for "Request a Mod" Button
Button visible? ❌ NO (or Disabled)
Disabled status: ✅ WORKS
        │
        ▼
Member: Hovers over disabled button
Tooltip: "Modification requests only available within 60 days"
        │
        ▼
Member: Alternative - Click "Ask a Question"
No time limit ✅
        │
        ▼
Member: Fills question modal
Question: "I think the Q3-Q4 calculation might be incorrect. Can you review?"
        │
        ▼
SEND COMMUNICATION:
├─ Message created
├─ Author: member
├─ Visible: to tech
└─ Audit: member_comment_added
        │
        ▼
Tech: Receives Question
Email/Badge notification: "Member has a question about case [ID]"
        ⚠️ UNCLEAR - Does tech get notified?
        │
        ▼
Tech: Reviews Case & Question
Can respond: "Yes, I'll review the calculation"
Or: "The calculation was correct because..."
        │
        ▼
Member: Gets Response
Sees: Tech's answer to question
Resolution: Can understand reasoning or request new case
        │
        ▼
END: Case stays completed (no modification case created)

TOTAL TIME: Variable (depends on response time)
COMMUNICATIONS: 1+ (question)
STATUS CHANGES: None (stays completed)
HOLDS: 0
MODIFICATIONS: 0 (blocked by 60-day window)
ALTERNATIVE: Ask a Question pathway used instead
```

## Implementation Status

| Feature | Status | Notes |
|---------|--------|-------|
| 60-day enforcement | ✅ WORKS | Button disabled after 60 days |
| Button disabled state | ✅ WORKS | Visual indicator shown |
| Tooltip message | ✅ WORKS | Explains why disabled |
| Ask a Question button | ✅ WORKS | No time limit |
| Question capability | ✅ WORKS | Can ask even after 60 days |

## Gaps to Address

None - **60-day enforcement complete!** ✅

---

# SCENARIO 9: Multiple Document Requests (Iterative)

## Description
Technician needs multiple pieces of information. Instead of putting on hold, uses iterative comment/question approach. Member uploads docs and responds to questions in back-and-forth communication until all info gathered.

## Flowchart

```
┌─────────────────────────────────────────────────────────────────┐
│ SCENARIO 9: Multiple Document Requests (Iterative)              │
└─────────────────────────────────────────────────────────────────┘

START: Tech is investigating
Status: accepted
        │
        ▼
REQUEST #1:
Tech: Adds public comment
"Can you upload a recent medical report to verify current status?"
        │ (Email to member? ⚠️ UNCLEAR)
        │
        ▼
Member: Sees question
Dashboard badge: Unread message ✅
        │
        ▼
Member: Uploads document
Medical report PDF uploaded
Status: still accepted (no change)
        │ (Tech notified? ⚠️ UNCLEAR)
        │ (Audit: document_uploaded logged)
        │
        ▼
Member: Responds
"Here's my recent medical report from Dr. Smith"
        │ (Audit: member_comment_added)
        │
        ▼
Tech: Reviews upload & response
Sees: Medical report received ✅
Determines: Needs clarification
        │
        ▼
REQUEST #2:
Tech: Adds public comment
"Great! Can you clarify the treatment dates in Section 3? They seem incomplete."
        │ (Email to member? ⚠️ UNCLEAR)
        │
        ▼
Member: Sees 2nd question
Dashboard badge updated
        │
        ▼
Member: Uploads supplement
"Treatment Timeline" document
        │
        ▼
Member: Responds
"I've attached a detailed timeline with all dates"
        │
        ▼
Tech: Reviews
Determines: One more question needed
        │
        ▼
REQUEST #3:
Tech: Asks final question
"Perfect! Do you have any employment history after [date]?"
        │ (Email to member? ⚠️ UNCLEAR)
        │
        ▼
Member: Responds
"No, I haven't worked since [date]. I've been on benefits."
Optional: Uploads supporting documentation
        │
        ▼
Tech: Has All Information
Investigation complete ✅
All questions answered ✅
All docs received ✅
        │
        ▼
COMPLETION:
Status: accepted → completed
Releases report
        │
        ▼
Member: Gets Final Report
        │
        ▼
END: Case Archived

TOTAL TIME: 40-60 hours
COMMUNICATIONS: 3+ questions, 3+ responses (all back-and-forth in comments)
STATUS CHANGES: submitted → accepted → completed
HOLDS: 0 (back-and-forth without holding)
ITERATIONS: 3 request/response cycles
DOCUMENTS: 2-3 uploaded
```

## Implementation Status

| Feature | Status | Notes |
|---------|--------|-------|
| Public comments | ✅ WORKS | Tech can ask questions |
| Comment visibility | ✅ WORKS | Member sees comments |
| Member can respond | ✅ WORKS | Can add comments back |
| Document uploads | ✅ WORKS | Member can upload docs |
| Document association | ✅ WORKS | Linked to case |
| Unread badge | ✅ WORKS | Member sees new questions |
| Comment threads | ✅ WORKS | Chronological view |
| Tech email notification | ⚠️ UNCLEAR | Does tech get email on member response? |
| Member email notification | ⚠️ UNCLEAR | Does member get email on tech question? |

## Gaps to Address

1. **Notification System**
   - Need to verify tech gets email when member responds
   - Need to verify member gets email when tech asks question
   - **Priority:** HIGH

---

# SCENARIO 10: Manager Quality Review

## Description
Manager reviews a completed case for quality assurance. Can add review notes, approve, or find issues. If issues found, case can be reopened for correction (missing feature).

## Flowchart

```
┌─────────────────────────────────────────────────────────────────┐
│ SCENARIO 10: Manager Quality Review                             │
└─────────────────────────────────────────────────────────────────┘

START: Case is completed
Status: completed
Tech: Available for review
        │
        ▼
Manager: Accesses Completed Cases
Dashboard: Manager can see all completed cases
        │ (Permission: ✅ Manager dashboard)
        │
        ▼
Manager: Reviews Case Detail
Sees: Full case, notes, documents, report
        │
        ▼
SCENARIO A: APPROVAL
Manager: Reviews work quality
Assessment: "Excellent work. Calculations correct, notes clear."
        │
        ▼
Manager: Adds Quality Review Note
Action: Clicks "Add Review Note" (if available)
Type: "Quality Review" or "Manager Approval"
        │ (Available to managers? ⚠️ UNCLEAR)
        │
        ▼
Content: "Excellent work on this case. Calculations are accurate and member communications were professional."
        │
        ▼
Visibility: Tech + Admin can see
Member: Cannot see (internal review)
        │
        ▼
Tech: Sees Manager Feedback
Dashboard badge: "Manager reviewed your case"
        ⚠️ UNCLEAR - Does tech get notified?
        │
        ▼
Tech: Reads positive feedback
Feels validated ✅
        │
        ▼
SCENARIO B: ISSUES FOUND
Manager: Reviews work quality
Issue identified: "Credit calculation in Q3 appears incorrect"
        │
        ▼
Manager: Wants to reopen case
Action: Clicks "Reopen for Correction"
        ⚠️ **MISSING** - No reopen button
        │
        ▼
IF FEATURE EXISTS:
├─ Status: completed → reopen_for_correction (or similar)
├─ Assigned back to: Original tech
├─ Note: "Manager found issue - please review Q3 calculation"
└─ Tech: Gets notification to fix
        │
        ▼
Tech: Receives Reopen Notification
Dashboard: "Case reopened for correction"
        │ (Email: ⚠️ UNCLEAR)
        │
        ▼
Tech: Investigates Issue
Recalculates Q3 credits
Finds: Manager is correct
        │
        ▼
Tech: Updates Report
Uploads corrected report
Marks: Complete again
        │
        ▼
Status: reopen_for_correction → completed
        │
        ▼
Manager: Sees correction
Can review again
        │
        ▼
END: Case finalized

CURRENT STATE:
├─ Manager can view completed cases ✅
├─ Manager can add notes ⚠️ UNCLEAR
├─ Tech sees manager notes ⚠️ UNCLEAR
└─ Manager can reopen case ❌ MISSING

TOTAL TIME: Varies (depends on review)
COMMUNICATIONS: 1 (manager feedback or reopen notification)
STATUS CHANGES: completed (or completed → reopen → completed if issues)
HOLDS: 0
```

## Implementation Status

| Feature | Status | Notes |
|---------|--------|-------|
| Manager dashboard | ✅ WORKS | Managers can see completed cases |
| Case detail access | ✅ WORKS | Can view full case |
| Add review notes | ⚠️ UNCLEAR | Can managers add notes? |
| Note visibility | ⚠️ UNCLEAR | Tech can see manager notes? |
| Tech notification | ⚠️ UNCLEAR | Does tech get email on review? |
| Reopen functionality | ❌ **MISSING** | No way to reopen case |
| Reopen status | ❌ **MISSING** | No status for reopened cases |
| Reopen notification | ❌ **MISSING** | Tech not notified |

## Gaps to Address

1. **Manager Review Workflow - NEEDS CLARIFICATION**
   - Can managers add notes to completed cases?
   - Are notes visible to tech?
   - How are notes different from tech notes?
   - **Priority:** MEDIUM
   - **Action:** Verify current implementation

2. **Case Reopening - MISSING FEATURE**
   - Manager needs ability to reopen completed cases for correction
   - New status needed: reopen_for_correction or pending_revision
   - Tech needs notification
   - Case should move back to tech's queue
   - **Priority:** HIGH
   - **Effort:** 6-8 hours

---

## SUMMARY MATRIX

| Scenario | Status | Holds | Reassign | Comms | Gaps |
|----------|--------|-------|----------|-------|------|
| 1 | ✅ | 0 | 0 | 3-4 | ⚠️ Email notifications unclear |
| 2 | ✅ | 0 | 0 | 4-5 | ⚠️ Resubmit notification unclear |
| 3 | ⚠️ | 1 | 0 | 3-5 | ❌ Hold duration UI missing |
| 4 | ✅ | 0 | 1 | 2-3 | ⚠️ Reassign notifications unclear |
| 5 | ❌ | 0 | 0 | 1 | ❌ CRITICAL: Cron job |
| 6 | ✅ | 0 | 0 | 3 | ✅ Complete |
| 7 | ⚠️ | 2 | 0 | 5+ | ⚠️ Hold history not visible |
| 8 | ✅ | 0 | 0 | 1 | ✅ Complete |
| 9 | ⚠️ | 0 | 0 | 3+ | ⚠️ Email notifications unclear |
| 10 | ❌ | 0 | 0 | 1 | ❌ Reopen missing |

---

## CRITICAL FINDINGS

### 🔴 MUST FIX - BLOCKING

1. **CRON JOB (Scenario 5)**
   - Scheduled releases completely depend on this
   - Status: UNKNOWN - need to verify
   - Impact: Without this, scheduled releases don't work
   - Timeline: 2 hours to verify, 6-8 hours to build if missing

2. **HOLD DURATION UI (Scenario 3)**
   - Currently only indefinite holds possible
   - Should offer: 2h, 4h, 8h, 1d, indefinite, custom
   - Impact: Can't set short holds
   - Timeline: 4-6 hours

3. **EMAIL NOTIFICATIONS (Scenarios 1, 2, 3, 4, 9)**
   - Multiple unclear paths
   - Does tech get email when member comments?
   - Does member get email when tech asks question?
   - Does tech get email when case resubmitted?
   - Impact: Workflow depends on notifications
   - Timeline: 2-4 hours to verify/implement

### 🟡 HIGH PRIORITY

4. **Case Reopening (Scenario 10)**
   - Managers need to reopen completed cases
   - Impact: Can't fix errors after completion
   - Timeline: 6-8 hours

5. **Hold History Visibility (Scenario 7)**
   - Multiple holds may overwrite data
   - History not visible in UI
   - Impact: Can't track hold pattern
   - Timeline: 4-6 hours

6. **Manager Review Workflow (Scenario 10)**
   - Unclear if managers can add notes
   - Unclear if tech sees notes
   - Impact: Quality assurance workflow unclear
   - Timeline: 2-3 hours to clarify/verify

---

This expanded version provides the detailed analysis you requested for each scenario.
