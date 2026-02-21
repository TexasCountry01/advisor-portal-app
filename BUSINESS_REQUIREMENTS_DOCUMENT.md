# Business Requirements Document (BRD)
## ProFeds Advisor Portal

**Version:** 2.0  
**Date:** February 21, 2026  
**System:** Advisor Portal — Django 5.0.7 / Python 3.11  
**Infrastructure:** DigitalOcean (TEST + PROD droplets)

---

## 1. System Purpose

The Advisor Portal is a case-management application for ProFeds, a federal employee benefits consulting firm. Financial advisors (members) submit benefits-analysis requests, which are processed by Benefits Technicians. The system manages the complete lifecycle of each case — from submission through investigation, quality review, and release of completed reports back to the member.

---

## 2. User Roles

| Role | Description | Count |
|------|-------------|-------|
| **Member** (Financial Advisor) | Submits cases, uploads documents, receives completed reports | Many |
| **Benefits Technician** | Accepts, investigates, and completes cases | Several |
| **Administrator** | Full system access, settings, user management | Few |
| **Manager** | Read-only analytics and audit access | Few |

### Technician Levels

| Level | Label | Capabilities |
|-------|-------|-------------|
| Level 1 | New Technician | Handle Tier 1 cases; completed work requires quality review by Level 2/3 |
| Level 2 | Technician | Handle Tier 1–2 cases; can review Level 1 work; direct completion |
| Level 3 | Senior Technician | Handle all tiers; can review Level 1 work; direct completion |

---

## 3. Permission Matrix

| Capability | Member | Technician | Administrator | Manager |
|-----------|--------|-----------|--------------|---------|
| View own cases | Yes | — | — | — |
| Submit new cases | Yes | — | — | — |
| Upload documents | Yes | — | — | — |
| Resubmit completed case | Yes | — | — | — |
| Request modification (60-day window) | Yes | — | — | — |
| Send/receive case messages | Yes | Yes (assigned) | Yes | — |
| Accept/reject cases | — | Yes | Yes | Yes |
| Assign/reassign technicians | — | Yes | Yes | Yes |
| Put on hold / resume | — | Yes (own) | Yes | Yes |
| Mark case completed | — | Yes (own) | Yes | Yes |
| Quality review (approve/revise/correct) | — | L2/L3 only | Yes | Yes |
| Admin take ownership | — | — | Yes | — |
| System settings | — | — | Yes | — |
| User management | — | — | Yes | — |
| Adjust credits | — | Yes | Yes | Yes |
| View all dashboards | — | — | Yes | — |
| Audit log access | — | — | Yes | Yes |
| Manager dashboard (read-only) | — | — | — | Yes |

---

## 4. Case Lifecycle

### 4.1 Statuses

| Status | Visible To Members | Description |
|--------|-------------------|-------------|
| Draft | Yes | Saved but not submitted |
| Submitted | Yes | Awaiting technician review |
| Resubmitted | Yes | Member sent updated documents after rejection |
| Accepted | Yes | Assigned to technician, under investigation |
| Hold | Yes | Paused — member notified with reason |
| Pending Review | No (shown as "Accepted") | Level 1 work awaiting Level 2/3 quality review |
| Needs Resubmission | Yes | Rejected — member must provide more info |
| Completed | Yes | Finished and released (or scheduled for release) |

### 4.2 Status Transitions

