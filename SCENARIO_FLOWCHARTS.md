# Scenario Flowcharts - Quick Reference Guide

## Overview

This document provides quick visual reference of all 10 case processing scenarios with flowchart summaries, status transitions, and key decision points.

---

## SCENARIO 1: Happy Path - Standard Processing

**Status Flow:**
```
draft → submitted → accepted → completed
```

**Timeline:** ~24 hours

**Key Participants:** Member, Tech

**Decision Points:** None (everything goes smoothly)

**Flowchart:**
```
┌────────────────────────────────────────┐
│     SCENARIO 1: Happy Path              │
└────────────────────────────────────────┘

    Create Draft
        │
        ▼
    Member Submits ─→ Tech Queue (Unassigned)
        │
        ▼
    Tech Reviews & Accepts
        │
        ▼
    Investigate (Tech-only work)
        │
        ├─→ Ask Member Question?
        │   ├─→ YES: Member responds
        │   └─→ NO: Continue
        │
        ▼
    Upload Report
        │
        ▼
    Mark Complete + Release Now
        │
        ▼
    Member Downloads Report
        │
        ▼
    END: Completed & Released ✅
```

**Database Changes:**
```
Case.status:        draft → submitted → accepted → completed
Case.assigned_to:   NULL → NULL → Technician → Technician
Case.date_submitted:    NULL → now()
Case.date_accepted:     NULL → now()
Case.date_completed:    NULL → now()
Case.actual_release_date: NULL → now()
```

**Communications:** 3-4 emails (submit confirm, accept, question?, completion)

**Holds:** 0
**Rejections:** 0
**Reassignments:** 0

---

## SCENARIO 2: Information Request & Resubmission

**Status Flow:**
```
submitted → needs_resubmission → submitted → accepted → completed
```

**Timeline:** ~36 hours

**Key Participants:** Member, Tech

**Decision Points:** 
- Tech: Accept or Reject?
- Member: Upload missing docs and resubmit?

**Flowchart:**
```
┌────────────────────────────────────────┐
│  SCENARIO 2: Resubmission              │
└────────────────────────────────────────┘

    Submit Case
        │
        ▼
    Tech Reviews
        │
        ├─→ Complete? ──YES──→ (Scenario 1)
        │
        └─→ NO: Missing Info
            │
            ▼
        Reject Case + Requirements
            │
            ▼
        Member Receives Requirements Email
            │
            ▼
        Member: Upload Missing Docs
            │
            ▼
        Member: Resubmit
            │
            ▼
        Status: submitted (again)
            │
            ▼
        Tech: Re-Review
            │
            ├─→ Complete? ──YES──→ Accept & Complete
            │
            └─→ Still Missing? → Reject again (loop)
            │
            ▼
        Accept & Complete (like Scenario 1)
            │
            ▼
    END: Completed after resubmission ✅
```

**Status Sequence:**
```
draft → submitted → needs_resubmission ─┐
                                         │
                    ┌─────────────────────┘
                    │
                    ▼
                submitted (resubmitted=true)
                    │
                    ▼
                accepted → completed
```

**Database Changes:**
```
Case.status:               submitted → needs_resubmission → submitted
Case.rejection_reason:     NULL → incomplete_fff (or similar)
Case.is_resubmitted:       False → True
Case.resubmission_count:   0 → 1 (or higher)
Case.date_resubmitted:     NULL → now()
```

**Communications:** 4-5 emails (submit, reject+requirements, resubmit confirm, accept?, completion)

**Holds:** 0
**Rejections:** 1
**Reassignments:** 0

---

## SCENARIO 3: Case Put on Hold

**Status Flow:**
```
accepted → HOLD → accepted → completed
```

**Timeline:** ~48 hours

**Key Participants:** Member, Tech

**Decision Points:**
- Tech: Put on hold? (incomplete info needed)
- Member: Upload docs during hold?
- Tech: Resume or keep on hold?

