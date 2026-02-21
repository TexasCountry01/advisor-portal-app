# Email Notification Testing Plan

**Date:** February 20, 2026  
**Status:** All emails currently DISABLED on both servers

---

## Current Status: Emails Are Safe

- **PROD** (`reports.profeds.com`): `email_notifications_enabled = False` in database. No SMTP configured in `.env` — falls back to console backend (prints to stdout, never leaves the server).
- **TEST** (`test-reports.profeds.com`): `email_notifications_enabled = False` in database. Live SMTP configured (`smtp.gmail.com` via `reports@profeds.com`) — emails *would* go out if the toggle were flipped.
- **No cron jobs installed** on either server — the `release_scheduled_cases` and `send_scheduled_emails` management commands are not running.

---

## Email Inventory

### Active Emails (wired up and functional)

| # | Template | Recipient | Trigger | Checks Toggle? |
|---|----------|-----------|---------|----------------|
| 1 | `case_on_hold.html` / `.txt` | Member | Tech puts case on hold | ✅ Yes |
| 2 | `tech_comment_notification.html` / `.txt` | Member | Tech posts a chat message | ✅ Yes |
| 3 | `case_completed.html` / `.txt` | Member | Case is released to member (5 trigger points) | ✅ Yes |
| 4 | `case_accepted_member.html` | Member | Tech accepts a case | ✅ Yes |
| 5 | `case_rejection_notification.html` / `.txt` | Member | Case is rejected | ✅ Yes |
| 6 | `case_question_asked.html` | Member | Tech asks a question via case notes | ✅ Yes |
| 7 | `case_hold_resumed.html` | Member | Hold is removed and case resumes | ✅ Yes |
| 8 | `case_resubmitted_notification.html` | Tech | Member resubmits a case | ✅ Yes |
| 9 | `member_response_notification.html` | Tech | Member responds to a question | ✅ Yes |
| 10 | `case_approved_notification.html` | Tech (L1) | Quality reviewer approves case | ✅ Yes |
| 11 | `case_revisions_needed_notification.html` | Tech (L1) | Quality reviewer requests revisions | ✅ Yes |
| 12 | `case_corrections_notification.html` | Tech (L1) | Quality reviewer requests corrections | ✅ Yes |
| 13 | `case_released_notification.html` / `.txt` | Member | Cron job (`send_scheduled_emails`) | ⚠️ NO |

### Dead Code (templates exist but never called)

| Template | Issue |
|----------|-------|
| `new_case_assigned.html` | Helper function exists in `email_service.py`, imported in `views.py`, but never called |
| `modification_created_notification.html` | Helper function exists in `email_service.py`, imported in `views.py`, but never called |

### Case Completed Email — 5 Trigger Points

The completed email fires whenever `actual_release_date` is set (case becomes available to member):

| # | Trigger | Location |
|---|---------|----------|
| 1 | Level 2/3 tech completes case with "Release Now" | `mark_case_complete` in `views.py` |
| 2 | Quality reviewer approves with "Release Now" | `approve_case_review` in `views.py` |
| 3 | Manual early release of a scheduled case | `release_case_immediately` in `views.py` |
| 4 | Change release date → Release Now | `change_release_date` in `views.py` |
| 5 | Daily cron job releases scheduled cases | `release_scheduled_cases.py` mgmt command |

---

## Testing Plan

### Phase 1 — Visual Template Review (Local, No Server Needed)

Render each template locally and open in a browser to verify formatting:

```python
python manage.py shell
```

```python
from django.template.loader import render_to_string

ctx = {
    'member_first_name': 'John',
    'employee_name': 'Jane Doe',
    'case_detail_url': 'https://test-reports.profeds.com/cases/1/',
    'logo_url': 'https://test-reports.profeds.com/static/images/RevisedCoverPageLogo.png',
    'hold_reason': 'We need a copy of your SF-50.',
}

for tmpl in ['case_on_hold', 'tech_comment_notification', 'case_completed']:
    html = render_to_string(f'emails/{tmpl}.html', ctx)
    with open(f'{tmpl}_preview.html', 'w') as f:
        f.write(html)
    print(f'Saved {tmpl}_preview.html')
```

