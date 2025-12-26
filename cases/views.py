from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Q
from django.utils import timezone
from django.http import JsonResponse, FileResponse, HttpResponseForbidden
from .models import Case, CaseDocument, CaseReport, CaseNote
from .models_fact_finder import FederalFactFinder
from .forms import CaseDocumentForm, CaseReportForm, CaseNoteForm
from .services import submit_case_to_benefits_software
from accounts.models import User
import logging
from decimal import Decimal, InvalidOperation

logger = logging.getLogger(__name__)


# DEV ONLY - Form preview without authentication
def form_preview(request):
    """Development view to preview form without authentication"""
    context = {
        'workshop_code': 'DEV001',
        'member_name': 'Preview User',
        'today': timezone.now().date(),
    }
    return render(request, 'cases/fact_finder_form.html', context)


@login_required
def member_dashboard(request):
    """Dashboard view for Member role"""
    user = request.user
    
    # Ensure user is a member
    if user.role != 'member':
        messages.error(request, 'Access denied. Members only.')
        return redirect('home')
    
    # Get all cases for this member
    cases = Case.objects.filter(member=user).select_related(
        'assigned_to', 'reviewed_by', 'fact_finder'
    ).order_by('-created_at')
    
    # Apply filters
    status_filter = request.GET.get('status')
    search_query = request.GET.get('search')
    
    if status_filter:
        cases = cases.filter(status=status_filter)
    
    if search_query:
        cases = cases.filter(
            Q(external_case_id__icontains=search_query) |
            Q(employee_first_name__icontains=search_query) |
            Q(employee_last_name__icontains=search_query)
        )
    
    # Calculate statistics
    stats = {
        'total_cases': Case.objects.filter(member=user).count(),
        'submitted': Case.objects.filter(member=user, status='submitted').count(),
        'accepted': Case.objects.filter(member=user, status='accepted').count(),
        'on_hold': Case.objects.filter(member=user, status='hold').count(),
        'completed': Case.objects.filter(member=user, status='completed').count(),
    }
    
    context = {
        'cases': cases,
        'stats': stats,
        'status_filter': status_filter,
        'search_query': search_query,
    }
    
    return render(request, 'cases/member_dashboard.html', context)


