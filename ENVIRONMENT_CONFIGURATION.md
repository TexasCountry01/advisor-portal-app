# Advisor Portal - Environment Configuration
**Last Updated:** February 1, 2026

---

## Overview

Advisor Portal is deployed on two separate DigitalOcean droplets (TEST and PROD), each with its own MySQL database and document storage.

---

## TEST ENVIRONMENT

### Server Infrastructure
- **Host:** `test-reports.profeds.com`
- **IP Address:** `157.245.141.42`
- **Provider:** DigitalOcean
- **SSH User:** `dev`
- **SSH Key:** Required (key-based authentication)

### Application Deployment
- **Path:** `/home/dev/advisor-portal-app`
- **Web Server:** Nginx (reverse proxy)
- **Application Server:** Gunicorn (3 workers)
- **Socket:** `/home/dev/advisor-portal-app/gunicorn.sock`
- **Python:** 3.11.2
- **Django:** 6.0

### Database - MySQL
- **Host:** `advisor-portal-db-test-do-user-6630088-0.e.db.ondigitalocean.com`
- **Port:** `25060`
- **Username:** `doadmin`
- **Password:** Stored in `.env` (see `.env.backup.test-server`)
- **Database Name:** `advisor_portal`
- **Engine:** Django ORM with MySQL backend

### Document Storage
- **Path:** `/home/dev/advisor-portal-app/media/`
- **Subdirectories:**
  - `/media/case_documents/` - Member-uploaded documents
  - `/media/case_reports/` - System-generated reports
- **Permissions:** User `dev` owned, writable by Nginx/Gunicorn
- **Backup:** Manual backups to local machine

### Nginx Configuration
- **File:** `/etc/nginx/sites-enabled/advisor-portal`
- **SSL:** Let's Encrypt certificate for `test-reports.profeds.com`
- **Static Files:** `/home/dev/advisor-portal-app/staticfiles/`
- **Proxy:** Gunicorn unix socket

### Deploy Script
- **File:** `deploy_to_test_server.ps1`
- **Purpose:** Automated deployment from GitHub
- **Workflow:**
  1. SSH into `157.245.141.42`
  2. Pull latest from `origin/main`
  3. Run Django migrations
  4. Restart Gunicorn

---

## PRODUCTION ENVIRONMENT

### Server Infrastructure
- **Host:** `reports.profeds.com`
- **IP Address:** `104.248.126.74`
- **Provider:** DigitalOcean
- **SSH User:** `dev`
- **SSH Key:** Required (key-based authentication)

### Application Deployment
- **Path:** `/var/www/advisor-portal`
- **Web Server:** Nginx (reverse proxy)
- **Application Server:** Gunicorn (3 workers)
- **Socket:** `/var/www/advisor-portal/gunicorn.sock`
- **Python:** 3.11.2
- **Django:** 6.0

### Database - MySQL
- **Host:** `db-mysql-nyc1-61187-do-user-6630088-0.e.db.ondigitalocean.com`
- **Port:** `25060`
- **Username:** `doadmin`
- **Password:** Stored in `.env` (separate from TEST)
- **Database Name:** `advisor_portal`
- **Engine:** Django ORM with MySQL backend
- **Region:** NYC1 (different from TEST)

### Document Storage
- **Path:** `/var/www/advisor-portal/media/`
- **Subdirectories:**
  - `/media/case_documents/` - Member-uploaded documents
  - `/media/case_reports/` - System-generated reports
- **Permissions:** User `dev` owned, writable by Nginx/Gunicorn
- **Backup:** Manual backups to local machine

### Nginx Configuration
- **File:** `/etc/nginx/sites-enabled/advisor-portal`
- **SSL:** Let's Encrypt certificate for `reports.profeds.com`
- **Static Files:** `/var/www/advisor-portal/staticfiles/`
- **Proxy:** Gunicorn unix socket

### Deploy Script
- **File:** `deploy_to_production.ps1`
- **Purpose:** Automated deployment from GitHub
- **Workflow:**
  1. SSH into `104.248.126.74`
  2. Pull latest from `origin/main`
  3. Run Django migrations
  4. Restart Gunicorn

---

## Comparison Table

