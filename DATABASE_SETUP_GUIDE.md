# Database Setup Guide

## CRITICAL: Three Different Database Configurations

This project uses **different databases** for local development, testing, and production. **DO NOT MIX THEM UP!**

---

## 1. LOCAL DEVELOPMENT - SQLite

**Database Type:** SQLite  
**File:** `db.sqlite3` (in project root)  
**Configuration:** Built-in to Django, no external database needed  
**Use Case:** Local testing, development, no external dependencies  

**Configuration (.env):**
```
DB_ENGINE=django.db.backends.sqlite3
DB_NAME=db.sqlite3
```

**When to use:**
- Running `python manage.py runserver` locally
- Running tests locally
- Development without external database setup

**Notes:**
- SQLite data is LOCAL ONLY
- Does NOT sync with remote databases
- Perfect for isolated development

---

## 2. REMOTE TEST SERVER - MySQL/MariaDB (DigitalOcean)

**Database Type:** MySQL/MariaDB (Managed by DigitalOcean)  
**Host:** `advisor-portal-db-test-do-user-6630088-0.e.db.ondigitalocean.com`  
**Port:** `25060` (non-standard port)  
**Database Name:** `advisor_portal`  
**User:** `doadmin`  
**Password:** Stored securely in `/var/www/advisor-portal/.env` on remote server  

**IP Address:** 157.245.141.42  
**Domain:** test-reports.profeds.com  

**Configuration (.env on remote server):**
```
DB_ENGINE=django.db.backends.mysql
DB_NAME=advisor_portal
DB_USER=doadmin
DB_PASSWORD=<stored-securely-on-remote-server>
DB_HOST=advisor-portal-db-test-do-user-6630088-0.e.db.ondigitalocean.com
DB_PORT=25060
```

**When to use:**
- Testing deployed application
- QA/Testing environment
- Verifying migrations before production
- Testing against real MySQL database

**Important:**
- Password is stored ONLY on the remote server
- NEVER commit password to GitHub
- Use DigitalOcean console to reset password if needed

---

## 3. PRODUCTION SERVER - MySQL/MariaDB (DigitalOcean)

**Database Type:** MySQL/MariaDB (Managed by DigitalOcean)  
**Configuration:** SAME AS TEST SERVER (will be configured when production server is set up)  

**Expected Setup:**
- Separate DigitalOcean managed MySQL database
- Same user/password management approach
- Configuration stored securely on production server

**Important:**
- Will use same pattern as test server (.env on production)
- Database credentials never committed to GitHub
- Production database and test database are SEPARATE

---

## Database Selection Flow

```
Does code run locally?
├─ YES: Use SQLite (db.sqlite3)
└─ NO: Check environment variables

Environment = TEST SERVER?
├─ YES: Use DigitalOcean MySQL (advisor-portal-db-test...)
└─ NO: Check if PRODUCTION

Environment = PRODUCTION?
├─ YES: Use DigitalOcean MySQL (production database)
└─ NO: Default to SQLite
```

---

## Backing Up Your Configuration

### Remote Test Server .env Backup
**Location:** `.env.backup.test-server` (in project root)  
**Created:** Automatically by deploy script  
**Contains:** All sensitive database configuration  
**Security:** Keep this file PRIVATE, do not commit to GitHub

### How to Restore Remote .env
If you lose the remote .env file, restore from backup:
```bash
ssh dev@157.245.141.42
cd /var/www/advisor-portal
cat > .env << 'EOF'
[paste contents from .env.backup.test-server]
EOF
```

---

## Migration Management

### Running Migrations Locally
```bash
# Uses SQLite (db.sqlite3)
python manage.py migrate
```

### Running Migrations on Test Server
```bash
# Deploy script does this automatically
# Uses DigitalOcean MySQL
./deploy_to_test_server.ps1
```

### Creating New Migrations
```bash
# Create migration (works with any database)
python manage.py makemigrations

# Test locally with SQLite
python manage.py migrate

# Commit migration files to Git
git add cases/migrations/
git commit -m "Add new migration"

# Deploy script will apply to test server automatically
```

---

## Common Issues

### Error: "no such column"
**Cause:** Migrations not applied to database  
**Solution:** Run migrations for correct environment

### Error: "Access denied for MySQL user"
**Cause:** Wrong password or user in .env  
**Solution:** Check DigitalOcean console for correct credentials

### Error: "Can't connect to MySQL server"
**Cause:** Network firewall blocking port 25060  
**Solution:** Check DigitalOcean firewall rules

### SQLite vs MySQL mismatch
**Cause:** Using SQLite .env on test server  
**Solution:** Ensure test server .env points to MySQL, NOT SQLite

---

## Security Reminders

⚠️ **NEVER:**
- Commit `.env` file to GitHub
- Hardcode passwords in scripts
- Mix database configurations
- Use local SQLite data on production

✅ **ALWAYS:**
- Keep `.env` files in `.gitignore`
- Store passwords in secure locations (DigitalOcean console)
- Back up `.env` files locally
- Test migrations locally before deploying
- Use deploy script to ensure correct database is configured

---

## Summary Table

| Aspect | LOCAL | TEST SERVER | PRODUCTION |
|--------|-------|------------|-----------|
| **Database** | SQLite | MySQL/MariaDB | MySQL/MariaDB |
| **Location** | db.sqlite3 | DigitalOcean | DigitalOcean |
| **Host** | Local file | advisor-portal-db-test-... | TBD |
| **Port** | N/A | 25060 | TBD |
| **User Management** | N/A | doadmin | TBD |
| **Config Location** | .env (local) | .env (remote) | .env (remote) |
| **Data Isolation** | Complete | Separate from LOCAL | Separate from TEST |
| **Use Case** | Development | Testing | Live users |