Open each `_preview.html` in a browser. Verify:
- FedImpact logo renders in the header
- Navy border under the header
- Body text is Arial 15px, proper spacing
- "CLICK HERE" CTA button is navy, centered, clickable
- Footer has copyright and "do not reply" text
- Overall width is 600px, centered on gray background

### Phase 2 — Live Email Test on TEST Server

1. **Create a test member account** with **your own email address** (or change an existing test member's email to yours).

2. **Flip the toggle ON** on TEST only:
   - Admin Dashboard → System Settings → Email Notifications → **ON**

3. **Trigger each email one at a time** through the UI:

| Email | How to Trigger |
|-------|---------------|
| **Case On Hold** | As a tech, put a test case on hold with a reason |
| **Tech Comment** | As a tech, post a chat message on a member's case |
| **Case Completed (immediate)** | As a Level 2/3 tech, complete a case with "Release Now" |
| **Case Completed (via QR approval)** | As Level 1 tech, complete a case → as Level 2+, approve the quality review with "Release Now" |
| **Case Completed (manual release)** | Complete a case with a future scheduled date, then click "Release Now" on the case detail page |
| **Case Accepted** | As a tech, accept a new case |
| **Case Rejected** | As a tech, reject a case |
| **Hold Resumed** | Put a case on hold, then resume it |

4. **Verify each email** arrives in your inbox:
   - Subject line matches the expected format
   - Greeting uses the member's first name
   - Employee name is correct
   - "CLICK HERE" button links to the correct case URL on the TEST domain
   - Logo renders properly
   - Footer is present
   - Plain-text fallback is readable (Gmail → "Show Original")

5. **Flip the toggle OFF** on TEST when done.

### Phase 3 — Cron Job Test on TEST

1. Create a test case and complete it with a **scheduled release date = today or yesterday**.
2. Flip email toggle **ON** on TEST.
3. SSH into TEST and run the cron command manually:

```bash
# Dry run first — shows what WOULD be released
python manage.py release_scheduled_cases --dry-run

# Then run for real
python manage.py release_scheduled_cases
```

4. Verify:
   - The case's `actual_release_date` got set
   - You received the "COMPLETE" email in your inbox
   - The case now shows as released in the member dashboard

5. Flip toggle **OFF** on TEST.

### Phase 4 — Production Cutover

Once all templates are verified on TEST:

1. **Add SMTP config to PROD `.env`** file:

```
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=reports@profeds.com
EMAIL_HOST_PASSWORD=rnnscdlqxtcfjwrj
DEFAULT_FROM_EMAIL=reports@profeds.com
```

2. **Restart gunicorn** on PROD:

```bash
pgrep -f 'gunicorn.*config' | head -1 | xargs kill -HUP
```

3. **Install cron job** on PROD (for scheduled case releases):

```bash
crontab -e
# Add this line:
0 0 * * * cd /var/www/advisor-portal && source venv/bin/activate && python manage.py release_scheduled_cases >> /var/log/release_cases.log 2>&1
```

4. **Flip toggle ON** in PROD Admin Dashboard → System Settings when ready to go live.

---

## Known Issues to Fix Before Go-Live

| Issue | Severity | Detail |
|-------|----------|--------|
| `send_scheduled_emails` skips toggle | **Medium** | The `send_scheduled_emails` cron command sends `case_released_notification` emails without checking `should_send_emails()`. Should add the check, or do not install this cron job. |
| Missing template `case_accepted.html` | **Low** | `views.py` line 1034 renders `emails/case_accepted.html` (tech-to-tech notification when a case is assigned to someone else) but this template file does not exist. Would throw `TemplateDoesNotExist` if triggered. |
| Duplicate email risk for scheduled releases | **Medium** | Both `send_scheduled_emails` (sends `case_released_notification`) and `release_scheduled_cases` (sends `case_completed`) could fire on the same case if both cron jobs are installed. The new `case_completed` email replaces the purpose of the old `case_released_notification`. **Only install `release_scheduled_cases` — do NOT install `send_scheduled_emails`.** |
| Dead code cleanup | **Low** | `send_new_case_assigned_email()` and `send_modification_created_email()` are imported but never called. Clean up when convenient. |
