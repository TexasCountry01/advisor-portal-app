# Member Workflow & Decision Tree

## Role Overview
**Members** are employees who submit cases for benefits verification and receive completed reports. Their workflow is straightforward and primarily involves case submission and review.

---

## Member Workflow Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     MEMBER WORKFLOW                             │
└─────────────────────────────────────────────────────────────────┘

                          START
                            │
                            ▼
                  ┌─────────────────────┐
                  │ Access Member       │
                  │ Dashboard           │
                  └────────┬────────────┘
                           │
                           ▼
                  ┌─────────────────────┐
                  │ Want to Submit      │
                  │ New Case?           │
                  └────────┬────────────┘
                           │
              ┌────────────┴────────────┐
              │                         │
             YES                       NO
              │                         │
              ▼                         ▼
    ┌─────────────────────┐   ┌─────────────────────┐
    │ Click "Submit New   │   │ View Existing Cases │
    │ Case" Button        │   │ & Reports           │
    └────────┬────────────┘   └────────┬────────────┘
             │                         │
             ▼                         ▼
    ┌─────────────────────┐   ┌─────────────────────┐
    │ Fill Case Form      │   │ Select Case to View │
    │ (Required Fields)   │   │ Details             │
    └────────┬────────────┘   └────────┬────────────┘
             │                         │
             ▼                         ▼
    ┌─────────────────────┐   ┌─────────────────────┐
    │ Upload Documents    │   │ Case Completed?     │
    │ (Fact Finder,       │   │                     │
    │  Supporting Docs)   │   └────────┬────────────┘
    └────────┬────────────┘            │
             │                ┌────────┴────────┐
             ▼                │                 │
    ┌─────────────────────┐  YES               NO
    │ Submit Case         │   │                 │
    │                     │   │                 ▼
    └────────┬────────────┘   │      ┌──────────────────────┐
             │                │      │ Message: "In Progress"│
             ▼                │      │ Check back later      │
    ┌─────────────────────┐   │      └──────────────────────┘
    │ Confirmation Page   │   │
    │ (Doc Count, IDs)    │   │
    └────────┬────────────┘   │
             │                │
             ▼                │
    ┌─────────────────────┐   │
    │ Case in Dashboard   │   │
    │ (Status: Submitted) │   │
    └────────┬────────────┘   │
             │                │
             └────────┬───────┘
                      │
                      ▼
            ┌─────────────────────┐
            │ Scheduled for       │
            │ Release?            │
            └────────┬────────────┘
                     │
         ┌───────────┴───────────┐
         │                       │
        YES                      NO
         │                       │
         ▼                       ▼
  ┌────────────────┐   ┌──────────────────────┐
  │ Shows:         │   │ Shows:               │
  │ "Available on  │   │ "Completed - Check   │
  │ [DATE]"        │   │ back later or ask    │
  │ (Pending)      │   │ administrator"       │
  └────────────────┘   └──────────────────────┘
         │                       │
         ▼                       ▼
  ┌────────────────┐   ┌──────────────────────┐
  │ Release Date   │   │ Not Yet Available    │
  │ Arrives        │   │ to Member            │
  └────────┬───────┘   └──────────────────────┘
           │
           ▼
  ┌────────────────────────┐
  │ Reports & Docs Now     │
  │ Visible in Dashboard   │
  └────────┬───────────────┘
           │
           ▼
  ┌────────────────────────┐
  │ Download/Review        │
  │ Reports & Documents    │
  └────────┬───────────────┘
           │
           ▼
  ┌────────────────────────┐
  │ Can Add Comments/Notes │
  │ on Case                │
  └────────┬───────────────┘
           │
           ▼
          END
```

---

## Decision Tree: "Should I Submit a Case?"

```
                START: Do I need benefits verification?
                            │
                ┌───────────┴───────────┐
                │                       │
               NO                      YES
                │                       │
                ▼                       ▼
        WAIT/CONTACT        ┌──────────────────────┐
        SUPERVISOR          │ Do I have all       │
                            │ required documents? │
                            └──────┬───────────────┘
                                   │
                        ┌──────────┴──────────┐
                        │                     │
                       NO                    YES
                        │                     │
                        ▼                     ▼
                    GATHER DOCS         ┌─────────────────┐
                    (Fact Finder,       │ Is this URGENT? │
                     Pay Stubs, etc)    └────────┬────────┘
                        │                        │
                        └────────┬───────────────┘
                                 │
                        ┌────────┴────────┐
                        │                 │
                       NO               YES
                        │                 │
                        ▼                 ▼
                    ┌─────────┐    ┌──────────────┐
                    │ Standard│    │ Rushed Fee?  │
                    │ Timeline│    │ (Extra Cost) │
                    └────┬────┘    └────┬─────────┘
                         │             │
                         ▼             ▼
                    SUBMIT CASE   SUBMIT CASE
                    (Normal Cost) (W/ Rush Fee)
                         │             │
                         └──────┬──────┘
                                │
                                ▼
                        ┌────────────────┐
                        │ Wait for Tech  │
                        │ to Accept &    │
                        │ Complete       │
                        └────────────────┘
```

---

## Decision Tree: "Can I View My Case?"

```
              START: Want to view case details?
                            │
                            ▼
                ┌──────────────────────────┐
                │ Go to Member Dashboard   │
                │ Find Case in List        │
                └────────┬─────────────────┘
                         │
                         ▼
                ┌──────────────────────────┐
                │ Check Case Status        │
                └────────┬─────────────────┘
                         │
    ┌────────────────────┼────────────────────┐
    │                    │                    │
 DRAFT            SUBMITTED            COMPLETED
    │                    │                    │
    ▼                    ▼                    ▼
