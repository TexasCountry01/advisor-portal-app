# TSP Fund Catalog — Phase 1 Implementation

**Date:** 2026-10-04
**Scope:** Implements the first safe phase of TSP Fund Maintenance, per
`docs/TSP_DYNAMIC_FUND_MAINTENANCE_ARCHITECTURE_ANALYSIS.md` and
`docs/TSP_CANONICAL_FUND_INVENTORY.md`. All code changes are in `benefits-software`.
No `advisor-portal-app` source was changed (compatibility confirmed by inspection only).

---

## What was implemented

1. A canonical **TSP Fund Catalog** table (`tsp_fund_catalog`) in `benefits-software`, additive only.
2. **18 seeded catalog records** — 16 active, 2 inactive/historical (`L2020`, `L2025`) — from a single
   source-of-truth definitions class, not duplicated inline in the migration/seeder.
3. A small, dedicated **TSP Fund Maintenance** admin screen, entirely separate from the existing
   annual TSP configuration screen (`DashboardController@configurations` — **not touched**).
4. Activate/deactivate (never delete) for existing supported funds, with system-metadata columns
   (`fund_code`, `balance_column`, `allocation_column`, `rate_config_key`, `lfund_distribution_key`)
   never exposed to or editable through that screen.
5. The Fact Finder Data Contract's `tsp.funds` collection is now generated from the **active** Fund
   Catalog (in display order) instead of the previous incomplete hardcoded 10-fund array — same JSON
   shape (`fund_code`/`balance`/`allocation_pct`), no Advisor Portal schema change needed.
6. The same duplicated hardcoded fund list that previously existed in 4 separate PHP files was
   consolidated to call the one new service instead.

## Catalog schema

Table `tsp_fund_catalog` (migration `2026_10_04_000000_create_tsp_fund_catalog_table`):

| Column | Type | Notes |
|---|---|---|
| `id` | increments | |
| `fund_code` | string, unique | System metadata — not editable via the admin screen |
| `display_name` | string | Business-facing name shown on the admin screen |
| `category` | string | `individual` or `lifecycle` |
| `rate_config_key` | string, nullable | System metadata — set for `individual` funds only |
| `lfund_distribution_key` | string, nullable | System metadata — set for `lifecycle` funds only |
| `balance_column` | string | System metadata — maps to the existing `TSP` table column |
| `allocation_column` | string | System metadata — maps to the existing `TSP` table column |
| `is_active` | boolean, default true | The ONLY field the admin screen changes |
| `display_order` | unsigned integer | Presentation order |
| `effective_end_date` | date, nullable | Present in the schema for future use; **not populated** for either historical fund in this phase (no exact date is documented for `L2020`; `L2025`'s retirement is only documented to month precision, not an exact date) |
| `created_at`/`updated_at` | timestamps | |

Single source of truth for the 18 seed rows: `app/Services/TspFundCatalogDefinitions.php` (used by both
the seeder and the unit tests — not duplicated).

## 18 seed records / 16 active default

Verified (via the full test suite and a direct DB query against the local dev database after seeding):

- **16 active**, in display order: `GFund, FFund, CFund, SFund, IFund, LIncome, L2030, L2035, L2040, L2045, L2050, L2055, L2060, L2065, L2070, L2075`
- **2 inactive/historical**: `L2020`, `L2025` — both `is_active=false`, both `effective_end_date=NULL` (per the explicit instruction not to invent an exact date for either).

## Admin maintenance behavior

- Route: `GET /dashboard/tsp-fund-catalog` (`admin.tspFundCatalog`) — lists all 18 rows (Fund /
  Type / Status / Display Order / Action). Inactive rows are visually labeled "(retained for history)".
- Action: `POST /dashboard/tsp-fund-catalog/change-status` (`admin.tspFundCatalog.changeStatus`) —
  accepts only `fund_code` + `action` (`activate`|`deactivate`); looks the row up by `fund_code` and
  sets only `is_active` — never mass-assigns the request body, so system-metadata fields cannot be
  changed through this action even if present in the POST payload (tested, see below).
- No delete route/action exists anywhere in this feature.
- New nav link "TSP Fund Maintenance" added next to the existing "Configuration" link in
  `admin_top_menu.blade.php`.
- Access gated the same way as the existing annual TSP configuration screen (`isLogin` +
  `checkIsActive` only, not the stricter `adminCheck` group) — consistent with that screen's
  existing precedent, not a new access level.

## Data Contract change

`EmployeeController@createPdfFEGLI`'s `tsp.funds` builder block (previously a hardcoded array of 10
fund codes, missing `L2035/L2045/L2055/L2060/L2065/L2070/L2075` and incorrectly including inactive
`L2020`) now reads:

```php
$tspFundsForContract = \App\Services\TspFundCatalogService::buildActiveTspFunds($tsp);
```

