#!/bin/bash
# Update test server config with password

PASSWORD="ForTheLoveOfJesus0a"
SERVER="dev@157.245.141.42"

echo "=== Updating Nginx Configuration ==="
ssh $SERVER << 'BASH_SCRIPT'
cat /tmp/nginx-new.conf | sudo -S tee /etc/nginx/sites-available/advisor-portal > /dev/null
sudo -S nginx -t
sudo -S systemctl restart nginx
echo "✓ Nginx updated and restarted"
BASH_SCRIPT

echo ""
echo "=== Updating Gunicorn Configuration ==="
ssh $SERVER << 'BASH_SCRIPT'
cat /tmp/gunicorn-new.service | sudo -S tee /etc/systemd/system/gunicorn.service > /dev/null
sudo -S systemctl daemon-reload
sudo -S systemctl restart gunicorn
echo "✓ Gunicorn updated and restarted"
BASH_SCRIPT

echo ""
echo "=== Verifying Configuration ==="
ssh $SERVER << 'BASH_SCRIPT'
echo "Gunicorn WorkingDirectory:"
grep WorkingDirectory /etc/systemd/system/gunicorn.service
echo ""
echo "Nginx socket path:"
grep proxy_pass /etc/nginx/sites-available/advisor-portal
echo ""
echo "Static files location:"
grep 'alias.*static' /etc/nginx/sites-available/advisor-portal
BASH_SCRIPT

echo ""
echo "✓ Complete!"
