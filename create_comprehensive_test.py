# -*- coding: utf-8 -*-
import os
import sys
import django

# Force UTF-8 encoding
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from cases.models import Case, FederalFactFinder
from django.contrib.auth import get_user_model
from decimal import Decimal
from datetime import date, datetime

User = get_user_model()

# Get or create member
member = User.objects.filter(role='member').first() or User.objects.first()

# Delete existing test case
try:
    Case.objects.get(external_case_id='TEST-FFF-2025').delete()
    print("[OK] Deleted old test case")
except Case.DoesNotExist:
    pass

# Create case
case = Case.objects.create(
    external_case_id='TEST-FFF-2025',
    workshop_code='WS-2025-TEST',
    member=member,
    employee_first_name='John',
    employee_last_name='Smith',
    client_email='john.smith@agency.gov',
    status='submitted',
    urgency='normal',
    tier='tier_2',
    date_submitted=datetime.now(),
    num_reports_requested=3,
    notes='Comprehensive test for PDF',
    fact_finder_data={}
)
print(f"[OK] Created case ID {case.id}: {case.external_case_id}")

# Create Federal Fact Finder with ALL the correct field names
fff = FederalFactFinder.objects.create(
    case=case,
    
    # Page 1: Basic Info
    employee_name='John Michael Smith',
    employee_dob=date(1965, 3, 15),
    spouse_name='Mary Elizabeth Smith',
    spouse_dob=date(1967, 7, 22),
    address='1234 Main Street',
    city='Washington',
    state='DC',
    zip_code='20001',
    
    # Retirement System
    retirement_system='FERS',
    employee_type='REGULAR',
    retirement_type='REGULAR',
    
    # Service & Pay
    leave_scd=date(1995, 6, 1),
    retirement_scd=date(1995, 6, 1),
    retirement_timing='FULLY_ELIGIBLE_AGE',
    retirement_age=62,
    current_annual_salary=Decimal('125000.00'),
    expects_highest_three_at_end=True,
    sick_leave_hours=Decimal('1840.00'),
    annual_leave_hours=Decimal('240.00'),
    
    # Social Security
    ss_benefit_at_62=Decimal('2100.00'),
    ss_desired_start_age=67,
    ss_benefit_at_desired_age=Decimal('2800.00'),
    
    # Page 2: Military Service
    has_active_duty=True,
    active_duty_start_date=date(1985, 9, 1),
    active_duty_end_date=date(1989, 8, 31),
    active_duty_deposit_made=True,
    
    has_reserves=True,
    reserves_start_date=date(1989, 9, 1),
    reserves_end_date=date(1995, 5, 31),
    reserves_creditable_time_years=5,
    reserves_creditable_time_months=9,
    reserves_deposit_made=False,
    reserves_amount_owed=Decimal('2500.00'),
    
    has_academy=True,
    academy_start_date=date(1981, 7, 1),
    academy_end_date=date(1985, 5, 31),
    academy_deposit_made=True,
    academy_appears_on_sf50=True,
    
    # Page 3: Special Service
    has_non_deduction_service=True,
    non_deduction_start_date=date(1990, 1, 1),
    non_deduction_end_date=date(1991, 12, 31),
    non_deduction_deposit_made=True,
    
    has_break_in_service=True,
    break_original_start_date=date(1990, 1, 1),
    break_original_end_date=date(1992, 12, 31),
    break_period_start_date=date(1992, 3, 1),
    break_period_end_date=date(1993, 2, 28),
    break_took_refund=False,
    break_made_redeposit=True,
    
    has_part_time_service=True,
    part_time_start_date=date(1993, 3, 1),
    part_time_end_date=date(1995, 5, 31),
    part_time_hours_per_week=Decimal('20.00'),
    part_time_contributed_to_retirement=True,
    
    # Page 4: Insurance
    fegli_premium_line1=Decimal('43.75'),
    fegli_premium_line2=Decimal('8.50'),
    fegli_premium_line3=Decimal('142.50'),
    fegli_premium_line4=Decimal('28.00'),
    fegli_five_year_requirement_met=True,
    fegli_keep_in_retirement=True,
    
    fehb_health_premium=Decimal('425.82'),
    fehb_coverage_type='SELF_PLUS_ONE',
    fehb_five_year_requirement_met=True,
    fehb_keep_in_retirement=True,
    fehb_spouse_reliant=True,
    
    fltcip_employee_premium=Decimal('185.00'),
    fltcip_daily_benefit=Decimal('150.00'),
    fltcip_benefit_period='3_YEARS',
    fltcip_inflation_protection='ACIO_3PCT',
    
    # Page 5: TSP
    tsp_use_for_income=True,
    tsp_use_for_legacy=True,
    tsp_retirement_goal_amount=Decimal('750000.00'),
    tsp_sole_source_investing=False,
    tsp_retirement_plan='LEAVE_IN_TSP',
    
    tsp_traditional_contribution=Decimal('500.00'),
    tsp_roth_contribution=Decimal('461.54'),
    
    # TSP Loans
    tsp_general_loan_date=date(2024, 1, 15),
    tsp_general_loan_balance=Decimal('25000.00'),
    tsp_general_loan_repayment=Decimal('450.00'),
    tsp_general_loan_payoff_date=date(2028, 12, 31),
    
    # TSP Balances
    tsp_g_fund_balance=Decimal('50000.00'),
    tsp_f_fund_balance=Decimal('40000.00'),
    tsp_c_fund_balance=Decimal('150000.00'),
    tsp_s_fund_balance=Decimal('100000.00'),
    tsp_i_fund_balance=Decimal('85000.00'),
    tsp_l_2030_balance=Decimal('0.00'),
    
    # TSP Allocations (new money)
    tsp_g_fund_allocation=Decimal('10.00'),
    tsp_f_fund_allocation=Decimal('10.00'),
    tsp_c_fund_allocation=Decimal('30.00'),
    tsp_s_fund_allocation=Decimal('25.00'),
    tsp_i_fund_allocation=Decimal('25.00'),
    
    # Risk Tolerance
    tsp_employee_risk_tolerance=7,
    tsp_spouse_risk_tolerance=5,
    tsp_best_outcome='Comfortable retirement with travel and legacy for children',
    tsp_worst_outcome='Running out of money or being a burden on family',
    
    # Page 6: Additional Notes
    additional_notes='''Client is planning to retire at age 62 with 30+ years of service.

GOALS:
- Maximize pension with sick leave credit
- Review FEGLI coverage (may reduce Option B in retirement)
- Evaluate TSP withdrawal strategy
- Consider Roth conversions
- Maintain FEHB into retirement

SPECIAL CONSIDERATIONS:
- Military service: Active Duty (4y), Reserves (5y 9m), Academy (4y)
- All military deposits completed except Reserves ($2,500 owed)
- Part-time service from 1993-1995 at 50% (fully credited)
- No break in service refund taken - redeposit completed
- FERS employee, fully eligible at age 62
- Spouse is 2 years younger, also planning retirement around same time

TSP STRATEGY:
- Current allocation moderate (70% stocks, 30% bonds/G Fund)
- Outstanding general purpose loan: $25K, paying off by 2028
- Contributing $961.54/pay period ($500 traditional + $461.54 Roth)
- Total balance ~$425K, goal is $750K by retirement

INSURANCE:
- Full FEGLI coverage (Basic + Options A, B 3x, C 2x)
- Blue Cross Blue Shield Self+One coverage
- Long-term care insurance with $150/day benefit, 3-year period
- All insurance meets 5-year requirement for retirement continuation'''
)

