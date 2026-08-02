# Pending Production Deploy — 2026-08-01

All items below are live on the **TEST** server and have been tested.  
They are **not yet deployed to PRODUCTION**.

Baseline: last PROD deploy commit `db20ae6` (Deploy to test: 2026-07-26 09:19)

---

## New Features

| # | Commit | Description |
|---|--------|-------------|
| 1 | `50f33cc` | Accept & Refuse Rush — validates checklist, accepts case, and downgrades rush urgency in one step |
| 2 | `5d27d6e` | Staff-created modification flow — requires justification and includes optional ProFeds error flag |

---

## Bug Fixes

| # | Commit | Description |
|---|--------|-------------|
| 3 | `f49d0ff` | Case Lifecycle timeline now shows Rush Downgraded and Declined events |
| 4 | `c9749e0` | Tech dashboard base query includes declined/cancelled cases so Status filter works correctly |
| 5 | `2224460` | Member view: declined cases now show 0.0 credits instead of "Not visible until released" |
| 6 | `72d5a61` | Selecting a status checkbox (e.g. Declined) no longer conflicts with the active quick-tile filter |
| 7 | `fff9df7` | Tech/admin view: declined cases now show 0.0 credits |
| 8 | `c08ff4e` | Cancelled cases now show 0.0 credits on member and tech views (same as declined) |
| 9 | `7424a3b` | Urgency resets to Normal when a case is declined or cancelled (all code paths) |
| 10 | `3f2c541` | Rush not available email — new subject line, updated body, CLICK HERE button |
| 11 | `d58d0de` | Case declined email — updated to match standard format with CLICK HERE button |
| 12 | `d5bf834` | Rush emails — logo URL and site URL building corrected |
| 13 | `7964586` | Credits column added to admin and technician dashboards |
| 14 | `c631b90` | Tech alert tile — personal unread message count restored (was over-corrected in prior fix) |
| 15 | `c95db60` | TinyMCE: disabled URL conversion — was stripping external absolute URLs on save |
| 16 | `233fd3f` | Case chat — markdown links render correctly; draft message persists to localStorage |
| 17 | `bb9ecf3` | Completed cases can now be reassigned (backend + tech/admin/manager case detail UI) |
| 18 | `8798860` | Case chat paste — HTML anchor tags convert to markdown `[text](url)` on paste |
| 19 | `3bfe353` | System settings tab fields explicitly bound to main form — prevents dropped saves on tab switch |
| 20 | `71e1252` | Case chat sender labels standardized across member and staff views |
| 21 | `7d3b00f` | Technician status filter made strict — unread-message override no longer bleeds into status filtering |
| 22 | `602b4e9` | Technician review alert banners collapsed by default |
| 23 | `c968f68` | Technician quick-stat tile sizing matched to admin/manager |
| 24 | `769d2ed` | Advisors can now edit due date on submitted cases; urgency auto-recalculates |
| 25 | `d62ec3b` | Technical Notes Template save hardened — TinyMCE fallback payload added |
| 26 | `bf37085` | Alert badges consistent across all staff roles; techs can now view cancelled/declined case detail |
| 27 | `649c2cb` | Cancelled cases automatically unassign the assigned technician |
| 28 | `a68135f` | Draft cases with a past due date must select a new due date before submitting |
| 29 | `d0dac29` | Case detail "Date Submitted" now shows actual submission date, not draft creation date |
| 30 | `f3285c0` | Technician dashboard: detailed filter panel (search, status, etc.) overrides active quick-tile |
| 31 | `f6f9817` | Technician status filter markup repaired; status query parameters sanitized server-side |
| 32 | `15cd915` | Technical Notes Template: TinyMCE syncs content on every change — eliminates race condition on save |

---

## Infrastructure / Chore

| # | Commit | Description |
|---|--------|-------------|
| 33 | `f307ec2` | TEST deploy script updated to use systemd gunicorn/nginx restarts (no more manual daemon) |

---

## Summary

- **2 new features**
- **30 bug fixes**
- **1 infrastructure change**
- **33 total commits** pending PROD deployment
- No database migrations required (all changes are code/template only)
