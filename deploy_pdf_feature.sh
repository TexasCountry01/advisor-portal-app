#!/bin/bash
# Deployment script for Federal Fact Finder PDF feature
# Deploy to: test-reports.profeds.com (157.245.141.42)
# Usage: ./deploy_pdf_feature.sh

set -e  # Exit on any error

echo "=================================================="
echo "Federal Fact Finder PDF - Deployment Script"
echo "=================================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration
APP_DIR="/home/dev/advisor-portal-app"
VENV_PATH="$APP_DIR/venv/bin/activate"
SERVICE_NAME="gunicorn"  # Adjust if using different service name

echo -e "${YELLOW}Step 1: Pulling latest code from GitHub...${NC}"
cd $APP_DIR
git pull origin main
echo -e "${GREEN}✓ Code updated${NC}"
echo ""

echo -e "${YELLOW}Step 2: Installing WeasyPrint system dependencies...${NC}"
echo "This may require sudo password..."
sudo apt-get update -qq
sudo apt-get install -y \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    shared-mime-info \
    2>&1 | grep -v "already the newest version" || true
echo -e "${GREEN}✓ System dependencies installed${NC}"
echo ""

echo -e "${YELLOW}Step 3: Activating virtual environment...${NC}"
source $VENV_PATH
echo -e "${GREEN}✓ Virtual environment activated${NC}"
echo ""

echo -e "${YELLOW}Step 4: Installing Python packages...${NC}"
pip install WeasyPrint==60.2 -q
echo -e "${GREEN}✓ WeasyPrint installed${NC}"
echo ""

echo -e "${YELLOW}Step 5: Running database migrations...${NC}"
python manage.py migrate
echo -e "${GREEN}✓ Database migrations applied${NC}"
echo ""

echo -e "${YELLOW}Step 6: Collecting static files...${NC}"
python manage.py collectstatic --noinput -v 0
echo -e "${GREEN}✓ Static files collected${NC}"
echo ""

echo -e "${YELLOW}Step 7: Testing WeasyPrint installation...${NC}"
python -c "from weasyprint import HTML; print('WeasyPrint: OK')"
echo -e "${GREEN}✓ WeasyPrint working${NC}"
echo ""

echo -e "${YELLOW}Step 8: Restarting application server...${NC}"
if systemctl is-active --quiet $SERVICE_NAME; then
    sudo systemctl restart $SERVICE_NAME
    echo -e "${GREEN}✓ $SERVICE_NAME restarted${NC}"
else
    echo -e "${RED}⚠ $SERVICE_NAME not running as systemd service${NC}"
    echo "You may need to restart manually:"
    echo "  sudo systemctl restart $SERVICE_NAME"
    echo "  OR"
    echo "  sudo supervisorctl restart advisor-portal"
fi
echo ""

echo -e "${YELLOW}Step 9: Checking service status...${NC}"
if systemctl is-active --quiet $SERVICE_NAME; then
    echo -e "${GREEN}✓ Application is running${NC}"
    systemctl status $SERVICE_NAME --no-pager -l | head -n 10
else
    echo -e "${RED}⚠ Service status unclear - check manually${NC}"
fi
echo ""

echo "=================================================="
echo -e "${GREEN}Deployment Complete!${NC}"
echo "=================================================="
echo ""
echo "Next steps:"
echo "1. Test the application: https://test-reports.profeds.com"
echo "2. Create a test case with Federal Fact Finder data"
echo "3. Verify PDF generation works correctly"
echo "4. Check PDF displays all 6 pages with data"
echo ""
echo "Troubleshooting:"
echo "  - View logs: sudo journalctl -u $SERVICE_NAME -f"
echo "  - Check processes: ps aux | grep gunicorn"
echo "  - Test PDF manually: python manage.py shell"
echo ""
