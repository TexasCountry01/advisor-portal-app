# Technician Tiers and Quality Review Process
## Comprehensive Analysis from Research Documentation

**Source Documents:** 
- advisor-portal/research/technical-requirements.md
- advisor-portal/research/technical-presentation.md
- advisor-portal/research/client-meeting-agenda.md

**Last Updated:** January 17, 2026

---

## Executive Summary

The Advisor Portal system implements a **three-tier technician hierarchy** with a **quality review workflow** designed to ensure case quality while managing workload. The review process is explicitly triggered when **Level 1 (junior) technicians complete cases**, requiring approval from **Level 2 or Level 3 (senior) technicians** before cases are released to advisors.

---

## 1. Technician Tier System

### 1.1 Three-Level Hierarchy

The system defines three distinct technician levels based on experience and expertise:

#### **Level 1: New Technician**
- **Description:** Junior/new benefits technicians
- **Experience:** Recently onboarded or entry-level
- **Key Characteristic:** ⚠️ **REQUIRES QUALITY REVIEW** before case completion
- **Responsibilities:**
  - Work on assigned cases
  - Perform initial case analysis
  - Create preliminary reports
  - Conduct investigations
  - **CANNOT** approve their own work
- **Access:** Cases assigned to them only
- **Capabilities:** Full case processing (but with mandatory review gate)

#### **Level 2: Technician**
- **Description:** Experienced technician with proven track record
- **Experience:** Typically 1-2+ years on the job
- **Key Characteristic:** ✅ **CAN PERFORM QUALITY REVIEWS**
- **Responsibilities:**
  - Work on own assigned cases
  - **Review and approve Level 1 technician work** (primary duty)
  - Can request changes/revisions from Level 1 techs
  - Provide feedback to improve Level 1 performance
  - Mentor less experienced technicians
- **Access:** 
  - Their own cases
  - **Level 1 technician cases in "pending review" status**
  - Can view team workload/metrics
- **Capabilities:** Full case processing + quality review authority

#### **Level 3: Senior Technician**
- **Description:** Senior/expert benefits technician
- **Experience:** 3+ years, proven expertise
- **Key Characteristic:** ✅ **CAN PERFORM QUALITY REVIEWS** (with seniority authority)
- **Responsibilities:**
  - Work on complex cases (Tier 2, Tier 3)
  - **Review and approve Level 1 technician work** (same as Level 2)
  - Handle escalations and complex cases
  - Lead technical initiatives
  - Mentor Level 1 and Level 2 technicians
  - May have team lead responsibilities
- **Access:** 
  - Their own cases
  - **All Level 1 technician cases in "pending review" status**
  - Can view all team metrics
  - Escalation cases
- **Capabilities:** Full case processing + quality review authority + escalation handling


## Core Technician Actions

Technicians work within a three-tier hierarchy with quality review gates:

- **Level 1** - Process cases (require review before completion)
- **Level 2/3** - Process cases + perform quality reviews
- **Quality Review** - Approval gate ensuring case quality

---

## 5. Implementation Status

### Currently Implemented ✅

- User levels (Level 1, 2, 3) in User model
- `reviewed_by` field on Case model
- `requires_review` property on Case model
- `pending_review` status value
- Admin dashboard "Review" stat tracking
- Case complexity tier structure (Tier 1, 2, 3)
- Database schema for review tracking

### Missing/Incomplete ❌

- **NO** automatic trigger to set `pending_review` status when Level 1 completes case
- **NO** review queue interface/view for Level 2/3 technicians
- **NO** approve/reject/correct action endpoints
- **NO** review decision notification system
- **NO** review queue template in dashboard
- **NO** audit logging for review actions
- **NO** revision routing (sending case back to Level 1)
- **NO** UI for Level 2/3 techs to see cases pending review

---

## 6. Configuration Decisions Needed

Based on the client meeting agenda, several decisions about the review process are outstanding:

### 6.1 Review Bypass Options

**Decision Needed:**
- Should Level 1 technicians' cases **ALWAYS** require review?
- OR should admins have ability to bypass review for certain Level 1 techs?
- OR should all cases from all techs (including Level 2/3) require review?

**Current Spec Assumption:** Only Level 1 cases require mandatory review.

### 6.2 Who Can Review Whom

**Decision Needed:**
- Can Level 2 review Level 1 cases? ✅ (Assumed YES)
- Can Level 3 review Level 1 cases? ✅ (Assumed YES)
- Can Level 2 and Level 3 review each other's cases? ❓
- Can Level 3 review Level 2 cases? ❓

**Current Spec Assumption:** Level 2 and Level 3 both review Level 1 cases (same authority).

### 6.3 Review Time Limits

**Decision Needed:**
- Should there be a maximum time a case can be in review?
- Should Level 2/3 be notified/escalated if review queue gets too old?
- Should admin have ability to force-complete a case if review takes too long?

**Current Spec:** No time limits mentioned.

### 6.4 Multiple Revisions