@login_required
def case_submit(request):
    """Case submission with Federal Fact Finder form for Members"""
    user = request.user
    
    # Ensure user is a member
    if user.role != 'member':
        messages.error(request, 'Access denied. Members only.')
        return redirect('home')
    
    if request.method == 'POST':
        # Debug: Log what notes fields are received
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"military_active_duty_notes: '{request.POST.get('military_active_duty_notes', '')}'")
        logger.info(f"fegli_notes: '{request.POST.get('fegli_notes', '')}'")
        logger.info(f"fehb_notes: '{request.POST.get('fehb_notes', '')}'")
        
        # Generate unique external_case_id
        import uuid
        external_case_id = f"CASE-{uuid.uuid4().hex[:8].upper()}"
        
        # Build comprehensive Federal Fact Finder data structure
        fact_finder_data = {
            'basic_information': {
                'employee_name': request.POST.get('employee_name', ''),
                'employee_dob': request.POST.get('employee_dob', ''),
                'spouse_name': request.POST.get('spouse_name', ''),
                'spouse_fed_emp': request.POST.get('spouse_fed_emp') == 'on',
                'spouse_dob': request.POST.get('spouse_dob', ''),
                'address': request.POST.get('address', ''),
                'city': request.POST.get('city', ''),
                'state': request.POST.get('state', ''),
                'zip': request.POST.get('zip', ''),
            },
            'retirement_system': {
                'system': request.POST.get('retirement_system', ''),
                'csrs_offset_date': request.POST.get('csrs_offset_date', ''),
                'fers_transfer_date': request.POST.get('fers_transfer_date', ''),
            },
            'employee_type': {
                'type': request.POST.get('employee_type', ''),
                'leo_start_date': request.POST.get('leo_start_date', ''),
                'cbpo_coverage': request.POST.get('cbpo_coverage', ''),
                'ff_start_date': request.POST.get('ff_start_date', ''),
                'atc_start_date': request.POST.get('atc_start_date', ''),
                'fs_start_date': request.POST.get('fs_start_date', ''),
            },
            'retirement_type': {
                'type': request.POST.get('retirement_type', ''),
                'optional_offer_date': request.POST.get('optional_offer_date', ''),
            },
            'retirement_pay_leave': {
                'leave_scd': request.POST.get('leave_scd', ''),
                'retirement_scd': request.POST.get('retirement_scd', ''),
                'retirement_timing': request.POST.get('retirement_timing', ''),
                'retirement_age': request.POST.get('retirement_age', ''),
                'desired_retirement_date': request.POST.get('desired_retirement_date', ''),
            },
            'employment_history': {
                'agency': request.POST.get('agency', ''),
                'position_title': request.POST.get('position_title', ''),
                'grade_step': request.POST.get('grade_step', ''),
                'has_other_agencies': request.POST.get('has_other_agencies') == 'on',
                'other_agencies': request.POST.get('other_agencies', ''),
                'has_non_deduction_service': request.POST.get('has_non_deduction_service') == 'on',
                'non_deduction_service_details': request.POST.get('non_deduction_service_details', ''),
                'reservist_guard': request.POST.get('reservist_guard', ''),
                'military_service': request.POST.get('military_service', ''),
                'military_years': request.POST.get('military_years', ''),
                'military_deposit_paid': request.POST.get('military_deposit_paid') == 'on',
            },
            'pay_information': {
                'annual_base_salary': float(request.POST.get('annual_base_salary', 0) or 0),
                'locality_pay_amount': float(request.POST.get('locality_pay_amount', 0) or 0),
                'other_regular_pay': float(request.POST.get('other_regular_pay', 0) or 0),
                'high_three_average': float(request.POST.get('high_three_average', 0) or 0),
            },
            'leave_balances': {
                'annual_leave_hours': float(request.POST.get('annual_leave_hours', 0) or 0),
                'sick_leave_hours': float(request.POST.get('sick_leave_hours', 0) or 0),
                'other_leave': request.POST.get('other_leave', ''),
            },
            'tsp': {
                'balance': float(request.POST.get('tsp_balance', 0) or 0),
                'contribution_pct': float(request.POST.get('tsp_contribution_pct', 0) or 0),
                'catchup': request.POST.get('tsp_catchup') == 'on',
                'g_fund': float(request.POST.get('tsp_g_fund', 0) or 0),
                'f_fund': float(request.POST.get('tsp_f_fund', 0) or 0),
                'c_fund': float(request.POST.get('tsp_c_fund', 0) or 0),
                's_fund': float(request.POST.get('tsp_s_fund', 0) or 0),
                'i_fund': float(request.POST.get('tsp_i_fund', 0) or 0),
                'l_fund': request.POST.get('tsp_l_fund', ''),
                'loans': request.POST.get('tsp_loans', ''),
                'loan_details': request.POST.get('tsp_loan_details', ''),
            },
            'other_retirement_accounts': {
                'ira_balance': float(request.POST.get('ira_balance', 0) or 0),
                'other_retirement_balance': float(request.POST.get('other_retirement_balance', 0) or 0),
                'other_investments': request.POST.get('other_investments', ''),
            },
            'social_security': {
                'estimated_benefit': float(request.POST.get('ss_estimated_benefit', 0) or 0),
                'collection_age': int(request.POST.get('ss_collection_age', 0) or 0) if request.POST.get('ss_collection_age') else None,
                'non_covered_employment': request.POST.get('non_covered_employment', ''),
                'spouse_benefit': float(request.POST.get('spouse_ss_benefit', 0) or 0),
                'spouse_collection_age': int(request.POST.get('spouse_ss_age', 0) or 0) if request.POST.get('spouse_ss_age') else None,
            },
            'other_pension': {
                'has_other_pension': request.POST.get('has_other_pension') == 'on',
                'details': request.POST.get('other_pension_details', ''),
            },
            'income_expenses': {
                'current_annual_income': float(request.POST.get('current_annual_income', 0) or 0),
                'spouse_annual_income': float(request.POST.get('spouse_annual_income', 0) or 0),
                'other_current_income': request.POST.get('other_current_income', ''),
                'expense_housing': float(request.POST.get('expense_housing', 0) or 0),
                'expense_utilities': float(request.POST.get('expense_utilities', 0) or 0),
                'expense_food': float(request.POST.get('expense_food', 0) or 0),
                'expense_healthcare': float(request.POST.get('expense_healthcare', 0) or 0),
                'expense_transportation': float(request.POST.get('expense_transportation', 0) or 0),
                'expense_entertainment': float(request.POST.get('expense_entertainment', 0) or 0),
                'other_expenses': request.POST.get('other_expenses', ''),
            },
            'insurance_beneficiaries': {
                'has_fegli': request.POST.get('has_fegli', ''),
                'fegli_basic': request.POST.get('fegli_basic') == 'on',
                'fegli_option_a': request.POST.get('fegli_option_a') == 'on',
                'fegli_option_b': request.POST.get('fegli_option_b') == 'on',
                'fegli_option_c': request.POST.get('fegli_option_c') == 'on',
                'fehb_plan': request.POST.get('fehb_plan', ''),
                'fehb_coverage_type': request.POST.get('fehb_coverage_type', ''),
                'continue_fehb': request.POST.get('continue_fehb', ''),
                'other_insurance': request.POST.get('other_insurance', ''),
                'tsp_beneficiary': request.POST.get('tsp_beneficiary', ''),
                'fegli_beneficiary': request.POST.get('fegli_beneficiary', ''),
                'survivor_benefit_election': request.POST.get('survivor_benefit_election', ''),
            },
            'additional_information': {
                'has_will': request.POST.get('has_will', ''),
                'has_poa': request.POST.get('has_poa', ''),
                'has_court_orders': request.POST.get('has_court_orders', ''),
                'court_order_details': request.POST.get('court_order_details', ''),
                'has_special_needs_dependents': request.POST.get('has_special_needs_dependents', ''),
                'special_needs_details': request.POST.get('special_needs_details', ''),
                'retirement_goals': request.POST.get('retirement_goals', ''),
                'retirement_concerns': request.POST.get('retirement_concerns', ''),
                'additional_notes': request.POST.get('additional_notes', ''),
            },
            'military_active_duty': {
                'has_service': request.POST.get('active_duty') == 'on',
                'start_date': request.POST.get('active_duty_start', ''),
                'end_date': request.POST.get('active_duty_end', ''),
                'deposit_made': request.POST.get('active_duty_deposit', ''),
                'amount_owed': request.POST.get('active_duty_owe_amount', ''),
                'lwop_dates': f"{request.POST.get('lwop_us_start', '')} to {request.POST.get('lwop_us_end', '')}" if request.POST.get('lwop_us_start') else '',
                'lwop_deposit_made': request.POST.get('lwop_deposit', ''),
                'retired': request.POST.get('retired_active_duty') == 'on',
                'pension_amount': request.POST.get('military_pension_amount', ''),
                'extra_time': request.POST.get('scd_overseas_time', ''),
                'notes': request.POST.get('military_active_duty_notes', ''),
            },
            'military_reserves': {
                'has_service': request.POST.get('reserve') == 'on',
                'start_date': request.POST.get('reserve_start', ''),
                'end_date': request.POST.get('reserve_end', ''),
                'years': request.POST.get('reserve_credit_years', ''),
                'months': request.POST.get('reserve_credit_months', ''),
                'days': request.POST.get('reserve_credit_days', ''),
                'deposit_made': request.POST.get('reserve_deposit', ''),
                'amount_owed': request.POST.get('reserve_owe_amount', ''),
                'lwop_dates': f"{request.POST.get('reserve_lwop_us_start', '')} to {request.POST.get('reserve_lwop_us_end', '')}" if request.POST.get('reserve_lwop_us_start') else '',
                'lwop_deposit_made': request.POST.get('reserve_lwop_deposit', ''),
                'retired': request.POST.get('retired_reserves') == 'on',
                'pension_amount': request.POST.get('reserve_pension_amount', ''),
                'pension_start_age': request.POST.get('reserve_pension_start_age', ''),
                'notes': request.POST.get('military_reserves_notes', ''),
            },
            'academy': {
                'has_service': request.POST.get('academy_service') == 'on',
                'start_date': request.POST.get('academy_start', ''),
                'end_date': request.POST.get('academy_end', ''),
                'deposit_made': request.POST.get('academy_deposit_made', ''),
                'owe_type': request.POST.get('academy_owe_type', ''),
                'amount_owed': request.POST.get('academy_owe_amount', ''),
                'in_leave_scd': request.POST.get('academy_in_leave_scd', ''),
                'notes': request.POST.get('military_academy_notes', ''),
            },
            'non_deduction_service': {
                'has_service': request.POST.get('non_deduction_service') == 'on',
                'start_date': request.POST.get('non_deduction_start', ''),
                'end_date': request.POST.get('non_deduction_end', ''),
                'deposit_made': request.POST.get('non_deduction_deposit_made', ''),
                'owe_type': request.POST.get('non_deduction_owe_type', ''),
                'amount_owed': request.POST.get('non_deduction_owe_amount', ''),
                'notes': request.POST.get('non_deduction_notes', ''),
            },
            'break_in_service': {
                'has_break': request.POST.get('break_in_service') == 'on',
                'original_start': request.POST.get('original_service_start', ''),
                'original_end': request.POST.get('original_service_end', ''),
                'break_start': request.POST.get('break_service_start', ''),
                'break_end': request.POST.get('break_service_end', ''),
                'took_refund': request.POST.get('took_refund', ''),
                'redeposit_made': request.POST.get('redeposit_made', ''),
                'owe_type': request.POST.get('break_service_owe_type', ''),
                'new_start_date': request.POST.get('break_new_start', ''),
                'deposit_made': request.POST.get('break_deposit_made') == 'on',
                'amount_owed': request.POST.get('break_service_owe_amount', ''),
                'notes': request.POST.get('break_in_service_notes', ''),
            },
            'part_time_service': {
                'has_service': request.POST.get('part_time_service') == 'on',
                'start_date': request.POST.get('part_time_start', ''),
                'end_date': request.POST.get('part_time_end', ''),
                'hours_per_week': request.POST.get('part_time_hours_per_week', ''),
                'contributed': request.POST.get('part_time_contributed', ''),
                'appears_on_sf50': request.POST.get('part_time_on_sf50') == 'on',
                'notes': request.POST.get('part_time_notes', ''),
            },
            'fegli': {
                'premium_1': request.POST.get('fegli_premium_1', ''),
                'premium_2': request.POST.get('fegli_premium_2', ''),
                'premium_3': request.POST.get('fegli_premium_3', ''),
                'premium_4': request.POST.get('fegli_premium_4', ''),
                'five_year_requirement': request.POST.get('fegli_5_years_coverage', ''),
                'keep_in_retirement': request.POST.get('fegli_keep_in_retirement', ''),
                'sole_source': request.POST.get('fegli_sole_source', ''),
                'purpose': request.POST.get('fegli_purpose', ''),
                'children_ages': request.POST.get('children_ages', ''),
                'notes': request.POST.get('fegli_notes', ''),
            },
            'fehb': {
                'health_premium': request.POST.get('fehb_health_premium', ''),
                'dental_premium': request.POST.get('fehb_dental_premium', ''),
                'vision_premium': request.POST.get('fehb_vision_premium', ''),
                'dental_vision_premium': request.POST.get('fehb_dental_vision_premium', ''),
                'coverage_self_only': request.POST.get('fehb_health_self_only') == 'on',
                'coverage_self_one': request.POST.get('fehb_health_self_one') == 'on',
                'coverage_self_family': request.POST.get('fehb_health_self_family') == 'on',
                'coverage_none': request.POST.get('fehb_health_none') == 'on',
                'five_year_requirement': request.POST.get('fehb_health_5_years', ''),
                'keep_in_retirement': request.POST.get('fehb_keep_in_retirement', ''),
                'spouse_reliant': request.POST.get('fehb_spouse_reliant', ''),
                'other_tricare': request.POST.get('other_health_tricare') == 'on',
                'other_va': request.POST.get('other_health_va') == 'on',
                'other_spouse_plan': request.POST.get('other_health_spouse_plan') == 'on',
                'other_private': request.POST.get('other_health_private') == 'on',
                'notes': request.POST.get('fehb_notes', ''),
            },
            'fltcip': {
                'employee_premium': request.POST.get('fltcip_employee_premium', ''),
                'spouse_premium': request.POST.get('fltcip_spouse_premium', ''),
                'other_premium': request.POST.get('fltcip_family_premium', ''),
                'daily_benefit': request.POST.get('fltcip_daily_benefit', ''),
                'period_2yrs': request.POST.get('fltcip_period_2yrs') == 'on',
                'period_3yrs': request.POST.get('fltcip_period_3yrs') == 'on',
                'period_5yrs': request.POST.get('fltcip_period_5yrs') == 'on',
                'inflation_acio': request.POST.get('fltcip_inflation_acio') == 'on',
                'inflation_fpo': request.POST.get('fltcip_inflation_fpo') == 'on',
                'discuss_options': request.POST.get('fltcip_discuss_options', ''),
                'notes': request.POST.get('fltcip_notes', ''),
            },
        }
        
        # Extract employee name for case display
        employee_name = request.POST.get('employee_name', '')
        name_parts = employee_name.split(' ', 1)
        first_name = name_parts[0] if len(name_parts) > 0 else ''
        last_name = name_parts[1] if len(name_parts) > 1 else ''
        
        # Create new case locally first (with temporary ID)
        case = Case(
            member=user,
            workshop_code=user.workshop_code,
            external_case_id=external_case_id,  # Temporary until API returns real ID
            employee_first_name=first_name or 'Unknown',
            employee_last_name=last_name or 'Employee',
            client_email=user.email,  # Use member's email as client email
            urgency=request.POST.get('urgency', 'normal'),
            num_reports_requested=1,
            status='submitted',
            fact_finder_data=fact_finder_data,
            notes=request.POST.get('additional_notes', ''),
            api_sync_status='pending',  # Mark as pending API sync
        )
        
        case.save()
        
        # Create FederalFactFinder record from POST data
        try:
            from datetime import datetime
            
            def parse_date(date_str):
                """Helper to parse date string safely"""
                if not date_str or date_str.strip() == '':
                    return None
                try:
                    return datetime.strptime(date_str, '%Y-%m-%d').date()
                except:
                    return None
            
            def parse_decimal(value_str):
                """Helper to parse decimal safely"""
                if not value_str or value_str.strip() == '':
                    return None
                try:
                    return Decimal(str(value_str).replace(',', ''))
                except (InvalidOperation, ValueError):
                    return None
            
            def parse_int(value_str):
                """Helper to parse integer safely"""
                if not value_str or value_str.strip() == '':
                    return None
                try:
                    return int(value_str)
                except (ValueError, TypeError):
                    return None
            
            def parse_bool(value):
                """Helper to parse boolean from checkbox"""
                if value is None or value == '':
                    return None
                return value == 'on' or value == 'true' or value == True
            
            # Create FederalFactFinder with all form data
            fff = FederalFactFinder.objects.create(
                case=case,
                # Basic Information
                employee_name=request.POST.get('employee_name', ''),
                employee_dob=parse_date(request.POST.get('employee_dob')),
                spouse_name=request.POST.get('spouse_name', ''),
                spouse_fed_emp=parse_bool(request.POST.get('spouse_fed_emp')),
                spouse_dob=parse_date(request.POST.get('spouse_dob')),
                address=request.POST.get('address', ''),
                city=request.POST.get('city', ''),
                state=request.POST.get('state', ''),
                zip_code=request.POST.get('zip', ''),
                
                # Retirement System
                retirement_system=request.POST.get('retirement_system', ''),
                csrs_offset_date=parse_date(request.POST.get('csrs_offset_date')),
                fers_transfer_date=parse_date(request.POST.get('fers_transfer_date')),
                
                # Employee Type
                employee_type=request.POST.get('employee_type', ''),
                leo_start_date=parse_date(request.POST.get('leo_start_date')),
                cbpo_on_date_7_6_2008=parse_bool(request.POST.get('cbpo_coverage')),
                firefighter_start_date=parse_date(request.POST.get('ff_start_date')),
                atc_start_date=parse_date(request.POST.get('atc_start_date')),
                foreign_service_start_date=parse_date(request.POST.get('fs_start_date')),
                
                # Retirement Type
                retirement_type=request.POST.get('retirement_type', ''),
                optional_offer_date=parse_date(request.POST.get('optional_offer_date')),
                
                # Retirement, Pay & Leave
                leave_scd=parse_date(request.POST.get('leave_scd')),
                retirement_scd=parse_date(request.POST.get('retirement_scd')),
                retirement_timing=request.POST.get('retirement_timing', ''),
                retirement_age=parse_int(request.POST.get('retirement_age')),
                retirement_date=parse_date(request.POST.get('desired_retirement_date')),
                reduce_spousal_pension_protection=parse_bool(request.POST.get('reduce_spousal_pension')),
                spousal_pension_reduction_reason=request.POST.get('spouse_protection_reason', ''),
                has_court_order_dividing_benefits=parse_bool(request.POST.get('court_order_dividing_benefits')),
                court_order_details=request.POST.get('court_order_details', ''),
                current_annual_salary=parse_decimal(request.POST.get('current_annual_salary')),
                expects_highest_three_at_end=parse_bool(request.POST.get('expects_highest_three')),
                highest_salary_history=request.POST.get('highest_salary_history', ''),
                sick_leave_hours=parse_decimal(request.POST.get('sick_leave_balance')),
                annual_leave_hours=parse_decimal(request.POST.get('annual_leave_balance')),
                ss_benefit_at_62=parse_decimal(request.POST.get('ss_benefit_62')),
                ss_desired_start_age=parse_int(request.POST.get('ss_desired_age')),
                ss_benefit_at_desired_age=parse_decimal(request.POST.get('ss_benefit_desired')),
                page1_notes=request.POST.get('retirement_pay_leave_notes', ''),
                
                # Military - Active Duty
                has_active_duty=parse_bool(request.POST.get('active_duty')),
                active_duty_start_date=parse_date(request.POST.get('active_duty_start')),
                active_duty_end_date=parse_date(request.POST.get('active_duty_end')),
                active_duty_deposit_made=request.POST.get('military_deposit', ''),
                active_duty_amount_owed=parse_decimal(request.POST.get('military_owe_amount')),
                active_duty_lwop_start=parse_date(request.POST.get('lwop_us_start')),
                active_duty_lwop_end=parse_date(request.POST.get('lwop_us_end')),
                active_duty_lwop_deposit_made=request.POST.get('lwop_deposit', ''),
                active_duty_retired=parse_bool(request.POST.get('retired_active_duty')),
                active_duty_pension_amount=parse_decimal(request.POST.get('military_pension_amount')),
                active_duty_overseas_time_amount=request.POST.get('scd_overseas_time', ''),
                active_duty_notes=request.POST.get('military_active_duty_notes', ''),
                
                # Military - Reserves
                has_reserves=parse_bool(request.POST.get('reserve')),
                reserves_start_date=parse_date(request.POST.get('reserve_start')),
                reserves_end_date=parse_date(request.POST.get('reserve_end')),
                reserves_creditable_time_years=parse_int(request.POST.get('reserve_credit_years')),
                reserves_creditable_time_months=parse_int(request.POST.get('reserve_credit_months')),
                reserves_creditable_time_days=parse_int(request.POST.get('reserve_credit_days')),
                reserves_deposit_made=request.POST.get('reserve_deposit', ''),
                reserves_amount_owed=parse_decimal(request.POST.get('reserve_owe_amount')),
                reserves_lwop_start=parse_date(request.POST.get('reserve_lwop_us_start')),
                reserves_lwop_end=parse_date(request.POST.get('reserve_lwop_us_end')),
                reserves_lwop_deposit_made=request.POST.get('reserve_lwop_deposit', ''),
                reserves_retired=parse_bool(request.POST.get('retired_reserves')),
                reserves_pension_amount=parse_decimal(request.POST.get('reserve_pension_amount')),
                reserves_pension_start_age=parse_int(request.POST.get('reserve_pension_start_age')),
                reserves_notes=request.POST.get('military_reserves_notes', ''),
                
                # Military - Academy
                has_academy=parse_bool(request.POST.get('academy_service')),
                academy_start_date=parse_date(request.POST.get('academy_start')),
                academy_end_date=parse_date(request.POST.get('academy_end')),
                academy_deposit_made=request.POST.get('academy_deposit_made', ''),
                academy_owe_type=request.POST.get('academy_owe_type', ''),
                academy_amount_owed=parse_decimal(request.POST.get('academy_owe_amount')),
                academy_in_leave_scd=request.POST.get('academy_in_leave_scd', ''),
                academy_notes=request.POST.get('military_academy_notes', ''),
                
                # Non-Deduction Service
                has_non_deduction_service=parse_bool(request.POST.get('non_deduction_service')),
                non_deduction_start_date=parse_date(request.POST.get('non_deduction_start')),
                non_deduction_end_date=parse_date(request.POST.get('non_deduction_end')),
                non_deduction_deposit_made_response=request.POST.get('non_deduction_deposit_made', ''),
                non_deduction_owe_type=request.POST.get('non_deduction_owe_type', ''),
                non_deduction_deposit_made=parse_bool(request.POST.get('non_deduction_deposit_made')),
                non_deduction_amount_owed=parse_decimal(request.POST.get('non_deduction_owe_amount')),
                non_deduction_notes=request.POST.get('non_deduction_notes', ''),
                
                # Break-in-Service
                has_break_in_service=parse_bool(request.POST.get('break_in_service')),
                break_original_start_date=parse_date(request.POST.get('original_service_start')),
                break_original_end_date=parse_date(request.POST.get('original_service_end')),
                break_service_start_date=parse_date(request.POST.get('break_service_start')),
                break_service_end_date=parse_date(request.POST.get('break_service_end')),
                break_took_refund=request.POST.get('took_refund', ''),
                break_redeposit_made=request.POST.get('redeposit_made', ''),
                break_owe_type=request.POST.get('break_service_owe_type', ''),
                break_new_start_date=parse_date(request.POST.get('break_new_start')),
                break_deposit_made=parse_bool(request.POST.get('break_deposit_made')),
                break_amount_owed=parse_decimal(request.POST.get('break_service_owe_amount')),
                break_notes=request.POST.get('break_in_service_notes', ''),
                
                # Part-Time Service
                has_part_time_service=parse_bool(request.POST.get('part_time_service')),
                part_time_start_date=parse_date(request.POST.get('part_time_start')),
                part_time_end_date=parse_date(request.POST.get('part_time_end')),
                part_time_hours_per_week=parse_decimal(request.POST.get('part_time_hours_per_week')),
                part_time_contributed_to_retirement=request.POST.get('part_time_contributed', ''),
                part_time_appears_on_sf50=parse_bool(request.POST.get('part_time_on_sf50')),
                part_time_notes=request.POST.get('part_time_notes', ''),
                
                # Other Pertinent Details
                other_pertinent_details=request.POST.get('other_pertinent_details', ''),
                
                # FEGLI
                fegli_premium_line1=parse_decimal(request.POST.get('fegli_premium_1')),
                fegli_premium_line2=parse_decimal(request.POST.get('fegli_premium_2')),
                fegli_premium_line3=parse_decimal(request.POST.get('fegli_premium_3')),
                fegli_premium_line4=parse_decimal(request.POST.get('fegli_premium_4')),
                fegli_coverage_5_year_requirement=request.POST.get('fegli_5_years_coverage', ''),
                fegli_keep_coverage_in_retirement=request.POST.get('fegli_keep_in_retirement', ''),
                fegli_sole_source_life_insurance=request.POST.get('fegli_sole_source', ''),
                fegli_purpose=request.POST.get('fegli_purpose', ''),
                fegli_children_ages=request.POST.get('children_ages', ''),
                fegli_five_year_requirement_met=parse_bool(request.POST.get('fegli_five_year')),
                fegli_keep_in_retirement=parse_bool(request.POST.get('fegli_keep_retirement')),
                fegli_notes=request.POST.get('fegli_notes', ''),
                
                # FEHB
                fehb_health_premium=parse_decimal(request.POST.get('fehb_health_premium')),
                fehb_dental_premium=parse_decimal(request.POST.get('fehb_dental_premium')),
                fehb_vision_premium=parse_decimal(request.POST.get('fehb_vision_premium')),
                fehb_dental_vision_premium=parse_decimal(request.POST.get('fehb_dental_vision_premium')),
                fehb_health_coverage_self_only=parse_bool(request.POST.get('fehb_health_self_only')),
                fehb_health_coverage_self_one=parse_bool(request.POST.get('fehb_health_self_one')),
                fehb_health_coverage_self_family=parse_bool(request.POST.get('fehb_health_self_family')),
                fehb_health_coverage_none=parse_bool(request.POST.get('fehb_health_none')),
                fehb_health_5_year_requirement=request.POST.get('fehb_health_5_years', ''),
                fehb_keep_coverage_in_retirement=request.POST.get('fehb_keep_in_retirement', ''),
                fehb_spouse_reliant_on_plan=request.POST.get('fehb_spouse_reliant', ''),
                fehb_other_coverage_tricare=parse_bool(request.POST.get('other_health_tricare')),
                fehb_other_coverage_va=parse_bool(request.POST.get('other_health_va')),
                fehb_other_coverage_spouse_plan=parse_bool(request.POST.get('other_health_spouse_plan')),
                fehb_other_coverage_private=parse_bool(request.POST.get('other_health_private')),
                fehb_coverage_type=request.POST.get('fehb_coverage_type', ''),
                fehb_five_year_requirement_met=parse_bool(request.POST.get('fehb_five_year')),
                fehb_keep_in_retirement=parse_bool(request.POST.get('fehb_keep_retirement')),
                fehb_notes=request.POST.get('fehb_notes', ''),
                
                # FLTCIP
                fltcip_employee_premium=parse_decimal(request.POST.get('fltcip_employee_premium')),
                fltcip_spouse_premium=parse_decimal(request.POST.get('fltcip_spouse_premium')),
                fltcip_other_premium=parse_decimal(request.POST.get('fltcip_family_premium')),
                fltcip_daily_benefit=parse_decimal(request.POST.get('fltcip_daily_benefit')),
                fltcip_benefit_period_2yrs=parse_bool(request.POST.get('fltcip_period_2yrs')),
                fltcip_benefit_period_3yrs=parse_bool(request.POST.get('fltcip_period_3yrs')),
                fltcip_benefit_period_5yrs=parse_bool(request.POST.get('fltcip_period_5yrs')),
                fltcip_inflation_acio=parse_bool(request.POST.get('fltcip_inflation_acio')),
                fltcip_inflation_fpo=parse_bool(request.POST.get('fltcip_inflation_fpo')),
                fltcip_discuss_options=request.POST.get('fltcip_discuss_options', ''),
                fltcip_benefit_period=request.POST.get('fltcip_benefit_period', ''),
                fltcip_inflation_protection=request.POST.get('fltcip_inflation', ''),
                fltcip_notes=request.POST.get('fltcip_notes', ''),
                
                # TSP Goals & Planning
                tsp_use_for_income=parse_bool(request.POST.get('tsp_use_income')),
                tsp_use_for_fun_money=parse_bool(request.POST.get('tsp_use_fun_money')),
                tsp_use_for_legacy=parse_bool(request.POST.get('tsp_use_legacy')),
                tsp_use_for_other=parse_bool(request.POST.get('tsp_use_other')),
                tsp_retirement_goal_amount=parse_decimal(request.POST.get('tsp_goal_amount')),
                tsp_amount_needed=parse_decimal(request.POST.get('tsp_need_amount')),
                tsp_need_asap=parse_bool(request.POST.get('tsp_need_asap')),
                tsp_need_at_age_checkbox=parse_bool(request.POST.get('tsp_need_at_age')),
                tsp_need_at_age=parse_int(request.POST.get('tsp_need_age')),
                tsp_need_unsure=parse_bool(request.POST.get('tsp_need_unsure')),
                tsp_sole_source_investing=request.POST.get('tsp_sole_source', ''),
                tsp_sole_source_explain=request.POST.get('tsp_sole_explain', ''),
                tsp_plan_leave_in_tsp=parse_bool(request.POST.get('tsp_plan_leave')),
                tsp_plan_rollover_to_ira=parse_bool(request.POST.get('tsp_plan_rollover')),
                tsp_plan_unsure=parse_bool(request.POST.get('tsp_plan_unsure')),
                tsp_in_service_withdrawal=request.POST.get('tsp_in_service_withdrawal', ''),
                tsp_withdrawal_financial_hardship=parse_bool(request.POST.get('tsp_withdrawal_hardship')),
                tsp_withdrawal_age_based=parse_bool(request.POST.get('tsp_withdrawal_age_based')),
                tsp_retirement_plan=request.POST.get('tsp_retirement_plan', ''),
                
                # TSP Contributions
                tsp_traditional_contributions=parse_decimal(request.POST.get('tsp_traditional_contributions')),
                tsp_roth_contributions=parse_decimal(request.POST.get('tsp_roth_contributions')),
                
                # TSP Loans
                tsp_general_loan_date=parse_date(request.POST.get('tsp_loan_general_date')),
                tsp_general_loan_balance=parse_decimal(request.POST.get('tsp_loan_general_balance')),
                tsp_general_loan_repayment=parse_decimal(request.POST.get('tsp_loan_general_repayment')),
                tsp_general_loan_payoff_date=parse_date(request.POST.get('tsp_loan_general_payoff_date')),
                tsp_residential_loan_date=parse_date(request.POST.get('tsp_loan_residential_date')),
                tsp_residential_loan_balance=parse_decimal(request.POST.get('tsp_loan_residential_balance')),
                tsp_residential_loan_repayment=parse_decimal(request.POST.get('tsp_loan_residential_repayment')),
                tsp_residential_loan_payoff_date=parse_date(request.POST.get('tsp_loan_residential_payoff_date')),
                
                # TSP Fund Balances
                tsp_g_fund_balance=parse_decimal(request.POST.get('tsp_g_balance')),
                tsp_f_fund_balance=parse_decimal(request.POST.get('tsp_f_balance')),
                tsp_c_fund_balance=parse_decimal(request.POST.get('tsp_c_balance')),
                tsp_s_fund_balance=parse_decimal(request.POST.get('tsp_s_balance')),
                tsp_i_fund_balance=parse_decimal(request.POST.get('tsp_i_balance')),
                tsp_l_income_balance=parse_decimal(request.POST.get('tsp_l_income_balance')),
                tsp_l_2025_balance=parse_decimal(request.POST.get('tsp_l2025_balance')),
                tsp_l_2030_balance=parse_decimal(request.POST.get('tsp_l2030_balance')),
                tsp_l_2035_balance=parse_decimal(request.POST.get('tsp_l2035_balance')),
                tsp_l_2040_balance=parse_decimal(request.POST.get('tsp_l2040_balance')),
                tsp_l_2045_balance=parse_decimal(request.POST.get('tsp_l2045_balance')),
                tsp_l_2050_balance=parse_decimal(request.POST.get('tsp_l2050_balance')),
                tsp_l_2055_balance=parse_decimal(request.POST.get('tsp_l2055_balance')),
                tsp_l_2060_balance=parse_decimal(request.POST.get('tsp_l2060_balance')),
                tsp_l_2065_balance=parse_decimal(request.POST.get('tsp_l2065_70_balance')),
                
                # TSP Fund Allocations
                tsp_g_fund_allocation=parse_decimal(request.POST.get('tsp_g_allocation')),
                tsp_f_fund_allocation=parse_decimal(request.POST.get('tsp_f_allocation')),
                tsp_c_fund_allocation=parse_decimal(request.POST.get('tsp_c_allocation')),
                tsp_s_fund_allocation=parse_decimal(request.POST.get('tsp_s_allocation')),
                tsp_i_fund_allocation=parse_decimal(request.POST.get('tsp_i_allocation')),
                tsp_l_income_allocation=parse_decimal(request.POST.get('tsp_l_income_allocation')),
                tsp_l_2025_allocation=parse_decimal(request.POST.get('tsp_l2025_allocation')),
                tsp_l_2030_allocation=parse_decimal(request.POST.get('tsp_l2030_allocation')),
                tsp_l_2035_allocation=parse_decimal(request.POST.get('tsp_l2035_allocation')),
                tsp_l_2040_allocation=parse_decimal(request.POST.get('tsp_l2040_allocation')),
                tsp_l_2045_allocation=parse_decimal(request.POST.get('tsp_l2045_allocation')),
                tsp_l_2050_allocation=parse_decimal(request.POST.get('tsp_l2050_allocation')),
                tsp_l_2055_allocation=parse_decimal(request.POST.get('tsp_l2055_allocation')),
                tsp_l_2060_allocation=parse_decimal(request.POST.get('tsp_l2060_allocation')),
                tsp_l_2065_allocation=parse_decimal(request.POST.get('tsp_l2065_70_allocation')),
                
                # TSP Risk & Comments
                tsp_employee_risk_tolerance=parse_int(request.POST.get('risk_tolerance_employee')),
                tsp_spouse_risk_tolerance=parse_int(request.POST.get('risk_tolerance_spouse')),
                tsp_best_outcome=request.POST.get('tsp_best_result', ''),
                tsp_worst_outcome=request.POST.get('tsp_worst_result', ''),
                # Combine risk tolerance "why" with general TSP comments
                tsp_comments='\n\n'.join(filter(None, [
                    f"Risk Tolerance Why: {request.POST.get('risk_tolerance_why', '')}" if request.POST.get('risk_tolerance_why', '') else '',
                    request.POST.get('tsp_comments', '')
                ])),
                
                # Additional notes - combine both text areas
                additional_notes='\n\n'.join(filter(None, [
                    request.POST.get('additional_notes_final', ''),
                    request.POST.get('additional_notes', '')
                ])),
            )
            logger.info(f"Created FederalFactFinder record for case {case.id}")
        except Exception as e:
            logger.exception(f"Failed to create FederalFactFinder for case {case.id}: {str(e)}")
        
        # Handle document uploads
        if request.FILES.getlist('documents[]'):
            document_types = request.POST.getlist('document_type[]')
            document_files = request.FILES.getlist('documents[]')
            
            for idx, doc_file in enumerate(document_files):
                if idx < len(document_types) and document_types[idx]:
                    CaseDocument.objects.create(
                        case=case,
                        document_type=document_types[idx],
                        file=doc_file,
                        original_filename=doc_file.name,
                        file_size=doc_file.size,
                        uploaded_by=user,
                        notes=f'Uploaded with Federal Fact Finder submission'
                    )
        
        # Submit to benefits-software API (disabled - will be implemented later)
        # success, benefits_case_id, error = submit_case_to_benefits_software(case)
        
        # Generate PDF from submitted form data
        pdf_generated = False
        try:
            from cases.services.pdf_generator import generate_fact_finder_pdf
            pdf_document = generate_fact_finder_pdf(case)
            pdf_generated = True
        except Exception as pdf_error:
            logger.exception(f"PDF generation failed for case {case.id}: {str(pdf_error)}")
        
        # Success message
        if pdf_generated:
            messages.success(
                request,
                f'✓ Case submitted successfully! Case ID: {case.external_case_id}. '
                f'Your Federal Fact Finder PDF has been generated and saved.'
            )
        else:
            messages.success(
                request,
                f'✓ Case submitted successfully! Case ID: {case.external_case_id}. '
                f'PDF will be generated shortly.'
            )
        
        from django.urls import reverse
        return redirect(reverse('member_dashboard') + '?submitted=true')
    
    # GET request - display form
    context = {
        'workshop_code': user.workshop_code,
        'member_name': f"{user.first_name} {user.last_name}",
        'today': timezone.now().date(),
    }
    
    return render(request, 'cases/fact_finder_form.html', context)



