# WP Fusion SSO Implementation — Working Document

**Created:** March 1, 2026
**Last Updated:** March 1, 2026 (SSO infrastructure built, dashboard toggle built)
**Status:** SSO plumbing complete — blocked on WP dev confirming endpoints + sample JSON

---

## 1. Architecture Decision

**SSO Method:** OAuth2 Authorization Code Grant
**OAuth Provider:** miniOrange OAuth Server (WordPress plugin)
**Authentication:** Handled by GHL (GoHighLevel) — WP/miniOrange passes authorization tags only
**Protocol:** Standard OAuth2 (not signed redirect, not JWT, not shared cookie)

### Two Environments

| Environment | WP Site | Portal Server |
|---|---|---|
| Test | `test-reports.profeds.com` | `https://157.245.141.42` |
| Production | `reports.profeds.com` | `https://104.248.126.74` |

SSO setup is identical on both WP sites. `WP_OAUTH_BASE_URL` env var determines which site to use.

---

## 2. OAuth2 Endpoints

**Test site (`test-reports.profeds.com`):**

| Endpoint | URL |
|---|---|
| Authorization | `https://test-reports.profeds.com/wp-json/moserver/authorize` |
| Token | `https://test-reports.profeds.com/wp-json/moserver/token` |
| Resource (User Info) | `https://test-reports.profeds.com/wp-json/moserver/resource` |

**Production site (`reports.profeds.com`):**

| Endpoint | URL |
|---|---|
| Authorization | `https://reports.profeds.com/wp-json/moserver/authorize` |
| Token | `https://reports.profeds.com/wp-json/moserver/token` |
| Resource (User Info) | `https://reports.profeds.com/wp-json/moserver/resource` |

**Status:** ⬜ Awaiting confirmation from WP developer that these are correct

---

## 3. Client Credentials

| Parameter | Value |
|---|---|
| Client ID | `GIbWesmTFmehLeDLZCqRjpyfUcWDscSa` |
| Client Secret | `luHBoeGKSryxWdeFBiNyPSTaXxSOboeo` |
| Scope | `openid profile email` |

**Source:** miniOrange_OAuth_server_collection.json (Postman collection from WP developer)
**Status:** ⬜ Need to confirm if same credentials work for both sites or if separate sets are needed

---

## 4. OAuth2 Flow

```
Step 1: User clicks "Login with ProFeds" on the portal
        ↓
Step 2: Portal redirects to WordPress authorization endpoint:
        https://{WP_OAUTH_BASE_URL}/wp-json/moserver/authorize?
          client_id=GIbWesmTFmehLeDLZCqRjpyfUcWDscSa
          &redirect_uri={SITE_URL}/accounts/sso/callback/
          &response_type=code
          &scope=openid+profile+email
          &state=<random_csrf_token>
        ↓
Step 3: User logs into WordPress (or is already logged in)
        ↓
Step 4: WordPress redirects back to our callback with auth code:
        {SITE_URL}/accounts/sso/callback/?code=AUTH_CODE&state=<token>
        ↓
Step 5: Our server exchanges auth code for access token:
        POST {WP_OAUTH_BASE_URL}/wp-json/moserver/token
        Body: client_id, client_secret, code, redirect_uri, grant_type=authorization_code
        ↓
Step 6: Our server fetches user profile:
        GET {WP_OAUTH_BASE_URL}/wp-json/moserver/resource
        Header: Authorization: Bearer <access_token>
        ↓
Step 7: Parse JSON response → match/create Django user → create session → redirect to dashboard
```

---

## 5. Callback URLs to Register

The WP developer must register these redirect URIs in the miniOrange OAuth Server settings on **each respective WP site**:

| WP Site | Callback URL to Register |
|---|---|
| `test-reports.profeds.com` | `https://157.245.141.42/accounts/sso/callback/` |
| `reports.profeds.com` | `https://104.248.126.74/accounts/sso/callback/` |

**Status:** ⬜ Not yet registered — included in email to WP developer

---

## 6. Test Credentials

| Field | Value |
|---|---|
| Email | `kennedy+testwpcreateuser128@profeds.com` |
| Password | `hell0th1sisatest` |
| Tags | Has portal tags applied (need to confirm which ones) |

### WP Test Accounts Created

3 test members and 3 test delegates have been set up in WordPress by the WP developer.

