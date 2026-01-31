# TEST Server Infrastructure Fix - Step by Step

## Summary

Fix the TEST server to match PRODUCTION's correct architecture by consolidating to single `/var/www/advisor-portal/` directory.

---

## Files That Need to Be Updated

### 1. Gunicorn Service File
**File:** `/etc/systemd/system/gunicorn.service` (on TEST server)

**CURRENT (WRONG):**
```ini
[Unit]
Description=gunicorn daemon for advisor-portal
After=network.target

[Service]
User=dev
Group=dev
WorkingDirectory=/home/dev/advisor-portal-app
Environment=PATH=/home/dev/advisor-portal-app/venv/bin
ExecStart=/home/dev/advisor-portal-app/venv/bin/gunicorn --workers 3 --bind unix:/home/dev/advisor-portal-app/gunicorn.sock --umask 0000 config.wsgi:application

[Install]
WantedBy=multi-user.target
```

**SHOULD BE (CORRECT):**
```ini
[Unit]
Description=gunicorn daemon for advisor-portal
After=network.target

[Service]
User=dev
Group=dev
WorkingDirectory=/var/www/advisor-portal
Environment=PATH=/var/www/advisor-portal/venv/bin
ExecStart=/var/www/advisor-portal/venv/bin/gunicorn --workers 3 --bind unix:/var/www/advisor-portal/gunicorn.sock --umask 0000 config.wsgi:application

[Install]
WantedBy=multi-user.target
```

**Changes:**
- WorkingDirectory: `/home/dev/advisor-portal-app` → `/var/www/advisor-portal`
- Environment PATH: `/home/dev/advisor-portal-app/venv/bin` → `/var/www/advisor-portal/venv/bin`
- ExecStart path: `/home/dev/advisor-portal-app/venv/bin` → `/var/www/advisor-portal/venv/bin`
- Socket path: `/home/dev/advisor-portal-app/gunicorn.sock` → `/var/www/advisor-portal/gunicorn.sock`

---

### 2. Nginx Configuration
**File:** `/etc/nginx/sites-available/advisor-portal` (on TEST server)

**CURRENT (SEEMS OK but verify):**
```nginx
location /static/ {
    alias /home/dev/advisor-portal-app/staticfiles/;
}

location /media/ {
    alias /home/dev/advisor-portal-app/media/;
}

location / {
    include proxy_params;
    proxy_pass http://unix:/home/dev/advisor-portal-app/gunicorn.sock;
}
```

**SHOULD BE:**
```nginx
location /static/ {
    alias /var/www/advisor-portal/staticfiles/;
}

location /media/ {
    alias /var/www/advisor-portal/media/;
}

location / {
    include proxy_params;
    proxy_pass http://unix:/var/www/advisor-portal/gunicorn.sock;
}
```

**Changes:**
- Static alias: `/home/dev/advisor-portal-app/staticfiles/` → `/var/www/advisor-portal/staticfiles/`
- Media alias: `/home/dev/advisor-portal-app/media/` → `/var/www/advisor-portal/media/`
- Socket proxy: `/home/dev/advisor-portal-app/gunicorn.sock` → `/var/www/advisor-portal/gunicorn.sock`

---

### 3. Deploy Script
**File:** `deploy_to_test_server.ps1` (on local machine)

**CURRENT (ALREADY FIXED):**
```powershell
$projectPath = "/var/www/advisor-portal"
$venvPath = "/var/www/advisor-portal/venv"
$gunicornSocket = "/var/www/advisor-portal/gunicorn.sock"
```

✅ Already corrected to match `/var/www/advisor-portal/`

---

## Cleanup Required

On TEST server, after updating service files:

1. **Verify `/var/www/advisor-portal/` exists and has full code:**
   ```bash
   ls -la /var/www/advisor-portal/
   ```

2. **Verify `/var/www/advisor-portal/venv` exists:**
   ```bash
   ls -la /var/www/advisor-portal/venv/bin/gunicorn
   ```

3. **Optional: Remove old `/home/dev/advisor-portal-app/` directory** (after verifying all code is in `/var/www/`)
   ```bash
   rm -rf /home/dev/advisor-portal-app
   ```
   
   NOTE: Only do this after confirming `/var/www/advisor-portal/` has everything!

---

## Deployment Steps

### Step 1: Update Gunicorn Service (requires sudo)
```bash
sudo nano /etc/systemd/system/gunicorn.service
# Replace all /home/dev/advisor-portal-app with /var/www/advisor-portal
# Save: Ctrl+X, Y, Enter
```

### Step 2: Update Nginx Config (requires sudo)
```bash
sudo nano /etc/nginx/sites-available/advisor-portal
# Replace all /home/dev/advisor-portal-app with /var/www/advisor-portal
# Save: Ctrl+X, Y, Enter
```

### Step 3: Reload Services
```bash
sudo systemctl daemon-reload
sudo systemctl restart gunicorn
sudo systemctl reload nginx
```

### Step 4: Verify Everything Works
```bash
# Check Gunicorn is running
sudo systemctl status gunicorn

# Check socket exists
ls -la /var/www/advisor-portal/gunicorn.sock

# Test connectivity (from local machine)
curl -k https://test-reports.profeds.com/
```

### Step 5: Verify Code is Being Served
```bash
# Check footer has "ProFeds"
curl -s -k https://test-reports.profeds.com/ | grep ProFeds

# Check navbar has sticky CSS
curl -s -k https://test-reports.profeds.com/ | grep sticky
```

---

## Why We're Doing This

| Aspect | Before | After |
|--------|--------|-------|
| Code Location | `/home/dev/advisor-portal-app/` | `/var/www/advisor-portal/` |
| Gunicorn Reads From | `/home/dev/advisor-portal-app/` | `/var/www/advisor-portal/` |
| Deploy Targets | `/var/www/advisor-portal/` | `/var/www/advisor-portal/` |
| **Alignment** | ❌ BROKEN | ✅ FIXED |

---

## After This Fix

✅ TEST server will have same architecture as PRODUCTION
✅ Deploy script will work correctly
✅ New deployments will immediately show in browser
✅ No more silent failures from deployments
✅ Team will have consistent infrastructure

---

## Verification Checklist

- [ ] Gunicorn service file updated
- [ ] Nginx config updated
- [ ] systemctl daemon-reload executed
- [ ] Services restarted successfully
- [ ] Gunicorn process running from `/var/www/advisor-portal/`
- [ ] Socket file exists at `/var/www/advisor-portal/gunicorn.sock`
- [ ] Nginx can connect to socket
- [ ] Website responds with HTTP 200
- [ ] New footer text visible (ProFeds)
- [ ] Sticky navbar CSS visible

---

**Status:** Ready to execute  
**Requires:** SSH access to TEST server, sudo privileges  
**Estimated Time:** 5-10 minutes  
**Risk:** LOW - Just aligning existing paths
