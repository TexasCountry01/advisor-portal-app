# ProFeds Advisor Portal — Project State Reference

> **This document is the single source of truth for the current state of the Advisor Portal application.**
> It is intended to be read by GitHub Copilot (or any AI assistant) at the start of a session to
> quickly understand the project's infrastructure, credentials, deployment, and codebase layout.
>
> **Last Updated:** February 21, 2026
> **Current Git Commit:** `be2c3cc` — all three environments in sync

---

## 1. Application Overview

The Advisor Portal is a case-management application for **ProFeds**, a federal employee benefits consulting firm. Financial advisors (members) submit benefits-analysis requests, which are processed by Benefits Technicians. The system manages the complete lifecycle — submission, investigation, quality review, and report release.

- **Framework:** Django 5.0.7
- **Language:** Python 3.11.2 (servers) / Python 3.12.10 (local dev)
- **Database:** SQLite (local), MySQL (TEST & PROD — DigitalOcean Managed)
- **CSS:** Bootstrap 5
- **Rich Text:** TinyMCE
- **Full BRD:** See `BUSINESS_REQUIREMENTS_DOCUMENT.md` in project root

---

## 2. Environments — Three Tiers

### 2.1 LOCAL (Development)

| Item | Value |
|------|-------|
| Machine | Windows PC |
| Workspace | `C:\Users\ProFed\workspace\advisor-portal-app` |
| Python | 3.12.10 (via `venv\` in project root) |
| Database | SQLite (`db.sqlite3`) |
| Email Backend | Console (prints to terminal, does not send) |
| Run Command | `.\venv\Scripts\Activate.ps1; python manage.py runserver 0.0.0.0:8000` |
| URL | `http://localhost:8000` |
| DEBUG | `True` |

### 2.2 TEST (Remote — DigitalOcean Droplet)

| Item | Value |
|------|-------|
| **IP Address** | `157.245.141.42` |
| **SSH User** | `dev` |
| **SSH Command** | `ssh dev@157.245.141.42` |
| **SSH Key** | `id_ed25519` (passwordless — key installed on server) |
| **App Path** | `/home/dev/advisor-portal-app` |
| **URL** | `https://test-reports.profeds.com` |
| **Python** | 3.11.2 (via `venv/` in app directory) |
| **Database** | MySQL — DigitalOcean Managed |
| **DB Host** | `advisor-portal-db-test-do-user-6630088-0.e.db.ondigitalocean.com:25060` |
| **DB Name** | `advisor_portal` |
| **DB User** | `doadmin` |
| **Email Backend** | SMTP (Gmail — `smtp.gmail.com:587` TLS) |
| **Email From** | `reports@profeds.com` |
| **SITE_URL** | `https://test-reports.profeds.com` |
| **DEBUG** | `True` |
| **Web Server** | Gunicorn (3 workers) → unix socket → Nginx |
| **Gunicorn Socket** | `/home/dev/advisor-portal-app/gunicorn.sock` |
| **SSL** | Yes (Let's Encrypt via Certbot) |
| **Sudo Required** | No (dev user owns everything) |

### 2.3 PRODUCTION (Remote — DigitalOcean Droplet)

| Item | Value |
|------|-------|
| **IP Address** | `104.248.126.74` |
| **SSH User** | `dev` |
| **SSH Command** | `ssh dev@104.248.126.74` |
| **SSH Key** | `id_ed25519` (passwordless — key installed on server) |
| **App Path** | `/var/www/advisor-portal` |
| **URL** | `https://reports.profeds.com` |
| **Python** | 3.11.2 (via `venv/` in app directory) |
| **Database** | MySQL — DigitalOcean Managed |
| **DB Host** | `db-mysql-nyc1-61187-do-user-6630088-0.e.db.ondigitalocean.com:25060` |
| **DB Name** | `advisor_portal` |
| **DB User** | `doadmin` |
| **Email Backend** | SMTP (Gmail — `smtp.gmail.com:587` TLS) |
| **Email From** | `reports@profeds.com` |
| **SITE_URL** | `https://reports.profeds.com` |
| **DEBUG** | `False` |
| **Web Server** | Gunicorn (3 workers) → unix socket → Nginx |
| **Gunicorn Socket** | `/var/www/advisor-portal/gunicorn.sock` |
| **SSL** | Yes (Let's Encrypt via Certbot) |
| **Sudo Password** | `ProFeds2025Prod!` |

> **⚠️ CRITICAL PATH DIFFERENCE:**
> - TEST path: `/home/dev/advisor-portal-app`
> - PROD path: `/var/www/advisor-portal`
>
> This affects all SSH commands, gunicorn service config, cron jobs, and venv paths.
> Always double-check which server you're targeting before running commands.

---

## 3. Git Configuration

| Item | Value |
|------|-------|
| **Repository** | `https://github.com/TexasCountry01/advisor-portal-app.git` |
| **Branch** | `main` (primary) |
| **Other Branches** | `badge-button-styling` (inactive) |
| **Latest Commit** | `be2c3cc` — "Workspace cleanup: organize docs and scripts into archive folders" |
| **Auth Method** | HTTPS with GitHub credentials cached |

### Recent Commit History
```
be2c3cc  Workspace cleanup: organize docs and scripts into archive folders
11bafc4  UX: Two-column Release Settings, prominent save button, no scroll
5a7b157  UX: Save stays on active tab, move save button to top-right
94d0ce1  Redesign System Settings: wire up toggles, add tooltips, sticky save
510a0b8  Remove test email script from repo
```

---

## 4. Deployment Process

> **⚠️ IMPORTANT:** Only pull to servers when there are actual **code changes**.
> Documentation-only commits (markdown files, PROJECT_STATE.md, etc.) do NOT need
> a server pull or gunicorn restart. Just `git push origin main` and leave the servers alone.
> The docs exist in the Git repo for reference but have no effect on the running application.

### Deploy to TEST

```powershell
# From local Windows machine (CODE CHANGES ONLY):
git push origin main
ssh dev@157.245.141.42 "cd /home/dev/advisor-portal-app && git pull origin main && sudo systemctl restart gunicorn"
```

### Deploy to PROD

```powershell
# From local Windows machine (CODE CHANGES ONLY):
git push origin main
ssh dev@104.248.126.74 "cd /var/www/advisor-portal && git pull origin main && echo 'ProFeds2025Prod!' | sudo -S systemctl restart gunicorn"
```

### If Migrations Are Needed

```bash
# On the server (after git pull, before gunicorn restart):
venv/bin/python manage.py migrate
venv/bin/python manage.py collectstatic --noinput
```

### Restart Gunicorn Only (no code change)

```bash
# TEST:
ssh dev@157.245.141.42 "sudo systemctl restart gunicorn"

# PROD:
ssh dev@104.248.126.74 "echo 'ProFeds2025Prod!' | sudo -S systemctl restart gunicorn"
```

### Deployment Scripts (Available in Root)

| Script | Purpose |
|--------|---------|
| `deploy_to_test_server.ps1` | Automated TEST deployment from Windows |
| `deploy_to_production.ps1` | Automated PROD deployment from Windows |
| `deploy.sh` | Linux/Mac deployment script |
| `setup_test_server.sh` | Initial TEST server setup |

---

## 5. Server Services

### 5.1 Gunicorn Service

Both servers run gunicorn as a systemd service:

**TEST** (`/etc/systemd/system/gunicorn.service`):
```ini
[Service]
User=dev
Group=dev
WorkingDirectory=/home/dev/advisor-portal-app
Environment=PATH=/home/dev/advisor-portal-app/venv/bin
ExecStart=/home/dev/advisor-portal-app/venv/bin/gunicorn --workers 3 --bind unix:/home/dev/advisor-portal-app/gunicorn.sock --umask 0000 config.wsgi:application
```

**PROD** (`/etc/systemd/system/gunicorn.service`):
```ini
[Service]
User=dev
Group=dev
WorkingDirectory=/var/www/advisor-portal
Environment="PATH=/var/www/advisor-portal/venv/bin"
ExecStart=/var/www/advisor-portal/venv/bin/gunicorn --workers 3 --bind unix:/var/www/advisor-portal/gunicorn.sock config.wsgi:application
```

### 5.2 Nginx

Both servers: Nginx reverse-proxies to the gunicorn unix socket. Config at `/etc/nginx/sites-enabled/advisor-portal`.

| Server | server_name | Proxy Target |
|--------|------------|-------------|
| TEST | `test-reports.profeds.com` | `unix:/home/dev/advisor-portal-app/gunicorn.sock` |
| PROD | `reports.profeds.com` | `unix:/var/www/advisor-portal/gunicorn.sock` |

### 5.3 Cron Jobs

Both servers have an identical cron job (under `dev` user's crontab):

**TEST:**
```cron
0 12 * * * cd /home/dev/advisor-portal-app && /home/dev/advisor-portal-app/venv/bin/python manage.py release_scheduled_cases >> /var/log/release_cases.log 2>&1
```

**PROD:**
```cron
0 12 * * * cd /var/www/advisor-portal && /var/www/advisor-portal/venv/bin/python manage.py release_scheduled_cases >> /var/log/release_cases.log 2>&1
```

- **Schedule:** Daily at 12:00 UTC (noon)
- **Purpose:** Processes scheduled case releases — finds completed cases where `scheduled_release_date ≤ today` and releases them (sets `actual_release_date`, sends completion email)
- **Log:** `/var/log/release_cases.log`
- **Respects:** `SystemSettings.batch_release_enabled` toggle — skips if disabled

---

## 6. Email Configuration

### SMTP Settings (Both Servers)

| Setting | Value |
|---------|-------|
| Host | `smtp.gmail.com` |
| Port | `587` |
| TLS | `True` |
| User | `reports@profeds.com` |
| App Password | `rnnscdlqxtcfjwrj` |

### Current Toggle States (as of Feb 21, 2026)

| Toggle | TEST | PROD |
|--------|------|------|
| Email Notifications Enabled | **ON** | **OFF** |
| Batch Release Enabled | **ON** | **OFF** |
| Enable Scheduled Releases | **ON** | **OFF** |

> **Note:** PROD toggles are intentionally OFF. The owner manually controls when to enable email and scheduling features in production.

---

## 7. Admin Credentials

### TEST Server Users
| Username | Password | Role |
|----------|----------|------|
| `admin` | (set via Django admin) | Administrator |

### PROD Server Users
| Username | Password | Role |
|----------|----------|------|
| `admin` | (set via Django admin) | Administrator |

### Server Sudo
| Server | User | Sudo Password |
|--------|------|---------------|
| TEST | `dev` | No password required (passwordless sudo) |
| PROD | `dev` | `ProFeds2025Prod!` |

---

## 8. Project Structure (Post-Cleanup)

```
advisor-portal-app/
├── .env                          # Local environment config (gitignored)
├── .gitignore
├── manage.py                     # Django management
├── requirements.txt              # Python dependencies
├── db.sqlite3                    # Local SQLite database
│
├── config/                       # Django project settings
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
│
├── accounts/                     # User management app
│   ├── models.py                 # User model (roles, levels), delegates, credits
│   ├── views.py                  # User management, profile editing, delegates
│   ├── forms.py
│   ├── urls.py
│   ├── templates/accounts/       # 6 templates
│   └── migrations/
│
├── cases/                        # Core case management app
│   ├── models.py                 # Case, CaseDocument, CaseNote, CaseMessage, etc.
│   ├── models_fact_finder.py     # FederalFactFinder model
│   ├── views.py                  # ~6150 lines — all case operations
│   ├── views_submit_case.py      # Enhanced case submission
│   ├── views_pdf_template.py     # PDF/FFF operations
│   ├── views_quick_submit.py     # Quick submit flow
│   ├── urls.py                   # 60+ URL patterns (app_name='cases')
│   ├── forms.py
│   ├── constants.py
│   ├── services/                 # Business logic modules
│   │   ├── email_service.py      # 10 email functions + should_send_emails() gate
│   │   ├── credit_service.py     # Credit operations
│   │   ├── case_id_generator.py
│   │   ├── case_audit_service.py
│   │   ├── case_operations.py
│   │   ├── document_count_service.py
│   │   ├── timezone_service.py
│   │   ├── api_integration.py
│   │   ├── pdf_form_handler.py
│   │   └── pdf_generator.py
│   ├── management/commands/
│   │   ├── release_scheduled_cases.py  # Cron job — batch release
│   │   ├── send_scheduled_emails.py
│   │   ├── create_sample_data.py
│   │   ├── delete_pdf_docs.py
│   │   └── retry_api_sync.py
│   ├── templates/cases/          # 31 templates
│   ├── templates/emails/         # 20 email templates
│   └── migrations/               # 33 migrations
│
├── core/                         # Core app — settings, auth, audit
│   ├── models.py                 # SystemSettings (toggles), AuditLog, StaffNotification
│   ├── views.py                  # Login, logout, profile, system settings
│   ├── views_audit.py            # 9 audit report views
│   ├── views_reports.py          # Reports dashboard
│   ├── urls.py
│   ├── signals.py                # Login/logout audit logging
│   └── migrations/               # 12 migrations
│
├── templates/                    # Global templates
│   ├── base.html                 # Base template (navbar, footer, JS)
│   └── core/                     # 15 core templates
│
├── static/                       # Static files (CSS, JS, images)
├── staticfiles/                  # collectstatic output (gitignored)
├── media/                        # User uploads (gitignored)
├── case_documents/               # Case file storage
│
├── # Essential Documentation (root)
├── BUSINESS_REQUIREMENTS_DOCUMENT.md   # Full BRD — system as built
├── TECHNICIAN_WORKFLOW.md              # Technician decision tree & actions
├── MEMBER_WORKFLOW.md                  # Member capabilities & flows
├── ADMINISTRATOR_WORKFLOW.md           # Admin capabilities
├── MANAGER_WORKFLOW.md                 # Manager (read-only) capabilities
├── WP_FUSION_INTEGRATION_GUIDE.md      # WP Fusion integration points (40+ placeholders)
├── WP_FUSION_SSO_MEETING_PREP.md       # SSO meeting prep for WP developer
├── CRON_JOB_SETUP.md                   # Cron job documentation
├── DEPLOYMENT_GUIDE.md                 # Full deployment guide
├── DEPLOYMENT_QUICK_REFERENCE.md       # Quick deploy commands
├── DATABASE_SETUP_GUIDE.md             # Database configuration
├── QUICK_START_GUIDE.md                # Getting started guide
├── PROJECT_STATE.md                    # THIS FILE — project state reference
│
├── # Deploy Scripts (root)
├── deploy_to_test_server.ps1
├── deploy_to_production.ps1
├── deploy.sh
├── setup_test_server.sh
├── start_server.bat
├── update-server-config.ps1
├── update-server-config.sh
│
├── docs/archive/                 # 138 archived implementation/analysis docs
├── _archived_files/              # Archived data files, old code
│   ├── scripts/                  # 50+ archived one-off Python scripts
│   └── debug_scripts/            # Archived debug scripts
│
├── venv/                         # Local Python virtual environment (gitignored)
└── .venv/                        # Alternative venv (gitignored)
```

---

## 9. Django Apps & Key Files

### Settings Module: `config/settings.py`
- `AUTH_USER_MODEL = 'accounts.User'`
- `LOGIN_URL = '/login/'`
- Session-based authentication (Django default)
- Installed apps: `accounts`, `cases`, `core`, `rest_framework`, `tinymce`, `storages`

### URL Routing
| Pattern | App | Notes |
|---------|-----|-------|
| `/` | `core` | Home page |
| `/login/`, `/logout/` | `core` | Authentication |
| `/system-settings/` | `core` | Admin settings (5 tabs) |
| `/audit-log/` | `core` | Audit log browser |
| `/reports/` | `core` | Reports dashboard |
| `/cases/member/dashboard/` | `cases` | Member dashboard |
| `/cases/technician/dashboard/` | `cases` | Tech dashboard |
| `/cases/admin/dashboard/` | `cases` | Admin dashboard |
| `/cases/manager/dashboard/` | `cases` | Manager dashboard |
| `/cases/<pk>/` | `cases` | Case detail |
| `/accounts/manage-users/` | `accounts` | User management |

---

## 10. Current Feature Status

### ✅ Fully Implemented & Deployed
- Case lifecycle (8 statuses, all transitions)
- 4 user roles with permission matrix
- Technician levels (L1/L2/L3) with tier validation
- Quality review workflow (approve/revise/correct)
- Email notification system (10+ email types, master toggle)
- Case release scheduling (immediate + scheduled + cron batch)
- Hold/resume with member notifications
- Case resubmission and modification (60-day window)
- Two-way messaging (member ↔ technician)
- Internal notes (tech-only)
- Document upload/download
- Federal Fact Finder form
- Delegate system (workshop-level)
- Credits system with quarterly allowances
- Comprehensive audit trail (58 action types, 9 reports)
- 4 role-specific dashboards with sorting, filtering, column preferences
- Member change requests (due date extension, cancellation)
- System settings (5 tabs with toggle persistence)
- Accessibility (font size adjustment, sticky nav)
- PDF generation (report notes, FFF)
- Sortable columns across all dashboards

### 🔲 Planned / Not Yet Started
- WP Fusion SSO integration (placeholders in code, meeting prep doc ready)
- Benefits-software API integration (model fields + API log ready, no endpoint configured)
- Production email/scheduling activation (toggles exist, currently OFF in PROD)

---

## 11. Useful Commands Reference

### Local Development
```powershell
# Activate venv and run server
.\venv\Scripts\Activate.ps1
python manage.py runserver 0.0.0.0:8000

# Run migrations
python manage.py makemigrations
python manage.py migrate

# Django shell
python manage.py shell

# Check for issues
python manage.py check
```

### Remote Server (SSH)
```bash
# Connect
ssh dev@157.245.141.42          # TEST
ssh dev@104.248.126.74          # PROD

# Pull latest code
cd /home/dev/advisor-portal-app && git pull origin main          # TEST
cd /var/www/advisor-portal && git pull origin main               # PROD

# Restart gunicorn
sudo systemctl restart gunicorn                                  # TEST (no pw)
echo 'ProFeds2025Prod!' | sudo -S systemctl restart gunicorn     # PROD

# Django shell on server
venv/bin/python manage.py shell

# Check toggle states
echo 'from core.models import SystemSettings; s=SystemSettings.get_settings(); print(s.email_notifications_enabled, s.batch_release_enabled, s.enable_scheduled_releases)' | venv/bin/python manage.py shell

# View logs
tail -f /var/log/release_cases.log      # Cron job log
sudo journalctl -u gunicorn -f          # Gunicorn log
sudo tail -f /var/log/nginx/error.log   # Nginx error log

# Run migrations on server
venv/bin/python manage.py migrate
venv/bin/python manage.py collectstatic --noinput
```

### Git
```powershell
# Standard workflow
git add -A
git commit -m "Description"
git push origin main

# Check server commit
ssh dev@157.245.141.42 "cd /home/dev/advisor-portal-app && git log --oneline -3"
ssh dev@104.248.126.74 "cd /var/www/advisor-portal && git log --oneline -3"
```

---

## 12. Key Contacts & Accounts

| Service | Account | Notes |
|---------|---------|-------|
| GitHub | `TexasCountry01` | Repository owner |
| DigitalOcean | (owner's account) | Hosts TEST + PROD droplets + managed MySQL |
| Google/Gmail | `reports@profeds.com` | SMTP sender for email notifications |
| Domain | `profeds.com` | DNS for `reports.profeds.com` and `test-reports.profeds.com` |

---

## 13. Notes for Copilot / AI Assistants

When resuming work on this project:

1. **Read this file first** to understand the full infrastructure.
2. **Read `BUSINESS_REQUIREMENTS_DOCUMENT.md`** for what the system does.
3. **The three environments must stay in sync** — always push to Git, then pull on both TEST and PROD after any code change.
4. **PROD toggles are OFF by design** — don't turn them on without the owner's explicit instruction.
5. **Path difference is critical** — TEST is `/home/dev/advisor-portal-app`, PROD is `/var/www/advisor-portal`. Every SSH command, cron job, and service config uses these paths.
6. **Local uses SQLite, servers use MySQL** — schema is identical but engines differ. Always test migrations locally before deploying.
7. **The `.gitignore` excludes** `test_*.py`, `check_*.py`, `_temp_scripts/`, `.env`, `db.sqlite3`, `venv/`, `media/`, `staticfiles/`, `*.log`, `*.sql`. Be aware of what's tracked vs not.
8. **134 archived docs** are in `docs/archive/` and **50+ archived scripts** are in `_archived_files/scripts/`. These are historical — the 12 docs in root are the current authoritative references.
9. **SSH uses `id_ed25519` key** — no SSH config file, just `ssh dev@<IP>`.
10. **WP Fusion SSO** is the next major feature planned — see `WP_FUSION_SSO_MEETING_PREP.md` and `WP_FUSION_INTEGRATION_GUIDE.md` for full context.

---

*This document should be updated whenever infrastructure, credentials, deployment process, or major feature status changes.*
