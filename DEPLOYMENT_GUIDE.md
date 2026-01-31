# Quick Deployment Guide - UI/UX Enhancements

## For TEST Server (157.245.141.42)

### Prerequisites
- SSH access to TEST server
- Git access configured
- Python virtual environment active

---

## Step-by-Step Deployment

### 1. SSH to TEST Server
```bash
ssh root@157.245.141.42
cd /home/dev/advisor-portal-app
```

### 2. Pull Latest Code
```bash
git pull origin main
```

### 3. Verify Changes Were Pulled
```bash
git log --oneline -5
```
You should see the new commits with UI/UX changes.

### 4. Activate Virtual Environment
```bash
source venv/bin/activate
```

### 5. Run Database Migrations
```bash
python manage.py migrate
```

**Expected Output:**
```
Applying accounts.0005_user_font_size... OK
```

### 6. Verify Migration Success
```bash
python manage.py showmigrations accounts | grep 0005
```

**Expected Output:**
```
 [X] 0005_user_font_size
```

### 7. Restart Gunicorn
```bash
sudo systemctl restart gunicorn
```

### 8. Verify Gunicorn Status
```bash
sudo systemctl status gunicorn
```

**Expected Output:**
```
● gunicorn.service - Gunicorn application server
   Loaded: loaded (/etc/systemd/system/gunicorn.service; enabled; vendor preset: enabled)
   Active: active (running)
```

### 9. Check Nginx Status (Should be automatic)
```bash
sudo systemctl status nginx
```

---

## Testing After Deployment

### Test Font Size Feature
1. Go to: `https://test-reports.profeds.com/profile/`
2. Scroll to "Preferences" section
3. Change font size from dropdown (try 75%, 130%, 150%)
4. Verify text size changes immediately
5. Refresh page - size should persist

### Test Sticky Navbar
1. Go to any dashboard (e.g., Member Dashboard)
2. Scroll down through the case table
3. Verify navbar stays at top
4. Verify you can still click navigation items while scrolled

### Test Sortable Columns
1. Go to any dashboard
2. Click on column headers
3. Verify data sorts ascending
4. Click again - should sort descending
5. Test on different columns

### Test Footer
1. Scroll to bottom of any page
2. Verify footer says: "© ProFeds. All rights reserved."

---

## Verification Checklist

- [ ] Migration applied successfully
- [ ] Gunicorn restarted
- [ ] Profile page shows "Preferences" card
- [ ] Font size dropdown works (all 6 sizes)
- [ ] Navbar stays sticky when scrolling
- [ ] Column headers are sortable
- [ ] Footer shows correct copyright text
- [ ] No error messages in browser console
- [ ] No error messages in Gunicorn logs

---

## Rollback Instructions (If Needed)

### Rollback Last Deployment
```bash
cd /home/dev/advisor-portal-app
git reset --hard HEAD~1
python manage.py migrate accounts 0004_workshopdelegate
sudo systemctl restart gunicorn
```

### Check Gunicorn Logs for Errors
```bash
sudo journalctl -u gunicorn -n 50
```

### Check Nginx Logs for Errors
```bash
sudo tail -f /var/log/nginx/error.log
```

---

## Performance Considerations

- **Font Size Feature Impact:** Minimal (single CSS property on body)
- **Sticky Navbar Impact:** Minimal (CSS position: sticky)
- **Sortable Columns Impact:** None (uses existing sorting backend)
- **Database Impact:** One new column, no performance issues
- **Migration Time:** < 1 second
- **Gunicorn Restart Time:** 5-10 seconds
- **Total Downtime:** ~10 seconds

---

## Support Contacts

For issues during or after deployment:
- Check Gunicorn logs: `sudo journalctl -u gunicorn -n 100`
- Check Nginx logs: `sudo tail -f /var/log/nginx/error.log`
- Check Django logs: `cat /var/log/gunicorn/error.log`

---

## Deployment Summary

**Files Modified:** 10  
**Migrations:** 1 (0005_user_font_size)  
**New Features:** 4  
**Risk Level:** LOW  
**Estimated Time:** 5-10 minutes  
**Downtime Required:** ~10 seconds  

---

## After Successful Deployment

1. ✅ Notify team that TEST server has been updated
2. ✅ Provide testing instructions
3. ✅ Collect feedback from testers
4. ✅ Document any issues
5. ✅ Plan PRODUCTION deployment

---

**Deployment Ready:** Yes ✅  
**Date:** 2026-01-31  
**Status:** All changes tested and ready to deploy
