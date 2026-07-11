# Pending Production Deployment — 2026-07-11

All items below are live on the **TEST server** and awaiting your approval to deploy to **PRODUCTION**.

---

## 1. Holiday Due Date — Rushed Alert Fix
**What was broken:** When manually setting a due date to the day before the holiday-adjusted default (e.g., 7/10 when the system recommended 7/11 due to July 4th), the form showed a plain informational note instead of the red "RUSHED" warning box.

**What was fixed:**
- Dates that fall in the holiday buffer window now correctly trigger the red RUSHED alert
- Alert title changes to **"ALERT: Upcoming Holiday!"** instead of "Rushed Request"
- Urgency is correctly set to `rush` and the $20 fee applies

---

## 2. Technician Dashboard — Default View on Login
**What was broken:** When a technician opened the dashboard, it defaulted to showing all cases from all time, sorted by submission date — not useful day-to-day.

**What was fixed:**
- Fresh page load now defaults to the logged-in tech's **own Pending Completion cases**
- Sorted by **due date ascending** (closest due date first)
- Navigating away and using other filters/tiles still works normally

---

## 3. Technician Dashboard — Removed Redundant Toggle
**What was broken:** The "All Cases / My Cases" toggle was still visible on the technician dashboard even after the quick tech buttons (All Techs / Tiffany / Chris / Becky) replaced its functionality.

**What was fixed:**
- Toggle removed entirely
- Quick tech buttons are now the only way to switch between techs on that dashboard

---

## 4. Need to Accept Tile — Cases Not Showing When Tech Selected
**What was broken:** When a specific tech was selected (e.g., Tiffany), the "Need to Accept" tile showed the correct global count (2), but clicking it returned an empty case list.

**What was fixed:**
- Clicking "Need to Accept" with a tech selected now correctly shows all submitted cases
- Submitted cases have no assigned tech yet — they are a shared queue, so the tech filter is intentionally bypassed for this tile only
- Fix applied to all three dashboards: Technician, Admin, and Manager

---

## 5. Status Dot — Logout Now Immediately Goes Grey
**What was broken:** When a technician logged out, their status dot stayed green for up to 5 minutes, then yellow for up to 30 minutes, before going grey.

**What was fixed:**
- Logging out now immediately clears the `last_active` timestamp
- Status dot goes grey instantly upon logout
- Behavior for browser close / inactivity is unchanged (still uses the 5/30 min thresholds)

---

## Ready to Deploy
Please confirm approval and all five fixes will be pushed to Production in a single deployment.