@login_required
def technician_workbench(request):
    """Workbench view for Technician role"""
    user = request.user
    
    # Ensure user is a technician
    if user.role != 'technician':
        messages.error(request, 'Access denied. Technicians only.')
        return redirect('home')
    
    # Get assigned cases
    assigned_cases = Case.objects.filter(
        assigned_to=user
    ).select_related('member', 'reviewed_by').order_by('-updated_at')
    
    # Get cases pending review (for Level 2 and Level 3 only)
    review_queue = Case.objects.none()
    if user.user_level in ['level_2', 'level_3']:
        review_queue = Case.objects.filter(
            status='pending_review',
            reviewed_by__isnull=True
        ).select_related('member', 'assigned_to').order_by('updated_at')
    
    # Apply filters
    status_filter = request.GET.get('status')
    search_query = request.GET.get('search')
    
    if status_filter:
        assigned_cases = assigned_cases.filter(status=status_filter)
    
    if search_query:
        assigned_cases = assigned_cases.filter(
            Q(external_case_id__icontains=search_query) |
            Q(employee_first_name__icontains=search_query) |
            Q(employee_last_name__icontains=search_query) |
            Q(workshop_code__icontains=search_query)
        )
    
    # Calculate statistics
    stats = {
        'assigned': assigned_cases.count(),
        'accepted': assigned_cases.filter(status='accepted').count(),
        'on_hold': assigned_cases.filter(status='hold').count(),
        'pending_review': review_queue.count() if user.user_level in ['level_2', 'level_3'] else 0,
        'completed_this_week': assigned_cases.filter(
            status='completed',
            date_completed__gte=timezone.now() - timezone.timedelta(days=7)
        ).count(),
    }
    
    context = {
        'assigned_cases': assigned_cases,
        'review_queue': review_queue,
        'stats': stats,
        'status_filter': status_filter,
        'search_query': search_query,
        'user_level': user.user_level,
    }
    
    return render(request, 'cases/technician_workbench.html', context)


