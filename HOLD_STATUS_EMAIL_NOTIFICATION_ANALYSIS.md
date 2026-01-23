# Hold Status Email Notification & Member Dashboard Alerts
**Analysis Date:** January 23, 2026  
**Requested By:** User  
**Status:** Requirements Analysis & Options

---

## CURRENT STATE

### 1. **Put on Hold Functionality**
- ✅ **Implemented**: `put_case_on_hold()` view in `cases/views.py` (line 823)
- ✅ **Status Change**: Case status changes from `'accepted'` → `'hold'`
- ✅ **Ownership**: Case assignment (`assigned_to`) is **preserved** when placed on hold
- ✅ **Audit Logging**: Uses `hold_case()` service which logs action to `AuditLog`
- ✅ **Hold Reason**: Captured in `case.hold_reason` field
- ✅ **Button Location**: Case detail page in "Actions" card

### 2. **Member Document Upload for Hold Cases**
- ⚠️ **Partially Implemented**: Members **CAN** upload documents to hold cases
  - `upload_member_document_to_completed_case()` view (line 1775)
  - Allowed statuses: `['draft', 'submitted', 'completed', 'pending_review', 'accepted', 'resubmitted']`
  - **NOTE**: `'hold'` status is **NOT** in the allowed list
  - Document upload triggers `has_member_updates=True` flag

### 3. **Email Functionality**
- ✅ **Infrastructure Exists**: `send_scheduled_emails` management command exists
- ✅ **Django Mail Setup**: Uses `django.core.mail.send_mail()`
- ✅ **Current Use Case**: Sends emails for completed cases on scheduled release dates
- ⚠️ **Configuration**: EMAIL_HOST/SMTP settings configured via `.env` file
- ❌ **Hold Status Emails**: NO email sending for "put on hold" events currently

### 4. **Member Dashboard Notifications**
- ✅ **Exists**: Member dashboard has notification sections
- ✅ **Case Status Display**: Shows hold status (`On Hold` badge)
- ❌ **Hold-Specific Alerts**: No special notification when case placed on hold
- ⚠️ **Document Upload Feature**: Member can upload in case detail, but no dashboard notification

### 5. **Member Profile Fields**
- ✅ `case.member` → ForeignKey to User
- ✅ `case.member.email` → Available for sending emails
- ✅ Case detail accessible via URL pattern `cases:case_detail` with case.pk

---

## REQUIREMENTS BREAKDOWN

**What needs to happen when technician puts a case on hold:**

1. **Email to Member**
   - Send email to `case.member.email`
   - Email must include link to case detail page
   - Email should explain why case is on hold and what member needs to do
   - Should reference the hold reason provided by technician

2. **Member Dashboard Notification**
   - Show prominent notification/badge on member dashboard
   - Indicate case is on hold
   - Provide quick link to case detail to upload documents

3. **Document Upload Capability**
   - Members should be able to upload additional documents while case is on hold
   - Currently NOT allowed (hold status not in `allowed_statuses` list)
   - Need to enable this functionality

4. **Case Detail Context**
   - Case detail should show:
     - Why case is on hold (reason)
     - Call-to-action for member to upload documents
     - Document upload section

---

## CURRENT CODEBASE RELEVANT FILES

| File | Purpose | Status |
|------|---------|--------|
| `cases/views.py:823` | `put_case_on_hold()` | ✅ Implemented |
| `cases/services/case_audit_service.py:16` | `hold_case()` service | ✅ Implemented |
| `cases/management/commands/send_scheduled_emails.py` | Email sending command | ✅ Infrastructure |
| `cases/templates/cases/member_dashboard.html` | Member dashboard | ✅ Exists (no hold alerts) |
| `cases/templates/cases/case_detail.html` | Case detail view | ✅ Exists |
| `cases/models.py` | Case model with `hold_reason` field | ✅ Has field |
| `cases/views.py:1775` | `upload_member_document_to_completed_case()` | ⚠️ Restricts hold status |

---

## OPTIONS & IMPLEMENTATION PATHS

### **OPTION 1: Simple (2-3 hours)**
**Send Email Only - No Dashboard Changes**

**What's Included:**
1. Modify `put_case_on_hold()` to send email immediately after status change
2. Create simple email template with:
   - Case ID
   - Hold reason
   - Link to case detail
   - Instructions to upload documents

**Pros:**
- Quick implementation
- Minimal code changes
- Uses existing email infrastructure

**Cons:**
- No dashboard notification (member has to check email)
- No prominent alert on member dashboard
- Member might miss notification

**Changes Needed:**
1. ✏️ `cases/views.py:put_case_on_hold()` - Add email sending logic
2. ✨ Create `cases/templates/emails/case_on_hold.txt` and `.html`
3. ✏️ `cases/models.py` - Possibly add `email_sent_on_hold_date` field (optional)

