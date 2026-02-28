# Advisor Portal — SSO Decisions Summary

**Date:** February 28, 2026  
**Purpose:** Summarize decisions and open questions from the SSO tag discussion

---

## Decisions Made

### 1. Tags Control Access — One Tag, One Login

- If a person has a portal tag → they can log in
- If the tag is removed → they cannot log in
- No other attributes (like "Active Member" status) are checked
- **Simple to grant. Simple to revoke.**

### 2. Administrators & Managers — No SSO, No Tags

- Administrator and Manager accounts are created directly in the portal
- They log in with a secure username and password — not through WordPress/SSO
- This eliminates the risk of someone giving themselves admin access through a tag
- Only a very small number of people have these roles

### 3. Delegates — No Tags, Managed by Benefits Technicians in the Portal

- Delegates (staff who submit cases on behalf of an advisor) do NOT get a portal tag
- Delegate assignments are managed **exclusively by Benefits Technicians** inside the portal
- Members (advisors) do NOT assign their own delegates — this is controlled by the Benefits Technician team
- **A person must already have an authorized user account in the portal before they can be assigned as a delegate** — Benefits Technicians cannot assign arbitrary people
- Delegates can be added, changed, or removed at any time — no GHL changes needed
- If a delegate is also independently a member (advisor), they get the `Portal: Member` tag for their own account, and the delegate assignment is separate

### 4. No Automation Yet

- Tags will be applied and removed manually for now
- Automation triggers will be decided and built later

---

## Open Decision: How to Handle Technician Levels

There are three levels of Benefits Technician in the portal. The question is whether the level is controlled by tags in GHL or by Admins inside the portal.

### Option 1 — One Technician Tag (levels managed in the portal)

| Tags Needed | |
|---|---|
| `Portal: Member` | For financial advisors |
| `Portal: Technician` | For all Benefits Technicians |

- The technician's level (1, 2, or 3) is set by an Admin or Manager inside the portal
- Promotions and level changes happen in the portal, not in GHL
- **Fewer tags to manage — only 2 total**

### Option 2 — Three Technician Tags (levels managed by tags)

| Tags Needed | |
|---|---|
| `Portal: Member` | For financial advisors |
| `Portal: Technician - Level 1` | New Technicians |
| `Portal: Technician - Level 2` | Standard Technicians |
| `Portal: Technician - Level 3` | Senior Technicians |

- The technician's level is determined by which tag they have
- To promote a technician, you swap the tag in GHL
- **4 tags total**

---

## Final Tag Count

| Scenario | Tags |
|----------|------|
| Tech levels in portal (Option 1) | **2 tags** |
| Tech levels by tag (Option 2) | **4 tags** |

Administrator, Manager, and Delegate access require **zero tags** — all managed in the portal.

---

## How Each Role Gets Access

| Role | How They Get In | Who Controls It |
|------|----------------|-----------------|
| **Member (Advisor)** | `Portal: Member` tag via SSO | GHL tag |
| **Benefits Technician** | Portal tag via SSO + level set in portal OR by tag | GHL tag + portal (or GHL only) |
| **Administrator** | Direct portal login (no SSO) | Portal admin |
| **Manager** | Direct portal login (no SSO) | Portal admin |
| **Delegate** | No login needed — acts under their advisor's cases | Benefits Technician (in portal) |

---

## Next Steps

| # | Action | Owner | Notes |
|---|--------|-------|-------|
| 1 | Decide on tech level approach (Option 1 or 2) | Chris | |
| 2 | Create the agreed-upon tags in GHL | Matt/Mike | No automation yet |
| 3 | Assign tags to initial users for testing | Chris/Matt | |
| 4 | Build SSO callback in the portal | Phil | Ready to start once tags are confirmed |
| 5 | Test SSO login flow on test server | Phil + Mike | |

---

*Awaiting decision on technician level approach to finalize the tag list.*
