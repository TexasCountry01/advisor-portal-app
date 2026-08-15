# User Provisioning and Role Flow Analysis
Date: 2026-08-15
Scope: Review document for admin-side user setup, SSO provisioning, and role-mapping options.

## Executive summary
The app already supports a "no impersonation required" workflow for standard member/delegate users, but not in the way the current business process is assuming.

There are two separate concepts in this system:

1. SSO identity / access tags from the external system (WordPress / GoHighLevel / OAuth provider)
2. the portal's internal Django role model and permission model

These are not identical, and that distinction is the root of the admin confusion.

The app does allow a user to be created automatically on first SSO login, but the portal role is not always determined from the same generic access tag that the admin is setting in GHL. In practice, this means:

- a user can be created and logged in without admin impersonation
- but if the external tag set does not match the internal role model, the admin still has to set the app-level role manually

This is why it feels like there is a required "log in as them before giving them credentials" step, even though the system does not strictly require it.

---

## The key architectural fact
The portal is built around a custom user model in [accounts/models.py](../accounts/models.py#L4-L61).

The relevant fields are:

- `role` — portal-level role, values include `member`, `technician`, `administrator`, `manager`
- `user_level` — technician level only
- `workshop_code` — member-level workshop assignment
- `is_pure_delegate` — delegate indicator
- `contact_id` — immutable external CRM identity key

This means the application is not using the external identity system as the final source of truth for everything. It keeps a portal-side user record and role structure.

---

## The current user creation flow

### A. Manual admin creation path
The direct portal creation flow is implemented in [accounts/forms.py](../accounts/forms.py#L7-L159) and [accounts/views.py](../accounts/views.py#L23-L104).

This flow does the following:

- creates a real Django user record
- sets username, email, first name, last name
- sets a password
- sets role
- sets `user_level` if technician
- sets `workshop_code` if member
- saves the user

There is no requirement to log in as the user in this flow.

This is the most direct proof that the app supports admin-side provisioning without impersonation.

### B. SSO first-login provisioning path
The SSO flow is implemented in [accounts/views_sso.py](../accounts/views_sso.py#L38-L118) and the actual matching/creation logic is in [accounts/sso.py](../accounts/sso.py#L265-L407).

The flow is:

1. user clicks SSO login
2. app redirects to WP/OAuth authorization
3. app exchanges auth code for token
4. app fetches the WP resource payload
5. `get_or_create_user_from_sso()` matches by `contact_id` or email
6. if not found, a new user is created
7. the user is logged in immediately

The final create branch explicitly creates a user with `User.objects.create(...)` and then calls `set_unusable_password()`. This is a clear sign that the app expects SSO-based login to be the auth path; the user does not need a manual password for first access and does not need to be impersonated by an admin.

---

## Why the process feels wrong to the admin
The confusion is caused by the app's separation between tag-based access and internal role assignment.

### What is being set externally
The external system is expected to send portal access tags, which are defined in [accounts/sso.py](../accounts/sso.py#L35-L55):

- `Portal access: Member` → `member`
- `Portal access: Delegate` → `member` with delegate flag

This mapping is intentionally narrow. It is not designed to cover all of the app's internal role meanings.

### What is still controlled inside the app
The app's internal role model includes:

- `member`
- `technician`
- `administrator`
- `manager`

The comments in [accounts/sso.py](../accounts/sso.py#L15-L33) make this explicit:

- Technician/Manager/Admin roles are managed inside the portal admin panel
- they are not controlled by SSO tags

This means that for a new member-facing user, the admin may be setting some generic external tag, but the app still needs the portal-side record to reflect the final internal role and workshop / member context.

So the feeling of "I have to log in as them first" is really a symptom of a role-mapping gap, not an actual impersonation requirement.

---

## The real root cause: external tags are not the same as portal roles
This is the heart of the issue.

A generic access tag in GHL is not the same thing as the app's internal permission model.

Example:

- GHL tag says: “Portal access: Member”
- app role may still need to be specifically set to `member`
- workshop code may need to be assigned
- delegate status may need to be determined
- some user-level or staff permissions may need to be assigned separately

The app does not assume that the external system knows enough to define all portal permissions. This is why the admin still has to do final adjustments inside the app.

---

## What the app does automatically
The SSO login logic does do a fair amount automatically once a user hits the portal:

- match by `contact_id` or email
- create user if absent
- sync name, email, workshop code, phone
- sync delegate flag
- set role if the tag determines it
- skip the tag requirement for existing portal-managed roles
- log audit events

This behavior is implemented in [accounts/sso.py](../accounts/sso.py#L265-L407).

That is the app's intended zero-friction model for normal users.

---

## What the app does not do automatically
The app does not automatically infer all portal role definitions from arbitrary GHL tags.

That means no automatic conversion from a business “new customer” or “member” tag into the full internal app model if the business is expecting more than a basic `member` profile.

In practical terms, the app will not automatically handle every custom relationship needed by a member-facing customer workflow unless those details are encoded in a way the app already understands.

Examples of things that may still require admin-side data setup:

- portal role for staff vs member
- member workshop code mapping
- delegate status
- user permission flags
- internal access grants

---

## The actual flow by user type

### 1) Member / customer-facing user
Desired flow:

- user gets SSO tag in GHL
- admin sets the user up in the source system
- first login auto-creates / matches the portal user
- user sees the correct member dashboard

This is the intended flow for self-service onboarding.

Current reality:

- works if the external tags align to the app's limited member/delegate mapping
- may still require final portal-side role or metadata changes if the external source is using different labels or business logic

### 2) Pure delegate user
The app uses the delegate flag pattern. See [accounts/sso.py](../accounts/sso.py#L203-L260).

- `Portal access: Delegate` yields `role='member'` but `is_pure_delegate=True`

This is a design choice: delegates are still ordinary app users, but they behave differently in the member/delegate access model.

### 3) Technician / manager / administrator
The code comments explicitly state these roles are not managed by SSO tags. See [accounts/sso.py](../accounts/sso.py#L15-L33) and [accounts/sso.py](../accounts/sso.py#L286-L311).

These must be created or assigned inside the admin portal.

This is a good example of a case where the app intentionally separates external SSO access from internal app role structure.

---

## Where the admin's expectation collides with the design
The admin expectation is roughly:

- if GHL says this user is a member, the app should know exactly how to set them up

The app's actual design is more like:

- GHL emits access tags only
- the app matches the user and applies the portal's internal rules
- some portal-side configuration still matters

This is not a bug in the sense of “an admin must first log in as them.” It is a design mismatch where the identity source is being treated like a complete admin authority for the app, when in reality it is only part of the provisioning input.

---

## Options available

### Option 1: Keep the current SSO-first model and accept some admin cleanup
Best when:

- the app should be mostly self-service for customer users
- generic tags are acceptable as the trigger for access

Pros:

- no need to impersonate users
- easy onboarding for standard member users
- matches the app’s intended SSO flow

Cons:

- if the source tags are not perfectly aligned to internal rules, some manual admin work remains
- staff roles still require admin-side provisioning

### Option 2: Admin creates the user record directly in the portal, then user uses SSO later
Best when:

- you want the portal metadata set before the user logs in
- you want full control over each user’s role and fields

Pros:

- deterministic setup
- no assumptions about tag mapping
- easier for unusual or edge-case accounts

Cons:

- requires admin effort for every user
- less self-service

### Option 3: Standardize the external tags so they map cleanly to internal roles
Best when:

- the business wants a fully automated onboarding model
- the GHL/CRM system can emit the exact app-ready tags and metadata

Pros:

- minimal admin work
- better long-term scalability
- closer to the original desired user experience

Cons:

- requires an agreed tag schema and governance
- still does not fully replace internal staff/admin role controls

### Option 4: Hybrid model
Best when:

- member/delegate onboarding should be automated
- technician/admin role creation should remain admin-controlled

This is the most practical and least risky option.

Pros:

- clean user experience for customer-facing users
- preserves admin control for internal roles
- matches the app's actual architecture

Cons:

- requires clear product rules for which roles are external vs internal

---

## Recommended direction
The best option for this app is a hybrid model:

- allow normal member / delegate onboarding to be auto-provisioned via SSO with no impersonation required
- keep admin-managed roles such as technician, administrator, and manager inside the portal
- standardize external tags so they reflect the app's real role model as closely as possible

This aligns with the actual code architecture rather than forcing a manual impersonation workaround.

---

## Conclusion
The app does not require an admin to log in as the user to provision a new member/delegate account.

What it does require is a clean alignment between:

- external access tags
- the app's internal role model
- and any member-specific setup data such as workshop code and delegate status

The admin’s current frustration is therefore not due to a hidden requirement to impersonate the user. It is due to the fact that the external tagging model and the internal portal role model are not the same thing.

That is the workflow issue to solve if the goal is “first login, correct app state, no extra admin step.”
