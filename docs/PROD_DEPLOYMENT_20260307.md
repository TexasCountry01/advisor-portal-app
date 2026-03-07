# PROD Deployment — March 7, 2026

## Status: DEPLOYED SUCCESSFULLY

---

## Git Sync Verification

| Environment | Branch | Commit | Status |
|---|---|---|---|
| LOCAL | main | 0ed71b5 | Clean — nothing to commit |
| TEST | main | 0ed71b5 | Clean (1 untracked: server_activity_report.py) |
| PROD | main | a24f4c8 | Clean (1 untracked: .env.deploy, 1 modified: FactFinder.pdf via SCP) |
| origin | main | 0ed71b5 | — |

LOCAL and TEST are in sync at commit 0ed71b5.
PROD is 38 commits behind at a24f4c8.

---

## Commits to Deploy (38 total, oldest first)

```
17f2975 SSO infrastructure, MemberDelegate model, dashboard toggle, delegate case submission
7b0b57a Add delegate infrastructure, webhook, tests, and deprecation cleanup
af5be07 Wire real WP resource endpoint field mappings into SSO
453e13c Add load_test_users command with 27 real GHL contacts and delegate assignments
a899f9d Add set_test_passwords + smoketest commands
80c1bca Fix case-insensitive tag matching + add SSO debug logging
2f72331 Add LOGGING config so SSO debug logs reach gunicorn journal
1b94eb8 Fix LOGIN_REDIRECT_URL: /dashboard/ -> / (home view handles role routing)
ee7a2e7 Auto-redirect unauthenticated users to SSO from home page
d6c505a Add SSO role protection + SSOAllowedEmail model + admin panel
5536ca0 Add Edit User Role feature for administrators
a9fafae Add admin dashboard preview for member/technician/manager views
a31b42d Fix logout redirect: send users to login page instead of WP OAuth
fd6f3ea Fix SSO name sync: title-case names from WP payload
40a41f2 Fix: home page now shows login form instead of bypassing to SSO
331f424 Fix: force WP login form on SSO + add switch account link
d724311 Remove credential form from login page, add admin SSO tag bypass
f943ecb Fix: Switch WordPress account link uses full absolute URL
4f471f2 Remove Switch WordPress account link, rely on prompt=login
5d36d73 Fix name casing: preserve McGregor, McDonald etc
0214ef8 Fix NameError: define admin_preview in technician_dashboard view
4d053eb Fix delegate access: view cases, submit dropdown, doc uploads
1ea5236 Fix: exclude pure delegates from their own advisor dropdown
ec3367f Fix audit trail gaps for SSO and delegate features
2f3b7b4 Fix all delegate permission gaps across 20+ views
1585646 Fix: import AuditLog in add_case_message email notification block
1da3cad Fix: rush date warning not appearing on submit case form
7bcb0fd Fix draft notes save + delegate access in case_detail template
e46e906 Remove dead toggleEditMode/saveDraftChanges JS code from case_detail
33ed47f Match member Technical Notes styling to tech view
f9f51f8 Remove all Case ID references from email subjects and templates
f6ac0f1 Fix: delegates chat messages now notify technician, not member
b4c3ff6 Enforce email policy: members only get HOLD/CHAT/READY emails, disable all tech emails
72f054b Fix CHAT email: remove copyright footer from all 3 active email templates
ae43d00 Restore red rush alert box on submit case page
1badc46 Update Federal Fact Finder form to v2 portal 5-Mar-2026 edition
e057992 Update FactFinder.pdf in static/documents as well
2c2e9cd Add 'To view the note and respond:' above CLICK HERE in CHAT email
24c30c8 Change completed email subject from COMPLETE to REPORT
e6de087 Send HOLD/CHAT/READY emails to both member AND delegates
0ed71b5 Add test account infrastructure: is_test_account, notification_email, SSO allowlist
```

---

## Migrations Needed on PROD

PROD currently has:
- accounts: through 0005
- core: through 0013
- cases: through 0033

Pending migrations after pull:

| App | Migration | Description |
|---|---|---|
| accounts | 0006 | MemberDelegate model |
| accounts | 0007 | UserPreference + AuditLog models |
| accounts | 0008 | User contact_id field |
| accounts | 0009 | SSOAllowedEmail model |
| accounts | 0010 | is_test_account + notification_email fields |

