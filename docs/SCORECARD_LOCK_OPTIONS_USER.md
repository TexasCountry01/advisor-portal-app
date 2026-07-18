# Performance Scorecard — Data Locking Options

**Prepared for:** End User Review  
**Date:** 2026-07-18  
**Purpose:** To select an approach for ensuring Performance Scorecard numbers do not change after they have been reviewed, so they can be reliably used for technician performance evaluations.

---

## The Problem

The Performance Scorecard currently shows live numbers calculated from the database each time the page is loaded. Because case corrections are a normal part of the L1/L2/L3 review workflow, a week's numbers can legitimately change even after that week has closed — for example, if an L3 technician approves or returns a case submitted the previous week.

For formal HR evaluations, this is a problem: the numbers extracted today may differ from the numbers reviewed last week.

---

## Option A — Admin Locks Each Week Manually *(Recommended)*

**How it works:**
1. At the end of each week, the admin reviews the Performance Scorecard
2. Once satisfied that all corrections for that week have been processed, the admin clicks **"Lock Week [dates]"**
3. The system permanently saves that week's numbers
4. Locked weeks display a 🔒 icon — their numbers will never change
5. Unlocked weeks show a ⚠️ indicator — numbers are still live

**If a correction must be made after locking:**
- The admin can unlock a week, but must enter a written reason
- The unlock is logged with the admin's name, date, and reason
- After corrections are complete, the admin re-locks the week
- The full history is preserved for audit purposes

**What the admin sees on the scorecard:**

| Week | Status | Reports Generated | ... |
|---|---|---|---|
| Jul 6 – Jul 12 | 🔒 Locked Jul 14 by J. Smith | 15 | ... |
| Jun 29 – Jul 5 | 🔒 Locked Jul 7 by J. Smith | 12 | ... |
| Jun 22 – Jun 28 | ⚠️ Not yet locked | 11 (live) | ... |

**Pros:**
- Admin controls exactly when a week's numbers are frozen
- Naturally accommodates the L1/L2/L3 correction workflow — admin waits until corrections settle, then locks
- Full audit trail: who locked it, when, and if ever unlocked, why
- Locked numbers match exactly what the admin reviewed before extracting for HR

**Cons:**
- Requires admin action every week
- If the admin forgets to lock a week, that week's numbers remain live

**Effort to build:** Medium

---

## Option B — Numbers Freeze Automatically Every Sunday Night

**How it works:**
- A scheduled job runs automatically every Sunday at 11:59 PM
- It permanently saves that week's final numbers with no admin action required
- The scorecard shows all past weeks as locked automatically

**Pros:**
- No weekly admin action needed
- Consistent — every week is treated the same way

**Cons:**
- If a correction is submitted on Monday for the previous week, it will NOT be reflected in the snapshot (the cron already ran)
- If the scheduled job fails silently, that week is never locked
- No built-in review step before numbers go to HR

**Effort to build:** Medium (requires server-side scheduled job configuration)

---

## Option C — The Downloaded File IS the Frozen Record

**How it works:**
- No changes to the application
- The admin downloads the CSV or PDF at the end of each week
- The downloaded file — which already includes the generation date, time, and admin name — is the permanent record
- That file is what gets submitted to the HR tool

**Pros:**
- No development work required
- Already available today
- The timestamp on the file proves when the data was captured

**Cons:**
- The app itself has no "frozen" view — if someone opens the scorecard later, they see updated live numbers that may differ from the HR submission
- Relies entirely on admin discipline to download at the right time
- No audit trail within the application for what numbers were submitted

**Effort to build:** None — already implemented

---

## Option D — Automatic Freeze with Admin Sign-Off *(Most Rigorous)*

**How it works:**
- Combines Options A and B
- Numbers freeze automatically every Sunday night (no admin needed for the freeze itself)
- The admin must explicitly **sign off** on each week before the data is considered final for HR
- If corrections are needed after the auto-freeze, the admin can re-freeze with a documented reason
- The HR extraction only includes weeks with admin sign-off

**Pros:**
- Safety net from automatic freeze prevents numbers from staying live indefinitely
- Admin review step before HR submission
- Most complete audit trail

**Cons:**
- Most complex to build
- Still has the Monday-correction problem from Option B

**Effort to build:** High

---

## Summary Comparison

| | A — Manual Lock | B — Auto Freeze | C — Export Only | D — Auto + Sign-Off |
|---|---|---|---|---|
| Numbers guaranteed frozen | ✅ After admin locks | ✅ After Sunday | ✅ In the file | ✅ After sign-off |
| Handles Monday corrections | ✅ Admin waits | ❌ Missed | ✅ If exported late | ❌ Missed |
| Requires weekly admin action | ✅ Yes (lock) | ❌ No | ✅ Yes (download) | ✅ Yes (sign-off) |
| In-app audit trail | ✅ Full | Partial | ❌ None | ✅ Full |
| Development effort | Medium | Medium | None | High |

---

## Recommendation

**Option A — Manual Admin Lock** best fits your workflow because:

- The L1/L2/L3 correction cycle means corrections legitimately arrive after a week closes — the admin needs the ability to wait until corrections settle before freezing
- The lock-then-extract workflow creates a natural review checkpoint before HR data is submitted
- The full audit trail (who locked, when, any unlocks and reasons) provides accountability

Please select your preferred option and the technical implementation will proceed accordingly.
