# Manager Workflow & Decision Tree

## Role Overview
**Managers** oversee technician operations, manage case assignments, handle escalations, and ensure quality. They provide a middle layer between technicians and administrators, managing workload and performance.

> **📊 AUDIT TRAIL TRACKING NOTE:**  
> All manager activities are automatically tracked in the audit trail system, including case assignments, holds/resumes, tier changes, and access to audit reports. Managers have access to comprehensive audit reports showing team performance, case workflows, and quality metrics. Administrator can view manager actions for oversight and compliance.

---

## Manager Workflow Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                      MANAGER WORKFLOW                            │
└──────────────────────────────────────────────────────────────────┘

                          START
                            │
                            ▼
                  ┌─────────────────────────┐
                  │ Access Manager          │
                  │ Dashboard               │
                  └────────┬────────────────┘
                           │
                ┌──────────┼──────────┐
                │          │          │
                ▼          ▼          ▼
        ┌──────────┐ ┌────────┐ ┌──────────┐
        │ View Team │ View    │ │Review    │
        │ Cases &   │ Metrics │ │Escalated │
        │ Stats     │ & Perf  │ │Cases     │
        └─┬────────┘ └────┬───┘ └────┬─────┘
          │               │         │
          ▼               ▼         ▼
      ┌────────────────────────────────────┐
      │ Take Action Based on Findings      │
      └────┬─────────────────────────────────┘
           │
    ┌──────┼──────┬──────┬────────┬────────┐
    │      │      │      │        │        │
   CASE   TEAM  ASSIGN  REQUEST  ESCALATE SYSTEM
  ISSUES  LOAD  CASE    INFO     TO ADMIN MAINT
    │      │      │      │        │        │
    ▼      ▼      ▼      ▼        ▼        ▼
┌─────┐ ┌───┐ ┌────┐ ┌────┐ ┌──────┐ ┌──────┐
│     │ │   │ │    │ │    │ │      │ │      │
└─────┘ └───┘ └────┘ └────┘ └──────┘ └──────┘
  │      │      │      │        │        │
  └──────┴──────┴──────┴────────┴────────┘
           │
           ▼
    ┌────────────────┐
    │ Monitor Team   │
    │ Performance &  │
    │ Case Outcomes  │
    └────────────────┘
           │
           ▼
         END