@login_required
def case_list(request):
    """List all cases - Admin and Manager only"""
    user = request.user
    
    # Ensure user is admin or manager
    if user.role not in ['admin', 'manager']:
        messages.error(request, 'Access denied. Administrators and Managers only.')
        return redirect('home')
    
    # Get all cases
    cases = Case.objects.all().select_related(
        'member', 'assigned_to', 'reviewed_by'
    ).order_by('-created_at')
    
    # Apply filters
    status_filter = request.GET.get('status')
    workshop_filter = request.GET.get('workshop')
    technician_filter = request.GET.get('technician')
    search_query = request.GET.get('search')
    
    if status_filter:
        cases = cases.filter(status=status_filter)
    
    if workshop_filter:
        cases = cases.filter(workshop_code=workshop_filter)
    
    if technician_filter:
        cases = cases.filter(assigned_to_id=technician_filter)
    
    if search_query:
        cases = cases.filter(
            Q(external_case_id__icontains=search_query) |
            Q(employee_first_name__icontains=search_query) |
            Q(employee_last_name__icontains=search_query) |
            Q(workshop_code__icontains=search_query)
        )
    
    # Get unique workshop codes and technicians for filter dropdowns
    workshops = Case.objects.values_list('workshop_code', flat=True).distinct().order_by('workshop_code')
    technicians = User.objects.filter(role='technician', is_active=True).order_by('username')
    
    # Calculate statistics
    stats = {
        'total': cases.count(),
        'submitted': cases.filter(status='submitted').count(),
        'accepted': cases.filter(status='accepted').count(),
        'on_hold': cases.filter(status='hold').count(),
        'pending_review': cases.filter(status='pending_review').count(),
        'completed': cases.filter(status='completed').count(),
    }
    
    context = {
        'cases': cases,
        'stats': stats,
        'workshops': workshops,
        'technicians': technicians,
        'status_filter': status_filter,
        'workshop_filter': workshop_filter,
        'technician_filter': technician_filter,
        'search_query': search_query,
    }
    
    return render(request, 'cases/case_list.html', context)