| Type | Count | Status |
|---|---|---|
| Test Members (advisors) | 3 | ⬜ Need usernames/emails from WP dev |
| Test Delegates (admin assistants) | 3 | ⬜ Need usernames/emails from WP dev |

---

## 7. Tag Strategy (Decided — Updated 2026-03-01)

### Authentication vs Authorization

- **Authentication** is handled by **GHL (GoHighLevel)** — not by tags
- **Authorization** (who can access the portal) is controlled by **2 tags only**
- All other roles (Technician, Manager, Administrator) are managed inside the portal's admin panel

### Authorization Tags (2 total)

| Tag | Maps To | Django Value | Who Gets It |
|---|---|---|---|
| `Portal access: Member` | `role` | `member` | Financial advisors who submit their own cases |
| `Portal access: Delegate` | `role` | `member` (with delegate flag) | Administrative assistants who only act on behalf of advisors |

### No Tags Needed For

| Role | Reason |
|---|---|
| Technician | Created directly in portal admin panel |
| Administrator | Created directly in portal admin panel |
| Manager | Created directly in portal admin panel |

### Role Protection Rule (Implemented 2026-03-01)

**Portal-managed roles are NEVER overwritten by SSO.** When a user with role `administrator`, `manager`, or `technician` logs in via SSO, their role is preserved — SSO will not reset them to `member` or `delegate`.

- SSO can only set/change roles for users currently assigned `member` or `delegate`
- This protection is enforced in `accounts/sso.py` → `_sync_user_fields()`
- The protected set: `PORTAL_MANAGED_ROLES = {'technician', 'manager', 'administrator'}`
- All other user fields (name, email, workshop_code, contact_id) still sync normally on each SSO login

**Why:** Administrators, managers, and technicians are promoted manually via the Django admin panel (`/admin/`). Without this protection, an SSO login would overwrite their role back to `member` based on their WP tags, locking them out of their dashboard.

### Tag-Based Access Rule

- Has a portal access tag → can log in via SSO
- Tag removed → locked out
- No other attributes checked (not "Active Member" status, not subscription, nothing else)

### Key Distinction: Member Tag vs Delegate Tag

- **Advisors** get `Portal access: Member` — they have their own cases
- **Admin assistants** get `Portal access: Delegate` — they never have their own cases, they only act on behalf of assigned members
- **Members who are ALSO delegates** for other members get `Portal access: Member` only — the delegate assignment is managed in the portal by Benefits Techs, not by tags

---

## 8. Delegate Rules (Decided)

| Rule | Detail |
|---|---|
| Who assigns delegates | Benefits Technicians only (not members/advisors) |
| Who can be a delegate | Any user with an existing portal account |
| Delegate-of-delegate | **Not allowed** — no chaining |
| Delegate for multiple members | Allowed |
| Member as delegate | Allowed — a member can also be a delegate for other members (uses `Portal access: Member` tag, not `Portal access: Delegate`) |
| Delegate with no assignments | Sees blank member dashboard |
| Delegate login | SSO via `Portal access: Delegate` tag; Benefits Tech then assigns them to member(s) |

---

## 8a. Dashboard Toggle Behavior (Decided + Built)

The member dashboard has a **toggle** that switches between "My Cases" and "Delegate Cases". The toggle only appears for users who are both a member AND a delegate for other members.

**✅ IMPLEMENTED** in `cases/views.py` (`member_dashboard`) and `cases/templates/cases/member_dashboard.html`.

### Who Sees What

| User Type | Tag | Dashboard Behavior |
|---|---|---|
| **Pure member** (advisor, not a delegate) | `Portal access: Member` | Normal dashboard — sees own cases only. No toggle. |
| **Pure delegate** (admin assistant, not a member) | `Portal access: Delegate` | Sees "Delegate Dashboard" heading. Shows only assigned members' cases. No toggle. |
| **Member who is also a delegate** | `Portal access: Member` | Sees toggle: **My Cases** \| **Delegate Cases**. "My Cases" = their own. "Delegate Cases" = all assigned members' cases. |

### Toggle Details

