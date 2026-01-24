# Member Workflow & Decision Tree

## Role Overview
**Members** submit cases and receive completed reports through the portal.

> **📊 AUDIT TRAIL TRACKING NOTE:**  
> All member activities are automatically tracked and logged in the audit trail system. Key activities include logins, case submissions, profile updates, and document uploads. Managers and administrators can access detailed activity reports at any time.

---

## Core Member Actions

Members interact with cases through three primary actions:

- **Submit New Case** - Create and submit a new case for processing
- **View Cases & Reports** - Track case status and download completed reports
- **Edit Profile** - Update personal information and view credit allowance

---

## Key User Actions by Status

### 1. **Draft Status**
- ✓ View case details
- ✓ Edit all form fields
- ✓ Upload/change documents
- ✓ Add personal notes
- ✗ Cannot resubmit (need to submit fresh)
- ✗ Cannot see tech notes

### 2. **Submitted Status - Collaboration Features**
- ✓ View case details (limited)
- ✓ See status updates
- ✓ Add new documents/information while case is being reviewed
- ✓ See when technician adds information
- ✓ Member update timestamps tracked
- ✓ Can see general timeline
- ✗ Cannot see reports yet

**What You Can Do:**
- Proactively add supporting documents or clarifications
- Technician sees notification when you add info
- Helps speed up case processing
- All updates tracked in audit trail

### 2B. **Accepted/In Progress Status**
- ✓ View assigned technician
- ✓ See case progress updates
- ✓ Upload documents if tech requests
- ✓ Add comments/questions
- ✗ Cannot edit main case fields
- ✗ Cannot see final reports (not released yet)

### 3A. **Hold Status** (NEW - Case Paused)
- ℹ️ Case has been **placed on hold** temporarily
- ✓ **Email notification received** - Technician explains hold reason and what's needed
- ✓ **In-app notification badge** - See notification bell on dashboard with hold alert
- ✓ View hold reason (e.g., "Waiting for Member Documents", "Awaiting Admin Decision")
- ✓ View expected resume date (if duration was set)
- ✓ Still see assigned technician name
- ✓ **Can upload/add documents** - Provide requested information while on hold
- ✓ Can add comments while on hold
- ✗ Case is not actively being worked on
- ✗ No progress updates until resumed
- **What this means:**
  - Your case is not forgotten - just paused temporarily
  - Technician may need: more documents, clarification, admin decision, etc.
  - You can provide missing info by uploading documents
  - Your case will resume when issue is resolved
  - Technician's ownership is preserved
  - Case will be completed when ready
  - You'll be notified when it resumes
- **📊 AUDIT TRACKING:**  
  - `case_held` - Logged when case put on hold with reason
  - `notification_created` - In-app notification created
  - `email_sent` - Email notification sent to member
  - `document_uploaded` - Logged for each document member uploads while on hold

### 4. **Needs Resubmission Status**
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
- **📊 AUDIT TRACKING:**  
  - `case_resubmitted` - Logged each time case is resubmitted
  - `document_uploaded` - Logged for each new document
  - Activity shows: Who resubmitted, when, and metadata about changes


### 5. **Completed Status - Pending Release**
- ✓ See "Available on [DATE]" message
- ✓ View case timeline
- ✓ Add comments
- ✗ Cannot see reports (not released yet)
- ✗ Cannot download documents (not released yet)
- ⏳ Must wait for release date

### 6. **Completed Status - Released**
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
- **📊 AUDIT TRACKING:**  
  - `case_status_changed` - Logged when case moves to released status
  - `email_notification_sent` - Logged when release email is sent
  - `document_downloaded` - Logged if reports are downloaded (optional)

### 7. **Edit Your Profile**
- ✓ Update your personal information
- ✓ Change contact preferences
- ✓ Update employment status
- ✓ See your quarterly credit allowance
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

| Entry Point           | Path                                 | Action                    |
| --------------------- | ------------------------------------ | ------------------------- |
| **Submit New Case**   | Dashboard → "Submit New Case"        | Create & submit new case  |
| **View Cases**        | Dashboard → Case List                | Browse all your cases     |
| **View Case Details** | Dashboard → Case → Click             | See case status & details |
| **Download Reports**  | Case Detail (if released) → Download | Get completed reports     |
| **Add Comments**      | Case Detail → Comments Section       | Add notes/questions       |
| **Edit Draft**        | Case Detail (Draft only) → Edit      | Modify draft case         |
| **Edit Profile**      | Dashboard → "My Profile"             | Update your personal info |

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