print(f"\n{'='*70}")
print(f"  COMPREHENSIVE TEST CASE CREATED SUCCESSFULLY")
print(f"{'='*70}")
print(f"\nEmployee: {fff.employee_name} (DOB: {fff.employee_dob})")
print(f"Spouse: {fff.spouse_name} (DOB: {fff.spouse_dob})")
print(f"Retirement: {fff.retirement_system} - {fff.employee_type}")
print(f"Salary: ${fff.current_annual_salary:,.2f}")
print(f"Leave: Sick {fff.sick_leave_hours}h, Annual {fff.annual_leave_hours}h")
print(f"\nMilitary Service:")
print(f"  - Active Duty: {fff.active_duty_start_date} to {fff.active_duty_end_date}")
print(f"  - Reserves: {fff.reserves_creditable_time_years}y {fff.reserves_creditable_time_months}m")
print(f"  - Academy: {fff.academy_start_date} to {fff.academy_end_date}")
print(f"\nInsurance:")
print(f"  - FEGLI Total: ${fff.total_fegli_premium:.2f}/biweekly")
print(f"  - FEHB: ${fff.fehb_health_premium:.2f} ({fff.fehb_coverage_type})")
print(f"  - FLTCIP: ${fff.fltcip_employee_premium:.2f}/month")
print(f"\nTSP:")
print(f"  - Total Balance: ${fff.total_tsp_balance:,.2f}")
print(f"  - Contributions: ${fff.tsp_traditional_contribution} (Trad) + ${fff.tsp_roth_contribution} (Roth)")
print(f"  - Loan Balance: ${fff.tsp_general_loan_balance:,.2f}")
print(f"  - Risk Tolerance: {fff.tsp_employee_risk_tolerance}/10")
print(f"\n{'='*70}")
print(f"  VIEW PDF AT:")
print(f"  http://127.0.0.1:8000/cases/{case.id}/fact-finder-pdf/")
print(f"{'='*70}\n")