```
                            ┌──────────────────┐
                            │      Draft       │
                            └───────┬──────────┘
                                    │ Member submits
                                    ▼
                            ┌──────────────────┐
                ┌──────────►│    Submitted      │◄──────────┐
                │           └───────┬──────────┘            │
                │                   │                       │
                │        ┌──────────┴──────────┐            │
                │        ▼                     ▼            │
        ┌───────────────────┐        ┌──────────────────┐   │
        │ Needs Resubmission│        │     Accepted     │◄──┤
        │   (Rejection)     │        └───────┬──────────┘   │
        └───────┬───────────┘                │              │
                │ Member fixes               │              │
                ▼                    ┌───────┴───────┐      │
        ┌──────────────────┐         │               │      │
        │   Resubmitted    │──────►  │     Hold      │      │
        └──────────────────┘         │               │      │
                                     └───────┬───────┘      │
                                             │ Resume       │
                                             └──────────────┘
                                     │
                          ┌──────────┴──────────┐
                          │                     │
                  L1 completes            L2/L3 completes
                          │                     │
                          ▼                     ▼
                ┌──────────────────┐   ┌──────────────────┐
                │ Pending Review   │   │   Completed      │
                └───────┬──────────┘   └──────────────────┘
                        │
             ┌──────────┼──────────┐
             ▼          ▼          ▼
          Approve    Revisions   Correct
             │       Requested   & Complete
             │          │          │
             │          ▼          │
             │    Back to          │
             │    Accepted         │
             ▼                     ▼
        ┌──────────────────────────────┐
        │         Completed            │
        └──────────────────────────────┘
```

### 4.3 Key Business Rules

- **Tier vs. Level gating**: A technician should handle cases at or below their level (Tier 1 → Level 1+, Tier 2 → Level 2+, Tier 3 → Level 3). Admin override available.
- **Quality review**: Level 1 technicians cannot directly complete a case. Their work routes to `pending_review` for a Level 2/3 reviewer.
- **Hold preserves ownership**: Putting a case on hold saves the previous status. Resume restores it. The technician remains assigned.
- **60-day modification window**: Members can request a modification of a completed case within 60 days of release. This creates a new linked case (not an edit).
- **ProFeds error flag**: If a modification is requested due to a ProFeds error, the new case is automatically marked as rush with a 3-day due date.

---

## 5. Case Data Model

### 5.1 Core Case Fields

| Field | Description |
|-------|-------------|
| External Case ID | Unique identifier (generated by benefits-software API) |
| Workshop Code | Member's workshop identifier |
| Member | The financial advisor who owns the case |
| Created By | May differ from member if submitted by delegate |
| Employee First/Last Name | The federal employee being analyzed |
| Client Email | Contact email for the employee |
| Number of Reports Requested | Default: 1 |
| Urgency | Normal or Rush |
| Tier | Tier 1, 2, or 3 (set by technician at acceptance; hidden from members) |
| Credit Value | 0.0 – 3.0 in 0.5 increments (adjustable) |
| Special Notes | Free-text from member |
| Retirement Date Preference | Optional date |

### 5.2 Case Timing Fields

| Field | Purpose |
|-------|---------|
| Date Submitted | When member submitted the case |
| Date Accepted | When technician accepted |
| Date Due | Calculated deadline (hidden from members) |
| Date Scheduled | Internal scheduling (hidden from members) |
| Date Completed | When marked complete |
| Scheduled Release Date | Future date for delayed release (null = immediate) |
| Actual Release Date | When report became visible to member |
| Scheduled Email Date | Future date for email notification |
| Actual Email Sent Date | When email was actually sent |

### 5.3 Hold Fields

| Field | Purpose |
|-------|---------|
| Hold Reason | Required text explaining why the case is paused |
| Hold Start Date | When hold began |
| Hold End Date | When hold ended |
| Hold Duration (days) | Calculated duration |
| Status Before Hold | Saved for resume (submitted or accepted) |

### 5.4 Rejection Fields

| Field | Purpose |
|-------|---------|
| Rejection Reason | Predefined: Incomplete FFF, Missing Documents, Insufficient Data, Invalid Credit Request, Tier Mismatch, Other |
| Rejection Notes | Detailed explanation to member |
| Date Rejected / Rejected By | Tracking |

### 5.5 Quality Review Fields

| Field | Purpose |
|-------|---------|
| Reviewed By | Level 2/3 tech who reviewed |
| Reviewed At | When the review occurred |
| Review Notes | Reviewer's comments |
| Review Status | Approved, Revisions Requested, or Corrections Needed |

