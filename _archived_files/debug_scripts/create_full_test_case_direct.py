#!/usr/bin/env python
"""
Create a fully populated test case directly in the database.
"""

import os
import django
import json
from datetime import datetime, date, timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from cases.models import Case

User = get_user_model()

print("="*100)
print("FULL FORM TEST CASE GENERATOR (Direct Database)")
print("="*100)

# Find Test user
test_user = User.objects.filter(username__icontains='test').first()
if not test_user:
    test_user = User.objects.filter(user_type='member').first()

if not test_user:
    print("ERROR: No test user found!")
    print("Available users:")
    for user in User.objects.all():
        print(f"  - {user.username} ({user.email})")
    exit(1)

print(f"\n✓ Found Test User: {test_user.username}")
print(f"  Email: {test_user.email}")
print(f"  Workshop Code: {test_user.workshop_code}")

# Comprehensive fact_finder_data - exactly as views.py would create it
fact_finder_data = {
    'employee_name': 'John Michael Smith',
    'employee_dob': '1965-03-15',
    'spouse_name': 'Mary Ellen Smith',
    'spouse_fed_emp': True,
    'spouse_dob': '1967-08-22',
    'address': '123 Main Street Apt 4B',
    'city': 'Arlington',
    'state': 'VA',
    'zip': '22201',
    'retirement_system': 'FERS',
    'retirement_type': 'Regular',
    'employee_type': 'Regular',
    'leave_scd': '2000-01-15',
    'retirement_scd': '2025-01-15',
    'retirement_fully_eligible': True,
    'retirement_mra_10': True,
    'desired_retirement_date': '2025-06-30',
    'current_annual_salary': 125000.0,
    'expects_highest_three': 'Yes',
    'sick_leave_balance': 480,
    'annual_leave_balance': 320,
    'reduce_spousal_pension': 'Yes',
    'spouse_protection_reason': 'Spouse dependent on benefits - will reduce pension by maximum survivor annuity',
    'court_order_dividing_benefits': 'No',
    
    # FEGLI
    'fegli': {
        'premium_1': '150.00',
        'premium_2': '200.00',
        'premium_3': '100.00',
        'premium_4': '0.00',
        'five_year_requirement': 'Yes',
        'keep_in_retirement': 'Yes',
        'sole_source': 'Yes',
        'purpose': 'Estate settlement and funeral expenses',
        'children_ages': '25, 22',
        'notes': 'Planning to maintain Basic life insurance into retirement. Options A and B provide good coverage for estate. Will reassess at age 70.',
    },
    
    # FEHB
    'fehb': {
        'health_premium': '350.00',
        'dental_premium': '45.00',
        'vision_premium': '25.00',
        'dental_vision_premium': '0.00',
        'coverage_self_only': False,
        'coverage_self_one': False,
        'coverage_self_family': True,
        'coverage_none': False,
        'five_year_requirement': 'Yes',
        'keep_in_retirement': 'Yes',
        'spouse_reliant': 'Yes',
        'other_tricare': True,
        'other_va': True,
        'other_spouse_plan': True,
        'other_private': False,
        'notes': 'Enrolled in Blue Cross Blue Shield Standard Self+Family. Spouse and employee both eligible. Plan to keep coverage into retirement. Also have VA access through military service. Dental and vision separate.',
    },
    
    # FLTCIP
    'fltcip': {
        'employee_premium': '75.00',
        'spouse_premium': '75.00',
        'other_premium': '0.00',
        'daily_benefit': '200.00',
        'period_2yrs': False,
        'period_3yrs': False,
        'period_5yrs': True,
        'inflation_acio': True,
        'inflation_fpo': False,
        'discuss_options': 'Yes',
        'notes': 'Both employee and spouse enrolled in FLTCIP. 5-year benefit period with annual compound inflation. Have discussed long-term care options with financial advisor.',
    },
    
    # TSP
    'tsp': {
        'sole_source': 'Yes',
        'sole_source_explain': 'TSP + Social Security + FERS pension will be primary retirement income sources',
        'plan_leave': True,
        'plan_rollover': False,
        'plan_unsure': False,
        'in_service_withdrawal': 'Yes',
        'withdrawal_hardship': False,
        'withdrawal_age_based': False,
        'retirement_goal': 'Maintain current lifestyle - $4,500/month needed',
        'amount_needed': '1800000',
        'need_asap': False,
        'need_at_age': True,
        'need_age': '60',
        'need_unsure': False,
        'traditional_contribution': '15000',
        'roth_contribution': '5000',
        'best_outcome': 'Annual 7% returns with early withdrawal at 60',
        'worst_outcome': '3% annual returns requiring delayed retirement to 65',
        'employee_risk_tolerance': 'Moderate',
        'spouse_risk_tolerance': 'Conservative',
        'risk_tolerance_why': 'Employee comfortable with balanced growth portfolio. Spouse prefers capital preservation as retirement approaches.',
        'comments': 'Current allocation: 40% C-Fund, 30% S-Fund, 20% I-Fund, 10% F-Fund. No G-Fund currently. L2030 fund used for spouse account.',
        # Fund allocations
        'c_fund_allocation': 40.0,
        'c_fund_balance': 450000.0,
        's_fund_allocation': 30.0,
        's_fund_balance': 337500.0,
        'i_fund_allocation': 20.0,
        'i_fund_balance': 225000.0,
        'f_fund_allocation': 10.0,
        'f_fund_balance': 112500.0,
        'g_fund_allocation': 0.0,
        'g_fund_balance': 0.0,
        'l_income_allocation': 0.0,
        'l_income_balance': 0.0,
        'l_2025_allocation': 0.0,
        'l_2025_balance': 0.0,
        'l_2030_allocation': 0.0,
        'l_2030_balance': 0.0,
        'l_2035_allocation': 0.0,
        'l_2035_balance': 0.0,
        'l_2040_allocation': 0.0,
        'l_2040_balance': 0.0,
        'l_2045_allocation': 0.0,
        'l_2045_balance': 0.0,
        'l_2050_allocation': 0.0,
        'l_2050_balance': 0.0,
        'l_2055_allocation': 0.0,
        'l_2055_balance': 0.0,
        'l_2060_allocation': 0.0,
        'l_2060_balance': 0.0,
        'l_2065_allocation': 0.0,
        'l_2065_balance': 0.0,
        # Loans
        'general_loan_balance': 0.0,
        'general_loan_date': '',
        'general_loan_payoff': '',
        'general_loan_repayment': 0.0,
        'residential_loan_balance': 0.0,
        'residential_loan_date': '',
        'residential_loan_payoff': '',
        'residential_loan_repayment': 0.0,
    },
    
    # MILITARY SERVICE
    'mad': {
        'has_service': True,
        'no_military_service': False,
        'no_special_service': False,
        'start_date': '1985-06-01',
        'end_date': '1992-06-01',
        'deposit_made': 'Yes',
        'military_deposit': 'Yes',
        'amount_owed': '',
        'military_owe': 'No',
        'military_owe_amount': '0',
        'military_owe_amount_check': '',
        'military_owe_zero': 'on',
        'lwop_dates': '',
        'lwop_deposit_made': '',
        'retired': False,
        'pension_amount': '0',
        'extra_time': '',
        'notes': 'Honorable discharge from US Army. Full deposit made in 2000.',
    },
    
    # RESERVES/GUARD
    'reserves': {
        'has_service': True,
        'start_date': '1992-07-15',
        'end_date': '2000-07-15',
        'reserve_credit': 'Yes',
        'years': '8',
        'months': '0',
        'days': '0',
        'deposit_made': 'Yes',
        'amount_owed': '',
        'reserve_owe': 'No',
        'reserve_owe_amount_check': '',
        'reserve_owe_zero': 'on',
        'lwop_dates': '',
        'lwop_deposit_made': '',
        'retired': False,
        'pension_amount': '0',
        'pension_start_age': '',
        'notes': 'Army National Guard service, part-time. Deposit completed.',
    },
    
    # ACADEMY
    'academy': {
        'has_service': False,
        'start_date': '',
        'end_date': '',
        'deposit_made': '',
        'owe_type': '',
        'amount_owed': '',
        'in_leave_scd': '',
        'notes': 'No academy service.',
    },
    
    # NON-DEDUCTION
    'non_deduction': {
        'has_service': False,
        'start_date': '',
        'end_date': '',
        'deposit_made': '',
        'owe_type': '',
        'amount_owed': '',
        'notes': 'No non-deduction service periods.',
    },
    
    # BREAK IN SERVICE
    'break_service': {
        'has_break': False,
        'original_start': '',
        'original_end': '',
        'break_start': '',
        'break_end': '',
        'took_refund': '',
        'redeposit_made': '',
        'owe_type': '',
        'new_start_date': '',
        'deposit_made': False,
        'amount_owed': '',
        'notes': 'No breaks in federal service.',
    },
    
    # PART-TIME
    'part_time': {
        'has_service': False,
        'start_date': '',
        'end_date': '',
        'hours_per_week': '',
        'contributed': '',
        'appears_on_sf50': False,
        'notes': 'No part-time service.',
    },
    
    # ADDITIONAL INFO
    'add_info': {
        'has_will': 'Yes',
        'has_poa': 'Yes',
        'has_court_orders': 'No',
        'court_order_details': '',
        'court_order_dividing_benefits': '',
        'reduce_spousal_pension': 'Yes',
        'spouse_protection_reason': 'Spouse dependent on benefits',
        'has_special_needs_dependents': 'No',
        'special_needs_details': '',
        'additional_notes': 'COMPREHENSIVE RETIREMENT PLANNING CASE: 59-year-old FERS employee with 25 years of service, eligible for immediate retirement. Excellent financial position with $1.125M in TSP, $150K IRA, $75K other investments. Married with financially independent adult children. Spouse also federal employee. Planning coordinated retirement with focus on benefit optimization and longevity planning. Meeting covers all major retirement topics including pension calculation, TSP strategy, FEHB/FEGLI continuation, FLTCIP evaluation, and overall retirement income projection.',
        'other_pertinent_details': 'Employee is in excellent health. Has children ages 25 and 22 (independent). Wife is also federal employee with separate FERS account. Both planning coordinated retirement strategy.',
        'page1_notes': 'Employee plans to retire at age 60. Currently has excellent leave balances. Expecting to maximize TSP and Social Security coordination.',
    },
    
    # SOCIAL SECURITY
    'social_security': {
        'estimated_benefit': 0.0,
        'estimated_benefit_age_62': 0.0,
        'estimated_benefit_fra': 0.0,
        'age_62': '',
        'desired_age': '67',
        'benefit_desired': 3600.0,
        'benefit_62': 2400.0,
        'collection_age': 67,
        'covered_employment': 'Yes',
        'non_covered_employment': 'No',
        'spouse_benefit': 0.0,
        'spouse_collection_age': None,
    },
    
    # OTHER ACCOUNTS
    'other_retirement_accounts': {
        'ira_balance': 150000.0,
        'other_retirement_balance': 0.0,
        'other_investments': 'Roth IRA with spouse ($50,000 total), regular brokerage account ($75,000)',
    },
    
    # INSURANCE/BENEFICIARIES
    'insurance_beneficiaries': {
        'has_fegli': 'Yes',
        'fegli_basic': True,
        'fegli_option_a': True,
        'fegli_option_b': True,
        'fegli_option_c': False,
        'fehb_plan': 'BCBS Standard',
        'fehb_coverage_type': 'Self+Family',
        'continue_fehb': 'Yes',
        'other_insurance': 'Life insurance through spouse employer ($500,000), disability insurance',
        'tsp_beneficiary': 'Spouse Mary Ellen Smith (100%)',
        'fegli_beneficiary': 'Spouse Mary Ellen Smith (100%)',
        'survivor_benefit_election': 'Maximum survivor annuity (JSRRA)',
    },
}

