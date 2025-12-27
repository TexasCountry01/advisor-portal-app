# Complete Field Renaming Map
**Date:** December 26, 2025  
**Purpose:** Rename all HTML form fields to match PDF template variable expectations

## TSP Section Renames

| Current Form Field Name | New Form Field Name | Notes |
|------------------------|---------------------|-------|
| `tsp_goal_amount` | `tsp_retirement_goal` | |
| `tsp_need_amount` | `tsp_amount_needed` | |
| `tsp_sole_explain` | `tsp_sole_source_explain` | |
| `tsp_traditional_contributions` | `tsp_traditional_contribution` | Remove plural |
| `tsp_roth_contributions` | `tsp_roth_contribution` | Remove plural |
| `tsp_loan_general_date` | `tsp_general_loan_date` | Reorder words |
| `tsp_loan_general_balance` | `tsp_general_loan_balance` | Reorder words |
| `tsp_loan_general_repayment` | `tsp_general_loan_repayment` | Reorder words |
| `tsp_loan_general_payoff_date` | `tsp_general_loan_payoff` | Reorder & shorten |
| `tsp_loan_residential_date` | `tsp_residential_loan_date` | Reorder words |
| `tsp_loan_residential_balance` | `tsp_residential_loan_balance` | Reorder words |
| `tsp_loan_residential_repayment` | `tsp_residential_loan_repayment` | Reorder words |
| `tsp_loan_residential_payoff_date` | `tsp_residential_loan_payoff` | Reorder & shorten |
| `tsp_g_balance` | `tsp_g_fund_balance` | Add `_fund` |
| `tsp_g_allocation` | `tsp_g_fund_allocation` | Add `_fund` |
| `tsp_f_balance` | `tsp_f_fund_balance` | Add `_fund` |
| `tsp_f_allocation` | `tsp_f_fund_allocation` | Add `_fund` |
| `tsp_c_balance` | `tsp_c_fund_balance` | Add `_fund` |
| `tsp_c_allocation` | `tsp_c_fund_allocation` | Add `_fund` |
| `tsp_s_balance` | `tsp_s_fund_balance` | Add `_fund` |
| `tsp_s_allocation` | `tsp_s_fund_allocation` | Add `_fund` |
| `tsp_i_balance` | `tsp_i_fund_balance` | Add `_fund` |
| `tsp_i_allocation` | `tsp_i_fund_allocation` | Add `_fund` |
| `tsp_l2025_balance` | `tsp_l_2025_balance` | Add underscore |
| `tsp_l2025_allocation` | `tsp_l_2025_allocation` | Add underscore |
| `tsp_l2030_balance` | `tsp_l_2030_balance` | Add underscore |
| `tsp_l2030_allocation` | `tsp_l_2030_allocation` | Add underscore |
| `tsp_l2035_balance` | `tsp_l_2035_balance` | Add underscore |
| `tsp_l2035_allocation` | `tsp_l_2035_allocation` | Add underscore |
| `tsp_l2040_balance` | `tsp_l_2040_balance` | Add underscore |
| `tsp_l2040_allocation` | `tsp_l_2040_allocation` | Add underscore |
| `tsp_l2045_balance` | `tsp_l_2045_balance` | Add underscore |
| `tsp_l2045_allocation` | `tsp_l_2045_allocation` | Add underscore |
| `tsp_l2050_balance` | `tsp_l_2050_balance` | Add underscore |
| `tsp_l2050_allocation` | `tsp_l_2050_allocation` | Add underscore |
| `tsp_l2055_balance` | `tsp_l_2055_balance` | Add underscore |
| `tsp_l2055_allocation` | `tsp_l_2055_allocation` | Add underscore |
| `tsp_l2060_balance` | `tsp_l_2060_balance` | Add underscore |
| `tsp_l2060_allocation` | `tsp_l_2060_allocation` | Add underscore |
| `tsp_l2065_70_balance` | `tsp_l_2065_balance` | Remove `_70`, add underscore |
| `tsp_l2065_70_allocation` | `tsp_l_2065_allocation` | NEW: Add this field to PDF template |
| `risk_tolerance_employee` | `tsp_employee_risk_tolerance` | Add `tsp_` prefix, reorder |
| `risk_tolerance_spouse` | `tsp_spouse_risk_tolerance` | Add `tsp_` prefix, reorder |
| `risk_tolerance_why` | `tsp_risk_tolerance_why` | Add `tsp_` prefix |
| `tsp_best_result` | `tsp_best_outcome` | Change `result` to `outcome` |
| `tsp_worst_result` | `tsp_worst_outcome` | Change `result` to `outcome` |

**Fields that match (no change needed):**
- `tsp_use_income`
- `tsp_use_fun_money`
- `tsp_use_legacy`
- `tsp_use_other`
- `tsp_need_asap`
- `tsp_need_at_age` (not in PDF, keep as is)
- `tsp_need_age`
- `tsp_need_unsure`
- `tsp_sole_source`
- `tsp_plan_leave`
- `tsp_plan_rollover`
- `tsp_plan_unsure`
- `tsp_in_service_withdrawal`
- `tsp_withdrawal_hardship`
- `tsp_withdrawal_age_based`
- `tsp_l_income_balance`
- `tsp_l_income_allocation`
- `tsp_comments`

## FEGLI Section Renames

| Current Form Field Name | New Form Field Name | Notes |
|------------------------|---------------------|-------|
| `fegli_5_years_coverage` | `fegli_five_year_requirement` | Spell out number, change wording |

**Fields that match (no change needed):**
- `fegli_premium_1`
- `fegli_premium_2`
- `fegli_premium_3`
- `fegli_premium_4`
- `fegli_keep_in_retirement`
- `fegli_sole_source`
- `fegli_purpose`
- `fegli_children_ages`
- `fegli_notes`

## Summary Statistics
- **Total TSP renames:** 48 fields
- **Total FEGLI renames:** 1 field
- **FEHB, FLTCIP, Military sections:** Pending detailed audit
- **Estimated total renames:** ~80-100 fields across all sections

## Implementation Approach
1. Start with TSP section (48 renames) - highest impact
2. Update form HTML
3. Update views.py processing
4. Test TSP section completely
5. Move to next section
6. Repeat until all sections complete