## Member Profile Management

### Access Your Profile
Navigate to Dashboard → **"My Profile"** tab or member dashboard

### What You Can Edit
1. **Personal Information:**
   - First/Last name
   - Contact information
   - Mailing address
   - Phone number
   - Email address
   - Employment status

2. **Delegate Information (View Only):**
   - You can see if a delegate has been assigned to your workshop code
   - Delegates are assigned by **Benefits Technicians** or **Administrators**
   - Delegates can submit cases on behalf of any member in your workshop
   - ⚠️ You cannot add/remove delegates yourself
   - To request a delegate be added or removed: Contact your Benefits Technician

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

## Scenario: "I see a delegate assigned to my workshop"
- A delegate has been assigned to your workshop code by your Benefits Technician
- This means they can submit cases on behalf of any member in your workshop
- This is normal and improves case processing efficiency
- You cannot manage this yourself - it's administered at the workshop level
- If you have concerns, contact your Benefits Technician directly

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

## Member Email Notifications

Members automatically receive email notifications at key points in their case journey. All emails are sent to their registered email address and tracked in the audit trail.

### Emails Members Receive

#### 1. **Case Accepted Email** ✅
- **When Sent:** Immediately when technician accepts a submitted case
- **Subject:** "Your Case [ID] - Your Case Has Been Accepted"
- **Content:** Confirmation that case received and accepted, tier level assigned, next steps
- **Action:** Member can log in to view case status and progress
- **Audit Trail:** Logged as email_sent action

#### 2. **Case On Hold Email** ✅
- **When Sent:** Immediately when technician puts case on hold
- **Subject:** "Action Required: Your Case [ID] Requires Additional Information"
- **Content:** Explanation of hold reason, documents/information needed, link to upload
- **Action:** Member should upload requested documents while case is on hold
- **Important:** Members CAN upload documents while case is on hold
- **Audit Trail:** Logged as email_sent with hold reason

#### 3. **Case Rejected - Needs Changes Email** ✅
- **When Sent:** Immediately when technician rejects case
- **Subject:** "Case [ID] - Additional Information Needed"
- **Content:** Rejection reason, detailed notes explaining what's needed, resubmission instructions
- **Action:** Member should resubmit case with corrected/additional information
- **Status Change:** Case status becomes 'needs_resubmission'
- **Audit Trail:** Logged with rejection details

#### 4. **Case Released - Available for Review Email** ✅
- **When Sent:** When scheduled release date arrives (can be delayed per system settings)
- **Subject:** "Your Case [ID] is Now Available"
- **Content:** Case is complete and ready for review, link to view completed case
- **Scheduling:** Can be delayed 0-24 hours based on system configuration
- **Delivery:** Via background job `python manage.py send_scheduled_emails`
- **Audit Trail:** Logged as email_notification_sent when delivered

### Email Scheduling & Configuration

- Release emails scheduled automatically when case marked completed
- Delay calculated from case completion + configured delay hours
- Batch job sends emails when date arrives (daily/hourly via cron)
- Email status tracking: Audit trail shows scheduled date, actual sent date, delivery status
- Failed emails logged with error details

---

## 📊 Audit Trail Activities (Member Role)

All member activities are automatically tracked in the system's audit trail. Here's what gets logged:

| Activity  | Audit Code | When Logged | Details Captured                   |
| --------- | ---------- | ----------- | ---------------------------------- |
| **Login** | `login`    | Immediate   | Session start, IP address, browser | \n | **Logout** | `logout` | Immediate | Session end, duration | \n | **Submit New Case** | `case_created` | On submission | Case ID, document count, urgency level | \n | **Upload Document** | `document_uploaded` | On upload | File name, size, case reference, document type | \n | **Resubmit Case** | `case_resubmitted` | On resubmission | Resubmission count, reason if provided, case changes | \n | **Update Profile** | `member_profile_updated` | On save | Which fields changed (name, email, phone), old/new values | \n | **Download Document** | `document_downloaded` | On download | File name, case reference, reason (if tracking enabled) | \n | **Add Comment** | `note_added` | On post | Comment text, case reference, timestamp | \n | **View Case** | `case_viewed` | Optional | Case ID, time viewed (if tracking enabled) | \n | **Receive Email** | `email_notification_sent` | When sent | Case link, release date, recipient email | \n\n### What This Means for You\n- **Transparency:** Your actions are tracked for compliance and dispute resolution\n- **Security:** Unusual activity (multiple logins, bulk downloads) can be identified\n- **Support:** If there's a discrepancy, staff can review your exact actions\n- **Privacy:** Only your authorized actions are logged; your actual documents aren't monitored\n\n### Access Your Activity\n- Members can view personal activity summary on \"My Dashboard\"\n- Managers/Admins can access detailed reports in the \"Audit Reports\" section\n- For detailed activity: Log in → Dashboard → Activity tab (if available)\n\n---\n\n## Member Support Resources\n\n**Need Help?**\n- Dashboard has \"Help\" section with FAQ |
- **Profile Questions:** Contact your benefits technician
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
- "Someone is submitting cases on my behalf" → That's your workshop delegate - contact technician with concerns


---

## Reference Diagrams

```
┌─────────────────────────────────────────────────────────────────┐
│                     MEMBER WORKFLOW                             │
└─────────────────────────────────────────────────────────────────┘

                          START
                            │
                            ▼
                  ┌─────────────────────┐Y
                  │ Access Member       │
                  │ Dashboard           │                  └────────┬────────────┘
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
             └─────────────┴─────────────┘
                           │
                           ▼
                  ┌─────────────────────┐
                  │ Select an Option    │
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
                    (Fact Finder,       │ Is this RUSH? │
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
    ┌────────┬──────────┬┴──────┬────────┬──────────┐
    │        │          │       │        │          │
 DRAFT  SUBMITTED   ACCEPTED  HOLD  COMPLETED  RESUBMIT
    │        │          │       │        │          │
    ▼        ▼          ▼       ▼        ▼          ▼
┌────┐  ┌──────┐   ┌───────┐┌──────┐┌──────────┐┌────────┐
│Edit│  │Viewing│  │In     ││Paused││Released?││Submit  │
│    │  │Only   │  │Prog   ││      ││         ││Updated │
└────┘  │       │  │(New)  ││(Hold)││         ││(Reject)│
    │   │Status:│  │Status:││      ││         ││Status  │
    │   │Pending││       ││(Hold)││         ││        │
    │   │       │  │       ││      ││         ││        │
    │   └───┬───┘  └────┬──┘└──┬──┘└────┬────┘└───┬────┘
    │       │           │      │        │         │
    │       ▼           ▼      ▼        ▼         ▼
    │   ┌────────┐ ┌────────┐┌────────┐┌───────┐┌────────┐
    │   │Checking│ │Check   ││See     ││Sched. ││Check  │
    │   │for     │ │for     ││Hold    ││Release││Notes  │
    │   │Release │ │Release ││Reason  ││Date   ││Apply  │
    │   │Date    │ │Date    ││Expected││       ││Changes│
    │   │(Pending││ (In    ││Resume  ││       ││       │
    │   │Release)││ Progres│ │Date    ││       ││       │
    │   │        │ │s)     ││        ││       ││       │
    │   └────────┘ └───┬───┘└────────┘└───────┘└────┬───┘
    │                  │                             │
    │                  ▼                             ▼
    │           ┌────────────┐              ┌──────────────┐
    │           │ Not Yet    │              │ Available    │
    │           │ Available  │              │ Now! Download│
    │           │ Check Back │              │ Reports      │
    │           │ Later      │              └──────────────┘
    │           └────────────┘                     │
    │                  │                           ▼
    │                  │                    ┌──────────────┐
    │                  │                    │ Download &   │
    │                  │                    │ Review       │
    │                  │                    └──────────────┘
    │
    ▼
┌──────────────────┐
│ You can also     │
│ add comments to  │
│ the case         │
└──────────────────┘
```

---