**Decision Needed:**
- If Level 1 tech resubmits after "Request Changes" and Level 2/3 tech requests changes again, what's the limit?
- Should there be audit trail of all revision cycles?
- Should case be escalated to admin after N revisions?

**Current Spec:** Unlimited revisions implied (but not explicitly stated).

---

## 7. Notifications for Review Process

### Level 1 Technician Notifications

**When Review Complete - APPROVED:**
- Title: "Case Review Approved"
- Message: "Your case [ID] has been approved by [Level 2/3 Name]"
- Details: Case now ready for release to advisor

**When Review Complete - CHANGES REQUESTED:**
- Title: "Case Review - Revisions Needed"
- Message: "Your case [ID] needs revisions from [Level 2/3 Name]"
- Details: [Specific feedback from Level 2/3 tech]
- Action: Case returned to "Accepted" status, awaiting rework

**When Review Complete - CORRECTED:**
- Title: "Case Review Complete - Corrected"
- Message: "Your case [ID] has been reviewed and corrected by [Level 2/3 Name]"
- Details: [What corrections were made]
- Action: Case is now complete and ready for advisor

### Level 2/3 Technician Notifications

**New Cases in Review Queue:**
- Title: "New Case Awaiting Review"
- Message: "[Level 1 Tech Name] has submitted case [ID] for review"
- Details: Case type, complexity tier, submission date

### Advisor Notifications

**When Case Completed (After Review Approved):**
- Title: "Your Case Report is Ready"
- Message: "Case [ID] analysis complete, report ready for download"
- Channel: Email + SMS (if enabled)

---

## 8. Key Metrics & Reporting

### Metrics Related to Review Process

**For Administrators/Managers:**
- Total cases pending review (by day)
- Average review time (days from pending to completed)
- Review approval rate (% approved vs. sent back)
- Review rejection rate (cases sent back for revisions)
- Multiple revision rate (cases requiring 2+ revision cycles)
- Average revisions per case before approval
- Level 1 tech "first-time approval" rate (quality indicator)

**For Level 2/3 Technicians:**
- Cases in my review queue
- Average time spent reviewing per case
- Review actions performed (approved/rejected/corrected counts)

**For Level 1 Technicians:**
- Cases awaiting review
- Approval rate (% cases approved on first review)
- Average feedback for improvements
- Common revision reasons (for skill development)

---

## 9. Quality Review Email Notifications

### Overview

All Level 1 technicians receive email notifications when their completed cases are reviewed by Level 2 or Level 3 technicians. These emails serve as the primary communication mechanism for quality review decisions and are logged in the audit trail.

### Emails Level 1 Technicians Receive

#### Email #1: **Case Approved** ✅
- **When Sent:** Immediately when Level 2/3 tech approves a Level 1 case
- **Recipient:** Level 1 technician who completed the case
- **Subject:** "Quality Review Complete: Your Case [ID] APPROVED"
- **Template:** case_approved_notification.html
- **Content:**
  - Approval confirmation
  - Reviewer name and tier level (Level 2 or 3)
  - Approval timestamp
  - Case proceeds to completion
- **Action:** No action needed; case automatically completed
- **Case Status:** Changes to 'completed'
- **Audit Trail:** Logged as email_sent with reviewer info

#### Email #2: **Revisions Requested** ✅
- **When Sent:** Immediately when Level 2/3 tech requests revisions
- **Recipient:** Level 1 technician who completed the case
- **Subject:** "Quality Review: Revisions Requested for Case [ID]"
- **Template:** case_revisions_needed_notification.html
- **Content:**
  - What revisions are needed (specific sections)
  - Reviewer name and tier level
  - Detailed feedback and comments
  - Deadline for revision completion
  - Instructions on how to resubmit
- **Action:** Level 1 tech must review feedback and make necessary revisions
- **Case Status:** Remains 'pending_review'
- **Audit Trail:** Logged with revision details and reviewer feedback

#### Email #3: **Corrections Required** ✅
- **When Sent:** Immediately when Level 2/3 tech requires corrections
- **Recipient:** Level 1 technician who completed the case
- **Subject:** "Quality Review: Corrections Required for Case [ID]"
- **Template:** case_corrections_notification.html
- **Content:**
  - What corrections are needed
  - Severity level (minor, moderate, critical)
  - Detailed explanation of issues
  - Reviewer name and tier level
  - Deadline for correction
- **Action:** Level 1 tech must correct errors and resubmit
- **Case Status:** Remains 'pending_review'
- **Audit Trail:** Logged with correction details and severity

#### Email #4: **Case Resubmitted Alert** ✅
- **When Sent:** Immediately when member resubmits a completed case
- **Recipient:** Technician currently assigned to case
- **Subject:** "Alert: Case [ID] Resubmitted by Member"
- **Content:**
  - Case has been resubmitted
  - Count of resubmissions
  - List of new documents uploaded
  - Member's resubmission reason/notes
- **Action:** Review member's new documents and assess changes
- **Case Status:** Changes to 'resubmitted'
- **Audit Trail:** Logged with resubmission count and member notes

