# Delayed Email Notifications - Quick Start Guide

**Commit**: `d3947ed` - Implement delayed email notifications  
**Date**: January 16, 2026  
**Status**: ✅ COMPLETE & READY

---

## What's New

Members now receive **email notifications** when their cases are completed and released. The email delay is **tied to the case release delay** (0-24 hours).

---

## For Technicians: How It Works

### Completing a Case

1. Open case detail page
2. Click **"Mark as Completed"** button
3. Dialog shows:
   ```
   Completion Delay Options:
   - Immediately (default)
   - 1 Hour Delay
   - 2 Hours Delay
   - ... up to 24 Hours Delay
   ```
4. Select delay (admin's default is pre-selected)
5. Click **"Confirm Completion"**

**What happens**:
- Case marked as `status = 'completed'`
- Release scheduled for selected date/time (CST)
- **Email to member also scheduled for same date/time**
- Staff can see status on case detail page

### Monitoring Notifications

On case detail page, see **"Member Notification"** card:

```
✅ Member Notified
Email sent on Jan 16, 2026 at 2:30 PM
To: member@email.com

(or)

⏳ Notification Scheduled  
Will be sent on Jan 16, 2026
To: member@email.com
```

---

## For Admins: Configuration

### Access Settings

1. Go to **Settings** (gear icon in header)
2. Click **"Release Settings"** tab
3. Scroll to **"Member Email Notifications"** section

### Configure

**Enable Delayed Email Notifications** (toggle)
- ON = Send emails
- OFF = Don't send emails

**Default Email Delay** (dropdown)
- Default: `Immediately`
- Can be 0, 1, 2, 3, 4, 5, 6, 12, or 24 hours
- Technicians override this per case

**Enable Automated Email Sending** (toggle)
- ON = Cron job sends emails
- OFF = Manual sending only

**Info Box** explains:
- Emails sent on same date as case release
- Pulled from member profile
- Staff sees notification status on case detail
- (Future: WP Fusion integration)

---

## For DevOps: Setup

### Deploy Code

```bash
# From local machine
git push origin main

# On test server
cd /home/dev/advisor-portal-app
git pull origin main
source venv/bin/activate
python manage.py migrate
python manage.py check
```

### Test Command

```bash
# Dry-run (preview what would be sent)
python manage.py send_scheduled_emails --dry-run

# Send emails for cases due today
python manage.py send_scheduled_emails
```

### Add Cron Job

**On Linux/Mac**:
```bash
crontab -e

# Add these lines:
0 0 * * * cd /home/dev/advisor-portal-app && python manage.py release_scheduled_cases
15 1 * * * cd /home/dev/advisor-portal-app && python manage.py send_scheduled_emails
```

**On Windows**:
- Open Task Scheduler
- Create task to run `python manage.py send_scheduled_emails`
- Set to run daily at 1:15 AM

---

## Testing Checklist

- [ ] Deploy code to test server
- [ ] Run migrations: `python manage.py migrate`
- [ ] Django check passes: `python manage.py check`
- [ ] Complete case with 0 hour delay → member email should send immediately (test in logs)
- [ ] Complete case with 1+ hour delay → verify `scheduled_email_date` is set
- [ ] Wait for cron job to run → email sent
- [ ] Staff can see notification indicator on case detail page
- [ ] Admin can configure default delay in System Settings
- [ ] Admin can enable/disable email notifications

---

## Files Changed

**Created**:
- `cases/management/commands/send_scheduled_emails.py` - Email sending
- `cases/templates/emails/case_released_notification.txt` - Email template
- `cases/templates/emails/case_released_notification.html` - HTML email template

**Modified**:
- `cases/models.py` - Added email fields
- `core/models.py` - Added email settings
- `cases/views.py` - Updated case completion logic
- `cases/templates/cases/case_detail.html` - Added indicator
- `templates/core/system_settings.html` - Added UI

**Migrations**:
- `cases/migrations/0018_case_actual_email_sent_date_and_more.py`
- `core/migrations/0004_systemsettings_batch_email_enabled_and_more.py`

---

## Database Fields

### Case Model
```python
scheduled_email_date = DateField(null=True, blank=True)
actual_email_sent_date = DateTimeField(null=True, blank=True)
```

### SystemSettings Model
```python
enable_delayed_email_notifications = BooleanField(default=True)
default_email_delay_hours = IntegerField(0-24, default=0)
batch_email_enabled = BooleanField(default=True)
```

---

## Email Contents

Members receive HTML email with:
- Case ID & employee name
- Completion date & status
- Link to view case in portal
- Important release delay info

---

## Technical Details

- **Timezone**: All delays calculated in CST (America/Chicago)
- **Tied to Release**: Email date = Release date
- **Member Email**: From `case.member.email` (future: WP Fusion)
- **Batch Job**: Runs daily/hourly via cron
- **Staff Visibility**: Tech/admin/manager only

---

## Future: WP Fusion Integration

Currently pulls email from member profile.

To integrate with WP Fusion:
1. Add WP Fusion client library
2. Modify `send_scheduled_emails.py` to call WP Fusion API
3. Pull email from WP Fusion contact
4. Log email sends to WP Fusion

No database changes needed.

---

## Support

For issues:
- Check logs: `/var/log/advisor-portal/` or Django logs
- Run dry-run: `python manage.py send_scheduled_emails --dry-run`
- Verify cron: `crontab -l` (Linux) or Task Scheduler (Windows)
- Check settings: System Settings → Release Settings → Email Notifications

See `DELAYED_EMAIL_NOTIFICATION_IMPLEMENTATION.md` for full technical details.

---

**Status**: ✅ READY FOR DEPLOYMENT
