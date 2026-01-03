# Production MySQL Database Setup Guide
**Advisor Portal Application**
**Date Created:** January 3, 2026
**Author:** Setup Documentation

---

## Overview

This document outlines the complete process for setting up a **MySQL database on the Advisor Portal production server**. This process was validated on the TEST server and should be followed exactly for PROD deployment.

**Key Requirements:**
- ✅ NO SQLite in production
- ✅ DigitalOcean Managed MySQL database cluster
- ✅ Secure remote database access
- ✅ Proper Django configuration
- ✅ Data migration/initialization

---

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Step 1: Create DigitalOcean MySQL Database](#step-1-create-digitalocean-mysql-database)
3. [Step 2: Configure Database Firewall](#step-2-configure-database-firewall)
4. [Step 3: Update Production Server .env](#step-3-update-production-server-env)
5. [Step 4: Configure Django Settings](#step-4-configure-django-settings)
6. [Step 5: Run Django Migrations](#step-5-run-django-migrations)
7. [Step 6: Load Data](#step-6-load-data)
8. [Step 7: Restart Application Server](#step-7-restart-application-server)
9. [Step 8: Verification](#step-8-verification)
10. [Troubleshooting](#troubleshooting)

---

## Prerequisites

Before starting, you need:
- ✅ DigitalOcean account with access to production database cluster
- ✅ Production server SSH access (e.g., `ssh dev@PROD_IP`)
- ✅ MySQL Workbench installed (optional, for visual verification)
- ✅ GitHub repo with latest code deployed to PROD server
- ✅ Test server setup completed (reference TEST configuration)

---

## Step 1: Create DigitalOcean MySQL Database

### 1a. In DigitalOcean Console:
1. Navigate to **Databases** section
2. Click **Create Database** or use existing cluster
3. Select **MySQL** as database engine
4. Create new database named **`advisor_portal`**
   ```sql
   CREATE DATABASE advisor_portal CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   ```

### 1b. Retrieve Connection Credentials

From the DigitalOcean "Connection parameters" tab, note:
- **Username:** `doadmin`
- **Password:** (copy from DigitalOcean - note: may contain special characters like `O` and `l`)
- **Host:** `advisor-portal-db-prod-do-user-XXXXXX-0.e.db.ondigitalocean.com` (exact hostname)
- **Port:** `25060`
- **Database:** `advisor_portal`
- **SSL Mode:** `REQUIRED`

**⚠️ IMPORTANT:** The password may look similar but is different from TEST. Copy exactly from DigitalOcean.

---

## Step 2: Configure Database Firewall

### 2a. Get Production Server IP

SSH into production server and get its IP:
```bash
ssh dev@PROD_IP
curl -s https://api.ipify.org
# Example output: 157.245.141.42
```

### 2b. Add Trusted Source in DigitalOcean

1. In DigitalOcean, go to **Databases** → **advisor-portal-db-prod**
2. Click **Trusted Sources** tab
3. Click **Add Trusted Sources**
4. Add production server IP:
   - **IP Address:** `<PROD_SERVER_IP>`
   - **Description:** `PROD App Server`
5. Click **Add Trusted Sources**
6. Wait 1-2 minutes for firewall rules to apply

### 2c. Test Connection

From production server, verify connection:
```bash
ssh dev@PROD_IP
mysql -h advisor-portal-db-prod-do-user-XXXXXX-0.e.db.ondigitalocean.com \
  -P 25060 \
  -u doadmin \
  -p'<PASSWORD>' \
  -e 'SELECT 1;'
```

**Expected output:** `1` or no error message

---

## Step 3: Update Production Server .env

SSH to production server and update `.env` file:

```bash
ssh dev@PROD_IP
cd /home/dev/advisor-portal-app
```

Update/create these environment variables in `.env`:

```env
# MySQL Database Configuration (Production)
DB_ENGINE=django.db.backends.mysql
DB_NAME=advisor_portal
DB_USER=doadmin
DB_PASSWORD=<EXACT_PASSWORD_FROM_DIGITALOCEAN>
DB_HOST=advisor-portal-db-prod-do-user-XXXXXX-0.e.db.ondigitalocean.com
DB_PORT=25060
```

**Verification:**
```bash
grep -E 'DB_' /home/dev/advisor-portal-app/.env
```

Should show all 6 DB_* variables.

---

## Step 4: Configure Django Settings

### 4a. Verify Local Django Settings

The `config/settings.py` should already have MySQL support. Verify it contains:

```python
if DB_ENGINE == 'django.db.backends.mysql':
    DATABASES = {
        'default': {
            'ENGINE': DB_ENGINE,
            'NAME': config('DB_NAME', default='advisor_portal'),
            'USER': config('DB_USER'),
            'PASSWORD': config('DB_PASSWORD'),
            'HOST': config('DB_HOST'),
            'PORT': config('DB_PORT', default='3306'),
            'OPTIONS': {
                'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
                'charset': 'utf8mb4',
            },
        }
    }
else:
    # SQLite fallback
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
```

**Note:** Settings.py was already updated during TEST setup. No changes needed if code is current.

### 4b. Push Code to GitHub

If settings.py was modified:
```bash
git add config/settings.py
git commit -m "Configure MySQL database for production"
git push origin main
```

---

## Step 5: Run Django Migrations

SSH to production server:

```bash
ssh dev@PROD_IP
cd /home/dev/advisor-portal-app

# Pull latest code
git pull origin main

# Run migrations
/home/dev/advisor-portal-app/venv/bin/python manage.py migrate --noinput
```

**Expected output:**
```
Operations to perform:
  Apply all migrations: accounts, admin, auth, cases, contenttypes, sessions
Running migrations:
  Applying contenttypes.0001_initial... OK
  Applying contenttypes.0002_remove_content_type_name... OK
  [... more migrations ...]
  Applying sessions.0001_initial... OK
```

**If you see errors:**
- Check database connectivity (Step 2)
- Verify credentials in .env (Step 3)
- Check for conflicting migrations (see Troubleshooting)

---

## Step 6: Load Data

### 6a. Export Data from TEST Server (if needed)

If you need to copy data from TEST to PROD:

```bash
# On TEST server
cd /home/dev/advisor-portal-app
/home/dev/advisor-portal-app/venv/bin/python manage.py dumpdata \
  accounts.User accounts.UserPreference accounts.AdvisorDelegate \
  cases.Case cases.CaseDocument cases.CaseNote cases.CaseReport \
  cases.FederalFactFinder \
  --indent 2 --output app_data_prod.json
```

### 6b. Transfer to PROD Server

```bash
# From local machine
scp app_data_prod.json dev@PROD_IP:/home/dev/advisor-portal-app/

# Or on PROD server, pull from TEST via SCP
```

### 6c. Load Data on PROD

```bash
ssh dev@PROD_IP
cd /home/dev/advisor-portal-app
/home/dev/advisor-portal-app/venv/bin/python manage.py loaddata app_data_prod.json
```

**Expected output:**
```
Installed 13 object(s) from 1 fixture(s)
```

**Alternative:** If starting fresh with no data:
```bash
# Just skip to Step 7, database is ready
```

---

## Step 7: Restart Application Server

### 7a. Restart Gunicorn

```bash
ssh dev@PROD_IP
sudo systemctl restart gunicorn

# Verify it's running
sudo systemctl status gunicorn | grep -E 'Active|running'
```

**Expected output:**
```
Active: active (running) since...
```

### 7b. Restart Nginx (if needed)

```bash
sudo systemctl restart nginx
```

---

## Step 8: Verification

### 8a. Test MySQL Connection from PROD Server

```bash
ssh dev@PROD_IP
mysql -h advisor-portal-db-prod-do-user-XXXXXX-0.e.db.ondigitalocean.com \
  -P 25060 \
  -u doadmin \
  -p'<PASSWORD>' \
  advisor_portal \
  -e 'SHOW TABLES;'
```

**Expected output:** List of ~20 Django tables (accounts_user, cases_case, etc.)

### 8b. Access Production Web Application

1. Navigate to your production domain (e.g., `https://reports.profeds.com`)
2. Try logging in with a test account
3. Verify case data loads correctly
4. Test case creation/editing functionality

### 8c. Verify in MySQL Workbench (Optional)

1. Create new connection in Workbench with PROD credentials
2. Connect to `advisor_portal` database
3. Expand **Tables** - should see all Django tables
4. Check `accounts_user` table has expected users
5. Check `cases_case` table has expected cases

---

## Troubleshooting

### Issue: "Access denied for user 'doadmin'"

**Causes:**
- Wrong password (check DigitalOcean console exactly)
- Wrong hostname
- IP not whitelisted in firewall

**Solution:**
1. Verify password copied exactly from DigitalOcean (note `O` vs `0`, `l` vs `1`)
2. Verify hostname matches DigitalOcean connection string
3. Verify PROD server IP is in Trusted Sources (wait 1-2 min after adding)
4. Test with: `mysql -h HOST -P 25060 -u doadmin -p'PASSWORD' -e 'SELECT 1;'`

### Issue: "Can't connect to server"

**Causes:**
- Network firewall blocking port 25060
- Production server IP not whitelisted
- DigitalOcean database cluster not responding

**Solution:**
1. Check firewall trusted sources in DigitalOcean console
2. Verify production server IP with `curl -s https://api.ipify.org`
3. Check DigitalOcean database cluster status (not destroyed/deleted)
4. Wait 2 minutes after adding IP to trusted sources

### Issue: "Conflicting migrations detected"

**Causes:**
- Multiple migration branches (0010 and 0011 both exist)

**Solution:**
```bash
/home/dev/advisor-portal-app/venv/bin/python manage.py makemigrations --merge --noinput
/home/dev/advisor-portal-app/venv/bin/python manage.py migrate --noinput
```

### Issue: "Integrity Error when loading data"

**Causes:**
- System tables already created by migrations
- Trying to load full dump including Django system data

**Solution:**
- Use app-data-only export (Step 6a)
- OR flush database first: `python manage.py flush --noinput`

### Issue: Application still using SQLite

**Check:**
1. Verify .env has `DB_ENGINE=django.db.backends.mysql`
2. Verify Django settings.py is current
3. Restart Gunicorn: `sudo systemctl restart gunicorn`
4. Check Django logs for database errors

---

## Configuration Reference

### TEST Server (for comparison)
- **Database Host:** `advisor-portal-db-test-do-user-6630088-0.e.db.ondigitalocean.com`
- **Port:** `25060`
- **Database:** `advisor_portal`
- **User:** `doadmin`
- **Firewall IP:** `157.245.141.42` (TEST server IP)

### PROD Server (to be configured)
- **Database Host:** `advisor-portal-db-prod-do-user-XXXXXX-0.e.db.ondigitalocean.com` (get exact name from DigitalOcean)
- **Port:** `25060`
- **Database:** `advisor_portal`
- **User:** `doadmin`
- **Firewall IP:** `XXX.XXX.XXX.XXX` (run `curl -s https://api.ipify.org` to find)

---

## Important Notes

1. **Password Security:** The password from DigitalOcean should be treated as sensitive. Don't commit it to GitHub - store in .env only.

2. **Backup:** Before running migrations on PROD, ensure you have a backup:
   - DigitalOcean automated backups enabled
   - Or manual backup: `mysqldump -h HOST -P 25060 -u doadmin -p advisor_portal > backup.sql`

3. **SSL:** DigitalOcean managed MySQL requires SSL connections. Django settings handle this automatically.

4. **Character Set:** Always use `utf8mb4` charset for proper Unicode support in Django.

5. **No SQLite:** Absolutely ensure `DB_ENGINE=django.db.backends.mysql` is set. SQLite is development-only.

6. **Testing:** After PROD setup, thoroughly test:
   - User login
   - Case creation/editing
   - Document uploads
   - All role-based features (member, technician, admin)

---

## Quick Checklist

- [ ] DigitalOcean PROD MySQL database created
- [ ] Database credentials retrieved
- [ ] PROD server IP whitelisted in firewall
- [ ] MySQL connection tested from PROD server
- [ ] `.env` updated with DB_ENGINE and credentials
- [ ] Latest code pulled to PROD server
- [ ] Django migrations run successfully
- [ ] Data loaded (if applicable)
- [ ] Gunicorn restarted
- [ ] Web app accessible and working
- [ ] MySQL Workbench connection verified (optional)
- [ ] Backup configured in DigitalOcean

---

## Support

If issues arise during PROD setup:
1. Reference this document step-by-step
2. Check troubleshooting section
3. Compare settings with TEST server (known good)
4. Review Django logs: `/var/log/gunicorn/error.log`

---

**Document Version:** 1.0
**Last Updated:** January 3, 2026
**Status:** Validated on TEST server