### Email Delivery & Audit Trail

**All Quality Review Emails:**
- Sent immediately (not scheduled)
- Logged in audit trail with action_type='email_sent'
- Include reviewer identification for accountability
- Track delivery status (success/failed)
- Failed emails logged as 'email_failed' for admin recovery

**Finding Email History:**
1. View case detail → Audit Trail tab
2. Filter by action_type='email_sent'
3. See all review decision emails sent with timestamps and content

---

## 9. Benefits of Three-Tier Review System

1. **Quality Assurance:** All junior tech work reviewed before member sees it
2. **Consistency:** Senior techs ensure uniform quality standards
3. **Mentoring:** Feedback helps junior techs improve
4. **Risk Mitigation:** Catches errors before delivery
5. **Workload Flexibility:** Senior techs can work on hard cases while reviewing juniors
6. **Career Development:** Clear path for advancement (Level 1 → 2 → 3)
7. **Audit Trail:** Full traceability of who reviewed and approved each case

---

## 10. Comparison: Review vs. No Review

### Without Review Process
```
Level 1 Tech Completes
    ↓
Status = "Completed"
    ↓
Report visible to advisor
    ↓
Problem: No quality gate, errors reach advisors
```

### With Review Process (Implemented)
```
Level 1 Tech Completes
    ↓
Status = "Pending Review"
    ↓
Level 2/3 Tech Reviews
    ↓
├─ APPROVE → Status = "Completed" → Report visible
├─ REQUEST CHANGES → Status = "Accepted" → Level 1 reworks
└─ CORRECT → Fix issues, Status = "Completed" → Report visible
```

---

## Summary Table

| Aspect | Level 1 | Level 2 | Level 3 |
|--------|---------|---------|---------|
| **Experience** | New/Junior | 1-2+ years | 3+ years |
| **Own Cases** | ✅ | ✅ | ✅ |
| **Review Others** | ❌ | ✅ (L1 only) | ✅ (L1 only) |
| **Can Approve** | ❌ | ✅ | ✅ |
| **Can Correct** | ❌ | ✅ | ✅ |
| **Review Bypass** | Always required | N/A | N/A |
| **Queue** | Work queue | Review queue | Review queue |
| **Complexity** | All tiers | 1-2 primary | 2-3 primary |
| **Notification** | Gets feedback | Sees review queue | Sees review queue |

---

## Next Steps for Implementation

To fully implement the quality review workflow:

1. **Trigger Logic:** Modify `mark_case_complete()` view to check technician level
2. **Review Queue View:** Create view for Level 2/3 to see pending cases
3. **Review Actions:** Implement approve/reject/correct endpoints
4. **Audit Logging:** Log all review actions with timestamps and notes
5. **Notifications:** Email/SMS for review decisions
6. **Dashboard:** Show review queue stats and metrics
7. **Testing:** Create test cases for all review scenarios
8. **Documentation:** Update user guides and training materials

---

**End of Document**

---

## Reference Diagrams & Hierarchy


## Core Technician Actions

Technicians work within a three-tier hierarchy with quality review gates:

- **Level 1** - Process cases (require review before completion)
- **Level 2/3** - Process cases + perform quality reviews
- **Quality Review** - Approval gate ensuring case quality

---

## 5. Implementation Status

### Currently Implemented ✅

- User levels (Level 1, 2, 3) in User model
- `reviewed_by` field on Case model
- `requires_review` property on Case model
- `pending_review` status value
- Admin dashboard "Review" stat tracking
- Case complexity tier structure (Tier 1, 2, 3)
- Database schema for review tracking

### Missing/Incomplete ❌

- **NO** automatic trigger to set `pending_review` status when Level 1 completes case
- **NO** review queue interface/view for Level 2/3 technicians
- **NO** approve/reject/correct action endpoints
- **NO** review decision notification system
- **NO** review queue template in dashboard
- **NO** audit logging for review actions
- **NO** revision routing (sending case back to Level 1)
- **NO** UI for Level 2/3 techs to see cases pending review

---

## 6. Configuration Decisions Needed

Based on the client meeting agenda, several decisions about the review process are outstanding:

### 6.1 Review Bypass Options

**Decision Needed:**
- Should Level 1 technicians' cases **ALWAYS** require review?
- OR should admins have ability to bypass review for certain Level 1 techs?
- OR should all cases from all techs (including Level 2/3) require review?

**Current Spec Assumption:** Only Level 1 cases require mandatory review.

### 6.2 Who Can Review Whom

**Decision Needed:**
- Can Level 2 review Level 1 cases? ✅ (Assumed YES)
- Can Level 3 review Level 1 cases? ✅ (Assumed YES)
- Can Level 2 and Level 3 review each other's cases? ❓
- Can Level 3 review Level 2 cases? ❓

**Current Spec Assumption:** Level 2 and Level 3 both review Level 1 cases (same authority).

### 6.3 Review Time Limits