---

### **OPTION 2: Standard (4-6 hours)**
**Email + Dashboard Badge + Enable Document Uploads for Hold Status**

**What's Included:**
1. Send email when case placed on hold
2. Add badge/alert on member dashboard for hold cases
3. Enable member document uploads while case is on hold
4. Update case detail to show hold status prominently

**Pros:**
- Comprehensive solution
- Members see notification in two places (email + dashboard)
- Can upload documents while on hold
- Professional, complete workflow

**Cons:**
- More code changes
- Requires migration if adding new fields

**Changes Needed:**
1. ✏️ `cases/views.py:put_case_on_hold()` - Add email sending
2. ✏️ `cases/views.py:1775` - Add `'hold'` to allowed statuses
3. ✨ Create email templates
4. ✏️ `cases/templates/cases/member_dashboard.html` - Add hold alert section
5. ✏️ `cases/templates/cases/case_detail.html` - Add hold context (reason, call-to-action)
6. 🗂️ Database migration if needed for tracking fields

---

### **OPTION 3: Premium (6-8 hours)**
**Email + Dashboard + Document Uploads + In-App Notification System**

**What's Included:**
- Everything in Option 2 PLUS:
1. In-app notification system (store notifications in database)
2. Notification center on member dashboard
3. Mark notifications as read/dismissed
4. Notification history
5. Optional: Email preferences (member can opt-in/out)

**Pros:**
- Most professional solution
- Complete audit trail of notifications
- Member control over notification preferences
- Scalable for future notifications

**Cons:**
- Significant development effort
- Requires new database model
- More complex frontend logic

**Changes Needed:**
1. ✨ New model: `CaseNotification` or `MemberNotification`
2. ✏️ All changes from Option 2
3. ✏️ `cases/views.py:put_case_on_hold()` - Create notification record + send email
4. ✏️ `cases/templates/cases/member_dashboard.html` - Notification center
5. ✨ New view for marking notifications as read
6. 🗂️ Database migration for new model

---

## MY RECOMMENDATION

**Go with Option 2 (Standard)**

**Reasoning:**
1. Balances functionality with implementation time
2. Addresses all stated requirements
3. Uses existing infrastructure (email, audit trail)
4. Provides good UX without over-engineering
5. Can be extended to Option 3 later if needed

---

## QUICK IMPLEMENTATION CHECKLIST FOR OPTION 2

### Step 1: Enable Document Uploads for Hold Cases
- [ ] Edit `cases/views.py` line 1794
- [ ] Add `'hold'` to `allowed_statuses` list
- [ ] Line becomes: `allowed_statuses = ['draft', 'submitted', 'completed', 'pending_review', 'accepted', 'resubmitted', 'hold']`

### Step 2: Create Email Sending Logic
- [ ] Modify `cases/views.py:put_case_on_hold()` 
- [ ] Add email sending after status is set to 'hold'
- [ ] Include case ID, hold reason, and case detail URL
- [ ] Generate URL using Django's `reverse()` with request.build_absolute_uri()

### Step 3: Create Email Templates
- [ ] Create `cases/templates/emails/case_on_hold.txt` (plain text)
- [ ] Create `cases/templates/emails/case_on_hold.html` (HTML version)
- [ ] Include:
  - Member name
  - Case ID
  - Hold reason
  - URL link to case detail
  - Instructions to upload documents

### Step 4: Update Member Dashboard
- [ ] Add section in `member_dashboard.html` showing "Cases on Hold"
- [ ] Show hold badge with case code
- [ ] Add link to upload documents

### Step 5: Update Case Detail
- [ ] Add hold reason display in `case_detail.html`
- [ ] Show "Documents Needed" call-to-action
- [ ] Ensure document upload form is visible for hold cases

### Step 6: Testing
- [ ] Put a test case on hold
- [ ] Verify email is sent to member
- [ ] Verify email contains case link
- [ ] Verify member can upload documents
- [ ] Verify dashboard shows notification

---

## ESTIMATED EFFORT

| Option | Time | Complexity | Scope |
|--------|------|-----------|-------|
| Option 1 | 2-3 hrs | Low | Email only |
| Option 2 | 4-6 hrs | Medium | Email + Dashboard + Uploads |
| Option 3 | 6-8 hrs | High | Email + Dashboard + Uploads + Notifications |

---

## WHICH SHOULD WE IMPLEMENT?

**Please let me know your preference:**
- [ ] Option 1 (Simple - Email Only)
- [ ] Option 2 (Standard - Email + Dashboard + Uploads)
- [ ] Option 3 (Premium - Full Notification System)
- [ ] Custom approach (please specify)

I'm ready to implement whichever option you prefer.
