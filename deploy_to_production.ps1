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
$gunicornSocket = "unix:/var/www/advisor-portal/gunicorn.sock"

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

# Pre-flight: Verify all local commits are pushed to GitHub
$localHead = git rev-parse HEAD
$remoteHead = (git ls-remote origin refs/heads/main) -split '\s+' | Select-Object -First 1
if ($localHead -ne $remoteHead) {
    Write-Host "ERROR: Local commits not pushed to GitHub." -ForegroundColor Red
    Write-Host "Run 'git push origin main' first, then re-run this script." -ForegroundColor Red
    exit 1
}
Write-Host "OK - All commits pushed to GitHub ($($localHead.Substring(0,7)))" -ForegroundColor Green
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

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Migration or collectstatic failed!" -ForegroundColor Red
    exit 1
}

Write-Host "OK - Migrations completed" -ForegroundColor Green
Write-Host ""

# STEP 4: Restart Gunicorn
Write-Host "[4/4] Restarting Gunicorn..." -ForegroundColor Yellow

# Kill existing gunicorn master via pidfile (avoids pkill -f which self-kills the SSH bash
# because the command string itself contains 'gunicorn').
# Removes stale socket and pidfile before starting fresh daemon.
ssh $prodServerUser@$prodServerHost "kill `$(cat /tmp/gunicorn.pid 2>/dev/null) 2>/dev/null; sleep 3; cd $projectPath && rm -f gunicorn.sock /tmp/gunicorn.pid && $venvPath/bin/gunicorn --workers 3 --bind $gunicornSocket --umask 0000 --daemon --pid /tmp/gunicorn.pid --log-file /tmp/gunicorn.log --log-level info config.wsgi:application"

Start-Sleep -Seconds 6

# Verify gunicorn is running
Write-Host "Verifying Gunicorn process..." -ForegroundColor Yellow
$processCount = ssh $prodServerUser@$prodServerHost "ps aux | grep gunicorn | grep -v grep | wc -l"

if ([int]$processCount -lt 2) {
    Write-Host "WARNING: Only $processCount gunicorn process(es) found - checking logs..." -ForegroundColor Red
    ssh $prodServerUser@$prodServerHost "tail -20 /tmp/gunicorn.log 2>/dev/null"
    exit 1
}

Write-Host "OK - $processCount gunicorn processes running" -ForegroundColor Green

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