**Decision Needed:**
- Should there be a maximum time a case can be in review?
- Should Level 2/3 be notified/escalated if review queue gets too old?
- Should admin have ability to force-complete a case if review takes too long?

**Current Spec:** No time limits mentioned.

### 6.4 Multiple Revisions

**Decision Needed:**
- If Level 1 tech resubmits after "Request Changes" and Level 2/3 tech requests changes again, what's the limit?
- Should there be audit trail of all revision cycles?
- Should case be escalated to admin after N revisions?

**Current Spec:** Unlimited revisions implied (but not explicitly stated).

---

## 7. Notifications for Review Process

### Level 1 Technician Notifications

**When Review Complete - APPROVED:**
- Title: "Case Review Approved"
- Message: "Your case [ID] has been approved by [Level 2/3 Name]"
- Details: Case now ready for release to advisor

**When Review Complete - CHANGES REQUESTED:**
- Title: "Case Review - Revisions Needed"
- Message: "Your case [ID] needs revisions from [Level 2/3 Name]"
- Details: [Specific feedback from Level 2/3 tech]
- Action: Case returned to "Accepted" status, awaiting rework

**When Review Complete - CORRECTED:**
- Title: "Case Review Complete - Corrected"
- Message: "Your case [ID] has been reviewed and corrected by [Level 2/3 Name]"
- Details: [What corrections were made]
- Action: Case is now complete and ready for advisor

### Level 2/3 Technician Notifications

**New Cases in Review Queue:**
- Title: "New Case Awaiting Review"
- Message: "[Level 1 Tech Name] has submitted case [ID] for review"
- Details: Case type, complexity tier, submission date

### Advisor Notifications

**When Case Completed (After Review Approved):**
- Title: "Your Case Report is Ready"
- Message: "Case [ID] analysis complete, report ready for download"
- Channel: Email + SMS (if enabled)

---

## 8. Key Metrics & Reporting

### Metrics Related to Review Process

**For Administrators/Managers:**
- Total cases pending review (by day)
- Average review time (days from pending to completed)
- Review approval rate (% approved vs. sent back)
- Review rejection rate (cases sent back for revisions)
- Multiple revision rate (cases requiring 2+ revision cycles)
- Average revisions per case before approval
- Level 1 tech "first-time approval" rate (quality indicator)

**For Level 2/3 Technicians:**
- Cases in my review queue
- Average time spent reviewing per case
- Review actions performed (approved/rejected/corrected counts)

**For Level 1 Technicians:**
- Cases awaiting review
- Approval rate (% cases approved on first review)
- Average feedback for improvements
- Common revision reasons (for skill development)

---

## 9. Quality Review Email Notifications

### Overview

All Level 1 technicians receive email notifications when their completed cases are reviewed by Level 2 or Level 3 technicians. These emails serve as the primary communication mechanism for quality review decisions and are logged in the audit trail.

### Emails Level 1 Technicians Receive

#### Email #1: **Case Approved** ✅
- **When Sent:** Immediately when Level 2/3 tech approves a Level 1 case
- **Recipient:** Level 1 technician who completed the case
- **Subject:** "Quality Review Complete: Your Case [ID] APPROVED"
- **Template:** case_approved_notification.html
- **Content:**
  - Approval confirmation
  - Reviewer name and tier level (Level 2 or 3)
  - Approval timestamp
  - Case proceeds to completion
- **Action:** No action needed; case automatically completed
- **Case Status:** Changes to 'completed'
- **Audit Trail:** Logged as email_sent with reviewer info

#### Email #2: **Revisions Requested** ✅
- **When Sent:** Immediately when Level 2/3 tech requests revisions
- **Recipient:** Level 1 technician who completed the case
- **Subject:** "Quality Review: Revisions Requested for Case [ID]"
- **Template:** case_revisions_needed_notification.html
- **Content:**
  - What revisions are needed (specific sections)
  - Reviewer name and tier level
  - Detailed feedback and comments
  - Deadline for revision completion
  - Instructions on how to resubmit
- **Action:** Level 1 tech must review feedback and make necessary revisions
- **Case Status:** Remains 'pending_review'
- **Audit Trail:** Logged with revision details and reviewer feedback

#### Email #3: **Corrections Required** ✅
- **When Sent:** Immediately when Level 2/3 tech requires corrections
- **Recipient:** Level 1 technician who completed the case
- **Subject:** "Quality Review: Corrections Required for Case [ID]"
- **Template:** case_corrections_notification.html
- **Content:**
  - What corrections are needed
  - Severity level (minor, moderate, critical)
  - Detailed explanation of issues
  - Reviewer name and tier level
  - Deadline for correction
- **Action:** Level 1 tech must correct errors and resubmit
- **Case Status:** Remains 'pending_review'
- **Audit Trail:** Logged with correction details and severity

#### Email #4: **Case Resubmitted Alert** ✅
- **When Sent:** Immediately when member resubmits a completed case
- **Recipient:** Technician currently assigned to case
- **Subject:** "Alert: Case [ID] Resubmitted by Member"
- **Content:**
  - Case has been resubmitted
  - Count of resubmissions
  - List of new documents uploaded
  - Member's resubmission reason/notes