```

---


## Core Manager Actions

Managers oversee technician operations and case workflows:

- **Assign Cases** - Distribute cases to technicians
- **Monitor Performance** - Track metrics, completion times, quality
- **Escalate Issues** - Handle complex cases and exceptions
- **Review Audit Trail** - Track team activity and compliance

---

## Key Manager Actions

### 1. **View Team Dashboard**
- ✓ See all team cases at a glance
- ✓ Case count by status
- ✓ Individual technician workload
- ✓ Performance metrics (case completion, quality)
- ✓ Overdue cases alerts
- ✓ Email notification status for completed cases
- ✓ Monitor case release scheduling (tech-controlled per-case)

### 2. **Manage Case Assignments**
- ✓ View unassigned cases (queue) with "Review & Accept" needed
- ✓ **Accept & Assign** new cases (or delegate to techs):
  - Review Federal Fact Finder completeness
  - Verify supporting documents
  - Adjust credit value if needed
  - Assign tier (Tier 1, 2, or 3)
  - Select technician
  - ⚠️ System warns if tier > tech level (can override)
- ✓ **Reject/Request More Info** if case incomplete:
  - Select rejection reason
  - Add notes about what's needed
  - Member receives email with requirements
  - Case status → "Needs Resubmission"
- ✓ **Reassign** cases between technicians:
  - Click "Reassign" on accepted case
  - Select new technician
  - Add reason (optional)
  - Audit trail automatically recorded
- ✓ Balance workload across team
- ✓ Assign based on expertise/urgency
- ✓ Verify email notifications are sent correctly after release

### 2A. **Dashboard Status Improvements** (NEW - Jan 2026)
- ✓ **Status badge hover tooltips:**
  - Hover over any status badge to see detailed description
  - Examples:
    - "Submitted" → "Case received and waiting for technician to start"
    - "On Hold" → "Case temporarily paused"
    - "Completed" → "Case completed and released to member" (if actual_release_date set)
    - "Scheduled for Release" → "Completed but scheduled for future release" (if scheduled_release_date set)
  - Helps clarify case state without needing legend
- ✓ **Delayed release system understanding:**
  - Cases with `actual_release_date`: Case is released (member can see reports)
  - Cases with `scheduled_release_date` (no actual_release_date): Awaiting release date
  - If case is completed but neither date set: Still in progress on technician's end
- ✓ **Clean dashboard layout:**
  - Status legend removed (replaced with hover tooltips)
  - Actions column properly populated with View, Edit, Release buttons
  - Column alignment standardized for better readability
  - On-Time/Late metrics visible for completed cases

### 2B. **Column Visibility Management**
### 2C. **Notification System Overview** (NEW)
- ✓ Can view own notification center if notifications exist
- ✓ Can access all case messaging via audit trail
- ✓ Cannot directly view member notifications (member-only access)
- ✓ Can monitor team messaging via case detail pages
- ✓ Can see email notification status on case detail
- ✓ Can respond to member messages (same as technician)
- ℹ️ **Message Notifications:** Instant (no email sent)
- ℹ️ **Case Completion Emails:** Scheduled 0-24 hours (different system)

### 2D. **Customize dashboard view:**
  - Click "Column Settings" button (gear icon)
  - Toggle columns on/off to show/hide:
    - Case ID, Member Name, Status, Created Date
    - Assigned Technician, Tier, Credit Value, Documents Count
    - Notes, Last Modified, Actions
  - Collapsible filter section (saves vertical space)
  - Filter counter showing active filters
- ✓ Preferences auto-save to your account
- ✓ Settings persist across login sessions
- ✓ Reduces horizontal scrolling
- ✓ Focus on relevant case information

### 3. **Monitor Case Progress**
- ✓ Review case details (all cases)
- ✓ See case timeline & history
- ✓ Read internal tech notes
- ✓ Check member communications
- ✓ Identify bottlenecks

### 4. **Escalation Handling**
- ✓ View escalated cases
- ✓ Review escalation reason
- ✓ Make decision: Resolve or Escalate to Admin
- ✓ Add management notes
- ✓ Follow up with technician

### 5. **Quality Review**
- ✓ Review cases completed by Level 1 technicians
- ✓ Check report quality and completeness
- ✓ Identify training needs for junior technicians
- ✓ Approve cases to release to members
- ✓ Request revisions if needed
- ✓ Monitoring team quality metrics

**Your Quality Review Role:**
While **technicians (Level 2/3)** perform technical case reviews, **managers** oversee quality trends:
- Monitor rejection rates by technician
- Identify common issues across team
- Provide coaching feedback to Level 1 technicians
- Approve escalations related to quality concerns
- Track case revision rates
- Assess training effectiveness

### 6. **Release Management**
- ✓ See scheduled release dates
- ✓ Release immediately if needed (rush)
- ✓ Approve delayed releases
- ✓ Contact member if issues
- ℹ️ Technicians now control release timing per-case on the Pre-Completion Review page (Release Now or Schedule Release)

### 7. **Hold Management**
- ✓ View cases placed on hold
- ✓ See hold reason and duration
- ✓ Monitor hold duration tracking
- ✓ **Put Case on Hold** (if technician hasn't):
  - Click "Put on Hold" button
  - Select reason (member docs waiting, technical issue, etc)
  - Select duration (immediate, 2h, 4h, 8h, 1 day, custom)
  - Case ownership preserved
  - Status changes to 'hold'
- ✓ **Resume Case from Hold**:
  - Click "Resume from Hold" button
  - Add reason for resuming
  - Status changes back to 'accepted'
  - Case returns to technician's active queue
- ✓ Audit trail tracks all hold actions
- ✓ Hold duration dates are calculated and stored

---

## Manager Case Actions

### Action: Put Case on Hold
```
Case: #1045
Tech: Alice (working on case)
Issue: Waiting for member to provide additional documents
Decision: Pause Alice's work temporarily

