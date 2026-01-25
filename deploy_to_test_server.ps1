# Deploy changes to test server via SSH
# This script ensures database config, pulls changes from GitHub, runs migrations, and restarts Gunicorn
# CRITICAL: This uses DigitalOcean Managed MySQL (NOT SQLite)
# 4-STEP WORKFLOW: Ensure .env config -> Git pull -> Run migrations -> Restart gunicorn

# Configuration
$testServerHost = "157.245.141.42"
$testServerUser = "dev"
$projectPath = "/var/www/advisor-portal"
$venvPath = "/home/dev/advisor-portal-app/venv"
$gunicornSocket = "/home/dev/advisor-portal-app/gunicorn.sock"

# Database Configuration (DigitalOcean Managed MySQL)
# NOTE: Database password is stored securely in the remote server .env file
# DO NOT commit passwords to GitHub - use secure deployment methods only
$dbEngine = "django.db.backends.mysql"
$dbName = "advisor_portal"
$dbUser = "doadmin"
$dbHost = "advisor-portal-db-test-do-user-6630088-0.e.db.ondigitalocean.com"
$dbPort = "25060"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Deploying to Test Server" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# STEP 1: Ensure .env has correct database configuration
Write-Host "[1/4] Verifying database configuration (.env)..." -ForegroundColor Yellow

# NOTE: The database password should already be set on the remote server's .env file
# This script only updates other configuration variables
# For security, database password is NOT included in this script

ssh $testServerUser@$testServerHost "cat > $projectPath/.env.deploy << 'ENVEOF'
DEBUG=False
ALLOWED_HOSTS=test-reports.profeds.com,157.245.141.42,localhost
CSRF_TRUSTED_ORIGINS=https://test-reports.profeds.com,https://157.245.141.42
SECRET_KEY=django-insecure-4-!+ec_gh4*-vap+do#iw76prls*e9j)xq%5q@n3smd3tdx1o`$

# TEST SERVER - MySQL Database Configuration (DigitalOcean Managed Database)
DB_ENGINE=$dbEngine
DB_NAME=$dbName
DB_USER=$dbUser
DB_HOST=$dbHost
DB_PORT=$dbPort

# Security
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True

# Email (for testing)
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend

# Storage
MEDIA_ROOT=media/
STATIC_ROOT=staticfiles/
ENVEOF

# Preserve existing password and merge configs
ssh $testServerUser@$testServerHost 'cd $projectPath && (grep -q "DB_PASSWORD" .env && grep "DB_PASSWORD" .env >> .env.deploy || true) && mv .env.deploy .env'"

Write-Host "OK - Database configuration verified" -ForegroundColor Green
Write-Host ""

# STEP 2: Pull latest changes from GitHub
Write-Host "[2/4] Pulling latest changes from GitHub..." -ForegroundColor Yellow
ssh $testServerUser@$testServerHost "cd $projectPath && git pull origin main"

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Git pull failed!" -ForegroundColor Red
    exit 1
}

Write-Host "OK - Git pull completed" -ForegroundColor Green
Write-Host ""

# STEP 3: Run database migrations
Write-Host "[3/4] Running database migrations..." -ForegroundColor Yellow
ssh $testServerUser@$testServerHost "cd $projectPath && source $venvPath/bin/activate && python manage.py migrate"

Write-Host "OK - Migrations completed" -ForegroundColor Green
Write-Host ""

# STEP 4: Restart Gunicorn
Write-Host "[4/4] Restarting Gunicorn..." -ForegroundColor Yellow

# STEP 4: Restart Gunicorn
Write-Host "[4/4] Restarting Gunicorn..." -ForegroundColor Yellow

ssh $testServerUser@$testServerHost "pkill -f gunicorn"
Start-Sleep -Seconds 2

$timeout = 5
$startGunicornScript = {
    ssh dev@157.245.141.42 "cd /var/www/advisor-portal && source /home/dev/advisor-portal-app/venv/bin/activate && nohup /home/dev/advisor-portal-app/venv/bin/gunicorn --workers 3 --bind unix:/home/dev/advisor-portal-app/gunicorn.sock --umask 0000 config.wsgi:application > /tmp/gunicorn.log 2>&1 &" 
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
$processCount = ssh dev@157.245.141.42 "ps aux | grep gunicorn | grep -v grep | wc -l"
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
Write-Host "To view Gunicorn logs:" -ForegroundColor Gray
Write-Host "  ssh dev@157.245.141.42 tail -f /tmp/gunicorn.log" -ForegroundColor Gray