- **My Cases** — Shows the member's own submitted cases (default view)
- **Delegate Cases** — Shows all cases for every member they've been assigned to as a delegate, grouped or filterable by member name
- The toggle UI should be similar to the benefits-technician dashboard view
- Only members with active delegate assignments see the toggle
- Pure delegates (`Portal access: Delegate` tag) always see assigned members' cases — no toggle needed since they have no cases of their own
- Delegate view shows an info bar listing which members' cases are being displayed
- Stats and filters are scoped to the active view

---

## 8b. Case Submission — Delegate UX (Decided + Built)

When a delegate submits a case, the submission page must account for the fact that a delegate may be assigned to **multiple members**.

### Advisor Name + Workshop Code Field Behavior

**Greyed out (readonly)** UNLESS the delegate has more than one advisor AND more than one workshop code.

| Scenario | Advisor Field | Workshop Code Field |
|---|---|---|
| Pure member submitting for self | Greyed out (their name) | Greyed out (their code) |
| Delegate with 1 assigned member | Greyed out (that member's name) | Greyed out (that member's code) |
| Delegate with multiple members, **same** workshop code | Greyed out (first member) | Greyed out (shared code) |
| Delegate with multiple members, **different** workshop codes | **Dropdown** — select advisor | **Auto-fills** from selected advisor (readonly) |
| Member who is also delegate for 1 member (same workshop) | Greyed out | Greyed out |
| Member who is also delegate for members (different workshops) | **Dropdown** — self + assigned members | **Auto-fills** from selection (readonly) |

### Key Rules
- The workshop code **always** comes from the member's profile, not the delegate's
- The delegate never types a workshop code — it's always derived from the selected member
- When dropdown is shown, the workshop code auto-fills on advisor selection

---

## 9. Field Mapping: OAuth Resource → Django User

Based on earlier WP JSON sample. **Awaiting confirmation from actual resource endpoint response.**

| WP JSON Field | Django Field | Notes |
|---|---|---|
| `contact_id` | `contact_id` **(new field)** | CRM contact ID — immutable match key between WP/CRM and portal |
| `email` | `email` + `username` | Updated on each SSO login |
| `first_name` | `first_name` | |
| `last_name` | `last_name` | |
| `member_code` | `workshop_code` | e.g., `"MRP"` |
| `wpf_tags` | `role` + `user_level` | Parsed for portal tags |
| `phone` | `phone` | May not be in response |
| `secondary_contact_type` | — | Not used (tags are sole access control) |

**⚠️ BLOCKER:** Need actual JSON response from resource endpoint to confirm field names.

---

## 9a. Data Sync Strategy (Decided)

The CRM **contact ID** is the unique identifier linking WP Fusion / CRM to the portal.

### Three Sync Mechanisms

#### 1. Initial Population Script (one-time)
- Django management command: `python manage.py sync_wp_users`
- Calls WP/CRM API to pull all users with portal tags (`Portal access: Member`, `Portal access: Delegate`)
- Creates portal `User` records with `contact_id`, name, email, role, workshop_code
- Run once before SSO goes live to seed the database
- Can also be re-run safely (upsert by `contact_id`)

#### 2. Login-Time Validation (every SSO login)
- The SSO callback already hits the resource endpoint (Step 6 of OAuth flow)
- After parsing the response, compare against stored portal data:
  - Name changed? → update `first_name`, `last_name`
  - Email changed? → update `email`
  - Tags changed? → update `role` (e.g., member lost tag → deactivate)
  - Workshop code changed? → update `workshop_code`
- No extra API call needed — the resource response provides everything
- Log any changes to AuditLog for compliance

#### 3. Manual Resync Button (on-demand)
- Located on the **Delegate Management** page (Benefits Tech only)
- Triggers an API call to the resource endpoint for a specific user
- Useful when a Benefits Tech notices stale data mid-session
- Shows what changed (before → after) in a confirmation dialog
- Future: could also sync from a webhook push (Phase 3)

---

## 10. Django Model Changes Required

### User model (`accounts/models.py`)

✅ **DONE** — `contact_id` field added (migration `0007_user_contact_id`):
```python
contact_id = models.IntegerField(
    unique=True,
    null=True,
    blank=True,
    help_text='WP Fusion CRM contact ID — immutable SSO identifier for sync'
)
```

### Delegate model consolidation

✅ **DONE** — Consolidated into `MemberDelegate` model (migration `0006_memberdelegate`).
Old models (`AdvisorDelegate`, `DelegateAccess`, `WorkshopDelegate`) marked deprecated, still in DB.

