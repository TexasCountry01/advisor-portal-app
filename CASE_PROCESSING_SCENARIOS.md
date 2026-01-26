# Case Processing Scenarios: From Creation to Completion

## Overview

This document maps realistic case scenarios showing different pathways a case can take from member creation through completion, resubmission, modification, and beyond. Each scenario identifies required functionality and flags what may be missing.

---

## SCENARIO 1: Happy Path - Standard Processing

### Timeline & Interactions

**Phase 1: Member Creation & Submission (T+0 hours)**

1. **Member logs in to portal**
   - Access: Member Dashboard
   - Required Functionality: ✅ Member authentication & dashboard
   - Notes: Member sees "Create New Case" button

2. **Member creates draft case**
   - Action: Fills Federal Fact Finder (FFF) form, uploads supporting docs
   - Fields: Employee info, workshop code, num_reports_requested, urgency
   - Saves as: Status = 'draft'
   - Required Functionality: ✅ Draft case creation, autosave
   - UI: "Save as Draft" button
   - **Communication:** None yet

3. **Member reviews and submits case**
   - Action: Clicks "Submit Case" button
   - Validation: Checks FFF completeness, document uploads
   - Status change: draft → submitted
   - Required Functionality: ✅ Case submission with validation
   - **Communication:** ❓ Does member get confirmation email?
   - Database: `date_submitted`, `submitted_by` fields set

---

**Phase 2: Queue & Technician Acceptance (T+0 to T+2 hours)**

4. **Case appears in unassigned queue**
   - Location: Technician Dashboard → "Unassigned Cases"
   - Status: submitted
   - Required Functionality: ✅ Queue system works
   - Fields visible: Case ID, Member Name, Urgency, Docs count
   - **Communication:** ❓ Notification to available technicians?

5. **Technician reviews case**
   - Action: Clicks "Review & Accept" button
   - Screen: Pre-acceptance review modal
   - Reviews: FFF data, supporting documents
   - Required Functionality: ✅ Case detail view, document viewer
   - Checks: 
     - FFF complete ✅
     - Docs present ✅
     - Credit value appropriate ✅
     - Tier assignment possible ✅

6. **Technician accepts case**
   - Decision: Accept with Tier = 1, Credit = 1.5
   - Action: Clicks "Accept & Assign" button
   - Assignment: Assigns to self (or different tech)
   - Status change: submitted → accepted
   - Required Functionality: ✅ Accept view with tier/assignment
   - Database Updates:
     - `status` = 'accepted'
     - `assigned_to` = technician
     - `tier` = tier_1
     - `date_accepted` = now()
     - `accepted_by` = technician
   - **Communication:** ❓ Email to member: "Your case has been accepted"?
   - Audit Trail: ✅ `case_accepted` logged

7. **Case moves to technician's active queue**
   - Location: Technician Dashboard → "My Cases" → "New"
   - Status: accepted
   - Technician can now: View full details, add notes, request docs

---

**Phase 3: Investigation & Research (T+2 hours to T+24 hours)**

8. **Technician reviews case details**
   - Action: Opens case in detail view
   - Accesses: 
     - FFF data ✅
     - Member documents ✅
     - Communication/notes area ✅
     - Member contact info ✅
   - Required Functionality: All accessible

9. **Technician performs investigation**
   - External research (credentials, employment verification, etc.)
   - No system interaction
   - Status: accepted (no status change)
   - Duration: Varies (4-12 hours typical)

10. **Technician adds internal notes**
    - Action: Types notes in "Internal Notes" section
    - Content: Research findings, validation results, concerns
    - Visibility: Tech + Admin only (not member)
    - Required Functionality: ✅ Internal notes with is_internal=True
    - **Communication:** None (internal only)
    - Audit Trail: ✅ `note_added` logged

11. **Technician has quick question for member**
    - Action: Adds public comment in notes section
    - Content: "Can you clarify your employment dates in Q3?"
    - Visibility: Member can see
    - Required Functionality: ✅ Public comments
    - **Communication:** ❓ Email to member with question?
    - Member sees: 
      - In-app notification on next login
      - Email notification (if enabled)
      - Dashboard badge showing unread messages
    - Database: Stored in CaseMessage or CaseNote with is_internal=False

12. **Member responds to question**
    - Action: Member logs in, sees question
    - Response: Types answer in public comment box
    - Status: case stays in 'accepted'
    - Required Functionality: ✅ Member can add comments
    - **Communication:** ❓ Tech notified of member response?
    - Audit Trail: ✅ `member_comment_added` or similar

13. **Technician reads member response**
    - Action: Case has `has_member_updates` flag set
    - Technician sees: Badge on dashboard "⚠️ Member has updated case"
    - Clicks case to read updates
    - Flag reset: `has_member_updates` = False
    - **Communication:** ❓ Notification that member responded?

---

**Phase 4: Report Generation & Completion (T+24 to T+30 hours)**

