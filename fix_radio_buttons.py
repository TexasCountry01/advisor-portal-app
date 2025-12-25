"""
Fix all yes/no/unsure checkboxes to be radio buttons
"""
import re

# Read the file
with open('cases/templates/cases/fact_finder_form.html', 'r', encoding='utf-8') as f:
    content = f.read()

# First pass: convert all checkbox yes/no/unsure fields to radio buttons
# by changing type="checkbox" to type="radio" for specific patterns

replacements = [
    # Pattern: type="checkbox" name="X" where X is a yes/no/unsure field
    # These need to have the same name to be mutually exclusive
    (r'type="checkbox" name="max_pension_yes"', 'type="radio" name="max_pension"'),
    (r'type="checkbox" name="max_pension_no"', 'type="radio" name="max_pension"'),
    
    (r'type="checkbox" name="court_order_yes"', 'type="radio" name="court_order"'),
    (r'type="checkbox" name="court_order_no"', 'type="radio" name="court_order"'),
    
    (r'type="checkbox" name="high3_end_yes"', 'type="radio" name="high3_end"'),
    (r'type="checkbox" name="high3_end_no"', 'type="radio" name="high3_end"'),
    
    (r'type="checkbox" name="active_duty_yes"', 'type="radio" name="active_duty"'),
    (r'type="checkbox" name="active_duty_no"', 'type="radio" name="active_duty"'),
    
    (r'type="checkbox" name="military_deposit_yes"', 'type="radio" name="military_deposit"'),
    (r'type="checkbox" name="military_deposit_no"', 'type="radio" name="military_deposit"'),
    (r'type="checkbox" name="military_deposit_unsure"', 'type="radio" name="military_deposit"'),
    
    (r'type="checkbox" name="military_owe_unsure"', 'type="radio" name="military_owe"'),
    
    (r'type="checkbox" name="lwop_deposit_yes"', 'type="radio" name="lwop_deposit"'),
    (r'type="checkbox" name="lwop_deposit_no"', 'type="radio" name="lwop_deposit"'),
    (r'type="checkbox" name="lwop_deposit_unsure"', 'type="radio" name="lwop_deposit"'),
    
    (r'type="checkbox" name="retired_active_duty_yes"', 'type="radio" name="retired_active_duty"'),
    (r'type="checkbox" name="retired_active_duty_no"', 'type="radio" name="retired_active_duty"'),
    
    (r'type="checkbox" name="reserve_yes"', 'type="radio" name="reserve"'),
    (r'type="checkbox" name="reserve_no"', 'type="radio" name="reserve"'),
    
    (r'type="checkbox" name="reserve_credit_unsure"', 'type="radio" name="reserve_credit"'),
    
    (r'type="checkbox" name="reserve_deposit_yes"', 'type="radio" name="reserve_deposit"'),
    (r'type="checkbox" name="reserve_deposit_no"', 'type="radio" name="reserve_deposit"'),
    (r'type="checkbox" name="reserve_deposit_unsure"', 'type="radio" name="reserve_deposit"'),
    
    (r'type="checkbox" name="reserve_owe_unsure"', 'type="radio" name="reserve_owe"'),
    
    (r'type="checkbox" name="reserve_lwop_deposit_yes"', 'type="radio" name="reserve_lwop_deposit"'),
    (r'type="checkbox" name="reserve_lwop_deposit_no"', 'type="radio" name="reserve_lwop_deposit"'),
    (r'type="checkbox" name="reserve_lwop_deposit_unsure"', 'type="radio" name="reserve_lwop_deposit"'),
    
    (r'type="checkbox" name="retired_reserves_yes"', 'type="radio" name="retired_reserves"'),
    (r'type="checkbox" name="retired_reserves_no"', 'type="radio" name="retired_reserves"'),
    
    # Academy Service - already has same name, just change type
    (r'type="checkbox" name="academy_service"', 'type="radio" name="academy_service"'),
    (r'type="checkbox" name="academy_deposit_made"', 'type="radio" name="academy_deposit_made"'),
    (r'type="checkbox" name="academy_owe_type"', 'type="radio" name="academy_owe_type"'),
    (r'type="checkbox" name="academy_in_leave_scd"', 'type="radio" name="academy_in_leave_scd"'),
    
    # Non-Deduction Service
    (r'type="checkbox" name="non_deduction_service"', 'type="radio" name="non_deduction_service"'),
    (r'type="checkbox" name="non_deduction_deposit_made"', 'type="radio" name="non_deduction_deposit_made"'),
    (r'type="checkbox" name="non_deduction_owe_type"', 'type="radio" name="non_deduction_owe_type"'),
    
    # Break in Service
    (r'type="checkbox" name="break_in_service"', 'type="radio" name="break_in_service"'),
    (r'type="checkbox" name="took_refund"', 'type="radio" name="took_refund"'),
    (r'type="checkbox" name="redeposit_made"', 'type="radio" name="redeposit_made"'),
    (r'type="checkbox" name="break_service_owe_type"', 'type="radio" name="break_service_owe_type"'),
    
    # Part-Time Service
    (r'type="checkbox" name="part_time_service"', 'type="radio" name="part_time_service"'),
    (r'type="checkbox" name="part_time_contributed"', 'type="radio" name="part_time_contributed"'),
    
    # FEGLI
    (r'type="checkbox" name="fegli_5_years_coverage"', 'type="radio" name="fegli_5_years_coverage"'),
    (r'type="checkbox" name="fegli_keep_in_retirement"', 'type="radio" name="fegli_keep_in_retirement"'),
    (r'type="checkbox" name="fegli_sole_source"', 'type="radio" name="fegli_sole_source"'),
    
    # FEHB
    (r'type="checkbox" name="fehb_health_5_years"', 'type="radio" name="fehb_health_5_years"'),
    (r'type="checkbox" name="fehb_keep_in_retirement"', 'type="radio" name="fehb_keep_in_retirement"'),
    (r'type="checkbox" name="fehb_spouse_reliant"', 'type="radio" name="fehb_spouse_reliant"'),
    
    # FLTCIP
    (r'type="checkbox" name="fltcip_discuss_options"', 'type="radio" name="fltcip_discuss_options"'),
    
    # TSP
    (r'type="checkbox" name="tsp_sole_source"', 'type="radio" name="tsp_sole_source"'),
    (r'type="checkbox" name="tsp_in_service_withdrawal"', 'type="radio" name="tsp_in_service_withdrawal"'),
]

count = 0
for old, new in replacements:
    new_content = content.replace(old, new)
    if new_content != content:
        count += 1
        content = new_content

print(f'✓ Replaced {count} checkbox fields with radio buttons')

# Write back
with open('cases/templates/cases/fact_finder_form.html', 'w', encoding='utf-8') as f:
    f.write(content)

print('✓ File updated successfully')