### 5.6 Report Notes

| Field | Purpose |
|-------|---------|
| Report Notes to Member | Rich text (TinyMCE HTML) — the finished analysis visible to the member after release |
| Report Notes (JSON) | Per-report status tracking array |

### 5.7 Resubmission & Modification Fields

| Field | Purpose |
|-------|---------|
| Is Resubmitted | Flag indicating member resubmitted |
| Resubmission Count | How many times resubmitted |
| Resubmission Date / Notes | When and why |
| Original Case | Link to parent case (for modifications) |
| Has Member Change Request | Flag for pending change requests |
| Has ProFeds Error | Flag indicating ProFeds-side error (triggers rush) |
| Error Modification Count | Number of error corrections |

---

## 6. Federal Fact Finder (FFF)

The system includes a comprehensive Federal Fact Finder form (OneToOne with Case) matching the official ProFeds FFF Rev 1-2025. It captures:

- Employee information (name, DOB, SSN, agency, grade/step)
- Spouse information
- Retirement system: CSRS, CSRS Offset, FERS, FERS Transfer
- Employee type: Regular, Postal, Military Tech, LEO, CBPO, Firefighter, ATC, Foreign Service
- Retirement type: Regular/Optional, Deferred, Disability
- Additional financial data for benefits analysis

The FFF can be submitted as structured form data or uploaded as a PDF. PDF extraction support exists for auto-populating fields.

---

## 7. Documents & Attachments

### Document Types

| Type | Uploaded By | Description |
|------|-----------|-------------|
| Fact Finder | Member | FFF form (PDF or structured data) |
| Supporting | Member | Birth certificates, SF-50s, pay stubs, etc. |
| Report | Technician | Completed analysis reports |
| Other | Either | Miscellaneous documents |

### Upload Rules

- Members can upload documents to cases in any active status (draft, submitted, accepted, hold, pending_review, completed, resubmitted)
- Technicians upload reports and technical documents
- All uploads are logged in the audit trail
- Documents track: filename, size, uploader, timestamp, and notes

---

## 8. Communication System

### 8.1 Case Messages (Two-Way)

Visible to both member and technician throughout the entire case lifecycle.

- Member posts message → unread notification created for assigned technician + email notification
- Technician posts message → unread notification created for member + in-app notification + email notification
- Unread message badges shown on dashboards per case
- Messages ordered chronologically

### 8.2 Internal Notes (Technician-Only)

- `is_internal = True` — never visible to members
- Used for investigation notes, internal coordination
- CRUD by technicians and administrators

### 8.3 Report Notes to Member

- Rich text (TinyMCE HTML editor) written by technician
- Visible to member only after case release
- Auto-save support
- PDF download available

---

## 9. Email Notification System

### 9.1 Master Toggle

All emails are gated by a single admin toggle: **Email Notifications Enabled** (in System Settings). When OFF, no emails are sent from any trigger.

### 9.2 Email Types

| # | Email | Recipient | Trigger |
|---|-------|-----------|---------|
| 1 | Case Accepted | Member | Technician accepts case |
| 2 | Case Rejected | Member | Technician rejects case (needs resubmission) |
| 3 | Case Put on Hold | Member | Technician puts case on hold |
| 4 | Case Resumed from Hold | Member | Technician resumes case |
| 5 | Question Asked | Member | Technician asks a question via case message |
| 6 | Case Completed | Member | Case completed and released |
| 7 | New Case Assigned | Technician | Case assigned to them |
| 8 | Member Response | Technician | Member uploads document or sends message |
| 9 | Case Resubmitted | Technician | Member resubmits after rejection |
| 10 | Modification Created | Technician | Member creates a modification request |

### 9.3 Quality Review Emails

| Email | Recipient | Trigger |
|-------|-----------|---------|
| Case Approved | L1 Technician | Reviewer approves their work |
| Revisions Needed | L1 Technician | Reviewer requests changes |
| Corrections Applied | L1 Technician | Reviewer corrects and completes |
| Tech Comment | Member | Technician posts a message on case |

