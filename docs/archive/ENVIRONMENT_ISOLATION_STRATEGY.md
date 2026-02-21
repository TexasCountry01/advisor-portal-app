# PRODUCTION Environment Configuration Strategy
**Date:** January 31, 2026  
**Status:** Configuration strategy in progress

---

## ENVIRONMENT SEPARATION STRATEGY

To ensure LOCAL, TEST, and PRODUCTION environments remain completely isolated:

### File Structure
```
LOCAL DEVELOPMENT:
  └─ .env (current - SQLite, DEBUG=True, localhost)

TEST SERVER (Remote):
  └─ .env.test (on TEST server at 157.245.141.42)
  └─ Deployment script: deploy_to_test_server.ps1

PRODUCTION SERVER (Remote):
  └─ .env.production (on PROD server at 104.248.126.74)
  └─ Deployment script: deploy_to_production.ps1
```

### Key Principles

**1. LOCAL Development (.env - LOCAL MACHINE)**
- Uses SQLite database
- DEBUG=True
- ALLOWED_HOSTS=localhost,127.0.0.1
- Email backend = console output
- No external dependencies
- File stays in workspace (NOT uploaded to TEST/PROD)

**2. TEST Server (.env.test - REMOTE TEST MACHINE)**
- Uses MySQL at DigitalOcean
- DEBUG=False
- ALLOWED_HOSTS=test-reports.profeds.com,157.245.141.42
- MySQL credentials for TEST database
- Separate from LOCAL

**3. PRODUCTION Server (.env.production - REMOTE PROD MACHINE)**
- Uses MySQL at DigitalOcean (separate instance)
- DEBUG=False
- ALLOWED_HOSTS=production-domain.com,104.248.126.74
- MySQL credentials for PROD database (different user/password)
- Separate from LOCAL and TEST

---

## DEPLOYMENT SCRIPT SAFEGUARDS

### TEST Deployment Script (deploy_to_test_server.ps1)
```powershell
# Uses TEST server credentials
# Copies .env.test to TEST server
# Does NOT affect LOCAL or PRODUCTION
# Explicitly targets 157.245.141.42
```

### PRODUCTION Deployment Script (deploy_to_production.ps1)
```powershell
# Uses PRODUCTION server credentials
# Copies .env.production to PROD server
# Does NOT affect LOCAL or TEST
# Explicitly targets 104.248.126.74
# Includes safety checks to prevent accidental overwrite
```

---

## ISOLATION CHECKLIST

### LOCAL (.env)
- ✅ SQLite database (no external dependencies)
- ✅ Local credentials only
- ✅ Never copied to remote servers
- ✅ Stays in .gitignore
- ✅ DEBUG=True for development

### TEST SERVER (.env.test)
- ✅ Separate MySQL credentials from PROD
- ✅ TEST database name (advisor_portal)
- ✅ TEST server IP/hostname
- ✅ Stored only on TEST server (104.248.126.74)
- ✅ DEBUG=False for security
- ✅ Never overwritten by LOCAL deployments

### PRODUCTION (.env.production)
- ✅ Separate MySQL credentials from TEST
- ✅ PRODUCTION database name
- ✅ PRODUCTION server IP (104.248.126.74)
- ✅ Stored only on PROD server
- ✅ DEBUG=False for security
- ✅ Never overwritten by TEST or LOCAL
- ✅ Additional safety: backup before overwrite

---

## IMPLEMENTATION STEPS

### Step 1: Keep LOCAL .env Unchanged ✅
- Current LOCAL .env stays as-is
- No modifications needed
- Development continues normally

### Step 2: Create TEST Server .env.test
**File:** `.env.test` (stored on TEST server only, NOT in git repo)
- Location: `/home/dev/advisor-portal-app/.env.test` on TEST server
- Created via: `deploy_to_test_server.ps1` script
- Content: MySQL TEST credentials
- Never pulled/pushed to git

### Step 3: Create PRODUCTION .env.production
**File:** `.env.production` (stored on PROD server only, NOT in git repo)
- Location: `/var/www/advisor-portal/.env.production` on PROD server
- Created via: `deploy_to_production.ps1` script
- Content: MySQL PRODUCTION credentials
- Never pulled/pushed to git

