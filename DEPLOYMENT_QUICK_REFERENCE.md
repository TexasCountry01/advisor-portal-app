# Quick Deployment Reference

## REMEMBER: Three Different Database Environments

```
LOCAL DEVELOPMENT    ➜ SQLite (db.sqlite3)
TEST SERVER          ➜ MySQL/MariaDB (DigitalOcean)  
PRODUCTION           ➜ MySQL/MariaDB (DigitalOcean)
```

---

## Quick Deployment Checklist

### Before Deploying
- [ ] Test changes locally with `python manage.py runserver`
- [ ] Run migrations locally: `python manage.py migrate`
- [ ] Commit changes: `git add .` and `git commit -m "message"`
- [ ] Push to GitHub: `git push origin main`
- [ ] Back up remote .env: Already done (see `.env.backup.test-server`)

### Deploy to Test Server
```powershell
./deploy_to_test_server.ps1
```

**What it does:**
1. ✅ Verifies .env has MySQL configuration (NOT SQLite)
2. ✅ Pulls latest code from GitHub
3. ✅ Runs migrations on DigitalOcean MySQL database
4. ✅ Restarts Gunicorn with 3 workers

### After Deployment
- [ ] Visit: https://test-reports.profeds.com
- [ ] Log in and verify features work
- [ ] Check Gunicorn logs: `ssh dev@157.245.141.42 "tail /tmp/gunicorn.log"`

---

## Database Command Reference

### LOCAL (SQLite)
```bash
# Run migrations locally
python manage.py migrate

# Check database:
sqlite3 db.sqlite3 ".tables"

# Reset database (WARNING: deletes all data):
rm db.sqlite3
python manage.py migrate
```

### TEST SERVER (MySQL)
```bash
# SSH to test server
ssh dev@157.245.141.42

# Check MySQL connection
mysql -h advisor-portal-db-test-do-user-6630088-0.e.db.ondigitalocean.com \
  -P 25060 -u doadmin -p advisor_portal

# Check migrations on MySQL
python manage.py migrate --plan

# View Gunicorn logs
tail /tmp/gunicorn.log
```

---

## Emergency: Restore Remote .env

If remote .env is lost or corrupted:

```bash
# 1. Restore from local backup
cat .env.backup.test-server

# 2. Copy contents and SSH to server
ssh dev@157.245.141.42

# 3. Edit .env on remote server
nano /var/www/advisor-portal/.env

# 4. Paste contents from backup

# 5. Verify database is MySQL (NOT SQLite)
grep DB_ENGINE /var/www/advisor-portal/.env
# Should output: DB_ENGINE=django.db.backends.mysql
```

---

## Current Environment Status

| Component | Status | Details |
|-----------|--------|---------|
| Test Server IP | ✅ Running | 157.245.141.42 |
| MySQL Database | ✅ Connected | advisor-portal (DigitalOcean) |
| Gunicorn | ✅ Running | 3 workers |
| Nginx | ✅ Running | Reverse proxy |
| Domain | ✅ Active | test-reports.profeds.com |
| .env Backup | ✅ Saved | .env.backup.test-server |

---

## Files Reference

- **Deploy Script:** `deploy_to_test_server.ps1`
- **Database Guide:** `DATABASE_SETUP_GUIDE.md` (detailed reference)
- **Backup of Remote Config:** `.env.backup.test-server` (keep secure!)
- **Member Dashboard:** `cases/templates/cases/member_dashboard.html`

---

## Key Reminders

🔴 **NEVER:**
- Use local `python manage.py runserver` against remote MySQL
- Mix SQLite and MySQL configurations
- Commit `.env` or passwords to GitHub
- Reset production database for testing

🟢 **ALWAYS:**
- Keep `.env` files in `.gitignore`
- Test locally with SQLite first
- Back up remote .env before changes
- Use deploy script for test server (keeps things safe)

