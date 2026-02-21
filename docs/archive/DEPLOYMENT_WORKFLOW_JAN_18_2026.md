# Deployment Workflow & Member Creation Fix
## January 18, 2026

---

## Summary of Changes

**Commit: 8832663**
- Fixed admin user list to include members

**Commit: 4f9b139**
- Fixed UserCreationForm to include member role in admin choices

**Commit: 25d0806**
- Fixed can_create_user() function to allow administrators to create member users

---

## Issues Resolved

### Problem 1: Member Role Missing from Admin Dropdown
**File:** `accounts/views.py` (can_create_user function)
- Admins could not create member users due to permission check
- Function only allowed: `['technician', 'manager']`
- **Fix:** Added `'member'` to allowed roles

### Problem 2: Member Role Not in Form Choices
**File:** `accounts/forms.py` (UserCreationForm.__init__)
- Form was filtering out member role for administrators
- Only showed Technician and Manager options
- **Fix:** Added `('member', 'Member (Financial Advisor)')` to admin choices

### Problem 3: Created Members Not Displaying in List
**File:** `accounts/views.py` (manage_users view)
- Admin user list query only fetched: `['technician', 'manager']`
- Created members were invisible to admins
- **Fix:** Added `'member'` to user list filter

---

## Simplified Deployment Workflow

**CRITICAL FIX:** Previous deployment commands used complex SSH with `nohup`, `&`, `sleep` which caused terminal hanging and required Ctrl+C.

### New Simplified Workflow (3 Separate Steps)

#### Step 1: Commit & Push Locally
```bash
cd c:\Users\ProFed\workspace\advisor-portal-app
git add <modified_files>
git commit -m "Your message"
git push origin main
```

#### Step 2: Pull on Remote (Simple SSH - No Hanging)
```bash
ssh dev@157.245.141.42 "cd /var/www/advisor-portal && git pull origin main"
```

#### Step 3: Restart Gunicorn (If Needed)
```bash
# Kill existing gunicorn
ssh dev@157.245.141.42 "pkill -f gunicorn"

# Start fresh instance
ssh dev@157.245.141.42 "cd /var/www/advisor-portal && source venv/bin/activate && /home/dev/advisor-portal-app/venv/bin/gunicorn --workers 3 --bind unix:/home/dev/advisor-portal-app/gunicorn.sock --umask 0000 config.wsgi:application &"
```

### Key Principles
- ✅ Use separate SSH commands (don't chain complex commands)
- ✅ Simple `git pull` without background process management
- ✅ Simple `pkill` to stop processes
- ✅ Straightforward gunicorn startup
- ❌ DO NOT use: `nohup`, `sleep`, complex piping in SSH commands

---

## Testing Results (January 18, 2026)

✅ **Member Creation Workflow Verified:**
1. Admin logs into test server (admin/test)
2. Navigates to Manage Users
3. Member (Financial Advisor) option now appears in role dropdown
4. Successfully creates new member user
5. Newly created member appears in user list immediately

✅ **Gunicorn Restart with Simplified Workflow:**
- No terminal hanging
- No need for Ctrl+C interruption
- Clean process termination and startup

---

## Remote Deployment Status

**Test Server:** test-reports.profeds.com (157.245.141.42)
**Current Commit:** 8832663
**Database:** SQLite migrated and functional
**Gunicorn:** Running with 3 workers on unix socket
**Status:** ✅ All fixes deployed and verified

---

## Code Changes Made

### accounts/views.py
```python
# can_create_user() function - Line 29-50
def can_create_user(current_user, target_role):
    """Allow administrators to create technicians, managers, AND members"""
    if current_user.role == 'administrator':
        return target_role in ['technician', 'manager', 'member']  # Added 'member'
    # ... rest of function

# manage_users view - Line 117-125
if current_user.role == 'administrator':
    users = User.objects.filter(
        role__in=['technician', 'manager', 'member']  # Added 'member'
    ).order_by('-created_at')
```

### accounts/forms.py
```python
# UserCreationForm.__init__() - Line 88-105
if current_user.role == 'administrator':
    self.fields['role'].choices = [
        ('technician', 'Technician'),
        ('manager', 'Manager'),
        ('member', 'Member (Financial Advisor)'),  # Added
    ]
```

---

## Lessons Learned

1. **Permission Checks in Multiple Places:** The permission logic was split between `can_create_user()`, the form's `__init__`, and the view's user list query. All three needed updating.

2. **Form Filtering vs Backend Checks:** Even with correct backend permissions, the form can silently hide options through its `__init__` method.

3. **SSH Command Complexity:** Complex background process management in SSH commands causes terminal hanging. Simplified approach with separate commands works reliably.

4. **Testing Workflow:** Created member functionality was broken at three different layers - permission check, form choices, and list visibility. Each fix needed independent verification.

---

**Documentation Created:** January 18, 2026, 18:38 UTC  
**Deployment Verified:** All fixes deployed and tested on remote test server
