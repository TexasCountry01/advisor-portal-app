# update-server-config.ps1 — Script Reference

## Full Script

```powershell
#!/usr/bin/env pwsh
param(
    [string]$Password = "ForTheLoveOfJesus0a"
)

$Server = "dev@157.245.141.42"

Write-Host "=== Updating Nginx Configuration ===" -ForegroundColor Green

# Update Nginx
$nginxCmd = @"
cat /tmp/nginx-new.conf | sudo -S tee /etc/nginx/sites-available/advisor-portal > /dev/null
sudo -S nginx -t
sudo -S systemctl restart nginx
echo '✓ Nginx updated and restarted'
"@

$nginxCmd | ssh $Server -o "StrictHostKeyChecking no" "bash -s" 2>&1 <<< $Password

Write-Host ""
Write-Host "=== Updating Gunicorn Configuration ===" -ForegroundColor Green

# Update Gunicorn
$gunicornCmd = @"
cat /tmp/gunicorn-new.service | sudo -S tee /etc/systemd/system/gunicorn.service > /dev/null
sudo -S systemctl daemon-reload
sudo -S systemctl restart gunicorn
echo '✓ Gunicorn updated and restarted'
"@

$gunicornCmd | ssh $Server -o "StrictHostKeyChecking no" "bash -s" 2>&1 <<< $Password

Write-Host ""
Write-Host "=== Verifying Configuration ===" -ForegroundColor Green

ssh $Server "echo '✓ Gunicorn WorkingDirectory:' && grep WorkingDirectory /etc/systemd/system/gunicorn.service && echo '' && echo '✓ Nginx socket path:' && grep proxy_pass /etc/nginx/sites-available/advisor-portal && echo '' && echo '✓ Static files location:' && grep 'alias.*static' /etc/nginx/sites-available/advisor-portal"

Write-Host ""
Write-Host "=== Complete! ===" -ForegroundColor Green
```

---

## What This Script Does

This is a **remote server configuration update script**. It connects to the test server via SSH and applies new Nginx and Gunicorn configuration files that must already be staged in `/tmp/` on the server before this script is run.

---

## Section-by-Section Explanation

### Parameters

```powershell
param(
    [string]$Password = "ForTheLoveOfJesus0a"
)
```

Declares an optional `-Password` parameter with a default value. This is the `sudo` password used on the remote server to run privileged commands. It can be overridden at the command line:
```powershell
.\update-server-config.ps1 -Password "differentpassword"
```

---

### Server Target

```powershell
$Server = "dev@157.245.141.42"
```

Sets the SSH target — the `dev` user account on the **TEST server** at IP `157.245.141.42`.

---

### Step 1 — Update Nginx Configuration

```powershell
$nginxCmd = @"
cat /tmp/nginx-new.conf | sudo -S tee /etc/nginx/sites-available/advisor-portal > /dev/null
sudo -S nginx -t
sudo -S systemctl restart nginx
echo '✓ Nginx updated and restarted'
"@

$nginxCmd | ssh $Server -o "StrictHostKeyChecking no" "bash -s" 2>&1 <<< $Password
```

**What it does:**
1. Reads the new Nginx config from `/tmp/nginx-new.conf` (must be pre-staged on the server)
2. Writes it to `/etc/nginx/sites-available/advisor-portal` using `tee` with `sudo` (the `-S` flag tells sudo to read the password from stdin)
3. Runs `nginx -t` to **test the config syntax** before applying
4. Restarts Nginx if the test passes
5. Prints a confirmation message

**Key flag — `sudo -S`:** Reads the sudo password from standard input rather than prompting interactively. This allows the script to pass the password non-interactively via `<<< $Password`.

**Key flag — `StrictHostKeyChecking no`:** Suppresses the SSH host key verification prompt so the script can run unattended.

---

### Step 2 — Update Gunicorn Configuration

```powershell
$gunicornCmd = @"
cat /tmp/gunicorn-new.service | sudo -S tee /etc/systemd/system/gunicorn.service > /dev/null
sudo -S systemctl daemon-reload
sudo -S systemctl restart gunicorn
echo '✓ Gunicorn updated and restarted'
"@

$gunicornCmd | ssh $Server -o "StrictHostKeyChecking no" "bash -s" 2>&1 <<< $Password
```

**What it does:**
1. Reads the new Gunicorn systemd service file from `/tmp/gunicorn-new.service` (must be pre-staged)
2. Writes it to `/etc/systemd/system/gunicorn.service`
3. Runs `systemctl daemon-reload` so systemd picks up the changed service definition
4. Restarts the Gunicorn service
5. Prints a confirmation message

**Gunicorn** is the Python WSGI application server that runs the Django app. It sits behind Nginx, which handles all incoming HTTP traffic and proxies requests to Gunicorn via a Unix socket.

---

### Step 3 — Verify Configuration

```powershell
ssh $Server "echo '✓ Gunicorn WorkingDirectory:' && grep WorkingDirectory /etc/systemd/system/gunicorn.service && echo '' && echo '✓ Nginx socket path:' && grep proxy_pass /etc/nginx/sites-available/advisor-portal && echo '' && echo '✓ Static files location:' && grep 'alias.*static' /etc/nginx/sites-available/advisor-portal"
```

**What it does:**
Runs a single SSH command that greps three key values from the newly applied config files and prints them as a human-readable summary:

| Check | Config file | What it verifies |
|---|---|---|
| Gunicorn WorkingDirectory | `/etc/systemd/system/gunicorn.service` | The Django project path Gunicorn is running from |
| Nginx socket path | `/etc/nginx/sites-available/advisor-portal` | The Unix socket Nginx uses to proxy requests to Gunicorn |
| Static files location | `/etc/nginx/sites-available/advisor-portal` | The `alias` directive pointing to Django's collected static files |

---

## Prerequisites Before Running

The script assumes these files already exist on the server in `/tmp/`:

| File | Purpose |
|---|---|
| `/tmp/nginx-new.conf` | The new Nginx virtual host configuration |
| `/tmp/gunicorn-new.service` | The new Gunicorn systemd service file |

These must be copied to the server manually (via `scp`) before this script is executed.

---

## How to Run

```powershell
# Run with default password
.\update-server-config.ps1

# Run with a custom password
.\update-server-config.ps1 -Password "yourpassword"
```

---

## Important Notes

- **This script targets the TEST server** (`157.245.141.42`), not PROD (`104.248.126.74`)
- The `sudo` password is stored in plaintext in the default parameter — do not commit sensitive passwords to version control
- The script does not stage the config files itself — that must be done separately before running
- If `nginx -t` fails (syntax error in the new config), Nginx will NOT be restarted, preventing a production outage from a bad config
