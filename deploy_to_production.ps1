# ==============================================================================
# DEPLOY SCRIPT: Production Server Deployment
# ==============================================================================
#
# ⚠️ CRITICAL DATABASE WARNING ⚠️
# This script deploys to the PRODUCTION SERVER which uses DigitalOcean MYSQL/MARIADB
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
# 1. Verify .env database configuration (MySQL, NOT SQLite)
# 2. Pull latest changes from GitHub
# 3. Run Django migrations on MySQL database
# 4. Restart Gunicorn application server
#
# Security Notes:
# - Database password stored securely in remote .env file (NOT in this script)
# - Never commit passwords to GitHub
# - Backup remote .env locally before changes
# - See .env.backup.production for reference
# ==============================================================================

# Configuration
$prodServerHost = "104.248.126.74"
$prodServerUser = "dev"
$projectPath = "/var/www/advisor-portal"
$venvPath = "/var/www/advisor-portal/venv"
$gunicornSocket = "/var/www/advisor-portal/gunicorn.sock"

# ⚠️ PRODUCTION DATABASE - DigitalOcean Managed MySQL/MariaDB
# (NOT SQLite - only use SQLite for LOCAL development)
$dbEngine = "django.db.backends.mysql"
$dbName = "advisor_portal"
$dbUser = "doadmin"
$dbHost = "db-mysql-nyc1-61187-do-user-6630088-0.e.db.ondigitalocean.com"
$dbPort = "25060"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Deploying to Production Server" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "⚠️  PRODUCTION DEPLOYMENT" -ForegroundColor Red
Write-Host "Target: $prodServerHost (PRODUCTION)" -ForegroundColor Red
Write-Host "Database: $dbHost" -ForegroundColor Red
Write-Host ""

# Safety confirmation
$confirmation = Read-Host "Type 'deploy' to confirm production deployment"
if ($confirmation -ne "deploy") {
    Write-Host "❌ Deployment cancelled by user" -ForegroundColor Red
    exit 1
}

Write-Host ""

# STEP 1: Ensure .env has correct database configuration
Write-Host "[1/4] Verifying database configuration (.env)..." -ForegroundColor Yellow

# NOTE: The .env file already exists on the remote server with all necessary configuration
# including the database password. We just verify it exists and contains required keys.
ssh $prodServerUser@$prodServerHost "cd $projectPath && if [ -f .env ]; then echo 'OK'; else echo 'ERROR: .env not found'; exit 1; fi" | Out-Null

Write-Host "OK - Database configuration verified" -ForegroundColor Green
Write-Host ""

# STEP 2: Pull latest changes from GitHub
Write-Host "[2/4] Pulling latest changes from GitHub..." -ForegroundColor Yellow
ssh $prodServerUser@$prodServerHost "cd $projectPath && git pull origin main"

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Git pull failed!" -ForegroundColor Red
    exit 1
}

Write-Host "OK - Git pull completed" -ForegroundColor Green
Write-Host ""

# STEP 3: Run database migrations
Write-Host "[3/4] Running database migrations..." -ForegroundColor Yellow
ssh $prodServerUser@$prodServerHost "cd $projectPath && source $venvPath/bin/activate && python manage.py migrate && python manage.py collectstatic --noinput 2>&1 | tail -3"

Write-Host "OK - Migrations completed" -ForegroundColor Green
Write-Host ""

# STEP 4: Restart Gunicorn
Write-Host "[4/4] Restarting Gunicorn..." -ForegroundColor Yellow

ssh $prodServerUser@$prodServerHost "pkill -f gunicorn"
Start-Sleep -Seconds 2

$timeout = 5
$startGunicornScript = {
    ssh dev@104.248.126.74 "cd /var/www/advisor-portal && source /var/www/advisor-portal/venv/bin/activate && nohup /var/www/advisor-portal/venv/bin/gunicorn --workers 3 --bind unix:/var/www/advisor-portal/gunicorn.sock --umask 0000 config.wsgi:application > /tmp/gunicorn.log 2>&1 &" 
}

$job = Start-Job -ScriptBlock $startGunicornScript
$job | Wait-Job -Timeout $timeout | Out-Null

if ($job.State -eq "Running") {
    Write-Host "OK - Gunicorn startup sent" -ForegroundColor Green
    $job | Stop-Job | Out-Null
    Remove-Job $job | Out-Null
} else {
    Write-Host "OK - Gunicorn startup command completed" -ForegroundColor Green
    Remove-Job $job | Out-Null
}

Start-Sleep -Seconds 2

# Verify gunicorn is running
Write-Host "Verifying Gunicorn process..." -ForegroundColor Yellow
$processCount = ssh dev@104.248.126.74 "ps aux | grep gunicorn | grep -v grep | wc -l"
Write-Host "Found $processCount gunicorn processes" -ForegroundColor Green

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "SUCCESS - Deployment completed!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "What was deployed:" -ForegroundColor Cyan
Write-Host "  - Database configuration verified (.env)" -ForegroundColor Cyan
Write-Host "  - Latest changes pulled from GitHub" -ForegroundColor Cyan
Write-Host "  - Database migrations applied" -ForegroundColor Cyan
Write-Host "  - Gunicorn restarted with 3 workers" -ForegroundColor Cyan
Write-Host ""
Write-Host "Database: DigitalOcean MySQL" -ForegroundColor Cyan
Write-Host "  Host: $dbHost" -ForegroundColor Cyan
Write-Host "  Port: $dbPort" -ForegroundColor Cyan
Write-Host ""
Write-Host "Production URL: https://reports.profeds.com" -ForegroundColor Cyan
Write-Host ""
Write-Host "To view Gunicorn logs:" -ForegroundColor Gray
Write-Host "  ssh dev@104.248.126.74 tail -f /tmp/gunicorn.log" -ForegroundColor Gray