**Flowchart:**
```
┌────────────────────────────────────────┐
│    SCENARIO 3: Hold & Resume           │
└────────────────────────────────────────┘

    Accept Case
        │
        ▼
    Tech Investigating
        │
        ├─→ All Info Available? ──YES──→ Complete (Scenario 1)
        │
        └─→ NO: Need More Info
            │
            ▼
        Put Case on HOLD
        ├─ Hold Reason: "Waiting for X"
        ├─ Duration: Indefinite (or time option if H1 implemented)
        ├─ Member Notified: ✅ Email + badge
        └─ Tech Can: Still see case
            │
            ▼
        Member Actions While on Hold:
        ├─ Upload Documents: ✅ Yes
        ├─ Add Comments: ✅ Yes
        └─ View Case: ✅ Yes (with "On Hold" label)
            │
            ▼
        Tech Sees Member Updates: has_member_updates=true
            │
            ▼
        Tech Reviews Member's Uploads
            │
            ├─→ Acceptable? ──YES──→ Resume
            │
            └─→ NO: More needed → Keep on hold (loop) or Reject
            │
            ▼
        Resume from Hold
        ├─ Status: hold → accepted
        ├─ Member Notified: ✅ Email
        └─ Resume Reason: Tracked
            │
            ▼
        Continue Investigation
            │
            ▼
        Complete & Release (like Scenario 1)
            │
            ▼
    END: Completed after hold ✅
```

**Status Sequence:**
```
submitted → accepted → HOLD ──┐
                              │
            ┌─────────────────┘
            │
            ▼
        accepted → completed
```

**Database Changes:**
```
Case.status:             accepted → hold → accepted
Case.assigned_to:        Unchanged (preserved during hold)
Case.hold_reason:        NULL → "Waiting for X"
Case.hold_start_date:    NULL → now()
Case.hold_end_date:      NULL → now() (when resumed)
Case.hold_duration_days: NULL (indefinite - ⚠️ needs UI)
Case.has_member_updates: False → True (when member uploads)
```

**Communications:** 5+ emails (hold notice, resume notice, questions/uploads)

**Holds:** 1 (indefinite or time-based)
**Rejections:** 0
**Reassignments:** 0

**⚠️ Critical Features Needed:**
- [ ] Hold duration options UI (C1)
- [ ] Email notification on member upload (C2)

---

## SCENARIO 4: Case Reassignment

**Status Flow:**
```
accepted (Tech A) → accepted (Tech B) → completed
```

**Timeline:** Variable (depends on work remaining)

**Key Participants:** Member, Tech A, Tech B, Manager (optional)

**Decision Points:**
- Tech A: Can I handle this or reassign?
- Choose: Which tech can take over?

**Flowchart:**
```
┌────────────────────────────────────────┐
│     SCENARIO 4: Reassignment           │
└────────────────────────────────────────┘

    Case is Accepted by Tech A
    Status: accepted
    Assigned To: Tech A
        │
        ▼
    Tech A: Cannot continue
    Reason: Vacation, sick, overwhelmed
        │
        ▼
    Tech A Clicks: Reassign
        │
        ▼
    Choose New Tech (Tech B)
    Filters: Same tier/level as Tech A
    Optional: Add reason
        │
        ▼
    UPDATE DATABASE:
    ├─ assigned_to: Tech A → Tech B
    ├─ reassignment_date: now()
    └─ reassignment_reason: Text provided
        │
        ▼
    SEND NOTIFICATIONS:
    ├─ Tech B: Email "Case reassigned to you"
    ├─ Tech A: Optional confirmation (⚠️ verify)
    └─ Member: Optional notification (⚠️ verify)
        │
        ▼
    Tech B: Case now in "My Cases"
    ├─ Same tier/level: ✅ Can see
    ├─ All history visible: ✅ Yes
    └─ Can complete: ✅ Yes
        │
        ▼
    Tech B: Continues work
    ├─ Reviews case history
    ├─ Continues investigation
    └─ Completes & releases (like Scenario 1)
        │
        ▼
    END: Completed by new tech ✅
```

**Status Sequence:**
```
accepted (assigned_to=Tech A)
    ↓
accepted (assigned_to=Tech B)
    ↓
completed (assigned_to=Tech B)
```

**Database Changes:**
```
Case.assigned_to:           Tech A → Tech B
Case.reassignment_date:     NULL → now()
Case.reassignment_reason:   NULL → "Text reason"
Case.previously_assigned_to: NULL → Tech A (if tracked)
Case.status:                Unchanged (still accepted)
```

