# Cron Job Setup for Scheduled Case Releases - 01/11/2026

## Overview
The `release_scheduled_cases` management command automatically releases completed cases on their scheduled release date. This needs to be set up to run once per day via a cron job.

---

## Prerequisites

### 1. Verify Management Command Works
Test the command manually first:

```bash
cd /path/to/advisor-portal-app
source venv/bin/activate  # On Windows: venv\Scripts\activate
python manage.py release_scheduled_cases
```

**Expected Output**:
```
No cases to release.
```

Or if cases are eligible:
```
✓ Released case WS000-2026-01-0001 (was scheduled for 2026-01-11)
Successfully released 1 case(s).
```

### 2. Test Dry-Run Mode
See what would be released without actually doing it:

```bash
python manage.py release_scheduled_cases --dry-run
```

---

## Linux/macOS Setup

### Option 1: Standard Cron Job (Recommended)

#### Step 1: Open Crontab
```bash
crontab -e
```

#### Step 2: Add Release Job
Add this line to run daily at midnight (00:00):

```cron
# Release scheduled cases daily at midnight (0 0 = 00:00 UTC)
0 0 * * * cd /var/www/advisor-portal-app && /var/www/advisor-portal-app/venv/bin/python manage.py release_scheduled_cases
```

**Explanation**:
- `0 0` = Midnight (00:00) every day
- `* * *` = Every day of month, every month, every day of week
- `cd /path` = Change to app directory
- `/path/venv/bin/python` = Full path to Python interpreter in virtualenv

**Alternative times**:
```cron
# Run at 1 AM
0 1 * * * cd /var/www/advisor-portal-app && /var/www/advisor-portal-app/venv/bin/python manage.py release_scheduled_cases

# Run at 6 AM
0 6 * * * cd /var/www/advisor-portal-app && /var/www/advisor-portal-app/venv/bin/python manage.py release_scheduled_cases

# Run every hour
0 * * * * cd /var/www/advisor-portal-app && /var/www/advisor-portal-app/venv/bin/python manage.py release_scheduled_cases

# Run every 6 hours
0 */6 * * * cd /var/www/advisor-portal-app && /var/www/advisor-portal-app/venv/bin/python manage.py release_scheduled_cases
```

#### Step 3: Verify Installation
```bash
crontab -l
```

Should show your release job.

#### Step 4: Check Cron Logs
```bash
# Linux systems
tail -f /var/log/syslog | grep CRON

# macOS
log stream --predicate 'process == "cron"' --level debug
```

---

### Option 2: Using Environment Variables

If your app needs Django settings or environment variables:

```bash
# Create a shell script
cat > /usr/local/bin/release_cases.sh << 'EOF'
#!/bin/bash
cd /var/www/advisor-portal-app
source venv/bin/activate
export DJANGO_SETTINGS_MODULE=config.settings
python manage.py release_scheduled_cases
EOF

chmod +x /usr/local/bin/release_cases.sh

# Add to crontab
0 0 * * * /usr/local/bin/release_cases.sh
```

---

### Option 3: With Logging

Capture output to a log file for monitoring:

```bash
# Run at midnight and log output
0 0 * * * cd /var/www/advisor-portal-app && /var/www/advisor-portal-app/venv/bin/python manage.py release_scheduled_cases >> /var/log/advisor-portal/release_cases.log 2>&1
```

Create the log directory first:
```bash
mkdir -p /var/log/advisor-portal
chmod 755 /var/log/advisor-portal
```

View the log:
```bash
tail -f /var/log/advisor-portal/release_cases.log
```

---

## Windows Setup

### Option 1: Task Scheduler (GUI)

#### Step 1: Open Task Scheduler
- Press `Win + R`
- Type `taskschd.msc`
- Click OK

#### Step 2: Create New Task
1. Click "Create Task..." in right panel
2. Fill in:
   - **Name**: Release Scheduled Cases
   - **Description**: Releases completed cases on their scheduled date
   - Check "Run whether user is logged in or not"
   - Check "Run with highest privileges"

#### Step 3: Set Trigger
1. Click "Triggers" tab
2. Click "New..."
3. Select: "Daily"
4. Time: 00:00 (or your preferred time)
5. Click OK

#### Step 4: Set Action
1. Click "Actions" tab
2. Click "New..."
3. Program/script: `C:\Users\ProFed\workspace\advisor-portal-app\venv\Scripts\python.exe`
4. Arguments: `manage.py release_scheduled_cases`
5. Start in: `C:\Users\ProFed\workspace\advisor-portal-app`
6. Click OK

#### Step 5: Test
1. Right-click the task
2. Select "Run" to test immediately
3. Check "Last Run Result" - should show 0 if successful

---

### Option 2: PowerShell Script

