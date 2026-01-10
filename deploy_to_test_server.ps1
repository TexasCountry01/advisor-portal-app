# Deploy changes to test server via SSH
# This script pulls the latest changes from GitHub and restarts the Django server

$testServerHost = "your-test-server-host"  # Replace with actual test server hostname/IP
$testServerUser = "your-username"           # Replace with SSH username
$projectPath = "/path/to/advisor-portal-app" # Replace with actual project path on test server

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Deploying to Test Server" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# SSH command to pull latest changes
$sshCommand = @"
cd $projectPath && `
git fetch origin && `
git pull origin main && `
echo 'Git pull completed' && `
source venv/bin/activate 2>/dev/null || . venv/Scripts/Activate.ps1 && `
pip install -r requirements.txt && `
python manage.py migrate && `
python manage.py collectstatic --noinput && `
echo 'Deployment completed successfully'
"@

Write-Host "Connecting to test server: $testServerHost" -ForegroundColor Yellow
Write-Host "Pulling latest changes from GitHub..." -ForegroundColor Yellow
Write-Host ""

# Execute SSH command
ssh $testServerUser@$testServerHost $sshCommand

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "✓ Deployment to test server successful!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "Changes have been deployed and server has been updated." -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Red
    Write-Host "✗ Deployment failed!" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
    Write-Host "Exit code: $LASTEXITCODE" -ForegroundColor Red
}
