# ProFeds Report Portal — Go-Live Health Report
**Date:** April 5, 2026  
**Environment:** Production (reports.profeds.com)  
**Status:** ✅ All Systems Healthy

---

## System Status

| Check | Status |
|-------|--------|
| Application Server (Gunicorn) | ✅ Active |
| Web Server (Nginx) | ✅ Active |
| Database (MySQL) | ✅ Connected |
| SSL/HTTPS | ✅ Active |
| All Migrations Applied | ✅ Yes |
| Code Synced (LOCAL / TEST / PROD) | ✅ All on same commit |

---

## Users & Access

| Category | Count |
|----------|-------|
| **Total Active Users** | **176** |
| Members (Advisors) | 163 |
| Technicians | 7 |
| Managers | 2 |
| Administrators | 4 |
| Workshop Codes | 78 |

---

## Delegates

| Category | Count |
|----------|-------|
| **Total Delegate Assignments** | **135** |
| Unique Delegates | 86 |
| Members with Delegates | 72 |
| Email Alerts Enabled | 135 |
| Portal Alerts Enabled | 135 |

---

## Cases

| Category | Count |
|----------|-------|
| **Total Cases** | **168** |
| Submitted (awaiting assignment) | 3 |
| Accepted (in progress) | 26 |
| Completed | 135 |
| Cancelled | 4 |
| Rush Cases | 9 |
| Unassigned | 7 |
| Case Documents on File | 408 |
| Case Reports on File | 134 |

---

## Settings & Notifications

| Setting | Status |
|---------|--------|
| Email Notifications | ON |
| Scheduled Releases | ON |
| Batch Release | ON |
| Feedback Email Alerts | Not yet configured |

---

## Storage

| Location | Files | Size |
|----------|-------|------|
| Media (documents, reports, images) | 580 | 593.9 MB |

---

## Notes

- **211 audit log entries** recorded in the last 24 hours — delegates and user provisioning activity from yesterday is fully logged.
- **5 portal feedback submissions** received to date. Most recent on April 2, 2026.
- **7 unassigned cases** — these may need technician assignment before go-live.
- **Feedback Email Alerts** are available in System Settings → Feedback Alerts tab but have not been configured yet.
- The `health_check` command can be run anytime for an updated report:  
  `python manage.py health_check`