Steps:
1. Open case detail
2. Click "Put Case on Hold" button
3. Select reason: "Waiting for Member Documents"
4. Select duration: "4 Hours" (or custom)
5. Click "Confirm Put on Hold"
Result: Case status → 'hold'
        Alice's ownership preserved
        Hold timestamp recorded
        Duration set: 4 hours
        Audit log updated

6. When ready to resume:
   Click "Resume from Hold"
   Add reason: "Member sent documents"
   Status → 'accepted'
   Alice can continue work
```

### Action: Reassign Case
```
Current Tech: Alice (Tech A)
Reason: Alice too busy (8 cases)
New Tech: Dennis (Tech D - 2 cases)

Steps:
1. Open case detail
2. Click "Reassign Case"
3. Select Dennis from dropdown
4. Add reason: "Load balancing"
5. Click "Reassign"
Result: Case moves to Dennis, Alice notified
```

### Action: Release Case Immediately
```
Case: #1042
Status: Completed, scheduled for release in 2 hours
Issue: Member needs rush processing (verified by tech)

Steps:
1. Open case detail
2. See "Scheduled Release" status
3. Click "Release Immediately" (if authorized)
4. Confirm action
Result: Member sees report now, not in 2 hours
```

### Action: Request Information
```
Case: #1038
Status: Pending escalation
Issue: Need clarification before deciding

Steps:
1. Open escalated case
2. Click "Request Information"
3. Select what's needed: documents, clarification, etc
4. Add message to technician
5. Submit request
Result: Tech notified, adds info, manager decides again
```

### Action: Escalate to Admin
```
Case: #1041
Status: Complex issue beyond manager scope
Issue: System limitation or high-level decision needed

Steps:
1. Open case detail
2. Click "Escalate to Administrator"
3. Select reason: system issue, policy question, etc
4. Add detailed notes
5. Submit
Result: Admin reviews, takes appropriate action
```

---

## Manager Workload Scenarios

### Scenario A: "Tech A has too many cases"
1. Check dashboard - see Tech A: 12 cases
2. Find similar-level tech with fewer: Tech D: 3 cases
3. Review Tech A's cases for ones suitable to reassign
4. Pick balanced cases to move
5. Use "Reassign Case" for each
6. Check Tech A's remaining work is manageable

### Scenario B: "Case is escalated - what now?"
1. See escalation flag in dashboard
2. Open escalated case
3. Read escalation reason from tech
4. Review case details & history
5. Decide: Can I resolve this?
   - Yes: Fix issue, update tech
   - No: Escalate to admin
6. Document decision & communicate

### Scenario C: "Quality issue in tech's work"
1. Review completed case
2. Notice quality issue (incomplete, error, etc)
3. Don't release to member yet
4. Add internal note to tech: "Need revision - [reason]"
5. Contact tech directly
6. Tech revises and resubmits
7. Review again before release

---

## Performance Monitoring

### Team Metrics to Track
| Metric | Target | Action if Below |
|--------|--------|-----------------|
| Cases/week | 25-30 | Check for bottlenecks |
| Avg completion time | 24-36 hrs | Add resources or simplify |
| Quality score | >90% | More training needed |
| Member satisfaction | >4.5/5 | Review low scores |
| On-time delivery | >95% | Check escalations |

### Individual Tech Performance
```
Tech Report Card:
┌─ Name: Alice
├─ Cases This Week: 8
├─ Avg Time: 1.1 days
├─ Quality: 96%
├─ Member Sat: 4.8/5
└─ Status: Excellent ✓

Tech Report Card:
┌─ Name: Bob
├─ Cases This Week: 5
├─ Avg Time: 1.8 days
├─ Quality: 87%
├─ Member Sat: 4.2/5
└─ Status: Needs support ⚠
```

---

## Escalation Guidelines

### When to Escalate to Admin:
- System errors or limitations
- Policy decisions needed
- High-value/high-stakes cases
- Member complaints beyond manager scope
- Configuration/setting changes needed
- Data integrity issues

### When to Handle at Manager Level:
- Case reassignment (load balancing)
- Tech performance issues
- Member communication
- Timeline adjustment
- Quality review & feedback

---

## Manager Communication Channels

### Internal Communication
- **Internal Case Notes**: Add management perspective
- **Direct to Tech**: Assign tasks, provide feedback
- **To Admin**: Escalate complex issues
- **Performance Reviews**: Scheduled feedback sessions

### External Communication
- **Member Contacts**: Through support if needed
- **Technician's Tech**: Collaborate on tech issues
- **HR**: If staffing/performance issues

---

## Case Status Flow (Manager Perspective)

```
SUBMITTED (In Queue)
    ↓ [Manager assigns or tech takes]
