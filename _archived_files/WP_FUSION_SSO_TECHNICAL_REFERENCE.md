# WP Fusion SSO Integration — Technical Reference

**Date:** February 28, 2026  
**System:** ProFeds Advisor Portal (Django 5.0.7)  
**Portal URLs:** https://reports.profeds.com (PROD) / https://test-reports.profeds.com (TEST)

---

## 1. Current Application Architecture

### User Model (`accounts/models.py`)

| Field | Type | Purpose |
|-------|------|---------|
| `username` | string | Login identifier (unique) |
| `password` | string | Django-hashed (PBKDF2) |
| `email` | string | Member's email |
| `first_name` / `last_name` | string | Display name |
| `role` | string | One of: `member`, `technician`, `administrator`, `manager` |
| `user_level` | string | Technician only: `level_1`, `level_2`, `level_3` |
| `workshop_code` | string | Member's workshop affiliation (e.g., "MRP") |
| `phone` | string | Contact number |
| `is_active` | boolean | Can log in when True |
| `font_size` | string | Accessibility preference |

### Four Portal Roles

| Role | Dashboard | Access |
|------|-----------|--------|
| **Member** (Financial Advisor) | Member Dashboard | Own cases only |
| **Benefits Technician** | Technician Dashboard | All cases, tiered by level |
| **Administrator** | Admin Dashboard | Full system access |
| **Manager** | Manager Dashboard | Read-only analytics |

### Benefits Technician Tiers

| Tier | Description | Significance |
|------|-------------|--------------|
| Level 1 | New Technician | Requires quality review on all cases |
| Level 2 | Technician | Standard workflow |
| Level 3 | Senior Technician | Can perform quality reviews |

### How Cases Link to Users

Cases are linked via Django ForeignKey on the `member` field → points to the Django User's **internal primary key (integer ID)**, NOT email or workshop code. This means if a member changes their email, all their cases remain correctly linked.

```
Case.member → ForeignKey → User.id (Django PK, auto-increment integer)
```

---

## 2. Sample WP JSON Response (from SSO endpoint)

```json
{
    "id": 705,
    "ID": 705,
    "sub": 705,
    "email": "retirehappy1650@gmail.com",
    "username": "retirehappy1650@gmail.com",
    "first_name": "Anna",
    "last_name": "Haber",
    "nickname": "Anna Haber",
    "display_name": "Anna Haber",
    "member_code": "MRP",
    "secondary_contact_type": "Member - Active",
    "contact_id": "L40vFVYiJnG0RQJDUbsE",
    "wpf_tags": [ ... 80+ tags ... ]
}
```

---

## 3. Field Mapping: WP JSON → Django User Model

| WP JSON Field | Django Field | Mapping Type | Notes |
|---|---|---|---|
| `id` | `wp_user_id` **(NEW field needed)** | **Primary match key** | Immutable WP user ID — must be used to link users because emails change |
| `email` | `email` + `username` | Direct map | Updated on each SSO login if changed in WP |
| `first_name` | `first_name` | Direct map | |
| `last_name` | `last_name` | Direct map | |
| `member_code` | `workshop_code` | Direct map | e.g., `"MRP"` |
| `secondary_contact_type` | `is_active` (supplementary) | Partial | `"Member - Active"` suggests active; need to confirm all possible values |
| `wpf_tags` | `role` + `user_level` | **Needs new tags** | No existing tags map to portal roles — see Section 4 |
| `phone` | `phone` | **Missing from JSON** | Not present in sample — ask if available |
| `contact_id` | — | Not used | CRM reference (GoHighLevel or similar) |
| `nickname` / `display_name` | — | Not used | Django constructs display name from first + last |

---

## 4. New WP Fusion Tags Required

**No existing WP Fusion tags map to the portal's 4 roles or 3 technician tiers.** The following 7 tags must be created in WP Fusion:

### Role Tags (mutually exclusive — one per user)

| Tag Name | Maps To | Django Value |
|----------|---------|-------------|
| `advisor-portal -> role: member` | `role` | `member` |
| `advisor-portal -> role: benefits-technician` | `role` | `technician` |
| `advisor-portal -> role: administrator` | `role` | `administrator` |
| `advisor-portal -> role: manager` | `role` | `manager` |

### Tier Tags (only for benefits-technicians)

