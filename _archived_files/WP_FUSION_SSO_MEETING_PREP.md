# WP Fusion / SSO Integration — Meeting Prep
## For Meeting with WordPress Developer

**Date Prepared:** February 21, 2026  
**System:** ProFeds Advisor Portal (Django 5.0.7)  
**Portal URLs:** https://reports.profeds.com (PROD) / https://test-reports.profeds.com (TEST)

---

## 1. Meeting Objective

Establish the technical approach for integrating Single Sign-On (SSO) between the ProFeds WordPress site and the Advisor Portal (Django), using WP Fusion as the bridge. Define responsibilities, data flows, and next steps.

---

## 2. Current State — What the Portal Has Today

### Authentication
- Standard Django session-based login (username + password)
- Login endpoint: `/login/` (POST with `username` and `password`)
- Session cookie managed by Django
- No external identity provider — all user accounts created directly in Django

### User Model (Django)
| Field | Type | Notes |
|-------|------|-------|
| `username` | string | Unique login identifier |
| `password` | string | Django-hashed (PBKDF2) |
| `email` | string | Member's email |
| `first_name` / `last_name` | string | Display name |
| `role` | string | `member`, `technician`, `administrator`, `manager` |
| `user_level` | string | Technician only: `level_1`, `level_2`, `level_3` |
| `workshop_code` | string | Member's workshop affiliation |
| `phone` | string | Contact number |
| `is_active` | boolean | Can log in when True |
| `font_size` | string | Accessibility preference |

### Role-Based Behavior
After login, users are redirected to their role-specific dashboard:
- **Member** → Member Dashboard (own cases only)
- **Technician** → Technician Dashboard (all cases)
- **Administrator** → Admin Dashboard (full system)
- **Manager** → Manager Dashboard (read-only analytics)

### What We Do NOT Have
- No OAuth / JWT / SAML endpoints
- No REST API for external authentication
- No WP Fusion plugin or middleware installed
- No token-based session management

---

## 3. What We Need from the WordPress Developer

### 3A. SSO Direction Decision

We need to agree on ONE of these approaches:

| Approach | How It Works | Complexity |
|----------|-------------|-----------|
| **A. WP → Django redirect** | User logs into WordPress → WP Fusion creates a signed token/URL → User is redirected to Django with token → Django validates and creates session | Medium |
| **B. Shared session / cookie** | Both apps on same domain → share session cookie or use WP Fusion to create a Django session on WP login | Medium (requires same domain) |
| **C. JWT-based** | WP issues a JWT on login → Django validates JWT on each request or on first visit → Creates local session | Medium-High |
| **D. OAuth2** | WP acts as OAuth2 provider → Django uses OAuth2 client flow → Token exchange → Local session | High (most standards-compliant) |

**Our preference**: Approach A or C — simplest to implement on the Django side.

### 3B. What the WP Developer Needs to Provide