**Special Case: Reassign During Hold**
```
Case on HOLD (assigned_to=Tech A)
    ↓
Reassign to Tech B
    ├─ Status: still HOLD (preserved)
    ├─ assigned_to: Tech A → Tech B
    └─ Tech B can either:
       ├─ Resume from hold and continue
       └─ Keep on hold longer
    ↓
completed
```

**Communications:** 2-3 emails (reassignment to Tech B, optional to Member)

**Holds:** Possible (if case already on hold)
**Rejections:** 0
**Reassignments:** 1

---

## SCENARIO 5: Scheduled Release

**Status Flow:**
```
completed (scheduled) → completed (released)
```

**Timeline:** 1-60 days (scheduled release window)

**Key Participants:** Tech, Member, Cron Job

**Decision Points:**
- Tech: Release now or schedule for later?
- Tech: How many hours/days from now?

**Flowchart:**
```
┌────────────────────────────────────────┐
│   SCENARIO 5: Scheduled Release        │
│  🔴 CRITICAL: Depends on Cron Job      │
└────────────────────────────────────────┘

    Tech Completes Case
    Status: accepted
        │
        ▼
    Tech Uploads Report
    Status: still accepted
        │
        ▼
    Tech Marks Case Complete
    Modal: Release Timing Options
        │
        ├─→ NOW: Release Immediately
        │   ├─ actual_release_date = now()
        │   ├─ Member sees case immediately
        │   └─ (Scenario 1 ending)
        │
        ├─→ ADMIN DEFAULT: Auto-release in X hours
        │   ├─ scheduled_release_date = now() + admin_default
        │   └─ Cron job processes at time
        │
        └─→ SCHEDULE: Pick date/time (1-60 days out)
            ├─ Tech: Date/time picker: "Tomorrow 9 AM"
            ├─ Constraint: ✅ Max 60 days from now
            ├─ Database:
            │  ├─ scheduled_release_date = Tomorrow 9 AM CST
            │  ├─ scheduled_email_date = Tomorrow 9 AM CST
            │  ├─ actual_release_date = NULL (not released yet)
            │  └─ actual_email_sent_date = NULL
            │
            ▼
        Case Status: completed (scheduled)
        ├─ Member: CANNOT SEE YET
        ├─ Tech: Can see in "Pending Release" section
        └─ Dashboard: Shows scheduled time
            │
            ▼
        TIME PASSES: Tomorrow 9:00 AM arrives
            │
            ▼
        🔴 CRITICAL: CRON JOB RUNS
        process_scheduled_releases management command
        ├─ Find: Cases where scheduled_release_date <= now()
        ├─ For each case:
        │  ├─ UPDATE actual_release_date = now()
        │  ├─ UPDATE actual_email_sent_date = now()
        │  ├─ SEND EMAIL to member: "Case ready"
        │  └─ AUDIT: email_notification_sent logged
        │
        ▼
        Member: Receives Email
        ├─ At exact scheduled time ✅
        ├─ Subject: "Your case report is ready"
        ├─ Body: "Download link"
        └─ Can now download & view
            │
            ▼
        END: Released at scheduled time ✅
```

**Status Sequence:**
```
accepted → completed (status=completed, actual_release_date=NULL)
              ↓
          [TIME PASSES - CRON JOB]
              ↓
          completed (actual_release_date=now())
```

**Database Changes:**
```
Case.status:                  accepted → completed
Case.date_completed:          NULL → now()
Case.scheduled_release_date:  NULL → Tomorrow 9 AM (if scheduled)
Case.scheduled_email_date:    NULL → Tomorrow 9 AM (if scheduled)
Case.actual_release_date:     NULL → null (initially)
                              → now() (when cron runs)
Case.actual_email_sent_date:  NULL → null (initially)
                              → now() (when cron runs)
```

**Communications:** 1 email (scheduled at exact time by cron job)

**Holds:** 0
**Rejections:** 0
**Reassignments:** 0

**🔴 CRITICAL Features Needed:**
- [ ] Cron job exists and is active (C1)
- [ ] Cron job sends emails (C2)

---

## SCENARIO 6: Member Requests Modification

**Status Flow (Original):**
```
completed (no change)
```

**Status Flow (New Modification Case):**
```
submitted → accepted → completed
```

**Timeline:** ~24-48 hours after completion

**Key Participants:** Member, Original Tech, Case System