14. **Technician completes investigation**
    - Writes formal report
    - Uploads as PDF/document
    - Action: Clicks "Upload Report" button
    - Status: case still 'accepted'
    - Required Functionality: ✅ Document upload for reports
    - Document type: 'report'
    - Audit Trail: ✅ `document_uploaded` logged

15. **Technician marks case as complete**
    - Action: Clicks "Mark as Complete" button
    - Decision point: Select release timing:
      - ✅ Release Now (0 hours)
      - ✅ Use Admin Default (e.g., 2 hours)
      - ✅ Schedule Release (future date/time up to 60 days)
    - Selection: "Release Now"
    - Status change: accepted → completed
    - Database Updates:
      - `status` = 'completed'
      - `date_completed` = now()
      - `actual_release_date` = now() (immediate release)
      - `scheduled_release_date` = None
    - Required Functionality: ✅ Completion view with release options
    - Audit Trail: ✅ `case_updated` logged

16. **Member receives report**
    - Immediate: (release now = 0 delay)
    - Member dashboard shows: "Your case is ready" badge
    - Member can: Download report, view technical notes
    - **Communication:** ✅ Email sent: "Your case report is ready"
    - Member notification: ✅ In-app badge
    - Member email: ✅ Sent with report link
    - Audit Trail: ✅ `email_notification_sent` logged

---

**Phase 5: Closure**

17. **Case moves to archive**
    - Location: Technician Dashboard → "Completed Cases"
    - Member Dashboard: "Completed Cases" section
    - Can still: View report, download docs, add comments (if enabled)
    - Status: completed

18. **End of Scenario**
    - Total duration: ~24 hours
    - Communications: 2-3 (member question, tech response, completion email)
    - Status changes: draft → submitted → accepted → completed
    - Holds: 0

---

## SCENARIO 2: Case with Information Requests

### Timeline & Interactions

**Phase 1: Member Creates & Submits (T+0)**
- Same as Scenario 1

**Phase 2: Technician Reviews - NEEDS MORE INFO**

1. **Technician reviews case**
   - Finds: Critical sections missing in FFF
   - Decision: Reject and request more info
   - Action: Clicks "Request More Info" button
   - Modal: Select rejection reason
   - Selection: "Federal Fact Finder incomplete - missing required sections"
   - Add notes: "Missing Q3-Q4 employment history, need pay stubs"
   - Required Functionality: ✅ Rejection modal with reason selection
   - Status change: submitted → needs_resubmission
   - **Communication:** ✅ Email sent to member with requirements
   - Audit Trail: ✅ `case_rejected` or status_changed logged
   - Case moves: Back to member's "Cases Needing Attention" section

---

**Phase 3: Member Responds to Requests**

2. **Member receives rejection email**
   - Sees: Requirements and what's missing
   - Dashboard: Shows case needs resubmission
   - Action: Uploads additional documents (pay stubs, employment letters)
   - Status: still needs_resubmission
   - Required Functionality: ✅ Member can upload to incomplete case
   - **Communication:** ❓ Tech notified of upload?
   - Database: New CaseDocument records created
   - Audit Trail: ✅ `document_uploaded` or `member_document_uploaded` logged

3. **Member clicks "Resubmit Case"**
   - Action: Case available for technician review again
   - Status change: needs_resubmission → submitted (or resubmitted)
   - Required Functionality: ✅ Resubmit functionality
   - **Communication:** ❓ Tech notified case is resubmitted?
   - Dashboard: Case appears in tech's "Unassigned Cases" or "To Review"
   - Audit Trail: ✅ `case_resubmitted` logged

---

**Phase 4: Technician Re-Reviews & Accepts**

4. **Technician reviews resubmitted case**
   - Checks new documents
   - Verifies: All missing info now present
   - Decision: Accept case
   - Same as Scenario 1 Phase 2, step 6
   - Status change: resubmitted/submitted → accepted
   - Continues with normal investigation...

---

**End of Scenario 2**
- Total duration: ~36 hours (including member response time)
- Communications: 3-4 (rejection email, potential question, resubmit notification, completion)
- Status changes: draft → submitted → needs_resubmission → submitted → accepted → completed
- Holds: 0
- Rejections: 1

---

## SCENARIO 3: Case Put on Hold

### Timeline & Interactions

**Phase 1-3: Normal (Same as Scenario 1)**
- Member creates, submits
- Tech accepts
- Tech investigates

**Phase 4: Technician Encounters Issue - NEEDS TO PAUSE**

1. **Technician discovers missing information**
   - Problem: Critical details needed but not in case
   - Examples: 
     - Waiting for member to confirm employment dates
     - Need external document (medical records)
     - Awaiting admin approval on policy interpretation
   - Decision: Put case on hold instead of rejecting
   - Why hold vs reject? 
     - Case is mostly complete
     - Just need one specific thing
     - Doesn't warrant full resubmission

