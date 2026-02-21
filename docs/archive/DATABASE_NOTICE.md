⚠️ **CRITICAL DATABASE CONFIGURATION REFERENCE**

This project uses THREE DIFFERENT DATABASE ENVIRONMENTS:

| Environment | Database Type | Location | Purpose |
|---|---|---|---|
| **LOCAL DEVELOPMENT** | SQLite | `db.sqlite3` (local file) | Development & testing |
| **TEST SERVER** | MySQL/MariaDB | DigitalOcean (157.245.141.42) | QA & testing deployed app |
| **PRODUCTION** | MySQL/MariaDB | DigitalOcean (TBD) | Live application |

**IMPORTANT: DO NOT MIX THESE UP!**

- ❌ Never use SQLite on test/production servers
- ❌ Never use MySQL connection on local development
- ✅ Always verify database type before running migrations

**See These Files for Details:**
- `DATABASE_SETUP_GUIDE.md` - Comprehensive database configuration
- `DEPLOYMENT_QUICK_REFERENCE.md` - Quick deployment checklist
- `deploy_to_test_server.ps1` - Automated deployment with MySQL verification

**Local Setup (SQLite):**
```bash
python manage.py migrate
python manage.py runserver
```

**Test Server Deployment (MySQL):**
```powershell
./deploy_to_test_server.ps1
```

**For Help:**
Review `DATABASE_SETUP_GUIDE.md` for complete documentation.