@login_required
def delete_case(request, pk):
    """Delete a case"""
    case = get_object_or_404(Case, pk=pk)
    
    # Redirect back to the appropriate dashboard
    if request.user.role == 'member':
        redirect_url = 'member_dashboard'
    elif request.user.role in ['tech_1', 'tech_2', 'tech_3']:
        redirect_url = 'technician_workbench'
    else:
        redirect_url = 'case_list'
    
    if request.method == 'POST':
        case.delete()
        messages.success(request, f'Case {case.external_case_id} has been deleted successfully.')
        return redirect(redirect_url)
    
    return redirect(redirect_url)


@login_required
def case_detail(request, pk):
    """Case detail view with documents, reports, and notes"""
    user = request.user
    case = get_object_or_404(Case, pk=pk)
    
    # Permission check
    can_view = False
    can_edit = False
    
    if user.role == 'member' and case.member == user:
        can_view = True  # Members can view their own cases
    elif user.role == 'technician' and case.assigned_to == user:
        can_view = True
        can_edit = True  # Assigned technician can edit
    elif user.role in ['admin', 'manager']:
        can_view = True
        can_edit = True  # Admins and managers can view/edit all
    
    if not can_view:
        messages.error(request, 'You do not have permission to view this case.')
        return redirect('home')
    
    # Get related objects
    documents = CaseDocument.objects.filter(case=case).order_by('-uploaded_at')
    reports = CaseReport.objects.filter(case=case).order_by('report_number')
    notes = CaseNote.objects.filter(case=case).select_related('author').order_by('-created_at')
    
    context = {
        'case': case,
        'can_edit': can_edit,
        'documents': documents,
        'reports': reports,
        'notes': notes,
    }
    
    return render(request, 'cases/case_detail.html', context)


