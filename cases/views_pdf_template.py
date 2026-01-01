"""
Serve the reference PDF directly with optional data overlay.
Users can download, print, and upload supporting documents.
"""
import os
import json
import uuid
import logging
from datetime import datetime
from django.http import FileResponse, HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.contrib import messages

from cases.models import Case, CaseDocument
from cases.forms import CaseDocumentForm

logger = logging.getLogger(__name__)

TEMPLATE_PDF_PATH = 'cases/static/documents/Federal-Fact-Finder-Template.pdf'

@login_required
@require_http_methods(["GET", "POST"])
def fact_finder_template(request, case_id):
    """
    Display the official Federal Fact Finder template PDF.
    Users can:
    - Upload Federal Fact Finder PDF
    - View the uploaded PDF
    """
    case = get_object_or_404(Case, id=case_id)
    
    # Check permissions - member can only view their own cases
    if request.user.role == 'member' and case.member != request.user:
        return HttpResponse('Access denied', status=403)
    
    # Check if Federal Fact Finder document has been uploaded
    ff_document = CaseDocument.objects.filter(
        case=case, 
        document_type='Federal Fact Finder'
    ).first()
    
    # Handle file uploads
    if request.method == 'POST':
        if 'fact_finder_file' in request.FILES:
            file = request.FILES['fact_finder_file']
            
            # Delete old Federal Fact Finder if it exists
            if ff_document:
                ff_document.file.delete()
                ff_document.delete()
            
            # Create new document
            ff_document = CaseDocument.objects.create(
                case=case,
                document_type='Federal Fact Finder',
                original_filename=file.name,
                file_size=file.size,
                uploaded_by=request.user,
                file=file,
            )
            
            messages.success(request, f'Federal Fact Finder PDF uploaded successfully!')
            return redirect('case_fact_finder', case_id=case.id)
        
        # If no Federal Fact Finder but tried to access view, redirect
        if not ff_document and request.POST.get('action') != 'upload':
            messages.error(request, 'Please upload the Federal Fact Finder form first.')
            if request.user.role == 'member':
                return redirect('member_dashboard')
            else:
                return redirect('case_list')
    
    # If no Federal Fact Finder document exists, show upload form
    if not ff_document:
        context = {
            'case': case,
            'show_upload_form': True,
        }
        return render(request, 'cases/fact_finder_template.html', context)
    
    # Federal Fact Finder exists - use direct media URL for iframe display
    # Use absolute URL to ensure iframe can load it correctly
    request_host = request.get_host()  # Gets hostname:port
    ff_url = f"http://{request_host}{ff_document.file.url}"
    
    context = {
        'case': case,
        'ff_document': ff_document,
        'ff_document_url': ff_url,
        'show_upload_form': False,
    }
    
    return render(request, 'cases/fact_finder_template.html', context)

@login_required
def view_fact_finder_pdf(request, case_id):
    """Serve the uploaded Federal Fact Finder PDF for inline viewing in iframe"""
    case = get_object_or_404(Case, id=case_id)
    
    # Check permissions
    if request.user.role == 'member' and case.member != request.user:
        return HttpResponse('Access denied', status=403)
    
    # Get the Federal Fact Finder document
    ff_document = CaseDocument.objects.filter(
        case=case,
        document_type='Federal Fact Finder'
    ).first()
    
    if not ff_document or not ff_document.file:
        return HttpResponse('Federal Fact Finder not found', status=404)
    
    # Get the file path
    file_path = ff_document.file.path
    
    if not os.path.exists(file_path):
        return HttpResponse('File not found on disk', status=404)
    
    # Open and serve the file with inline disposition
    try:
        file_obj = open(file_path, 'rb')
        file_size = os.path.getsize(file_path)
        
        response = FileResponse(
            file_obj,
            content_type='application/pdf'
        )
        response['Content-Disposition'] = f'inline; filename="{ff_document.original_filename}"'
        response['Content-Length'] = file_size
        response['Cache-Control'] = 'public, max-age=3600'
        
        return response
    except Exception as e:
        logger.error(f"Error serving PDF for case {case_id}: {str(e)}")
        return HttpResponse(f'Error serving PDF: {str(e)}', status=500)

@login_required
def download_template(request):
    """Download the blank Federal Fact Finder template"""
    # Get the correct path to the PDF file
    pdf_path = os.path.join(
        os.path.dirname(__file__),
        'static',
        'documents',
        'Federal-Fact-Finder-Template.pdf'
    )
    
    if not os.path.exists(pdf_path):
        return HttpResponse(f'Template PDF not found at {pdf_path}', status=404)
    
    return FileResponse(
        open(pdf_path, 'rb'),
        as_attachment=True,
        filename='Federal-Fact-Finder-Template.pdf'
    )