### 9.4 Email Infrastructure

- **SMTP**: Gmail (`smtp.gmail.com:587` TLS)
- **From**: `reports@profeds.com`
- **Templates**: HTML + plain-text fallback for each email type
- **Audit**: Every sent email logged in the audit trail

---

## 10. Case Release & Scheduling

### 10.1 Release Options (at Completion)

| Option | Behavior |
|--------|----------|
| Release Now | Report immediately visible to member; email sent |
| Schedule Release | Report held until specified date/time; member sees nothing until then |

### 10.2 Admin Controls

| Setting | Purpose | Default |
|---------|---------|---------|
| Enable Scheduled Releases | Allow technicians to choose a future release date | ON |
| Batch Release Enabled | Allow cron job to process scheduled releases daily | ON |
| Batch Release Time | UTC time for daily batch processing | 09:00 |

When **Enable Scheduled Releases** is OFF, all completions force immediate release regardless of technician selection.

### 10.3 Cron Job: Batch Release

- **Command**: `python manage.py release_scheduled_cases`
- **Schedule**: Daily at noon UTC (`0 12 * * *`)
- **Logic**:
  1. Check `batch_release_enabled` — skip if OFF
  2. Find completed cases where `scheduled_release_date ≤ today` and `actual_release_date IS NULL`
  3. Set `actual_release_date = now()`
  4. Send completion email to member
  5. Log results
- **Supports** `--dry-run` flag for testing

### 10.4 Post-Release Actions

- Technician can **change release date** (move to a different future date)
- Technician can **release immediately** (override a scheduled date)
- Both actions are audited and trigger email if applicable

---

## 11. Quality Review Workflow

### Trigger

When a **Level 1** technician marks a case completed, it does NOT go to `completed`. Instead it transitions to `pending_review`.

### Reviewer Actions

| Action | Result | Next Status |
|--------|--------|-------------|
| **Approve** | Work accepted as-is; release scheduling applied | Completed |
| **Request Revisions** | Returned to Level 1 tech with feedback | Accepted (returned) |
| **Correct and Complete** | Reviewer fixes issues themselves and releases | Completed |

### Quality Review Data

- `CaseReviewHistory` model captures every review action (submitted, approved, revisions requested, corrections, resubmitted, completed)
- In-app staff notifications sent to Level 1 tech for each outcome
- Email notifications sent for all three outcomes
- Review queue dashboard available for reviewers

---

## 12. Credits System

### 12.1 Case Credits

Each case has a `credit_value` (0.0 – 3.0 in 0.5 increments). The credit is set at acceptance and can be adjusted at any time by technicians, administrators, or managers.

### 12.2 Quarterly Member Allowances

| Field | Description |
|-------|-------------|
| Member | The financial advisor |
| Fiscal Year | e.g. 2026 |
| Quarter | 1–4 |
| Allowed Credits | Total credits available for the quarter (default: 100) |
| Configured By | Administrator or manager who set the allowance |

Unique constraint: One allowance record per member per fiscal year per quarter.

### 12.3 Credit Audit Trail

The `CreditAuditLog` model tracks every credit value change:

| Field | Purpose |
|-------|---------|
| Credit Value Before / After | Old and new values |
| Adjustment Context | submission, acceptance, update, or completion |
| Adjustment Reason | Free-text explanation |
| Changed By / Changed At | Who and when |

---

## 13. Delegate System

### 13.1 Workshop Delegates (Active Model)

Delegates are assigned at the **workshop code** level, not per individual member. This means a delegate can submit cases for ANY member in that workshop.

| Field | Description |
|-------|-------------|
| Workshop Code | The workshop the delegate can act within |
| Delegate | The user granted access |
| Permission Level | `view`, `submit`, `edit`, `approve` |
| Granted By | Technician or admin who set this up |
| Is Active | Can be deactivated without deletion |

### 13.2 Delegate Capabilities

