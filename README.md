# Advisor Portal

Federal Employee Benefits Case Management Platform

## Technology Stack

- **Framework:** Django 6.0 (Python 3.12)
- **Database:** MySQL 8.0+
- **API:** Django REST Framework
- **Task Queue:** Celery + Redis
- **Storage:** DigitalOcean Spaces (S3-compatible)
- **Notifications:** Twilio SMS

## Project Structure

```
advisor-portal-app/
├── apps/                   # Django applications
│   ├── users/             # User management, authentication
│   ├── cases/             # Case submission and management
│   ├── documents/         # Document upload and storage
│   ├── notifications/     # SMS and in-app notifications
│   ├── credits/           # Credit system and billing
│   └── integrations/      # External API integrations (GHL, etc.)
├── config/                # Django project settings
├── venv/                  # Virtual environment (not in git)
├── media/                 # Uploaded files (local dev)
├── staticfiles/           # Collected static files
├── .env                   # Environment variables (not in git)
├── .gitignore            # Git ignore rules
├── manage.py             # Django management script
└── requirements.txt      # Python dependencies
```

## Local Development Setup

### Prerequisites

- Python 3.12+
- MySQL 8.0+ (local installation)
- Git

### Installation Steps

1. **Clone the repository:**
   ```powershell
   git clone <repository-url>
   cd advisor-portal-app
   ```

2. **Create and activate virtual environment:**
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```

3. **Install dependencies:**
   ```powershell
   pip install -r requirements.txt
   ```

4. **Configure environment variables:**
   ```powershell
   cp .env.example .env
   # Edit .env with your local MySQL credentials
   ```

5. **Create MySQL database:**
   ```sql
   CREATE DATABASE advisor_portal CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   ```

6. **Run migrations:**
   ```powershell
   python manage.py migrate
   ```

7. **Create superuser:**
   ```powershell
   python manage.py createsuperuser
   ```

8. **Run development server:**
   ```powershell
   python manage.py runserver
   ```

9. **Access the application:**
   - Admin: http://localhost:8000/admin/
   - API: http://localhost:8000/api/

## Database Configuration

The project uses MySQL (matching the benefits-software application).

**Local MySQL Connection:**
- Database: `advisor_portal`
- Host: `localhost`
- Port: `3306`
- Update credentials in `.env` file

**Benefits Software Integration:**
- Both apps can share the same MySQL server
- Separate databases: `advisor_portal` and `benefits_software`
- No interference between applications

## Git Workflow

```powershell
# Create feature branch
git checkout -b feature/your-feature-name

# Make changes and commit
git add .
git commit -m "Description of changes"

# Push to remote
git push origin feature/your-feature-name

# Create pull request on GitHub/GitLab
```

## Common Commands

```powershell
# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Run development server
python manage.py runserver

# Create new Django app
python manage.py startapp appname

# Make migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Collect static files
python manage.py collectstatic

# Run tests
pytest

# Django shell
python manage.py shell
```

## Next Steps

1. ✅ Project structure created
2. ✅ Virtual environment configured
3. ✅ Django installed
4. 🔲 Create Django apps (users, cases, documents, etc.)
5. 🔲 Configure MySQL connection
6. 🔲 Create database models
7. 🔲 Build admin interface
8. 🔲 Implement REST API
9. 🔲 Add authentication
10. 🔲 Integrate with benefits-software

## Documentation

- Technical Requirements: `../advisor-portal/research/technical-requirements.md`
- Technical Presentation: `../advisor-portal/research/technical-presentation.md`
- Client Meeting Agenda: `../advisor-portal/research/client-meeting-agenda.md`

## Support

For questions or issues, contact the development team.

---

**Version:** 0.1.0 (Initial Setup)  
**Last Updated:** December 8, 2025
