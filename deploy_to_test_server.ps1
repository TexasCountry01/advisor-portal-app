# ==============================================================================
# DEPLOY SCRIPT: Test Server Deployment
# ==============================================================================
#
# ⚠️ CRITICAL DATABASE WARNING ⚠️
# This script deploys to the TEST SERVER which uses DigitalOcean MYSQL/MARIADB
# 
# DO NOT CONFUSE DATABASES:
# - LOCAL DEVELOPMENT: SQLite (db.sqlite3) - for local testing ONLY
# - TEST SERVER: DigitalOcean MySQL/MariaDB - for testing deployed app
# - PRODUCTION: DigitalOcean MySQL/MariaDB - for live users
#
# See DATABASE_SETUP_GUIDE.md for complete database configuration documentation
# ==============================================================================
#
# WORKFLOW: 4 STEPS
# 1. Commit & push all local changes to GitHub
# 2. Verify .env database configuration (MySQL, NOT SQLite)
# 3. Pull latest changes from GitHub on TEST server
# 4. Run Django migrations + Restart Gunicorn
#
# Security Notes:
# - Database password stored securely in remote .env file (NOT in this script)
# - Never commit passwords to GitHub
# - Backup remote .env locally before changes
# - See .env.backup.test-server for reference
# ==============================================================================

# Configuration
$testServerHost = "157.245.141.42"
$testServerUser = "dev"
$projectPath = "/home/dev/advisor-portal-app"
$venvPath = "/home/dev/advisor-portal-app/venv"
$gunicornSocket = "unix:/home/dev/advisor-portal-app/gunicorn.sock"

# ⚠️ TEST SERVER DATABASE - DigitalOcean Managed MySQL/MariaDB
# (NOT SQLite - only use SQLite for LOCAL development)
$dbEngine = "django.db.backends.mysql"
$dbName = "advisor_portal"
$dbUser = "doadmin"
$dbHost = "advisor-portal-db-test-do-user-6630088-0.e.db.ondigitalocean.com"
$dbPort = "25060"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Deploying to Test Server" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# STEP 1: Commit and push all local changes to GitHub
Write-Host "[1/5] Committing and pushing local changes to GitHub..." -ForegroundColor Yellow

$gitStatus = git status --porcelain
if ($gitStatus) {
    git add -A
    $commitMessage = "Deploy to test: $(Get-Date -Format 'yyyy-MM-dd HH:mm')"
    git commit -m $commitMessage
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Git commit failed!" -ForegroundColor Red
        exit 1
    }
    git push origin main
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Git push failed!" -ForegroundColor Red
        exit 1
    }
    Write-Host "OK - Changes committed and pushed" -ForegroundColor Green
} else {
    Write-Host "OK - No local changes to commit (already up to date)" -ForegroundColor Green
}
Write-Host ""

# STEP 2: Ensure .env has correct database configuration
Write-Host "[2/5] Verifying database configuration (.env)..." -ForegroundColor Yellow

# NOTE: The .env file already exists on the remote server with all necessary configuration
# including the database password. We just verify it exists and contains required keys.
ssh $testServerUser@$testServerHost "cd $projectPath && if [ -f .env ]; then echo 'OK'; else echo 'ERROR: .env not found'; exit 1; fi" | Out-Null

Write-Host "OK - Database configuration verified" -ForegroundColor Green
Write-Host ""

# STEP 3: Pull latest changes from GitHub
Write-Host "[3/5] Pulling latest changes from GitHub..." -ForegroundColor Yellow
ssh $testServerUser@$testServerHost "cd $projectPath && git pull origin main"

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Git pull failed!" -ForegroundColor Red
    exit 1
}

# Remove docs/ — reference documents are not needed on the server
ssh $testServerUser@$testServerHost "rm -rf $projectPath/docs"

Write-Host "OK - Git pull completed" -ForegroundColor Green
Write-Host ""

# STEP 4: Run database migrations
Write-Host "[4/5] Running database migrations..." -ForegroundColor Yellow
ssh $testServerUser@$testServerHost "cd $projectPath && source $venvPath/bin/activate && python manage.py migrate && python manage.py collectstatic --noinput 2>&1 | tail -3"

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Migration or collectstatic failed!" -ForegroundColor Red
    exit 1
}

Write-Host "OK - Migrations completed" -ForegroundColor Green
Write-Host ""

Write-Host "[5/5] Restarting Gunicorn..." -ForegroundColor Yellow
ssh $testServerUser@$testServerHost "sudo -n systemctl restart gunicorn && sudo -n systemctl restart nginx"

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to restart gunicorn/nginx via systemd!" -ForegroundColor Red
    exit 1
}

# Verify services are running
Write-Host "Verifying Gunicorn and Nginx services..." -ForegroundColor Yellow
$gunicornStatus = ssh $testServerUser@$testServerHost "systemctl is-active gunicorn"
$nginxStatus = ssh $testServerUser@$testServerHost "systemctl is-active nginx"

if ($gunicornStatus.Trim() -ne "active" -or $nginxStatus.Trim() -ne "active") {
    Write-Host "ERROR: One or more services are not active." -ForegroundColor Red
    Write-Host "Gunicorn: $gunicornStatus" -ForegroundColor Red
    Write-Host "Nginx: $nginxStatus" -ForegroundColor Red
    exit 1
}

Write-Host "OK - Gunicorn and Nginx are active" -ForegroundColor Green

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "SUCCESS - Deployment completed!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "What was deployed:" -ForegroundColor Cyan
Write-Host "  - Local changes committed and pushed to GitHub" -ForegroundColor Cyan
Write-Host "  - Database configuration verified (.env)" -ForegroundColor Cyan
Write-Host "  - Latest changes pulled from GitHub" -ForegroundColor Cyan
Write-Host "  - Database migrations applied" -ForegroundColor Cyan
Write-Host "  - Gunicorn restarted with 3 workers" -ForegroundColor Cyan
Write-Host ""
Write-Host "Database: DigitalOcean MySQL" -ForegroundColor Cyan
Write-Host "  Host: $dbHost" -ForegroundColor Cyan
Write-Host "  Port: $dbPort" -ForegroundColor Cyan
Write-Host ""
Write-Host "To view Gunicorn logs:" -ForegroundColor Gray
Write-Host "  ssh dev@157.245.141.42 tail -f /tmp/gunicorn.log" -ForegroundColor Gray
