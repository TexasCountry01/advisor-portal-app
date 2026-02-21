# Gunicorn Dual Directory Issue - Root Cause Analysis & Fix

## Problem Summary

The TEST server has **two separate copies** of the advisor-portal code:

```
/home/dev/advisor-portal-app/           ← Gunicorn ACTUALLY RUNS FROM HERE
/var/www/advisor-portal/                ← Deploy script deploys HERE (IGNORED!)
```

This causes deployments to fail silently - code updates go to `/var/www/` but Gunicorn serves stale code from `/home/dev/`.

---

## How This Happened

### Root Cause: Conflicting Deployment Paths

1. **Gunicorn Service** (`/etc/systemd/system/gunicorn.service`)
   - `WorkingDirectory=/home/dev/advisor-portal-app`
   - `ExecStart=/home/dev/advisor-portal-app/venv/bin/gunicorn ...`
   - Uses `/home/dev/advisor-portal-app/gunicorn.sock`

2. **Nginx Configuration** (`/etc/nginx/sites-available/advisor-portal`)
   - `proxy_pass http://unix:/home/dev/advisor-portal-app/gunicorn.sock`
   - Static files: `alias /home/dev/advisor-portal-app/staticfiles/`
   - Media files: `alias /home/dev/advisor-portal-app/media/`

3. **Deploy Script** (`deploy_to_test_server.ps1`)
   - Sets `$projectPath = "/var/www/advisor-portal"` (WRONG!)
   - Deploys code there
   - But pulls venv from `/home/dev/advisor-portal-app/venv` (MISMATCH!)
   - Restarts Gunicorn which ignores the deployment

### Timeline of How This Evolved

**Likely Scenario:**
1. Initial setup: Code deployed to `/home/dev/advisor-portal-app/`
2. Someone created `/var/www/advisor-portal/` as a "standard" location (common practice)
3. Deploy script was updated to use `/var/www/` but Gunicorn service wasn't updated
4. For months, deployments were silently failing - code updated in one place, app running from another
5. Discovered only when we needed to compare deployed vs running code

---

## Is This Documented?

**No - it's not documented anywhere.** This is the discovery moment!

---

## The Fix - Unify to Single Directory

### Option A: Move Everything to `/home/dev/advisor-portal-app/` (RECOMMENDED)

This is simpler because everything is already set up here.

**Steps:**

1. **Make `/home/dev/advisor-portal-app/` the single source of truth**
   ```bash
   # Remove the unnecessary copy
   ssh dev@157.245.141.42 "rm -rf /var/www/advisor-portal"
   
   # Verify it's gone
   ssh dev@157.245.141.42 "ls -la /var/www/"
   ```

2. **Update deploy script** to deploy to correct path:
   - Change `$projectPath = "/var/www/advisor-portal"` 
   - To: `$projectPath = "/home/dev/advisor-portal-app"`

3. **Everything else already works:**
   - Gunicorn service: ✅ Points to `/home/dev/advisor-portal-app/`
   - Nginx config: ✅ Points to `/home/dev/advisor-portal-app/`
   - Venv: ✅ Located at `/home/dev/advisor-portal-app/venv`
   - Sockets: ✅ Located at `/home/dev/advisor-portal-app/gunicorn.sock`

### Option B: Move Everything to `/var/www/advisor-portal/`

Standard practice is to put apps in `/var/www/`. Would require:
1. Update Gunicorn service to point to `/var/www/advisor-portal/`
2. Update nginx to point to `/var/www/advisor-portal/`
3. Move venv to `/var/www/advisor-portal/venv`
4. Update deploy script to `/var/www/advisor-portal/`

**More work than Option A.**

---

## RECOMMENDED FIX: Option A (Single Directory)

### Step 1: Remove Duplicate

```bash
ssh dev@157.245.141.42 "rm -rf /var/www/advisor-portal"
```

### Step 2: Update Deploy Script

Change `deploy_to_test_server.ps1` line 33:

**BEFORE:**
```powershell
$projectPath = "/var/www/advisor-portal"
```

**AFTER:**
```powershell
$projectPath = "/home/dev/advisor-portal-app"
```

### Step 3: Update Paths in Deploy Script

Lines 35-36 currently have a workaround for mixed paths. After the fix, they should be consistent:

**BEFORE:**
```powershell
$venvPath = "/home/dev/advisor-portal-app/venv"
$gunicornSocket = "/home/dev/advisor-portal-app/gunicorn.sock"
```

**AFTER:** (Keep the same - already correct!)
```powershell
$venvPath = "/home/dev/advisor-portal-app/venv"
$gunicornSocket = "/home/dev/advisor-portal-app/gunicorn.sock"
```

### Step 4: Test Deployment

After making changes, test with:
```bash
powershell -ExecutionPolicy Bypass -File deploy_to_test_server.ps1
```

---

## Documentation: Create a Deployment Architecture Document

Here's what we need to document:

```
DEPLOYMENT ARCHITECTURE
======================

TEST Server (157.245.141.42)
├── Single Source of Truth: /home/dev/advisor-portal-app/
│   ├── Application code
│   ├── Django project (config/)
│   ├── Virtual environment (venv/)
│   ├── Static files (staticfiles/)
│   ├── Media files (media/)
│   └── Gunicorn socket (gunicorn.sock)
│
└── Services Configuration
    ├── Gunicorn Service (/etc/systemd/system/gunicorn.service)
    │   └── WorkingDirectory: /home/dev/advisor-portal-app/
    │   └── ExecStart: .../venv/bin/gunicorn --bind unix:.../gunicorn.sock
    │
    └── Nginx (/etc/nginx/sites-available/advisor-portal)
        ├── proxy_pass: unix:/home/dev/advisor-portal-app/gunicorn.sock
        ├── Static: /home/dev/advisor-portal-app/staticfiles/
        └── Media: /home/dev/advisor-portal-app/media/

Deployment Flow
===============
1. Local development (Ctrl+Shift+R to refresh)
   ↓
2. Git push to GitHub
   ↓
3. Deploy script pulls from /home/dev/advisor-portal-app/
   ↓
4. Run migrations if needed
   ↓
5. Restart Gunicorn (reads from same directory)
   ↓
6. Nginx serves from same directory
   ↓
7. Browser sees updated app

NO DUPLICATE DIRECTORIES - SINGLE CHAIN OF TRUTH
```

---

## Why This Wasn't Caught Earlier

1. **Automation Hides Problems** - Deploy script ran without obvious errors
2. **Silent Failures** - Git pull succeeded, migrations reported success, but wrong directory was being deployed
3. **Inconsistent Documentation** - No clear architecture document
4. **Mixed Paths** - Venv in one place, deploy in another masked the real issue

---

## Prevention Going Forward

1. **Add validation to deploy script** - Verify code was actually updated after deploy
2. **Document architecture clearly** - Keep deployment diagram in repo
3. **Clean up immediately** - Remove `/var/www/` duplicate now
4. **Test deploys** - Always verify changes appear in browser after deployment
5. **Check Gunicorn logs** - `sudo journalctl -u gunicorn -n 50` to verify process is running fresh code

---

## Action Items

- [ ] Remove `/var/www/advisor-portal/` directory
- [ ] Update `deploy_to_test_server.ps1` line 33
- [ ] Create `DEPLOYMENT_ARCHITECTURE.md` document
- [ ] Add deployment validation to script
- [ ] Test next deployment to confirm it works
- [ ] Update team documentation

---

**Status:** Ready to implement fix  
**Risk Level:** LOW - We're consolidating to what already works  
**Estimated Fix Time:** 5 minutes