**Decision Points:**
- Member: Within 60-day window? Request mod?
- Tech: Accept or reject modification?

**Flowchart:**
```
┌────────────────────────────────────────┐
│  SCENARIO 6: Member Modification       │
│         Request                        │
└────────────────────────────────────────┘

    Member Has Completed Case
    Status: completed
    Days since release: < 60
        │
        ▼
    Member Reviews Report
    ├─ Identifies error or concern
    └─ "Something doesn't look right"
        │
        ▼
    Can Request Modification?
    ├─ IF days_since_release < 60: ✅ YES
    │
    └─ IF days_since_release >= 60: ❌ NO
       └─ Disabled: "Requests only in first 60 days"
            │
            ▼
        Member Clicks: "Request Modification"
        Modal: Reason for modification
        Input: "Q3-Q4 calculations appear incorrect"
        Optional: Upload supporting docs
            │
            ▼
        CREATE NEW CASE:
        ├─ Case.external_case_id: Auto-generated (new ID)
        ├─ Case.status: submitted
        ├─ Case.original_case: FK → original case ✅
        ├─ Case.member: Same member
        ├─ Case.workshop_code: Same code
        ├─ Case.tier: Copied from original
        ├─ Case.credit_value: Copied from original
        ├─ Case.created_by: member
        └─ Case.date_submitted: now()
            │
            ▼
        STORE MOD REASON:
        ├─ Message created on original case
        ├─ Author: member
        ├─ Content: Modification reason
        └─ Visible to tech: ✅ Yes
            │
            ▼
        SEND NOTIFICATIONS:
        ├─ Member: "Modification case [ID] created"
        ├─ Original Tech: "Modification requested for [ID]"
        │                 "New case: [ID]"
        │                 "Reason: Q3-Q4 calculations..."
        └─ Visible link to both cases
            │
            ▼
        Tech: Accepts Modification Case
        ├─ Reviews reason & original case
        ├─ Linked view: Can compare original
        └─ Accepts and investigates
            │
            ▼
        Tech: Completes Modification
        ├─ Uploads corrected report
        ├─ Same completion process as normal
        ├─ Auto-assign back to original tech ✅
        └─ Release (now or scheduled)
            │
            ▼
        Member: Receives Modification Report
        ├─ Original case still available
        ├─ Modification case now available
        ├─ Can compare: Original vs Corrected
        └─ Linked in both directions ✅
            │
            ▼
    END: Member has both cases ✅
        Original case: unchanged
        Modification case: completed with correction
        Both linked: bidirectional
```

**Modification Case Status Sequence:**
```
[Original Case]
  Status: completed (UNCHANGED)
    ↓
[New Modification Case Created]
  Status: submitted
    ↓
  Status: accepted
    ↓
  Status: completed

[Linking]
  original_case → FK to original
  Bidirectional: Can navigate original ↔ modification
```

**Database Changes:**
```
[New Case Created]
Case.external_case_id:    Auto-generated
Case.status:              submitted
Case.original_case:       FK → original case
Case.member:              Same member
Case.tier:                Copied
Case.credit_value:        Copied
Case.created_by:          member

[Original Case]
Case.status:              completed (UNCHANGED)
Message created:          Modification request stored

[Linking]
Can query: Case.objects.filter(original_case=original_id)
Member sees: Both cases in dashboard
Tech sees: Original ↔ modification link in UI
```

**Communications:** 3 emails
- Member: "Modification case created"
- Tech: "Modification requested for [original]"
- Member: "Modification complete"

**Holds:** Possible (if mod case needs info)
**Rejections:** Possible (if mod case incomplete)
**Reassignments:** 0 (auto-assigned to original tech)

**✅ Features Complete:**
- Original case linking ✅
- Bidirectional UI display ✅ (recently added)
- Auto-assignment to original tech ✅

---

## SCENARIO 7: Complex Hold & Resume Cycle

**Status Flow:**
```
accepted → HOLD → accepted → HOLD → accepted → completed
```

**Timeline:** ~72+ hours

**Key Participants:** Tech, Member

**Decision Points:**
- Tech: Hold, continue, or reject?
- Member: Upload during hold?
- Tech: Resume or keep waiting?