`TspFundCatalogService::buildActiveTspFunds()` queries the active catalog rows (ordered), then maps
each one's `balance_column`/`allocation_column` onto the **same, unchanged** `$tsp` array that
`EmployeeRepository::getEmpTspDetails()`/`getTSPNewBalance_new()` already produce — it performs **no
calculation**, only enumeration/lookup. Output shape is unchanged: a list of
`{fund_code, balance, allocation_pct}` objects, exactly what
`advisor-portal-app/cases/fact_finder_data_contract.py`'s `TspFundSerializer` already accepts (no
`fund_code` choice-restriction exists there — confirmed by inspection, no Advisor Portal change needed).

The same consolidation was applied to the 3 other PHP files that had duplicated this exact hardcoded
array: `scripts/export_golden_master_contracts.php`, `scripts/validate_fact_finder_data_contract.php`,
`scripts/validate_fact_finder_html_diff.php` — all 4 call sites now share the one canonical source.

## Files changed

**Created:**
- `database/migrations/2026_10_04_000000_create_tsp_fund_catalog_table.php`
- `database/seeds/TspFundCatalogSeeder.php`
- `app/Models/TspFundCatalog.php`
- `app/Services/TspFundCatalogDefinitions.php`
- `app/Services/TspFundCatalogService.php`
- `app/Http/Controllers/Admin/TspFundCatalogController.php`
- `resources/views/admin/tsp_fund_catalog/index.blade.php`
- `tests/Unit/TspFundCatalogDefinitionsTest.php`
- `tests/Unit/TspFundCatalogServiceMappingTest.php`
- `tests/Feature/TspFundCatalogControllerTest.php`

**Modified:**
- `routes/web.php` — 2 new routes, added immediately after the existing annual configuration routes
- `resources/views/admin/layouts/admin_top_menu.blade.php` — 1 new nav link
- `app/Http/Controllers/Admin/EmployeeController.php` — replaced the hardcoded `tsp.funds` builder block
- `scripts/export_golden_master_contracts.php`, `scripts/validate_fact_finder_data_contract.php`,
  `scripts/validate_fact_finder_html_diff.php` — same consolidation

**Not modified (explicitly out of scope, confirmed untouched):**
- `DashboardController@configurations`/`saveConfigs`, `resources/views/admin/dashboard/configuration.blade.php` (the existing annual TSP configuration screen)
- `EmployeeRepository`'s TSP calculation methods (`getEmpTspDetails`, `getTSPNewBalance_new`, `calcProjectedEndingBalanceTsp`, `getAgencyContribution`, Lifecycle glide-path methods)
- `report_pdf.blade.php`'s TSP rendering tables/loops
- `FactFinderGovernedContentResolver`/`FactFinderMergeFieldSubstitutor` (governed-content fallback behavior)
- Any `advisor-portal-app` source file

## Tests run and results

**Pure unit tests (no database, `vendor/bin/phpunit.bat --bootstrap vendor/autoload.php`):**
- `tests/Unit/TspFundCatalogDefinitionsTest.php` — 8 tests, 46 assertions, **all pass**. Proves: exactly
  18 records defined; exactly 16 active; `L2020`/`L2025` both inactive with no invented
  `effective_end_date`; active funds in the exact expected display order; every individual fund has a
  `rate_config_key` and no lifecycle key (and vice versa); no duplicate fund codes.
- `tests/Unit/TspFundCatalogServiceMappingTest.php` — 5 tests, 51 assertions, **all pass**. Proves: the
  previously-omitted active Lifecycle funds (e.g. `L2035`, `L2070`) are now included; inactive funds
  (`L2020`, `L2025`) are excluded even when present in `$tsp`; output shape matches the existing
  3-key Data Contract expectation; active funds are returned in catalog display order.

**Feature tests (real local dev database, `tsp_fund_catalog` table migrated+seeded; no
RefreshDatabase — any row mutated by a test is restored in `tearDown()`):**
- `tests/Feature/TspFundCatalogControllerTest.php` — 6 tests, 14 assertions, **all pass**:
  admin page renders; admin can deactivate an active fund; admin can reactivate an inactive fund;
  system-metadata fields (`balance_column`/`allocation_column`/`rate_config_key`) cannot be changed
  through the maintenance action even when included in the request; no delete route is exposed;
  an invalid `action` value is rejected.

**Full benefits-software suite:** `vendor/bin/phpunit.bat --bootstrap vendor/autoload.php tests` —
**109 tests, 283 assertions, 0 failures** (up from the pre-existing suite + 19 new tests above).

**PDF/golden-master regression check:** `php artisan fact-finder:golden-master --check` was run twice —
once with this implementation's `EmployeeController.php` change in place, and once with that one file
temporarily reverted (via `git stash`) to isolate cause. **Both runs produced byte-for-byte identical
results** (all 24 cases showing the same size deltas) — proving the diffs are pre-existing, unrelated
to this implementation (consistent with this project's previously-documented "age-drift" phenomenon;
see Known limitations below for why more cases than usual showed drift this time). `$tspFundsForContract`
is only used inside the read-only Data Contract logging block and is never passed to the Blade view, so
this result was expected, not merely hoped for.