| Item | Details |
|------|---------|
| **SSO endpoint URL** | The WP URL that initiates the SSO flow (e.g., `https://profeds.com/sso/initiate`) |
| **Token format** | What does the signed token look like? JWT? Signed query parameter? Encrypted payload? |
| **Token signing key** | Shared secret or public key for Django to verify the token's authenticity |
| **Token payload fields** | What user data is included? (email, name, role, workshop_code, subscription status, etc.) |
| **Token expiration** | How long is the token valid? (We suggest 60 seconds for redirect tokens) |
| **Callback/return URL** | Will WP redirect to a specific Django URL? (We'll create one, e.g., `/sso/callback/`) |
| **Logout sync** | When user logs out of WP, should Django session also end? If so, how? (redirect, webhook, or cookie clear) |
| **User provisioning** | Will WP Fusion create Django users automatically on first SSO login, or should Django auto-create from token data? |
| **Subscription status field** | How does WP Fusion expose whether a member's subscription is active/inactive/expired? |
| **WP Fusion tag mapping** | What WP Fusion tags correspond to portal roles (member, technician, admin, manager)? |
| **Test credentials** | WP admin access or test user accounts for integration testing |
| **Webhook for status changes** | Can WP send a webhook to Django when a member's subscription changes? (e.g., `POST /api/wp-webhook/`) |

### 3C. WordPress Site Questions

| Question | Why It Matters |
|----------|---------------|
| Are both sites on the same top-level domain? | Affects cookie-sharing feasibility (e.g., `profeds.com` and `reports.profeds.com`) |
| What WP Fusion license/plan is active? | Determines available features (tags, webhooks, API access) |
| Is WP Fusion already managing member data? | Determines whether members already exist in WP with attributes we need |
| What membership/subscription plugin is used? | WooCommerce Memberships? MemberPress? Paid Memberships Pro? Affects how subscription status is exposed |
| Can WP Fusion fire webhooks on user events? | Critical for real-time sync (user created, subscription changed, etc.) |

---

## 4. What We Can Provide to the WP Developer

### 4A. SSO Callback Endpoint (We Will Build)

We will create:
```
POST/GET https://reports.profeds.com/sso/callback/
```

This endpoint will:
1. Receive the token from WP redirect
2. Validate the token signature and expiration
3. Look up or create the Django user based on token data
4. Log the user in (create Django session)
5. Redirect to the appropriate role-based dashboard
6. Log the SSO event in the audit trail

### 4B. User Data Mapping

The following fields can be populated from WP Fusion data:

| WP Fusion Field | Django Field | Notes |
|-----------------|-------------|-------|
| User email | `email` | **Primary identifier** — used to match WP user to Django user |
| First name | `first_name` | |
| Last name | `last_name` | |
| WP Fusion tag / role | `role` | Map WP tags to: `member`, `technician`, `administrator`, `manager` |
| Workshop code (user meta) | `workshop_code` | Must match existing workshop codes in Django |
| Phone (user meta) | `phone` | Optional |
| Subscription status | `is_active` | Active subscription → `True`; Expired → `False` |

### 4C. Webhook Endpoint (We Will Build)

We will create:
```
POST https://reports.profeds.com/api/wp-webhook/
```

For WP Fusion to notify us when:
- A member's subscription is activated/deactivated
- A member's profile data changes in WP
- A new member is created in WP

Payload we expect:
```json
{
  "event": "subscription_changed",
  "email": "member@example.com",
  "status": "active",
  "workshop_code": "WS-2026-001",
  "timestamp": "2026-02-21T12:00:00Z",
  "signature": "<HMAC signature for verification>"
}
```

### 4D. Existing Code Readiness

Our codebase already has **40+ WP Fusion placeholder comments** marking exact integration points in:

| File | Integration Points |
|------|-------------------|
| `accounts/models.py` | User model fields, subscription status sync, delegate auto-revocation |
| `accounts/views.py` | Profile sync on save, delegate validation, credit sync |
| `accounts/forms.py` | WP subscription display, delegate office filtering, credit calculation |
| Templates | WP status display, office filters, credit source indicators |

These placeholders use markers: `# WP FUSION PLACEHOLDER:` and `# WP FUSION INTEGRATION NOTES:`

---

## 5. Key Decisions to Make in This Meeting

| # | Decision | Options | Impact |
|---|----------|---------|--------|
| 1 | **Who is the identity source of truth?** | WordPress (recommended) vs. Django | Determines where accounts are created and managed |
| 2 | **SSO method** | Signed redirect, JWT, OAuth2, shared cookie | Determines implementation complexity on both sides |
| 3 | **User matching strategy** | By email (recommended) vs. by username vs. by WP user ID | How we link WP accounts to Django accounts |
| 4 | **Auto-provisioning** | Yes (create Django user on first SSO login) vs. No (pre-create required) | Affects onboarding flow |
| 5 | **Role mapping** | WP Fusion tags → Django roles | Who defines the mapping? |
| 6 | **Subscription sync** | Real-time webhook vs. check-on-login vs. daily batch | Affects how quickly deactivations take effect |
| 7 | **Which fields sync from WP?** | All user fields vs. only auth + status | Determines ongoing sync complexity |
| 8 | **Fallback when WP is down** | Allow Django-local login? Block access? Cache last-known status? | Resilience strategy |
| 9 | **Can technicians/admins bypass SSO?** | Yes (direct Django login) vs. No (all through WP) | Staff may not be WP members |
| 10 | **Timeline & phases** | SSO first, then data sync? Or everything at once? | Project planning |

---

## 6. Recommended Phased Approach

### Phase 1: SSO Login (2–3 weeks)
- WP dev: Implement signed redirect or JWT on WP login
- Portal dev: Build `/sso/callback/` endpoint, validate token, create session
- Test: Member logs into WP → lands on portal dashboard authenticated
- **No data sync yet** — just authentication

### Phase 2: User Auto-Provisioning (1 week)
- On first SSO login, auto-create Django user from token data
- Map email, name, role, workshop_code
- Existing users matched by email

### Phase 3: Subscription Status Sync (1–2 weeks)
- WP dev: Set up webhook for subscription changes
- Portal dev: Build `/api/wp-webhook/` endpoint
- Auto-deactivate Django users when WP subscription expires
- Auto-reactivate on renewal

### Phase 4: Profile & Credit Data Sync (2–3 weeks)
- Bi-directional or one-way sync of profile fields
- WP subscription tier → credit allowance auto-calculation
- Delegate auto-management based on WP status
- This phase uses the 40+ placeholder integration points already in our code

---

## 7. Technical Environment Summary

| Item | Value |
|------|-------|
| Portal Framework | Django 5.0.7 (Python 3.11) |
| Portal DB | SQLite |
| Portal Auth | Django sessions (`django.contrib.sessions`) |
| Custom User Model | `accounts.User` (extends `AbstractUser`) |
| Portal PROD URL | `https://reports.profeds.com` |
| Portal TEST URL | `https://test-reports.profeds.com` |
| Portal Hosting | DigitalOcean Droplets |
| Current Login Page | `/login/` (username + password form) |
| After-Login Routing | Role-based redirect (member→member dashboard, etc.) |
| Audit Logging | All auth events logged (`login`, `logout` action types) |

---

## 8. Action Items After Meeting

| # | Action | Owner | Due |
|---|--------|-------|----|
| 1 | Decide on SSO method (signed redirect vs JWT vs OAuth) | Both | In meeting |
| 2 | WP dev: Document token format and signing approach | WP Dev | 1 week |
| 3 | WP dev: Provide test WP credentials and WP Fusion access | WP Dev | 1 week |
| 4 | Portal dev: Build SSO callback endpoint on TEST server | Portal Dev | 2 weeks |
| 5 | WP dev: Implement SSO trigger on WP login | WP Dev | 2 weeks |
| 6 | Both: Integration test on TEST environment | Both | 3 weeks |
| 7 | Define WP Fusion tag → Django role mapping | Both | In meeting |
| 8 | Decide on subscription webhook vs check-on-login | Both | In meeting |

---

*Prepared for WP Fusion / SSO integration planning meeting.*
