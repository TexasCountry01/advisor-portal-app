# PRODUCTION Deployment - Pre-Deployment Checklist
**Date:** January 31, 2026  
**Status:** ✅ ALL CHECKS PASSED - READY FOR DEPLOYMENT

---

## ✅ Pre-Deployment Verification Completed

### 1. Server Access & Credentials ✅
- [x] PRODUCTION server IP: 104.248.126.74
- [x] SSH user: dev
- [x] SSH key-based authentication: CONFIGURED
- [x] Passwordless access: VERIFIED
- [x] Server is accessible without password prompt

### 2. Server Environment ✅
- [x] Python 3.11.2: INSTALLED ✓
- [x] pip 23.0.1: INSTALLED ✓
- [x] venv module: AVAILABLE ✓
- [x] Git 2.39.5: INSTALLED ✓
- [x] MariaDB 10.11.14: INSTALLED ✓
- [x] All 94 required Python packages: INSTALLED ✓

### 3. Project Structure ✅
- [x] Project directory: /var/www/advisor-portal (EXISTS)
- [x] Git repository: INITIALIZED
- [x] Virtual environment: CREATED (venv/)
- [x] Gunicorn installed: 21.2.0 ✓
- [x] Gunicorn socket path: READY (/var/www/advisor-portal/gunicorn.sock)

### 4. Database ✅
- [x] MySQL host: db-mysql-nyc1-61187-do-user-6630088-0.e.db.ondigitalocean.com
- [x] MySQL port: 25060
- [x] MySQL user: doadmin
- [x] MySQL password: VERIFIED
- [x] Database name: advisor_portal (EXISTS)
- [x] Database tables: 15 tables PRESENT
- [x] Connection test: SUCCESSFUL ✓

### 5. Critical Packages ✅
- [x] Django 5.0.7: INSTALLED ✓
- [x] gunicorn 21.2.0: INSTALLED ✓
- [x] mysqlclient 2.2.4: INSTALLED ✓
- [x] pytz 2023.3: INSTALLED ✓
- [x] python-decouple 3.8: INSTALLED ✓
- [x] boto3 1.42.14: INSTALLED ✓ (for Spaces storage)

### 6. Deployment Script ✅
- [x] deploy_to_production.ps1: CREATED
- [x] Target verification: CONFIGURED (104.248.126.74)
- [x] User confirmation: REQUIRED
- [x] Backup on deploy: ENABLED
- [x] Safety checks: INCLUDED

### 7. Configuration Files ✅
- [x] PRODUCTION_CONFIG_REFERENCE.md: CREATED
- [x] PRODUCTION_ENVIRONMENT_VERIFICATION.md: CREATED
- [x] PRODUCTION_DATABASE_VERIFICATION.md: CREATED
- [x] ENVIRONMENT_ISOLATION_STRATEGY.md: CREATED
- [x] deploy_to_production.ps1: CREATED

### 8. Environment Isolation ✅
- [x] LOCAL environment: PROTECTED (SQLite, no changes needed)
- [x] TEST environment: PROTECTED (157.245.141.42, isolated)
- [x] PRODUCTION environment: ISOLATED (104.248.126.74)
- [x] .env files: SEPARATE for each environment
- [x] Credentials: UNIQUE for each database

### 9. Latest Code ✅
- [x] Timezone fixes: DEPLOYED to TEST server
- [x] Workflow documentation: DEPLOYED to TEST server
- [x] Commits ready: b54b5a2, a1cb409 (available for PRODUCTION)
- [x] Git connectivity: VERIFIED
- [x] Latest commit available: 2a11934 + timezone fixes

### 10. Passwordless Deployment ✅
- [x] SSH key-based auth: CONFIGURED
- [x] TEST server (157.245.141.42): PASSWORDLESS ✓
- [x] PRODUCTION server (104.248.126.74): PASSWORDLESS ✓
- [x] Deployment scripts: NO PASSWORD NEEDED
- [x] Automated deployment: READY

---

## ✅ Deployment Readiness Summary

