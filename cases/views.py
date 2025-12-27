from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone
from django.http import HttpResponseForbidden
from .models import Case, CaseDocument
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
    cases = Case.objects.filter(member=user).prefetch_related(
        'documents'
    ).select_related(
        'assigned_to'
    ).order_by('-date_submitted')
    
    # Apply filters
    status_filter = request.GET.get('status')
    urgency_filter = request.GET.get('urgency')
    search_query = request.GET.get('search')
    sort_by = request.GET.get('sort', '-date_submitted')
    
    if status_filter:
        cases = cases.filter(status=status_filter)
    
    if urgency_filter:
        cases = cases.filter(urgency=urgency_filter)
    
    if search_query:
        cases = cases.filter(
            Q(external_case_id__icontains=search_query) |
            Q(employee_first_name__icontains=search_query) |
            Q(employee_last_name__icontains=search_query) |
            Q(workshop_code__icontains=search_query)
        )
    
    # Handle sorting
    if sort_by in ['external_case_id', '-external_case_id', 'date_submitted', '-date_submitted', 
                   'date_due', '-date_due', 'status', '-status', 'urgency', '-urgency']:
        cases = cases.order_by(sort_by)
    
    # Calculate statistics
    stats = {
        'total_cases': Case.objects.filter(member=user).count(),
        'draft': Case.objects.filter(member=user, status='draft').count(),
        'submitted': Case.objects.filter(member=user, status='submitted').count(),
        'accepted': Case.objects.filter(member=user, status='accepted').count(),
        'completed': Case.objects.filter(member=user, status='completed').count(),
    }
    
    context = {
        'cases': cases,
        'stats': stats,
        'status_filter': status_filter,
        'urgency_filter': urgency_filter,
        'search_query': search_query,
        'sort_by': sort_by,
    }
    
    return render(request, 'cases/member_dashboard.html', context)


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
    ).select_related('member').order_by('-updated_at')
    
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
        'completed': assigned_cases.filter(status='completed').count(),
    }
    
    context = {
        'assigned_cases': assigned_cases,
        'stats': stats,
        'status_filter': status_filter,
        'search_query': search_query,
    }
    
    return render(request, 'cases/technician_workbench.html', context)


@login_required
def case_list(request):
    """List all cases - Admin and Manager only"""
    user = request.user
    
    # Ensure user is admin or manager
    if user.role not in ['admin', 'manager']:
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    # Get all cases
    cases = Case.objects.all().select_related(
        'member', 'assigned_to'
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
        'total': cases.count(),
        'draft': cases.filter(status='draft').count(),
        'submitted': cases.filter(status='submitted').count(),
        'accepted': cases.filter(status='accepted').count(),
        'completed': cases.filter(status='completed').count(),
    }
    
    context = {
        'cases': cases,
        'stats': stats,
        'status_filter': status_filter,
        'search_query': search_query,
    }
    
    return render(request, 'cases/case_list.html', context)


@login_required
def delete_case(request, pk):
    """Delete a case"""
    case = get_object_or_404(Case, pk=pk)
    
    # Permission check - only members can delete their own drafts
    if request.user.role == 'member' and case.member == request.user and case.status == 'draft':
        case.delete()
        messages.success(request, f'Case {case.external_case_id} has been deleted.')
        return redirect('member_dashboard')
    
    # Redirect based on user role
    if request.user.role == 'member':
        return redirect('member_dashboard')
    elif request.user.role == 'technician':
        return redirect('technician_workbench')
    else:
        return redirect('case_list')


@login_required
def case_detail(request, pk):
    """Case detail view"""
    user = request.user
    case = get_object_or_404(Case, pk=pk)
    
    # Permission check
    can_view = False
    can_edit = False
    
    if user.role == 'member' and case.member == user:
        can_view = True
    elif user.role == 'technician' and case.assigned_to == user:
        can_view = True
        can_edit = True
    elif user.role in ['admin', 'manager']:
        can_view = True
        can_edit = True
    
    if not can_view:
        messages.error(request, 'You do not have permission to view this case.')
        return redirect('home')
    
    # Get related documents
    documents = CaseDocument.objects.filter(case=case).order_by('-uploaded_at')
    
    context = {
        'case': case,
        'can_edit': can_edit,
        'documents': documents,
    }
    
    return render(request, 'cases/case_detail.html', context)
