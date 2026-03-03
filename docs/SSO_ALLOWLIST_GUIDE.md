# SSO Allowlist — Controlling Who Can Access the Portal

## What Is It?

The **SSO Allowlist** is a gatekeeper that restricts which email addresses can log into the portal via SSO. It was designed specifically for the **TEST server** so you can share the same WordPress OAuth setup as PROD without letting every member stumble into the test environment.

## How It Works

The allowlist combines two sources:

| Source | Where | How to Edit |
|--------|-------|-------------|
| **Database table** (`SSOAllowedEmail`) | Django Admin (`/admin/`) | Add/remove rows via the admin UI |
| **Environment variable** (`SSO_ALLOWED_EMAILS`) | `.env` file on the server | Edit the file, restart gunicorn |

### The Rule Is Simple

- **If the allowlist is EMPTY** (both sources have zero entries) → **ALL tagged users can SSO in**. This is "open mode" — the intended behavior for PRODUCTION.
- **If the allowlist has ANY entries** → **ONLY those listed emails can SSO in**. Everyone else gets: *"Access to this portal instance is restricted. Contact your administrator."*

### Important: This Is an ADDITIONAL Gate

The allowlist does NOT replace the tag check. Users must still pass the tag check first (have `portal access: member` tag, or be an existing admin/tech/manager). The allowlist is a **second gate** on top of that.

```
User clicks SSO → WP authenticates → Portal checks:
  1. Does user have portal access tag? (or existing admin/tech/manager role?)
  2. Is allowlist empty? If yes → let them in
     Is allowlist populated? → Is their email on it? If no → BLOCKED
  3. Match/create user → log them in
```

## Current Status

### TEST Server (`test-reports.profeds.com`)
- **DB entries: 0**
- **ENV entries: [] (empty)**
- **Result: OPEN MODE** — all tagged users can SSO in
- **Is it blocking anyone right now? NO.**

### PROD Server (`reports.profeds.com`)
- Same config — allowlist is empty
- **Result: OPEN MODE** — all tagged users can SSO in

## How to Use It

### Option 1: Django Admin (Recommended for TEST)

1. Go to `https://test-reports.profeds.com/admin/`
2. Log in as a superuser
3. Find **"SSO Allowed Emails"** in the Accounts section
4. Click **"Add SSO Allowed Email"**
5. Enter the email address and an optional note (e.g., "Tester - Chris")
6. Save

Now ONLY emails in that table (plus any in the ENV var) can SSO in. To go back to open mode, delete all rows.

### Option 2: Environment Variable (Server-Level)

Edit `/home/dev/advisor-portal-app/.env` on the TEST server:

```
SSO_ALLOWED_EMAILS=chris@profeds.com,tsdspyj@sbcglobal.net,dale@mcgregorfg.com
```

Then restart gunicorn:
```
sudo systemctl restart gunicorn
```

To go back to open mode, set it to empty or remove the line:
```
SSO_ALLOWED_EMAILS=
```

### When to Use It

| Scenario | What to Do |
|----------|------------|
| **Lock down TEST** so only testers can access | Add tester emails to the allowlist |
| **Open TEST** for broader testing | Clear the allowlist (delete all DB rows, empty ENV var) |
| **PROD** | Leave allowlist empty — never restrict production |

## Notes

- The allowlist is **case-insensitive** — `Chris@ProFeds.com` and `chris@profeds.com` are treated the same
- Admin/tech/manager users bypass the **tag check** but NOT the allowlist. If the allowlist is active, even admins must be listed.
- Only **superusers** can see/edit the SSOAllowedEmail table in Django Admin
- Changes to the DB table take effect **immediately** (no restart needed). Changes to the ENV var require a gunicorn restart.
