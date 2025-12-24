from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Q
from django.utils import timezone
from django.http import JsonResponse, FileResponse, HttpResponseForbidden
from .models import Case, CaseDocument, CaseReport, CaseNote
from .forms import CaseDocumentForm, CaseReportForm, CaseNoteForm
from .services import submit_case_to_benefits_software
from accounts.models import User
import logging

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
        
        # Submit to benefits-software API
        success, benefits_case_id, error = submit_case_to_benefits_software(case)
        
        if success:
            # API call succeeded - case now has real case ID from benefits-software
            messages.success(
                request, 
                f'Case submitted successfully! Case ID: {benefits_case_id}'
            )
        else:
            # API call failed - case saved locally but needs retry
            messages.warning(
                request,
                f'Case saved locally (ID: {case.external_case_id}) but could not sync to benefits system. '
                f'Our team will retry automatically. Error: {error}'
            )
        
        # Generate PDF from submitted form data
        pdf_generated = False
        try:
            from cases.services.pdf_generator import generate_fact_finder_pdf
            pdf_document = generate_fact_finder_pdf(case)
            pdf_generated = True
        except Exception as pdf_error:
            logger.exception(f"PDF generation failed for case {case.id}: {str(pdf_error)}")
        
        # Final success message with all details
        if success and pdf_generated:
            messages.success(
                request,
                f'✓ Case submitted successfully! Case ID: {benefits_case_id}. '
                f'Your Federal Fact Finder PDF has been generated and saved.'
            )
        elif success:
            messages.success(
                request,
                f'✓ Case submitted successfully! Case ID: {benefits_case_id}. '
                f'PDF will be generated shortly.'
            )
        elif pdf_generated:
            messages.warning(
                request,
                f'Case saved locally (ID: {case.external_case_id}) with PDF generated. '
                f'Syncing to benefits system will be retried automatically.'
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