A delegate submitting a case is recorded as `created_by` (distinct from `member`), creating a clear audit trail that the case was submitted on behalf of the member by a delegate.

---

## 14. Dashboards

### 14.1 Member Dashboard

- Shows the member's own cases only
- Columns: Case Code, Employee Name, Reports, Urgency, Submitted Date, Due Date, Completed Date, Status, Credit Value, Actions
- Filtering: status (multi-select), urgency, search
- Sorting: all columns sortable, preferences saved per user
- Unread message count per case
- In-app notification center for hold/resume/release alerts
- "Cases on Hold" alert section

### 14.2 Technician Dashboard

- Shows ALL cases (not just assigned) — toggle for "My Cases" vs "All Cases"
- Columns: Case Code, Member, Employee Name, Reports, Urgency, Submitted, Due Date, Completed, Status, Assigned To, Tier, Actions
- Filtering: status, urgency, tier, assigned technician, search
- Statistics: total, submitted, accepted, resubmitted, pending review, needs revision, completed, rush

### 14.3 Administrator Dashboard

- Full system visibility — all cases except drafts
- Additional columns: Release Date, Date Scheduled, Reviewed By, On-Time/Late, Date Finalized, Notes
- Additional filters: member, technician, date range (today/week/month/custom)
- Statistics include: active members, active technicians, unassigned count, requiring review count

### 14.4 Manager Dashboard

- **Read-only** analytics view with same column and filter options as Administrator
- Cannot modify cases, settings, or users

### 14.5 Additional Views

| View | Purpose |
|------|---------|
| Technician Workbench | Focused view of assigned cases for the working technician |
| Review Queue | Cases in `pending_review` awaiting quality review |
| Case Detail | Full case view with documents, messages, notes, audit trail |
| Case Review & Accept | Acceptance workflow (checklist, tier assignment, technician assignment) |

---

## 15. System Settings (Admin Panel)

### 15.1 Settings Tabs

| Tab | Settings |
|-----|----------|
| **Credits** | Available credit values (comma-separated list) |
| **Case Defaults** | Default due days (1–90), rush threshold days |
| **Release Settings** | Enable scheduled releases, batch release enabled, batch release time, email notifications enabled, delayed email notifications, email delay hours |
| **API Configuration** | Benefits-software API URL, key, and enable toggle |
| **Notes Template** | HTML template pre-populated into technician notes on case acceptance |

### 15.2 Tab Persistence

The settings page preserves the active tab on save (via `?tab=` query parameter), so administrators land on the same tab after saving changes.

---

## 16. Audit Trail

### 16.1 Scope

All system activity is logged to a centralized `AuditLog` model. There are 58 tracked action types covering:

- Authentication (login, logout)
- Case lifecycle (created, submitted, accepted, assigned, reassigned, status changed, held, resumed, completed, rejected, cancelled, deleted)
- Documents (uploaded, viewed, downloaded, deleted)
- Notes (added, deleted)
- Quality review (submitted, approved, revisions, corrected)
- User management (created, updated, deleted, role changed)
- Credits (adjustments, quarterly resets, bulk resets)
- Email (sent, failed)
- System (settings updated, cron executed, exports)

### 16.2 Audit Log Data

Each entry captures:

| Field | Description |
|-------|-------------|
| User | Who performed the action |
| Action Type | One of 58 types |
| Timestamp | When it occurred (indexed for performance) |
| Description | Human-readable explanation |
| Case | Related case (if applicable) |
| Document | Related document (if applicable) |
| Related User | Second user involved (e.g., reassignment target) |
| Changes (JSON) | `{field: {before, after}}` — field-level diff |
| IP Address | Client IP |
| Metadata (JSON) | Additional context |

### 16.3 Audit Reports

| Report | Description |
|--------|-------------|
| Audit Log Browser | Searchable, filterable log of all activity |
| Case Audit Trail | Per-case activity history |
| Activity Summary | High-level activity metrics |
| User Activity | Per-user activity report |
| Case Change History | Field-level change tracking |
| Quality Review Audit | Review-specific audit trail |
| System Event Audit | System-level events (cron, settings, exports) |
| Credit Audit Trail | Credit value change history |
| CSV Export | Full audit log export |

