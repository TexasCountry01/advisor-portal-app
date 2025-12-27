#!/usr/bin/env pwsh
param(
    [string]$Password = "ForTheLoveOfJesus0a"
)

$Server = "dev@157.245.141.42"

Write-Host "=== Updating Nginx Configuration ===" -ForegroundColor Green

# Update Nginx
$nginxCmd = @"
cat /tmp/nginx-new.conf | sudo -S tee /etc/nginx/sites-available/advisor-portal > /dev/null
sudo -S nginx -t
sudo -S systemctl restart nginx
echo '✓ Nginx updated and restarted'
"@

$nginxCmd | ssh $Server -o "StrictHostKeyChecking no" "bash -s" 2>&1 <<< $Password

Write-Host ""
Write-Host "=== Updating Gunicorn Configuration ===" -ForegroundColor Green

# Update Gunicorn
$gunicornCmd = @"
cat /tmp/gunicorn-new.service | sudo -S tee /etc/systemd/system/gunicorn.service > /dev/null
sudo -S systemctl daemon-reload
sudo -S systemctl restart gunicorn
echo '✓ Gunicorn updated and restarted'
"@

$gunicornCmd | ssh $Server -o "StrictHostKeyChecking no" "bash -s" 2>&1 <<< $Password

Write-Host ""
Write-Host "=== Verifying Configuration ===" -ForegroundColor Green

ssh $Server "echo '✓ Gunicorn WorkingDirectory:' && grep WorkingDirectory /etc/systemd/system/gunicorn.service && echo '' && echo '✓ Nginx socket path:' && grep proxy_pass /etc/nginx/sites-available/advisor-portal && echo '' && echo '✓ Static files location:' && grep 'alias.*static' /etc/nginx/sites-available/advisor-portal"

Write-Host ""
Write-Host "=== Complete! ===" -ForegroundColor Green
