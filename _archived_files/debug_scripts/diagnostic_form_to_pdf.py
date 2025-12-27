import os
import django
import json
from collections import defaultdict

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from cases.models import Case

# Get Case #27
case = Case.objects.get(id=27)
data = case.fact_finder_data

print("="*80)
print("WEBFORM TO PDF MAPPING DIAGNOSTIC - CASE #27")
print("="*80)

# Define which fields the form submits for each major section
form_fields = {
    'FEHB (Federal Employees Health Benefits)': [
        'health_premium', 'dental_premium', 'vision_premium', 'dental_vision_premium',
        'coverage_self_only', 'coverage_self_one', 'coverage_self_family', 'coverage_none',
        'five_year_requirement', 'keep_in_retirement', 'spouse_reliant',
        'other_tricare', 'other_va', 'other_spouse_plan', 'other_private',
        'notes'
    ],
    'FLTCIP (Federal Long Term Care)': [
        'employee_premium', 'spouse_premium', 'other_premium',
        'daily_benefit',
        'period_2yrs', 'period_3yrs', 'period_5yrs',
        'inflation_acio', 'inflation_fpo',
        'discuss_options', 'notes'
    ],
    'TSP (Thrift Savings Plan)': [
        # Questions
        'sole_source', 'sole_source_explain',
        'in_service_withdrawal', 'withdrawal_hardship', 'withdrawal_age_based',
        # Allocations
        'g_fund_allocation', 'f_fund_allocation', 'c_fund_allocation',
        's_fund_allocation', 'i_fund_allocation',
        'l_income_allocation', 'l_2025_allocation', 'l_2030_allocation', 'l_2035_allocation',
        'l_2040_allocation', 'l_2045_allocation', 'l_2050_allocation', 'l_2055_allocation',
        'l_2060_allocation', 'l_2065_allocation',
        # Balances
        'g_fund_balance', 'f_fund_balance', 'c_fund_balance', 's_fund_balance', 'i_fund_balance',
        'l_income_balance', 'l_2025_balance', 'l_2030_balance', 'l_2035_balance',
        'l_2040_balance', 'l_2045_balance', 'l_2050_balance', 'l_2055_balance',
        'l_2060_balance', 'l_2065_balance',
        # Loans
        'general_loan_balance', 'general_loan_date', 'general_loan_payoff', 'general_loan_repayment',
        'residential_loan_balance', 'residential_loan_date', 'residential_loan_payoff', 'residential_loan_repayment',
        # New contributions & risk
        'traditional_contribution', 'roth_contribution',
        'employee_risk_tolerance', 'spouse_risk_tolerance', 'risk_tolerance_why',
        # Goals & plans
        'retirement_goal', 'amount_needed', 'best_outcome', 'worst_outcome',
        'plan_leave', 'plan_rollover', 'use_income'
    ],
    'ADDITIONAL NOTES': [
        'additional_notes'
    ],
    'FEGLI': [
        'premium_1', 'premium_2', 'premium_3', 'premium_4',
        'five_year_requirement', 'keep_in_retirement', 'sole_source', 'purpose',
        'children_ages', 'notes'
    ]
}

print("\nCHECKING DATA MAPPING:\n")

missing_by_section = defaultdict(list)
populated_by_section = defaultdict(list)

# Map the actual section names in the JSON to the form field categories
section_mapping = {
    'FEHB (Federal Employees Health Benefits)': 'fehb',
    'FLTCIP (Federal Long Term Care)': 'fltcip',
    'TSP (Thrift Savings Plan)': 'tsp',
    'FEGLI': 'fegli',
}

special_section_mapping = {
    'ADDITIONAL NOTES': 'add_info'
}

for category, field_names in form_fields.items():
    print(f"\n{category}:")
    print("-" * 80)
    
    # Get the section name from JSON
    if category in section_mapping:
        section_name = section_mapping[category]
        section_data = data.get(section_name, {})
    elif category in special_section_mapping:
        section_name = special_section_mapping[category]
        section_data = data.get(section_name, {})
    else:
        section_data = {}
    
    for field in field_names:
        if field in section_data:
            value = section_data[field]
            if value or value == 0 or value == False:  # Include 0 and False as populated
                populated_by_section[category].append(field)
                # Show non-empty values
                if value and value != '' and value != False:
                    print(f"  ✓ {field}: {str(value)[:60]}")
                else:
                    print(f"  ✓ {field}: (empty/false)")
            else:
                missing_by_section[category].append(field)
                print(f"  ✗ {field}: MISSING/EMPTY")
        else:
            missing_by_section[category].append(field)
            print(f"  ✗ {field}: NOT IN DATABASE")

# Summary
print("\n" + "="*80)
print("SUMMARY - FIELDS NOT POPULATED:")
print("="*80)

total_missing = 0
for category in form_fields:
    missing = missing_by_section.get(category, [])
    if missing:
        print(f"\n{category}: {len(missing)} fields missing")
        for field in missing[:5]:  # Show first 5
            print(f"  - {field}")
        if len(missing) > 5:
            print(f"  ... and {len(missing)-5} more")
        total_missing += len(missing)

print(f"\n{'='*80}")
print(f"TOTAL MISSING/EMPTY: {total_missing} fields")
print(f"Total expected fields: {sum(len(fields) for fields in form_fields.values())}")
print(f"Total populated: {sum(len(fields) for fields in populated_by_section.values())}")

# Check PDF template expectations
print("\n" + "="*80)
print("PDF TEMPLATE VARIABLE MISMATCH:")
print("="*80)
print("\nThe PDF template references these variable names:")
print("  - {{ fact_finder.fehb_health_premium }}")
print("  - {{ fact_finder.fehb_dental_premium }}")
print("  - {{ fact_finder.fltcip_employee_premium }}")
print("  etc.")
print("\nBut the JSON data is structured as:")
print("  - fehb.health_premium")
print("  - fehb.dental_premium")
print("  - fltcip.employee_premium")
print("  etc.")
print("\n⚠️  ISSUE: The PDF template expects 'fact_finder' object with flattened field names")
print("           But the database stores nested JSON with section-based structure")
print("\n✓ SOLUTION: Update PDF template to use correct JSON paths")
print("            Example: Change {{ fact_finder.fehb_health_premium }}")
print("                  To: {{ fehb.health_premium }}")