---

## 17. User Interface

### 17.1 Accessibility

- User-level font size adjustment (6 sizes: 75%, 85%, 100%, 115%, 130%, 150%)
- Preference saved to user profile and applied globally

### 17.2 Navigation

- Sticky navigation bar (stays visible on scroll)
- Role-based menu items — each role sees only relevant links
- Unread message badge in navbar

### 17.3 Table Features

- All dashboard columns sortable
- Column visibility preferences saved per user per dashboard
- Sort preferences saved per user

### 17.4 Branding

- Copyright footer: "© ProFeds. All rights reserved."

---

## 18. Authentication & Authorization

### 18.1 Current Implementation

- Django session-based authentication
- Username + password login at `/login/`
- Role-based redirect after login:
  - Member → Member Dashboard
  - Technician → Technician Dashboard
  - Manager → Manager Dashboard
  - Administrator → Admin Dashboard
- `@login_required` decorator on all protected views
- Role-based access checks in views (e.g., only members can submit; only techs can accept)

### 18.2 Future: SSO via WordPress / WP Fusion

- Integration planned with WP Fusion for Single Sign-On
- WordPress site to serve as identity provider
- Placeholder integration points exist in codebase (see WP_FUSION_INTEGRATION_GUIDE.md)
- Additional sync points: subscription status, credit auto-calculation, delegate auto-management

---

## 19. Member Change Requests

Members can create change requests for active cases:

| Request Type | Description |
|-------------|-------------|
| Due Date Extension | Request more time before case completion |
| Cancellation | Request to cancel the case |
| Additional Info | Provide supplemental information |

Each request has a status (pending, approved, denied) and is processed by technicians or administrators.

---

## 20. API Integration (Placeholder)

The system includes fields and settings for integration with ProFeds' benefits-analysis software:

| Setting | Status |
|---------|--------|
| Benefits Software API URL | Placeholder (not yet configured) |
| Benefits Software API Key | Placeholder (not yet configured) |
| API Enabled Toggle | OFF by default |
| Case `external_case_id` | Ready to receive API-generated case IDs |
| Case `api_sync_status` | Tracks sync state (pending, synced, failed) |
| `APICallLog` model | Ready to log all API calls |

---

## 21. Infrastructure

### 21.1 Environments

| Environment | Server | Path | URL |
|-------------|--------|------|-----|
| TEST | 157.245.141.42 | /home/dev/advisor-portal-app | https://test-reports.profeds.com |
| PRODUCTION | 104.248.126.74 | /var/www/advisor-portal | https://reports.profeds.com |

### 21.2 Stack

| Component | Technology |
|-----------|-----------|
| Framework | Django 5.0.7 |
| Language | Python 3.11.2 |
| Database | SQLite (db.sqlite3) |
| Web Server | Gunicorn + Nginx |
| Hosting | DigitalOcean Droplets |
| SMTP | Gmail (reports@profeds.com) |
| Rich Text | TinyMCE |
| CSS Framework | Bootstrap 5 |

### 21.3 Cron Jobs

| Job | Schedule | Command |
|-----|----------|---------|
| Batch Release | Daily 12:00 UTC | `python manage.py release_scheduled_cases` |

---

## 22. Deployment Process

- Code deployed via Git push to both servers
- Gunicorn restarted via `sudo systemctl restart gunicorn`
- Migrations run via `python manage.py migrate`
- Static files collected via `python manage.py collectstatic --noinput`
- Deployment scripts available: `deploy_to_test_server.ps1`, `deploy_to_production.ps1`

---

## Document History

| Version | Date | Description |
|---------|------|-------------|
| 1.0 | January 2026 | Initial technician workflow documentation |
| 2.0 | February 21, 2026 | Complete BRD reflecting current system state |
