# GHL On-Demand Sync — Analysis & Implementation Plan
**Date:** 2026-08-29  
**Status:** Analysis complete — implementation pending GHL Private Integration Token

---

## The Problem

The admin currently feels she must log in as a new user so that SSO auto-provisioning fires and the user record is created with the correct role inside the portal.

**What's actually happening:**
- For members and delegates, SSO auto-provisioning works on first login — no impersonation needed
- For staff (technician, admin, manager), the role must be set manually inside the portal because those roles are intentionally NOT driven by GHL tags
- The friction is: the admin has to wait for the user's first SSO login before the portal record exists, then go set the role

**Desired state:** Admin can pre-provision users and assign roles inside the portal without waiting for the user to log in first.

---

## Why the Existing SSO Credentials Can't Be Reused

The portal's existing credentials (`WP_OAUTH_CLIENT_ID`, `WP_OAUTH_CLIENT_SECRET`) are for OAuth2 **Authorization Code Grant** only. This flow requires:

1. The user's browser redirected to WP
2. The user authenticates
3. WP sends a code back to the portal
4. The portal exchanges the code for a short-lived, **per-user** access token
5. That token hits the WP resource endpoint for **that specific user's data only**

This cannot be used server-side for arbitrary users without their browser session. The chain is:

```
Portal  ←→  WP OAuth (miniOrange/profeds.com)  ←→  WP Fusion  ←→  GHL
```

The portal never calls GHL directly. It calls WP, which has synced data from GHL via WP Fusion. The existing credentials give no direct access to GHL.

---

## Constraints

- No WP Fusion developer involvement
- No changes to WP or GHL configuration
- Role provisioning stays 100% inside the portal
- Staff roles (technician, admin, manager) are never set from external tags

---

## Options Evaluated

### Option 1 — Portal Pre-Provisioning UI *(no external API — implement first)*

The SSO handler in `accounts/sso.py` already checks for an existing user by `contact_id` or `email` before creating a new one. If a user record already exists when they first SSO-login, the system matches it and the user lands in the correct experience immediately.

The gap: there is no admin UI for creating these records. The admin has to use Django admin.

**Solution:** Build a "User Management" page in the portal admin panel with a clean form for entering name, email, role, workshop code, and contact_id. Roles are set here, never from GHL.

**Pros:**
- Zero external API calls
- Zero new credentials
- Immediate value — works today

**Cons:**
- Doesn't help discover users who exist in GHL but aren't known to the admin yet
- Manual entry per user

---

### Option 2 — GHL Private Integration Token *(on-demand sync — implement second)*

GHL's REST API v2 allows direct server-to-server queries of contacts. A **Private Integration Token** (GHL's current credential model, replacing legacy API keys) provides scoped, static access to the GHL API without user interaction.

**What the sync does:**
1. Admin clicks "Sync from GHL" in the portal
2. Portal calls `GET https://services.leadconnectorhq.com/contacts/?locationId={id}` with the token
3. Filters contacts with `portal access: member` or `portal access: delegate` tags
4. Compares against the portal user table by `contact_id` (already stored on every User)
5. Shows the admin a diff: users in GHL not yet in the portal
6. Admin reviews, optionally assigns roles, clicks "Provision" to create the records

**Roles remain 100% in the portal.** GHL data is used only for identity (email, name, contact_id) and to flag member vs. delegate. Technician, admin, and manager roles are always set by the admin in the portal UI.

**Pros:**
- Goes directly to the source of truth (GHL is where tags are added)
- `contact_id` is already on every User record — matching is trivial
- Discovers new users the admin didn't know to add manually
- Token is static and self-managed (no expiry unless rotated)

**Cons:**
- Requires generating a GHL Private Integration Token (10-minute setup, see below)
- Requires the GHL Sub-Account Location ID (findable in GHL settings)
- GHL API rate limits: 100 req/10s, 200k req/day — not a concern for this use case

---

### Option 3 — WordPress REST API *(not recommended)*

