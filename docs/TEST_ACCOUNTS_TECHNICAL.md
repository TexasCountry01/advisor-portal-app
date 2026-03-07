# Test Account Implementation — Technical Document

## Overview

Seven dedicated WordPress accounts will be created for testing the Advisor Portal. These accounts use the same SSO pipeline as production users — same OAuth app, same WP Fusion tags, same miniOrange flow. No environment differences between TEST and PROD.

---

## Account Matrix

| WP Username | Email (Gmail + alias) | WP Fusion Tag | Django Role | Purpose |
|---|---|---|---|---|
| DevopsAdmin | devops+admin@profeds.com | Portal access: Member | member → promoted to administrator | Admin workflows |
| DevopsManager | devops+manager@profeds.com | Portal access: Member | member → promoted to manager | Manager workflows |
| DevopsMember | devops+member@profeds.com | Portal access: Member | member | Case submission, member dashboard |
| DevopsDelegate | devops+delegate@profeds.com | Portal access: Delegate | member (pure delegate) | Delegate access to DevopsMember's cases |
| DevopsBen1 | devops+ben1@profeds.com | Portal access: Member | member → promoted to technician | Tech workflows |
| DevopsBen2 | devops+ben2@profeds.com | Portal access: Member | member → promoted to technician | Tech workflows |
| DevopsBen3 | devops+ben3@profeds.com | Portal access: Member | member → promoted to technician | Tech workflows |

All 7 email addresses deliver to the single `devops@profeds.com` inbox. Gmail ignores everything between `+` and `@`.

---

## How the SSO Flow Works for These Accounts

### Step 1: User Clicks "Login with ProFeds" on the Portal

The portal redirects to the miniOrange OAuth authorization endpoint on profeds.com:

```
https://profeds.com/wp-json/moserver/authorize
  ?client_id=GIbWesmTFmehLeDLZCqRjpyfUcWDscSa
  &redirect_uri=https://{portal-domain}/accounts/sso/callback/
  &response_type=code
  &state={random-csrf-token}
```

Both TEST and PROD hit the same WordPress OAuth server. The `redirect_uri` is the only difference — it points back to whichever portal the user started from.

### Step 2: WordPress Authenticates and Returns Authorization Code

WordPress verifies the user's credentials and redirects back to the portal with an authorization code:

```
https://{portal-domain}/accounts/sso/callback/?code={auth-code}&state={csrf-token}
```

### Step 3: Portal Exchanges Code for Token, Fetches Profile

The `sso_callback` view in `accounts/views_sso.py`:
1. Validates the state parameter (CSRF check)
2. Exchanges the authorization code for an access token via `POST /wp-json/moserver/token`
3. Fetches the user profile via `GET /wp-json/moserver/resource` using the access token

The profile payload includes: `username`, `email`, `first_name`, `last_name`, `contact_id`, `member_code` (workshop code), `wpf_tags` (list of WP Fusion tag strings).

### Step 4: Tag-Based Role Assignment

`accounts/sso.py` → `determine_role_from_tags()` reads the `wpf_tags` from the profile:

| WP Fusion Tag | Django Role | is_pure_delegate |
|---|---|---|
| `Portal access: Member` | `member` | `False` |
| `Portal access: Delegate` | `member` | `True` |

Tag matching is **case-insensitive**. Only these two tags grant SSO access. No tag = access denied.

### Step 5: User Provisioning

`get_or_create_user_from_sso()` either:
- **Creates** a new Django user (first SSO login) with `role='member'` and `set_unusable_password()`
- **Updates** an existing user (subsequent logins) — syncs name, email, workshop_code, phone

Portal-managed roles (`technician`, `manager`, `administrator`) are **never overwritten** by SSO. Once promoted, the role sticks.

---

## Post-SSO Setup for Each Account

After Chris creates the 7 WordPress accounts and each one SSO-logs-in for the first time, we need to do two things in Django:

### 1. Promote Roles (One-Time)

DevopsAdmin, DevopsManager, DevopsBen1-3 will arrive in Django as `role='member'` because their WP tag is "Portal access: Member". We promote them via Django Admin (`/admin/`) or management command:

```python
from django.contrib.auth import get_user_model
User = get_user_model()

# Promote to correct roles
User.objects.filter(username='DevopsAdmin').update(role='administrator')
User.objects.filter(username='DevopsManager').update(role='manager')
User.objects.filter(username__in=['DevopsBen1', 'DevopsBen2', 'DevopsBen3']).update(role='technician')
```

These roles are in `PORTAL_MANAGED_ROLES` so SSO will never overwrite them on subsequent logins.

### 2. Set up Delegate Relationship

After DevopsDelegate SSO-logs-in (arrives as pure delegate), create the delegation link:

```python
from accounts.models import MemberDelegate

# DevopsDelegate can access DevopsMember's cases
MemberDelegate.objects.create(
    member=User.objects.get(username='DevopsMember'),
    delegate=User.objects.get(username='DevopsDelegate'),
    can_submit=True,
    can_edit=True,
    can_view=True,
)
```

### 3. Flag as Test Accounts

Add `is_test_account = BooleanField(default=False)` to the User model (requires migration), then flag all 7:

```python
User.objects.filter(username__startswith='Devops').update(is_test_account=True)
```

Cleanup scripts will use `.exclude(is_test_account=True)` to preserve these accounts during data resets.

---

## SSO Allowlist (TEST Server Only)

The TEST server has an `SSO_ALLOWED_EMAILS` setting in `.env` that restricts who can SSO in. After Chris creates the accounts, add all 7 to the allowlist:

```
SSO_ALLOWED_EMAILS=dale@profeds.com,devops+admin@profeds.com,devops+manager@profeds.com,devops+member@profeds.com,devops+delegate@profeds.com,devops+ben1@profeds.com,devops+ben2@profeds.com,devops+ben3@profeds.com
```

Or manage via the `SSOAllowedEmail` model in Django Admin. Either source works — they're merged at login time.

The PROD server leaves `SSO_ALLOWED_EMAILS` blank, which means all tagged users can log in.

---

## Email Behavior for Test Accounts

The portal sends three types of email notifications: HOLD, CHAT, and READY.

- Emails are sent to the member **and** all their delegates via `get_case_recipient_emails(case)`
- For test accounts, emails go to the `+` alias addresses (e.g., `devops+member@profeds.com`)
- Gmail delivers all of them to the `devops@profeds.com` inbox
- The catch-all mailbox is **not involved** — these are real Gmail addresses, not nonexistent addresses

This means whoever monitors `devops@profeds.com` can verify that email notifications work correctly without polluting Chris's catch-all.

---

## Gmail + Alias — How It Works

Gmail's plus addressing:
- `devops@profeds.com` is the actual mailbox
- `devops+anything@profeds.com` delivers to the same mailbox
- No configuration needed — Gmail handles this automatically
- WordPress sees each `+` variant as a unique email address (valid for account creation)
- The sending system (Django SMTP) sends to the full address — it doesn't know or care that it's an alias

To filter in Gmail: create a filter for `to:devops+*@profeds.com` and apply a label like "Portal Test" or auto-archive.

---

## Files Involved

| File | Purpose |
|---|---|
| `accounts/sso.py` | Tag → role mapping, user provisioning, login-time sync |
| `accounts/views_sso.py` | OAuth callback handler |
| `accounts/models.py` | User model (role, contact_id, workshop_code), MemberDelegate |
| `config/settings.py` | OAuth URLs, client credentials, SSO_ALLOWED_EMAILS |
| `cases/services/email_service.py` | Email sending, `get_case_recipient_emails()` |

---

## Summary

1. Chris creates 7 WP accounts with the correct tags and `+` alias emails
2. Each account SSO-logs-in to the TEST portal for the first time
3. We promote 5 accounts to their target roles in Django
4. We create the delegate relationship for DevopsDelegate → DevopsMember
5. We flag all 7 as `is_test_account=True`
6. We add the 7 emails to the TEST server's SSO allowlist
7. Test accounts are permanent, work identically to real users, and survive data cleanups
