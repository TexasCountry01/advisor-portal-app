# Server Paths Reference - CRITICAL CLARIFICATION

## Problem Statement

The codebase has conflicting documentation about deployment paths:
- **DEPLOYMENT_GUIDE.md** references `/home/dev/advisor-portal-app` 
- **TEST_SERVER_INFRASTRUCTURE_FIX.md** says TEST server **should** use `/var/www/advisor-portal/`
- **PRODUCTION_PREDEPLOY_CHECKLIST.md** confirms PRODUCTION uses `/var/www/advisor-portal/`

**Current Reality:** We've been using `/home/dev/advisor-portal-app` for TEST deployments, but the infrastructure documentation says this is WRONG.

---

## CORRECT PATHS (AUTHORITATIVE)

### TEST Server (157.245.141.42)
- **IP:** `157.245.141.42`
- **Correct Path:** `/home/dev/advisor-portal-app` ✅
- **Why:** This is where the code actually exists; `/var/www/advisor-portal/` was a planned migration that never completed
- **Gunicorn Socket:** `/home/dev/advisor-portal-app/gunicorn.sock`
- **Virtual Environment:** `/home/dev/advisor-portal-app/venv/`

### PRODUCTION Server (104.248.126.74)
- **IP:** `104.248.126.74`
- **Correct Path:** `/var/www/advisor-portal/` ✅
- **Why:** Standard web app location; follows Apache/Nginx conventions
- **Gunicorn Socket:** `/var/www/advisor-portal/gunicorn.sock`
- **Virtual Environment:** `/var/www/advisor-portal/venv/`

---

## Why The Confusion Exists

### Historical Context
1. **Original Setup:** TEST server was provisioned with code at `/home/dev/advisor-portal-app/`
2. **Plan:** TEST_SERVER_INFRASTRUCTURE_FIX.md documents a migration to `/var/www/advisor-portal/` to match PRODUCTION's architecture
3. **Status:** This migration was **planned but never executed**
4. **Result:** TEST server still uses `/home/dev/` path while documentation recommends `/var/www/`

### Documentation Problems
- **DEPLOYMENT_GUIDE.md** assumes `/home/dev/advisor-portal-app/` (correct for current TEST state, but outdated philosophy)
- **TEST_SERVER_INFRASTRUCTURE_FIX.md** prescribes `/var/www/advisor-portal/` (correct for desired state, but not implemented)
- **PRODUCTION_PREDEPLOY_CHECKLIST.md** confirms `/var/www/advisor-portal/` (correct and actually deployed)

---

## Action Items to Resolve This

### Option 1: Update TEST Server to Match PRODUCTION (Recommended Long-term)
**Pros:**
- Eliminates confusion between environments
- Both TEST and PRODUCTION use same directory structure
- Easier team onboarding
- Cleaner server organization

**Cons:**
- Requires downtime for migration
- Risk of data loss if not done carefully

**Steps:**
1. SSH to TEST server: `ssh dev@157.245.141.42`
2. Backup current code: `cp -r /home/dev/advisor-portal-app /home/dev/advisor-portal-app.backup`
3. Create target directory: `mkdir -p /var/www && sudo chown dev:dev /var/www`
4. Move code: `mv /home/dev/advisor-portal-app /var/www/advisor-portal`
5. Update Gunicorn service file to reference `/var/www/advisor-portal/`
6. Update Nginx config to reference `/var/www/advisor-portal/`
7. Restart services

### Option 2: Update Documentation to Match TEST Reality (Quick Fix)
**Pros:**
- No changes needed to running systems
- Immediate resolution of confusion
- Zero downtime

**Cons:**
- Leaves TEST and PRODUCTION with different paths
- Technical debt

**Steps:**
1. Update DEPLOYMENT_GUIDE.md to clearly state TEST uses `/home/dev/advisor-portal-app/`
2. Mark TEST_SERVER_INFRASTRUCTURE_FIX.md as "PLANNED MIGRATION - NOT YET IMPLEMENTED"
3. Add explicit server path callouts at top of all deployment docs

---

## IMMEDIATE FIX: Update Documentation (Done Below)

### Files Updated Today

