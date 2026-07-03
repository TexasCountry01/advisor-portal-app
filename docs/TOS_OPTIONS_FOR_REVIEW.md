# Terms of Service — Options for Review

**Prepared by:** ProFeds Development  
**Date:** June 21, 2026  
**Purpose:** Review and select a Terms of Service approach before implementation

---

## Background

You have asked about adding a Terms of Service agreement to the Advisor Portal.
When a user signs in, they are taken directly to their dashboard. We can insert a
TOS agreement step into that login flow. The question is: **how often should a
user be required to agree?**

There are three options below. Each is fully buildable. The choice comes down to
your preference on user experience and legal/compliance needs.

---

## Option 1 — Agree Once, Then Never Again

The user sees the TOS the first time they log in. They click "I Agree."
They are never shown it again.

**What the user experiences:**
- First login: sees a TOS page, clicks agree, goes to dashboard
- Every login after that: goes straight to dashboard as usual

**What gets recorded:**
- The date and time the user agreed is saved permanently in the system
- Viewable by administrators

**Best for:** Low-friction onboarding. Users who log in frequently will
appreciate not being interrupted.

**Limitation:** If you ever update the Terms of Service, existing users
will NOT be prompted to re-agree unless you specifically request a
"re-agreement trigger."

---

## Option 2 — Agree Once Per Version ⭐ Recommended

This is a smarter version of Option 1. The TOS has a version number.
Users agree once per version. When you update the TOS, you simply tell
us to bump the version — and every user is prompted to agree again on
their next login.

**What the user experiences:**
- First login (or after a TOS update): sees TOS, clicks agree, proceeds
- All other logins: straight to dashboard

**What gets recorded:**
- The version they agreed to and the date/time — saved permanently
- Viewable by administrators

**Best for:** Most organizations. Balances low user friction with the
ability to enforce re-agreement whenever your legal language changes.
This is the most common approach used in professional web applications.

**Limitation:** None significant. This is the recommended path.

---

## Option 3 — Agree Every Single Login

The user must click "I Agree" every time they log in, no exceptions.

**What the user experiences:**
- Every login: sees TOS page, must click agree before reaching the dashboard

**What gets recorded:**
- Each agreement session is logged with date, time, and IP address

**Best for:** Situations where maximum legal protection is the priority
and frequent friction is acceptable — for example, compliance-heavy
regulated environments where demonstrating repeated acknowledgement
is required by policy.

**Limitation:** This is the most disruptive to daily users. Advisors who
log in every day will have to click through every single time.

---

## Side-by-Side Comparison

| | Option 1 — Once Ever | Option 2 — Once Per Version | Option 3 — Every Login |
|---|---|---|---|
| How often does user see TOS? | One time only | Once per TOS update | Every login |
| Agreement recorded in system? | Yes | Yes | Yes (per session) |
| Works when TOS is updated? | Requires dev work | Automatic | Always |
| Daily user friction | Very low | Very low | High |
| Legal protection level | Basic | Good | Strongest |
| Recommended? | — | ⭐ Yes | Specialized use only |

---

## Additional Considerations

**Who sees the TOS?**
By default, all users — advisors, delegates, and internal staff — would see it.
If you want TOS to apply only to advisors and delegates (not your own technicians
and managers), that is a simple adjustment.

**What does the TOS page look like?**
You provide the text. We build the page to match the portal's existing design —
your logo, colors, and branding. It includes a scroll area for the agreement text
and a single "I Agree" button. There is no "I Decline" path (they cannot use the
portal without agreeing).

**Can I see who has and hasn't agreed?**
Yes. For Options 1 and 2, the agreement date and version are stored on each user
account and visible to administrators.

**What happens if I update the TOS later?**
- Option 1: You would need to request a manual re-trigger for all users.
- Option 2: You tell us the new version date. We update one line in the system.
  Every user sees the new TOS on their next login automatically.
- Option 3: Already shown every login — nothing to do.

---

## Your Decision

Please indicate your preference:

- [ ] **Option 1** — One-time, never again
- [ ] **Option 2** — One-time per version *(recommended)*
- [ ] **Option 3** — Every login
- [ ] **Option 2 with staff excluded** — Only advisors/delegates see TOS; technicians/managers do not

Any questions or adjustments to the options — just let us know before we build.
