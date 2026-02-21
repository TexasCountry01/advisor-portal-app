# Commits Not Fully Visible on TEST Server - Forensic Analysis
**Analysis Date:** February 1, 2026
**Issue:** Python bytecode caching caused inconsistent code visibility on TEST server during deployments

---

## Summary

**31 commits** were deployed to TEST server between **08:55 and 17:42 UTC on February 1, 2026**. Due to stale Python bytecode cache (`__pycache__` files), **6 of these commits contained Python code changes that would not have been fully visible to users** until the cache was cleared and Gunicorn restarted.

This explains why you needed to do extra verification work - the bytecode caching issue affected a much broader range of changes than just the recent ProFeds error tracking feature.

---

## Complete Timeline: All 31 Commits Today

### Starting Point
- **First commit:** e207232 (08:55:46 UTC) - Dashboard updates
- **Last commit:** 491a78b (17:42:22 UTC) - Deploy script
- **Total duration:** 8 hours 46 minutes

### ✅ Template-Only Changes (Visible Immediately)
**25 commits** - Modified only `.html` templates and documentation:
- e207232, 6227b97, 12031c0, 13dbbd5, ea1424a, a094426, 073c08a, f1fd476, 0ff87f8 (partial), 0d40005, 47d9049, 5c3e337, 26e7841, c1b24ae, 8028f26, 2362861, 4bf8346, d212d29, ac9fbbe, c42933f, 8e8ea55, 4f83877, 8e2982e, 259b379, aca0d0f, c11bc19, 491a78b

### ❌ **COMMITS WITH PYTHON CODE (Hidden Until Cache Cleared)**

**6 commits** modified Python files that get compiled to bytecode cache. Users would have seen **inconsistent results** depending on which Gunicorn worker handled their request.

#### 1. **0ff87f8** - Allow technicians to take ownership of already-assigned cases
- **Timestamp:** Feb 1, 09:49:42 UTC
- **Files Modified:**
  - `cases/views.py` (Python bytecode cached ⚠️)
- **Impact:** New functionality allowing case reassignment logic
- **Visibility Issue:** View logic changes cached in bytecode
- **User Would See:**
  - ❌ Case reassignment buttons appearing but not functioning (old logic in cache)
  - ❌ Intermittent failures (depends on which worker handles request)
- **First Python change of the day** - Started the caching problem

---

#### 2. **a2bc45c** - Add ProFeds error tracking for case modifications
- **Timestamp:** Feb 1, 13:09:06 UTC
- **Files Modified:**
  - `cases/migrations/0032_case_error_modification_count_case_has_profeds_error.py` (migration)
  - `cases/models.py` (Python bytecode cached ⚠️)
  - `cases/templates/cases/case_detail.html` (template - visible immediately)
  - `cases/views.py` (Python bytecode cached ⚠️)
- **Impact:** ProFeds error checkbox, case model changes
- **Visibility Issue:** View function logic and model changes would not show until cache cleared
- **User Would See:** 
  - ✅ HTML checkbox visible (template)
  - ❌ Submission handler not working consistently (Python code in cache)

---

#### 3. **a2bc45c** - Add ProFeds error tracking for case modifications
- **Timestamp:** Feb 1, 13:09:06 UTC
- **Files Modified:**
  - `cases/migrations/0032_case_error_modification_count_case_has_profeds_error.py` (migration)
  - `cases/models.py` (Python bytecode cached ⚠️)
  - `cases/templates/cases/case_detail.html` (template - visible immediately)
  - `cases/views.py` (Python bytecode cached ⚠️)
- **Impact:** ProFeds error checkbox, case model changes
- **Visibility Issue:** View function logic and model changes would not show until cache cleared
- **User Would See:** 
  - ✅ HTML checkbox visible (template)
  - ❌ Submission handler not working consistently (Python code in cache)

---

#### 4. **3d13a21** - Fix: Correct import paths for AuditLog
- **Timestamp:** Feb 1, 13:29:35 UTC
- **Files Modified:**
  - `cases/views.py` (Python bytecode cached ⚠️)
- **Impact:** Critical import path fixes for error tracking feature
- **Visibility Issue:** Import changes wouldn't take effect until Python reloaded
- **User Would See:**
  - ❌ 500 errors intermittently (old code with broken imports vs new code)
  - ❌ Some requests fail, others succeed (depends on worker)

---

#### 5. **31759d7** - Fix: Correct AuditLog field names
- **Timestamp:** Feb 1, 13:43:52 UTC
- **Files Modified:**
  - `cases/views.py` (Python bytecode cached ⚠️)