- **Action:** Review member's new documents and assess changes
- **Case Status:** Changes to 'resubmitted'
- **Audit Trail:** Logged with resubmission count and member notes

### Email Delivery & Audit Trail

**All Quality Review Emails:**
- Sent immediately (not scheduled)
- Logged in audit trail with action_type='email_sent'
- Include reviewer identification for accountability
- Track delivery status (success/failed)
- Failed emails logged as 'email_failed' for admin recovery

**Finding Email History:**
1. View case detail → Audit Trail tab
2. Filter by action_type='email_sent'
3. See all review decision emails sent with timestamps and content

---

## 9. Benefits of Three-Tier Review System

1. **Quality Assurance:** All junior tech work reviewed before member sees it
2. **Consistency:** Senior techs ensure uniform quality standards
3. **Mentoring:** Feedback helps junior techs improve
4. **Risk Mitigation:** Catches errors before delivery
5. **Workload Flexibility:** Senior techs can work on hard cases while reviewing juniors
6. **Career Development:** Clear path for advancement (Level 1 → 2 → 3)
7. **Audit Trail:** Full traceability of who reviewed and approved each case

---

## 10. Comparison: Review vs. No Review

### Without Review Process
```
Level 1 Tech Completes
    ↓
Status = "Completed"
    ↓
Report visible to advisor
    ↓
Problem: No quality gate, errors reach advisors
```

### With Review Process (Implemented)
```
Level 1 Tech Completes
    ↓
Status = "Pending Review"
    ↓
Level 2/3 Tech Reviews
    ↓
├─ APPROVE → Status = "Completed" → Report visible
├─ REQUEST CHANGES → Status = "Accepted" → Level 1 reworks
└─ CORRECT → Fix issues, Status = "Completed" → Report visible
```

---

## Summary Table

| Aspect | Level 1 | Level 2 | Level 3 |
|--------|---------|---------|---------|
| **Experience** | New/Junior | 1-2+ years | 3+ years |
| **Own Cases** | ✅ | ✅ | ✅ |
| **Review Others** | ❌ | ✅ (L1 only) | ✅ (L1 only) |
| **Can Approve** | ❌ | ✅ | ✅ |
| **Can Correct** | ❌ | ✅ | ✅ |
| **Review Bypass** | Always required | N/A | N/A |
| **Queue** | Work queue | Review queue | Review queue |
| **Complexity** | All tiers | 1-2 primary | 2-3 primary |
| **Notification** | Gets feedback | Sees review queue | Sees review queue |

---

## Next Steps for Implementation

To fully implement the quality review workflow:

1. **Trigger Logic:** Modify `mark_case_complete()` view to check technician level
2. **Review Queue View:** Create view for Level 2/3 to see pending cases
3. **Review Actions:** Implement approve/reject/correct endpoints
4. **Audit Logging:** Log all review actions with timestamps and notes
5. **Notifications:** Email/SMS for review decisions
6. **Dashboard:** Show review queue stats and metrics
7. **Testing:** Create test cases for all review scenarios
8. **Documentation:** Update user guides and training materials

---

**End of Document**

---

## Reference Diagrams & Hierarchy

### 1.2 Visual Hierarchy

```
┌─────────────────────────────────────────────────────┐
│             TECHNICIAN HIERARCHY                    │
├─────────────────────────────────────────────────────┤
│                                                     │
│  Level 3: Senior Technician                        │
│  ├─ Expert (3+ years)                             │
│  ├─ Can review Level 1 work ✅                     │
│  ├─ Handles escalations                            │
│  └─ May lead team                                  │
│                                                     │
│  Level 2: Technician                               │
│  ├─ Experienced (1-2+ years)                       │
│  ├─ Can review Level 1 work ✅                     │
│  └─ Full case authority                            │
│                                                     │
│  Level 1: New Technician                           │
│  ├─ Junior/New (entry-level)                       │
│  ├─ REQUIRES review ⚠️                              │
│  ├─ Own case processing                            │
│  └─ No approval authority                          │
│                                                     │
└─────────────────────────────────────────────────────┘
```

---

## 2. Case Complexity Tiers (Internal Classification)

**Important:** Case complexity tiers are **DIFFERENT** from technician levels and are **invisible to advisors**.

### 2.1 Three Complexity Tiers

#### **Tier 1: Plain Cases**
- **Description:** Straightforward, simple cases
- **Characteristics:**
  - Straightforward calculations
  - No special services requested
  - Standard retirement planning
  - Minimal complexity
- **Processing Time:** 2-4 hours
- **Typical Work:** 
  - Basic retirement date projection
  - Standard TSP calculations
  - No special circumstances
- **Technician Assignment:** Can be assigned to any level (1, 2, or 3)