| Component | TEST | PROD |
|-----------|------|------|
| **Host** | test-reports.profeds.com | reports.profeds.com |
| **IP** | 157.245.141.42 | 104.248.126.74 |
| **App Path** | /home/dev/advisor-portal-app | /var/www/advisor-portal |
| **Gunicorn Socket** | /home/dev/advisor-portal-app/gunicorn.sock | /var/www/advisor-portal/gunicorn.sock |
| **MySQL Host** | advisor-portal-db-test-do-user-6630088-0.e.db.ondigitalocean.com | db-mysql-nyc1-61187-do-user-6630088-0.e.db.ondigitalocean.com |
| **MySQL Port** | 25060 | 25060 |
| **Media Path** | /home/dev/advisor-portal-app/media/ | /var/www/advisor-portal/media/ |
| **Status** | Active - Latest Code | Active - Latest Code |
| **Current Commit** | 491a78b | 491a78b |
| **Users** | QA/Testing Only | Live Users (When Deployed) |

---

## DigitalOcean MySQL Instances

### TEST Database Instance
- **Name:** advisor-portal-db-test
- **Connection String:** `advisor-portal-db-test-do-user-6630088-0.e.db.ondigitalocean.com:25060`
- **User:** `doadmin`
- **Database:** `advisor_portal`
- **Purpose:** Testing deployed code
- **Backup:** DigitalOcean automated backups

### PRODUCTION Database Instance
- **Name:** db-mysql-nyc1-61187
- **Connection String:** `db-mysql-nyc1-61187-do-user-6630088-0.e.db.ondigitalocean.com:25060`
- **User:** `doadmin`
- **Database:** `advisor_portal`
- **Purpose:** Live application data
- **Backup:** DigitalOcean automated backups + manual backups

---

## Current Deployed Code

**Commit Hash:** `491a78b`
**Branch:** `main`
**Last Updated:** February 1, 2026, 23:56 UTC

### Key Features Deployed
- ✅ ProFeds error tracking system
- ✅ StaffNotification in-app alerts
- ✅ Error tracking report (`/reports/profeds-errors/`)
- ✅ Case detail page enhancements
- ✅ All UI refinements from today's work

### Database Migrations Applied
- ✅ `cases.0032_case_error_modification_count_case_has_profeds_error`
- ✅ `core.0009_staffnotification`

---

## Important Notes

### Security
⚠️ **CRITICAL:**
- Never commit passwords to GitHub
- Use SSH key-based authentication
- Store `.env` files securely on servers only
- Database passwords stored in server `.env` files

### Directory Structure Difference
- **TEST** uses `/home/dev/` path (dev server convention)
- **PROD** uses `/var/www/` path (production convention)
- Both have correct deploy scripts pointing to their actual locations
- Future standardization: Consider moving both to `/var/www/` with proper permissions

### Deployment Process
1. **Local:** Make changes, commit to GitHub, push to `origin/main`
2. **TEST:** Run `deploy_to_test_server.ps1` to pull and test
3. **PROD:** Run `deploy_to_production.ps1` when ready for live deployment

### Database Management
- TEST and PROD use SEPARATE MySQL instances
- Each has its own data - **do NOT confuse them**
- Use `.env` files to specify which database
- Test database can be reset; PROD database is production data

### Document Storage
- Both environments store uploads in `/media/` subdirectory
- Accessible via web server (Nginx)
- Persists between deployments
- Should be included in backup procedures

---

## Troubleshooting

### TEST Server Issues
```bash
ssh dev@157.245.141.42
cd /home/dev/advisor-portal-app
source venv/bin/activate
python manage.py check          # Check Django setup
python manage.py migrate        # Apply migrations
ps aux | grep gunicorn          # Check Gunicorn status
tail -50 /tmp/gunicorn.log      # View Gunicorn log
```

### PROD Server Issues
```bash
ssh dev@104.248.126.74
cd /var/www/advisor-portal
source venv/bin/activate
python manage.py check          # Check Django setup
python manage.py migrate        # Apply migrations
ps aux | grep gunicorn          # Check Gunicorn status
```

### Database Connection Test
```bash
mysql -h [MYSQL_HOST] -u doadmin -p -D advisor_portal -e "SELECT VERSION();"
```

---

## Next Steps

1. **Directory Standardization** (Future)
   - Move PROD to `/home/dev/advisor-portal-app` OR
   - Move TEST to `/var/www/advisor-portal`
   - Requires sudo access or DigitalOcean support

2. **Automated Backups**
   - Implement database backup automation
   - Implement media folder backup automation

3. **Monitoring**
   - Set up error tracking/monitoring
   - Set up performance monitoring
   - Set up uptime monitoring

4. **SSL Certificate Renewal**
   - Monitor certificate expiration
   - Automate renewal if possible

---

**Document Version:** 1.0
**Created:** February 1, 2026
**Last Modified:** February 1, 2026