| Category | Status | Details |
|----------|--------|---------|
| Server Access | ✅ READY | Passwordless SSH configured |
| System Environment | ✅ READY | Python 3.11, Git, MySQL client |
| Project Structure | ✅ READY | Git repo, venv, Gunicorn |
| Database | ✅ READY | Connected, credentials verified, tables exist |
| Python Dependencies | ✅ READY | 94 packages installed |
| Deployment Script | ✅ READY | Safety checks, user confirmation, backup |
| Configuration | ✅ READY | All docs created, settings prepared |
| Code Ready | ✅ READY | Latest commits available for deployment |

**OVERALL STATUS: ✅ PRODUCTION SERVER READY FOR DEPLOYMENT**

---

## What Will Happen During Deployment

When you run `deploy_to_production.ps1`:

### Step 1: Verification (2 seconds)
- Confirms target is 104.248.126.74 (not TEST server)
- Requires you to type "DEPLOY TO PRODUCTION" to proceed

### Step 2: Backup (5 seconds)
- Creates backup of existing .env.production
- Stored as: `/var/www/advisor-portal/.env.production.backup_YYYYMMDD_HHMMSS`

### Step 3: Configuration (5 seconds)
- Creates new .env.production with production credentials
- Sets DEBUG=False, ALLOWED_HOSTS, database settings
- Sets S3/Spaces credentials for document storage

### Step 4: Git Pull (10-30 seconds)
- Pulls latest code from GitHub main branch
- Brings in timezone fixes and documentation updates
- About 13 files changed, 1,852 insertions

### Step 5: Migrations (10-30 seconds)
- Runs Django migrations on production database
- Creates/updates any new tables
- Initializes application schema

### Step 6: Gunicorn Restart (10 seconds)
- Stops existing Gunicorn processes
- Starts new Gunicorn with 3 workers
- Binds to Unix socket: /var/www/advisor-portal/gunicorn.sock

### Total Time: ~1-2 minutes

---

## After Deployment

### Immediate Verification (will be automated)
1. Check Gunicorn processes running (3 workers)
2. Verify HTTP 200 response from server
3. Test database connectivity
4. Check for errors in logs

### Manual Verification (if needed)
```bash
# SSH to PRODUCTION
ssh dev@104.248.126.74

# Check Gunicorn status
ps aux | grep gunicorn

# Check logs
tail -f /tmp/gunicorn.log

# Test app access
curl http://localhost/

# Check database
mysql -u doadmin -p -h db-mysql-nyc1-61187-do-user-6630088-0.e.db.ondigitalocean.com -P 25060 -e "USE advisor_portal; SELECT COUNT(*) as users FROM accounts_user;"
```

---

## Rollback Plan (if needed)

If deployment encounters issues:

```bash
# SSH to PRODUCTION server
ssh dev@104.248.126.74

# Restore backup
cp /var/www/advisor-portal/.env.production.backup_* /var/www/advisor-portal/.env.production

# Restart Gunicorn
pkill -f gunicorn
cd /var/www/advisor-portal && source venv/bin/activate
nohup gunicorn --workers 3 --bind unix:/var/www/advisor-portal/gunicorn.sock config.wsgi:application > /tmp/gunicorn.log 2>&1 &
```

---

## Ready to Deploy?

✅ **YES - ALL SYSTEMS GO**

You can now run:
```powershell
.\deploy_to_production.ps1
```

The script will:
1. Ask for confirmation (type "DEPLOY TO PRODUCTION")
2. Backup existing config
3. Deploy latest code and configuration
4. Start the application
5. Verify deployment success

**Recommendation:** Execute deployment when ready.

---

## Support

### Deployment Issues?
1. Check logs: `ssh dev@104.248.126.74 tail -f /tmp/gunicorn.log`
2. Review PRODUCTION_ENVIRONMENT_VERIFICATION.md
3. Review PRODUCTION_DATABASE_VERIFICATION.md
4. Check ENVIRONMENT_ISOLATION_STRATEGY.md

### Database Issues?
1. Review PRODUCTION_DATABASE_VERIFICATION.md
2. Verify credentials in deploy_to_production.ps1
3. Check remote database access

### General Issues?
1. SSH to PRODUCTION: `ssh dev@104.248.126.74`
2. Check project status: `cd /var/www/advisor-portal && git status`
3. Check migrations: `source venv/bin/activate && python manage.py showmigrations`

