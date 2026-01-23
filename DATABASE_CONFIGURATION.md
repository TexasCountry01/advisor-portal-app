# Database Configuration

## CRITICAL: Server Database Setup

### Remote Test Server (157.245.141.42)
- **Database Type**: MySQL (NOT SQLite)
- **Host**: advisor-portal-db-test-do-user-6630088-0.e.db.ondigitalocean.com
- **Port**: 25060
- **Database Name**: advisor_portal
- **Configured via**: `.env` file (DO NOT COMMIT .env FILE TO GIT)

### Production Server (Future)
- **Database Type**: MySQL (NOT SQLite)
- **Configuration**: Via `.env` file environment variables

---

## Local Development
- **Database Type**: SQLite (db.sqlite3)
- **Purpose**: Local testing only
- **Warning**: Local SQLite data does NOT sync with remote MySQL

---

## Environment Variables (.env file)

The application uses `python-decouple` library to read environment variables from `.env` file.

**Required .env variables for MySQL:**
```
DB_ENGINE=django.db.backends.mysql
DB_NAME=advisor_portal
DB_USER=doadmin
DB_PASSWORD=<password>
DB_HOST=advisor-portal-db-test-do-user-6630088-0.e.db.ondigitalocean.com
DB_PORT=25060
```

**Settings.py logic:**
- Reads `DB_ENGINE` from environment via `config('DB_ENGINE', default='django.db.backends.sqlite3')`
- If `DB_ENGINE == 'django.db.backends.mysql'`: Uses MySQL configuration
- Otherwise: Falls back to SQLite (local development default)

---

## Critical Discovery (Jan 18, 2026)

**Issue Found:**
- Remote test server was defaulting to SQLite instead of MySQL
- `.env` file existed but wasn't being explicitly loaded
- Django `decouple` library handles `.env` loading automatically IF the file exists in project root

**Resolution:**
- Added comment to settings.py noting that decouple handles .env loading
- Verified `.env` file is in `/home/dev/advisor-portal-app/.env`
- Verified decouple is in requirements.txt and installed on remote
- Gunicorn now correctly connects to MySQL on startup

---

## Deployment Checklist

When deploying to new server:
1. ✅ Ensure MySQL credentials are in `.env` file
2. ✅ Place `.env` in project root directory
3. ✅ DO NOT commit `.env` to git (add to .gitignore)
4. ✅ Verify `python-decouple` is in requirements.txt
5. ✅ Run `pip install -r requirements.txt` on server
6. ✅ Verify MySQL connectivity before starting gunicorn
7. ✅ Start gunicorn (it will auto-load .env via decouple)

---

## Testing Database Connection

To verify which database is being used:

**Via Django shell:**
```bash
python manage.py shell
>>> from django.conf import settings
>>> settings.DATABASES
```

Should show MySQL connection details if `.env` is properly loaded.

---

## .gitignore Configuration

```
# Never commit environment files
.env
.env.local
.env.*.local
```

This ensures sensitive credentials never enter version control.