#### **Tier 2: Special Services**
- **Description:** Cases with special circumstances
- **Characteristics:**
  - **ANY service marked "yes" on page 2-3 of Federal Fact Finder**
  - Disability cases
  - Multiple scenarios requested
  - More complex calculations required
- **Processing Time:** 4-6 hours
- **Services Included:**
  - Survivor benefits analysis
  - Widow situation planning
  - Court orders or legal constraints
  - Contested benefits
  - Medical retirement
  - Other special circumstances
- **Technician Assignment:** Typically Level 2 or Level 3

#### **Tier 3: Complex Cases**
- **Description:** Highly complex cases requiring expertise
- **Characteristics:**
  - Court orders involved
  - Widow situations
  - Executive involvement
  - Multiple concurrent issues
  - Unusual circumstances
- **Processing Time:** 6-12+ hours (can exceed)
- **Examples:**
  - Court-ordered benefit division
  - Widow/survivor special claims
  - Executive branch special rules
  - Military-to-civilian benefit transfers
  - Unusual or precedent-setting situations
- **Technician Assignment:** Level 3 (Senior) primarily

### 2.2 Credit Pricing is Tier-Agnostic

**Critical Point:** All tiers cost the **SAME credits** to the advisor:
- Tier 1 case = 1 credit (same as Tier 3)
- Tier 2 case = 1 credit (same as Tier 1)
- Tier 3 case = 1 credit (same as Tier 1)

**Why?** The tier classification is for **internal workload management**, not for charging. Advisors don't know (or need to know) the tier of their case.

---

## 3. Quality Review Process

### 3.1 When Review is Triggered

The review process **AUTOMATICALLY TRIGGERS** when:

**TRIGGER:** Level 1 technician clicks "Mark as Complete" on their assigned case

```
Level 1 Tech           System                    Case Status
     │                   │                            │
     ├─ Completes case ──────────────────────────────┤
     │                   │                            │
     │                   │ Creates draft report      │
     │                   ├─────────────────────────>│
     │                   │                            │
     │                   │ Check: assigned_to        │
     │                   │ .user_level == 'level_1'? │
     │                   │                            │
     │                   ├─ YES ─────────────────────┤
     │                   │                            │
     │                   │ Set status =              │
     │                   │ "pending_review"          │
     │                   │ (NOT "completed")         │
     │                   ├──> Status changed to     │
     │                   │     "pending_review"     │
     │                   │                            │
     └─────── Notification: "Your case is now in review queue"
```

### 3.2 Case Status Transitions

The review process creates a new status gate:

```
OLD FLOW (WITHOUT REVIEW):
Submitted → Accepted → In Progress → Completed ← Released to Advisor

NEW FLOW (WITH REVIEW - LEVEL 1):
Submitted → Accepted → In Progress → Pending Review → Completed ← Released

                                           ↑
                                     Level 2/3 Tech
                                        Must Approve
```

**Status Field Values:**
```python
STATUS_CHOICES = [
    ('submitted', 'Submitted'),           # Initial state
    ('accepted', 'Accepted'),             # Tech accepted case
    ('in_progress', 'In Progress'),       # Tech working on it
    ('pending_review', 'Pending Review'), # ⭐ NEW: Awaiting senior tech review
    ('completed', 'Completed'),           # Analysis complete, ready for member
    ('on_hold', 'On Hold'),               # Needs more info
    ('needs_resubmission', 'Needs Resubmission'),  # Member needs to resubmit
]
```

### 3.3 Review Queue Formation

**When** a Level 1 tech completes a case:
1. Case status becomes `pending_review`
2. Case appears in **Review Queue** (visible only to Level 2/3 techs)
3. **NOT** visible to advisor yet
4. **NOT** marked as "Completed" yet
5. Awaits Level 2/3 tech action

### 3.4 Review Queue Details

#### Database Table: `case_review_history`

```sql
CREATE TABLE case_review_history (
    review_id INT AUTO_INCREMENT PRIMARY KEY,
    case_id INT NOT NULL,
    reviewed_by INT NOT NULL,        -- Level 2/3 tech who performed review
    original_tech INT NOT NULL,      -- Level 1 tech whose work was reviewed
    review_action VARCHAR(50) NOT NULL CHECK (
        review_action IN ('approved', 'sent_back', 'corrected')
    ),
    review_notes TEXT,               -- Feedback for Level 1 tech
    reviewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_case (case_id),
    INDEX idx_reviewed_by (reviewed_by),
    INDEX idx_original_tech (original_tech),
    INDEX idx_reviewed_at (reviewed_at),
    INDEX idx_review_action (review_action),
    FOREIGN KEY (case_id) REFERENCES cases(case_id) ON DELETE CASCADE,
    FOREIGN KEY (reviewed_by) REFERENCES users(user_id),
    FOREIGN KEY (original_tech) REFERENCES users(user_id)
);
```

#### What Level 2/3 Can See in Review Queue