┌────────┐         ┌──────────┐        ┌──────────────┐
│ Can    │         │ Assigned │        │ Released?    │
│ Edit   │         │ to Tech  │        │              │
└────────┘         │ Status   │        └────┬─────────┘
    │              │ Visible  │             │
    │              │ Only     │    ┌────────┴────────┐
    │              │ to You   │    │                 │
    │              └──────────┘    │                 │
    │                              │                │
    │                              ▼                ▼
    │                          ┌────────┐    ┌──────────┐
    │                          │ In     │    │ Available│
    │                          │ Progress│   │ Now!     │
    │                          │ Msg    │    │          │
    │                          └────────┘    └──────────┘
    │                              │              │
    │                              ▼              ▼
    │                          ┌────────┐    ┌───────────┐
    │                          │ Check  │    │ Download  │
    │                          │ Release│    │ Reports & │
    │                          │ Date   │    │ Documents │
    │                          └────────┘    └───────────┘
    │
    ▼
┌──────────────────┐
│ You can also     │
│ add comments to  │
│ the case         │
└──────────────────┘
```

---

## Key User Actions by Status

### 1. **Draft Status**
- ✓ View case details
- ✓ Edit all form fields
- ✓ Upload/change documents
- ✓ Add personal notes
- ✗ Cannot resubmit (need to submit fresh)
- ✗ Cannot see tech notes

### 2. **Submitted Status**
- ✓ View case details (limited)
- ✓ See status updates
- ✗ Cannot edit case details
- ✗ Cannot upload documents (until tech requests)
- ✓ Can see general timeline
- ✗ Cannot see reports yet

### 3. **Accepted/In Progress Status**
- ✓ View assigned technician
- ✓ See case progress updates
- ✓ Upload documents if tech requests
- ✓ Add comments/questions
- ✗ Cannot edit main case fields
- ✗ Cannot see final reports (not released yet)

### 4. **Completed Status - Pending Release**
- ✓ See "Available on [DATE]" message
- ✓ View case timeline
- ✓ Add comments
- ✗ Cannot see reports (not released yet)
- ✗ Cannot download documents (not released yet)
- ⏳ Must wait for release date

### 5. **Completed Status - Released**
- ✓ Download all reports
- ✓ Download supporting documents
- ✓ View complete case analysis
- ✓ Add comments/feedback
- ✓ Print for records
- ✓ Contact technician with questions
- ✓ **Email notification received** when case released to you
  - If released immediately: Get email right away
  - If scheduled release: Get email on release date
  - Email contains case link and key information

---

## Email Notification System

When a case is marked "Completed" by your technician, an **automatic email notification** is scheduled:

- **Immediate Release (0 hours)**: You receive email immediately
- **Scheduled Release (1-24 hours)**: You receive email on the scheduled release date
- **Email includes**: 
  - Case ID and employee name
  - Case completion date
  - Link to download reports
  - Instructions for accessing documents
  - Contact info for support

### Notification Card on Case Detail:
The staff team can see on the case detail page:
- ✅ "Member Notified on [DATE TIME]" - email was sent
- ⏳ "Notification Scheduled for [DATE]" - email waiting to send
- ⚠️ "No Notification Scheduled" - notification not enabled
- ℹ️ "Not Yet Completed" - case still being processed

---

## Common Member Scenarios

### Scenario A: "I need my benefits verified ASAP"
1. Go to "Submit New Case"
2. Select "Rushed" option (understand extra cost)
3. Upload all documents
4. Submit with rush fee
5. Case prioritized in queue
6. Tech accepts and completes faster

### Scenario B: "My case is still in progress, when will it be done?"
1. Go to Member Dashboard
2. Find your case
3. If status is "Submitted" or "Accepted": Check back later
4. If status is "Completed": Check for release date
5. If release date has passed: Reports should be visible
6. If release date is future: Wait for that date

### Scenario C: "My case was completed but I can't see the report"
1. Go to case detail
2. If status is "Completed": Check scheduled release date
3. If date hasn't arrived yet: Come back on that date
4. If date has passed but still no report: Contact administrator
5. If release date is NULL: Contact administrator to release immediately

### Scenario D: "I want to add more documents to my case"
1. Go to case detail
2. If status is "Accepted" or later: Look for upload button
3. If no button visible: Case may be completed - contact tech
4. Upload your documents
5. Confirm upload in dashboard

---

## Member Entry Points

| Entry Point | Path | Action |
|---|---|---|
| **Submit New Case** | Dashboard → "Submit New Case" | Create & submit new case |
| **View Cases** | Dashboard → Case List | Browse all your cases |
| **View Case Details** | Dashboard → Case → Click | See case status & details |
| **Download Reports** | Case Detail (if released) → Download | Get completed reports |
| **Add Comments** | Case Detail → Comments Section | Add notes/questions |
| **Edit Draft** | Case Detail (Draft only) → Edit | Modify draft case |

---

## Member Support Resources

**Need Help?**
- Dashboard has "Help" section with FAQ
- Email: member-support@company.com
- Phone: [support number]
- Hours: [business hours]

**Common Issues:**
- "I can't upload documents" → Check file size/format
- "Case not showing in dashboard" → Refresh page, try different browser
- "Can't see report even though release date passed" → Contact support
- "Forgot my password" → Use "Forgot Password" link on login
