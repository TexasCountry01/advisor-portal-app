# Terms of Service — Implementation Options

**Date:** June 21, 2026  
**Scope:** SSO-authenticated users (members, delegates, technicians, managers, administrators)  
**Codebase entry point:** `accounts/views_sso.py` → `sso_callback()`

---

## How the Current Login Flow Works

```
User clicks "Sign In"
      ↓
sso_login()  →  redirects to miniOrange on profeds.com
      ↓
miniOrange authenticates → sends code back
      ↓
sso_callback()
  1. Validates state token (CSRF)
  2. Exchanges code for access token
  3. Fetches user profile from WP resource endpoint
  4. get_or_create_user_from_sso() — matches/creates Django user, syncs fields
  5. login(request, user, ...)           ← user is authenticated here
  6. redirect(next_url)                  ← straight to dashboard
```

**Key constraint:** There is no second "stop" between steps 5 and 6. Any TOS gate
must be inserted here, or enforced by middleware on every subsequent request.

---

## Option A — One-Time Acknowledgement

> User agrees once. After that, they are never shown the TOS again
> (unless the TOS version changes — see the Versioned variant below).

### How it works

1. Add a `tos_agreed_at` field to the `User` model (`DateTimeField`, null/blank).
2. After `login()` in `sso_callback()`, check `if not user.tos_agreed_at`.
3. If not agreed: store `next_url` in session, redirect to `/accounts/tos/`.
4. TOS page shows the agreement text and an "I Agree" button.
5. On POST: set `user.tos_agreed_at = now()`, save, redirect to the stored `next_url`.
6. All future logins skip the TOS page entirely.

### Files that need changes

| File | Change |
|------|--------|
| `accounts/models.py` | Add `tos_agreed_at = DateTimeField(null=True, blank=True)` to `User` |
| New migration | `python manage.py makemigrations accounts` |
| `accounts/views_sso.py` | After `login()`, check `tos_agreed_at`; redirect to TOS if null |
| New `accounts/views_tos.py` | `tos_view()` — GET renders page, POST saves timestamp, redirects |
| `accounts/urls.py` | Add `path('tos/', views_tos.tos_view, name='tos')` |
| New `accounts/templates/accounts/tos.html` | TOS agreement page with "I Agree" button |
| `core/models.py` | Add `tos_agreed` to `ACTION_CHOICES` for audit logging (optional) |

### Pros
- Minimal user friction — one extra click, ever
- Database record with timestamp for compliance (`tos_agreed_at` is stored on the User row)
- Admin/manager can query who has and hasn't agreed

### Cons
- Does not guarantee the user re-read the TOS
- If TOS is updated, existing users are not prompted again (unless versioning is added)

### Variant: Versioned One-Time TOS (Recommended)

Instead of a plain timestamp, store a version string:

```python
# accounts/models.py
tos_version_agreed = models.CharField(max_length=20, blank=True, default='')

# config/settings.py
TOS_CURRENT_VERSION = '2026-06-21'
```

In `sso_callback()`, check:
```python
if user.tos_version_agreed != settings.TOS_CURRENT_VERSION:
    # show TOS gate
```

On "I Agree" POST, set `user.tos_version_agreed = settings.TOS_CURRENT_VERSION`.

**Effect:** When the TOS changes, bump `TOS_CURRENT_VERSION` in settings.
Every user (including long-standing ones) is prompted once more on their next login.
No new migration needed when TOS content changes — only a settings change.

---

## Option B — Every-Login Acknowledgement

> User must click "I Agree" on every single login before reaching the dashboard.

### How it works

1. Add a session flag approach — no database field needed.
2. In `sso_callback()`, after `login()`, store `request.session['tos_pending'] = True`
   and redirect to `/accounts/tos/` unconditionally.
3. TOS page shows the agreement and "I Agree" button.
4. On POST: set `request.session['tos_agreed'] = True`, clear `tos_pending`,
   redirect to `next_url`.
5. Add `TOSMiddleware` that checks every authenticated request:
   - If `tos_pending` is True and `tos_agreed` is not True, redirect to TOS.
   - This prevents users from bypassing the TOS page by navigating directly.

### Files that need changes

| File | Change |
|------|--------|
| `accounts/views_sso.py` | After `login()`, set session flag, redirect to TOS unconditionally |
| New `accounts/views_tos.py` | Same TOS view as Option A |
| `accounts/urls.py` | Add TOS URL |
| New `accounts/templates/accounts/tos.html` | TOS agreement page |
| New `accounts/middleware.py` (or add to existing) | `TOSMiddleware` session check |
| `config/settings.py` | Add `TOSMiddleware` to `MIDDLEWARE` list |