WordPress has a REST API (`/wp-json/wp/v2/users`) that can be called with a WP Application Password. However, WP Fusion tag data in user meta may not be exposed by the REST API without a developer registering the meta fields — an uncertain dependency. Option 2 is more reliable and goes to the true source.

---

### Option 4 — Complete the Existing Webhook *(best long-term, needs WP dev)*

`accounts/views_webhook.py` is already built as a skeleton. When a tag changes in GHL, WP Fusion fires to the portal webhook which updates the user immediately. This eliminates the sync step entirely. However, the WP Fusion developer must configure the webhook destination — violates the "no WP dev involvement" constraint. Defer to later.

---

## Recommendation

| Phase | Action |
|---|---|
| **Now** | Implement Option 1: Portal pre-provisioning UI (no dependencies) |
| **After GHL token is ready** | Implement Option 2: GHL on-demand sync with diff view |
| **Later (with WP dev)** | Implement Option 4: Webhook for real-time automatic sync |

---

## GHL Private Integration Token Setup

> **Note:** Legacy GHL API keys (v1) reached end-of-support December 31, 2025.  
> The correct modern approach is a **Private Integration Token** (v2 API).

### Step-by-step

**1. Go to GHL Sub-Account Settings**
- Log into GHL
- Navigate to the **Sub-Account** (Location) that manages your contacts (not the Agency level unless you need agency-wide access)
- Click **Settings** (gear icon, left sidebar)

**2. Find Private Integrations**
- In Settings, look for **Integrations** → **Private Integrations**
- If not visible, check **Labs** in Settings and enable the Private Integrations feature

**3. Create a new integration**
- Click **"Create new Integration"**
- Name: `Benefits Portal Sync`
- Description: `On-demand contact sync for advisor portal provisioning`

**4. Select scopes (minimum required)**
- `contacts.readonly` — to read contacts and their tags
- Do NOT grant write scopes — this integration is read-only

**5. Copy the token**
- GHL shows the token once — copy it immediately
- You cannot retrieve it again (only rotate it)

**6. Get your Location ID**
- In GHL Sub-Account Settings → go to **Business Profile** or check the URL — the Location ID is the alphanumeric ID in the URL (e.g., `ve9EPM428h8vShlRW1KT`)
- Alternatively: Settings → General → the Location/Sub-account ID is shown there

**7. Add to portal `.env`**
```
GHL_PRIVATE_TOKEN=your_token_here
GHL_LOCATION_ID=your_location_id_here
```

**8. Test the connection**
```bash
curl -X GET "https://services.leadconnectorhq.com/contacts/?locationId=YOUR_LOCATION_ID&limit=5" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Version: 2021-07-28"
```
Should return a JSON response with contacts.

---

## Technical Notes for Implementation

### GHL API endpoint for contacts
```
GET https://services.leadconnectorhq.com/contacts/
  ?locationId={GHL_LOCATION_ID}
  &query={email_or_name}        # optional search
  &limit=100
  &startAfterId={last_id}       # pagination cursor
```

Response includes: `id` (= contact_id), `email`, `firstName`, `lastName`, `tags[]`

### Tag matching
The same `determine_role_from_tags()` and `_normalize_tags()` functions in `accounts/sso.py` can be reused exactly as-is. No new business logic needed.

### Matching against portal DB
```python
# contact_id is already stored on User model
User.objects.filter(contact_id=ghl_contact_id)
# fallback
User.objects.filter(email__iexact=ghl_email)
```

### Rate limits
At 100 contacts, a single paginated call is sufficient. Rate limits (100 req/10s) are not a concern.

---

## Files to Create/Modify

| File | Change |
|---|---|
| `accounts/views_provisioning.py` | New: pre-provisioning UI + GHL sync view |
| `accounts/ghl_client.py` | New: GHL API client (contacts fetch, tag parse) |
| `accounts/templates/accounts/provisioning.html` | New: admin provisioning UI |
| `accounts/urls.py` | Add provisioning URL routes |
| `.env` / `.env.example` | Add `GHL_PRIVATE_TOKEN`, `GHL_LOCATION_ID` |
| `config/settings.py` | Read new env vars |
