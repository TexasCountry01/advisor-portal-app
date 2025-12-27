"""
Validate that test data field names match actual form field names
"""

# Actual form field names (from fact_finder_form.html)
FORM_FIELDS = [
    'member_name', 'date_submitted', 'workshop_code', 'requested_due_date',
    'employee_name', 'employee_dob', 'spouse_name', 'spouse_fed_emp', 'spouse_dob',
    'address', 'city', 'state', 'zip',
    'retirement_system', 'csrs_offset_date', 'fers_transfer_date',
    'retirement_type', 'optional_offer_date',
    'employee_type', 'leo_start_date', 'cbpo_coverage', 'ff_start_date', 'atc_start_date', 'fs_start_date',
    'leave_scd', 'retirement_scd', 'retirement_fully_eligible', 'retirement_mra_10',
    'retirement_by_age', 'retirement_age', 'retirement_by_date', 'desired_retirement_date',
    'reduce_spousal_pension', 'spouse_protection_reason', 'court_order_dividing_benefits',
    'current_annual_salary', 'expects_highest_three',
    'sick_leave_balance', 'annual_leave_balance',
    'ss_age_62', 'ss_benefit_62', 'ss_desired_age', 'ss_benefit_desired',
    'retirement_pay_leave_notes',
    'no_military_service',
    'active_duty', 'active_duty_start', 'active_duty_end', 'military_deposit',
    'military_owe_zero', 'military_owe_amount_check', 'military_owe_amount', 'military_owe',
    'lwop_us_start', 'lwop_us_end', 'lwop_deposit',
    'retired_active_duty', 'military_pension_amount', 'scd_overseas_time',
    'military_active_duty_notes',
    'reserve', 'reserve_start', 'reserve_end',
    'reserve_credit_years', 'reserve_credit_months', 'reserve_credit_days', 'reserve_credit',
    'reserve_deposit', 'reserve_owe_zero', 'reserve_owe_amount_check', 'reserve_owe_amount', 'reserve_owe',
    'reserve_lwop_us_start', 'reserve_lwop_us_end', 'reserve_lwop_deposit',
    'retired_reserves', 'reserve_pension_amount', 'reserve_pension_start_age',
    'military_reserves_notes',
    'academy_service', 'academy_start', 'academy_end', 'academy_deposit_made',
    'academy_owe_type', 'academy_owe_amount', 'academy_in_leave_scd',
    'military_academy_notes',
    'no_special_service',
    'non_deduction_service', 'non_deduction_start', 'non_deduction_end',
    'non_deduction_deposit_made', 'non_deduction_owe_type', 'non_deduction_owe_amount',
    'non_deduction_notes',
    'break_in_service', 'original_service_start', 'original_service_end',
    'break_service_start', 'break_service_end', 'took_refund', 'redeposit_made',
    'break_service_owe_type', 'break_service_owe_amount',
    'break_in_service_notes',
    'part_time_service', 'part_time_start', 'part_time_end',
    'part_time_hours_per_week', 'part_time_contributed', 'part_time_notes',
    'other_pertinent_details',
    'fegli_premium_1', 'fegli_premium_2', 'fegli_premium_3', 'fegli_premium_4',
    'fegli_five_year_requirement', 'fegli_keep_in_retirement', 'fegli_sole_source',
    'fegli_purpose', 'children_ages', 'fegli_notes',
    'fehb_health_premium', 'fehb_dental_premium', 'fehb_vision_premium', 'fehb_dental_vision_premium',
    'fehb_health_self_only', 'fehb_health_self_one', 'fehb_health_self_family', 'fehb_health_none',
    'fehb_health_5_years', 'fehb_keep_in_retirement', 'fehb_spouse_reliant',
    'other_health_tricare', 'other_health_va', 'other_health_spouse_plan', 'other_health_private',
    'fehb_notes',
    'fltcip_employee_premium', 'fltcip_spouse_premium', 'fltcip_family_premium',
    'fltcip_daily_benefit', 'fltcip_period_2yrs', 'fltcip_period_3yrs', 'fltcip_period_5yrs',
    'fltcip_inflation_acio', 'fltcip_inflation_fpo', 'fltcip_discuss_options',
    'fltcip_notes',
    'tsp_use_income', 'tsp_use_fun_money', 'tsp_use_legacy', 'tsp_use_other',
    'tsp_retirement_goal', 'tsp_amount_needed',
    'tsp_need_asap', 'tsp_need_at_age', 'tsp_need_age', 'tsp_need_unsure',
    'tsp_sole_source', 'tsp_sole_source_explain',
    'tsp_plan_leave', 'tsp_plan_rollover', 'tsp_plan_unsure',
    'tsp_in_service_withdrawal', 'tsp_withdrawal_hardship', 'tsp_withdrawal_age_based',
    'tsp_traditional_contribution', 'tsp_roth_contribution',
    'tsp_general_loan_date', 'tsp_general_loan_balance', 'tsp_general_loan_repayment', 'tsp_general_loan_payoff',
    'tsp_residential_loan_date', 'tsp_residential_loan_balance', 'tsp_residential_loan_repayment', 'tsp_residential_loan_payoff',
    'tsp_g_fund_balance', 'tsp_g_fund_allocation',
    'tsp_f_fund_balance', 'tsp_f_fund_allocation',
    'tsp_c_fund_balance', 'tsp_c_fund_allocation',
    'tsp_s_fund_balance', 'tsp_s_fund_allocation',
    'tsp_i_fund_balance', 'tsp_i_fund_allocation',
    'tsp_l_income_balance', 'tsp_l_income_allocation',
    'tsp_l_2025_balance', 'tsp_l_2025_allocation',
    'tsp_l_2030_balance', 'tsp_l_2030_allocation',
    'tsp_l_2035_balance', 'tsp_l_2035_allocation',
    'tsp_l_2040_balance', 'tsp_l_2040_allocation',
    'tsp_l_2045_balance', 'tsp_l_2045_allocation',
    'tsp_l_2050_balance', 'tsp_l_2050_allocation',
    'tsp_l_2055_balance', 'tsp_l_2055_allocation',
    'tsp_l_2060_balance', 'tsp_l_2060_allocation',
    'tsp_l_2065_balance', 'tsp_l_2065_allocation',
    'tsp_employee_risk_tolerance', 'tsp_spouse_risk_tolerance', 'tsp_risk_tolerance_why',
    'tsp_best_outcome', 'tsp_worst_outcome', 'tsp_comments',
    'additional_notes_final',
    'document_type', 'documents'
]

