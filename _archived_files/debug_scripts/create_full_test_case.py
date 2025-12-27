#!/usr/bin/env python
"""
Create a fully populated test case for validation testing.
Uses schema to populate EVERY field in the form.
"""

import os
import sys
import django
import json
from datetime import datetime, date, timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from cases.models import Case

User = get_user_model()

print("="*100)
print("FULL FORM TEST CASE GENERATOR")
print("="*100)

# Find Test user
test_user = User.objects.filter(username__icontains='test').first()
if not test_user:
    # Try to find any member user
    test_user = User.objects.filter(user_type='member').first()

if not test_user:
    print("ERROR: No test user found!")
    print("Available users:")
    for user in User.objects.all():
        print(f"  - {user.username} ({user.email}) - {user.user_type}")
    sys.exit(1)

print(f"\n✓ Found Test User: {test_user.username}")
print(f"  Email: {test_user.email}")
print(f"  Workshop Code: {test_user.workshop_code}")

# Create comprehensive test data
form_data = {
    # MEMBER INFO
    'member_name': test_user.username,
    'date_submitted': date.today().strftime('%Y-%m-%d'),
    'workshop_code': test_user.workshop_code,
    'requested_due_date': (date.today() + timedelta(days=14)).strftime('%Y-%m-%d'),
    
    # EMPLOYEE INFO
    'employee_name': 'John Michael Smith',
    'employee_dob': '1965-03-15',
    'spouse_name': 'Mary Ellen Smith',
    'spouse_fed_emp': 'on',
    'spouse_dob': '1967-08-22',
    'address': '123 Main Street Apt 4B',
    'city': 'Arlington',
    'state': 'VA',
    'zip': '22201',
    
    # RETIREMENT SYSTEM
    'retirement_system': 'FERS',
    'retirement_type': 'Regular',
    'employee_type': 'Regular',
    
    # SERVICE DATES
    'leave_scd': '2000-01-15',
    'retirement_scd': '2025-01-15',
    'retirement_fully_eligible': 'on',
    'retirement_mra_10': 'on',
    'desired_retirement_date': '2025-06-30',
    
    # PAY & LEAVE
    'current_annual_salary': '125000',
    'expects_highest_three': 'Yes',
    'sick_leave_balance': '480',
    'annual_leave_balance': '320',
    
    # SOCIAL SECURITY
    'ss_benefit_62': '2400',
    'ss_desired_age': '67',
    'ss_benefit_desired': '3600',
    
    # RETIREMENT/PAY/LEAVE NOTES
    'retirement_pay_leave_notes': 'Employee plans to retire at age 60. Currently has excellent leave balances. Expecting to maximize TSP and Social Security coordination.',
    
    # SPOUSAL PROTECTION
    'reduce_spousal_pension': 'Yes',
    'spouse_protection_reason': 'Spouse dependent on benefits - will reduce pension by maximum survivor annuity',
    'court_order_dividing_benefits': 'No',
    
    # MILITARY SERVICE
    'active_duty_yes': 'on',
    'active_duty_start': '1985-06-01',
    'active_duty_end': '1992-06-01',
    'active_duty_deposit_yes': 'on',
    'retired_active_duty_no': 'on',
    'military_active_duty_notes': 'Honorable discharge from US Army. Full deposit made in 2000.',
    
    # RESERVES/GUARD
    'reserve_yes': 'on',
    'reserve_start': '1992-07-15',
    'reserve_end': '2000-07-15',
    'reserve_credit_years': '8',
    'reserve_credit_months': '0',
    'reserve_credit_days': '0',
    'reserve_deposit_yes': 'on',
    'retired_reserves_no': 'on',
    'reserve_pension_amount': '0',
    'military_reserves_notes': 'Army National Guard service, part-time. Deposit completed.',
    
    # ACADEMY SERVICE
    'academy_no': 'on',
    'military_academy_notes': 'No academy service.',
    
    # NON-DEDUCTION SERVICE
    'non_deduction_no': 'on',
    'non_deduction_notes': 'No non-deduction service periods.',
    
    # BREAK IN SERVICE
    'break_service_no': 'on',
    'break_in_service_notes': 'No breaks in federal service.',
    
    # PART-TIME SERVICE
    'part_time_no': 'on',
    'part_time_notes': 'No part-time service.',
    
    # ADDITIONAL INFO
    'other_pertinent_details': 'Employee is in excellent health. Has children ages 25 and 22 (independent). Wife is also federal employee with separate FERS account. Both planning coordinated retirement strategy.',
    'has_will': 'Yes',
    'has_poa': 'Yes',
    'has_court_orders': 'No',
    'has_special_needs_dependents': 'No',
    
    # FEGLI
    'fegli_premium_1': '150.00',
    'fegli_premium_2': '200.00',
    'fegli_premium_3': '100.00',
    'fegli_premium_4': '0.00',
    'fegli_5yr_yes': 'on',
    'fegli_keep_yes': 'on',
    'fegli_sole_yes': 'on',
    'fegli_purpose': 'Estate settlement and funeral expenses',
    'children_ages': '25, 22',
    'fegli_notes': 'Planning to maintain Basic life insurance into retirement. Options A and B provide good coverage for estate. Will reassess at age 70.',
    
    # FEHB
    'fehb_health_premium': '350.00',
    'fehb_dental_premium': '45.00',
    'fehb_vision_premium': '25.00',
    'fehb_dental_vision_premium': '0.00',
    'fehb_health_self_family': 'on',
    'fehb_health_5yr_yes': 'on',
    'fehb_keep_yes': 'on',
    'fehb_spouse_yes': 'on',
    'other_health_tricare': 'on',
    'other_health_va': 'on',
    'fehb_notes': 'Enrolled in Blue Cross Blue Shield Standard Self+Family. Spouse and employee both eligible. Plan to keep coverage into retirement. Also have VA access through military service. Dental and vision separate.',
    
    # FLTCIP
    'fltcip_employee_premium': '75.00',
    'fltcip_spouse_premium': '75.00',
    'fltcip_family_premium': '0.00',
    'fltcip_daily_benefit': '200.00',
    'fltcip_period_5yrs': 'on',
    'fltcip_inflation_acio': 'on',
    'fltcip_discuss_yes': 'on',
    'fltcip_notes': 'Both employee and spouse enrolled in FLTCIP. 5-year benefit period with annual compound inflation. Have discussed long-term care options with financial advisor.',
    
    # TSP
    'tsp_retirement_goal': 'Maintain current lifestyle - $4,500/month needed',
    'tsp_amount_needed': '1800000',
    'tsp_need_at_age': 'on',
    'tsp_need_age': '60',
    'tsp_sole_yes': 'on',
    'tsp_sole_source_explain': 'TSP + Social Security + FERS pension will be primary retirement income sources',
    'tsp_plan_leave': 'on',
    'tsp_withdrawal_yes': 'on',
    'tsp_traditional_contribution': '15000',
    'tsp_roth_contribution': '5000',
    'tsp_best_outcome': 'Annual 7% returns with early withdrawal at 60',
    'tsp_worst_outcome': '3% annual returns requiring delayed retirement to 65',
    'tsp_employee_risk_tolerance': 'Moderate',
    'tsp_spouse_risk_tolerance': 'Conservative',
    'tsp_risk_tolerance_why': 'Employee comfortable with balanced growth portfolio. Spouse prefers capital preservation as retirement approaches.',
    'tsp_comments': 'Current allocation: 40% C-Fund, 30% S-Fund, 20% I-Fund, 10% F-Fund. No G-Fund currently. L2030 fund used for spouse account.',
    
    # TSP FUND ALLOCATIONS
    'tsp_c_fund_allocation': '40',
    'tsp_c_fund_balance': '450000',
    'tsp_s_fund_allocation': '30',
    'tsp_s_fund_balance': '337500',
    'tsp_i_fund_allocation': '20',
    'tsp_i_fund_balance': '225000',
    'tsp_f_fund_allocation': '10',
    'tsp_f_fund_balance': '112500',
    'tsp_g_fund_allocation': '0',
    'tsp_g_fund_balance': '0',
    
    # TSP LOANS
    'tsp_general_loan_balance': '0',
    'tsp_residential_loan_balance': '0',
    
    # OTHER RETIREMENT ACCOUNTS
    'ira_balance': '150000',
    'other_retirement_balance': '0',
    'other_investments': 'Roth IRA with spouse ($50,000 total), regular brokerage account ($75,000)',
    
    # INSURANCE & BENEFICIARIES
    'has_fegli': 'Yes',
    'fegli_basic': 'on',
    'fegli_option_a': 'on',
    'fegli_option_b': 'on',
    'fehb_plan': 'BCBS Standard',
    'fehb_coverage_type': 'Self+Family',
    'continue_fehb': 'Yes',
    'other_insurance': 'Life insurance through spouse employer ($500,000), disability insurance',
    'tsp_beneficiary': 'Spouse Mary Ellen Smith (100%)',
    'fegli_beneficiary': 'Spouse Mary Ellen Smith (100%)',
    'survivor_benefit_election': 'Maximum survivor annuity (JSRRA)',
    
    # ADDITIONAL NOTES
    'additional_notes': 'COMPREHENSIVE RETIREMENT PLANNING CASE: 59-year-old FERS employee with 25 years of service, eligible for immediate retirement. Excellent financial position with $1.125M in TSP, $150K IRA, $75K other investments. Married with financially independent adult children. Spouse also federal employee. Planning coordinated retirement with focus on benefit optimization and longevity planning. Meeting covers all major retirement topics including pension calculation, TSP strategy, FEHB/FEGLI continuation, FLTCIP evaluation, and overall retirement income projection. Goal is to maintain $4,500/month lifestyle in retirement.',
}