## Known limitations / deliberately deferred

- **L2070/L2075 glide-path data verification is explicitly out of scope** for this phase, per the
  canonical inventory's own finding that the local seeder has no rows for these two funds — not
  investigated or changed here.
- **Calculations were NOT dynamically refactored.** `getEmpTspDetails()`, `getTSPNewBalance_new()`,
  `calcProjectedEndingBalanceTsp()`, and `report_pdf.blade.php`'s rendering loops still read/sum the
  16 active fund columns by literal name, exactly as before this phase. The catalog is used ONLY to
  determine which funds are enumerated in `tsp.funds` and in the new admin screen — proving the
  catalog concept safely before any future phase considers refactoring the calculation engine itself.
- **No arbitrary "Create Fund" capability** — an administrator can only activate/deactivate one of the
  18 existing, already-mapped catalog rows. Adding a genuinely new fund code still requires a schema
  migration (new `TSP` columns) and is out of scope, matching the existing wide-column storage model
  this phase deliberately does not change.
- **No Advisor Portal maintenance UI or write-API was built** — deferred per explicit instruction; the
  service class (`TspFundCatalogService`) is kept small and self-contained specifically so a future
  Advisor Portal-facing API could call it later without redesigning this phase.
- **The golden-master harness showed drift across all 24 cases** (not just the previously-typical
  ~7 of 24) at the time this phase was tested — confirmed unrelated to this implementation (see Tests
  section above), most likely the same previously-documented date-sensitive content (e.g. "Current
  Age"/IRS early-withdrawal-penalty text) drifting further as more real time has passed since the
  fixtures were last captured (2026-09-26 per prior project history) versus today (2026-10-04). Not
  investigated further or fixed here — unrelated to TSP Fund Catalog work and explicitly out of this
  phase's scope; flagged for whoever next refreshes the golden-master baseline.
- **A git-hygiene mistake occurred and is disclosed here directly:** while investigating the
  golden-master drift, a blanket `git checkout -- storage/framework/views/` was run to clean up
  `view:clear`'s side effects. This correctly removed the *new* deletions caused by this session's own
  `golden-master --check` runs, but it also reverted 3 **pre-existing, unrelated** modified/deleted
  files in that directory (`2eb160819b4341aa7006926302ee7b3bd453c035.php`,
  `bc356608657637f9da38fe09d5107cd3dac44ba8.php`, `f8ce95c6c486c4d29c1c9df21c444a3746e97423.php`) back
  to their committed (HEAD) state, instead of leaving them exactly as they were found. These are
  Laravel's auto-generated *compiled Blade template cache* files (derived, machine-generated build
  artifacts, not hand-authored source or data) — per this exact repo's own established, previously-
  documented behavior, they are automatically regenerated/resynced the next time any page is rendered
  and a staleness mismatch is detected, so no source code or data was lost. Reported transparently
  per the explicit instruction not to touch unrelated files, even though the practical impact is
  believed to be nil.

## Rollback / backout procedure

Nothing has been committed, staged, or deployed. To fully back out this Phase 1 work from the local
environment:

1. **Database (local dev only):** `php artisan migrate:rollback --path=database/migrations/2026_10_04_000000_create_tsp_fund_catalog_table.php`
   — drops only the new `tsp_fund_catalog` table. Verified additive: the migration's `down()` does not
   reference or touch the existing `TSP` employee table in any way.
2. **Source files:** discard the specific new/modified files listed above (e.g.
   `git checkout -- app/Http/Controllers/Admin/EmployeeController.php routes/web.php resources/views/admin/layouts/admin_top_menu.blade.php scripts/export_golden_master_contracts.php scripts/validate_fact_finder_data_contract.php scripts/validate_fact_finder_html_diff.php`
   and `git clean` or manual deletion of the newly-created, still-untracked files listed under
   "Created" above) — do **not** run a blanket `git checkout`/`git clean` across the whole repository,
   since unrelated pre-existing modified/untracked files must be preserved exactly as found.
3. No data migration/backfill/dual-write was introduced, so there is nothing else to reverse.

---

## Explicit confirmations

- Existing annual TSP configuration screen (`DashboardController@configurations`/`saveConfigs`,
  `admin.dashboard.configuration` view) was **not changed**.
- TSP calculation formulas were **not changed**.
- Lifecycle glide-path calculation logic was **not changed**.
- Existing employee `TSP` table columns were **not removed, renamed, or normalized**.
- No Advisor Portal TSP UI was created; no Advisor Portal source file was modified.
- Governed-content fallback behavior (`FactFinderGovernedContentResolver`,
  `FactFinderMergeFieldSubstitutor`) was **not changed**.
- Nothing was staged, committed, pushed, or deployed in either repository.