@login_required  
def download_document(request, doc_id):
    """Download an uploaded supporting document"""
    doc = get_object_or_404(CaseDocument, id=doc_id)
    case = doc.case
    
    # Check permissions
    if request.user.role == 'member' and case.member != request.user:
        return HttpResponse('Access denied', status=403)
    
    if not doc.file:
        return HttpResponse('File not found', status=404)
    
    return FileResponse(
        doc.file.open('rb'),
        as_attachment=True,
        filename=os.path.basename(doc.file.name)
    )

@login_required
def delete_document(request, doc_id):
    """Delete an uploaded document (only if case is not submitted)"""
    doc = get_object_or_404(CaseDocument, id=doc_id)
    case = doc.case
    
    # Check permissions - only member can delete their own case documents
    if request.user.role == 'member' and case.member != request.user:
        messages.error(request, 'Access denied - this is not your case.')
        return redirect('case_detail', pk=case.id)
    
    # Check case status - cannot delete documents from submitted cases
    if case.status == 'submitted':
        messages.error(request, 'Cannot delete documents from a submitted case.')
        return redirect('case_detail', pk=case.id)
    
    filename = doc.original_filename
    doc.delete()
    messages.success(request, f'Document "{filename}" deleted successfully.')
    return redirect('case_detail', pk=case.id)

@login_required
def submit_case(request, case_id):
    """Submit a case for processing"""
    case = get_object_or_404(Case, id=case_id)
    
    # Check permissions - only member can submit their own cases
    if request.user.role == 'member' and case.member != request.user:
        return HttpResponse('Access denied', status=403)
    
    if request.method == 'POST':
        # Update case status to submitted
        case.status = 'submitted'
        case.save()
        
        messages.success(
            request, 
            f'Case {case.external_case_id} submitted successfully. Benefits team will review shortly.'
        )
        return redirect('case_detail', pk=case_id)
    
    return redirect('case_fact_finder', case_id=case_id)

@login_required
@require_http_methods(["POST"])
def extract_pdf_fields(request, case_id):
    """Extract form field values from a filled PDF file"""
    case = get_object_or_404(Case, id=case_id)
    
    # Check permissions
    if request.user.role == 'member' and case.member != request.user:
        return JsonResponse({'success': False, 'error': 'Access denied'}, status=403)
    
    # Check if file was uploaded
    if 'pdf_file' not in request.FILES:
        return JsonResponse({'success': False, 'error': 'No PDF file provided'})
    
    try:
        pdf_file = request.FILES['pdf_file']
        pdf_bytes = pdf_file.read()
        
        # Extract field values from the filled PDF
        from cases.services.pdf_form_handler import extract_pdf_field_values
        field_values = extract_pdf_field_values(pdf_bytes)
        
        logger.info(f"Extracted {len(field_values)} field values from uploaded PDF for case {case_id}")
        
        return JsonResponse({
            'success': True,
            'field_values': field_values,
            'fields_count': len(field_values)
        })
    
    except Exception as e:
        logger.error(f"Error extracting PDF fields: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

@login_required
def save_case_draft(request, case_id):
    """Save case as draft without submitting"""
    case = get_object_or_404(Case, id=case_id)
    
    # Check permissions
    if request.user.role == 'member' and case.member != request.user:
        return HttpResponse('Access denied', status=403)
    
    if request.method == 'POST':
        import json
        
        # Capture form data from POST request
        form_data = {}
        
        # Extract all form fields (except file uploads and metadata)
        for key, value in request.POST.items():
            if key not in ['csrfmiddlewaretoken', 'action']:
                form_data[key] = value
        
        # Store all form data in fact_finder_data
        # This includes both case details and any PDF field data sent
        case.fact_finder_data = form_data
        
        # Update case status to draft (or keep it as is if already submitted)
        if case.status != 'submitted':
            case.status = 'draft'
        
        case.save()
        
        # Log the save
        logger.info(f"Case {case.external_case_id} (ID: {case_id}) draft saved with {len(form_data)} fields")
        
        # Return JSON response for AJAX requests
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': f'Case {case.external_case_id} saved successfully!',
                'saved_fields': len(form_data)
            })
        
        # For regular form submission, show message and redirect
        messages.success(request, f'Case {case.external_case_id} saved successfully!')
        return redirect('case_fact_finder', case_id=case_id)
    
    return redirect('case_fact_finder', case_id=case_id)
