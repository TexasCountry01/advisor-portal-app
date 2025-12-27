# Field Mapping Strategy: Database → PDF Template

## Current Database Structure → PDF Template Mapping

### Page 1-2: Basic Info, Retirement, Pay & Leave

| PDF Field | Database Path |
|-----------|---------------|
| Employee name | `data.basic_information.employee_name` | ✓ Mapped
| Employee DOB | `data.basic_information.employee_dob` | ✓ Mapped  
| Spouse name | `data.basic_information.spouse_name` | ✓ Mapped
| Spouse DOB | `data.basic_information.spouse_dob` | ✓ Mapped
| Address | `data.basic_information.address` | ✓ Mapped
| City, State, Zip | `data.basic_information.city/state/zip` | ✓ Mapped
| Retirement System | `data.retirement_system.system` | ⚠️ Need to map
| CSRS Offset date | `data.retirement_system.csrs_offset_date` | ✓ Mapped
| FERS Transfer date | `data.retirement_system.fers_transfer_date` | ✓ Mapped
| Employee Type | `data.employee_type.type` | ⚠️ Need to map
| LEO start date | `data.employee_type.leo_start_date` | ✓ Mapped
| CBPO coverage | `data.employee_type.cbpo_coverage` | ⚠️ Need to map
| FF start date | `data.employee_type.ff_start_date` | ✓ Mapped
| ATC start date | `data.employee_type.atc_start_date` | ✓ Mapped
| FS start date | `data.employee_type.fs_start_date` | ✓ Mapped
| Retirement Type | `data.retirement_type.type` | ⚠️ Need to map
| Optional offer date | `data.retirement_type.optional_offer_date` | ⚠️ Need to map
| Leave SCD | `data.retirement_pay_leave.leave_scd` | ⚠️ Need to map
| Retirement SCD | `data.retirement_pay_leave.retirement_scd` | ⚠️ Need to map
| Retirement timing | `data.retirement_pay_leave.retirement_timing` | ⚠️ Need to map
| Retirement age | `data.retirement_pay_leave.retirement_age` | ⚠️ Need to map
| Current salary | `data.pay_information.annual_base_salary` | ⚠️ Need to map
| Sick leave hours | `data.leave_balances.sick_leave_hours` | ❌ Using wrong path (sick_leave)
| Annual leave hours | `data.leave_balances.annual_leave_hours` | ❌ Using wrong path (annual_leave)
| SS at 62 | `data.social_security.estimated_benefit` | ❌ Using wrong path (benefit_at_62)
| SS desired age | `data.social_security.collection_age` | ❌ Using wrong path (desired_start_age)

### Page 2: Military Service  

**MISSING FROM DATABASE!** The reference PDF has detailed military sections:
- Military Active Duty (dates, deposit, pension, overseas time)
- Military Reserves (dates, creditable time, deposit, pension start age)
- Military Academy (dates, deposit)

Current database only has:
- `employment_history.military_service` (text)
- `employment_history.military_years` (text)
- `employment_history.military_deposit_paid` (boolean)

**ACTION NEEDED**: Either:
1. Add detailed military fields to database schema
2. Or map what exists from employment_history

### Page 3: Special Federal Service

**MISSING FROM DATABASE!** The reference PDF has:
- Non-Deduction Service (dates, deposit amount owed, notes)
- Break-in-Service (original dates, break dates, refund/redeposit, notes)
- Part-Time Service (dates, hours/week, contribution status, notes)

Current database only has:
- `employment_history.has_non_deduction_service` (boolean)
- `employment_history.non_deduction_service_details` (text)

**ACTION NEEDED**: Add special service fields to database

### Page 4: Insurance (FEGLI, FEHB, FLTCIP)

**PARTIALLY MAPPED**:
- FEGLI: `insurance_beneficiaries.has_fegli`, `fegli_basic/option_a/b/c`
- FEHB: `insurance_beneficiaries.fehb_plan`, `fehb_coverage_type`, `continue_fehb`

**MISSING**: 
- FEGLI premium amounts (4 lines)
- FEGLI 5-year requirement, sole source, purpose, children ages
- FEHB health/dental/vision premium amounts
- FEHB 5-year requirement, spouse reliance, other coverage (TRICARE/VA)
- FLTCIP premium amounts, daily benefit, benefit period, inflation protection

### Page 5: TSP

**PARTIALLY MAPPED**:
- TSP balance: `tsp.balance`
- Contributions: `tsp.contribution_pct`, `tsp.catchup`
- Fund balances: `tsp.g_fund`, `f_fund`, `c_fund`, `s_fund`, `i_fund`, `l_fund`
- Loans: `tsp.loans`, `loan_details`

**MISSING**:
- Retirement goal amount
- Amount needed & when
- Sole source explanation
- Plan for TSP at retirement
- In-service withdrawal
- Traditional vs Roth contributions (separate amounts)
- Loan details table (type, date, balance, repayment, payoff date)
- Fund allocation percentages
- Risk tolerance ratings
- Best/worst outcome questions
- Comments/notes

### Page 6: Additional Notes

**MAPPED**: `additional_information.additional_notes`
But template uses wrong path: `data.additional_notes`

## Summary of Required Changes

### Fix 1: Correct Field Paths in Template
- `data.leave_balances.annual_leave` → `data.leave_balances.annual_leave_hours`
- `data.leave_balances.sick_leave` → `data.leave_balances.sick_leave_hours`
- `data.additional_notes` → `data.additional_information.additional_notes`
- Remove references to non-existent: `service_history_notes`, `benefit_at_62`, `desired_start_age`

### Fix 2: Add Missing Mappings to Template
Map these existing database fields that are currently unused:
- Retirement system, employee type, retirement type selections
- Pay information (salary, locality, high-3)
- Social Security (estimated_benefit, collection_age)
- All TSP fields
- FEGLI/FEHB basic fields
- Retirement planning fields

### Fix 3: Database Schema Extensions (Future)
For complete PDF matching reference, would need to add:
- Detailed military service tables (active/reserves/academy)
- Special federal service tables (non-deduction/break/part-time)
- Insurance premium amounts and additional questions
- TSP extended fields (risk tolerance, goals, etc.)

### Fix 4: Use What We Have Now
For immediate functionality, template should:
1. Use all available database fields
2. Show empty/blank for missing reference PDF fields
3. Map text fields where detailed structure doesn't exist
