# Production Deployment Game Plan — Messaging App

**Date:** March 21, 2026  
**Prerequisite:** User approval of messaging feature on TEST server  
**Risk Level:** Low — additive feature, no changes to existing functionality  
**Estimated Downtime:** None (graceful reload)

---

## Pre-Deployment Checklist

- [ ] User has approved messaging feature on TEST server
- [ ] Confirm LOCAL, TEST, and remote origin are all at the same commit
- [ ] Confirm no active users on PROD are mid-workflow (optional, low risk)

---

## Deployment Steps

### Step 1: Verify Environment State

```bash
# LOCAL
git log --oneline -3

# TEST
ssh dev@157.245.141.42 "cd /home/dev/advisor-portal-app && git log --oneline -3"

# PROD
ssh dev@104.248.126.74 "cd /var/www/advisor-portal && git log --oneline -3"
```

Confirm LOCAL and TEST are at the same commit (currently `ec7f469`).  
Note PROD commit hash for rollback reference.

---

### Step 2: Deploy Code to PROD

PROD has a diverged git history (cherry-picked commits). Use merge to preserve PROD history:

```bash
ssh dev@104.248.126.74 "cd /var/www/advisor-portal && git fetch origin && git merge origin/main --no-edit"
```

If merge conflicts occur (possible in `views.py` or `send_scheduled_emails.py` due to cherry-picks):
- The conflicts will be in files where cherry-picked code already matches main
- Resolve by accepting the incoming (main) version since the code is functionally identical
- `git add . && git commit --no-edit`

If merge is too messy, fallback to reset (safe because cherry-picks are functionally identical to main):
```bash
ssh dev@104.248.126.74 "cd /var/www/advisor-portal && git fetch origin && git reset --hard origin/main"
```

---

### Step 3: Run Database Migration

```bash
ssh dev@104.248.126.74 "cd /var/www/advisor-portal && source venv/bin/activate && python manage.py migrate messaging"
```

This creates 3 new tables: `messaging_conversation`, `messaging_message`, `messaging_messagereadstatus`.  
No existing tables are modified.

---

### Step 4: Collect Static Files

```bash
ssh dev@104.248.126.74 "cd /var/www/advisor-portal && source venv/bin/activate && python manage.py collectstatic --noinput"
```

---

### Step 5: Reload Gunicorn

```bash
# Find gunicorn master PID
ssh dev@104.248.126.74 "ps aux | grep gunicorn | grep -v grep | head -1"

# Graceful reload (no downtime — workers restart one at a time)
ssh dev@104.248.126.74 "kill -HUP <master_pid>"
```

---

### Step 6: Verify Deployment

```bash
# Confirm git is current
ssh dev@104.248.126.74 "cd /var/www/advisor-portal && git log --oneline -3"

# Confirm migration applied
ssh dev@104.248.126.74 "cd /var/www/advisor-portal && source venv/bin/activate && python manage.py showmigrations messaging"

# Confirm Django starts cleanly
ssh dev@104.248.126.74 'cd /var/www/advisor-portal && source venv/bin/activate && python manage.py check --deploy 2>&1 | tail -5'

# Confirm gunicorn workers are fresh
ssh dev@104.248.126.74 "ps aux | grep gunicorn | grep -v grep"
```

---

## Post-Deployment Verification

- [ ] Portal loads at https://portal.profeds.com without errors
- [ ] Log in as a member — confirm "Messages" link appears in navbar
- [ ] Log in as staff — confirm "Messages" link appears with queue view
- [ ] Create a test conversation as a member
- [ ] Reply to the conversation as staff
- [ ] Verify unread badge updates
- [ ] Verify existing case workflows still work (open a case, view case detail, etc.)

---

## Rollback Plan

If something goes wrong, revert to the pre-deployment PROD commit:

```bash
# Note the PROD commit hash from Step 1 (currently 5e26eac)
ssh dev@104.248.126.74 "cd /var/www/advisor-portal && git reset --hard <pre_deploy_commit>"
ssh dev@104.248.126.74 "kill -HUP <gunicorn_master_pid>"
```

The messaging migration can be reversed if needed:
```bash
ssh dev@104.248.126.74 "cd /var/www/advisor-portal && source venv/bin/activate && python manage.py migrate messaging zero"
```

---

## What Changes for Users After Deployment

| User Role | What They See |
|-----------|---------------|
| **Members** | New "Messages" nav link; can submit questions and see replies |
| **Technicians** | New "Messages" nav link; can view, claim, and reply to member questions |
| **Administrators** | New "Messages" nav link; same as technicians plus admin panel access |
| **Managers** | New "Messages" nav link; same as technicians |

No existing pages, workflows, or features are modified.
