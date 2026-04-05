# Health Check — How to Run

Run this command anytime to get a full system diagnostic of the ProFeds Report Portal.

---

## From Your Local Machine (PowerShell)

Make sure you're in the project folder:
```
cd C:\Users\ProFed\workspace\advisor-portal-app
```

### Run on PROD
```
ssh dev@104.248.126.74 "cd /var/www/advisor-portal && venv/bin/python manage.py health_check"
```

### Run on TEST
```
ssh dev@157.245.141.42 "cd /home/dev/advisor-portal-app && venv/bin/python manage.py health_check"
```

### Run Locally
```
python manage.py health_check
```

---

## What It Checks

- **Deployment** — Current git commit and when it was deployed
- **Database** — Connection status, engine, name
- **Migrations** — Any unapplied database migrations
- **Users** — Counts by role (members, techs, managers, admins), workshop codes
- **Delegates** — Total assignments, unique delegates, alert settings
- **Cases** — Counts by status, rush cases, unassigned cases
- **Documents & Reports** — File counts
- **System Settings** — Email toggles, feedback alerts, last update
- **Notifications & Messaging** — Staff notifications, conversations
- **Portal Feedback** — Total submissions, most recent
- **Audit Trail** — Total entries, last 24 hours activity
- **Storage** — File counts and disk usage

---

## Recommended Schedule

| When | What to Check |
|------|---------------|
| **Morning of go-live** | Full health check on PROD |
| **After first hour** | Run again — look for new audit entries and case activity |
| **End of each day (Days 1–3)** | Full health check — compare user/case/delegate counts |
| **If something seems wrong** | Run immediately — check for migration warnings or DB errors |

---

## Quick Checks (Without Full Report)

### Is PROD running?
```
ssh dev@104.248.126.74 "echo 'ProFeds2025Prod!' | sudo -S systemctl is-active gunicorn 2>/dev/null; echo 'ProFeds2025Prod!' | sudo -S systemctl is-active nginx 2>/dev/null"
```
Expected output: `active` twice.

### Restart PROD if needed
```
ssh dev@104.248.126.74 "echo 'ProFeds2025Prod!' | sudo -S systemctl restart gunicorn"
```