### Step 4: Update Deployment Scripts
**TEST Deploy (already exists):**
- Confirms target is TEST server (157.245.141.42)
- Pushes .env.test with TEST credentials

**PRODUCTION Deploy (to be created):**
- Confirms target is PROD server (104.248.126.74)
- Pushes .env.production with PROD credentials
- Includes safety prompt to prevent mistakes

---

## DJANGO SETTINGS CONFIGURATION

### How Django Reads Environment Variables

```python
# config/settings.py (same for all environments)
from decouple import config

# Django reads from .env file automatically
DEBUG = config('DEBUG', default=False, cast=bool)
SECRET_KEY = config('SECRET_KEY')
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost').split(',')

DB_ENGINE = config('DB_ENGINE', default='django.db.backends.sqlite3')
DB_NAME = config('DB_NAME', default='db.sqlite3')
DB_USER = config('DB_USER', default='')
DB_PASSWORD = config('DB_PASSWORD', default='')
DB_HOST = config('DB_HOST', default='localhost')
DB_PORT = config('DB_PORT', default='3306', cast=int)
```

**Key Point:** Same settings.py file works for all environments because it reads from the appropriate .env file on each machine.

---

## SAFETY MEASURES

### Prevent Accidental Overwrites

**On TEST Server:**
```bash
# .env.test protected
chmod 600 /home/dev/advisor-portal-app/.env.test
# Only owner can read/write
```

**On PRODUCTION Server:**
```bash
# .env.production super protected
chmod 600 /var/www/advisor-portal/.env.production
# Only owner can read/write
```

### Deployment Script Checks

**TEST Deploy:**
```powershell
# Before deploying:
# 1. Verify target is 157.245.141.42 (not PROD IP)
# 2. Backup existing .env.test
# 3. Copy new .env.test
# 4. Verify Django can read it
```

**PRODUCTION Deploy:**
```powershell
# Before deploying:
# 1. Verify target is 104.248.126.74 (not TEST IP)
# 2. USER CONFIRMATION: "Deploy to PRODUCTION? [Y/N]"
# 3. Backup existing .env.production
# 4. Copy new .env.production
# 5. Verify Django can read it
# 6. Additional: Show what will change
```

---

## VERIFICATION

After deployment, verify correct environment is running:

**TEST Server Check:**
```bash
# Should show TEST database name
ssh dev@157.245.141.42 "cat /home/dev/advisor-portal-app/.env.test | grep DB_NAME"
# Output: DB_NAME=advisor_portal
```

**PRODUCTION Server Check:**
```bash
# Should show PRODUCTION database name
ssh dev@104.248.126.74 "cat /var/www/advisor-portal/.env.production | grep DB_NAME"
# Output: DB_NAME=advisor_portal
```

**Django Verification:**
```bash
# Each server should connect to correct database
# TEST server queries TEST database
# PROD server queries PROD database
# LOCAL queries SQLite
```

---

## .gitignore PROTECTION

```
# .gitignore (already configured to prevent accidental commits)
.env
.env.local
.env.test
.env.production
.env.*.local
```

This ensures:
- ❌ No LOCAL .env committed
- ❌ No TEST .env.test committed
- ❌ No PROD .env.production committed
- ✅ Only code committed (same settings.py for all)
- ✅ Each environment uses its own credentials

---

## SUMMARY

| Environment | File | Location | Database | Debug | Access |
|---|---|---|---|---|---|
| LOCAL | `.env` | LOCAL machine | SQLite | True | Development only |
| TEST | `.env.test` | 157.245.141.42 | MySQL (TEST) | False | Via deploy script |
| PRODUCTION | `.env.production` | 104.248.126.74 | MySQL (PROD) | False | Via deploy script |

**Key Points:**
- ✅ Complete isolation between environments
- ✅ LOCAL development unaffected
- ✅ TEST deployments don't touch PROD
- ✅ PROD deployments don't touch TEST
- ✅ Each environment has unique credentials
- ✅ Deployment scripts include safety checks

---

## NEXT ACTION

Ready to create:
1. `.env.production` content (with PRODUCTION credentials)
2. `deploy_to_production.ps1` script
3. Both will use this isolation strategy
4. No risk to LOCAL or TEST environments

