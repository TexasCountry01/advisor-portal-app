#!/bin/bash
# Deployment script to sync test server with local changes

echo "=== Advisor Portal Deployment Script ==="
echo ""

# Configuration
TEST_SERVER="dev@157.245.141.42"
REMOTE_PATH="/home/dev/advisor-portal-app"
REMOTE_WWW_PATH="/var/www/advisor-portal"

echo "1. Pushing code to GitHub..."
git push origin main
if [ $? -ne 0 ]; then
    echo "❌ Git push failed. Aborting deployment."
    exit 1
fi

echo "✓ Code pushed to GitHub"
echo ""

echo "2. Pulling changes on test server..."
ssh $TEST_SERVER "cd $REMOTE_PATH && git pull origin main"
if [ $? -ne 0 ]; then
    echo "❌ Git pull failed on test server."
    exit 1
fi

echo "✓ Code pulled on test server"
echo ""

echo "3. Collecting static files on test server..."
ssh $TEST_SERVER "cd $REMOTE_PATH && source venv/bin/activate && python manage.py collectstatic --noinput --clear 2>&1 | tail -2"

echo "✓ Static files collected"
echo ""

echo "4. Syncing staticfiles to Nginx location..."
ssh $TEST_SERVER "cp -r $REMOTE_PATH/staticfiles/* $REMOTE_WWW_PATH/staticfiles/"

echo "✓ Staticfiles synced"
echo ""

echo "5. Restarting services on test server..."
ssh $TEST_SERVER "sudo -n systemctl restart gunicorn && sudo -n systemctl restart nginx"

echo "✓ Services restarted"
echo ""

echo "=== Deployment Complete! ==="
echo "Test server updated and running:"
echo "  URL: https://test-reports.profeds.com/cases/member/dashboard/"
echo ""
echo "To verify: Check network tab in DevTools for CSS (should be 200)"
