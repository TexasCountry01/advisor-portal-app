# Review Settings — Quick Guide

## What It Does

The **Review Settings** page lets you control whether a technician's cases require senior review before being sent to the member. You can toggle this on or off per technician, per tier (Tier 1, Tier 2, Tier 3).

---

## Where to Find It

### As an Administrator or Manager

1. Log in to the portal
2. In the **top navigation bar**, click **Review Settings** (clipboard icon)
3. You'll see a table of all technicians with toggle switches for each tier

### As a Level 3 Technician (if granted permission)

1. The **Review Settings** link will appear in your navbar once an Admin enables it for you
2. Same page, same functionality

---

## How to Toggle Mandatory Review

On the **Review Settings** page:

1. Find the technician in the table
2. For each tier, flip the **toggle switch**:
   - **ON (blue)** = Cases of that tier require senior review before release
   - **OFF (gray)** = Technician can release cases of that tier on their own
3. Changes save automatically (no save button needed)

### Defaults

| Tier | Default |
|------|---------|
| Tier 1 | Review required |
| Tier 2 | No review required |
| Tier 3 | No review required |

---

## How to Grant a Level 3 Tech Access to Review Settings

As an **Administrator**:

1. Go to **Users** (Manage Users page)
2. Click the **Edit** button next to the technician
3. Under **Staff Permissions**, toggle on **Can Manage Review Settings**
4. Click **Save Changes**

That technician will now see the **Review Settings** link in their navbar.

> **Note:** The "Can Manage Delegates" toggle on the same screen controls access to the Delegate Management page (separate feature).

---

## Things to Test

- [ ] Admin sees "Review Settings" in the navbar
- [ ] Manager sees "Review Settings" in the navbar
- [ ] Admin can toggle review on/off for any technician on the Review Settings page
- [ ] Admin can grant "Can Manage Review Settings" permission to a Level 3 tech via Edit User
- [ ] Level 3 tech with permission sees "Review Settings" in their navbar
- [ ] Level 3 tech without permission does NOT see "Review Settings"
- [ ] Toggling review off lets the technician release cases without senior review
- [ ] Toggling review back on requires senior review for newly completed cases