**Flowchart:**
```
┌────────────────────────────────────────┐
│  SCENARIO 7: Multiple Hold/Resume      │
│           Cycles                       │
│  ⚠️ CONCERN: Data may overwrite        │
└────────────────────────────────────────┘

    ┌─────────────────────────┐
    │  HOLD CYCLE #1          │
    └─────────────────────────┘

    Tech: Put on HOLD #1
    Reason: "Waiting for employment verification"
    Duration: Indefinite (⚠️ no UI options yet)
        │
        ▼
    Member: Notified ✅
    Email: "Case on hold - reason given"
        │
        ▼
    Member: Uploads Employment Letter
    Status: still HOLD (no change)
        │ (Tech notified? ⚠️ UNCLEAR)
        │
        ▼
    Tech: Reviews Upload
    Assessment: "Verification acceptable"
        │
        ▼
    Tech: Resume from Hold #1
    Status: hold → accepted
    Duration #1 calculation: start → now()
        │
        ▼
    Member: Notified ✅
    Email: "Case processing resumed"
        │
        ├─────────────────────────────────┐
        │                                 │
        ▼                                 ▼
    Continue Investigation          Case Complete
                │                        (Scenario 1)
                │
    ┌─────────────────────────┐
    │  HOLD CYCLE #2          │
    └─────────────────────────┘
                │
                ▼
    Tech: Put on HOLD #2
    Reason: "Awaiting manager approval"
    Status: accepted → HOLD (AGAIN)
    ⚠️ CONCERN: hold_reason may overwrite
        │       hold_start_date may overwrite
        │       hold_end_date may overwrite
        │
        ▼
    Member: Notified ✅ (AGAIN)
    Email: "Case on hold again"
        │ (Confusing? Multiple holds not clear)
        │
        ▼
    Manager: Approves
    Tech: Gets approval info
        │
        ▼
    Tech: Resume from Hold #2
    Status: hold → accepted (AGAIN)
    ⚠️ CONCERN: Previous hold data lost?
        │
        ▼
    Member: Notified ✅ (AGAIN)
    Email: "Resume notification #2"
        │
        ▼
    Continue Investigation
        │
        ▼
    Tech: Complete & Release
    (Like Scenario 1)
        │
        ▼
    END: Case Complete ✅
    ⚠️ But: Hold history not visible
        └─ Can't see: Hold 1, Resume 1, Hold 2, Resume 2
        └─ Only see: Current state (hold data overwritten)
```

**Status Sequence:**
```
accepted → HOLD ─────→ accepted → HOLD ─────→ accepted → completed
  Hold #1                  Hold #2
```

**Database Changes - CONCERN:**
```
[HOLD #1]
Case.status:             accepted → HOLD
Case.hold_start_date:    NULL → now()
Case.hold_reason:        NULL → "Employment verification"
Case.hold_end_date:      NULL → now() (resume)
Case.hold_duration_days: NULL → 0.5 days

[HOLD #2 - OVERWRITES?]
Case.status:             accepted → HOLD
Case.hold_start_date:    [Hold#1] → now() ⚠️ OVERWRITES
Case.hold_reason:        [Hold#1] → "Manager approval" ⚠️ OVERWRITES
Case.hold_end_date:      [Hold#1] → NULL ⚠️ LOST
Case.hold_duration_days: [Hold#1] → NULL ⚠️ LOST
```

**⚠️ CONCERN: Hold History Lost**
- Original Hold #1 data overwritten
- Can't report: "Case was on hold twice for different reasons"
- Can't show member: Hold timeline
- Can't show tech: Hold patterns

**Solution Needed:** HoldHistory table (H2 in Implementation Priorities)