---

## 11. Implementation Phases

### Phase 1: Portal-Internal Work (No WP developer needed)
- [x] Add `contact_id` to User model (migration `0007`)
- [x] Consolidate delegate models → `MemberDelegate` (migration `0006`)
- [x] Delegate management UI (working assign/remove)
- [x] Wire delegates into member dashboard (toggle — My Cases / Delegate Cases)
- [x] Wire delegates into case submission (greyed-out / dropdown UX)

### Phase 2: SSO Integration (Requires WP developer coordination)
- [x] Build SSO service module (`accounts/sso.py`)
- [x] Build SSO views (`accounts/views_sso.py` — `sso_login` + `sso_callback`)
- [x] Add SSO URL routes (`/accounts/sso/login/`, `/accounts/sso/callback/`)
- [x] Add OAuth settings to `config/settings.py` (env-driven, test/prod agnostic)
- [x] Add "Login with ProFeds Account" SSO button to login page
- [x] Tag parsing and role mapping (2 tags: `Portal access: Member`, `Portal access: Delegate`)
- [x] Auto-provisioning on first SSO login
- [x] Login-time data sync (compare resource response → update portal → AuditLog)
- [ ] **Update `_extract_user_data()` field mapping** (⬜ blocked on sample JSON from WP dev)
- [ ] Register callback URLs in miniOrange settings (⬜ email sent to WP dev)
- [ ] End-to-end SSO testing with test credentials

### Phase 2a: Initial Data Population
- [ ] Build `sync_wp_users` management command
- [ ] Call WP/CRM API to pull all tagged users
- [ ] Create/update portal `User` records by `contact_id`
- [ ] Run on TEST server first, then PROD

### Phase 3: Real-Time Sync & Manual Resync
- [ ] Resync button on Delegate Management page
- [ ] Build WP webhook endpoint (`/api/wp-webhook/`)
- [ ] Subscription status → `is_active` sync
- [ ] Profile field change sync
- [ ] Auto-revoke delegate access on account deactivation

---

## 12. Open Questions / Blockers

| # | Question | Status | Answer |
|---|---|---|---|
| 1 | What JSON fields come back from the resource endpoint? | ⬜ Email sent to WP dev | Need sample JSON — this is the only code blocker |
| 2 | Are tags included in the OAuth resource response? | ⬜ Email sent to WP dev | Need field name and format |
| 3 | Has WP developer registered our callback URLs? | ⬜ Email sent to WP dev | Test: `157.245.141.42`, Prod: `104.248.126.74` |
| 4 | Tech levels: handled inside portal admin panel | ✅ Decided | No tags needed — managed in portal |
| 5 | Is `member_code` / `workshop_code` in OAuth response? | ⬜ Email sent to WP dev | Maps to `workshop_code` |
| 6 | Are Client ID/Secret valid for both WP sites? | ⬜ Email sent to WP dev | May need separate credentials per site |
| 7 | Correct domain for WP site? | ✅ Decided | `reports.profeds.com` (prod), `test-reports.profeds.com` (test) |
| 8 | What are the 3 test member + 3 test delegate credentials? | ⬜ Email sent to WP dev | Need from WP dev — testing on `test-reports.profeds.com` |

---

## 13. Decision Log

