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
              ┌────────────┼────────────┐
              │            │            │
              ▼            ▼            ▼
        ┌──────────┐  ┌──────────┐  ┌──────────────┐
        │ Submit   │  │ View     │  │ Edit My      │
        │ New Case │  │ Cases &  │  │ Profile      │
        │          │  │ Reports  │  │              │
        └────┬─────┘  └────┬─────┘  └────┬─────────┘
             │             │             │
             ▼             ▼             ▼
        [Start New]   [Review Existing] [Update Info]
             │             │             │
             └─────────────┴─────────────┘
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

### 4. **Needs Resubmission Status** (NEW)
- ⚠️ Case was **rejected** by technician/admin
- ✓ View rejection reason (why case wasn't accepted)
- ✓ View detailed notes about what's needed
- ✓ Email notification sent with requirements
- ✓ Resubmit case with updated documents/information
  - Update Federal Fact Finder if needed
  - Add missing supporting documents
  - Re-upload any corrected forms
  - Confirm all items from rejection notes are addressed
- ✓ Submit again for tech review
- Case re-enters review workflow


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

### 6. **Edit Your Profile** (NEW)
- ✓ Update your personal information
- ✓ Change contact preferences
- ✓ Update employment status
- ✓ View your delegate assignments (if any)
- ✓ See your quarterly credit allowance
- ✗ Cannot add/remove delegates (done by technician)
- ✗ Cannot change credit amounts (set by technician)

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
| **Edit Profile** | Dashboard → "My Profile" | Update your personal info |

---

## Member Dashboard Features

### Column Visibility Management (NEW)
**Customize your dashboard view to see only the case information you need:**

```
Dashboard Column Visibility:
├─ Click "Column Settings" button (gear icon)
├─ Toggle columns on/off:
│  ├─ Case ID (always shown)
│  ├─ Status
│  ├─ Created Date
│  ├─ Completion Date
│  ├─ Documents Count
│  ├─ Release Date
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
- ✓ Faster scanning of your cases
- ✓ Focus on what matters most to you
- ✓ Reduce screen clutter
- ✓ Personalized dashboard layout
- ✓ Settings remember your preferences

---

## Member Profile Management (NEW)

### Access Your Profile
Navigate to Dashboard → **"My Profile"** tab

### What You Can Edit
1. **Personal Information:**
   - First/Last name
   - Contact information
   - Mailing address
   - Phone number
   - Email address
   - Employment status

2. **View Your Delegate Information:**
   - See who has access to your account (delegates)
   - View effective dates for each delegate
   - See delegate type (full/limited access)
   - ⚠️ You cannot add/remove delegates - contact your benefits department
   - To remove delegate: Contact administrator

3. **Check Your Quarterly Credit Allowance:**
   - See your current credit balance
   - View quarterly limits
   - See credit usage history
   - View rollover settings
   - ⚠️ You cannot change credit amounts - set by benefits team

### Profile Update Process
1. Click **"Edit Profile"** button
2. Update any fields you need to change
3. Review all changes before saving
4. Click **"Save Changes"**
5. Confirmation message: "Profile updated successfully"
6. Changes take effect immediately
7. Your updated info available to technicians/administrators

### Who Can See Your Profile
- ✓ You can see/edit your own profile
- ✓ Your assigned technician can see it
- ✓ Managers can see it
- ✓ Administrators can see it
- ✗ Other members cannot see your profile
- ✗ Delegates can only see delegated information (limited access)

---

## Scenario: "I Need to Update My Contact Information"
1. Go to Member Dashboard
2. Click **"My Profile"** tab
3. Update fields:
   - Email: new.email@company.com
   - Phone: 555-0123
4. Click **"Save Changes"**
5. Confirmation: "Profile updated successfully"
6. Your new info available for communications
7. Next case correspondence will use new contact info

---

## Scenario: "Why does my profile show a delegate?"
- A delegate (family member, representative, etc.) has been assigned access to your account
- This is set up by your benefits department/technician
- You cannot remove this yourself
- Contact your technician or call benefits support to request removal
- You can view delegate effective dates on your profile

---

## Member Dashboard Features

### Column Visibility Management (NEW)
**Customize your dashboard view to see only the case information you need:**

```
Dashboard Column Visibility:
├─ Click "Column Settings" button (gear icon)
├─ Toggle columns on/off:
│  ├─ Case ID (always shown)
│  ├─ Status
│  ├─ Created Date
│  ├─ Completion Date
│  ├─ Documents Count
│  ├─ Release Date
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
- ✓ Faster scanning of your cases
- ✓ Focus on what matters most to you
- ✓ Reduce screen clutter
- ✓ Personalized dashboard layout
- ✓ Settings remember your preferences

---

## Member Entry Points

---

## Member Support Resources

**Need Help?**
- Dashboard has "Help" section with FAQ
- **Profile Questions:** Contact your benefits technician
- **Delegate Assigned:** Email your technician to request removal
- **Credit Balance:** Check "My Profile" → "Quarterly Credits"
- Email: member-support@company.com
- Phone: [support number]
- Hours: [business hours]

**Common Issues:**
- "I can't upload documents" → Check file size/format
- "Case not showing in dashboard" → Refresh page, try different browser
- "Can't see report even though release date passed" → Contact support
- "Forgot my password" → Use "Forgot Password" link on login
- "Need to update my address" → Go to "My Profile" → Edit → Save
- "How do I know who my delegate is?" → Check "My Profile" → Delegates section
- "Can I remove a delegate myself?" → No, contact administrator
