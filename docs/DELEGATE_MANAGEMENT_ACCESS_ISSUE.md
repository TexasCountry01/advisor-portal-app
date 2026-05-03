# Delegate Management Access Issue — Analysis & Options

**Date:** May 3, 2026  
**Reporter:** Tiffany Wideliki (Benefits Technician)  
**Environment:** PROD (https://reports.profeds.com)

---

## Problem

Tiffany receives the error: *"You do not have permission to manage delegates. Contact an administrator to grant access."* when clicking **Management → Delegate Management**.

Additionally, the user requested the ability to **view** all advisor/delegate assignments without necessarily being able to **assign or remove** them.

---

## Root Cause

### Issue 1 — Tiffany's permission flag was turned off
The `delegate_management` view in `accounts/views.py` (line 747) requires technicians to have `can_manage_delegates=True`:

```python
elif user.role == 'technician' and user.can_manage_delegates:
    pass  # Explicitly granted
elif user.role == 'technician':
    messages.error(request, 'You do not have permission to manage delegates...')
    return redirect('cases:technician_dashboard')
```

Tiffany's `can_manage_delegates` flag is currently `False` in the PROD database. This was likely turned off accidentally via Manage Users.

### Issue 2 — Menu link shown to all technicians regardless of permission
`cases/templates/cases/technician_dashboard.html` (line 26) shows the Delegate Management link in the Management dropdown to **all technicians** unconditionally — no permission check. This causes a confusing dead-end for any technician without the flag.

---

## Options

### Option A — Re-grant Tiffany `can_manage_delegates` via Admin UI
**What:** Go to Admin → Manage Users → Tiffany → check `can_manage_delegates` → Save.  
**Effort:** 1 minute, no code change.  
**Result:** Tiffany regains full assign/remove access as before.  
**Downside:** Doesn't fix the dead-end link for other techs without the flag.

---

### Option B — Hide the menu link for techs without `can_manage_delegates` (code fix)
**What:** Wrap the Delegate Management link in `technician_dashboard.html` with a permission check:

```html
{% if user.role != 'technician' or user.can_manage_delegates %}
    <li>
        <a class="dropdown-item" href="{% url 'delegate_management' %}">
            <i class="bi bi-people"></i> Delegate Management
        </a>
    </li>
{% endif %}
```

**File:** `cases/templates/cases/technician_dashboard.html` line ~26  
**Effort:** 1-line template change + deploy.  
**Result:** Techs without the flag never see the link; no dead-end error.  
**Downside:** Doesn't address the view-only request.

---

### Option C — Add read-only view mode for technicians without `can_manage_delegates`
**What:** Allow all technicians to visit the page in read-only mode. Techs without the flag see the assignments table but the Assign and Remove buttons are hidden/disabled. Only techs with `can_manage_delegates=True` (or admins/managers) can make changes.

**Changes required:**
1. `accounts/views.py` — change permission check: instead of redirecting on missing flag, set a `read_only = True` context variable
2. `accounts/templates/accounts/delegate_management.html` — wrap Assign/Remove forms with `{% if not read_only %}`
3. `cases/templates/cases/technician_dashboard.html` — link remains visible for all techs (no change needed)

**Effort:** ~30 minutes, requires deploy.  
**Result:** Tiffany can see every advisor and their delegates; cannot assign or remove.

---

## Recommendation

**Do both Option A + Option B now** (5 minutes total):
- A gets Tiffany working immediately with no deploy needed
- B prevents any future technician from hitting the same dead-end

**Do Option C later** if the read-only view requirement is confirmed as a real workflow need.

---

## Action Items

- [ ] **Option A:** Set `can_manage_delegates=True` for Tiffany via Admin → Manage Users (no deploy)
- [ ] **Option B:** Fix `technician_dashboard.html` to hide the link for techs without the flag (requires deploy)
- [ ] **Option C (optional):** Implement read-only delegate view for all technicians (requires deploy)