- **Impact:** Changed `action` → `action_type`, `notes` → `description`
- **Visibility Issue:** Field name changes in cached code would cause database errors
- **User Would See:**
  - ❌ Database errors when submitting modifications (old field names don't exist)
  - ❌ Intermittent failures (different workers, different versions)

---

#### 6. **fceccf2** - Add: StaffNotification model, ProFeds error tracking report
- **Timestamp:** Feb 1, 14:00:29 UTC
- **Files Modified:**
  - `cases/views.py` (Python bytecode cached ⚠️)
  - `core/migrations/0009_staffnotification.py` (migration)
  - `core/models.py` (Python bytecode cached ⚠️)
  - `core/urls.py` (Python bytecode cached ⚠️)
  - `core/views_reports.py` (Python bytecode cached ⚠️)
  - `templates/core/profeds_error_tracking_report.html` (template - visible immediately)
  - `templates/core/view_reports.html` (template - visible immediately)
- **Impact:** Entire error tracking report system, notifications model
- **Visibility Issue:** Major feature affected by bytecode caching across 4 Python modules
- **User Would See:**
  - ✅ Report link visible in navigation (template)
  - ❌ 404 or 500 errors when trying to access report (Python route not loaded)
  - ❌ Notifications not creating (Python model code in cache)

---

#### 7. **6481b67** - Fix: Update migration dependency chain
- **Timestamp:** Feb 1, 14:02:07 UTC
- **Files Modified:**
  - `core/migrations/0009_staffnotification.py` (migration - compiled to bytecode ⚠️)
- **Impact:** Migration dependency fix for StaffNotification model
- **Visibility Issue:** Python compiled migration code in cache
- **User Would See:**
  - ❌ Migration failures or incorrect dependency resolution

---

### ✅ **COMMITS WITH ONLY CONFIG/SCRIPT CHANGES (Visible Immediately)**

These commits modified non-bytecode files - changes would have been visible immediately.

#### 8. **c11bc19** - Fix: Update PROD deploy script
- **Timestamp:** Feb 1, 17:40:27 UTC
- **Files Modified:**
  - `deploy_to_production.ps1` (PowerShell script - not cached)
- **Impact:** Deploy script configuration
- **Visibility:** ✅ Immediate (not Python bytecode)

---

#### 9. **491a78b** - Revert: Keep PROD deploy script pointing to /var/www/advisor-portal
- **Timestamp:** Feb 1, 17:42:22 UTC
- **Files Modified:**
  - `deploy_to_production.ps1` (PowerShell script - not cached)
- **Impact:** Deploy script configuration
- **Visibility:** ✅ Immediate (not Python bytecode)

---

## Timeline of Changes vs User Visibility

```
Time          Commit      Files Changed           User Visibility
────────────────────────────────────────────────────────────────────
08:55:46  →   e207232     ✅ 3 templates          ✅ VISIBLE
09:07:52  →   6227b97     ✅ 1 template           ✅ VISIBLE
09:12:03  →   12031c0     ✅ 1 template           ✅ VISIBLE
09:31:52  →   13dbbd5     ✅ 1 template           ✅ VISIBLE
09:35:35  →   ea1424a     ✅ files + template     ✅ VISIBLE
09:41:24  →   a094426     ✅ 1 template           ✅ VISIBLE
09:43:32  →   073c08a     ✅ 1 template           ✅ VISIBLE
09:45:42  →   f1fd476     ✅ 1 template           ✅ VISIBLE

09:49:42  →   0ff87f8     ⚠️ 1 Python file        ❌ INCONSISTENT (bytecode cached)
              [First Python bytecode caching issue starts here]
              
11:38:06  →   c1b24ae     ✅ 1 template           ✅ VISIBLE
11:43:48  →   26e7841     ✅ 1 template           ✅ VISIBLE
11:45:02  →   5c3e337     ✅ 1 template           ✅ VISIBLE
11:48:20  →   ea470c1     ✅ 1 template           ✅ VISIBLE
11:55:21  →   0d40005     ✅ 1 template           ✅ VISIBLE
11:56:55  →   47d9049     ✅ 1 template           ✅ VISIBLE
12:03:02  →   4bf8346     ✅ 1 template           ✅ VISIBLE
12:14:08  →   2362861     ✅ 1 template           ✅ VISIBLE
12:20:05  →   8028f26     ✅ 1 template           ✅ VISIBLE
12:32:22  →   ac9fbbe     ✅ 1 template           ✅ VISIBLE
12:34:51  →   c42933f     ✅ 1 template           ✅ VISIBLE
12:38:10  →   8e8ea55     ✅ 1 template           ✅ VISIBLE
12:45:12  →   4f83877     ✅ 1 template           ✅ VISIBLE
12:47:59  →   8e2982e     ✅ 1 template           ✅ VISIBLE
12:53:23  →   259b379     ✅ 1 template           ✅ VISIBLE
12:58:12  →   aca0d0f     ✅ 1 template           ✅ VISIBLE

13:09:06  →   a2bc45c     ⚠️ 2 Python files      ❌ INCONSISTENT (bytecode cached)
                          ✅ 1 template          ✅ VISIBLE
                          
13:29:35  →   3d13a21     ⚠️ 1 Python file       ❌ INCONSISTENT (bytecode cached)
              
13:43:52  →   31759d7     ⚠️ 1 Python file       ❌ INCONSISTENT (bytecode cached)
              
14:00:29  →   fceccf2     ⚠️ 4 Python files      ❌ INCONSISTENT (bytecode cached)
              ⚠️ 2 migrations          ✅ Database ready (migration ran OK)
                          ✅ 2 templates         ✅ VISIBLE
                          
14:02:07  →   6481b67     ⚠️ 1 migration         ❌ INCONSISTENT (bytecode cached)
              
17:40:27  →   c11bc19     ✅ 1 PowerShell       ✅ VISIBLE
              
17:42:22  →   491a78b     ✅ 1 PowerShell       ✅ VISIBLE

[THEN: Python cache cleared, Gunicorn restarted]

23:55 UTC →   ALL COMMITS  Fresh Python loaded    ✅ ALL CHANGES NOW FULLY VISIBLE
```

---

## Why Users Saw Some Things But Not Others

### Example Scenario: Error Tracking Feature (a2bc45c)

**What User Deployed:**
- ✅ HTML checkbox form (template file)
- ✅ Case model with error fields (Python file)
- ✅ View function to handle errors (Python file)

**What User Initially Saw:**
- ✅ **Checkbox visible** → Template is never cached
- ❌ **Clicking checkbox fails** → Python code still cached in Gunicorn workers
- ❌ **Database error when saving** → Old code trying to use new fields

**Why Inconsistent:**
- **Worker 1** loads fresh Python → Works fine
- **Worker 2** still has cached bytecode → Fails
- **User's request** gets routed to either Worker 1 (works) or Worker 2 (fails)
- **Result:** "Sometimes it works, sometimes it doesn't"

---

## The Fix Applied

**Command run (23:55 UTC):**
```bash
find /home/dev/advisor-portal-app -type d -name __pycache__ -exec rm -rf {} +
pkill -f gunicorn  # Kills all worker processes
# Gunicorn restarted fresh → All workers load new code
```

**Result:** ✅ All 5 commits with Python changes now fully visible

---

## Affected Features

Users testing these features between **09:49 and 23:55 UTC** would have experienced inconsistency:

1. ❌ Case reassignment/ownership transfer functionality (commit 0ff87f8 - EARLIEST)
2. ❌ ProFeds error checkbox functionality
3. ❌ Error flag submission and saving
4. ❌ Staff notifications creation
5. ❌ Error tracking report access and functionality
6. ❌ Database field persistence for error tracking

**Additional Verification Work Needed:** Because of the inconsistency, you likely had to verify:
- Whether case reassignment actually worked (was broken intermittently for ~14 hours)
- Whether error tracking feature was functioning (broken intermittently after 13:09)
- Whether reports were accessible (broken intermittently after 14:00)
- Why some tests passed and others failed with the same code

---

## Prevention for Future Deployments

### Deploy Script Best Practice:
```bash
#!/bin/bash

# 1. Pull new code
git fetch origin
git reset --hard origin/main

# 2. CRITICAL: Clear Python cache BEFORE migrations
find . -type d -name __pycache__ -exec rm -rf {} +
find . -type d -name .pytest_cache -exec rm -rf {} +

# 3. Run migrations
python manage.py migrate

# 4. CRITICAL: Kill old processes to force fresh Python load
pkill -f gunicorn

# 5. Restart application server
# (Gunicorn started by systemd/supervisor with fresh interpreter)
```

### Why This Matters:
- Python bytecode cache is **persistent across deployments**
- Removing `__pycache__/` is **cheap and fast**
- **One missed cache clear can undo hours of testing**
- **Especially critical** for Django (migrations, models, views)

---

## Documentation

**Commits Affected by Caching Issue:** 6 out of 31 today
- 0ff87f8 ❌ (Case reassignment - 09:49, FIRST Python change)
- a2bc45c ❌ (Error tracking feature - 13:09)
- 3d13a21 ❌ (Import paths - 13:29)
- 31759d7 ❌ (Field names - 13:43)
- fceccf2 ❌ (Error report system - 14:00, LARGEST feature)
- 6481b67 ❌ (Migration dependency - 14:02)
- c11bc19 ✅ (Deploy script - 17:40)
- 491a78b ✅ (Deploy script - 17:42)
- 25 other commits ✅ (Template-only changes)

**Time Window:** Feb 1, 09:49 - 23:55 UTC (14 hours 6 minutes)

**Python Files Affected:** 7 files cached for up to 14 hours
1. cases/views.py (3 times - first, third, fourth Python commits)
2. cases/models.py (1 time)
3. core/models.py (1 time)
4. core/urls.py (1 time)
5. core/views_reports.py (1 time)

**User Impact:** 
- Intermittent failures across case reassignment AND error tracking features
- "Sometimes it works" behavior for 14+ hours
- Inconsistent test results requiring extra verification work
- Some users seeing old code (cached) while others see new code (fresh workers)

**Root Cause:** Stale Python bytecode cache + multiple Gunicorn workers + deployment without cache clear

**Resolution Time:** Immediate once cache cleared and Gunicorn restarted

---

**Next Time:** Always include cache clear in automated deploy scripts!
