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
            'military': {'notes': fff.active_duty_notes},
            'reserves': {'notes': fff.reserves_notes},
            'academy': {'notes': fff.academy_notes},
            'non_deduction': {'notes': fff.non_deduction_notes},
            'break_service': {'notes': fff.break_notes},
            'part_time': {'notes': fff.part_time_notes},
            'fegli': {'notes': fff.fegli_notes},
            'fehb': {'notes': fff.fehb_notes},
            'fltcip': {'notes': fff.fltcip_notes},
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