2. **Technician puts case on hold**
   - Action: Clicks "Put on Hold" button
   - Modal appears: Select hold reason
   - Options: ❓ Hard-coded list or free-text?
   - Selection: "Waiting for member to provide additional documentation"
   - Duration: ❓ Indefinite or select duration (2h, 4h, 8h, 1 day, custom)?
   - Current state: Only indefinite available
   - **Gap #1: Duration not in UI** ⚠️
   - Status change: accepted → hold
   - Database Updates:
     - `status` = 'hold'
     - `assigned_to` = technician (PRESERVED ✅)
     - `hold_reason` = "Waiting for member to provide documentation"
     - `hold_start_date` = now()
     - `hold_end_date` = None (if indefinite) or future date
     - `hold_duration_days` = 0 (if indefinite) or duration value
   - Required Functionality: ✅ Put on hold with reason
   - Audit Trail: ✅ `case_held` logged with reason

3. **Member notified of hold**
   - **Communication:** ✅ Email sent to member:
     - Subject: "Your case has been placed on hold"
     - Body: Case link, hold reason, what's needed
     - "We're waiting for: Employment verification documents"
     - "Please upload documents to this case"
   - In-app notification: ✅ Member sees notification badge
   - Dashboard: Member sees "Cases on Hold" section with count
   - Member can: Still view case, upload documents
   - Required Functionality: ✅ Member notifications
   - Audit Trail: ✅ `notification_created` logged

---

**Phase 5: Member Responds While on Hold**

4. **Member sees case on hold**
   - Dashboard: "Cases on Hold" alert showing
   - Clicks case to view
   - Sees: Hold reason, technician contact info
   - Action: Clicks "Upload Documents" button
   - Uploads: Employment verification letter
   - Status: case still 'hold' (no status change)
   - Required Functionality: ✅ Member can upload while on hold
   - Audit Trail: ✅ `document_uploaded` logged
   - **Communication:** ❓ Tech notified of upload during hold?

5. **Member adds comment**
   - Action: Types in notes: "I've uploaded the employment letter. Let me know if you need anything else."
   - Visibility: Public (technician can see)
   - Status: case still 'hold'
   - Required Functionality: ✅ Member can comment while on hold
   - **Communication:** ❓ Tech notified of comment?
   - Audit Trail: ✅ `member_comment_added` logged

---

**Phase 6: Technician Resumes from Hold**

6. **Technician sees member has uploaded**
   - Dashboard: Shows "Member has updates" badge or similar
   - Clicks case to review
   - Sees: New documents, member comment
   - Reviews: Employment verification is complete
   - Decision: Resume case processing

7. **Technician resumes from hold**
   - Action: Clicks "Resume Processing" button
   - Modal: "Add reason for resuming (optional)" - text field
   - Entry: "Employment verification received and verified"
   - Status change: hold → accepted (back to active work)
   - Database Updates:
     - `status` = 'accepted'
     - `assigned_to` = technician (still same)
     - `hold_end_date` = now()
     - `hold_resume_reason` = "Employment verification received and verified"
   - Required Functionality: ✅ Resume from hold
   - Audit Trail: ✅ `case_resumed` logged with reason
   - **Communication:** ✅ Email to member: "Your case processing has resumed"

8. **Case continues normal processing**
   - Technician completes investigation
   - Uploads report
   - Marks complete
   - Same as Scenario 1 Phase 4

---

**End of Scenario 3**
- Total duration: ~48 hours (includes member response time)
- Communications: 4-5 (hold notification, potential clarifications, resume notification, completion)
- Status changes: draft → submitted → accepted → **hold → accepted** → completed
- Holds: 1 (indefinite, ~24 hour duration)
- **Gaps Found:**
  - ❌ Duration options not in UI
  - ❓ Tech notification when member uploads during hold?
  - ❓ Tech notification when member comments during hold?

---

## SCENARIO 4: Case Reassignment

### Timeline & Interactions

**Phase 1-3: Normal (Same as Scenario 1)**
- Member creates, submits
- Tech accepts case
- Tech investigates

**Phase 4: Technician Unavailable - NEEDS REASSIGNMENT**

1. **Technician needs to reassign**
   - Situation: Tech gets sick, takes vacation, or overwhelmed with queue
   - Decision: Reassign to another technician
   - Action: Opens case, clicks "Reassign" button (or similar)
   - Required Functionality: ✅ Reassign interface
   - Modal appears: Select new technician
   - Filters: Only active technicians of appropriate level
   - Tier constraint: If case is Tier 2, only show Level 2+ technicians
   - Required Functionality: ✅ Tier-level filtering on reassignment
   - Selection: Selects "Tech B" (Level 2)
   - Optional: Add reason: "I'm going on vacation - please take this"

2. **Case reassigned**
   - Status change: accepted → accepted (no status change, just reassignment)
   - Database Updates:
     - `assigned_to` = Tech B
     - `previously_assigned_to` = Tech A (if tracked)
     - `reassignment_date` = now()
     - `reassignment_reason` = "Going on vacation"
   - Required Functionality: ✅ Reassignment logic
   - Audit Trail: ✅ `case_reassigned` logged
   - **Communication:** ✅ Email to Tech B: "Case [ID] has been reassigned to you"
   - **Communication:** ✅ Email to member (optional): "Your case has been reassigned to Tech B"?

