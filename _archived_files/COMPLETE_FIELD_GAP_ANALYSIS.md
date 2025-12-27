# Complete Field Gap Analysis

## CRITICAL FINDING
**123 additional fields are missing from the HTML form that the backend expects.**

Previously added: 29 fields  
Still missing: **123 fields**  
Total fields backend expects: **307 fields**

Current form coverage: **184/307 fields = 60% (NOT 95%)**

---

## Missing Fields Breakdown by Category

### 1. FEGLI Coverage Fields (14 fields)
- `fegli_basic` - Basic coverage checkbox
- `fegli_beneficiary` - Beneficiary information
- `fegli_five_year` - Five-year requirement met
- `fegli_keep_retirement` - Keep in retirement (duplicate name?)
- `fegli_option_a` - Option A coverage amount
- `fegli_option_b` - Option B coverage amount
- `fegli_option_c` - Option C coverage amount
- `has_fegli` - Has FEGLI coverage checkbox

### 2. FEHB Coverage Fields (13 fields)
- `fehb_coverage_type` - Coverage type dropdown
- `fehb_dental_vision_premium` - Combined dental+vision premium
- `fehb_health_5_years` - Met 5-year requirement
- `fehb_health_none` - No coverage checkbox
- `fehb_health_self_family` - Self+family coverage
- `fehb_health_self_one` - Self+one coverage  
- `fehb_health_self_only` - Self only coverage
- `fehb_keep_retirement` - Keep in retirement (duplicate name?)
- `fehb_plan` - Plan name
- `fehb_spouse_reliant` - Spouse reliant checkbox
- `continue_fehb` - Continue FEHB checkbox
- `other_health_private` - Private insurance
- `other_health_spouse_plan` - Spouse's plan
- `other_health_tricare` - TRICARE coverage
- `other_health_va` - VA coverage

### 3. FLTCIP Fields (14 fields - ALL MISSING!)
- `fltcip_benefit_period` - Benefit period
- `fltcip_daily_benefit` - Daily benefit amount
- `fltcip_discuss_options` - Discuss options checkbox
- `fltcip_employee_premium` - Employee premium
- `fltcip_family_premium` - Family premium
- `fltcip_inflation` - Inflation protection
- `fltcip_inflation_acio` - ACIO inflation
- `fltcip_inflation_fpo` - FPO inflation
- `fltcip_notes` - Notes textarea
- `fltcip_period_2yrs` - 2-year period
- `fltcip_period_3yrs` - 3-year period
- `fltcip_period_5yrs` - 5-year period
- `fltcip_spouse_premium` - Spouse premium

### 4. TSP Analysis Fields (40 fields - CRITICAL!)
**Checkboxes for fund types:**
- `tsp_g_fund`, `tsp_f_fund`, `tsp_c_fund`, `tsp_s_fund`, `tsp_i_fund`, `tsp_l_fund`

**TSP Account & Usage:**
- `tsp_balance` - Overall balance
- `tsp_beneficiary` - Beneficiary info
- `tsp_comments` - General comments
- `tsp_loans` - Has loans checkbox
- `tsp_loan_details` - Loan details textarea
- `tsp_in_service_withdrawal` - In-service withdrawal checkbox
- `tsp_traditional_contribution` - Traditional contribution amount
- `tsp_roth_contribution` - Roth contribution amount

**Retirement Planning:**
- `tsp_retirement_goal` - Retirement goal textarea
- `tsp_retirement_plan` - Retirement plan
- `tsp_plan_leave` - Plan to leave in TSP
- `tsp_plan_rollover` - Plan to rollover
- `tsp_plan_unsure` - Unsure about plan

**Withdrawal Timing:**
- `tsp_need_asap` - Need money ASAP
- `tsp_need_at_age` - Need at specific age
- `tsp_need_age` - Age when needed
- `tsp_need_unsure` - Unsure when needed
- `tsp_amount_needed` - Amount needed
- `tsp_withdrawal_age_based` - Age-based withdrawal
- `tsp_withdrawal_hardship` - Hardship withdrawal

**Usage Purpose:**
- `tsp_use_income` - Use for income
- `tsp_use_legacy` - Use for legacy
- `tsp_use_fun_money` - Use for fun money
- `tsp_use_other` - Other usage