| Tag Name | Maps To | Django Value |
|----------|---------|-------------|
| `advisor-portal -> tier: level-1` | `user_level` | `level_1` |
| `advisor-portal -> tier: level-2` | `user_level` | `level_2` |
| `advisor-portal -> tier: level-3` | `user_level` | `level_3` |

The `advisor-portal ->` prefix keeps these namespaced and easy to identify in the `wpf_tags` array.

---

## 5. Why `wp_user_id` is Critical (Not Email)

**Problem:** Members frequently change their email addresses.

**Risk without `wp_user_id`:** If we match users by email and a member changes their email in WordPress:
- SSO login wouldn't find their existing Django account
- A duplicate account could be created
- Their case history would be orphaned on the old account

**Solution:** Store the WordPress `id` (e.g., `705`) as `wp_user_id` on the Django User model. This is immutable and always ties the WP user to the correct Django account regardless of email changes.

**SSO Login Flow:**
1. Receive SSO token with WP `id: 705`
2. Look up Django user by `wp_user_id = 705`
3. If found → log them in, update email/name if changed
4. If not found → auto-create new Django user with `wp_user_id = 705`
5. Redirect to role-based dashboard

---

## 6. SSO Callback Endpoint (To Be Built)

```
POST/GET https://reports.profeds.com/sso/callback/
```

**Steps:**
1. Receive token from WP redirect
2. Validate token signature and expiration
3. Extract `id`, `email`, `first_name`, `last_name`, `member_code`, `wpf_tags`
4. Match user by `wp_user_id` (or create new)
5. Parse `wpf_tags` for role and tier
6. Update user profile fields if changed
7. **Role protection check:** If user's current role is `administrator`, `manager`, or `technician`, skip role update (preserve portal-assigned role)
8. Create Django session
9. Redirect to appropriate dashboard
10. Log SSO event in audit trail

---

## 7. Webhook Endpoint (To Be Built)

```
POST https://reports.profeds.com/api/wp-webhook/
```

**Purpose:** Receive real-time notifications from WP when:
- Subscription activated/deactivated → toggle `is_active`
- Profile data changes → sync fields
- New member created → auto-provision Django account

**Expected Payload:**
```json
{
    "event": "subscription_changed",
    "wp_user_id": 705,
    "email": "member@example.com",
    "status": "active",
    "workshop_code": "MRP",
    "timestamp": "2026-02-28T12:00:00Z",
    "signature": "<HMAC signature>"
}
```

---

## 8. Model Change Required

Add one field to `accounts/models.py` → `User` model:

```python
wp_user_id = models.IntegerField(
    unique=True,
    null=True,
    blank=True,
    help_text='WordPress user ID — immutable SSO identifier'
)
```

---

## 9. Existing Integration Points

The codebase has **40+ WP Fusion placeholder comments** across:

| File | Placeholders |
|------|-------------|
| `accounts/models.py` | Subscription status sync, delegate auto-revocation, credit calculation |
| `accounts/views.py` | Profile sync on save, delegate validation |
| `accounts/forms.py` | WP subscription display, office filtering, credit source |
| Templates | WP status display, office filters, credit indicators |

Markers: `# WP FUSION PLACEHOLDER:` and `# WP FUSION INTEGRATION NOTES:`

---

## 10. Open Questions for WP Developer

| # | Question | Impact |
|---|----------|--------|
| 1 | Can the 7 role/tier tags be created and assigned in WP Fusion? | **Blocker** — cannot determine user role without these |
| 2 | Is `id` (705) the immutable WordPress user ID? | Must confirm it won't change |
| 3 | Is `secondary_contact_type` the definitive subscription status? What are all possible values? | Determines `is_active` logic |
| 4 | Is `phone` available in the JSON payload? | Missing from sample |
| 5 | Will every SSO user have a `member_code`? | Only members may have workshop codes |
| 6 | What token format for SSO? Signed redirect URL, JWT, or other? | Determines callback validation logic |
| 7 | What signing key or shared secret for token verification? | Security requirement |
| 8 | Can WP Fusion fire webhooks on subscription changes? | Needed for real-time `is_active` sync |
| 9 | Should technicians/admins also use SSO, or keep direct Django login? | Staff may not be WP members |
| 10 | What is the token expiration window? (Suggest 60 seconds for redirects) | Security requirement |

---

*Prepared: February 28, 2026*
