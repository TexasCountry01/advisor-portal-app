"""
Serve the reference PDF directly with optional data overlay.
Users can download, print, and upload supporting documents.
"""
import os
from datetime import datetime
from django.http import FileResponse, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.contrib import messages

from cases.models import Case, CaseDocument
from cases.forms import CaseDocumentForm

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
    
    context = {
        'case': case,
        'documents': documents,
        'form': form,
        'template_url': '/static/documents/Federal-Fact-Finder-Template.pdf',
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
def save_case_draft(request, case_id):
    """Save case as draft without submitting"""
    case = get_object_or_404(Case, id=case_id)
    
    # Check permissions
    if request.user.role == 'member' and case.member != request.user:
        return HttpResponse('Access denied', status=403)
    
    if request.method == 'POST':
        # Update case status to draft (or keep it as is if already submitted)
        if case.status != 'submitted':
            case.status = 'draft'
            case.save()
        
        messages.success(request, f'Case {case.external_case_id} saved. You can continue uploading documents.')
        return redirect('case_fact_finder', case_id=case_id)
    
    return redirect('case_fact_finder', case_id=case_id)