ACCEPTED (Assigned to Tech)
    ↓ [Tech investigates]
IN_PROGRESS (Tech working)
    ├─ [May request member docs]
    ├─ [Tech may escalate for help]
    ↓ [Tech completes work]
COMPLETED (Ready for release)
    ├─ [Manager may review for quality]
    ├─ [Manager may release immediately if needed]
    ├─ [Or scheduled for delayed release]
    ↓
RELEASED (Member can see)
    ↓
CLOSED (Archived)
```

---

## Manager Tools & Features

### Dashboards
- Team performance dashboard
- Individual tech dashboards
- Case status dashboard
- Escalation alerts dashboard

### Reports
- Weekly case completion report
- Team performance report
- Quality metrics report
- Member satisfaction report

### Actions
- Assign/reassign cases
- Release cases immediately
- Request additional information
- Escalate to admin
- Add management notes
- Mark cases for review

---

## Common Manager Tasks by Day

### Morning (Check-in)
- [ ] Review overnight escalations
- [ ] Check team load distribution
- [ ] Identify any overdue cases
- [ ] Read rush/priority messages

### Mid-Day (Management)
- [ ] Review escalated cases
- [ ] Reassign cases if needed
- [ ] Monitor team progress
- [ ] Respond to escalations

### End of Day (Review)
- [ ] Check case completions
- [ ] Review quality samples
- [ ] Plan tomorrow's assignments
- [ ] Document issues/improvements

### Weekly (Planning)
- [ ] Detailed performance review
- [ ] 1:1s with team members
- [ ] Training opportunities
- [ ] Capacity planning

---

## Troubleshooting for Managers

| Issue | Solution |
|-------|----------|
| Can't find case to assign | Use search, check filters |
| Tech won't accept reassignment | Contact admin - may need force-reassign |
| Case stuck in queue | Assign it or check for system issues |
| Member upset about wait time | Check release date, can release early if needed |
| Quality issue discovered | Don't release, contact tech, request revision |
| Tech performance declining | Pull analytics, schedule 1:1, discuss issues |

---

## Email Notifications & Visibility

### What Emails Managers Receive

**Managers receive NO direct case emails.**

Instead, managers have visibility into email notifications through:
- Case dashboard email status fields
- Audit trail email action logs
- Email delivery monitoring

### Email Status on Dashboard

When viewing cases in dashboard, managers can see email-related information:

| Field | Shows | Purpose |
|-------|-------|---------|
| Hold Email Status | ✓ Sent / ✗ Failed | Verify member received hold notification |
| Release Email Scheduled | Date scheduled | When member will get release email |
| Release Email Sent | Timestamp | When release email was delivered |
| Email Delivery Status | Success/Failed/Pending | Email delivery confirmation |
| Member Notifications | Unread/Read count | In-app notification status |

### Email Monitoring for Escalations

**When case has issues, check email status:**

| Scenario | Check | Action |
|----------|-------|--------|
| Case put on hold | Audit trail for email_sent | Verify member notified |
| Case completed | Scheduled_email_date | Verify release email scheduled |
| Resubmitted case | Audit trail for email_sent | Verify tech was notified |
| Failed communication | Email_failed in audit trail | Troubleshoot delivery issue |

### Email Tracking Audit Trail

**To view email history for any case:**

1. Navigate to case detail
2. Click "Audit Trail" tab
3. Filter by action_type='email_sent' OR 'email_failed'
4. View: Timestamp, recipient email, email type, delivery status

**Email Actions in Audit Trail:**
- `email_sent` = Email successfully delivered
- `email_failed` = Email delivery failed
- `email_notification_sent` = Scheduled release email sent
- `notification_created` = In-app notification + email created

### Manager's Email Responsibilities

**Managers should monitor emails when:**

1. **Placing case on hold:** Verify member received hold email → Check audit trail
2. **Managing case completion:** Verify release email scheduled → Check dashboard date
3. **Handling resubmissions:** Verify assigned tech received alert → Audit trail check
4. **Escalating to admin:** Use email failures as evidence → Email_failed entries

---

## 📊 Audit Trail Activities (Manager Role)

All manager activities are automatically tracked in the system's audit trail. Here's what gets logged:

| Activity | Audit Code | When Logged | Details Captured |
|----------|-----------|-------------|------------------|
| **Login** | `login` | Immediate | Session start, manager ID, timestamp |
| **Logout** | `logout` | Immediate | Session end, duration |
| **Assign Case to Tech** | `case_assigned` | On assignment | Case ID, technician assigned, reason, manager ID |
| **Reassign Case** | `case_reassigned` | On reassignment | From tech, to tech, reason, manager authorization |
| **Place Case on Hold** | `case_held` | On hold | Case ID, reason, hold duration, manager ID |
| **Resume Case** | `case_resumed` | On resumption | Case ID, reason, who resumed, timestamp |
| **Change Case Tier** | `case_tier_changed` | On change | Previous/new tier, case ID, reason, manager ID |
| **Force Release Case** | `case_status_changed` | On release | Case ID, release time, member notified, manager ID |
| **Escalate to Admin** | `case_updated` | On escalation | Case ID, escalation reason, admin destination |
| **Review Member Profile** | `member_profile_updated` | Optional | Member ID, fields reviewed (no changes logged) |
| **Access Audit Reports** | `audit_log_accessed` | On access | Report type, filters used, data range, manager ID |
| **Generate Performance Report** | `report_generated` | On generation | Report type, team scope, date range, manager ID |
| **Add Team Note** | `note_added` | On post | Note text, visibility, team members affected |
| **Delegate to Technician** | `user_role_changed` | On delegation | Tech granted powers, scope, duration, manager ID |
| **Approve Quality Review** | `review_submitted` | On approval | Case ID, reviewed by tech, approved by manager, score |
| **Request Case Revision** | `case_updated` | On request | Case ID, revision reason, tech assigned |

### Key Audit Activities

**Team Management Tracking:**
- All case assignments and reassignments logged with manager authority
- Hold/resume decisions tracked with business justification
- Escalations to admin include reasoning for audit trail
- Tier changes visible to administrators for oversight

**Performance Oversight:**
- Manager access to audit reports is itself logged (meta-audit)
- Report generation tracked for compliance verification
- Analytics access shows when managers reviewed data
- Performance trends documented in audit trail

**Case Quality Assurance:**
- Quality review approvals/rejections captured
- Manager overrides logged with justification
- Early release decisions documented
- Case revision requests traceable

### Audit Trail Uses for Managers
- **Accountability:** All decisions documented for audit trail compliance
- **Team Performance:** Analytics show which techs are productive
- **Case Status:** Quick access to case history and decision trail
- **Disputes:** Evidence of how cases were managed
- **Compliance:** Demonstrate proper case management procedures

### Access Audit Information
- Managers can view team activity through dedicated audit reports
- Activity Summary Report - system-wide overview
- User Activity Report - individual tech tracking
- Case Change History - modification timeline
- All reports accessible via "Audit & Compliance" menu

---

## Manager Support Resources

**Need Help?**\n- Admin on-call for escalations
- Email: manager-support@company.com
- Monthly manager meetings
- Training docs in knowledge base
- HR for personnel issues

---

## Reference Diagrams

## Manager Dashboard View

```
┌────────────────────────────────────────────────────────────┐
│ MANAGER DASHBOARD                                          │
├────────────────────────────────────────────────────────────┤
│                                                             │
│ TEAM OVERVIEW                    CASE STATUS              │
│ ├─ Techs: 5 active              ├─ Total Cases: 247      │
│ ├─ Cases Assigned: 43           ├─ New: 8                │
│ ├─ Avg Completion: 1.2d         ├─ In Progress: 28       │
│ └─ Quality Score: 94%           └─ Completed: 211        │
│                                                             │
│ THIS WEEK'S METRICS              BOTTLENECKS              │
│ ├─ Cases Completed: 42          ├─ Pending Escalations: 3│
│ ├─ Avg Resolution Time: 24h     ├─ Overdue Cases: 2      │
│ ├─ Quality Issues: 1             ├─ Waiting on Member: 5  │
│ └─ Member Satisfaction: 4.6/5   └─ System Issues: 0      │
│                                                             │
│ TEAM LOAD DISTRIBUTION           ACTION ITEMS            │
│ ├─ Tech A: 8 cases (28%)         ├─ Review Tech A case   │
│ ├─ Tech B: 7 cases (24%)         ├─ Check escalation     │
│ ├─ Tech C: 6 cases (20%)         ├─ Contact member on 2  │
│ ├─ Tech D: 5 cases (18%)         └─ Approve 3 releases   │
│ └─ Tech E: 2 cases (7%)                                   │
│                                                             │
└────────────────────────────────────────────────────────────┘
```

---

## Decision Tree: "What Should I Manage?"

```
                START: Manager checking system
                            │
                            ▼
                ┌──────────────────────────┐
                │ Are there issues to      │
                │ address?                 │
                └────────┬─────────────────┘
                         │
    ┌────────────────────┼────────────────────┐
    │                    │                    │
 TEAM ISSUE        CASE ISSUE            SYSTEM
 (Performance)     (Escalation/          (Config/
                   Problem)              Process)
    │                    │                    │
    ▼                    ▼                    ▼
