# PROD Deployment Synopsis

**Date:** March 27, 2026

## Current State

| Environment | Commit | Status |
|-------------|--------|--------|
| LOCAL | `c6e61bf` | In sync with origin/main ✅ |
| TEST | `c6e61bf` | In sync with origin/main ✅ |
| PROD | `5e26eac` | **DIVERGED** — 2 cherry-picks ahead, 3 commits behind ⚠️ |

## Why PROD Is Diverged

PROD has 2 cherry-picked commits (`5e26eac`, `09474b8`) that duplicate fixes already on `main` under different SHAs (`36ff299`, `ae8dfdf`). A normal `git pull` will **fail or create merge conflicts**. You must hard-reset.

---

## 16 Commits Going to PROD

### 1. Messaging App — Phase 1 (1 commit)
- `fa9c5ba` — General questions for members to staff

### 2. Scheduled Release / Email Fixes (3 commits — content already on PROD via cherry-picks, different SHAs)
- `36ff299` — DateField → DateTimeField for same-day scheduled releases
- `ae8dfdf` — Fix actual_email_sent_date set before send
- `ec7f469` — Fix approve_case_review to store full datetime

### 3. Data Sync Tool (9 commits — completely inert on PROD via `ENABLE_DATA_SYNC=False`)
- `1545d13` — Core sync tool: PROD export + TEST/LOCAL sync panel
- `23d2900` — Data Sync button on admin dashboard toolbar
- `9b7f809` — Fix: serialize SSH calls
- `d7a5b33` — Fix: absolute paths for ssh/scp
- `d7c8bba` — Back to Dashboard link, stats toggle labels
- `9922e66` — Case search feature
- `af85ced` — Fix search input enable
- `324cd89` — Fix JS duplicate catch block
- `c6e61bf` — Auto-select single search result

### 4. Navigation / UI Fixes (3 commits)
- `040ba10` — Status cards CSS + missing stats on case_list
- `355be98` — Dashboard links for admin/manager, case_list redirect
- `373b9eb` — ENABLE_DATA_SYNC feature flag

---

## New Migrations (2)

| Migration | App | Description |
|-----------|-----|-------------|
| `core/0015_add_data_sync_codes.py` | core | Adds `dev_sync_code` and `admin_sync_code` to SystemSettings |
| `messaging/0001_initial.py` | messaging | Creates Conversation, Message, MessageAttachment tables |

---

## PROD .env — No Changes Needed

`ENABLE_DATA_SYNC` is **not** in PROD's `.env` and defaults to `False` in settings.py. The data sync tool (URLs, button, views) will be completely hidden/inert. Safe.

PROD already has `export_data.py` management command (SCP'd directly earlier) — this was the read-only half of the sync tool.

---

## Deployment Steps

```bash
# SSH to PROD
ssh dev@104.248.126.74

cd /var/www/advisor-portal

# 1. Hard-reset to match origin/main (required due to cherry-pick divergence)
git fetch origin
git reset --hard origin/main

# 2. Install any new dependencies
source venv/bin/activate
pip install -r requirements.txt

# 3. Run migrations
python manage.py migrate

# 4. Collect static files
python manage.py collectstatic --noinput

# 5. Restart Gunicorn
pkill -HUP -f 'gunicorn.*config.wsgi'
```

---

## Post-Deployment Verification Checklist

- [ ] Admin dashboard loads, navbar "Dashboard" links to admin_dashboard (not Django /admin/)
- [ ] Manager dashboard loads, navbar shows correct links
- [ ] Member can see "General Questions" messaging in navbar
- [ ] Scheduled release still works (datetime fix already live via cherry-pick, just new SHAs now)
- [ ] Data Sync button is **NOT** visible on admin dashboard (feature flag off)
- [ ] SSO login still enforces 3-gate check (allowlist, tags, active status)
- [ ] Status cards on case list display correctly with stats

---

## Risk Assessment

| Risk | Mitigation |
|------|-----------|
| `git reset --hard` loses cherry-picks | Same fixes exist on main under different SHAs — no code loss |
| Data sync tool accidentally enabled | Feature flag defaults False, PROD .env has no override |
| Messaging migration fails | No conflicting tables — fresh app, first migration |
| Static files missing | `collectstatic` step handles this |

---

## Branches

Cleaned up — only `main` and `remotes/origin/main` remain. No stale branches.