> **Note:** No model migration needed for Option B (session-only).
> However, there is no persistent database record of when each user agreed.
> If audit trail of agreement is required for compliance, a database write
> must be added to the POST handler anyway (making the migration unavoidable).

### Pros
- Maximum assurance that user acknowledged TOS before each session
- Simplest data story: if session has the flag, they agreed this session
- No migration needed for basic session-only version

### Cons
- Significant user friction — every login adds a required click
- No durable record of agreement per-session unless explicitly logged
- Can feel disruptive for a tool users access daily

---

## Option C — Hybrid (Recommended Starting Point)

Combine the best of both:

1. Use **versioned one-time TOS** (Option A Variant) for the database record.
2. Add **middleware** as a safety net for direct URL access.

```
sso_callback()
  └─ After login():
       if user.tos_version_agreed != settings.TOS_CURRENT_VERSION:
           session['tos_next'] = next_url
           redirect → /accounts/tos/

TOSMiddleware (all requests):
  └─ if request.user.is_authenticated
       and request.user.tos_version_agreed != settings.TOS_CURRENT_VERSION
       and request.path not in ['/accounts/tos/', '/accounts/logout/']:
           redirect → /accounts/tos/
```

This ensures:
- Users who complete SSO but navigate away before the TOS page still
  get intercepted on their next page load
- Manual login (non-SSO) users are also covered
- Versioning allows forced re-agreement when TOS changes
- A permanent, timestamped record is kept per user

---

## Comparison Summary

| | Option A (One-Time) | Option A Versioned | Option B (Every Login) | Option C (Hybrid) |
|---|---|---|---|---|
| User friction | One time ever | Once per TOS version | Every login | Once per TOS version |
| DB record | ✅ Timestamp | ✅ Version + timestamp | ❌ Session only | ✅ Version + timestamp |
| Migration needed | Yes | Yes | No (basic) | Yes |
| Handles TOS updates | ❌ | ✅ | ✅ (auto) | ✅ |
| Works for non-SSO login | Only with middleware | Only with middleware | ✅ | ✅ |
| Implementation effort | Low | Low | Medium | Medium |
| Recommended for compliance | Moderate | Good | High | Best |

---

## Implementation Notes

### Which users are affected

All roles go through `sso_callback()`:
- `member` (advisors)
- `member` (pure delegates)
- `technician`, `manager`, `administrator` — these bypass the WP tag check but still
  go through the same SSO flow and would hit the TOS gate equally

If TOS should only apply to **members/delegates** (not internal staff), add a role check:
```python
if user.role == 'member' and user.tos_version_agreed != settings.TOS_CURRENT_VERSION:
```

### Audit logging

Any option should log TOS agreement to `core.AuditLog`:
```python
AuditLog.objects.create(
    user=user,
    action_type='tos_agreed',
    description=f'{user.get_full_name()} agreed to TOS version {settings.TOS_CURRENT_VERSION}',
    metadata={'tos_version': settings.TOS_CURRENT_VERSION},
    ip_address=_get_client_ip(request),
)
```
Add `('tos_agreed', 'Terms of Service Agreed')` to `ACTION_CHOICES` in `core/models.py`.

### Logout behavior for Option B / Option C middleware

The TOS redirect must explicitly exclude:
- `/accounts/tos/` (the TOS page itself — avoid redirect loop)
- `/accounts/logout/` (allow user to log out without being stuck)
- Any static file / media paths

### Manual login path

The portal has a manual login path (non-SSO) via Django's standard `login` view.
Options A/C with middleware will catch those users too.
Option B only covers SSO logins unless the manual login view is also modified.

---

## Recommended Next Step

Implement **Option C (Hybrid)** with the versioned field, starting with:

1. Add `tos_version_agreed` field to `User` model and run migration
2. Add `TOS_CURRENT_VERSION` to `settings.py`
3. Add TOS check in `sso_callback()` (3 lines)
4. Create TOS view, URL, and template
5. Add `TOSMiddleware` as safety net
6. Add `tos_agreed` to `core.AuditLog.ACTION_CHOICES`

Estimated scope: ~6 small, contained changes. No existing logic is modified except
`sso_callback()` (a 3-line addition after the `login()` call).