3. **New technician takes over**
   - Tech B logs in
   - Case appears in: "My Cases" section of dashboard
   - Status: accepted (already assigned, ready to work)
   - Tech B can: Continue investigation, add notes, etc.
   - No context loss (all previous notes visible)
   - Required Functionality: ✅ Full case history visible to new tech

---

**Variant: Reassignment During Hold**

4. **Case is on hold when reassigned**
   - Status: hold
   - Action: Original tech reassigns to Tech B
   - Status change: hold → hold (no status change)
   - Database: `assigned_to` = Tech B
   - **Communication:** ✅ Email to Tech B: "Case [ID] on hold reassigned to you. Hold reason: [reason]"
   - Tech B can: Resume from hold or continue hold
   - Required Functionality: ✅ Preserve hold status on reassignment

---

**End of Scenario 4**
- Total duration: Varies (same day to days depending on when reassignment happens)
- Communications: 2 (notification to new tech, optional to member)
- Status changes: None (just assignment change)
- Holds: 0 or 1 (if case already on hold)

---

## SCENARIO 5: Case Completed with Scheduled Release

### Timeline & Interactions

**Phase 1-4: Investigation & Report (Same as Scenario 1)**
- Create, submit, accept, investigate

**Phase 5: Completion with Future Release**

1. **Technician marks case complete**
   - Uploads report
   - Decision: Don't release immediately
   - Reason: Wants manager review before member sees it
   - Action: Clicks "Mark as Complete"
   - Modal: Release timing options
   - Selection: "Schedule Release" → Date/Time picker
   - Selected: "Tomorrow at 9:00 AM CST"
   - Status change: accepted → completed
   - Database Updates:
     - `status` = 'completed'
     - `date_completed` = now()
     - `scheduled_release_date` = Tomorrow 9:00 AM CST
     - `actual_release_date` = None (not released yet)
     - `scheduled_email_date` = Tomorrow 9:00 AM CST
     - `actual_email_sent_date` = None
   - Required Functionality: ✅ Scheduled release with date/time picker
   - Validation: ✅ Date must be tomorrow to 60 days out
   - **Communication:** None yet to member (case not released)
   - Audit Trail: ✅ `case_updated` logged with scheduled release date

2. **Case status shows "Pending Release"**
   - Location: Technician Dashboard → "My Cases" → "Pending Release"
   - Shows: Scheduled release time
   - Can still: Add notes, "Release Immediately" override
   - Member cannot see: Case is not yet visible

3. **Cron job processes scheduled release**
   - Time: Tomorrow 9:00 AM CST
   - Action: Cron job finds cases with `scheduled_release_date` <= now()
   - Processing:
     - `actual_release_date` = now()
     - `actual_email_sent_date` = now()
     - Case marked as ready for member download
   - Required Functionality: ✅ Cron job for scheduled releases
   - **Gap #2: Cron job verification unclear** ⚠️
   - **Communication:** ✅ Email sent to member at exact scheduled time
   - Audit Trail: ✅ `email_notification_sent` logged

4. **Member receives notification**
   - Email arrives: "Your case report is ready"
   - Dashboard: "Case Ready" badge appears
   - Member can: Download report, view technical notes
   - Status: completed

---

**End of Scenario 5**
- Total duration: ~24+ hours (includes scheduled delay)
- Communications: 1 (completion email at scheduled time)
- Status changes: draft → submitted → accepted → completed (with scheduled release)
- Holds: 0
- **Gaps Found:**
  - ❓ Cron job status unclear - need verification

---

## SCENARIO 6: Member Resubmits Completed Case for Modification

### Timeline & Interactions

**Phase 1-5: Normal completion (Same as Scenario 1)**
- Create, submit, accept, investigate, complete

**Phase 6: Member Reviews & Wants Modification**

1. **Member receives completed case**
   - Downloads report
   - Reviews technical notes
   - Notices: Technician made error in calculations
   - Decision: Request modification

2. **Member checks modification eligibility**
   - Requirements: 
     - Case must be completed ✅
     - Within 60 days of release ✅ (just released)
   - Sees: "Request a Mod" button in case detail
   - ✅ Button visible and enabled
   - Clicks button
   - Required Functionality: ✅ Request modification modal

3. **Member fills modification request**
   - Modal appears: "Request a Modification"
   - Fields: Reason for modification (required)
   - Input: "Please recalculate Q3-Q4 credits. I believe the projection is too low."
   - Optional: Upload new documents if needed
   - Action: Clicks "Submit Modification Request"
   - Status: Original case stays 'completed'
   - Required Functionality: ✅ Modification request capture
   - Audit Trail: ✅ `member_comment_added` or similar logged

4. **New case created for modification**
   - Triggered by: Member's modification request
   - New case generated:
     - `external_case_id` = New ID (linked series)
     - `status` = 'submitted'
     - `original_case` = Link to original case (FK)
     - `member` = Same member
     - `workshop_code` = Same
     - `created_by` = member
     - `date_submitted` = now()
     - **Copies from original:**
       - Employee name
       - Credit information
       - Tier
   - Required Functionality: ✅ Modification case creation with linking
   - Audit Trail: ✅ New case_created logged
   - **Communication:** ✅ Email to member: "New case [ID] created for your modification request"