┌────────────┐     ┌────────────┐     ┌────────────┐
│ Check Team │     │ Open       │     │ Contact   │
│ Metrics    │     │ Escalated  │     │ Admin     │
└─────┬──────┘     │ Case       │     └────────────┘
      │            └─────┬──────┘
      ▼                   ▼
  ┌──────────┐      ┌────────────┐
  │ Uneven   │      │ Review     │
  │ Load?    │      │ Issue      │
  └────┬─────┘      │ Details    │
       │            └─────┬──────┘
    ┌──┴──┐              │
    │     │          ┌───┴────┐
   YES   NO         │         │
    │     │       SIMPLE   COMPLEX
    │     │         │         │
    ▼     ▼         ▼         ▼
┌─────┐ ┌──┐   ┌──────┐ ┌─────────┐
│Move │ │OK│   │Fix   │ │Escalate │
│Case │ │  │   │Now   │ │to Admin  │
│Load │ │  │   │      │ │         │
└─────┘ └──┘   └──────┘ └─────────┘
    │    │         │         │
    └────┴─────────┴─────────┘
           │
           ▼
    ┌────────────────┐
    │ Monitor Outcome│
    │ & Follow Up    │
    └────────────────┘
```

---

## Decision Tree: "Should I Reassign This Case?"

```
              START: Tech is overloaded or case needs reassignment
                            │
                            ▼
                ┌──────────────────────────┐
                │ Why reassign?             │
                └────────┬─────────────────┘
                         │
    ┌────────┬──────────┬┴────────┬────────┐
    │        │          │         │        │
 RUSH    OVER-    SPECIALIST  ESCALATE  SWAP
  CASE   LOAD      NEEDED      TO ADMIN  LOAD
    │     │         │           │        │
    ▼     ▼         ▼           ▼        ▼
  FIND   FIND     FIND         ASK      FIND
 BEST   LEAST    EXPERT      ADMIN    EQUAL
 TECH   BUSY                          LEVEL
    │     │        │           │       │
    └─────┴────────┴───────────┴───────┘
           │
           ▼
    ┌────────────────────────┐
    │ Click "Reassign Case"  │
    │ Select New Technician  │
    │ Add Reason (optional)  │
    │ Confirm                │
    └────────────────────────┘
           │
           ▼
    ┌────────────────────────┐
    │ Technician Notified    │
    │ Case Reassigned        │
    │ Old Tech: Read-only    │
    │ New Tech: Full Access  │
    └────────────────────────┘
```

---

