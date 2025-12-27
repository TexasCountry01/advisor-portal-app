# MISSING FORM FIELDS - ABSOLUTE CONFIRMATION

## Problem Statement
The HTML form (fact_finder_form.html) is missing 36 input fields that the backend view (cases/views.py) expects to receive. When users fill out the web form manually, these fields send NO DATA, resulting in blank sections in the PDF.

The test script works because it bypasses the HTML form and directly submits POST data with all field names.

## 36 MISSING FIELDS

### Employment History Section (Missing 5 fields)
**Backend expects but form doesn't have:**
1. `agency` - Current federal agency
2. `position_title` - Job title
3. `grade_step` - Grade and step (e.g., "GS-12 Step 5")
4. `has_other_agencies` - Checkbox for prior agencies
5. `other_agencies` - Text description of other agencies

**Impact:** Employment history section completely empty in PDF

---

### Pay Information Section (Missing 3 fields)
**Backend expects but form doesn't have:**
6. `annual_base_salary` - Base annual salary
7. `locality_pay_amount` - Locality pay amount
8. `high_three_average` - High-3 average salary

**Impact:** Pay details section mostly empty in PDF

---

### TSP Section (Missing 5 fields)
**Backend expects but form doesn't have:**
9. `tsp_current_balance` - Total TSP balance
10. `tsp_traditional_balance` - Traditional TSP balance
11. `tsp_roth_balance` - Roth TSP balance
12. `tsp_contribution_pct` - Total contribution percentage
13. `tsp_employee_contribution_pct` - Employee contribution percentage
14. `tsp_agency_match_pct` - Agency match percentage
15. `tsp_catchup` - Catch-up contribution checkbox

**Impact:** TSP overview section incomplete

---

### Retirement Planning (Missing 2 fields)
**Backend expects but form doesn't have:**
16. `retirement_timing` - When planning to retire (text)
17. `years_of_service` - Total years of service

**Impact:** Retirement timing incomplete

---

### Social Security (Missing 2 fields)
**Backend expects but form doesn't have:**
18. `ss_estimated_benefit` - Estimated SS benefit
19. `ss_covered_employment` - SS covered employment checkbox

**Impact:** SS section incomplete

---

### Other Retirement Accounts (Missing 3 fields)
**Backend expects but form doesn't have:**
20. `ira_balance` - IRA balance
21. `other_retirement_balance` - Other retirement account balances
22. `other_investments` - Other investments description

**Impact:** Other retirement section completely empty

---

### Military Active Duty (Missing 2 fields)
**Backend expects but form doesn't have:**
23. `active_duty_deposit` - Deposit made radio (Yes/No/Unsure)
24. `active_duty_owe_amount` - Amount owed if deposit not made

**Note:** Form has `military_deposit` checkbox but view expects `active_duty_deposit` radio buttons

---

### Military Reserves (Missing 1 field)
**Backend expects but form doesn't have:**
25. `reserve_owe_amount` - Amount owed (form has reserve_owe_amount_check instead)

---

### Military Academy (Missing 1 field)
**Backend expects but form doesn't have:**
26. `academy_owe_amount` - Amount owed (form has academy_owe_type instead)

---

### Non-Deduction Service (Missing 1 field)
**Backend expects but form doesn't have:**
27. `non_deduction_owe_amount` - Amount owed (form has non_deduction_owe_type instead)

---

### Break in Service (Missing 1 field)
**Backend expects but form doesn't have:**
28. `break_service_owe_amount` - Amount owed (form has break_service_owe_type instead)

---

### Part-Time Service (Missing 1 field)
**Backend expects but form doesn't have:**
29. `part_time_on_sf50` - Shows on SF-50 checkbox

---

### FEGLI (Missing 1 field)
**Backend expects but form doesn't have:**
30. `fegli_children_ages` - Children's ages for FEGLI

**Note:** Form has `children_ages` in basic info, but backend expects separate `fegli_children_ages`

---

### FEHB (Missing 4 fields - NAMING MISMATCH)
**Backend expects these names:**
31. `fehb_health_coverage_self_only` - Self only coverage
32. `fehb_health_5_year_requirement` - 5 year requirement
33. `fehb_keep_coverage_in_retirement` - Keep in retirement
34. `fehb_spouse_reliant_on_plan` - Spouse reliant on plan
35. `fehb_other_coverage_tricare` - Other coverage - TRICARE

**Form has DIFFERENT names:**
- `fehb_health_self_only` instead of `fehb_health_coverage_self_only`
- `fehb_health_5_years` instead of `fehb_health_5_year_requirement`
- `fehb_keep_in_retirement` instead of `fehb_keep_coverage_in_retirement`
- `fehb_spouse_reliant` instead of `fehb_spouse_reliant_on_plan`
- `other_health_tricare` instead of `fehb_other_coverage_tricare`

---

### FLTCIP (Missing 2 fields - NAMING MISMATCH)
**Backend expects:**
36. `fltcip_other_premium` - Other premium amount
37. `fltcip_benefit_period_3yrs` - 3 year benefit period

**Form has:**
- `fltcip_family_premium` instead of `fltcip_other_premium`
- `fltcip_period_3yrs` instead of `fltcip_benefit_period_3yrs`

---

### Additional Information (Missing 2 fields)
**Backend expects but form doesn't have:**
38. `retirement_goals` - Retirement goals text
39. `retirement_concerns` - Retirement concerns text

---

### Basic Information (Missing 1 field)
**Backend expects but form doesn't have:**
40. `spouse_income` - Spouse's annual income

---

## TOTAL IMPACT

**36 fields missing or misnamed** = Approximately **20-30% of form data not captured** when using the web form manually.

## Why Test Script Works

The test script directly submits POST data with correct field names, completely bypassing the HTML form. That's why the PDF looks perfect with the test data but blank with manual entry.

## Solution Required

1. **Add missing input fields** to fact_finder_form.html
2. **Rename mismatched fields** to match backend expectations
3. **Test with manual form submission** (not just script)

## Verification Method

After fixing:
1. Fill out form manually through web interface
2. Submit case
3. View PDF
4. Confirm all sections populated (not just test script success)