@login_required
def upload_document(request, case_id):
    """Upload a document to a case"""
    case = get_object_or_404(Case, pk=case_id)
    
    # Permission check - only technicians/admins/managers can upload
    can_edit = False
    if request.user.role == 'technician' and case.assigned_to == request.user:
        can_edit = True
    elif request.user.role in ['admin', 'manager']:
        can_edit = True
    
    if not can_edit:
        messages.error(request, 'You do not have permission to upload documents to this case.')
        return redirect('case_detail', pk=case_id)
    
    if request.method == 'POST':
        form = CaseDocumentForm(request.POST, request.FILES)
        if form.is_valid():
            document = form.save(commit=False)
            document.case = case
            document.uploaded_by = request.user
            # Set file metadata
            uploaded_file = request.FILES['file']
            document.original_filename = uploaded_file.name
            document.file_size = uploaded_file.size
            document.save()
            messages.success(request, f'{document.document_type} uploaded successfully!')
            return redirect('case_detail', pk=case_id)
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    
    return redirect('case_detail', pk=case_id)


@login_required
def upload_report(request, case_id):
    """Upload a report to a case"""
    case = get_object_or_404(Case, pk=case_id)
    
    # Permission check - only technicians/admins/managers can upload
    can_edit = False
    if request.user.role == 'technician' and case.assigned_to == request.user:
        can_edit = True
    elif request.user.role in ['admin', 'manager']:
        can_edit = True
    
    if not can_edit:
        messages.error(request, 'You do not have permission to upload reports to this case.')
        return redirect('case_detail', pk=case_id)
    
    if request.method == 'POST':
        form = CaseReportForm(request.POST, request.FILES)
        if form.is_valid():
            report = form.save(commit=False)
            report.case = case
            report.assigned_to = request.user
            # Set report_number to next available number
            existing_reports = CaseReport.objects.filter(case=case).count()
            report.report_number = existing_reports + 1
            report.save()
            messages.success(request, f'Report #{report.report_number} uploaded successfully!')
            return redirect('case_detail', pk=case_id)
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    
    return redirect('case_detail', pk=case_id)


