"""
PDF Generation Service for Federal Fact Finder Forms
Uses WeasyPrint to convert HTML templates to PDF
NOTE: Requires GTK libraries on Windows (works natively on Linux/production)
"""
import io
import logging
import platform
from django.template.loader import render_to_string
from django.core.files.base import ContentFile
from django.utils import timezone

logger = logging.getLogger(__name__)

# Check if WeasyPrint is available (may fail on Windows without GTK)
WEASYPRINT_AVAILABLE = False
try:
    from weasyprint import HTML, CSS
    from weasyprint.text.fonts import FontConfiguration
    WEASYPRINT_AVAILABLE = True
except OSError as e:
    logger.warning(f"WeasyPrint not fully functional: {e}. PDF generation will be skipped on this system.")
    logger.warning("This is expected on Windows without GTK libraries. PDFs will work on Linux/production server.")


def generate_fact_finder_pdf(case):
    """
    Generate PDF from Federal Fact Finder form data.
    
    Args:
        case: Case instance with fact_finder_data populated
    
    Returns:
        CaseDocument instance with generated PDF, or None if failed/unavailable
    
    Raises:
        Exception: If PDF generation fails (caller should handle)
    """
    from cases.models import CaseDocument
    
    # Check if WeasyPrint is available
    if not WEASYPRINT_AVAILABLE:
        logger.warning(f"PDF generation skipped for case {case.id} - WeasyPrint not available on this system")
        case.fact_finder_pdf_status = 'pending'
        case.save(update_fields=['fact_finder_pdf_status'])
        return None
    
    try:
        logger.info(f"Starting PDF generation for case {case.id}")
        
        # Update status to generating
        case.fact_finder_pdf_status = 'generating'
        case.save(update_fields=['fact_finder_pdf_status'])
        
        # Get FederalFactFinder data (new structured model)
        try:
            fff = case.fact_finder
            # Structure the data to match template expectations
            data = {
                # Direct fields (already fixed in template)
                'employee_name': fff.employee_name,
                'employee_dob': fff.employee_dob,
                'spouse_name': fff.spouse_name,
                'spouse_dob': fff.spouse_dob,
                'address': fff.address,
                'city': fff.city,
                'state': fff.state,
                'zip_code': fff.zip_code,
                'retirement_system': fff.retirement_system,
                'employee_type': fff.employee_type,
                'retirement_type': fff.retirement_type,
                
                # Nested structure for compatibility with template
                'basic_information': {
                    'employee_name': fff.employee_name,
                    'employee_dob': fff.employee_dob,
                    'spouse_name': fff.spouse_name,
                    'spouse_fed_emp': fff.spouse_fed_emp,
                    'spouse_dob': fff.spouse_dob,
                    'address': fff.address,
                    'city': fff.city,
                    'state': fff.state,
                    'zip': fff.zip_code,
                },
                'retirement_system': {
                    'system': fff.retirement_system,
                    'csrs_offset_date': fff.csrs_offset_date,
                    'fers_transfer_date': fff.fers_transfer_date,
                },
                'employee_type': {
                    'type': fff.employee_type,
                    'leo_start_date': fff.leo_start_date,
                    'cbpo_on_date_7_6_2008': fff.cbpo_on_date_7_6_2008,
                    'ff_start_date': fff.firefighter_start_date,
                    'atc_start_date': fff.atc_start_date,
                    'fs_start_date': fff.foreign_service_start_date,
                },
                'retirement_type': {
                    'type': fff.retirement_type,
                    'offer_date': fff.optional_offer_date,
                },
                'retirement_pay_leave': {
                    'leave_scd': fff.leave_scd,
                    'retirement_scd': fff.retirement_scd,
                    'retirement_timing': fff.retirement_timing,
                    'retirement_age': fff.retirement_age,
                    'desired_retirement_date': fff.retirement_date,
                    'spouse_protection_reason': fff.spousal_pension_reduction_reason,
                },
                'pay_information': {
                    'current_salary': fff.current_annual_salary,
                },
                'leave_balances': {
                    'sick_leave_hours': fff.sick_leave_hours,
                    'annual_leave_hours': fff.annual_leave_hours,
                },
                'social_security': {
                    'estimated_benefit': fff.ss_benefit_at_62,
                    'collection_age': fff.ss_desired_start_age,
                },
                'additional_information': {
                    'additional_notes': fff.additional_notes,
                },
            }
        except Exception as e:
            logger.warning(f"FederalFactFinder not found for case {case.id}: {e}")
            # Fallback to old JSON structure
            data = case.fact_finder_data or {}
        
        # Prepare context data for template
        context = {
            'case': case,
            'data': data,  # Nested structure matching template expectations
            'employee_name': f"{case.employee_first_name} {case.employee_last_name}",
            'workshop_code': case.workshop_code,
            'member_name': f"{case.member.first_name} {case.member.last_name}" if case.member else "Unknown",
            'date_submitted': case.created_at,
            # Add FederalFactFinder object directly for notes access
            'fact_finder': fff,
            # Individual section context for notes fields
            'military_active_duty': {
                'has_service': fff.has_active_duty,
                'start_date': fff.active_duty_start_date,
                'end_date': fff.active_duty_end_date,
                'deposit_made': fff.active_duty_deposit_made,
                'amount_owed': fff.active_duty_amount_owed,
                'lwop_dates': f"{fff.active_duty_lwop_start} to {fff.active_duty_lwop_end}" if fff.active_duty_lwop_start else '',
                'lwop_deposit_made': fff.active_duty_lwop_deposit_made,
                'retired': fff.active_duty_retired,
                'pension_amount': fff.active_duty_pension_amount,
                'extra_time': fff.active_duty_overseas_time_amount,
                'notes': fff.active_duty_notes,
            },
            'military_reserves': {
                'has_service': fff.has_reserves,
                'start_date': fff.reserves_start_date,
                'end_date': fff.reserves_end_date,
                'years': fff.reserves_creditable_time_years,
                'months': fff.reserves_creditable_time_months,
                'days': fff.reserves_creditable_time_days,
                'deposit_made': fff.reserves_deposit_made,
                'amount_owed': fff.reserves_amount_owed,
                'lwop_dates': f"{fff.reserves_lwop_start} to {fff.reserves_lwop_end}" if fff.reserves_lwop_start else '',
                'lwop_deposit_made': fff.reserves_lwop_deposit_made,
                'retired': fff.reserves_retired,
                'pension_amount': fff.reserves_pension_amount,
                'pension_start_age': fff.reserves_pension_start_age,
                'notes': fff.reserves_notes,
            },
            'academy': {
                'has_service': fff.has_academy,
                'start_date': fff.academy_start_date,
                'end_date': fff.academy_end_date,
                'deposit_made': fff.academy_deposit_made,
                'owe_type': fff.academy_owe_type,
                'amount_owed': fff.academy_amount_owed,
                'in_leave_scd': fff.academy_in_leave_scd,
                'notes': fff.academy_notes,
            },
            'non_deduction_service': {
                'has_service': fff.has_non_deduction_service,
                'start_date': fff.non_deduction_start_date,
                'end_date': fff.non_deduction_end_date,
                'deposit_made': fff.non_deduction_deposit_made_response,
                'owe_type': fff.non_deduction_owe_type,
                'amount_owed': fff.non_deduction_amount_owed,
                'notes': fff.non_deduction_notes,
            },
            'break_in_service': {
                'has_break': fff.has_break_in_service,
                'original_start': fff.break_original_start_date,
                'original_end': fff.break_original_end_date,
                'break_start': fff.break_service_start_date,
                'break_end': fff.break_service_end_date,
                'took_refund': fff.break_took_refund,
                'redeposit_made': fff.break_redeposit_made,
                'owe_type': fff.break_owe_type,
                'amount_owed': fff.break_amount_owed,
                'notes': fff.break_notes,
            },
            'part_time_service': {
                'has_service': fff.has_part_time_service,
                'start_date': fff.part_time_start_date,
                'end_date': fff.part_time_end_date,
                'hours_per_week': fff.part_time_hours_per_week,
                'contributed': fff.part_time_contributed_to_retirement,
                'notes': fff.part_time_notes,
            },
            'employment_history': {
                'other_agencies': fff.other_pertinent_details,
            },
            'fegli': {
                'premium_1': fff.fegli_premium_line1,
                'premium_2': fff.fegli_premium_line2,
                'premium_3': fff.fegli_premium_line3,
                'premium_4': fff.fegli_premium_line4,
                'five_year_requirement': fff.fegli_coverage_5_year_requirement,
                'keep_in_retirement': fff.fegli_keep_coverage_in_retirement,
                'sole_source': fff.fegli_sole_source_life_insurance,
                'purpose': fff.fegli_purpose,
                'children_ages': fff.fegli_children_ages,
                'notes': fff.fegli_notes,
            },
            'fehb': {
                'health_premium': fff.fehb_health_premium,
                'dental_premium': fff.fehb_dental_premium,
                'vision_premium': fff.fehb_vision_premium,
                'dental_vision_premium': fff.fehb_dental_vision_premium,
                'coverage_self_only': fff.fehb_health_coverage_self_only,
                'coverage_self_one': fff.fehb_health_coverage_self_one,
                'coverage_self_family': fff.fehb_health_coverage_self_family,
                'coverage_none': fff.fehb_health_coverage_none,
                'five_year_requirement': fff.fehb_health_5_year_requirement,
                'keep_in_retirement': fff.fehb_keep_coverage_in_retirement,
                'spouse_reliant': fff.fehb_spouse_reliant_on_plan,
                'other_tricare': fff.fehb_other_coverage_tricare,
                'other_va': fff.fehb_other_coverage_va,
                'other_spouse_plan': fff.fehb_other_coverage_spouse_plan,
                'other_private': fff.fehb_other_coverage_private,
                'notes': fff.fehb_notes,
            },
            'fltcip': {
                'employee_premium': fff.fltcip_employee_premium,
                'spouse_premium': fff.fltcip_spouse_premium,
                'other_premium': fff.fltcip_other_premium,
                'daily_benefit': fff.fltcip_daily_benefit,
                'period_2yrs': fff.fltcip_benefit_period_2yrs,
                'period_3yrs': fff.fltcip_benefit_period_3yrs,
                'period_5yrs': fff.fltcip_benefit_period_5yrs,
                'inflation_acio': fff.fltcip_inflation_acio,
                'inflation_fpo': fff.fltcip_inflation_fpo,
                'discuss_options': fff.fltcip_discuss_options,
                'notes': fff.fltcip_notes,
            },
            # TSP risk tolerance and outcomes
            'tsp': {
                # Goals & Planning
                'use_income': fff.tsp_use_for_income,
                'use_fun_money': fff.tsp_use_for_fun_money,
                'use_legacy': fff.tsp_use_for_legacy,
                'use_other': fff.tsp_use_for_other,
                'retirement_goal': fff.tsp_retirement_goal_amount,
                'amount_needed': fff.tsp_amount_needed,
                'need_asap': fff.tsp_need_asap,
                'need_at_age_checkbox': fff.tsp_need_at_age_checkbox,
                'need_age': fff.tsp_need_at_age,
                'need_unsure': fff.tsp_need_unsure,
                'sole_source': fff.tsp_sole_source_investing,
                'sole_source_explain': fff.tsp_sole_source_explain,
                'plan_leave': fff.tsp_plan_leave_in_tsp,
                'plan_rollover': fff.tsp_plan_rollover_to_ira,
                'plan_unsure': fff.tsp_plan_unsure,
                'in_service_withdrawal': fff.tsp_in_service_withdrawal,
                'withdrawal_hardship': fff.tsp_withdrawal_financial_hardship,
                'withdrawal_age_based': fff.tsp_withdrawal_age_based,
                # Contributions
                'traditional_contribution': fff.tsp_traditional_contributions,
                'roth_contribution': fff.tsp_roth_contributions,
                # Loan information
                'general_loan_date': fff.tsp_general_loan_date,
                'general_loan_balance': fff.tsp_general_loan_balance,
                'general_loan_repayment': fff.tsp_general_loan_repayment,
                'general_loan_payoff': fff.tsp_general_loan_payoff_date,
                'residential_loan_date': fff.tsp_residential_loan_date,
                'residential_loan_balance': fff.tsp_residential_loan_balance,
                'residential_loan_repayment': fff.tsp_residential_loan_repayment,
                'residential_loan_payoff': fff.tsp_residential_loan_payoff_date,
                # Fund balances
                'g_fund_balance': fff.tsp_g_fund_balance,
                'f_fund_balance': fff.tsp_f_fund_balance,
                'c_fund_balance': fff.tsp_c_fund_balance,
                's_fund_balance': fff.tsp_s_fund_balance,
                'i_fund_balance': fff.tsp_i_fund_balance,
                'l_income_balance': fff.tsp_l_income_balance,
                'l_2025_balance': fff.tsp_l_2025_balance,
                'l_2030_balance': fff.tsp_l_2030_balance,
                'l_2035_balance': fff.tsp_l_2035_balance,
                'l_2040_balance': fff.tsp_l_2040_balance,
                'l_2045_balance': fff.tsp_l_2045_balance,
                'l_2050_balance': fff.tsp_l_2050_balance,
                'l_2055_balance': fff.tsp_l_2055_balance,
                'l_2060_balance': fff.tsp_l_2060_balance,
                'l_2065_balance': fff.tsp_l_2065_balance,
                # Fund allocations
                'g_fund_allocation': fff.tsp_g_fund_allocation,
                'f_fund_allocation': fff.tsp_f_fund_allocation,
                'c_fund_allocation': fff.tsp_c_fund_allocation,
                's_fund_allocation': fff.tsp_s_fund_allocation,
                'i_fund_allocation': fff.tsp_i_fund_allocation,
                'l_income_allocation': fff.tsp_l_income_allocation,
                'l_2025_allocation': fff.tsp_l_2025_allocation,
                'l_2030_allocation': fff.tsp_l_2030_allocation,
                'l_2035_allocation': fff.tsp_l_2035_allocation,
                'l_2040_allocation': fff.tsp_l_2040_allocation,
                'l_2045_allocation': fff.tsp_l_2045_allocation,
                'l_2050_allocation': fff.tsp_l_2050_allocation,
                'l_2055_allocation': fff.tsp_l_2055_allocation,
                'l_2060_allocation': fff.tsp_l_2060_allocation,
                'l_2065_allocation': fff.tsp_l_2065_allocation,
                # Risk tolerance and outcomes
                'employee_risk_tolerance': fff.tsp_employee_risk_tolerance,
                'spouse_risk_tolerance': fff.tsp_spouse_risk_tolerance,
                'best_outcome': fff.tsp_best_outcome,
                'worst_outcome': fff.tsp_worst_outcome,
                'comments': fff.tsp_comments,
            },
        }
        
        # Render HTML template
        html_string = render_to_string('cases/fact_finder_pdf_template_v2.html', context)
        
        # Configure fonts for WeasyPrint
        font_config = FontConfiguration()
        
        # Generate PDF in memory
        pdf_file = io.BytesIO()
        html = HTML(string=html_string)
        html.write_pdf(pdf_file, font_config=font_config)
        pdf_file.seek(0)
        
        # Generate filename
        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        filename = f"fact-finder-{case.external_case_id}-{timestamp}.pdf"
        
        # Create CaseDocument record
        document = CaseDocument.objects.create(
            case=case,
            document_type='fact_finder',
            original_filename=filename,
            file_size=pdf_file.getbuffer().nbytes,
            uploaded_by=case.member,
            notes='Auto-generated Federal Fact Finder PDF'
        )
        
        # Save PDF file (django-storages will handle Spaces vs local storage automatically)
        document.file.save(filename, ContentFile(pdf_file.read()), save=True)
        
        # Update case status to completed
        case.fact_finder_pdf_status = 'completed'
        case.fact_finder_pdf_generated_at = timezone.now()
        case.save(update_fields=['fact_finder_pdf_status', 'fact_finder_pdf_generated_at'])
        
        logger.info(f"PDF generated successfully for case {case.id}: {filename}")
        return document
        
    except Exception as e:
        logger.exception(f"PDF generation failed for case {case.id}: {str(e)}")
        
        # Update status to failed
        case.fact_finder_pdf_status = 'failed'
        case.save(update_fields=['fact_finder_pdf_status'])
        
        # Re-raise exception so caller can handle
        raise


def get_fact_finder_pdf(case):
    """
    Get the generated PDF document for a case.
    
    Args:
        case: Case instance
    
    Returns:
        CaseDocument instance or None if no PDF exists
    """
    from cases.models import CaseDocument
    
    return CaseDocument.objects.filter(
        case=case,
        document_type='fact_finder'
    ).order_by('-uploaded_at').first()