| Date | Decision | Notes |
|---|---|---|
| 2026-02-28 | Tags = sole access control | One tag = access, remove tag = no access |
| 2026-02-28 | No SSO for Admin/Manager | Created directly in portal |
| 2026-02-28 | Delegates managed by Benefits Techs | No tags, no SSO, portal-only |
| 2026-02-28 | No automation yet | Tags applied manually for now |
| 2026-03-01 | OAuth2 is the SSO method | miniOrange OAuth Server, not signed redirect or JWT |
| 2026-03-01 | Test credentials received | kennedy+testwpcreateuser128@profeds.com |
| 2026-03-01 | Delegate mgmt mock UI built | Accessible via Management dropdown on tech dashboard |
| 2026-03-01 | Removed active/inactive from delegate UI | Per Chris meeting — delegates are assigned or removed, no status toggle |
| 2026-03-01 | `Portal access: Delegate` tag for admin assistants | Separate from `Portal access: Member` |
| 2026-03-01 | Dashboard toggle for member+delegate | Members who are also delegates see a My Cases / Delegate Cases toggle |
| 2026-03-01 | Pure delegates see assigned cases only | "Delegate Dashboard" heading, no toggle |
| 2026-03-01 | `MemberDelegate` model built | Replaces AdvisorDelegate/DelegateAccess/WorkshopDelegate |
| 2026-03-01 | Delegate mgmt page is functional | Real assign/remove via POST, no more mock data |
| 2026-03-01 | `contact_id` replaces `wp_user_id` | CRM contact ID is the immutable sync key |
| 2026-03-01 | 3-tier sync strategy decided | Initial script → login-time validation → manual resync button |
| 2026-03-01 | 3 test members + 3 test delegates in WP | Set up by WP developer, need credentials |
| 2026-03-01 | Delegate case submission needs member dropdown | Delegate picks member → workshop code auto-fills |
| 2026-03-01 | Only 2 authorization tags (not 3) | Authentication by GHL; tags for authorization only |
| 2026-03-01 | Technician/Manager/Admin roles via admin panel | No SSO tags — created directly in portal |
| 2026-03-01 | Correct WP domain is `reports.profeds.com` | Test site: `test-reports.profeds.com` |
| 2026-03-01 | SSO infrastructure built | `accounts/sso.py`, `accounts/views_sso.py`, settings, login button |
| 2026-03-01 | `contact_id` field added to User model | Migration `0007_user_contact_id` applied |
| 2026-03-01 | Dashboard toggle built | My Cases / Delegate Cases with info bar, scoped stats |
| 2026-03-01 | Email sent to WP developer | Requesting endpoints, sample JSON, callback registration, tags, test accounts |

---

## 14. Files Modified / Created

| File | Change | Status |
|---|---|---|
| `accounts/models.py` | `contact_id` field, `MemberDelegate` model, deprecate old models | ✅ Done (migrations `0006`, `0007`) |
| `accounts/sso.py` | SSO service: OAuth2 flow, tag→role mapping, user provisioning, login-time sync | ✅ Built |
| `accounts/views_sso.py` | `sso_login` + `sso_callback` views | ✅ Built |
| `accounts/views.py` | delegate_management view (functional) | ✅ Done |
| `accounts/admin.py` | Register `MemberDelegate` in admin | ✅ Done |
| `accounts/urls.py` | `/accounts/sso/login/`, `/accounts/sso/callback/`, `/delegate-management/` | ✅ Done |
| `accounts/templates/accounts/delegate_management.html` | Delegate mgmt with working assign/remove forms | ✅ Built |
| `accounts/migrations/0006_memberdelegate.py` | MemberDelegate table | ✅ Applied |
| `accounts/migrations/0007_user_contact_id.py` | `contact_id` field on User | ✅ Applied |
| `cases/views.py` | Dashboard toggle: My Cases / Delegate Cases with scoped stats | ✅ Built |
| `cases/templates/cases/technician_dashboard.html` | Management dropdown → Delegate Management | ✅ Updated |
| `cases/templates/cases/member_dashboard.html` | Dashboard toggle buttons, delegate info bar, conditional heading | ✅ Built |
| `cases/views_submit_case.py` | Wire MemberDelegate into case submission | ✅ Done — greyed-out/dropdown logic |
| `cases/templates/cases/submit_case.html` | Advisor dropdown + auto-fill workshop code | ✅ Done — conditional greyed-out vs dropdown |
| `config/settings.py` | OAuth settings: `WP_OAUTH_BASE_URL`, client ID/secret, endpoint URLs | ✅ Done (env-driven) |
| `templates/core/login.html` | "Login with ProFeds Account" SSO button + message display | ✅ Done |
| `requirements.txt` | `requests==2.32.5` already present (no extra lib needed) | ✅ OK |
| `WP_DEV_EMAIL.txt` | Plain-text email to WP developer with all requirements | ✅ Created |
| `WP_DEV_SSO_REQUIREMENTS.md` | Formatted version of the WP developer email | ✅ Created |
| `accounts/management/commands/sync_wp_users.py` | Initial population script | ⬜ Blocked on sample JSON |
| `miniOrange_OAuth_server_collection.json` | Reference file (Postman) | ✅ Added to workspace |

---

*This document will be updated as decisions are made and implementation progresses.*