(Core and Cases migrations are up to date on PROD)

---

## Pre-Deploy Checklist

- [x] LOCAL clean, on main, at 0ed71b5
- [x] TEST clean, on main, at 0ed71b5 (in sync with LOCAL)
- [x] PROD state documented (a24f4c8, 38 commits behind)
- [x] Pending migrations identified (accounts 0006-0010, core 0014)
- [x] PROD .env has SSO_ALLOWED_EMAILS blank (allow all users)
- [x] Backup PROD database before deploy (244K → /tmp/prod_backup_20260307.json)
- [x] git pull on PROD (38 commits, 74 files, fast-forward)
- [x] Run migrations on PROD (accounts 0006-0010, core 0014 — all OK)
- [x] Collect static files (1 copied, 320 unmodified)
- [x] Restart Gunicorn
- [x] Verify PROD is running (302 on /)
- [x] Django system check — no issues
- [x] PROD at commit 0ed71b5 (matches LOCAL + TEST)
- [ ] Smoke test SSO login
- [ ] Smoke test case workflows
- [ ] Verify email sending works

---

## Deploy Steps

### 1. Backup PROD Database
```bash
ssh dev@104.248.126.74
cd /var/www/advisor-portal
source venv/bin/activate
python manage.py dumpdata --natural-foreign --natural-primary -o /tmp/prod_backup_20260307.json
```

### 2. Git Pull
```bash
cd /var/www/advisor-portal
git stash  # stash the SCP'd FactFinder.pdf change
git pull origin main
git stash pop  # restore (will be overwritten by the git version anyway)
```

### 3. Run Migrations
```bash
python manage.py migrate
```

### 4. Collect Static Files
```bash
python manage.py collectstatic --noinput
```

### 5. Verify PROD .env
- SSO_ALLOWED_EMAILS should be BLANK (no allowlist = all tagged users can SSO in)
- EMAIL_BACKEND should be smtp (real emails)

### 6. Restart Gunicorn
```bash
sudo systemctl restart gunicorn
```

### 7. Post-Deploy Verification
- [ ] Site loads at portal.profeds.com
- [ ] SSO login works for a real member
- [ ] Member dashboard shows cases
- [ ] Case detail page loads
- [ ] Email notifications send correctly
- [ ] Admin panel accessible

---

## PROD .env Differences from TEST

| Setting | TEST | PROD |
|---|---|---|
| SSO_ALLOWED_EMAILS | 10 allowed emails | BLANK (all users) |
| ALLOWED_HOSTS | test-reports.profeds.com | portal.profeds.com |
| DEBUG | False | False |
| EMAIL_BACKEND | smtp | smtp |

---

## Rollback Plan

If critical issues found after deploy:
```bash
cd /var/www/advisor-portal
git checkout a24f4c8  # revert to previous commit
python manage.py migrate accounts 0005  # reverse account migrations
sudo systemctl restart gunicorn
```

---

## Deploy Log

(Updated in real-time during deployment)

| Time (UTC) | Action | Result |
|---|---|---|
| 16:02 | Backup PROD database | OK — 244K → /tmp/prod_backup_20260307.json |
| 16:03 | git stash + git pull | OK — 38 commits, 74 files, fast-forward from a24f4c8 to 0ed71b5 |
| 16:04 | python manage.py migrate | OK — accounts 0006-0010 + core 0014 applied |
| 16:05 | python manage.py collectstatic | OK — 1 file copied (FactFinder.pdf), 320 unmodified |
| 16:05 | Verify .env | OK — SSO_ALLOWED_EMAILS blank, EMAIL_BACKEND=smtp, DEBUG=False |
| 16:06 | Restart Gunicorn | OK — 302 response on https://reports.profeds.com/ |
| 16:06 | Django system check | OK — no issues |
| 16:06 | Confirm PROD commit | OK — 0ed71b5 (matches LOCAL + TEST) |
| — | Smoke test SSO login | PENDING — user to test |
| — | Smoke test case workflows | PENDING — user to test |
| — | Verify emails | PENDING — user to test |