**Communications:** 5+ emails (hold #1, resume #1, hold #2, resume #2, completion)

**Holds:** 2 back-to-back
**Rejections:** 0
**Reassignments:** 0

**⚠️ Features Needed:**
- [ ] Hold history tracking (H2)
- [ ] Hold history visibility (H3)
- [ ] Better UI explanation for multiple holds

---

## SCENARIO 8: Modification Outside 60-Day Window

**Status Flow:**
```
completed (old case - no change)
```

**Timeline:** 60+ days after release

**Key Participants:** Member

**Decision Points:**
- Member: Try to request modification after 60 days?

**Flowchart:**
```
┌────────────────────────────────────────┐
│  SCENARIO 8: 60-Day Window              │
│       Enforcement                       │
└────────────────────────────────────────┘

    Member Reviews Old Case
    Status: completed
    Days since release: 65 (OUTSIDE window)
        │
        ▼
    Member Notices Issue
    Wants: Request modification
        │
        ▼
    "Request Modification" Button?
    ├─ Visibility: Still visible (not hidden)
    ├─ State: ❌ DISABLED
    ├─ Reason: "Modification requests only available within 60 days"
    └─ Tooltip/Help text: Shows countdown message
        │
        ▼
    Member: Cannot request modification
    ├─ No new case created
    ├─ No tech notification
    └─ Blocked by 60-day limit ✅
        │
        ▼
    ALTERNATIVE: Ask a Question
    ├─ Button: "Ask a Question" (NO TIME LIMIT)
    ├─ Modal: Question text box
    ├─ No disable: Always available
    └─ Can submit question anytime
        │
        ▼
    Member: Asks Question
    Input: "I think the calculation might be wrong"
        │
        ▼
    SEND NOTIFICATION:
    ├─ Message: member_comment_added
    ├─ Visible to: Tech
    ├─ No modification case: Created
    └─ Communication style: Question, not formal mod
        │
        ▼
    Tech: Responds (manual, not formal process)
    ├─ Explanation: "Calculation was correct because..."
    ├─ Or: "You're right, let me review"
    └─ Resolution: Explanation or new modification case
        │
        ▼
    Member: Gets Response
    ├─ Understands reasoning
    └─ Or: Can propose new modification if tech agrees
        │
        ▼
    END: Outside 60-day window ✅
        Original case: completed, read-only
        Question: Answered by tech
        Modification: Not allowed but question pathway available
```

**Status Sequence:**
```
completed (> 60 days old)
  ├─ Request Mod button: DISABLED ❌
  └─ Ask Question button: ENABLED ✅
```

**Implementation Check:**
```python
# Template logic
{% if case.is_within_modification_window %}
    <button class="btn btn-primary">Request Modification</button>
{% else %}
    <button class="btn btn-primary" disabled>Request Modification</button>
    <span class="help-text">60 days have passed</span>
{% endif %}

# View logic
days_since_release = (now - case.actual_release_date).days
can_request_mod = days_since_release < 60
```

**Communications:** 1 (question from member)

**Holds:** 0
**Rejections:** 0
**Modifications:** 0 (blocked)

**✅ Features Complete:**
- 60-day enforcement ✅
- Button disabled properly ✅
- Question pathway available ✅

---

## SCENARIO 9: Multiple Document Requests (Iterative)

**Status Flow:**
```
accepted (with back-and-forth)
```

**Timeline:** 40-60 hours

**Key Participants:** Tech, Member

**Decision Points:**
- Tech: Ask question or put on hold?
- Member: Upload docs or provide answer?

**Flowchart:**
```
┌────────────────────────────────────────┐
│  SCENARIO 9: Iterative Requests        │
│      (No Holds - Just Comments)        │
└────────────────────────────────────────┘

    Case Accepted
    Status: accepted
        │
        ▼
    ┌─────────────────────────────────────┐
    │  REQUEST #1                         │
    └─────────────────────────────────────┘
        │
        ▼
    Tech: Adds Public Question
    Content: "Can you upload medical report?"
    Status: No change (still accepted)
        │ (Email to member? ⚠️ UNCLEAR)
        │
        ▼
    Member: Sees Unread Message
    ├─ Dashboard badge ✅
    ├─ Case detail: New comment
    └─ Notification icon
        │
        ▼
    Member: Uploads Document
    Type: Medical report
    Status: No change (still accepted)
        │ (Tech notified? ⚠️ UNCLEAR)
        │ (Audit: document_uploaded logged)
        │
        ▼
    Member: Adds Response
    Content: "Medical report attached from Dr. Smith"
        │ (Audit: member_comment_added)
        │ (Tech notified? ⚠️ UNCLEAR)
        │
        ├─────────────────────────────────────┐
        │  REQUEST #2                         │
        │                                     │
        ▼                                     ▼
    Tech: Reviews Upload               Tech: Needs Clarification
    Assessment: "Good, but..."              │
                                            ▼
                                        Adds Public Question
                                        "Clarify treatment dates"
                                            │
                                            ▼
                                        (Email to member? ⚠️)
                                            │
                                            ▼
                                        Member: Uploads Supplement
                                        Type: Treatment Timeline
                                            │
                                            ▼
                                        Member: Responds
                                        "Timeline attached"
                                            │
                                        ├─────────────────────────────────────┐
                                        │  REQUEST #3                         │
                                        │                                     │
                                        ▼                                     ▼
                                    Tech: Reviews               Tech: Final Question
                                    "Complete"                 "Any employment after 2023?"
                                        │                           │
                                        │                           ▼
                                        │                       Member: Final Answer
                                        │                       "No, on benefits"
                                        │                           │
                                        │                           │
                                        └───────────┬───────────────┘
                                                    │
                                                    ▼
                                        Tech: All Info Gathered ✅
                                        ├─ All questions answered ✅
                                        ├─ All docs received ✅
                                        └─ Ready to complete
                                            │
                                            ▼
                                        Tech: Complete & Release
                                        (Like Scenario 1)
                                            │
                                            ▼
                                        END: Complete ✅
                                        Total: 3 question/response cycles
                                               No holds needed
                                               Back-and-forth only
```

**Communication Pattern:**
```
Tech Q1 → Member A1 + Doc1 → Tech Q2 → Member A2 + Doc2 → Tech Q3 → Member A3 → Tech: Complete
```

**Status Sequence:**
```
accepted (unchanged throughout)
  + Comments/Questions: 3 cycles
  + Documents: 2-3 uploaded
  + No hold events
  └─ → completed
```

**Database Changes:**
```
Case.status:              accepted (UNCHANGED - no status changes)
Messages:                 6 created (3 tech, 3 member)
Documents:                2-3 created
Case.has_member_updates:  False → True (multiple times)
Audit trail:              document_uploaded × 2-3
                          member_comment_added × 3
```

**Communications:** Multiple emails
- Tech Q1 → Member (⚠️ verify email)
- Member A1+Doc1 → Tech (⚠️ verify email)
- Tech Q2 → Member (⚠️ verify email)
- Member A2+Doc2 → Tech (⚠️ verify email)
- Tech Q3 → Member (⚠️ verify email)
- Member A3 → Tech (⚠️ verify email)
- Completion → Member (✅ verify)

**Holds:** 0 (alternative to holding)
**Rejections:** 0
**Reassignments:** 0

**⚠️ Features Needed:**
- [ ] Email notification on tech question (C2)
- [ ] Email notification on member response (C2)

---

## SCENARIO 10: Manager Quality Review

**Status Flow:**
```
completed → [Manager Review] → completed (or reopen_for_correction)
```

**Timeline:** Variable

**Key Participants:** Manager, Tech, Member (optional)

**Decision Points:**
- Manager: Approve or find issues?
- If issues: Reopen for correction?

**Flowchart:**
```
┌────────────────────────────────────────┐
│  SCENARIO 10: Quality Review            │
│  🔴 Case Reopening MISSING              │
└────────────────────────────────────────┘

    Tech Completes Case
    Status: completed
        │
        ▼
    Case Available for Manager Review
    Dashboard: "Completed Cases" section
        │
        ▼
    Manager: Reviews Case
    Access: Full case detail
    Can see: FFF data, docs, notes, report, audit trail
        │
        ▼
    ┌────────────────────┐  ┌────────────────────┐
    │  PATH A: APPROVE   │  │  PATH B: ISSUES    │
    └────────────────────┘  └────────────────────┘
         │                           │
         ▼                           ▼
    Quality Assessment:         Found Error:
    "Excellent work"            "Q3 calculation wrong"
    Calculations: ✅             Calculations: ❌
    Notes: Clear ✅              Notes: Clear ✅
         │                           │
         ▼                           ▼
    Manager Add Note         Manager Needs to Reopen
    (if available):          ❌ MISSING FEATURE
    "Approved"                   │
         │                       ▼
         │                   IF FEATURE EXISTED:
         │                   ├─ Click: "Reopen"
         │                   ├─ Status: completed
         │                   │         → reopen_for_correction
         │                   ├─ Reason: "Q3 error found"
         │                   ├─ Tech: Gets notified
         │                   ├─ Tech: Case in queue
         │                   ├─ Tech: Fixes calculation
         │                   ├─ Tech: Uploads corrected
         │                   └─ Status: → completed
         │                       │
         │                       ▼
         │                   Manager: Re-reviews
         │                       │
         │                       ▼
         │                   APPROVE
         │                       │
         ▼                       ▼
    END: Case Stays           END: Case Corrected
    completed ✅              completed ✅

    Tech Gets Feedback        Tech Notified to Fix
    Optional: Email ⚠️        Email: "Case reopened"
                             Email: "Reason: Q3 error"
                             Dashboard: Case marked urgent
```

**Status Sequences:**

**Path A (No Issues):**
```
completed → [Manager Review] → completed
  (Manager adds optional note)
```

**Path B (Issues - IF Reopening Implemented):**
```
completed → reopen_for_correction → accepted → completed
  (Manager found issue)  (Tech fixes)    (Tech completes again)
                                       (Manager reviews again)
```

**Database Changes:**

**Current State:**
```
Case.status:  completed (NO CHANGE)
Manager note: ⚠️ Unclear if available
Tech notified: ⚠️ Unclear
Reopening:    ❌ MISSING
```

**If Reopening Implemented:**
```
Case.status:          completed → reopen_for_correction
Case.reopen_reason:   NULL → "Q3 calculation error"
Case.reopened_date:   NULL → now()
Case.reopened_by:     NULL → manager user
Notification:         Tech gets email
Dashboard:            Case reappears in tech queue
```

**Communications:**
- Path A: Optional manager feedback email
- Path B: Reopen notification email, manager follow-up

**Holds:** Possible (if case needs more info during reopen)
**Rejections:** Possible (if tech reopen still incomplete)
**Reassignments:** Possible

**🔴 Critical Features Needed:**
- [ ] Case reopening functionality (C3)
- [ ] Reopen status in model
- [ ] Manager can reopen button
- [ ] Tech gets reopening notification

**⚠️ Unclear Features:**
- [ ] Manager review workflow (H4)
- [ ] Can manager add notes?
- [ ] Are notes visible to tech?

---

## SCENARIO SUMMARY TABLE

| Scenario | Status Flow | Timeline | Holds | Rejections | Reassigns | Key Features | Gaps |
|----------|-------------|----------|-------|-----------|-----------|--------------|------|
| 1 | draft→submitted→accepted→completed | 24h | 0 | 0 | 0 | Submit, accept, release | Email notifications |
| 2 | submitted→needs_resubmission→submitted→accepted→completed | 36h | 0 | 1 | 0 | Reject, resubmit | Resubmit notification |
| 3 | accepted→HOLD→accepted→completed | 48h | 1 | 0 | 0 | Hold, resume | Hold duration, duration options |
| 4 | accepted(A)→accepted(B)→completed | Var | 0 | 0 | 1 | Reassign, history preserved | Reassign notifications |
| 5 | accepted→completed→[time]→released | 24-60d | 0 | 0 | 0 | Schedule release | 🔴 Cron job verification |
| 6 | completed→new:submitted→accepted→completed | 24-48h | 0-1 | 0-1 | 0 | Modification request, link cases | ✅ Complete |
| 7 | accepted→HOLD→accepted→HOLD→accepted→completed | 72+h | 2 | 0 | 0 | Multiple holds | 🔴 Hold history tracking |
| 8 | completed + 60+ days | Var | 0 | 0 | 0 | 60-day window enforcement | ✅ Complete |
| 9 | accepted + iterations | 40-60h | 0 | 0 | 0 | Q&A without hold | Email notifications |
| 10 | completed→[review]→reopen or stay | Var | 0-1 | 0 | 0 | Manager review, reopen | 🔴 Reopening missing |

---

## IMPLEMENTATION DEPENDENCY MAP

```
        C1: Cron Job
            ↓
        S5: Works
        
        C2: Email
        ↙   ↓   ↘
    S1  S2  S3  S4  S9
    
        H1: Hold Duration
        ↓
        H2: Hold History
        ↓
        H3: Hold History Visibility
        ↓
        S3, S7: Hold features complete
    
        C3: Case Reopening
        ↓
        S10: Manager review works
    
        Independent: S6, S8
```

---

This quick reference provides visual navigation of all 10 scenarios for developers, testers, and managers.