```
Case ID    | Level 1 Tech    | Status          | Date Submitted | Action
-----------|-----------------|-----------------|----------------|----------
2024-1001  | John Smith      | Pending Review  | Jan 15, 2024  | Review
2024-1003  | Jane Doe        | Pending Review  | Jan 15, 2024  | Review
2024-1007  | John Smith      | Pending Review  | Jan 16, 2024  | Review
2024-1012  | Bob Johnson     | Pending Review  | Jan 17, 2024  | Review
```

**Visible in Review Queue:**
- ✅ All Level 1 technician cases with `status = 'pending_review'`
- ✅ Original technician's name
- ✅ Date submitted
- ✅ Complete case details (investigation, reports, documents)
- ✅ Level 1 tech's notes and findings
- ✅ Uploaded report

**NOT visible:**
- ❌ Other Level 2/3 technician's cases (unless shared review queue)
- ❌ Level 1 tech's other cases (unless in review)

### 3.5 Review Actions Available to Level 2/3 Techs

When reviewing a Level 1 case, the senior tech can take **ONE** of three actions:

#### **Action 1: APPROVE** ✅

**Scenario:** Senior tech reviews Level 1's work, finds it acceptable

**Process:**
```
Level 2/3 Tech                 System                    Case
     │                           │                         │
     ├─ Reviews case ─────────────┤                        │
     │ (investigation,            │                        │
     │  report, findings)          │                        │
     │                             │                        │
     │ All looks good ─────────────┤                        │
     │ Click "APPROVE"             │                        │
     │                             │ Update:              │
     │                             ├─ reviewed_by = L2/L3 │
     │                             ├─> reviewed_by set
     │                             ├─ review_action =    │
     │                             │  'approved'          │
     │                             ├─> Insert review_history
     │                             ├─ status = 'completed'│
     │                             ├─> Status changed
     │                             ├─ Log to audit trail   │
     │                             ├─> Audit recorded
     │                             ├─ Send notification   │
     │                             └─> Level 1 notified
     │
     └─ Notification: "Your case #2024-1001 was approved by Jane Doe"
                      "Status: Ready for release to advisor"
```

**Result:**
- Case status → `completed` ✅
- Advisor can now see/download report
- Report becomes available to advisor (based on release schedule)
- Level 1 tech receives notification of approval
- Entry created in `case_review_history` with action='approved'

**Use Cases:**
- Investigation thorough and accurate
- Report well-written and complete
- No issues found
- Ready for immediate release

---

#### **Action 2: REQUEST CHANGES** 🔄

**Scenario:** Senior tech finds issues requiring rework

**Process:**
```
Level 2/3 Tech                 System                    Case
     │                           │                         │
     ├─ Reviews case ─────────────┤                        │
     │                             │                        │
     │ Issues found ──────────────┤                        │
     │ (incomplete analysis,       │                        │
     │  missing docs, etc)         │                        │
     │                             │                        │
     │ Click "REQUEST CHANGES"    │                        │
     │ Add notes:                  │                        │
     │ "Need to verify TSP        │                        │
     │  balance with GHL..."       │                        │
     │                             │ Update:              │
     │                             ├─ reviewed_by = L2/L3 │
     │                             ├─> reviewed_by set
     │                             ├─ review_action =    │
     │                             │  'sent_back'         │
     │                             ├─> Insert review_history
     │                             ├─ review_notes =     │
     │                             │  "Need to verify..." │
     │                             ├─> Notes stored
     │                             ├─ status = 'accepted' │
     │                             ├─> Status reverted (back to work)
     │                             ├─ assigned_to unchanged
     │                             ├─> Level 1 still owns it
     │                             ├─ Send notification   │
     │                             └─> Level 1 gets review feedback
     │
     └─ Notification: "Case #2024-1001 needs revisions from Jane Doe"
                      "Review notes: Need to verify TSP balance with GHL..."
```

**Result:**
- Case status → `accepted` (back to working state)
- Level 1 tech receives notification with feedback
- Case **REMOVED** from review queue
- Case appears back in Level 1 tech's "my cases" list
- Entry created in `case_review_history` with action='sent_back'
- Level 1 tech can now make requested changes
- When ready, Level 1 tech clicks "Complete" again
- Case goes back to `pending_review` status
- Appears back in review queue for another Level 2/3 tech to review

**Use Cases:**
- Incomplete investigation
- Report quality issues
- Missing supporting documents
- Calculation errors
- Incomplete fact-finder data
- Need to gather more member information

---

#### **Action 3: CORRECT** (Optional) 🛠️

**Scenario:** Senior tech makes edits/corrections themselves

