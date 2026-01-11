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
            │ (w/ delay option)        │
            └────────┬─────────────────┘
                     │
                     ▼
            ┌──────────────────────────┐
            │ Select Release Timing:   │
            │ 0, 1, 2, 3, 4, or 5 hrs  │
            └────────┬─────────────────┘
                     │
         ┌───────────┴───────────┐
         │                       │
       0 hrs                   1-5 hrs
    (Immediate)              (Delayed)
         │                       │
         ▼                       ▼
    ┌────────────┐         ┌──────────────┐
    │ Released   │         │ Scheduled    │
    │ Immediately│         │ for Future   │
    │            │         │ Release      │
    └─────┬──────┘         └────┬─────────┘
          │                     │
          ▼                     ▼
    ┌──────────────┐      ┌───────────────┐
    │ Member Sees  │      │ Can Release   │
    │ Report Now   │      │ Immediately   │
    └──────────────┘      │ if Needed     │
                          └───────────────┘
                                 │
                                 ▼
                          ┌───────────────┐
                          │ Member Gets   │
                          │ Report on     │
                          │ Release Date  │
                          └───────────────┘
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
- ✓ Take ownership (become assigned tech)
- ✓ Read member's fact-finder submission
- ✗ Cannot complete case yet (need investigation)

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

### 5. **Completing Case**
- ✓ Mark as "Completed"
- ✓ Select release timing (0-5 hours)
- ✓ Set actual_release_date (if 0 hrs)
- ✓ Set scheduled_release_date (if 1-5 hrs)

### 6. **Completed Case - Awaiting Release**
- ✓ Can still add internal notes
- ✓ View scheduled release date
- ✓ Option: Release immediately (if authorized)

---

## Key Features for Technicians

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

### Case Completion Options

| Option | Delay | Description | Use Case |
|--------|-------|-------------|----------|
| **Immediate** | 0 hours | Member sees report now | Urgent cases, quick turnaround |
| **1 Hour** | CST | Member sees in 1 hour | Standard processing |
| **2 Hours** | CST | Member sees in 2 hours | Standard (default) |
| **3 Hours** | CST | Member sees in 3 hours | Quality review window |
| **4 Hours** | CST | Member sees in 4 hours | Extended review |
| **5 Hours** | CST | Member sees in 5 hours | Maximum delay window |

---

## Common Technician Workflows

### Workflow A: "Fast Track Case"
1. Dashboard shows new case (Submitted)
2. Click "Take Ownership"
3. Review fact-finder & documents
4. Quick investigation (1-2 hours)
5. Upload report
6. Mark Complete → Select "0 hours" (Immediate)
7. Report visible to member now

### Workflow B: "Standard Processing"
1. Accept case from queue
2. Full investigation (8-12 hours)
3. Multiple document requests from member
4. Upload comprehensive report
5. Mark Complete → Select "2 hours" (CST)
6. System releases at CST+2hrs
7. Member sees report on time

### Workflow C: "Complex Case with Escalation"
1. Accept complex case
2. Add internal notes (research phase)
3. Request additional documents
4. Perform detailed investigation
5. If needed: Request manager review
6. Upload final report
7. Mark Complete with review delay
8. Report released after quality check

### Workflow D: "Member Resubmitted - Needs Re-review"
1. See "Resubmitted" status
2. New documents from member (updated info)
3. Review what changed
4. Incorporate into report
5. Mark Complete → Select delay
6. Release at scheduled time

---

## Technician Tools & Features

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