5. **Original technician notified**
   - Message: Modification request notification
   - Details: Reason, new case ID
   - Dashboard: Sees badge "Member requested modification"
   - Optional: Can prioritize modification case
   - Required Functionality: ✅ Tech notification of modification
   - **Communication:** ✅ Email to tech: "Modification requested for case [ID]: New case [ID]"

6. **Original technician reviews modification**
   - Clicks "Review" or new case ID
   - Navigates to modification case (status = submitted)
   - Reviews: Original case details + modification reason
   - Available in UI: Link to original case for comparison
   - Required Functionality: ✅ Bidirectional case linking visible
   - Shows: "This is a modification of case [original ID] - View Original"

7. **Modification case follows normal workflow**
   - Tech accepts → investigates → completes
   - Same as Scenario 1 from acceptance onwards
   - Reassignment: Tech who completed original gets priority notification
   - Auto-assignment: When modification marked complete, auto-assign back to original tech
   - Required Functionality: ✅ Auto-assignment of mod case to original tech
   - Audit Trail: ✅ Modification case lifecycle logged separately

---

**Phase 7: Modification Complete & Released**

8. **Tech completes modification case**
   - Status change: accepted → completed
   - Releases: Immediately or scheduled
   - New report generated
   - **Communication:** ✅ Email to member: "Your modification request is complete"

9. **Member receives modification results**
   - Dashboard: Both original and modification visible
   - Can compare: Original report vs modified report
   - Original case view: Shows "Modification Cases: [list with links]"
   - Modification case view: Shows "Original Case: [link]"
   - Required Functionality: ✅ Bidirectional linking in UI
   - Member can: Quick-switch between cases with buttons

---

**End of Scenario 6**
- Total duration: ~24-48 hours (depending on modification complexity)
- Communications: 3-4 (modification created, tech notified, completion, member notified)
- Original case status changes: None (stays completed)
- Modification case status changes: submitted → accepted → completed
- Holds: Possibly (if mod case needs info)
- New feature: Modification workflow complete ✅

---

## SCENARIO 7: Complex Hold & Resume Cycle

### Timeline & Interactions

**Phase 1-3: Normal (Same as Scenario 1)**
- Member creates, submits, tech accepts

**Phase 4: First Hold**

1. **Tech puts case on hold (Reason: Waiting for external verification)**
   - Status: accepted → hold
   - Reason: "Waiting for employment verification from employer"
   - Duration: Indefinite
   - Member notified ✅
   - **Communication:** Email to member