print("\n" + "="*100)
print("SUBMITTING COMPREHENSIVE TEST FORM")
print("="*100)

# Create client and login
client = Client()
client.force_login(test_user)

# Submit the form
response = client.post(
    '/cases/member/submit/',
    data=form_data,
    follow=True
)

print(f"\nForm submission status: {response.status_code}")

# Extract case ID from response
import re
case_match = re.search(r'/cases/(\d+)/', response.request['PATH_INFO'])
if case_match:
    case_id = int(case_match.group(1))
    print(f"Created Case #{case_id}")
else:
    # Try to find most recent case for this user
    case = Case.objects.filter(member=test_user).latest('created_at')
    case_id = case.id
    print(f"Created Case #{case_id} (found via latest)")

# Retrieve case and verify data
case = Case.objects.get(id=case_id)
data = case.fact_finder_data or {}

print("\n" + "="*100)
print("VERIFICATION - DATA IN DATABASE")
print("="*100)

# Check critical fields
critical_fields = [
    ('employee_name', 'employee_name'),
    ('FEGLI notes', 'fegli.notes'),
    ('FEHB notes', 'fehb.notes'),
    ('FLTCIP notes', 'fltcip.notes'),
    ('TSP comments', 'tsp.comments'),
    ('Additional notes', 'add_info.additional_notes'),
    ('FEGLI sole source', 'fegli.sole_source'),
    ('FEHB keep in retirement', 'fehb.keep_in_retirement'),
    ('TSP sole source', 'tsp.sole_source'),
    ('Military notes', 'mad.notes'),
    ('Reserves notes', 'reserves.notes'),
    ('Retirement/pay notes', 'add_info.page1_notes'),
]

for label, path in critical_fields:
    parts = path.split('.')
    value = data
    for part in parts:
        value = value.get(part, 'MISSING') if isinstance(value, dict) else 'MISSING'
    
    if value == 'MISSING':
        print(f"❌ {label}: NOT FOUND")
    elif value == '' or value is None:
        print(f"⚠️  {label}: EMPTY")
    else:
        print(f"✅ {label}: {repr(value)[:60]}...")

# Generate PDF view URL
print("\n" + "="*100)
print("NEXT STEPS")
print("="*100)
print(f"\n1. View Case #{case_id}:")
print(f"   http://127.0.0.1:8000/cases/{case_id}/")
print(f"\n2. Render PDF:")
print(f"   http://127.0.0.1:8000/cases/{case_id}/pdf/")
print(f"\n3. Check if ALL fields populated above appear in the PDF")
print(f"\n4. Run validation script:")
print(f"   python validate_test_case.py {case_id}")
