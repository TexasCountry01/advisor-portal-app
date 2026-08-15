# Provisioning and Role Setup Summary
Date: 2026-08-15

## Bottom line
The issue is not that the admin must log in as the new user to create them.

The real issue is that the app has two separate layers:

1. SSO / external access information from GHL or WordPress
2. the portal’s internal user roles and permissions inside this application

These are not automatically the same thing.

Because of that, a new user may be recognized by the external system, but they still need the correct internal role defined inside the portal before they see the right experience.

---

## What this means in practice
A user can be created and authenticated through SSO without anyone logging in as them.

However, the portal role inside this app still matters. For example:

- member
- technician
- administrator
- manager

The app is designed so that some of these internal roles are managed inside the portal, not simply inherited from a generic external tag.

This is why the admin may feel like they have to do an extra step: they are not logging in as the user to create them — they are setting the app-level identity and role that determines what the user should actually see.

---

## Why this happens
The external access tag tells the app whether the user has access at all.

It does not always define the complete internal portal role.

So the process is effectively:

- external system says: this user is allowed in
- portal says: what role do they have inside this app?
- app then decides what dashboard, permissions, and case access they should see

That second step is the one currently requiring admin attention.

---

## What is automatic vs. what still needs admin action

### Automatic
For standard member/delegate onboarding, the app supports first-login auto-provisioning.

That means the user can log in for the first time and the system can create or match their account without a manual impersonation step.

### Still admin-controlled
Staff roles such as technician, administrator, and manager are not expected to be fully derived from external tags.

Those roles are considered internal portal roles and should still be managed in the app.

---

## Recommended approach
The cleanest model is:

- use SSO for user creation and first login
- let new member/delegate users land in the app without impersonation
- keep internal staff roles controlled inside the portal
- make sure the external tags align with the app’s expected member/delegate access model

This gives the user the experience they want:

- they click login
- they are created or matched automatically
- they see what they are supposed to see on first login

without anyone having to log in as them first.

---

## Final takeaway
The bottom line is this:

The issue is not that the admin must log in as the new user.

The issue is that the app’s internal roles are separate from the external access tags, and that is what still requires an app-side role definition.

The system is already built to support the desired experience for member users, but the internal role mapping needs to be aligned cleanly with the external tagging model.