Create `release_cases.ps1`:
```powershell
# Release scheduled cases task
$appPath = "C:\Users\ProFed\workspace\advisor-portal-app"
$pythonPath = "$appPath\venv\Scripts\python.exe"
$logPath = "$appPath\logs\release_cases.log"

# Ensure log directory exists
New-Item -ItemType Directory -Force -Path (Split-Path $logPath) | Out-Null

# Run command and log output
& $pythonPath "$appPath\manage.py" release_scheduled_cases | Tee-Object -FilePath $logPath -Append
```

Schedule in Task Scheduler:
- Program/script: `powershell.exe`
- Arguments: `-NoProfile -ExecutionPolicy Bypass -File "C:\path\to\release_cases.ps1"`

---

### Option 3: Batch File

Create `release_cases.bat`:
```batch
@echo off
cd C:\Users\ProFed\workspace\advisor-portal-app
call venv\Scripts\activate.bat
python manage.py release_scheduled_cases
```

Schedule in Task Scheduler:
- Program/script: `C:\Users\ProFed\workspace\advisor-portal-app\release_cases.bat`
- Start in: `C:\Users\ProFed\workspace\advisor-portal-app`

---

## Monitoring & Troubleshooting

### Check If Job Is Running
```bash
# Linux/Mac - check process list
ps aux | grep "release_scheduled_cases"

# Check if cases were released
python manage.py shell
>>> from cases.models import Case
>>> from datetime import date
>>> cases = Case.objects.filter(status='completed', scheduled_release_date__lte=date.today(), actual_release_date__isnull=False)
>>> for case in cases: print(f"{case.external_case_id}: Released at {case.actual_release_date}")
```

### Common Issues

#### 1. Command Not Found
**Error**: `python: command not found` or `activate: No such file`

**Fix**: Use full path to Python interpreter
```bash
/var/www/advisor-portal-app/venv/bin/python manage.py release_scheduled_cases
```

#### 2. Import Errors
**Error**: `ModuleNotFoundError: No module named 'django'`

**Fix**: Activate venv in the cron command
```bash
cd /var/www/advisor-portal-app && source venv/bin/activate && python manage.py release_scheduled_cases
```

#### 3. Database Permission Errors
**Error**: `django.db.utils.OperationalError: database is locked`

**Fix**: Ensure database is accessible and not locked by other processes

#### 4. No Cases Being Released
**Check**:
```bash
# Verify cases exist with past scheduled_release_date
python manage.py shell
>>> from cases.models import Case
>>> from datetime import date
>>> Case.objects.filter(status='completed', scheduled_release_date__lte=date.today(), actual_release_date__isnull=True)
```

---

## Cron Expression Reference

| Expression | Meaning |
|-----------|---------|
| `0 0 * * *` | Every day at midnight |
| `0 6 * * *` | Every day at 6 AM |
| `0 12 * * *` | Every day at noon |
| `0 */6 * * *` | Every 6 hours |
| `0 * * * *` | Every hour |
| `*/30 * * * *` | Every 30 minutes |
| `0 0 * * MON` | Every Monday at midnight |
| `0 0 1 * *` | First day of month at midnight |

---

## Testing the Setup

### Test 1: Manual Execution
```bash
python manage.py release_scheduled_cases
```

### Test 2: Dry-Run Mode
```bash
python manage.py release_scheduled_cases --dry-run
```

### Test 3: Create Test Case
```bash
python manage.py shell
>>> from cases.models import Case
>>> from datetime import date, timedelta
>>> case = Case.objects.first()
>>> case.status = 'completed'
>>> case.scheduled_release_date = date.today() - timedelta(days=1)  # Past date
>>> case.actual_release_date = None
>>> case.save()
>>> exit()

# Run command
python manage.py release_scheduled_cases

# Verify
python manage.py shell
>>> from cases.models import Case
>>> case = Case.objects.first()
>>> print(f"Released at: {case.actual_release_date}")
```

---

## Deployment Checklist

- [ ] Test command manually: `python manage.py release_scheduled_cases`
- [ ] Test dry-run: `python manage.py release_scheduled_cases --dry-run`
- [ ] Create cron job / scheduled task
- [ ] Test cron job execution once manually
- [ ] Monitor logs for first few days
- [ ] Verify cases are being released on schedule
- [ ] Set up log rotation (for large log files)
- [ ] Document in operations manual

---

## Summary

**Quick Setup** (Linux/macOS):
```bash
crontab -e
# Add this line:
0 0 * * * cd /var/www/advisor-portal-app && /var/www/advisor-portal-app/venv/bin/python manage.py release_scheduled_cases
```

**Quick Setup** (Windows):
- Open Task Scheduler
- Create task to run: `C:\path\venv\Scripts\python.exe manage.py release_scheduled_cases`
- Set to run daily at preferred time

**Verify it works**:
```bash
python manage.py release_scheduled_cases --dry-run
```

That's it! Cases will now automatically release on their scheduled dates.
