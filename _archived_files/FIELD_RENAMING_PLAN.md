# Field Renaming Implementation Plan
**Status:** In Progress  
**Objective:** Achieve absolute consistency between HTML form field names and PDF template variables

## Naming Convention Standard

### Current Problem
- **Form fields:** Flat naming with underscores (`tsp_f_balance`, `fegli_premium_1`)
- **Database:** Nested JSON structure (`fact_finder_data.tsp.f_balance`)
- **PDF Template:** Expects nested structure (`{{ tsp.f_fund_balance }}`)

### New Standard (Canonical)
**Use PDF template variable names as the source of truth:**

1. **TSP Fields:** Add `_fund` suffix for fund-specific fields
   - OLD: `tsp_f_balance` → NEW: `tsp_f_fund_balance`
   - OLD: `tsp_g_allocation` → NEW: `tsp_g_fund_allocation`

2. **Nested References:** Template variable `{{ section.field }}` → Form name `section_field`
   - Template: `{{ fegli.premium_1 }}` → Form: `fegli_premium_1` ✓ (already matches)
   - Template: `{{ tsp.f_fund_balance }}` → Form: `tsp_f_fund_balance` (needs update)

3. **Consistency Rule:**
   ```
   Template Variable: {{ section.field_name }}
   Form Field Name:   section_field_name
   Database Path:     fact_finder_data['section']['field_name']
   ```

## Implementation Steps

### Step 1: Create Field Mapping Matrix ✓
- Extracted all 236 form fields
- Extracted all 104 PDF template variables
- Identified mismatches

### Step 2: Document Specific Renames (Current)
List every field that needs renaming with old→new mapping.

### Step 3: Update HTML Form
Update `cases/templates/cases/fact_finder_form.html`:
- Change `name="old_field"` to `name="new_field"` for all mismatches
- Preserve all other attributes (id, class, etc.)

### Step 4: Update Views Processing
Update `cases/views.py` `case_submit()` function:
- Update `request.POST.get('old_field')` to `request.POST.get('new_field')`
- Verify all 236 fields captured correctly
- Database structure remains the same (nested JSON)

### Step 5: Test & Verify
- Delete existing test cases
- Submit new test case with ALL fields populated
- Verify database contains all 236 fields
- Generate PDF
- Confirm all fields display correctly

## Field Renames Required

### TSP Section (67 fields need updates)

**Fund Balances & Allocations:**
```
tsp_g_allocation → tsp_g_fund_allocation
tsp_g_balance → tsp_g_fund_balance
tsp_f_allocation → tsp_f_fund_allocation
tsp_f_balance → tsp_f_fund_balance
tsp_c_allocation → tsp_c_fund_allocation
tsp_c_balance → tsp_c_fund_balance
tsp_s_allocation → tsp_s_fund_allocation
tsp_s_balance → tsp_s_fund_balance
tsp_i_allocation → tsp_i_fund_allocation
tsp_i_balance → tsp_i_fund_balance
```

**L Funds:**
```
tsp_l_income_allocation → tsp_l_income_fund_allocation
tsp_l_income_balance → tsp_l_income_fund_balance
tsp_l2025_allocation → tsp_l2025_fund_allocation
tsp_l2025_balance → tsp_l2025_fund_balance
... (repeat for all L funds: 2030, 2035, 2040, 2045, 2050, 2055, 2060, 2065_70)
```

**Other TSP Fields:**
```
tsp_goal_amount → tsp_retirement_goal
tsp_need_amount → tsp_amount_needed
tsp_sole_explain → tsp_sole_source_explain
tsp_traditional_contributions → tsp_traditional_contribution
tsp_roth_contributions → tsp_roth_contribution
risk_tolerance_employee → tsp_employee_risk_tolerance
risk_tolerance_spouse → tsp_spouse_risk_tolerance
risk_tolerance_why → tsp_risk_tolerance_why
tsp_best_result → tsp_best_outcome
tsp_worst_result → tsp_worst_outcome
```

**TSP Loan Fields:**
```
tsp_loan_general_balance → tsp_loan_general_balance (matches ✓)
tsp_loan_general_date → tsp_loan_general_date (matches ✓)
tsp_loan_general_payoff_date → tsp_loan_general_payoff_date (matches ✓)
tsp_loan_general_repayment → tsp_loan_general_repayment (matches ✓)
tsp_loan_residential_balance → tsp_loan_residential_balance (matches ✓)
tsp_loan_residential_date → tsp_loan_residential_date (matches ✓)
tsp_loan_residential_payoff_date → tsp_loan_residential_payoff_date (matches ✓)
tsp_loan_residential_repayment → tsp_loan_residential_repayment (matches ✓)
```

### FEGLI Section (Already matches ✓)
```
fegli_premium_1 → fegli_premium_1 (no change)
fegli_premium_2 → fegli_premium_2 (no change)
fegli_premium_3 → fegli_premium_3 (no change)
fegli_premium_4 → fegli_premium_4 (no change)
fegli_5_years_coverage → fegli_five_year_requirement (needs update)
fegli_keep_in_retirement → fegli_keep_in_retirement (no change)
fegli_sole_source → fegli_sole_source (no change)
fegli_purpose → fegli_purpose (no change)
fegli_children_ages → fegli_children_ages (no change)
fegli_notes → fegli_notes (no change)
```

### FEHB Section
```
fehb_health_premium → fehb_health_premium (matches ✓)
fehb_dental_premium → fehb_dental_premium (matches ✓)
fehb_vision_premium → fehb_vision_premium (matches ✓)
... (verify all FEHB fields)
```

### Military & Special Service Sections
**Need detailed audit from subagent report - names don't follow consistent pattern**

### Retirement Pay & Leave (RPL) Section
```
leave_scd → rpl_leave_scd
retirement_scd → rpl_retirement_scd
desired_retirement_date → rpl_desired_retirement_date
... (all retirement/pay/leave fields need rpl_ prefix)
```

## Next Action
Extract complete rename list from subagent audit report and create SQL-style UPDATE statements for clarity.