# Create case
case = Case(
    member=test_user,
    workshop_code=test_user.workshop_code,
    employee_first_name='John',
    employee_last_name='Smith',
    client_email=test_user.email,
    urgency='normal',
    num_reports_requested=1,
    status='submitted',
    fact_finder_data=fact_finder_data,
    notes='Comprehensive test case with all fields populated',
    api_sync_status='pending',
)
case.save()

print(f"\n✓ Created Case #{case.id}")
print(f"\nFact Finder Data Summary:")
print(f"  Sections populated: {len(fact_finder_data)}")
print(f"  FEGLI notes: {fact_finder_data['fegli']['notes'][:50]}...")
print(f"  FEHB notes: {fact_finder_data['fehb']['notes'][:50]}...")
print(f"  FLTCIP notes: {fact_finder_data['fltcip']['notes'][:50]}...")
print(f"  TSP comments: {fact_finder_data['tsp']['comments'][:50]}...")
print(f"  Military notes: {fact_finder_data['mad']['notes'][:50]}...")
print(f"  Additional notes: {fact_finder_data['add_info']['additional_notes'][:50]}...")

print("\n" + "="*100)
print("CRITICAL FIELD VALUES")
print("="*100)
print(f"✓ FEGLI sole_source: {fact_finder_data['fegli']['sole_source']}")
print(f"✓ FEHB five_year_requirement: {fact_finder_data['fehb']['five_year_requirement']}")
print(f"✓ FEHB keep_in_retirement: {fact_finder_data['fehb']['keep_in_retirement']}")
print(f"✓ FLTCIP discuss_options: {fact_finder_data['fltcip']['discuss_options']}")
print(f"✓ TSP sole_source: {fact_finder_data['tsp']['sole_source']}")
print(f"✓ TSP in_service_withdrawal: {fact_finder_data['tsp']['in_service_withdrawal']}")

print("\n" + "="*100)
print("NEXT STEPS")
print("="*100)
print(f"\n1. View Case #{case.id}:")
print(f"   http://127.0.0.1:8000/cases/{case.id}/")
print(f"\n2. Render PDF:")
print(f"   http://127.0.0.1:8000/cases/{case.id}/pdf/")
print(f"\n3. Verify ALL these fields appear in the PDF:")
print(f"   - Employee name: John Michael Smith")
print(f"   - FEGLI notes with 'reassess at age 70'")
print(f"   - FEHB notes with 'Blue Cross Blue Shield'")
print(f"   - FLTCIP notes with 'Both spouses enrolled'")
print(f"   - TSP comments with 'C-Fund, S-Fund, I-Fund'")
print(f"   - Military notes with 'Honorable discharge'")
print(f"   - All Y/N/Unsure fields for FEGLI, FEHB, FLTCIP")
print(f"\n4. Run validation to check all fields:")
print(f"   python validate_full_case.py {case.id}")
