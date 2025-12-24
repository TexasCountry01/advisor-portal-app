#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Create a comprehensive test case for Federal Fact Finder PDF testing.
Run with: python create_test_case.py
"""
import os
import sys
import django

# Force UTF-8 encoding for print statements
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from cases.models import Case, FederalFactFinder
from django.contrib.auth import get_user_model
from decimal import Decimal
from datetime import date, datetime

User = get_user_model()

def create_test_case():
    # Get first member user or create one
    try:
        member = User.objects.filter(role='member').first()
        if not member:
            member = User.objects.create_user(
                email='test.advisor@profeds.com',
                first_name='Test',
                last_name='Advisor',
                role='member'
            )
            print(f"[OK] Created test member: {member.email}")
        else:
            print(f"[OK] Using existing member: {member.email}")
    except Exception as e:
        print(f"Error getting member: {e}")
        member = User.objects.first()

    # Delete existing test case if it exists
    try:
        test_case = Case.objects.get(external_case_id='TEST-2025-FFF-001')
        test_case.delete()
        print("[OK] Deleted existing test case")
    except Case.DoesNotExist:
        pass

    # Create a new test case
    case = Case.objects.create(
        external_case_id='TEST-2025-FFF-001',
        workshop_code='WS-2025-001',
        member=member,
        employee_first_name='John',
        employee_last_name='Smith',
        client_email='john.smith@agency.gov',
        status='submitted',
        urgency='normal',
        tier='tier_2',
        date_submitted=datetime.now(),
        num_reports_requested=3,
        notes='Comprehensive test case for Federal Fact Finder PDF generation',
        fact_finder_data={}
    )
    print(f"[OK] Created test case: {case.external_case_id} (ID: {case.id})")

    # Create comprehensive FederalFactFinder data
    fact_finder = FederalFactFinder.objects.create(
        case=case,
        
        # Page 1: Basic Information
        employee_name='John Michael Smith',
        employee_dob=date(1965, 3, 15),
        employee_email_address='john.smith@agency.gov',
        employee_phone_number='202-555-1234',
        
        spouse_name='Mary Elizabeth Smith',
        spouse_dob=date(1967, 7, 22),
        spouse_email='mary.smith@email.com',
        spouse_phone='202-555-5678',
        
        # Retirement System Information
        retirement_system='FERS',
        employee_type='civilian',
        retirement_type='regular',
        employer='Department of Commerce',
        scd_date=date(1995, 6, 1),
        creditable_years=29,
        creditable_months=6,
        
        # Pay & Leave Information
        salary=Decimal('125000.00'),
        high_three=Decimal('122500.00'),
        locality_percentage=Decimal('32.49'),
        
        sick_leave=1840,
        annual_leave=240,
        
        # Social Security
        ss_benefit=Decimal('2500.00'),
        ss_benefit_62=Decimal('2100.00'),
        ss_benefit_67=Decimal('2800.00'),
        ss_benefit_70=Decimal('3200.00'),
        
        # Page 2: Military Service - Active Duty
        active_duty=True,
        active_start=date(1985, 9, 1),
        active_end=date(1989, 8, 31),
        active_years=4,
        active_months=0,
        active_deposit_paid=True,
        active_deposit_amount=Decimal('3500.00'),
        
        # Military Service - Reserves
        reserves=True,
        reserves_start=date(1989, 9, 1),
        reserves_end=date(1995, 5, 31),
        reserves_years=5,
        reserves_months=9,
        reserves_deposit_paid=False,
        
        # Military Service - Service Academy
        academy=True,
        academy_branch='US Naval Academy',
        academy_start=date(1981, 7, 1),
        academy_end=date(1985, 5, 31),
        academy_years=4,
        academy_deposit_paid=True,
        academy_deposit_amount=Decimal('2800.00'),
        
        # Page 3: Special Federal Service
        non_deduction=True,
        non_deduction_start=date(1990, 1, 1),
        non_deduction_end=date(1991, 12, 31),
        non_deduction_years=2,
        non_deduction_months=0,
        non_deduction_owed=Decimal('4200.00'),
        non_deduction_paid=Decimal('4200.00'),
        
        break_in_service=True,
        break_start=date(1992, 3, 1),
        break_end=date(1993, 2, 28),
        break_years=1,
        break_months=0,
        
        part_time=True,
        part_time_start=date(1993, 3, 1),
        part_time_end=date(1995, 5, 31),
        part_time_years=2,
        part_time_months=3,
        part_time_percent=Decimal('50.00'),
        
        # Page 4: Insurance - FEGLI
        basic_life=True,
        basic_coverage=Decimal('125000.00'),
        basic_premium=Decimal('43.75'),
        
        option_a=True,
        option_a_coverage=Decimal('10000.00'),
        option_a_premium=Decimal('8.50'),
        
        option_b=True,
        option_b_multiple=3,
        option_b_coverage=Decimal('375000.00'),
        option_b_premium=Decimal('142.50'),
        
        option_c=True,
        option_c_multiple=2,
        option_c_coverage=Decimal('20000.00'),
        option_c_premium=Decimal('28.00'),
        
        # FEHB
        health_plan=True,
        health_plan_name='Blue Cross Blue Shield Standard',
        health_plan_code='Self Plus One',
        health_premium_bi_weekly=Decimal('425.82'),
        health_govt_contribution=Decimal('319.37'),
        health_employee_cost=Decimal('106.45'),
        
        # FLTCIP
        ltc=True,
        ltc_benefit_amount=Decimal('150.00'),
        ltc_benefit_period='3 years',
        ltc_premium=Decimal('185.00'),
        
        # Page 5: TSP
        tsp_percent=Decimal('10.00'),
        tsp_amount=Decimal('961.54'),
        catchup=Decimal('7500.00'),
        match=Decimal('480.77'),
        
        traditional=Decimal('425000.00'),
        roth=Decimal('125000.00'),
        
        g_fund=Decimal('10.00'),
        f_fund=Decimal('10.00'),
        c_fund=Decimal('30.00'),
        s_fund=Decimal('25.00'),
        i_fund=Decimal('25.00'),
        
        risk_profile='moderate',
        planned_retirement_age=62,
        monthly_goal=Decimal('5000.00'),
        
        # TSP Loans
        tsp_loan=True,
        loan_balance=Decimal('25000.00'),
        loan_payment=Decimal('450.00'),
        loan_category='General Purpose',
        
        # Page 6: Additional Information
        notes='''Client is planning to retire in 3 years at age 62. 

Goals include:
- Maximize pension calculation with unused sick leave credit
- Review FEGLI options for cost reduction in retirement
- Evaluate TSP withdrawal strategy
- Consider part-time work after retirement
- Ensure spouse survivor benefits are properly configured

Special considerations:
- Has qualifying military service fully credited
- Completed all required deposits for non-deduction service
- May be eligible for special retirement supplement
- Wants to maintain FEHB coverage in retirement'''
    )

    print(f"\n{'='*60}")
    print(f"[SUCCESS] COMPREHENSIVE TEST CASE CREATED")
    print(f"{'='*60}")
    print(f"\nEmployee Information:")
    print(f"  Name: {fact_finder.employee_name}")
    print(f"  DOB: {fact_finder.employee_dob} (Age: {2025 - fact_finder.employee_dob.year})")
    print(f"  Email: {fact_finder.employee_email_address}")
    print(f"  Phone: {fact_finder.employee_phone_number}")
    
    print(f"\nSpouse Information:")
    print(f"  Name: {fact_finder.spouse_name}")
    print(f"  DOB: {fact_finder.spouse_dob} (Age: {2025 - fact_finder.spouse_dob.year})")
    
    print(f"\nRetirement:")
    print(f"  System: {fact_finder.retirement_system}")
    print(f"  Type: {fact_finder.employee_type} - {fact_finder.retirement_type}")
    print(f"  Employer: {fact_finder.employer}")
    print(f"  Service: {fact_finder.creditable_years} years, {fact_finder.creditable_months} months")
    print(f"  SCD: {fact_finder.scd_date}")
    
    print(f"\nCompensation:")
    print(f"  Annual Salary: ${fact_finder.salary:,.2f}")
    print(f"  High-3: ${fact_finder.high_three:,.2f}")
    print(f"  Locality Pay: {fact_finder.locality_percentage}%")
    
    print(f"\nLeave Balances:")
    print(f"  Sick Leave: {fact_finder.sick_leave} hours")
    print(f"  Annual Leave: {fact_finder.annual_leave} hours")
    
    print(f"\nMilitary Service:")
    print(f"  Active Duty: {fact_finder.active_years}y {fact_finder.active_months}m ({fact_finder.active_start} to {fact_finder.active_end})")
    print(f"    Deposit: ${fact_finder.active_deposit_amount} ({'PAID' if fact_finder.active_deposit_paid else 'UNPAID'})")
    print(f"  Reserves: {fact_finder.reserves_years}y {fact_finder.reserves_months}m ({fact_finder.reserves_start} to {fact_finder.reserves_end})")
    print(f"    Deposit: {'NOT PAID' if not fact_finder.reserves_deposit_paid else 'PAID'}")
    print(f"  Academy: {fact_finder.academy_branch}, {fact_finder.academy_years}y")
    print(f"    Deposit: ${fact_finder.academy_deposit_amount} ({'PAID' if fact_finder.academy_deposit_paid else 'UNPAID'})")
    
    print(f"\nSpecial Service:")
    print(f"  Non-Deduction: {fact_finder.non_deduction_years}y {fact_finder.non_deduction_months}m")
    print(f"    Owed: ${fact_finder.non_deduction_owed}, Paid: ${fact_finder.non_deduction_paid}")
    print(f"  Break in Service: {fact_finder.break_years}y {fact_finder.break_months}m")
    print(f"  Part-Time: {fact_finder.part_time_years}y {fact_finder.part_time_months}m at {fact_finder.part_time_percent}%")
    
    print(f"\nFEGLI Coverage:")
    print(f"  Basic: ${fact_finder.basic_coverage:,.2f} (${fact_finder.basic_premium}/biweekly)")
    print(f"  Option A: ${fact_finder.option_a_coverage:,.2f} (${fact_finder.option_a_premium}/biweekly)")
    print(f"  Option B: {fact_finder.option_b_multiple}x = ${fact_finder.option_b_coverage:,.2f} (${fact_finder.option_b_premium}/biweekly)")
    print(f"  Option C: {fact_finder.option_c_multiple}x = ${fact_finder.option_c_coverage:,.2f} (${fact_finder.option_c_premium}/biweekly)")
    
    total_fegli = (fact_finder.basic_premium or 0) + (fact_finder.option_a_premium or 0) + \
                  (fact_finder.option_b_premium or 0) + (fact_finder.option_c_premium or 0)
    print(f"  Total FEGLI Premium: ${total_fegli:.2f}/biweekly")
    
    print(f"\nFEHB:")
    print(f"  Plan: {fact_finder.health_plan_name}")
    print(f"  Type: {fact_finder.health_plan_code}")
    print(f"  Premium: ${fact_finder.health_premium_bi_weekly}/biweekly")
    print(f"  Govt: ${fact_finder.health_govt_contribution}, Employee: ${fact_finder.health_employee_cost}")
    
    print(f"\nFLTCIP:")
    print(f"  Daily Benefit: ${fact_finder.ltc_benefit_amount}")
    print(f"  Period: {fact_finder.ltc_benefit_period}")
    print(f"  Premium: ${fact_finder.ltc_premium}/month")
    
    print(f"\nTSP:")
    total_tsp = (fact_finder.traditional or 0) + (fact_finder.roth or 0)
    print(f"  Total Balance: ${total_tsp:,.2f}")
    print(f"    Traditional: ${fact_finder.traditional:,.2f}")
    print(f"    Roth: ${fact_finder.roth:,.2f}")
    print(f"  Contribution: {fact_finder.tsp_percent}% (${fact_finder.tsp_amount}/biweekly)")
    print(f"  Catch-up: ${fact_finder.catchup:,.2f}/year")
    print(f"  Match: ${fact_finder.match}/biweekly")
    print(f"  Allocation: G:{fact_finder.g_fund}% F:{fact_finder.f_fund}% C:{fact_finder.c_fund}% S:{fact_finder.s_fund}% I:{fact_finder.i_fund}%")
    print(f"  Risk Profile: {fact_finder.risk_profile}")
    print(f"  Planned Retirement: Age {fact_finder.planned_retirement_age}")
    print(f"  Monthly Goal: ${fact_finder.monthly_goal:,.2f}")
    if fact_finder.tsp_loan:
        print(f"  Loan: ${fact_finder.loan_balance:,.2f} ({fact_finder.loan_category}) - ${fact_finder.loan_payment}/payment")
    
    print(f"\nSocial Security:")
    print(f"  Estimated Benefit: ${fact_finder.ss_benefit:,.2f}/month")
    print(f"  At age 62: ${fact_finder.ss_benefit_62:,.2f}")
    print(f"  At age 67: ${fact_finder.ss_benefit_67:,.2f}")
    print(f"  At age 70: ${fact_finder.ss_benefit_70:,.2f}")
    
    print(f"\n{'='*60}")
    print(f"Case ID: {case.id}")
    print(f"External ID: {case.external_case_id}")
    print(f"Status: {case.status}")
    print(f"\n>> View PDF at:")
    print(f"   http://127.0.0.1:8000/cases/{case.id}/fact-finder-pdf/")
    print(f"{'='*60}\n")
    
    return case, fact_finder

if __name__ == '__main__':
    create_test_case()