**Process:**
```
Level 2/3 Tech                 System                    Case
     │                           │                         │
     ├─ Reviews case ─────────────┤                        │
     │                             │                        │
     │ Issues found BUT ──────────┤                        │
     │ Quick to fix               │                        │
     │                             │                        │
     │ Makes edits:                │                        │
     │ - Fixes calculations        │                        │
     │ - Updates report            │                        │
     │ - Clarifies findings        │                        │
     │                             │                        │
     │ Click "CORRECT & APPROVE"  │                        │
     │ Add notes:                  │                        │
     │ "Fixed TSP calc, was..."   │                        │
     │                             │ Update:              │
     │                             ├─ reviewed_by = L2/L3 │
     │                             ├─> reviewed_by set
     │                             ├─ review_action =    │
     │                             │  'corrected'         │
     │                             ├─> Insert review_history
     │                             ├─ review_notes =     │
     │                             │  "Fixed TSP calc..." │
     │                             ├─> Notes stored
     │                             ├─ status = 'completed' │
     │                             ├─> Status changed (approved)
     │                             ├─ Log edits to       │
     │                             │  audit trail         │
     │                             ├─> Audit recorded
     │                             ├─ Send notification   │
     │                             └─> Level 1 & advisor notified
     │
     └─ Notifications: 
         "Case #2024-1001 corrected by Jane Doe and approved"
         "Changes made: Fixed TSP calculation..."
         
         TO ADVISOR:
         "Your case #2024-1001 is ready for download"
```

**Result:**
- Case status → `completed` ✅
- Senior tech's corrections now part of official case record
- Case available to advisor
- Entry created in `case_review_history` with action='corrected'
- Both Level 1 tech and advisor notified of corrections
- Audit trail documents who made corrections and what changed
- Report version updated (new version created with corrections)

**Use Cases:**
- Minor calculation errors
- Quick clarifications needed
- Senior tech expertise improves report quality
- Faster turnaround than sending back for revision
- Small issues that don't require full re-investigation

---

### 3.6 Complete Review Workflow Diagram

```
START: Level 1 Tech Completes Case
    │
    ▼
┌─────────────────────────────────┐
│ Case Status = 'Pending Review' │
└────────────┬────────────────────┘
             │
    APPEARS IN LEVEL 2/3 REVIEW QUEUE
             │
             ▼
    ┌─────────────────────────┐
    │ Level 2/3 Tech Reviews: │
    │ - Investigation         │
    │ - Report                │
    │ - Documents             │
    │ - Findings              │
    └────────┬────────────────┘
             │
    ┌────────┴────────┬──────────────┐
    │                 │              │
    ▼                 ▼              ▼
 APPROVE         REQUEST CHANGES   CORRECT
  ✅               🔄               🛠️
    │                 │              │
    │ status →        │ status →     │ Make edits,
    │ 'completed'     │ 'accepted'   │ status →
    │                 │              │ 'completed'
    │ Ready for       │ Back to      │
    │ release to      │ Level 1 work │ Ready for
    │ advisor         │              │ release
    │                 │              │
    └────────┬────────┴──────────────┘
             │
             ▼
    ┌─────────────────────────┐
    │ CASE COMPLETED          │
    │ Release to Advisor      │
    │ Report Available        │
    └─────────────────────────┘
             │
             ▼
    END: Advisor downloads report
```

---

## 4. Database Fields Supporting Review Process

### 4.1 Case Model Fields

```python
class Case(models.Model):
    # ... other fields ...
    
    # Field 11 in spec: Reviewed By (Level 2/3 Technician for Level 1 cases)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_cases',
        limit_choices_to={
            'role': 'technician', 
            'user_level__in': ['level_2', 'level_3']  # ← Only Level 2/3
        }
    )
    
    # Review-related fields (extended)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_notes = models.TextField(blank=True)
    review_status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending Review'),
            ('approved', 'Approved'),
            ('changes_requested', 'Changes Requested'),
        ],
        default='pending',
        null=True,
        blank=True
    )
```

### 4.2 Audit Tables

```sql
-- Tracks all status changes including review transitions
CREATE TABLE case_status_history (
    history_id INT AUTO_INCREMENT PRIMARY KEY,
    case_id INT NOT NULL,
    old_status VARCHAR(50),
    new_status VARCHAR(50) NOT NULL,
    changed_by INT NOT NULL,     -- User who triggered change
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    INDEX idx_case (case_id),
    INDEX idx_changed_by (changed_by),
    FOREIGN KEY (case_id) REFERENCES cases(case_id) ON DELETE CASCADE,
    FOREIGN KEY (changed_by) REFERENCES users(user_id)
);

-- Tracks quality review actions
CREATE TABLE case_review_history (
    review_id INT AUTO_INCREMENT PRIMARY KEY,
    case_id INT NOT NULL,
    reviewed_by INT NOT NULL,           -- Level 2/3 tech
    original_tech INT NOT NULL,         -- Level 1 tech
    review_action VARCHAR(50) NOT NULL CHECK (
        review_action IN ('approved', 'sent_back', 'corrected')
    ),
    review_notes TEXT,
    reviewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_case (case_id),
    INDEX idx_reviewed_by (reviewed_by),
    INDEX idx_review_action (review_action),
    FOREIGN KEY (case_id) REFERENCES cases(case_id) ON DELETE CASCADE,
    FOREIGN KEY (reviewed_by) REFERENCES users(user_id),
    FOREIGN KEY (original_tech) REFERENCES users(user_id)
);
```

---


---

## Reference Diagrams & Hierarchy