@login_required
def add_note(request, case_id):
    """Add a note to a case"""
    case = get_object_or_404(Case, pk=case_id)
    
    # Permission check
    can_edit = False
    if request.user.role == 'technician' and case.assigned_to == request.user:
        can_edit = True
    elif request.user.role in ['admin', 'manager']:
        can_edit = True
    
    if not can_edit:
        messages.error(request, 'You do not have permission to add notes to this case.')
        return redirect('case_detail', pk=case_id)
    
    if request.method == 'POST':
        form = CaseNoteForm(request.POST)
        if form.is_valid():
            note = form.save(commit=False)
            note.case = case
            note.author = request.user
            note.save()
            messages.success(request, 'Note added successfully!')
            return redirect('case_detail', pk=case_id)
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    
    return redirect('case_detail', pk=case_id)


@login_required
def view_fact_finder_pdf(request, case_id):
    """View the generated Federal Fact Finder PDF for a case"""
    case = get_object_or_404(Case, pk=case_id)
    
    # Permission check - members can only view their own, technicians/admins can view all
    if request.user.role == 'member' and case.member != request.user:
        return HttpResponseForbidden('You do not have permission to view this PDF.')
    elif request.user.role == 'technician' and case.assigned_to != request.user:
        return HttpResponseForbidden('You do not have permission to view this PDF.')
    # admins and managers can view all
    
    # Check if WeasyPrint is available on this system
    from cases.services.pdf_generator import WEASYPRINT_AVAILABLE
    if not WEASYPRINT_AVAILABLE:
        messages.warning(
            request,
            'PDF generation is not available on this development system (Windows requires GTK libraries). '
            'The form data is saved and PDFs will be generated automatically on the production server. '
            'You can view the raw data in the case details.'
        )
        return redirect('case_detail', pk=case_id)
    
    # Get the PDF document or generate it if it doesn't exist
    from cases.services.pdf_generator import get_fact_finder_pdf, generate_fact_finder_pdf
    pdf_document = get_fact_finder_pdf(case)
    
    if not pdf_document:
        # Try to generate the PDF now
        try:
            pdf_document = generate_fact_finder_pdf(case)
            if not pdf_document:
                messages.error(request, 'PDF generation failed. Please contact support.')
                return redirect('case_detail', pk=case_id)
            messages.success(request, 'PDF generated successfully!')
        except Exception as e:
            logger.exception(f"Failed to generate PDF for case {case_id}")
            messages.error(request, f'PDF generation failed: {str(e)}')
            return redirect('case_detail', pk=case_id)
    
    if not pdf_document.file:
        messages.error(request, 'PDF file not found.')
        return redirect('case_detail', pk=case_id)
    
    # Return the PDF file
    try:
        return FileResponse(
            pdf_document.file.open('rb'),
            content_type='application/pdf',
            filename=pdf_document.original_filename
        )
    except Exception as e:
        logger.exception(f"Error serving PDF for case {case_id}: {str(e)}")
        messages.error(request, 'Error loading PDF file.')
        return redirect('case_detail', pk=case_id)
