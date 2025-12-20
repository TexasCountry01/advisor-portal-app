from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Q
from django.utils import timezone
from django.http import JsonResponse
from .models import Case, CaseDocument, CaseReport, CaseNote
from .forms import CaseDocumentForm, CaseReportForm, CaseNoteForm
from accounts.models import User


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
        'assigned_to', 'reviewed_by'
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
        # Generate unique external_case_id (temporary - would be replaced by API integration)
        import uuid
        external_case_id = f"CASE-{uuid.uuid4().hex[:8].upper()}"
        
        # Build Federal Fact Finder data structure
        fact_finder_data = {
            'employee_info': {
                'first_name': request.POST.get('employee_first_name'),
                'last_name': request.POST.get('employee_last_name'),
                'date_of_birth': request.POST.get('date_of_birth'),
                'ssn_last_four': request.POST.get('ssn_last_four', ''),
                'email': request.POST.get('client_email'),
                'phone': request.POST.get('phone'),
            },
            'employment': {
                'agency': request.POST.get('agency'),
                'position_title': request.POST.get('position_title'),
                'retirement_system': request.POST.get('retirement_system'),
                'service_computation_date': request.POST.get('service_computation_date'),
                'years_of_service': float(request.POST.get('years_of_service', 0) or 0),
                'creditable_military_service': float(request.POST.get('creditable_military_service', 0) or 0),
                'leo_coverage': request.POST.get('leo_coverage') == 'on',
                'special_provisions': request.POST.get('special_provisions', ''),
                'grade_step': request.POST.get('grade_step', ''),
                'locality_pay': request.POST.get('locality_pay', ''),
            },
            'salary': {
                'current_annual_salary': float(request.POST.get('current_annual_salary', 0) or 0),
                'high_three_average': float(request.POST.get('high_three_average', 0) or 0),
            },
            'retirement_goals': {
                'desired_retirement_date': request.POST.get('desired_retirement_date'),
                'retirement_age': int(request.POST.get('retirement_age', 0) or 0),
                'continuation_of_health_benefits': request.POST.get('continuation_of_health_benefits') == 'on',
                'survivor_benefit_election': request.POST.get('survivor_benefit_election', ''),
            },
            'tsp': {
                'current_balance': float(request.POST.get('tsp_current_balance', 0) or 0),
                'employee_contribution_pct': float(request.POST.get('tsp_employee_contribution_pct', 0) or 0),
                'agency_match_pct': float(request.POST.get('tsp_agency_match_pct', 5) or 5),
                'roth_balance': float(request.POST.get('tsp_roth_balance', 0) or 0),
                'traditional_balance': float(request.POST.get('tsp_traditional_balance', 0) or 0),
                'loan_balance': float(request.POST.get('tsp_loan_balance', 0) or 0),
            },
            'social_security': {
                'covered_employment': request.POST.get('ss_covered_employment') == 'on',
                'estimated_benefit_age_62': float(request.POST.get('ss_estimated_benefit_age_62', 0) or 0),
                'estimated_benefit_fra': float(request.POST.get('ss_estimated_benefit_fra', 0) or 0),
            },
            'other_income': {
                'spouse_income': float(request.POST.get('spouse_income', 0) or 0),
                'rental_income': float(request.POST.get('rental_income', 0) or 0),
                'pension_income': float(request.POST.get('pension_income', 0) or 0),
            },
        }
        
        # Create new case
        case = Case(
            member=user,
            workshop_code=user.workshop_code,
            external_case_id=external_case_id,
            employee_first_name=request.POST.get('employee_first_name'),
            employee_last_name=request.POST.get('employee_last_name'),
            client_email=request.POST.get('client_email'),
            urgency=request.POST.get('urgency', 'normal'),
            num_reports_requested=int(request.POST.get('num_reports_requested', 1)),
            status='submitted',
            fact_finder_data=fact_finder_data,
            notes=request.POST.get('additional_notes', ''),
        )
        
        case.save()
        
        messages.success(request, f'Case {case.external_case_id} submitted successfully!')
        return redirect('member_dashboard')
    
    context = {
        'workshop_code': user.workshop_code,
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
    reports = CaseReport.objects.filter(case=case).order_by('-uploaded_at')
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
