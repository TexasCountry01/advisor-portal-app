# DUAL DIRECTORY ISSUE - COMPLETE ANALYSIS

## The Real Problem

You have **TWO SEPARATE DEPLOYMENT CONFIGURATIONS** that evolved separately:

### TEST Server (157.245.141.42)
```
WRONG SETUP (Discovered today):
- Code deployed to:   /var/www/advisor-portal/
- Gunicorn runs from: /home/dev/advisor-portal-app/
- MISMATCH = Silent deployment failures

CAUSE: deploy_to_test_server.ps1 uses /var/www/ path
       but Gunicorn service points to /home/dev/
```

### PRODUCTION Server (104.248.126.74)
```
CORRECT SETUP (As documented):
- Code at:            /var/www/advisor-portal/
- Gunicorn runs from: /var/www/advisor-portal/
- Everything aligned ✅
```

---

## How This Happened

Looking at the documentation trail:

1. **PRODUCTION was designed correctly** in ENVIRONMENT_ISOLATION_STRATEGY.md
   - Clear path: `/var/www/advisor-portal/`
   - Gunicorn service configured for `/var/www/advisor-portal/`
   - Deploy script (deploy_to_production.ps1) never created
   
2. **TEST server evolved differently**
   - Started with `/home/dev/advisor-portal-app/` (from initial setup)
   - Someone created `/var/www/advisor-portal/` directory
   - deploy_to_test_server.ps1 was written to use `/var/www/`
   - But Gunicorn service was NEVER updated to match
   
3. **Result**: TEST has a mismatch, PRODUCTION does not

---

## What Changed Today?

**Nothing broke PRODUCTION!** 

Timeline:
- PRODUCTION was deployed yesterday/earlier today (commit a1cb409)
- Correctly deployed to `/var/www/advisor-portal/`
- All paths match
- Gunicorn service correct
- Nginx config correct

We just deployed UI/UX to TEST and discovered the TEST server has the dual-directory problem.

---

## The Root Cause of the TEST Problem

The `deploy_to_test_server.ps1` script (lines 33-36):

```powershell
# WRONG!
$projectPath = "/var/www/advisor-portal"
$venvPath = "/home/dev/advisor-portal-app/venv"
$gunicornSocket = "/home/dev/advisor-portal-app/gunicorn.sock"
```

This tries to deploy to `/var/www/` but then uses Gunicorn from `/home/dev/` - they don't match!

The Gunicorn service configuration (`/etc/systemd/system/gunicorn.service`) on TEST:
```
WorkingDirectory=/home/dev/advisor-portal-app
ExecStart=/home/dev/advisor-portal-app/venv/bin/gunicorn
```

So when Gunicorn restarts, it reads code from `/home/dev/advisor-portal-app/` (the old location) not from `/var/www/advisor-portal/` (where deploy script put it).

---

## The Solution: Make TEST Match PRODUCTION

TEST should follow the same architecture as PRODUCTION:

**Option 1: Update TEST to match PRODUCTION's `/var/www/` approach** (RECOMMENDED)
- Gunicorn service: Point to `/var/www/advisor-portal/`
- Nginx: Already points to `/var/www/advisor-portal/`
- Deploy script: Already targets `/var/www/advisor-portal/`
- Result: Everything aligned

**Option 2: Keep TEST at `/home/dev/` like initial setup**
- Deploy script: Change to `/home/dev/advisor-portal-app/`
- Delete `/var/www/advisor-portal/`
- Result: Reverting to original TEST setup

---

## Recommended Action Plan

1. **Standardize TEST to match PRODUCTION architecture**
   - Update Gunicorn service on TEST to point to `/var/www/advisor-portal/`
   - Update Nginx static paths to `/var/www/advisor-portal/`
   - Delete `/home/dev/advisor-portal-app/` (but keep venv if needed)
   - Delete `/var/www/advisor-portal/` that was accidentally created

2. **Fix deploy_to_test_server.ps1**
   - Path should remain `/var/www/advisor-portal/` (matches PRODUCTION)
   - Venv should be `/var/www/advisor-portal/venv/`
   - Socket should be `/var/www/advisor-portal/gunicorn.sock`

3. **Verify alignment**
   - TEST structure ← → PRODUCTION structure
   - Same paths, different servers
   - Same deployment script approach

---

## Why This Matters

If both TEST and PRODUCTION don't follow the same pattern:
- Deployments work differently on each
- Team confusion about where things are
- Silent failures possible
- Future deployments could go wrong

**Goal: Make TEST and PRODUCTION architecturally identical (same paths, different IPs)**

---

## Current Status

✅ PRODUCTION: Correct single directory at `/var/www/advisor-portal/`
❌ TEST: Broken dual directory (code in `/var/www/` but Gunicorn runs from `/home/dev/`)

The PRODUCTION deployment today was fine. We just discovered the TEST infrastructure was broken.
