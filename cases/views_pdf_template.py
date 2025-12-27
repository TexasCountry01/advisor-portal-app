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
    - View/download the blank template
    - Update case details (due date, reports, notes, retirement date)
    - Upload supporting documents
    """
    case = get_object_or_404(Case, id=case_id)
    
    # Check permissions - member can only view their own cases
    if request.user.role == 'member' and case.member != request.user:
        return HttpResponse('Access denied', status=403)
    
    # Handle form submissions
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'save_details':
            # Handle case details form submission
            try:
                if request.POST.get('due_date'):
                    case.date_due = datetime.strptime(request.POST.get('due_date'), '%Y-%m-%d').date()
                else:
                    case.date_due = None
                    
                if request.POST.get('num_reports_requested'):
                    case.num_reports_requested = int(request.POST.get('num_reports_requested'))
                    
                if request.POST.get('retirement_date_preference'):
                    case.retirement_date_preference = datetime.strptime(request.POST.get('retirement_date_preference'), '%Y-%m-%d').date()
                else:
                    case.retirement_date_preference = None
                    
                case.special_notes = request.POST.get('special_notes', '')
                case.save()
                
                messages.success(request, 'Case details saved successfully.')
            except Exception as e:
                messages.error(request, f'Error saving case details: {str(e)}')
            
            return redirect('case_fact_finder', case_id=case.id)
        
        elif action == 'upload_document':
            # Handle document upload
            form = CaseDocumentForm(request.POST, request.FILES)
            if form.is_valid():
                doc = form.save(commit=False)
                doc.case = case
                doc.uploaded_by = request.user
                doc.save()
                messages.success(request, 'Document uploaded successfully.')
                return redirect('case_fact_finder', case_id=case.id)
            else:
                for errors in form.errors.values():
                    for error in errors:
                        messages.error(request, error)
    else:
        form = CaseDocumentForm()
    
    # Get existing documents
    documents = case.documents.all().order_by('-uploaded_at')
    
    # Get saved PDF field data if it exists
    saved_pdf_data = case.fact_finder_data or {}
    
    # Try to create a pre-filled PDF if we have saved data
    template_url = '/static/documents/Federal-Fact-Finder-Template.pdf'
    if saved_pdf_data:
        try:
            from cases.services.pdf_form_handler import fill_pdf_form, get_pdf_form_fields
            pdf_path = os.path.join(os.path.dirname(__file__), TEMPLATE_PDF_PATH)
            
            # Get the list of valid PDF field names
            if os.path.exists(pdf_path):
                valid_pdf_fields = get_pdf_form_fields(pdf_path)
                
                # Filter saved_pdf_data to only include actual PDF fields (not case details)
                # and only fields that exist in the PDF and have values
                case_detail_keys = {'due_date', 'num_reports_requested', 'retirement_date_preference', 'special_notes'}
                filtered_data = {
                    k: v for k, v in saved_pdf_data.items() 
                    if k in valid_pdf_fields and v and k not in case_detail_keys
                }
                
                if filtered_data:
                    filled_pdf = fill_pdf_form(pdf_path, filtered_data)
                    if filled_pdf:
                        # Save the filled PDF temporarily and serve it
                        import uuid
                        temp_filename = f"filled_ff_{case_id}_{uuid.uuid4().hex[:8]}.pdf"
                        temp_path = os.path.join(
                            os.path.dirname(__file__), 
                            'static', 'documents', 'temp',
                            temp_filename
                        )
                        
                        # Create temp directory if it doesn't exist
                        os.makedirs(os.path.dirname(temp_path), exist_ok=True)
                        
                        with open(temp_path, 'wb') as f:
                            f.write(filled_pdf.getvalue())
                        
                        # Use the filled PDF
                        template_url = f'/static/documents/temp/{temp_filename}'
                        logger.info(f"Created pre-filled PDF for case {case_id} with {len(filtered_data)} fields")
        except Exception as e:
            logger.warning(f"Could not create pre-filled PDF for case {case_id}: {str(e)}")
            # Fall back to regular template
            pass
    
    context = {
        'case': case,
        'documents': documents,
        'form': form,
        'template_url': template_url,
        'saved_pdf_data': json.dumps(saved_pdf_data),
    }
    
    return render(request, 'cases/fact_finder_template.html', context)

@login_required
def download_template(request):
    """Download the blank Federal Fact Finder template"""
    pdf_path = os.path.join(os.path.dirname(__file__), TEMPLATE_PDF_PATH)
    
    if not os.path.exists(pdf_path):
        return HttpResponse('Template PDF not found', status=404)
    
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
    """Delete an uploaded document"""
    doc = get_object_or_404(CaseDocument, id=doc_id)
    case = doc.case
    
    # Check permissions - only member or admin can delete
    if request.user.role == 'member' and case.member != request.user:
        return HttpResponse('Access denied', status=403)
    
    doc.delete()
    messages.success(request, 'Document deleted.')
    return redirect('case_fact_finder', case_id=case.id)

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
