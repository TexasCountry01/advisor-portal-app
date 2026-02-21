# Badge/Button Styling — Branch Strategy

**Date:** February 20, 2026

## What Happened

The badge vs button styling overhaul (43 files, commit `99cfc6a`) was deployed to TEST but the user hasn't signed off yet. Email functionality work needs to go to PROD now. To avoid blocking PROD deployments, the badge work was moved to its own feature branch.

## Current State

| Location | Branch | Commit | Badge changes? |
|----------|--------|--------|----------------|
| Local | `main` | `1722d9f` | No |
| Local | `badge-button-styling` | `99cfc6a` | Yes |
| GitHub | `main` | `1722d9f` | No |
| GitHub | `badge-button-styling` | `99cfc6a` | Yes |
| TEST server | `main` / `1722d9f` | — | No |
| PROD server | `main` / `1722d9f` | — | No |

## How to Resume Badge Work

When the user approves the badge styling:

```bash
# 1. Switch to main
git checkout main

# 2. Merge the badge branch
git merge badge-button-styling

# 3. Push to GitHub
git push origin main

# 4. Deploy to TEST
ssh dev@157.245.141.42 "cd /home/dev/advisor-portal-app && git pull origin main && source venv/bin/activate && python manage.py collectstatic --noinput && kill -HUP 1570772"

# 5. Deploy to PROD
ssh dev@104.248.126.74 "cd /var/www/advisor-portal && git pull origin main && source venv/bin/activate && python manage.py collectstatic --noinput && pgrep -f 'gunicorn.*config' | head -1 | xargs kill -HUP"

# 6. Clean up the feature branch
git branch -d badge-button-styling
git push origin --delete badge-button-styling
```

## How to Preview Badge on TEST Only

If you want TEST to show the badge styling for user review while keeping PROD clean:

```bash
ssh dev@157.245.141.42 "cd /home/dev/advisor-portal-app && git fetch origin && git checkout badge-button-styling && source venv/bin/activate && python manage.py collectstatic --noinput && kill -HUP 1570772"
```

To switch TEST back to main afterward:

```bash
ssh dev@157.245.141.42 "cd /home/dev/advisor-portal-app && git checkout main && git pull origin main && source venv/bin/activate && python manage.py collectstatic --noinput && kill -HUP 1570772"
```

## Important Reminders

- **collectstatic is required** whenever CSS changes are deployed — the server serves from `staticfiles/`, not `cases/static/`
- The badge branch may need a rebase if main has diverged significantly: `git checkout badge-button-styling && git rebase main`
- PROD sudo password: `ProFeds2025Prod!`
- TEST gunicorn PID: `1570772`