2. **Member uploads documents**
   - Uploads employer verification letter
   - Status: still hold (case doesn't auto-resume)
   - **Communication:** ❓ Tech notified?

---

**Phase 5: Technician Reviews & Resumes First Hold**

3. **Tech checks case**
   - Sees member uploaded doc
   - Reviews: Verification letter looks good
   - Decision: Resume but need one more thing
   - Action: Clicks "Resume Processing"
   - Status: hold → accepted
   - Reason: "Employment verification received. Need to review with manager before proceeding."
   - **Communication:** ✅ Email to member

---

**Phase 6: Investigation Continues**

4. **Tech investigates further**
   - Adds internal notes about verification
   - Works on other aspects of case
   - Completes most research

---

**Phase 7: Second Hold (Different Reason)**

5. **Tech encounters another issue**
   - Problem: Calculation shows member over credit limit (policy question)
   - Decision: Put back on hold to wait for manager approval
   - Status: accepted → hold (again)
   - Reason: "Awaiting manager approval on credit limit exception"
   - Duration: Indefinite
   - Member notified ✅
   - **Communication:** Email to member

---

**Phase 8: Technician Resumes Second Hold**

6. **Manager approves exception**
   - Tech gets manager sign-off
   - Tech marks case ready
   - Status: hold → accepted
   - Reason: "Manager approved credit limit exception"
   - **Communication:** Email to member

---

**Phase 9: Completion**

7. **Tech completes case**
   - No more holds needed
   - Status: accepted → completed
   - Release: Immediate
   - **Communication:** Completion email

---

**End of Scenario 7**
- Total duration: ~72 hours
- Communications: 5+ (hold notifications, resume notifications, completion)
- Status changes: submitted → accepted → **hold → accepted → hold → accepted** → completed
- Holds: 2 (back-to-back different reasons)
- **Questions:**
  - ❓ Can case be put on hold multiple times? (Should be yes, but verify)
  - ❓ Does UI show hold history? (Should be yes)
  - ❓ Does tech get notified when member uploads during hold? (Should be yes)

---

## SCENARIO 8: Case Completion Outside Time Window

### Timeline & Interactions

**Phase 1-5: Normal completion (Same as Scenario 1)**

**Phase 6: Member Tries Modification After 60 Days**

1. **Member views completed case**
   - It's been 65 days since release
   - Button check: "Request a Mod" button
   - Status: ❓ Button disabled or error message?
   - Required Functionality: ✅ 60-day limit enforced
   - Attempts: Tries to click (should be disabled or show message)

2. **System blocks modification**
   - Button: Disabled with tooltip
   - OR Error: "Modification requests only available within 60 days of completion"
   - Member cannot proceed
   - **Communication:** None (UI handles it)
   - Required Functionality: ✅ 60-day validation

3. **Member alternative: Ask a Question**
   - Decision: Click "Ask a Question" button instead
   - No time limit on questions
   - Can communicate with tech about corrections
   - Required Functionality: ✅ Unlimited question capability
   - Message: "There seems to be an error in the Q3-Q4 calculation. Can you review?"
   - Status: Case stays completed
   - **Communication:** Question sent, tech can respond

---

**End of Scenario 8**
- Total duration: 65+ days
- Communications: 1 (member question after expiration)
- Status changes: None (stays completed)
- Holds: 0
- Modifications: 0 (blocked by 60-day window)

---

## SCENARIO 9: Case with Multiple Document Requests

### Timeline & Interactions

**Phase 1-3: Normal (Same as Scenario 1)**
- Create, submit, accept

**Phase 4: Investigation with Communication Loop**

1. **Technician reviewing case**
   - Needs: Medical documentation
   - Decision: Request from member via comment
   - Action: Adds public comment
   - Message: "Can you upload a recent medical report? We need to verify your current status."
   - Status: case stays 'accepted'
   - **Communication:** ❓ Email to member with question?
   - Audit Trail: ✅ Comment logged

2. **Member responds to request**
   - Dashboard: Sees comment badge
   - Uploads: Medical report PDF
   - Adds comment: "Here's my recent medical report from Dr. Smith dated [date]"
   - Status: case stays 'accepted'
   - **Communication:** ❓ Tech notified of response?
   - Audit Trail: ✅ Document and comment logged

3. **Tech requests second clarification**
   - Reviews medical report
   - Needs: Clarification on specific dates
   - Adds comment: "Great, but can you clarify the treatment dates listed in Section 3? It looks incomplete."
   - **Communication:** Email to member
   - Audit Trail: ✅ Comment logged

4. **Member provides clarification**
   - Uploads: Supplementary document with dates
   - Comment: "I've attached a detailed timeline. Let me know if this helps."
   - Status: case stays 'accepted'
   - Audit Trail: ✅ Logged

5. **Tech has final question**
   - Comment: "Perfect! One last thing - do you have any employment history after [date]?"
   - Status: case stays 'accepted'
   - **Communication:** Email to member

6. **Member provides final info**
   - Comment: "No, I haven't worked since [date]. I've been on benefits."
   - Uploads: Optional supporting docs
   - Status: case stays 'accepted'

7. **Investigation complete**
   - Tech proceeds with case completion
   - All info gathered through iterative back-and-forth
   - Status: accepted → completed
   - **Communication:** Completion email

---

**End of Scenario 9**
- Total duration: ~40-60 hours
- Communications: 5+ (request, response, question, clarification, completion)
- Document requests: 3
- Status changes: submitted → accepted → completed
- Holds: 0 (back-and-forth without holding)
- **Questions:**
  - ✅ Member can upload? Yes
  - ✅ Tech can request? Yes
  - ✅ Communication visible? Yes
  - **Gap:** Does system notify tech when member responds? Unclear

---

## SCENARIO 10: Manager Quality Review Workflow

### Timeline & Interactions

**Phase 1-5: Normal completion (Same as Scenario 1)**
- Create through completion

**Phase 6: Manager Reviews Completed Case**

1. **Manager sees completed case**
   - Dashboard: Shows "Completed Cases" 
   - Can review: All completed cases
   - Selection: Clicks case to review
   - Sees: Full case details, tech notes, report
   - Required Functionality: ✅ Manager dashboard with case list
   - Permission: ✅ Can view completed cases

2. **Manager adds quality review note**
   - Action: Clicks "Add Note" (if available to managers)
   - Type: "Quality Review" or similar
   - Content: "Great work on this one. Calculations are accurate and notes are clear."
   - Visibility: Tech and admin can see
   - Status: case stays 'completed'
   - Required Functionality: ✅ Manager notes capability
   - Audit Trail: ✅ Review note logged

3. **Technician sees manager feedback**
   - Dashboard notification: ❓ "Manager reviewed your case"?
   - Case detail: Shows manager note
   - Status: case stays 'completed'
   - Required Functionality: ❓ Manager note visibility to tech?

---

**Variant: Manager Finds Issue**

4. **Manager identifies problem**
   - Content: "I found an error in the credit calculation. Need to reopen this."
   - Decision: Reopen case for correction
   - Action: ❓ "Reopen" button or reassign to tech?
   - Required Functionality: ❓ Case reopening capability?
   - Status change: completed → ??? (reopen_for_correction? pending_revision?)

---

**End of Scenario 10**
- Total duration: Varies
- Communications: 0-1 (manager feedback)
- Status changes: None (or reopen if issues found)
- Holds: 0
- **Gaps Found:**
  - ❓ Can manager reopen completed cases?
  - ❓ What status used for reopened cases?
  - ❓ Tech notified of manager feedback?

---

## FUNCTIONALITY CHECKLIST

### Critical Path (Must Have)

| Functionality | Scenario | Status | Notes |
|--------------|----------|--------|-------|
| Member create draft case | S1 | ✅ | Works |
| Member submit case | S1 | ✅ | Works |
| Tech review & accept | S1 | ✅ | Works |
| Tech adds internal notes | S1 | ✅ | Works |
| Tech adds public comments | S1 | ✅ | Works |
| Member responds to comments | S1 | ✅ | Works |
| Tech uploads report | S1 | ✅ | Works |
| Tech marks complete | S1 | ✅ | Works |
| Member gets notification | S1 | ✅ | Works |
| Case appears in completed | S1 | ✅ | Works |

### Hold Workflow (High Priority)

| Functionality | Scenario | Status | Notes |
|--------------|----------|--------|-------|
| Put case on hold | S3 | ✅ | Works - indefinite |
| Hold with duration options | S3 | ⚠️ | **MISSING** - No UI for 2h/4h/8h/1d |
| Member notified of hold | S3 | ✅ | Email + in-app notification |
| Member can upload during hold | S3 | ✅ | Works |
| Member can comment during hold | S3 | ✅ | Works |
| Resume from hold | S3 | ✅ | Works |
| Hold history tracked | S3 | ⚠️ | Logged but not visible in UI |

### Requests & Resubmission (High Priority)

| Functionality | Scenario | Status | Notes |
|--------------|----------|--------|-------|
| Request more info | S2 | ✅ | Rejection workflow works |
| Member receives requirements | S2 | ✅ | Email sent |
| Member resubmits | S2 | ✅ | Works |
| Tech notified of resubmit | S2 | ⚠️ | Unclear if auto-notified |

### Modification Requests (Medium Priority)

| Functionality | Scenario | Status | Notes |
|--------------|----------|--------|-------|
| Request modification button | S6 | ✅ | Works |
| 60-day limit enforcement | S6 | ✅ | Works |
| New case created for mod | S6 | ✅ | Works |
| Original case linked | S6 | ✅ | original_case FK |
| Bidirectional linking in UI | S6 | ✅ | Recently implemented |
| Tech notified of mod | S6 | ✅ | Works |
| Auto-assign mod to original tech | S6 | ✅ | Works when mod completed |
| Member can compare cases | S6 | ✅ | Bidirectional UI links |

### Reassignment (Medium Priority)

| Functionality | Scenario | Status | Notes |
|--------------|----------|--------|-------|
| Reassign case | S4 | ✅ | Works |
| Tier-level validation on reassign | S4 | ✅ | Only show appropriate techs |
| New tech notified | S4 | ⚠️ | Check if email sent |
| Member notified (optional) | S4 | ⚠️ | Unclear if implemented |
| Hold preserved on reassign | S4 | ⚠️ | Should preserve but not verified |

### Release Timing (Medium Priority)

| Functionality | Scenario | Status | Notes |
|--------------|----------|--------|-------|
| Immediate release | S1 | ✅ | Works |
| Scheduled release | S5 | ✅ | Date/time picker |
| 60-day max on schedule | S5 | ⚠️ | Check validation |
| Cron job processes release | S5 | ❌ | **NEED TO VERIFY** |
| Cron sends email | S5 | ❌ | **NEED TO VERIFY** |
| Release date logged | S5 | ✅ | actual_release_date set |
| Email date logged | S5 | ✅ | actual_email_sent_date set |

### Communication (High Priority)

| Functionality | Scenario | Status | Notes |
|--------------|----------|--------|-------|
| Tech → Member comments | S1,S9 | ✅ | Works |
| Member → Tech comments | S1,S9 | ✅ | Works |
| Tech internal notes | S1 | ✅ | is_internal=True |
| Member doesn't see internal | S1 | ✅ | Hidden from member |
| Case message unread tracking | S1 | ✅ | UnreadMessage model |
| Member gets email on comment | S1 | ⚠️ | **UNCLEAR** - Verify |
| Tech gets email on comment | S9 | ⚠️ | **UNCLEAR** - Verify |
| Tech notified of member update | S3 | ⚠️ | has_member_updates flag exists |
| Comment thread visible | S9 | ✅ | Chronological view |

### Management Workflows (Medium Priority)

| Functionality | Scenario | Status | Notes |
|--------------|----------|--------|-------|
| Manager see completed cases | S10 | ✅ | Manager dashboard |
| Manager add review notes | S10 | ⚠️ | Unclear if available |
| Tech sees manager notes | S10 | ⚠️ | Unclear if visible |
| Manager reopen case | S10 | ❌ | **MISSING** - No reopen workflow |
| Manager reassign | S4 | ✅ | Managers can reassign |

### Dashboard Features (Medium Priority)

| Functionality | Scenario | Status | Notes |
|--------------|----------|--------|-------|
| Unassigned queue | S1 | ✅ | Works |
| My Cases section | S1 | ✅ | Works |
| Cases on Hold section | S3 | ✅ | Shows held cases |
| Cases Pending Release | S5 | ✅ | Shows scheduled releases |
| Completed Cases | S1 | ✅ | Archived view |
| Member update badges | S3 | ✅ | has_member_updates |
| Column visibility | - | ⚠️ | **MISSING PERSISTENCE** |

### Multi-Hold Scenarios (Low Priority)

| Functionality | Scenario | Status | Notes |
|--------------|----------|--------|-------|
| Multiple holds on same case | S7 | ⚠️ | Should work but not tested |
| Hold history shown | S7 | ⚠️ | Logged but not visible UI |
| Resume reason tracked | S7 | ✅ | Fields exist |

---

## SUMMARY OF GAPS & MISSING FUNCTIONALITY

### Critical Issues (Fix First)

1. **Cron Job Verification** ❌ HIGH PRIORITY
   - S5: Scheduled releases depend on this
   - Action: Verify cron task exists and runs correctly
   - Impact: Without this, scheduled releases don't work
   - Timeline: 1-2 hours to verify, 4-8 hours to build if missing

2. **Communication Notifications** ⚠️ UNCLEAR
   - S1, S3, S9: When member comments, does tech get email?
   - S9: When tech comments, does member get email?
   - Action: Verify email notification system
   - Impact: Workflow depends on notifications
   - Timeline: 2-4 hours to verify/implement

3. **Hold Duration Options** ❌ MEDIUM PRIORITY
   - S3, S7: Should offer 2h, 4h, 8h, 1d, indefinite, custom
   - Action: Add duration selector UI
   - Impact: Can only use indefinite holds now
   - Timeline: 4-6 hours to implement

### Important Missing Features

4. **Multiple Holds Tracking** ⚠️ UI/VISIBILITY
   - S7: Can put on hold multiple times but history not visible
   - Action: Add hold history timeline
   - Impact: Technicians can't see hold pattern
   - Timeline: 3-4 hours

5. **Case Reopening** ❌ NEW FEATURE
   - S10: Manager needs ability to reopen completed cases
   - Action: Implement reopen workflow with status
   - Impact: Can't correct errors after completion
   - Timeline: 6-8 hours

6. **Column Visibility Persistence** ⚠️ PARTIAL
   - UI works but preferences reset on logout
   - Action: Add localStorage or database persistence
   - Impact: UX gap, doesn't persist across sessions
   - Timeline: 2-4 hours

### Verification Needed

7. **Manager Review Workflow** ⚠️ UNCLEAR
   - S10: Manager note visibility, reopen capability
   - Action: Verify manager can add notes and reopen cases
   - Impact: Quality control workflow unclear
   - Timeline: 2-3 hours to verify

8. **Reassignment Communication** ⚠️ PARTIAL
   - S4: New tech notified? Member notified?
   - Action: Verify emails sent on reassignment
   - Impact: Stakeholders may not know about change
   - Timeline: 2-3 hours to verify

9. **Member Update Notifications** ⚠️ UNCLEAR
   - S3, S9: Does tech get email when member uploads/comments?
   - Action: Verify notification system
   - Impact: Tech may miss member responses
   - Timeline: 2-3 hours to verify

---

## RECOMMENDED IMPLEMENTATION ORDER

### Phase 1 (Week 1) - CRITICAL
1. Verify Cron Job - Essential for scheduled releases
2. Verify Communication Notifications - Essential for workflow
3. Add Hold Duration Options - High-use feature

**Timeline:** 1 week

### Phase 2 (Week 2) - HIGH PRIORITY
4. Enhance Comment Notifications - Workflow clarity
5. Verify Manager Review Workflow - Quality control
6. Verify Reassignment Communication - Stakeholder notifications

**Timeline:** 1 week

### Phase 3 (Week 3-4) - MEDIUM PRIORITY
7. Add Case Reopening - Error correction
8. Add Hold History Timeline - Audit/visibility
9. Fix Column Visibility Persistence - UX improvement

**Timeline:** 1-2 weeks

### Phase 4 (Week 4+) - NICE TO HAVE
10. Multi-hold statistics - Analytics
11. Case comparison UI - Member convenience
12. Automated workflows - Efficiency

---

## CONCLUSION

The application has **solid core functionality** but needs verification on notification systems and a few feature additions:

**Strengths:**
- ✅ Core case workflow (create → submit → accept → complete)
- ✅ Hold system with member notification
- ✅ Case linking (original ↔ modification)
- ✅ Audit trail tracking
- ✅ Modification workflow

**Must Verify:**
- ⚠️ Cron job for scheduled releases
- ⚠️ Email notifications on comments
- ⚠️ Manager review workflow

**Must Add:**
- ❌ Hold duration options (UI)
- ❌ Case reopening capability
- ❌ Column visibility persistence

**Nice to Have:**
- Hold history timeline
- Better reassignment notification
- Case comparison interface

With these fixes and additions, the application will fully support the complete case processing workflow from member creation through modification and beyond.
