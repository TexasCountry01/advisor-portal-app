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
        
        # Prepare context data for template
        context = {
            'case': case,
            'data': case.fact_finder_data,
            'employee_name': f"{case.employee_first_name} {case.employee_last_name}",
            'workshop_code': case.workshop_code,
            'member_name': f"{case.member.first_name} {case.member.last_name}" if case.member else "Unknown",
            'date_submitted': case.created_at,
        }
        
        # Render HTML template
        html_string = render_to_string('cases/fact_finder_pdf_template.html', context)
        
        # Configure fonts for WeasyPrint
        font_config = FontConfiguration()
        
        # Generate PDF in memory
        pdf_file = io.BytesIO()
        HTML(string=html_string).write_pdf(
            pdf_file,
            font_config=font_config
        )
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
