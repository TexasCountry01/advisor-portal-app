# TSP Canonical Fund Inventory (verified against code/schema, 2026-10-04)

**Scope:** resolves the 16-vs-17 fund-count discrepancy in `docs/TSP_DYNAMIC_FUND_MAINTENANCE_ARCHITECTURE_ANALYSIS.md` before TSP Fund Catalog implementation. Read-only investigation; no source/tests/config/migrations/data changed. See git status at end.

---

## 1. Active / supported funds today

**Exact count: 16.** Confirmed identical, in this exact order, in all three of: `EmployeeRepository::getEmpTspDetails()`'s `totalCurrentBalance` sum ([EmployeeRepository.php:3567](../../benefits-software/app/Repositories/EmployeeRepository.php#L3567)), `getTSPNewBalance_new()`'s final `new_balance` sum ([EmployeeRepository.php:9437](../../benefits-software/app/Repositories/EmployeeRepository.php#L9437)), and `report_pdf.blade.php`'s Current Balance & Growth table rows (~lines 2265-2375):

```
GFund, FFund, CFund, SFund, IFund, LIncome,
L2030, L2035, L2040, L2045, L2050, L2055, L2060, L2065, L2070, L2075
```

= 5 Individual funds + 11 Lifecycle funds (LIncome + 10 target-date funds).

## 2. Retired / inactive funds still present in schema or code

**Exact count: 2 — `L2020` and `L2025`.** Both are physically present as columns (`L2020`/`L2020Dist`, `L2025`/`L2025Dist` on `TSP`) but excluded from every active calculation/render listed in §1. They are retired for **different reasons and with different levels of documentation**:

| | `L2025` | `L2020` |
|---|---|---|
| Retirement documented? | **Yes, explicitly** — `2025_08_23_000000_update_lifecycle_funds_2025.php` comment: *"L2025 expires July 2025"*; one-time data migration `UPDATE TSP SET LIncome = LIncome + L2025 WHERE L2025 > 0` then zeroes it; ~20 "L2025 fund expired July 2025 — removed" comments throughout `EmployeeRepository.php` (e.g. lines 3676, 3789, 3953, 9217) | **No** — zero comments anywhere explaining its absence from the active set |
| In `totalCurrentBalance`/`new_balance`/PDF sums? | No (deliberately removed) | No |
| In admin edit form `tsp_edit.blade.php`? | No input field; only a `<!-- L2025 fund removed - expired July 2025 -->` comment (line 361) | **No input field, and no comment either** — simply absent |
| In audit-history seeder (`HistoryColumnsSeeder.php`)? | Yes — `L2025`/`L2025Dist` both registered (lines 283, 358) | **No** — never registered |
| In Lifecycle glide-path seed data (`lfundDistSeeder.php`)? | Yes — 20 seeded distribution rows (`'type' => 'L2025'`) | **No** — zero rows found |
| In `Tsp::$fillable`? | No | **Yes** — `'L2020'`, `'L2020Dist'` still listed |
| In the Data Contract's hardcoded `tsp.funds` builder array (`EmployeeController.php:1654`)? | No | **Yes** |

**Conclusion:** `L2025` is a cleanly, deliberately, recently retired fund (real precedent for "retire a fund" = zero its balance into `LIncome` + remove from all active code paths, but leave the column and its historical glide-path/audit-history registration in place). `L2020` has **no retirement event at all in the codebase** — it appears to have been excluded from every *active* calculation/rendering/admin path from an earlier, undocumented point, while still lingering in two places that were never cleaned up (`Tsp::$fillable` and the Data Contract's hardcoded fund list). This is flagged as an ambiguity in §7, not resolved here.

## 3. Why the prior analysis said "16" but listed 17

**Confirmed: a genuine documentation error in the prior analysis, not a hidden distinction.** `TSP_DYNAMIC_FUND_MAINTENANCE_ARCHITECTURE_ANALYSIS.md` §3 labeled its list "16 funds" but the prose actually enumerated **17** items (`GFund, FFund, CFund, SFund, IFund, LIncome, L2020, L2030, L2035, L2040, L2045, L2050, L2055, L2060, L2065, L2070, L2075`) — a plain counting/transcription slip.

That 17-item list was **also substantively wrong**, independent of the count error: it incorrectly included `L2020` as if active. `L2020` is excluded from every real active calculation/render path (§1/§2) — it is retired-in-practice, just undocumented as such. So the correct, verified active count is **16**, and it is **not** the same 16 as "17 minus a typo" — the correct list additionally requires removing `L2020`, which the prior list wrongly kept. Net effect: one counting error plus one composition error, both now resolved — see §1 for the corrected, verified list.

## 4. Per-fund mapping table (16 active funds)

| Fund code | Display name | Type | Balance field | Allocation field | Rate / distribution source |
|---|---|---|---|---|---|
| `GFund` | G Fund | Individual | `TSP.GFund` | `TSP.GFundDist` | `AppLookup`/`EmployeeConfig` key `TSPGFundReturn` (via `getEmpTspConfigurations()['gfund']`) |
| `FFund` | F Fund | Individual | `TSP.FFund` | `TSP.FFundDist` | `TSPFFundReturn` → `['ffund']` |
| `CFund` | C Fund | Individual | `TSP.CFund` | `TSP.CFundDist` | `TSPCFundReturn` → `['cfund']` |
| `SFund` | S Fund | Individual | `TSP.SFund` | `TSP.SFundDist` | `TSPSFundReturn` → `['sfund']` |
| `IFund` | I Fund | Individual | `TSP.IFund` | `TSP.IFundDist` | `TSPIFundReturn` → `['ifund']` |
| `LIncome` | L Income | Lifecycle | `TSP.LIncome` | `TSP.LIncomeDist` | `lfundDistribution` glide-path rows where `lfund_type='LIncome'` (also the universal fallback target for every other L-fund lookup, §2 of prior analysis) |
| `L2030` | L 2030 | Lifecycle | `TSP.L2030` | `TSP.L2030Dist` | `lfundDistribution` where `lfund_type='L2030'` — seeded rows confirmed present |
| `L2035` | L 2035 | Lifecycle | `TSP.L2035` | `TSP.L2035Dist` | `lfundDistribution` where `lfund_type='L2035'` (not individually re-verified for seed rows in this pass; same mechanism as `L2030`) |
| `L2040` | L 2040 | Lifecycle | `TSP.L2040` | `TSP.L2040Dist` | same mechanism |
| `L2045` | L 2045 | Lifecycle | `TSP.L2045` | `TSP.L2045Dist` | same mechanism |
| `L2050` | L 2050 | Lifecycle | `TSP.L2050` | `TSP.L2050Dist` | same mechanism |
| `L2055` | L 2055 | Lifecycle | `TSP.L2055` | `TSP.L2055Dist` | same mechanism |
| `L2060` | L 2060 | Lifecycle | `TSP.L2060` | `TSP.L2060Dist` | same mechanism |
| `L2065` | L 2065 | Lifecycle | `TSP.L2065` | `TSP.L2065Dist` | same mechanism |
| `L2070` | L 2070 | Lifecycle | `TSP.L2070` | `TSP.L2070Dist` | `lfundDistribution` where `lfund_type='L2070'` — **no seeded rows found in `lfundDistSeeder.php`** (§7 ambiguity); falls back to `LIncome`'s distribution rows per `getDistributionForLfund_new()`'s documented fallback logic if none exist live either |
| `L2075` | L 2075 | Lifecycle | `TSP.L2075` | `TSP.L2075Dist` | same gap as `L2070` — **no seeded rows found** |

Retired funds (not seeded into any future catalog as active rows — see §6):

| Fund code | Balance/allocation fields (still exist) | Status |
|---|---|---|
| `L2025` | `TSP.L2025` / `TSP.L2025Dist` | Explicitly retired July 2025; balance zeroed, migrated into `LIncome` |
| `L2020` | `TSP.L2020` / `TSP.L2020Dist` | Excluded from all active paths; no documented retirement event (ambiguity, §7) |

## 5. Cross-layer discrepancies (confirms and refines the prior `tsp.funds` finding)

**Confirmed and refined.** The prior analysis's claim that the Fact Finder Data Contract's `tsp.funds` list omits newer Lifecycle funds is **confirmed**, and this investigation found the gap is larger/more specific than previously stated:

`EmployeeController.php` (~line 1654, `$tspFundDistColumns`) and `scripts/export_golden_master_contracts.php`/`validate_fact_finder_data_contract.php`/`validate_fact_finder_html_diff.php` (same hardcoded array, independently duplicated in at least 3 PHP files) all build `tsp.funds` from exactly:

```
GFund, FFund, CFund, SFund, IFund, LIncome, L2020, L2030, L2040, L2050
```

Compared against the verified active 16-fund list (§1), this hardcoded 10-fund array:
- **Omits 7 real, active funds:** `L2035, L2045, L2055, L2060, L2065, L2070, L2075`
- **Wrongly includes 1 retired fund:** `L2020` (always balance=0/allocation=0 in every one of the 24 golden-master JSON fixtures checked, consistent with it being dead, not merely coincidentally zero)

No other cross-layer omission was found for the 5 Individual funds or `LIncome` — those are consistently present in the DB schema, calculation engine, admin forms, PDF rendering, and (correctly) the Data Contract.

## 6. Proposed TSP Fund Catalog seed rows (NOT created — for the future migration/seeder only)

Based only on the verified 16-fund active inventory in §1/§4. One row per fund, mapped to existing columns, consistent with the catalog shape already proposed in the prior architecture analysis (§18 there):

| fund_code | display_name | category | rate_config_key | lfund_distribution_key | balance_column | allocation_column | is_active | display_order |
|---|---|---|---|---|---|---|---|---|
| GFund | G Fund | core | TSPGFundReturn | — | GFund | GFundDist | true | 1 |
| FFund | F Fund | core | TSPFFundReturn | — | FFund | FFundDist | true | 2 |
| CFund | C Fund | core | TSPCFundReturn | — | CFund | CFundDist | true | 3 |
| SFund | S Fund | core | TSPSFundReturn | — | SFund | SFundDist | true | 4 |
| IFund | I Fund | core | TSPIFundReturn | — | IFund | IFundDist | true | 5 |
| LIncome | L Income | lifecycle | — | LIncome | LIncome | LIncomeDist | true | 6 |
| L2030 | L 2030 | lifecycle | — | L2030 | L2030 | L2030Dist | true | 7 |
| L2035 | L 2035 | lifecycle | — | L2035 | L2035 | L2035Dist | true | 8 |
| L2040 | L 2040 | lifecycle | — | L2040 | L2040 | L2040Dist | true | 9 |
| L2045 | L 2045 | lifecycle | — | L2045 | L2045 | L2045Dist | true | 10 |
| L2050 | L 2050 | lifecycle | — | L2050 | L2050 | L2050Dist | true | 11 |
| L2055 | L 2055 | lifecycle | — | L2055 | L2055 | L2055Dist | true | 12 |
| L2060 | L 2060 | lifecycle | — | L2060 | L2060 | L2060Dist | true | 13 |
| L2065 | L 2065 | lifecycle | — | L2065 | L2065 | L2065Dist | true | 14 |
| L2070 | L 2070 | lifecycle | — | L2070 | L2070 | L2070Dist | true | 15 |
| L2075 | L 2075 | lifecycle | — | L2075 | L2075 | L2075Dist | true | 16 |

**`L2025` seed row (retired, not active):** `fund_code=L2025, category=lifecycle, is_active=false, effective_end_date=2025-07-xx` (exact date not re-derived in this pass — only "July 2025" is stated in code comments), `balance_column=L2025, allocation_column=L2025Dist`. Included so historical cases retain a resolvable catalog reference; excluded from §1's active list.

**`L2020`: do NOT seed yet — pending §7 decision.** Seeding it as `is_active=false` would be consistent with the other retired fund, but unlike `L2025` there is no known retirement date, no historical precedent to anchor `effective_end_date`, and no confirmation this exclusion was intentional rather than a latent bug. Recommend resolving the §7 ambiguity before deciding whether `L2020` gets a catalog row at all.

## 7. Ambiguities that must be resolved before implementation

1. **`L2020`'s true status is undocumented.** Was its exclusion from `totalCurrentBalance`/`new_balance`/the PDF table/the admin edit form/the audit-history seeder a deliberate historical retirement (its 2020 target date had already passed before this system's real usage window) or an unnoticed bug? This determines whether it gets a `is_active=false` catalog row (with what `effective_end_date`) or is dropped from the catalog design entirely. Not resolved by this investigation — recommend asking whoever has institutional history with this codebase, or inspecting production data (any employee with a nonzero `L2020` balance would be strong evidence it was once live).
2. **`L2070`/`L2075` have no seeded Lifecycle glide-path (`lfundDistribution`) rows** in `database/seeds/lfundDistSeeder.php`, despite being part of the active 16-fund calculation/render set (added August 2025). At runtime they would fall back to `LIncome`'s distribution weights per the existing, documented fallback logic in `getDistributionForLfund_new()` — this may be intentional (safe default) or may mean real glide-path data was loaded directly into the production database outside this seeder file and was simply not captured here (this investigation did not query a live database). Recommend confirming against the actual running database before assuming the fallback is what production currently uses for these two funds.
3. **The Data Contract fund-list hardcoding is duplicated in at least 3 separate PHP files** (`EmployeeController.php`, `scripts/export_golden_master_contracts.php`, `scripts/validate_fact_finder_data_contract.php`, `scripts/validate_fact_finder_html_diff.php`) — any future fix (catalog-driven or otherwise) needs to update all of these consistently, or consolidate them into one shared source, to avoid re-introducing the same drift.

---

## Source files/locations supporting the conclusions above

- `benefits-software/app/Models/Tsp.php` — `$fillable` (stale; includes `L2020` but not `L2025`/`L2035`/`L2045`/`L2055`/`L2060`/`L2065`/`L2070`/`L2075`; does not gate direct property writes, see `updateEmployeeTsp()`)
- `benefits-software/app/Models/LfundsDist.php` — `lfundDistribution` model
- `benefits-software/database/migrations/2020_12_24_120538_add_colmns_in_tsp.php` — adds `L2025, L2035, L2045, L2055, L2060, L2065`
- `benefits-software/database/migrations/2023_01_06_212215_update_tsp_columns_size.php` — precision fix, same 6 columns
- `benefits-software/database/migrations/2025_01_27_000000_add_multiple_general_purpose_loan_columns_to_tsp.php` — unrelated (second GP loan columns), confirms no further fund columns added here
- `benefits-software/database/migrations/2025_08_23_000000_update_lifecycle_funds_2025.php` — adds `L2070, L2075`; retires `L2025` (data migration + comments)
- `benefits-software/database/migrations/2025_08_23_000001_fix_l2070_l2075_data_types.php` — precision fix for `L2070`/`L2075`
- `benefits-software/database/seeds/HistoryColumnsSeeder.php` (lines ~250-360) — audit-history column registry; has `L2025`/`L2025Dist`, lacks `L2020`/`L2020Dist`
- `benefits-software/database/seeds/lfundDistSeeder.php` — glide-path seed data; `L2025` (20 rows) and `L2030` confirmed present; `L2020`, `L2070`, `L2075` confirmed absent
- `benefits-software/app/Repositories/EmployeeRepository.php` — `getEmpTspDetails()` (~3567 `totalCurrentBalance`), `updateEmployeeTsp()` (~3676-3981, L2025/L2070/L2075 history+write handling), `getTSPNewBalance_new()` (~8886-9437, glide-path fallback logic + final `new_balance` sum), `calcProjectedEndingBalanceTsp()`/`getEmpTspConfigurations()` (rate config keys)
- `benefits-software/resources/views/admin/employee/tsp_edit.blade.php` (line 361) — per-employee balance/allocation admin form; `L2025` has a removal comment, `L2020` has no input and no comment
- `benefits-software/resources/views/admin/employee/report_pdf.blade.php` (~2126-2170 rates table, ~2265-2375 balance table) — confirms the 16-fund active render set and the 5-fund-only rates table (Lifecycle funds have no independent rate row)
- `benefits-software/app/Http/Controllers/Admin/EmployeeController.php` (~line 1654) — hardcoded 10-fund array feeding the Data Contract's `tsp.funds`
- `benefits-software/scripts/export_golden_master_contracts.php`, `scripts/validate_fact_finder_data_contract.php`, `scripts/validate_fact_finder_html_diff.php` — duplicate copies of the same hardcoded 10-fund array
- `benefits-software/scripts/output/golden_master_contracts/*.json` (24 files) — real exported Data Contracts, all show `L2020` present with `balance:0, allocation_pct:0` and no entries for `L2035/L2045/L2055/L2060/L2065/L2070/L2075`
- `advisor-portal-app/cases/fact_finder_data_contract.py` — `TspFundSerializer`/`TspSerializer` (schema side, no `fund_code` restriction, confirmed tolerant of any code)

---

## Git status — before and after this investigation

Confirmed identical before and after (only this one new document added in `advisor-portal-app`; `benefits-software` untouched):

```
# advisor-portal-app
 M cases/templates/cases/case_detail.html
 M cases/templates/cases/member_dashboard.html
 M cases/templates/cases/technician_dashboard.html
 M fact_finder_content/templates/fact_finder_content/content_block_detail.html
 M fact_finder_content/tests.py
 M fact_finder_content/views.py
?? FACT_FINDER_ADMIN_FUNCTIONAL_CAPABILITY_AUDIT.md
?? FACT_FINDER_ADMIN_PRESENTATION_LAYER_ANALYSIS.md
?? FACT_FINDER_PRE_MERGE_BACKOUT_PLAN.md
?? docs/TSP_DYNAMIC_FUND_MAINTENANCE_ARCHITECTURE_ANALYSIS.md
?? docs/TSP_CANONICAL_FUND_INVENTORY.md   <-- this document, the only new file

branch: main
HEAD: 0ad0268 Fix governed PDF content migration regressions

# benefits-software
 M storage/framework/views/2eb160819b4341aa7006926302ee7b3bd453c035.php
 M storage/framework/views/bc356608657637f9da38fe09d5107cd3dac44ba8.php
 D storage/framework/views/f8ce95c6c486c4d29c1c9df21c444a3746e97423.php
?? CASE_42210_USER_RESPONSE.md
?? IDEAL_TEST_CASE_SEARCH.md
?? PDF_ORIGINAL_REPORT_LOGIC_ANALYSIS_VALIDATED.md
?? PDF_REPORT_LITERAL_HARDCODING_INVENTORY.md
?? PDF_USER_FRIENDLY_CHANGE_SYNOPSIS.md
?? PDF_USER_LITERAL_AND_CONDITIONAL_LOGIC.md
?? PDF_WORK_REAPPLY_AND_RESET_PLAN.md
?? TSP_CASE_41216_ANALYSIS.md
?? TSP_DYNAMIC_FUND_ADD_DELETE_OPTIONS_ANALYSIS.md
?? TSP_PROJECTION_ANALYSIS.md
?? TSP_PROJECTION_BREAKDOWN.md
?? TSP_PROJECTION_USER_GUIDE.md
?? UNICORN_CASE_QUERIES.sql
?? UNICORN_CASE_REPORT.md
?? UNICORN_CASE_REPORT_FINAL.md
?? UNICORN_CASE_REPORT_REVISED.md
?? run_unicorn_report.ps1
?? storage/logs/
?? sync_dump_20260829_084609.sql

branch: master
HEAD: f9f5715 Fix governed PDF content spacing and checklist layout
```

All pre-existing modifications/untracked files above predate this investigation (unrelated prior session work) — not caused by this task.