# Test data field names (what we're submitting in the test)
TEST_DATA_FIELDS = [
    'employee_name', 'employee_dob', 'spouse_name', 'spouse_fed_emp', 'spouse_dob', 'spouse_income',
    'address', 'city', 'state', 'zip', 'children_ages',
    'retirement_system', 'fers_transfer_date',
    'employee_type',
    'retirement_type',
    'leave_scd', 'retirement_scd', 'retirement_timing', 'retirement_age', 'desired_retirement_date',
    'retirement_by_age', 'years_of_service', 'retirement_pay_leave_notes',
    'agency', 'position_title', 'grade_step', 'has_other_agencies', 'other_agencies',
    'annual_base_salary', 'current_annual_salary', 'locality_pay_amount', 'high_three_average',
    'expects_highest_three',
    'annual_leave_balance', 'sick_leave_balance',
    'tsp_current_balance', 'tsp_traditional_balance', 'tsp_roth_balance',
    'tsp_contribution_pct', 'tsp_employee_contribution_pct', 'tsp_agency_match_pct', 'tsp_catchup',
    'tsp_g_fund_allocation', 'tsp_g_fund_balance',
    'tsp_f_fund_allocation', 'tsp_f_fund_balance',
    'tsp_c_fund_allocation', 'tsp_c_fund_balance',
    'tsp_s_fund_allocation', 'tsp_s_fund_balance',
    'tsp_i_fund_allocation', 'tsp_i_fund_balance',
    'tsp_l_income_allocation', 'tsp_l_income_balance',
    'tsp_l_2025_allocation', 'tsp_l_2025_balance',
    'tsp_l_2030_allocation', 'tsp_l_2030_balance',
    'tsp_l_2035_allocation', 'tsp_l_2035_balance',
    'tsp_l_2040_allocation', 'tsp_l_2040_balance',
    'tsp_l_2045_allocation', 'tsp_l_2045_balance',
    'tsp_l_2050_allocation', 'tsp_l_2050_balance',
    'tsp_l_2055_allocation', 'tsp_l_2055_balance',
    'tsp_l_2060_allocation', 'tsp_l_2060_balance',
    'tsp_l_2065_allocation', 'tsp_l_2065_balance',
    'tsp_use_income', 'tsp_retirement_goal', 'tsp_amount_needed', 'tsp_need_asap',
    'tsp_sole_source', 'tsp_sole_source_explain', 'tsp_plan_leave', 'tsp_in_service_withdrawal',
    'tsp_traditional_contribution', 'tsp_roth_contribution',
    'tsp_general_loan_balance', 'tsp_general_loan_date', 'tsp_general_loan_payoff', 'tsp_general_loan_repayment',
    'tsp_residential_loan_balance', 'tsp_residential_loan_date', 'tsp_residential_loan_payoff', 'tsp_residential_loan_repayment',
    'tsp_employee_risk_tolerance', 'tsp_spouse_risk_tolerance', 'tsp_risk_tolerance_why',
    'tsp_best_outcome', 'tsp_worst_outcome', 'tsp_comments',
    'ira_balance', 'other_retirement_balance', 'other_investments',
    'ss_estimated_benefit', 'ss_age_62', 'ss_desired_age', 'ss_benefit_desired', 'ss_benefit_62', 'ss_covered_employment',
    'active_duty', 'active_duty_start', 'active_duty_end', 'active_duty_deposit', 'military_deposit',
    'active_duty_owe_amount', 'lwop_us_start', 'lwop_us_end', 'lwop_deposit',
    'retired_active_duty', 'military_pension_amount', 'scd_overseas_time', 'military_active_duty_notes',
    'reserve', 'reserve_start', 'reserve_end',
    'reserve_credit_years', 'reserve_credit_months', 'reserve_credit_days', 'reserve_deposit', 'reserve_owe_amount',
    'retired_reserves', 'reserve_pension_amount', 'reserve_pension_start_age', 'military_reserves_notes',
    'academy_service', 'academy_start', 'academy_end', 'academy_deposit_made', 'academy_owe_amount',
    'academy_in_leave_scd', 'military_academy_notes',
    'non_deduction_service', 'non_deduction_start', 'non_deduction_end',
    'non_deduction_deposit_made', 'non_deduction_owe_amount', 'non_deduction_notes',
    'break_in_service', 'original_service_start', 'original_service_end',
    'break_service_start', 'break_service_end', 'took_refund', 'redeposit_made', 'break_service_owe_amount',
    'break_in_service_notes',
    'part_time_service', 'part_time_start', 'part_time_end',
    'part_time_hours_per_week', 'part_time_contributed', 'part_time_on_sf50', 'part_time_notes',
    'other_pertinent_details',
    'fegli_premium_1', 'fegli_premium_2', 'fegli_premium_3', 'fegli_premium_4',
    'fegli_five_year_requirement', 'fegli_keep_in_retirement', 'fegli_sole_source', 'fegli_purpose',
    'fegli_children_ages', 'fegli_notes',
    'fehb_health_premium', 'fehb_dental_premium', 'fehb_vision_premium', 'fehb_dental_vision_premium',
    'fehb_health_coverage_self_only', 'fehb_health_5_year_requirement', 'fehb_keep_coverage_in_retirement',
    'fehb_spouse_reliant_on_plan', 'fehb_other_coverage_tricare', 'fehb_notes',
    'fltcip_employee_premium', 'fltcip_spouse_premium', 'fltcip_other_premium',
    'fltcip_daily_benefit', 'fltcip_benefit_period_3yrs', 'fltcip_inflation_acio',
    'fltcip_discuss_options', 'fltcip_notes',
    'court_order_dividing_benefits', 'reduce_spousal_pension', 'spouse_protection_reason',
    'retirement_goals', 'retirement_concerns', 'additional_notes_final',
]

print("=" * 80)
print("FORM FIELD VALIDATION")
print("=" * 80)

form_set = set(FORM_FIELDS)
test_set = set(TEST_DATA_FIELDS)

# Fields in test but not in form
test_only = test_set - form_set
if test_only:
    print(f"\n❌ {len(test_only)} fields in TEST DATA but NOT in FORM:")
    for field in sorted(test_only):
        print(f"   - {field}")
else:
    print(f"\n✅ All test fields exist in form")

# Fields in form but not in test
form_only = form_set - test_set
if form_only:
    print(f"\n⚠️  {len(form_only)} fields in FORM but NOT in TEST DATA (may be optional):")
    for field in sorted(form_only):
        print(f"   - {field}")

# Matching fields
matching = form_set & test_set
print(f"\n✅ {len(matching)} fields match between form and test data")

print(f"\n" + "=" * 80)
print(f"SUMMARY:")
print(f"  Form fields: {len(form_set)}")
print(f"  Test fields: {len(test_set)}")
print(f"  Matching: {len(matching)}")
print(f"  Test-only (PROBLEMS): {len(test_only)}")
print(f"  Form-only (optional): {len(form_only)}")
print("=" * 80)