#### 1. DEPLOYMENT_GUIDE.md
**Change:** Add clear header distinguishing TEST server paths from any future PRODUCTION paths
```markdown
## ⚠️ IMPORTANT: Server Paths
- **TEST Server (157.245.141.42):** `/home/dev/advisor-portal-app/` ← CURRENT & CORRECT
- **PRODUCTION Server (104.248.126.74):** `/var/www/advisor-portal/` ← Different path
```

#### 2. TEST_SERVER_INFRASTRUCTURE_FIX.md
**Change:** Add note at top explaining status
```markdown
# ⚠️ PLANNED MIGRATION - NOT YET IMPLEMENTED

This document outlines a proposed infrastructure consolidation. 
**As of Feb 2026, TEST server still uses `/home/dev/advisor-portal-app/`**

Migration to `/var/www/advisor-portal/` was planned but not executed.
```

#### 3. This New File (SERVER_PATHS_REFERENCE.md)
**Change:** Single source of truth for path clarification
```markdown
- Add to GitHub repo
- Reference from deployment docs
- Update when either server path changes
```

---

## Testing the Current Configuration

### Verify TEST Server Path is Correct
```bash
# SSH to TEST
ssh dev@157.245.141.42

# Check where code actually is
ls -la /home/dev/advisor-portal-app/ | head
# Should show: manage.py, config, cases, core, accounts, db.sqlite3, etc.

# Check if old path exists
ls -la /var/www/advisor-portal/ 2>&1
# Expected: "No such file or directory" or empty

# Check Gunicorn socket location
ls -la /home/dev/advisor-portal-app/gunicorn.sock
# Should exist and show timestamp of recent restart

# Verify Gunicorn is actually running from /home/dev path
ps aux | grep gunicorn | grep -v grep
# Should show: /home/dev/advisor-portal-app/venv/bin/gunicorn
```

### Verify PRODUCTION Path is Correct
```bash
# SSH to PRODUCTION
ssh dev@104.248.126.74

# Check code location
ls -la /var/www/advisor-portal/ | head
# Should show: manage.py, config, cases, core, accounts, etc.

# Verify Gunicorn socket
ls -la /var/www/advisor-portal/gunicorn.sock
# Should exist
```

---

## How to Prevent This Confusion Going Forward

### 1. Add to README.md
```markdown
## Server Locations

- **TEST:** `ssh dev@157.245.141.42:/home/dev/advisor-portal-app/`
- **PRODUCTION:** `ssh dev@104.248.126.74:/var/www/advisor-portal/`
```

### 2. Create `.server-config` at Root
```bash
# File: .server-config (git-tracked)
TEST_DEPLOY_PATH="/home/dev/advisor-portal-app"
PROD_DEPLOY_PATH="/var/www/advisor-portal"
TEST_SERVER_IP="157.245.141.42"
PROD_SERVER_IP="104.248.126.74"
```

### 3. Update Deploy Scripts
Make all deployment scripts reference this config instead of hardcoding paths.

### 4. Document in Wiki
If using GitHub wiki, add a "Server Reference" page with this exact information.

---

## Summary Table

| Aspect | TEST (157.245.141.42) | PRODUCTION (104.248.126.74) |
|--------|-------------------------|------------------------------|
| **Deployment Path** | `/home/dev/advisor-portal-app/` | `/var/www/advisor-portal/` |
| **Code Status** | ✅ Lives here | ✅ Lives here |
| **Virtual Env** | `/home/dev/advisor-portal-app/venv/` | `/var/www/advisor-portal/venv/` |
| **Gunicorn Socket** | `/home/dev/advisor-portal-app/gunicorn.sock` | `/var/www/advisor-portal/gunicorn.sock` |
| **Database** | test_db (MySQL) | production_db (MySQL) |
| **Environment File** | `.env.test` | `.env.production` |
| **Infrastructure Doc Status** | ✅ Matches reality | ✅ Matches reality |
| **Deployment Guide Status** | ⚠️ Needs clarification | N/A (not in guide yet) |

---

## Related Issues

This confusion likely stems from:
1. Lack of central "source of truth" document
2. Multiple deployment guides with different assumptions
3. Incomplete infrastructure migration (planned but never executed)
4. No version control of infrastructure configuration

**All of the above can be solved by:**
1. **This file** (SERVER_PATHS_REFERENCE.md) as source of truth
2. References in all deployment docs pointing here
3. `.server-config` file with environment variables
4. Regular audit of documentation vs. actual server state
