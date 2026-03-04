# Delegate Access Fixes — Summary for Testers

**Date:** March 3, 2026  
**Status:** All fixes deployed to the TEST portal

---

## What Was Reported

During testing, two problems were discovered when delegates tried to use the portal:

1. **"Access Denied" when viewing a case** — Delegates could see cases in their queue but were blocked when they clicked "View."
2. **Advisor dropdown only showed themselves** — On the Submit Case page, delegates should have seen a dropdown of the advisors they work for, but only saw their own name.

---

## What Was Fixed

### Fix 1: Delegates Can Now View and Edit Cases

Delegates can now open and work with cases belonging to the advisors they are assigned to. This includes viewing case details, uploading documents, and submitting new information — exactly the same access the advisor would have.

**Who this affected:**  
Frank Dimicelli, Brandon Dimicelli, Jaylon Dukes, Dale McGregor, Madison McGregor, and Ed Smith.

These six testers are all **advisors who also serve as delegates** for other advisors. They could manage their own cases fine, but were blocked from accessing cases for the advisors they delegate for. This is now resolved.

---

### Fix 2: Advisor Dropdown Now Shows Correct Names

When a delegate goes to Submit a New Case, the advisor dropdown now correctly shows the advisor(s) they are assigned to work for. If the delegate is also an advisor themselves, their own name appears in the dropdown too.

**Who this affected:**  
Same six testers as Fix 1 — they all had the dropdown issue as well, since both problems came from the same underlying cause.

---

### Fix 3: Pure Delegates No Longer See Themselves in the Dropdown

Some testers are **pure delegates** — they assist advisors but do not have their own cases. These users were incorrectly showing their own name in the advisor dropdown, which doesn't make sense since they don't submit cases under their own name.

Now, pure delegates only see the advisor(s) they are assigned to. Their own name does not appear.

**Who this affected:**  
Sabra Singleton, Janae Lickert, Evan Hicks, James Lavy, Shawn Hicks, Les McGregor, and Autumn Chartier.

All seven are pure delegates — they only use the portal to submit and manage cases on behalf of their assigned advisors.

---

## How the Testers Break Down

The 13 testers fall into two groups, and each group experienced the same set of issues:

### Group A: Advisors Who Are Also Delegates (6 testers)

| Tester | Workshop | Fixes Applied |
|--------|----------|---------------|
| Frank Dimicelli | CFG | Fix 1 + Fix 2 |
| Brandon Dimicelli | CFG | Fix 1 + Fix 2 |
| Jaylon Dukes | CFG | Fix 1 + Fix 2 |
| Dale McGregor | DMCG | Fix 1 + Fix 2 |
| Madison McGregor | DMCG | Fix 1 + Fix 2 |
| Ed Smith | VWP | Fix 1 + Fix 2 |

These users have their own cases **and** serve as delegates for other advisors. They experienced the "Access Denied" and dropdown issues when working on behalf of the advisors they delegate for. Their own cases were always fine.

### Group B: Pure Delegates (7 testers)

| Tester | Workshop | Fix Applied |
|--------|----------|-------------|
| Sabra Singleton | CFG | Fix 3 |
| Janae Lickert | CFG | Fix 3 |
| Evan Hicks | HFR | Fix 3 |
| James Lavy | HFR | Fix 3 |
| Shawn Hicks | HFR | Fix 3 |
| Les McGregor | DMCG | Fix 3 |
| Autumn Chartier | DMCG | Fix 3 |

These users only work on behalf of advisors — they don't have their own cases. Their issue was simpler: they saw their own name in the dropdown when they shouldn't have.

---

## Additional Improvement: Audit Trail

While verifying the fixes above, we also improved the system's audit trail (the activity log that administrators and managers can review). Specifically:

- **SSO login events** (when users sign in through the ProFeds website) are now properly recorded in the main activity log. Previously, these events were being stored separately and were not visible to administrators.
- **Failed login attempts** are now logged, so administrators can see when someone tries to log in but is denied access.
- **Delegate actions are now clearly labeled** — When a delegate submits a case or uploads a document on behalf of an advisor, the audit trail now shows who the delegate is and which advisor they were acting for. Previously it only showed the action without this context.

---

## What Testers Should Verify

All fixes are live on the TEST portal. Testers can verify by:

1. **Logging in via SSO** (the "Login with ProFeds Account" button)
2. **Viewing the dashboard** — Delegates should see cases for their assigned advisors
3. **Clicking "View" on a case** — Should open successfully (no "Access Denied")
4. **Going to Submit New Case** — The advisor dropdown should show the correct advisor(s)
5. **Uploading a document** to a case they delegate for — Should work without errors

No action is needed from testers regarding the audit trail improvements — those are internal system enhancements.