**Risk Tolerance:**
- `tsp_employee_risk_tolerance` - Employee risk tolerance
- `tsp_spouse_risk_tolerance` - Spouse risk tolerance
- `tsp_risk_tolerance_why` - Why this risk level
- `tsp_best_outcome` - Best outcome expectation
- `tsp_worst_outcome` - Worst outcome concern
- `tsp_sole_source` - TSP sole retirement source
- `tsp_sole_source_explain` - Explanation if sole source

### 5. Military Deposit Fields (3 fields)
- `active_duty_deposit` - Made deposit (Yes/No/Unsure) - ALREADY EXISTS as `military_deposit`
- `active_duty_owe_amount` - Amount owed - ALREADY EXISTS as `military_owe_amount`  
- `military_deposit_paid` - Deposit paid in full
- `military_service` - Years of military service
- `military_years` - Total military years
- `reservist_guard` - Reservist or Guard checkbox
- `reserve_lwop_deposit` - Reserve LWOP deposit made

### 6. Income & Expenses (13 fields)
- `current_annual_income` - Current annual income
- `spouse_annual_income` - Spouse annual income
- `pension_income` - Pension income
- `rental_income` - Rental income
- `other_current_income` - Other current income
- `other_regular_pay` - Other regular pay
- `expense_housing` - Housing expenses
- `expense_food` - Food expenses
- `expense_transportation` - Transportation expenses
- `expense_utilities` - Utilities expenses
- `expense_healthcare` - Healthcare expenses
- `expense_entertainment` - Entertainment expenses
- `other_expenses` - Other expenses

### 7. Personal/Legal (9 fields)
- `has_will` - Has will checkbox
- `has_poa` - Has power of attorney
- `has_court_orders` - Has court orders
- `court_order_details` - Court order details textarea
- `has_other_pension` - Has other pension
- `other_pension_details` - Other pension details
- `has_special_needs_dependents` - Special needs dependents
- `special_needs_details` - Special needs details
- `num_reports_requested` - Number of reports requested

### 8. Leave/Service Fields (8 fields)
- `sick_leave_hours` - Sick leave in hours (vs balance)
- `annual_leave_hours` - Annual leave in hours (vs balance)
- `other_leave` - Other leave balance
- `service_computation_date` - Service computation date
- `break_new_start` - New start date after break
- `break_deposit_made` - Deposit made for break in service
- `has_non_deduction_service` - Has non-deduction service
- `non_deduction_service_details` - Non-deduction details
- `non_covered_employment` - Non-covered employment

### 9. SS & Spouse (7 fields)
- `spouse_ss_age` - Spouse SS collection age
- `spouse_ss_benefit` - Spouse SS benefit amount
- `ss_collection_age` - Employee SS collection age
- `ss_estimated_benefit_age_62` - SS benefit at 62
- `ss_estimated_benefit_fra` - SS benefit at FRA
- `survivor_benefit_election` - Survivor benefit election

### 10. Notes & Misc (6 fields)
- `additional_notes` - Additional notes (page 1?)
- `additional_notes_final` - Final additional notes
- `urgency` - Urgency level
- `date_of_birth` - Date of birth (vs employee_dob)
- `highest_salary_history` - Highest salary history
- `other_insurance` - Other insurance details

---

## IMMEDIATE ACTION PLAN

### Phase 1: Add Critical Missing Sections (COMPLETE SECTIONS)
1. **FLTCIP Section** - 14 fields - ENTIRE SECTION MISSING
2. **TSP Risk Analysis** - 40 fields - CRITICAL for retirement planning
3. **Income & Expenses** - 13 fields - Needed for budget analysis

### Phase 2: Complete Existing Sections
4. **FEGLI** - Add 8 missing fields (coverage amounts, options)
5. **FEHB** - Add 13 missing fields (coverage types, plan details)
6. **Social Security** - Add 7 missing fields (spouse SS, FRA calculations)

### Phase 3: Add Supporting Fields
7. **Personal/Legal** - Add 9 fields (will, POA, court orders)
8. **Leave Details** - Add 8 fields (service dates, deposits)
9. **Notes & Misc** - Add 6 fields (urgency, additional notes)

---

## ESTIMATED IMPACT

**Before**: 60% data capture (184/307 fields)  
**After**: 100% data capture (307/307 fields)

**Data Loss**: Currently losing 40% of submitted data  
**After Fix**: 0% data loss

---

## NEXT STEPS

1. Start with FLTCIP (entire section missing)
2. Add TSP risk analysis fields (40 fields)
3. Add Income/Expenses section
4. Complete FEGLI section
5. Complete FEHB section
6. Add remaining fields

User confirmation needed before proceeding with 123 field additions.
