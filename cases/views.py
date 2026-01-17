from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.db import models
from django.utils import timezone
from django.http import HttpResponseForbidden, JsonResponse
from django.urls import reverse
from django.core.paginator import Paginator
from django.views.decorators.http import require_http_methods
from accounts.models import User
from .models import Case, CaseDocument
import logging
import json

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
    from django.db.models import Q
    
    user = request.user
    
    # Ensure user is a member
    if user.role != 'member':
        messages.error(request, 'Access denied. Members only.')
        return redirect('home')
    
    # Get all cases for this member
    # Show all cases - completed cases appear as "working" if scheduled but not yet released
    cases = Case.objects.filter(
        member=user
    ).prefetch_related(
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
    all_cases = Case.objects.filter(member=user)
    stats = {
        'total_cases': all_cases.count(),
        'draft': all_cases.filter(status='draft').count(),
        'submitted': all_cases.filter(status='submitted').count(),
        'accepted': all_cases.filter(status='accepted').count(),
        'resubmitted': all_cases.filter(status='resubmitted').count(),
        'completed': all_cases.filter(status='completed').count(),
    }
    
    # Get column visibility settings
    visible_columns = get_user_visible_columns(user, 'member_dashboard')
    
    context = {
        'cases': cases,
        'stats': stats,
        'status_filter': status_filter,
        'urgency_filter': urgency_filter,
        'search_query': search_query,
        'sort_by': sort_by,
        'visible_columns': visible_columns,
        'all_columns': DASHBOARD_COLUMN_CONFIG['member_dashboard']['available_columns'],
    }
    
    return render(request, 'cases/member_dashboard.html', context)


@login_required
def technician_dashboard(request):
    """Dashboard view for Benefits Technician - shows all cases (not just assigned)"""
    user = request.user
    
    # Ensure user is a technician, manager, or admin
    if user.role not in ['technician', 'manager', 'administrator']:
        messages.error(request, 'Access denied. Technicians and Admins only.')
        return redirect('home')
    
    # Load saved view preference
    from accounts.models import UserPreference
    saved_preference = UserPreference.objects.filter(
        user=user,
        preference_key='technician_dashboard_view'
    ).first()
    
    # Get saved view type or default to 'all'
    default_view = 'all'
    if saved_preference:
        default_view = saved_preference.preference_value.get('view', 'all')
    
    # Get all cases (technicians see all, not just assigned)
    # BUT exclude draft cases unless assigned to them
    from django.db.models import Q
    cases = Case.objects.filter(
        Q(status__in=['submitted', 'resubmitted', 'accepted', 'hold', 'pending_review', 'completed']) |  # Non-draft cases
        Q(assigned_to=user)  # OR cases assigned to this technician (even if draft)
    ).prefetch_related(
        'documents'
    ).select_related(
        'member', 'assigned_to', 'reviewed_by'
    ).order_by('-date_submitted')
    
    # Apply filters
    status_filters = request.GET.getlist('status')  # Get list of selected statuses
    urgency_filter = request.GET.get('urgency')
    tier_filter = request.GET.get('tier')
    search_query = request.GET.get('search')
    sort_by = request.GET.get('sort', '-date_submitted')
    assigned_filter = request.GET.get('assigned', default_view)  # Use saved preference as default
    
    # Apply "My Cases" filter
    if assigned_filter == 'mine':
        cases = cases.filter(assigned_to=user)
    
    # Apply multi-status filter
    if status_filters:
        cases = cases.filter(status__in=status_filters)
    
    if urgency_filter:
        cases = cases.filter(urgency=urgency_filter)
    
    if tier_filter:
        cases = cases.filter(tier=tier_filter)
    
    if search_query:
        cases = cases.filter(
            Q(external_case_id__icontains=search_query) |
            Q(employee_first_name__icontains=search_query) |
            Q(employee_last_name__icontains=search_query) |
            Q(workshop_code__icontains=search_query) |
            Q(member__first_name__icontains=search_query) |
            Q(member__last_name__icontains=search_query)
        )
    
    # Handle sorting
    allowed_sorts = [
        'external_case_id', '-external_case_id',
        'workshop_code', '-workshop_code',
        'employee_first_name', '-employee_first_name',
        'employee_last_name', '-employee_last_name',
        'date_submitted', '-date_submitted',
        'date_due', '-date_due',
        'date_scheduled', '-date_scheduled',
        'status', '-status',
        'urgency', '-urgency',
        'tier', '-tier'
    ]
    if sort_by in allowed_sorts:
        cases = cases.order_by(sort_by)
    else:
        cases = cases.order_by('-date_submitted')
    
    # Calculate statistics - based on accessible cases
    stats = {
        'total': cases.count(),
        'submitted': cases.filter(status='submitted').count(),
        'accepted': cases.filter(status='accepted').count(),
        'pending_review': cases.filter(status='pending_review').count(),
        'completed': cases.filter(status='completed').count(),
        'urgent': cases.filter(urgency='urgent').count(),
    }
    
    # Get available technicians and administrators for assignment dropdown
    technicians = User.objects.filter(
        role__in=['technician', 'administrator']
    ).order_by('last_name', 'first_name')
    
    context = {
        'cases': cases,
        'stats': stats,
        'status_filters': status_filters,  # List of selected statuses
        'urgency_filter': urgency_filter,
        'tier_filter': tier_filter,
        'search_query': search_query,
        'sort_by': sort_by,
        'assigned_filter': assigned_filter,
        'technicians': technicians,
        'dashboard_type': 'technician',
    }
    
    # Add column visibility data
    visible_columns = get_user_visible_columns(user, 'technician_dashboard')
    context['visible_columns'] = visible_columns
    context['all_columns'] = DASHBOARD_COLUMN_CONFIG['technician_dashboard']['available_columns']
    
    return render(request, 'cases/technician_dashboard.html', context)


@login_required
def admin_dashboard(request):
    """Dashboard view for Administrators - full system visibility and control"""
    user = request.user
    
    # Ensure user is an administrator
    if user.role != 'administrator':
        messages.error(request, 'Access denied. Administrators only.')
        return redirect('home')
    
    # Get all cases with all related data
    cases = Case.objects.all().prefetch_related(
        'documents'
    ).select_related(
        'member', 'assigned_to', 'reviewed_by'
    ).order_by('-date_submitted')
    
    # Apply filters
    status_filter = request.GET.get('status')
    urgency_filter = request.GET.get('urgency')
    tier_filter = request.GET.get('tier')
    member_filter = request.GET.get('member')
    technician_filter = request.GET.get('technician')
    date_range = request.GET.get('date_range')
    custom_date_from = request.GET.get('date_from')
    custom_date_to = request.GET.get('date_to')
    search_query = request.GET.get('search')
    sort_by = request.GET.get('sort', '-date_submitted')
    
    if status_filter:
        cases = cases.filter(status=status_filter)
    
    if urgency_filter:
        cases = cases.filter(urgency=urgency_filter)
    
    if tier_filter:
        cases = cases.filter(tier=tier_filter)
    
    if member_filter:
        cases = cases.filter(member_id=member_filter)
    
    if technician_filter:
        cases = cases.filter(assigned_to_id=technician_filter)
    
    # Date range filter - custom dates take precedence
    if custom_date_from or custom_date_to:
        from datetime import datetime
        if custom_date_from:
            date_from = datetime.strptime(custom_date_from, '%Y-%m-%d').date()
            cases = cases.filter(date_submitted__date__gte=date_from)
        if custom_date_to:
            date_to = datetime.strptime(custom_date_to, '%Y-%m-%d').date()
            cases = cases.filter(date_submitted__date__lte=date_to)
    elif date_range:
        from datetime import timedelta
        today = timezone.now().date()
        if date_range == 'today':
            cases = cases.filter(date_submitted__date=today)
        elif date_range == 'week':
            week_ago = today - timedelta(days=7)
            cases = cases.filter(date_submitted__date__gte=week_ago)
        elif date_range == 'month':
            month_ago = today - timedelta(days=30)
            cases = cases.filter(date_submitted__date__gte=month_ago)
    
    if search_query:
        cases = cases.filter(
            Q(external_case_id__icontains=search_query) |
            Q(employee_first_name__icontains=search_query) |
            Q(employee_last_name__icontains=search_query) |
            Q(workshop_code__icontains=search_query) |
            Q(member__first_name__icontains=search_query) |
            Q(member__last_name__icontains=search_query) |
            Q(client_email__icontains=search_query)
        )
    
    # Handle sorting
    allowed_sorts = [
        'external_case_id', '-external_case_id',
        'workshop_code', '-workshop_code',
        'employee_first_name', '-employee_first_name',
        'employee_last_name', '-employee_last_name',
        'date_submitted', '-date_submitted',
        'date_due', '-date_due',
        'date_scheduled', '-date_scheduled',
        'status', '-status',
        'urgency', '-urgency',
        'tier', '-tier'
    ]
    if sort_by in allowed_sorts:
        cases = cases.order_by(sort_by)
    else:
        cases = cases.order_by('-date_submitted')
    
    # Get related data for filters
    from accounts.models import User
    members = User.objects.filter(role='member', is_active=True).order_by('username')
    technicians = User.objects.filter(role='technician', is_active=True).order_by('username')
    
    # Calculate comprehensive statistics
    all_cases = Case.objects.all()
    
    # Get active users (currently logged in) from sessions
    from django.contrib.sessions.models import Session
    from django.utils import timezone
    active_sessions = Session.objects.filter(expire_date__gte=timezone.now())
    active_user_ids = set()
    for session in active_sessions:
        session_data = session.get_decoded()
        user_id = session_data.get('_auth_user_id')
        if user_id:
            active_user_ids.add(int(user_id))
    
    # Count active members and technicians
    active_members = User.objects.filter(id__in=active_user_ids, role='member').count()
    active_technicians = User.objects.filter(id__in=active_user_ids, role='technician').count()
    
    stats = {
        'total': all_cases.count(),
        'submitted': all_cases.filter(status='submitted').count(),
        'accepted': all_cases.filter(status='accepted').count(),
        'hold': all_cases.filter(status='hold').count(),
        'pending_review': all_cases.filter(status='pending_review').count(),
        'completed': all_cases.filter(status='completed').count(),
        'urgent': all_cases.filter(urgency='urgent').count(),
        'total_members': active_members,
        'total_technicians': active_technicians,
        'unassigned': all_cases.filter(assigned_to__isnull=True).count(),
        'requiring_review': all_cases.filter(status='pending_review').count(),
    }
    
    context = {
        'cases': cases,
        'stats': stats,
        'members': members,
        'technicians': technicians,
        'status_filter': status_filter,
        'urgency_filter': urgency_filter,
        'tier_filter': tier_filter,
        'member_filter': member_filter,
        'technician_filter': technician_filter,
        'date_range': date_range,
        'custom_date_from': custom_date_from,
        'custom_date_to': custom_date_to,
        'search_query': search_query,
        'sort_by': sort_by,
        'dashboard_type': 'admin',
        'visible_columns': get_user_visible_columns(user, 'admin_dashboard'),
        'all_columns': DASHBOARD_COLUMN_CONFIG['admin_dashboard']['available_columns'],
    }
    
    return render(request, 'cases/admin_dashboard.html', context)


@login_required
def manager_dashboard(request):
    """Dashboard view for Managers - read-only visibility with analytics"""
    user = request.user
    
    # Ensure user is a manager
    if user.role != 'manager':
        messages.error(request, 'Access denied. Managers only.')
        return redirect('home')
    
    # Get all cases with all related data (read-only)
    cases = Case.objects.all().prefetch_related(
        'documents'
    ).select_related(
        'member', 'assigned_to', 'reviewed_by'
    ).order_by('-date_submitted')
    
    # Apply filters
    status_filter = request.GET.get('status')
    urgency_filter = request.GET.get('urgency')
    tier_filter = request.GET.get('tier')
    member_filter = request.GET.get('member')
    technician_filter = request.GET.get('technician')
    date_range = request.GET.get('date_range')
    custom_date_from = request.GET.get('date_from')
    custom_date_to = request.GET.get('date_to')
    search_query = request.GET.get('search')
    sort_by = request.GET.get('sort', '-date_submitted')
    
    if status_filter:
        cases = cases.filter(status=status_filter)
    
    if urgency_filter:
        cases = cases.filter(urgency=urgency_filter)
    
    if tier_filter:
        cases = cases.filter(tier=tier_filter)
    
    if member_filter:
        cases = cases.filter(member_id=member_filter)
    
    if technician_filter:
        cases = cases.filter(assigned_to_id=technician_filter)
    
    # Date range filter - custom dates take precedence
    if custom_date_from or custom_date_to:
        from datetime import datetime
        if custom_date_from:
            date_from = datetime.strptime(custom_date_from, '%Y-%m-%d').date()
            cases = cases.filter(date_submitted__date__gte=date_from)
        if custom_date_to:
            date_to = datetime.strptime(custom_date_to, '%Y-%m-%d').date()
            cases = cases.filter(date_submitted__date__lte=date_to)
    elif date_range:
        from datetime import timedelta
        today = timezone.now().date()
        if date_range == 'today':
            cases = cases.filter(date_submitted__date=today)
        elif date_range == 'week':
            week_ago = today - timedelta(days=7)
            cases = cases.filter(date_submitted__date__gte=week_ago)
        elif date_range == 'month':
            month_ago = today - timedelta(days=30)
            cases = cases.filter(date_submitted__date__gte=month_ago)
    
    if search_query:
        cases = cases.filter(
            Q(external_case_id__icontains=search_query) |
            Q(employee_first_name__icontains=search_query) |
            Q(employee_last_name__icontains=search_query) |
            Q(workshop_code__icontains=search_query) |
            Q(member__first_name__icontains=search_query) |
            Q(member__last_name__icontains=search_query) |
            Q(client_email__icontains=search_query)
        )
    
    # Handle sorting
    allowed_sorts = [
        'external_case_id', '-external_case_id',
        'workshop_code', '-workshop_code',
        'employee_first_name', '-employee_first_name',
        'employee_last_name', '-employee_last_name',
        'date_submitted', '-date_submitted',
        'date_due', '-date_due',
        'date_scheduled', '-date_scheduled',
        'status', '-status',
        'urgency', '-urgency',
        'tier', '-tier'
    ]
    if sort_by in allowed_sorts:
        cases = cases.order_by(sort_by)
    else:
        cases = cases.order_by('-date_submitted')
    
    # Get related data for filters
    from accounts.models import User
    members = User.objects.filter(role='member', is_active=True).order_by('username')
    technicians = User.objects.filter(role='technician', is_active=True).order_by('username')
    
    # Calculate comprehensive analytics statistics
    all_cases = Case.objects.all()
    completed_cases = all_cases.filter(status='completed')
    
    submitted_count = all_cases.filter(status='submitted').count()
    accepted_count = all_cases.filter(status='accepted').count()
    hold_count = all_cases.filter(status='hold').count()
    pending_review_count = all_cases.filter(status='pending_review').count()
    completed_count = completed_cases.count()
    urgent_count = all_cases.filter(urgency='urgent').count()
    total_count = all_cases.count()
    
    # Calculate percentages for progress bars
    if total_count > 0:
        submitted_pct = round((submitted_count + accepted_count) * 100 / total_count, 1)
        pending_review_pct = round(pending_review_count * 100 / total_count, 1)
        completed_pct = round(completed_count * 100 / total_count, 1)
        hold_pct = round(hold_count * 100 / total_count, 1)
    else:
        submitted_pct = pending_review_pct = completed_pct = hold_pct = 0
    
    stats = {
        'total': total_count,
        'submitted': submitted_count,
        'accepted': accepted_count,
        'hold': hold_count,
        'pending_review': pending_review_count,
        'completed': completed_count,
        'completion_rate': round((completed_count / total_count * 100) if total_count > 0 else 0, 1),
        'urgent': urgent_count,
        'normal': max(0, total_count - urgent_count),
        'total_members': User.objects.filter(role='member', is_active=True).count(),
        'total_technicians': User.objects.filter(role='technician', is_active=True).count(),
        'avg_processing_time': 'N/A',  # Would require more complex calculation
        'submitted_pct': submitted_pct,
        'pending_review_pct': pending_review_pct,
        'completed_pct': completed_pct,
        'hold_pct': hold_pct,
    }
    
    context = {
        'cases': cases,
        'stats': stats,
        'members': members,
        'technicians': technicians,
        'status_filter': status_filter,
        'urgency_filter': urgency_filter,
        'tier_filter': tier_filter,
        'member_filter': member_filter,
        'technician_filter': technician_filter,
        'date_range': date_range,
        'custom_date_from': custom_date_from,
        'custom_date_to': custom_date_to,
        'search_query': search_query,
        'sort_by': sort_by,
        'dashboard_type': 'manager',
        'is_readonly': True,
        'visible_columns': get_user_visible_columns(user, 'manager_dashboard'),
        'all_columns': DASHBOARD_COLUMN_CONFIG['manager_dashboard']['available_columns'],
    }
    
    return render(request, 'cases/manager_dashboard.html', context)


@login_required
def case_list(request):
    """List all cases - Admin and Manager only"""
    user = request.user
    
    # Ensure user is admin or manager
    if user.role not in ['administrator', 'manager']:
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
    """Delete a case - members can only delete draft cases, admins can delete any case"""
    case = get_object_or_404(Case, pk=pk)
    
    # Permission check
    can_delete = False
    redirect_to = 'cases:case_list'
    
    if request.user.role == 'member' and case.member == request.user:
        # Members can only delete their own draft cases
        if case.status == 'draft':
            can_delete = True
            redirect_to = 'cases:member_dashboard'
        else:
            messages.error(request, f'Cannot delete case {case.external_case_id}. Only draft cases can be deleted. This case is currently {case.get_status_display().lower()}.')
            return redirect('cases:case_detail', pk=pk)
    elif request.user.role in ['administrator', 'manager']:
        # Admins can delete any case
        can_delete = True
        redirect_to = 'cases:admin_dashboard'
    
    if not can_delete:
        messages.error(request, 'You do not have permission to delete this case.')
        return redirect(redirect_to)
    
    if request.method == 'POST':
        case_id = case.external_case_id
        
        # Get counts before deletion for the success message
        documents = case.documents.count()
        reports = case.reports.count()
        notes = case.case_notes.count()
        
        # Delete the case (cascade will handle related objects)
        case.delete()
        
        messages.success(request, f'Case {case_id} and all related data ({documents} documents, {reports} reports, {notes} notes) have been permanently deleted.')
        return redirect(redirect_to)
    
    # GET request - show confirmation page
    context = {
        'case': case,
        'documents_count': case.documents.count(),
        'reports_count': case.reports.count(),
        'notes_count': case.case_notes.count(),
    }
    return render(request, 'cases/confirm_delete_case.html', context)


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
        can_edit = True  # Members can edit their own cases (add/remove documents)
    elif user.role == 'technician':
        # Technicians can view submitted cases and cases assigned to them
        if case.status in ['submitted', 'accepted', 'hold', 'pending_review', 'completed'] or case.assigned_to == user:
            can_view = True
        # Technicians can edit cases they own
        if case.assigned_to == user:
            can_edit = True
    elif user.role in ['administrator', 'manager']:
        can_view = True
        can_edit = True
    
    if not can_view:
        messages.error(request, 'You do not have permission to view this case.')
        return redirect('home')
    
    # Handle draft edit POST requests
    if request.method == 'POST' and request.POST.get('edit_draft'):
        if case.status == 'draft' and user.role == 'member' and case.member == user:
            # Update the case fields
            if 'num_reports_requested' in request.POST:
                try:
                    case.num_reports_requested = int(request.POST.get('num_reports_requested'))
                except (ValueError, TypeError):
                    pass
            
            if 'date_due' in request.POST and request.POST.get('date_due'):
                try:
                    from datetime import datetime
                    case.date_due = datetime.strptime(request.POST.get('date_due'), '%Y-%m-%d').date()
                except (ValueError, TypeError):
                    pass
            
            if 'special_notes' in request.POST:
                case.special_notes = request.POST.get('special_notes', '')
            
            case.save()
            messages.success(request, 'Draft case updated successfully.')
            return redirect('cases:case_detail', pk=case.id)
        else:
            messages.error(request, 'You do not have permission to edit this case.')
            return redirect('cases:case_detail', pk=case.id)
    
    # Get related documents - ordered by type for proper grouping in template
    documents = CaseDocument.objects.filter(case=case).order_by('document_type', '-uploaded_at')
    
    # Get case notes (technician/internal notes)
    from cases.models import CaseNote, CaseReport
    
    # Determine if user can see internal notes
    can_view_internal_notes = user.role in ['technician', 'administrator', 'manager']
    
    # Filter case notes based on visibility
    if can_view_internal_notes:
        # Techs/admins see all notes
        case_notes = CaseNote.objects.filter(case=case).order_by('-created_at')
    else:
        # Members see only public notes (is_internal=False)
        case_notes = CaseNote.objects.filter(case=case, is_internal=False).order_by('-created_at')
    
    # Check if member can view technician's report and documents
    # Members can only see these if case is completed AND released
    can_view_report = True
    if user.role == 'member' and case.member == user:
        # For members: only show report/docs if case is completed AND actual_release_date is set
        if case.status == 'completed' and case.actual_release_date is None:
            can_view_report = False
    
    # Get technician documents only
    tech_documents = documents.filter(document_type='report').order_by('-uploaded_at')
    
    # Get case reports
    reports = case.reports.all().order_by('report_number')
    
    # Only technicians can upload reports
    can_upload_reports = user.role == 'technician' and can_edit
    
    # Check if user can release case immediately (case owner or admin, and case is scheduled for release)
    can_release_immediately = False
    if case.status == 'completed' and case.scheduled_release_date is not None:
        # Only case owner (assigned_to) or admin can release
        if user.role == 'administrator' or (user.role == 'technician' and case.assigned_to == user):
            can_release_immediately = True
    
    # Get available technicians for reassignment dropdown
    available_techs = User.objects.filter(role='technician', is_active=True).order_by('first_name')
    
    # Get audit history for this case (Manager/Admin only)
    audit_logs = []
    if user.role in ['manager', 'administrator']:
        from core.models import AuditLog
        from django.db.models import Q
        audit_logs = AuditLog.objects.filter(
            Q(case=case) | Q(document__case=case)
        ).select_related('user', 'case', 'document').order_by('-timestamp')[:15]
    
    context = {
        'case': case,
        'can_edit': can_edit,
        'can_upload_reports': can_upload_reports,
        'can_view_report': can_view_report,
        'can_view_internal_notes': can_view_internal_notes,
        'can_release_immediately': can_release_immediately,
        'documents': documents,
        'tech_documents': tech_documents,
        'case_notes': case_notes,
        'reports': reports,
        'available_techs': available_techs,
        'audit_logs': audit_logs,
    }
    
    return render(request, 'cases/case_detail.html', context)


@login_required
def release_case_immediately(request, case_id):
    """Release a scheduled case immediately to member"""
    from django.http import JsonResponse
    from django.utils import timezone
    
    user = request.user
    case = get_object_or_404(Case, id=case_id)
    
    # Permission check - case must be scheduled for release
    if case.status != 'completed' or case.scheduled_release_date is None:
        return JsonResponse({
            'success': False,
            'message': 'This case is not scheduled for release.'
        }, status=400)
    
    # Permission check - only case owner (assigned_to) or admin can release
    if user.role == 'administrator' or (user.role == 'technician' and case.assigned_to == user):
        # Release the case immediately
        case.actual_release_date = timezone.now()
        case.scheduled_release_date = None
        case.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Case {case.external_case_id} has been released immediately to the member.'
        })
    else:
        return JsonResponse({
            'success': False,
            'message': 'You do not have permission to release this case.'
        }, status=403)


@login_required
def admin_take_ownership(request, case_id):
    """Allow admin to take ownership of a case (becomes the assigned technician)"""
    user = request.user
    case = get_object_or_404(Case, id=case_id)
    
    # Permission check - only admin can take ownership
    if user.role != 'administrator':
        messages.error(request, 'Only administrators can take ownership of cases.')
        return redirect('cases:case_detail', pk=case_id)
    
    if request.method == 'POST':
        # Store the previous owner for audit trail
        previous_owner = case.assigned_to
        
        # Admin takes ownership by setting assigned_to to the admin user
        case.assigned_to = user
        
        # Get credit value from form if provided, otherwise keep existing
        credit_value = request.POST.get('credit_value')
        if credit_value:
            from decimal import Decimal
            try:
                credit_value = Decimal(credit_value)
                # Log credit change if it differs from current
                from cases.services.credit_service import set_case_credit
                set_case_credit(case, credit_value, user, 'acceptance', 'Confirmed/adjusted upon taking ownership')
            except (ValueError, TypeError):
                pass
        
        # Transition to 'accepted' status when ownership is taken
        case.status = 'accepted'
        case.save()
        
        # Log the action
        previous_owner_name = f"{previous_owner.first_name} {previous_owner.last_name}" if previous_owner else "None"
        messages.success(
            request, 
            f'You have taken ownership of case {case.external_case_id}. Previous owner: {previous_owner_name}. Status: Accepted'
        )
        
        return redirect('cases:case_detail', pk=case_id)
    
    # GET request - show confirmation page
    context = {
        'case': case,
        'current_owner': case.assigned_to,
    }
    return render(request, 'cases/admin_take_ownership.html', context)


@login_required
def edit_case(request, pk):
    """Edit case details (members only, before submission)"""
    user = request.user
    case = get_object_or_404(Case, pk=pk)
    
    # Permission check - only the member who owns the case can edit
    if user.role != 'member' or case.member != user:
        messages.error(request, 'You do not have permission to edit this case.')
        return redirect('cases:case_detail', pk=pk)
    
    # Check if case can be edited
    if case.status == 'submitted':
        messages.error(request, 'Cannot edit a submitted case.')
        return redirect('cases:case_detail', pk=pk)
    
    if request.method == 'POST':
        # Get form data
        urgency = request.POST.get('urgency', case.urgency)
        num_reports = request.POST.get('num_reports_requested', case.num_reports_requested)
        due_date = request.POST.get('date_due', case.date_due)
        special_notes = request.POST.get('special_notes', case.special_notes)
        
        # Validate data
        try:
            num_reports = int(num_reports)
            if num_reports < 1 or num_reports > 10:
                num_reports = case.num_reports_requested
        except (ValueError, TypeError):
            num_reports = case.num_reports_requested
        
        # Validate urgency
        if urgency not in ['normal', 'urgent']:
            urgency = case.urgency
        
        # Update case
        case.urgency = urgency
        case.num_reports_requested = num_reports
        if due_date:
            case.date_due = due_date
        case.special_notes = special_notes
        case.save()
        
        messages.success(request, 'Case details updated successfully.')
        return redirect('cases:case_detail', pk=pk)
    
    context = {
        'case': case,
    }
    return render(request, 'cases/edit_case.html', context)


@login_required
def reassign_case(request, case_id):
    """API endpoint to reassign a case to a different technician"""
    from django.http import JsonResponse
    
    user = request.user
    case = get_object_or_404(Case, id=case_id)
    
    # Permission check - only techs and admins can reassign
    if user.role not in ['technician', 'administrator', 'manager']:
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
    
    if request.method == 'POST':
        new_technician_id = request.POST.get('technician_id')
        
        if not new_technician_id:
            return JsonResponse({'success': False, 'error': 'No technician selected'}, status=400)
        
        try:
            new_technician = User.objects.get(id=new_technician_id, role='technician')
            old_technician = case.assigned_to
            case.assigned_to = new_technician
            case.save()
            
            return JsonResponse({
                'success': True, 
                'message': f'Case reassigned from {old_technician.username if old_technician else "Unassigned"} to {new_technician.username}',
                'new_assignee': new_technician.get_full_name() or new_technician.username
            })
        except User.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Technician not found'}, status=404)
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=400)


@login_required
def submit_case_final(request, case_id):
    """Submit a draft case to transition it from draft to submitted status"""
    if request.method == 'POST':
        try:
            user = request.user
            case = get_object_or_404(Case, pk=case_id)
            
            # Permission check: Only the case creator (member) can submit their own case
            if case.member != user:
                return JsonResponse({
                    'success': False, 
                    'error': 'You do not have permission to submit this case'
                }, status=403)
            
            # Status check: Only draft cases can be submitted
            if case.status != 'draft':
                return JsonResponse({
                    'success': False, 
                    'error': f'Only draft cases can be submitted. This case is {case.get_status_display()}'
                }, status=400)
            
            # Update case status to submitted
            case.status = 'submitted'
            case.date_submitted = timezone.now()
            case.save()
            
            return JsonResponse({
                'success': True,
                'message': f'Case {case.external_case_id} has been submitted successfully',
                'redirect': reverse('cases:member_dashboard')
            })
        except Case.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Case not found'}, status=404)
        except Exception as e:
            logger.error(f'Error submitting case {case_id}: {str(e)}')
            return JsonResponse({'success': False, 'error': 'An error occurred while submitting the case'}, status=500)
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=400)


@login_required
def take_case_ownership(request, case_id):
    """API endpoint for a technician to take ownership of an unassigned case"""
    if request.method == 'POST':
        try:
            user = request.user
            case = get_object_or_404(Case, pk=case_id)
            
            # Permission check: Only technicians can take ownership
            if user.role != 'technician':
                return JsonResponse({
                    'success': False,
                    'error': 'Only technicians can take ownership of cases'
                }, status=403)
            
            # Check if case is already assigned
            if case.assigned_to is not None:
                return JsonResponse({
                    'success': False,
                    'error': f'Case is already assigned to {case.assigned_to.get_full_name()}'
                }, status=400)
            
            # Assign the case to the current technician and mark as accepted
            case.assigned_to = user
            case.status = 'accepted'
            case.save()
            
            return JsonResponse({
                'success': True,
                'message': f'You have taken ownership of case {case.external_case_id}',
                'new_assignee': user.get_full_name() or user.username
            })
        except Case.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Case not found'}, status=404)
        except Exception as e:
            logger.error(f'Error taking ownership of case {case_id}: {str(e)}')
            return JsonResponse({'success': False, 'error': 'An error occurred while taking ownership'}, status=500)
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=400)


@login_required
def add_case_note(request, case_id):
    """Add a note to a case (everyone can add, but visibility depends on is_internal flag)"""
    from cases.models import CaseNote
    from django.utils import timezone
    from datetime import timedelta
    
    user = request.user
    case = get_object_or_404(Case, id=case_id)
    
    # Permission check - members and techs/admins can add notes
    if user.role not in ['member', 'technician', 'administrator', 'manager']:
        messages.error(request, 'You do not have permission to add notes to this case.')
        return redirect('cases:case_detail', pk=case_id)
    
    # Additional check for members - can only add notes to their own cases
    if user.role == 'member' and case.member != user:
        messages.error(request, 'You do not have permission to add notes to this case.')
        return redirect('cases:case_detail', pk=case_id)
    
    if request.method == 'POST':
        note_text = request.POST.get('notes', '').strip()
        
        if note_text:
            # Check for duplicate notes created in the last 30 seconds to prevent accidental duplicates
            recent_duplicate = CaseNote.objects.filter(
                case=case,
                author=user,
                note=note_text,
                created_at__gte=timezone.now() - timedelta(seconds=30)
            ).exists()
            
            if recent_duplicate:
                messages.warning(request, 'This note was just added. Duplicate prevented.')
            else:
                # Members add public notes (is_internal=False)
                # Techs/admins add internal notes (is_internal=True)
                is_internal = user.role in ['technician', 'administrator', 'manager']
                
                CaseNote.objects.create(
                    case=case,
                    author=user,
                    note=note_text,
                    is_internal=is_internal
                )
                messages.success(request, 'Note added successfully.')
        else:
            messages.warning(request, 'Note cannot be empty.')
    
    return redirect('cases:case_detail', pk=case_id)


@login_required
def delete_case_note(request, case_id, note_id):
    """Delete a case note (author or admin only)"""
    from cases.models import CaseNote
    from django.http import JsonResponse
    
    user = request.user
    case = get_object_or_404(Case, id=case_id)
    note = get_object_or_404(CaseNote, id=note_id, case=case)
    
    # Permission check - only note author or admins can delete
    if user.id != note.author.id and user.role not in ['administrator', 'manager']:
        return JsonResponse({
            'success': False,
            'error': 'You do not have permission to delete this note'
        }, status=403)
    
    if request.method == 'POST':
        try:
            note.delete()
            return JsonResponse({
                'success': True,
                'message': 'Note deleted successfully'
            })
        except Exception as e:
            logger.error(f'Error deleting note {note_id}: {str(e)}')
            return JsonResponse({
                'success': False,
                'error': 'Failed to delete note'
            }, status=500)
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=400)


@login_required
def upload_case_report(request, case_id):
    """Upload a completed report for a case (technician/admin only)"""
    from cases.models import CaseReport
    
    user = request.user
    case = get_object_or_404(Case, id=case_id)
    
    # Permission check - only techs and admins can upload reports
    if user.role not in ['technician', 'administrator', 'manager']:
        messages.error(request, 'You do not have permission to upload reports to this case.')
        return redirect('cases:case_detail', pk=case_id)
    
    # Check if technician owns the case
    if user.role == 'technician' and case.assigned_to != user:
        messages.error(request, 'You can only upload reports to cases you are assigned to.')
        return redirect('cases:case_detail', pk=case_id)
    
    if request.method == 'POST':
        report_file = request.FILES.get('report_file')
        report_notes = request.POST.get('report_notes', '').strip()
        report_number = request.POST.get('report_number')
        
        if not report_file:
            messages.error(request, 'Please select a file to upload.')
            return redirect('cases:case_detail', pk=case_id)
        
        if not report_number:
            messages.error(request, 'Report number is required.')
            return redirect('cases:case_detail', pk=case_id)
        
        try:
            report_number = int(report_number)
            if report_number < 1 or report_number > 10:
                messages.error(request, 'Report number must be between 1 and 10.')
                return redirect('cases:case_detail', pk=case_id)
        except (ValueError, TypeError):
            messages.error(request, 'Invalid report number.')
            return redirect('cases:case_detail', pk=case_id)
        
        # Check if report already exists
        existing_report = CaseReport.objects.filter(
            case=case,
            report_number=report_number
        ).first()
        
        if existing_report:
            # Update existing report
            existing_report.report_file = report_file
            existing_report.notes = report_notes
            existing_report.updated_at = timezone.now()
            existing_report.save()
            messages.success(request, f'Report #{report_number} updated successfully.')
        else:
            # Create new report
            CaseReport.objects.create(
                case=case,
                report_number=report_number,
                report_file=report_file,
                notes=report_notes,
                assigned_to=user,
                status='completed'
            )
            messages.success(request, f'Report #{report_number} uploaded successfully.')
    
    return redirect('cases:case_detail', pk=case_id)


@login_required
def upload_technician_document(request, case_id):
    """Upload an additional document for a case (technician/admin, or members on draft cases)"""
    
    user = request.user
    case = get_object_or_404(Case, id=case_id)
    
    # Permission check
    can_upload = False
    
    if user.role in ['technician', 'administrator', 'manager']:
        # Technicians and admins can upload
        if user.role == 'technician' and case.assigned_to != user:
            # Technician must own the case
            messages.error(request, 'You can only upload documents to cases you are assigned to.')
            return redirect('cases:case_detail', pk=case_id)
        can_upload = True
    elif user.role == 'member' and case.member == user and case.status == 'draft':
        # Members can upload to their own draft cases
        can_upload = True
    
    if not can_upload:
        messages.error(request, 'You do not have permission to upload documents to this case.')
        return redirect('cases:case_detail', pk=case_id)
    
    if request.method == 'POST':
        document_file = request.FILES.get('document_file')
        document_notes = request.POST.get('document_notes', '').strip()
        
        if not document_file:
            messages.error(request, 'Please select a file to upload.')
            return redirect('cases:case_detail', pk=case_id)
        
        from cases.models import CaseDocument
        
        # Append employee last name to filename
        import os
        fed_last_name = case.employee_last_name
        filename_with_employee = f"{fed_last_name}_{document_file.name}"
        
        # For members uploading to draft cases, use 'fact_finder' type
        # For technicians, use 'report' type
        doc_type = 'fact_finder' if user.role == 'member' else 'report'
        
        CaseDocument.objects.create(
            case=case,
            document_type=doc_type,
            original_filename=filename_with_employee,
            file_size=document_file.size,
            uploaded_by=user,
            file=document_file,
            notes=document_notes,
        )
        
        # Show updated document count
        from cases.services.document_count_service import get_document_count_message
        doc_count_msg = get_document_count_message(case, include_breakdown=True)
        messages.success(request, f'Document uploaded successfully. {doc_count_msg}')
    
    return redirect('cases:case_detail', pk=case_id)


@login_required
def validate_case_completion(request, case_id):
    """Validate if a case can be marked as completed (returns errors before confirmation)"""
    
    user = request.user
    case = get_object_or_404(Case, id=case_id)
    
    # Permission check - only techs and admins can mark as completed
    if user.role not in ['technician', 'administrator', 'manager']:
        return JsonResponse({'valid': False, 'error': 'You do not have permission to mark this case as completed.'}, status=403)
    
    # Check if technician owns the case
    if user.role == 'technician' and case.assigned_to != user:
        return JsonResponse({'valid': False, 'error': 'You can only mark cases you are assigned to as completed.'}, status=403)
    
    # Check if ALL requested reports have been uploaded
    from cases.models import CaseReport
    uploaded_report_numbers = set(CaseReport.objects.filter(case=case).values_list('report_number', flat=True))
    required_report_numbers = set(range(1, case.num_reports_requested + 1))
    
    if uploaded_report_numbers != required_report_numbers:
        missing_reports = required_report_numbers - uploaded_report_numbers
        missing_str = ', '.join(str(r) for r in sorted(missing_reports))
        # Allow override - return warning but allow technician to proceed
        return JsonResponse({
            'valid': False,
            'canOverride': True,
            'error': f'All {case.num_reports_requested} reports must be uploaded. Missing: Report {missing_str}',
            'warning': f'This case was requested with {case.num_reports_requested} reports, but only {len(uploaded_report_numbers)} report(s) have been submitted. Would you like to proceed with completion anyway?'
        }, status=200)  # Return 200 instead of 400 since this is overridable
    
    # All validations passed
    return JsonResponse({'valid': True, 'message': f'Case {case.external_case_id} is ready to be marked as completed.'})


@login_required
def mark_case_completed(request, case_id):
    """Mark a case as completed with optional delay before member visibility (technician/admin only)"""
    
    user = request.user
    case = get_object_or_404(Case, id=case_id)
    
    # Permission check - only techs and admins can mark as completed
    if user.role not in ['technician', 'administrator', 'manager']:
        return JsonResponse({'success': False, 'error': 'You do not have permission to mark this case as completed.'}, status=403)
    
    # Check if technician owns the case
    if user.role == 'technician' and case.assigned_to != user:
        return JsonResponse({'success': False, 'error': 'You can only mark cases you are assigned to as completed.'}, status=403)
    
    # Check if ALL requested reports have been uploaded
    from cases.models import CaseReport
    uploaded_report_numbers = set(CaseReport.objects.filter(case=case).values_list('report_number', flat=True))
    required_report_numbers = set(range(1, case.num_reports_requested + 1))
    
    # Parse request body once
    try:
        body_data = json.loads(request.body) if request.body else {}
    except json.JSONDecodeError:
        body_data = {}
    
    override_incomplete = body_data.get('override_incomplete', False)
    
    if uploaded_report_numbers != required_report_numbers and not override_incomplete:
        missing_reports = required_report_numbers - uploaded_report_numbers
        missing_str = ', '.join(str(r) for r in sorted(missing_reports))
        return JsonResponse({
            'success': False, 
            'error': f'All {case.num_reports_requested} reports must be uploaded. Missing: Report {missing_str}'
        }, status=400)
    
    if request.method == 'POST':
        try:
            from datetime import timedelta, date
            from cases.services.timezone_service import calculate_release_time_cst, convert_to_scheduled_date_cst, get_delay_label
            from core.models import SystemSettings
            
            case.status = 'completed'
            
            # Get completion delay option (hours: 0-5, or use default from settings)
            completion_delay_hours = body_data.get('completion_delay_hours')
            
            if completion_delay_hours is None:
                # Use default from system settings
                settings = SystemSettings.get_settings()
                completion_delay_hours = settings.default_completion_delay_hours
            else:
                try:
                    completion_delay_hours = int(completion_delay_hours)
                    if completion_delay_hours < 0 or completion_delay_hours > 24:
                        completion_delay_hours = 0
                except (ValueError, TypeError):
                    completion_delay_hours = 0
            
            if completion_delay_hours == 0:
                # Immediate release and email
                case.scheduled_release_date = None
                case.actual_release_date = timezone.now()
                case.scheduled_email_date = None
                case.actual_email_sent_date = timezone.now()
                case.date_completed = timezone.now()
                release_msg = "released immediately"
            else:
                # Calculate release time in CST with delay
                release_time_cst = calculate_release_time_cst(completion_delay_hours)
                case.scheduled_release_date = convert_to_scheduled_date_cst(release_time_cst)
                case.scheduled_email_date = convert_to_scheduled_date_cst(release_time_cst)  # Tied together
                case.actual_release_date = None
                case.actual_email_sent_date = None  # Keep empty until sent
                case.date_completed = None  # Keep empty until released
                delay_label = get_delay_label(completion_delay_hours)
                release_msg = f"scheduled for release in {delay_label} (CST)"
            
            case.save()
            
            messages.success(request, f'Case marked as completed and {release_msg}.')
            return JsonResponse({
                'success': True, 
                'message': f'Case marked as completed and {release_msg}.',
                'redirect_url': str(reverse('cases:case_detail', kwargs={'pk': case_id}))
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=400)


@login_required
def mark_case_incomplete(request, case_id):
    """Mark a completed case as incomplete (reactivate it) (technician/admin only)"""
    
    user = request.user
    case = get_object_or_404(Case, id=case_id)
    
    # Permission check - only techs and admins can mark as incomplete
    if user.role not in ['technician', 'administrator', 'manager']:
        return JsonResponse({'success': False, 'error': 'You do not have permission to modify this case.'}, status=403)
    
    # Check if technician owns the case
    if user.role == 'technician' and case.assigned_to != user:
        return JsonResponse({'success': False, 'error': 'You can only modify cases you are assigned to.'}, status=403)
    
    # Check if case is actually completed
    if case.status != 'completed':
        return JsonResponse({'success': False, 'error': 'This case is not marked as completed.'}, status=400)
    
    if request.method == 'POST':
        try:
            case.status = 'pending_review'  # Revert to pending review status
            case.date_completed = None  # Clear completion date
            case.save()
            
            messages.success(request, 'Case marked as incomplete and reactivated.')
            return JsonResponse({
                'success': True, 
                'message': 'Case has been reactivated successfully.',
                'redirect_url': str(reverse('cases:case_detail', kwargs={'pk': case_id}))
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=400)


@login_required
def save_view_preference(request, view_type):
    """Save technician's dashboard view preference (all vs mine)"""
    
    user = request.user
    
    # Permission check
    if user.role not in ['technician', 'administrator', 'manager']:
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
    
    # Validate view_type
    if view_type not in ['all', 'mine']:
        return JsonResponse({'success': False, 'error': 'Invalid view type'}, status=400)
    
    if request.method == 'POST':
        try:
            from accounts.models import UserPreference
            
            # Save or update the preference
            preference, created = UserPreference.objects.update_or_create(
                user=user,
                preference_key='technician_dashboard_view',
                defaults={'preference_value': {'view': view_type}}
            )
            
            return JsonResponse({
                'success': True, 
                'message': f'View preference saved ({view_type})',
                'view': view_type
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=400)


@login_required
def get_view_preference(request):
    """Get technician's saved dashboard view preference"""
    
    user = request.user
    
    # Permission check
    if user.role not in ['technician', 'administrator', 'manager']:
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
    
    try:
        from accounts.models import UserPreference
        
        preference = UserPreference.objects.filter(
            user=user,
            preference_key='technician_dashboard_view'
        ).first()
        
        if preference:
            view_type = preference.preference_value.get('view', 'all')
        else:
            view_type = 'all'  # Default to All Cases
        
        return JsonResponse({
            'success': True, 
            'view': view_type
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@login_required
def upload_member_document_to_completed_case(request, case_id):
    """Allow members to upload supplementary documents to their cases"""
    from cases.models import CaseDocument
    import os
    
    user = request.user
    case = get_object_or_404(Case, id=case_id)
    
    # Permission check - only the member who owns the case can upload
    if user.role != 'member' or case.member != user:
        messages.error(request, 'You do not have permission to upload documents to this case.')
        return redirect('cases:case_detail', pk=case_id)
    
    # Check if case is in an appropriate status for member document upload
    # Allow uploads for: completed (resubmission), pending_review, accepted, and draft statuses
    allowed_statuses = ['draft', 'completed', 'pending_review', 'accepted']
    if case.status not in allowed_statuses:
        messages.error(request, f'You cannot upload documents to cases in {case.get_status_display()} status.')
        return redirect('cases:case_detail', pk=case_id)
    
    if request.method == 'POST':
        document_file = request.FILES.get('document_file')
        document_notes = request.POST.get('document_notes', '').strip()
        
        if not document_file:
            messages.error(request, 'Please select a file to upload.')
            return redirect('cases:case_detail', pk=case_id)
        
        # Validate file size (max 50MB)
        if document_file.size > 50 * 1024 * 1024:
            messages.error(request, 'File size exceeds 50MB limit.')
            return redirect('cases:case_detail', pk=case_id)
        
        # Append employee last name to filename
        fed_last_name = case.employee_last_name
        filename_with_employee = f"{fed_last_name}_{document_file.name}"
        
        # Create document with 'supporting' type
        CaseDocument.objects.create(
            case=case,
            document_type='supporting',  # Using 'supporting' type for member supplements
            original_filename=filename_with_employee,
            file_size=document_file.size,
            uploaded_by=user,
            file=document_file,
            notes=document_notes if document_notes else 'Member supplementary document',
        )
        
        # Show updated document count
        from cases.services.document_count_service import get_document_count_message
        doc_count_msg = get_document_count_message(case, include_breakdown=True)
        messages.success(request, f'Document uploaded successfully. {doc_count_msg} You can upload more documents before resubmitting.')
    
    return redirect('cases:case_detail', pk=case_id)


def detect_case_changes(case):
    """
    Detect if a case has changed since it was marked for resubmission.
    
    Returns: {
        'has_changes': bool,
        'changes': {
            'new_documents': int (count of new documents),
            'field_changes': dict (field name -> new value),
            'description': str (human-readable summary)
        }
    }
    """
    changes = {
        'has_changes': False,
        'changes': {
            'new_documents': 0,
            'field_changes': {},
            'description': ''
        }
    }
    
    # Get the date the case was marked for resubmission
    # Look for the most recent audit log entry showing status change to 'needs_resubmission'
    from core.models import AuditLog
    try:
        resubmission_audit = AuditLog.objects.filter(
            case=case,
            action__in=['case_rejected', 'status_changed'],
            new_value__contains='needs_resubmission'
        ).order_by('-timestamp').first()
        
        if resubmission_audit:
            rejection_date = resubmission_audit.timestamp
        else:
            # Fallback: use date_rejected if available
            rejection_date = case.date_rejected if case.date_rejected else timezone.now()
    except:
        rejection_date = case.date_rejected if case.date_rejected else timezone.now()
    
    # 1. Check for new documents uploaded since rejection
    new_documents = CaseDocument.objects.filter(
        case=case,
        uploaded_at__gte=rejection_date
    ).count()
    
    if new_documents > 0:
        changes['has_changes'] = True
        changes['changes']['new_documents'] = new_documents
    
    # 2. Check for changes to member-editable fields
    # Member-editable fields: fact_finder_data, report_notes (member-visible)
    # These would typically be modified in case_detail or update views
    
    # Check fact_finder_data for changes (would be captured in audit trail)
    try:
        fact_finder_audit = AuditLog.objects.filter(
            case=case,
            action='field_updated',
            field_name='fact_finder_data',
            timestamp__gte=rejection_date
        ).exists()
        
        if fact_finder_audit:
            changes['has_changes'] = True
            changes['changes']['field_changes']['fact_finder_data'] = 'Updated'
    except:
        pass
    
    # Generate human-readable description
    if changes['has_changes']:
        desc_parts = []
        if changes['changes']['new_documents'] > 0:
            doc_word = 'document' if changes['changes']['new_documents'] == 1 else 'documents'
            desc_parts.append(f"{changes['changes']['new_documents']} new {doc_word}")
        if changes['changes']['field_changes']:
            field_count = len(changes['changes']['field_changes'])
            field_word = 'field' if field_count == 1 else 'fields'
            desc_parts.append(f"{field_count} {field_word} updated")
        
        changes['changes']['description'] = 'Changes detected: ' + ', '.join(desc_parts)
    else:
        changes['changes']['description'] = 'No changes detected since case was rejected.'
    
    return changes


@login_required
def resubmit_case(request, case_id):
    """Allow members to resubmit completed cases with additional documentation"""
    user = request.user
    case = get_object_or_404(Case, id=case_id)
    
    # Permission check - only the member who owns the case can resubmit
    if user.role != 'member' or case.member != user:
        messages.error(request, 'You do not have permission to resubmit this case.')
        return redirect('cases:case_detail', pk=case_id)
    
    # Check if case is completed
    if case.status != 'completed':
        messages.error(request, 'Only completed cases can be resubmitted.')
        return redirect('cases:case_detail', pk=case_id)
    
    if request.method == 'POST':
        try:
            # Check if case has actually changed
            change_detection = detect_case_changes(case)
            
            if not change_detection['has_changes']:
                messages.warning(
                    request,
                    f'Cannot resubmit case {case.external_case_id}: No changes have been made to the case. '
                    f'Please upload additional documents or update case information before resubmitting.'
                )
                return redirect('cases:case_detail', pk=case_id)
            
            resubmission_notes = request.POST.get('resubmission_notes', '').strip()
            
            # Store the old status before changing
            case.previous_status = 'completed'
            
            # Update case for resubmission
            case.status = 'resubmitted'
            case.is_resubmitted = True
            case.resubmission_count = case.resubmission_count + 1
            case.resubmission_date = timezone.now()
            case.resubmission_notes = resubmission_notes
            
            # Reset completion and release dates when resubmitting
            case.date_completed = None
            case.actual_release_date = None
            case.scheduled_release_date = None
            
            case.save()
            
            # Log the resubmission with details of changes
            try:
                from core.models import AuditLog
                AuditLog.objects.create(
                    user=user,
                    case=case,
                    action='case_resubmitted',
                    description=f'Member resubmitted case. Changes: {change_detection["changes"]["description"]}',
                    old_value=f'Status: completed, Resubmission count: {case.resubmission_count - 1}',
                    new_value=f'Status: resubmitted, Resubmission count: {case.resubmission_count}'
                )
            except:
                pass  # Audit logging is optional
            
            messages.success(
                request, 
                f'Case {case.external_case_id} has been resubmitted successfully. '
                f'The assigned technician will review your submitted documents and any supplementary files you have uploaded. '
                f'{change_detection["changes"]["description"]}.'
            )
            return redirect('cases:member_dashboard')
        except Exception as e:
            logger.error(f'Error resubmitting case {case_id}: {str(e)}')
            messages.error(request, 'An error occurred while resubmitting the case. Please try again.')
            return redirect('cases:case_detail', pk=case_id)
    
    # GET request - show confirmation page with change detection
    change_detection = detect_case_changes(case)
    # Get supplementary documents uploaded since completion
    from cases.models import CaseDocument
    supplementary_docs = CaseDocument.objects.filter(
        case=case,
        uploaded_by=user,
        uploaded_at__gte=case.date_completed if case.date_completed else timezone.now()
    ).order_by('-uploaded_at')
    
    context = {
        'case': case,
        'supplementary_docs': supplementary_docs,
        'resubmission_count': case.resubmission_count + 1,
        'change_detection': change_detection,
        'has_changes': change_detection['has_changes'],
        'change_summary': change_detection['changes']['description'],
    }
    
    return render(request, 'cases/confirm_resubmit_case.html', context)


@login_required
def adjust_case_credit(request, case_id):
    """Adjust case credit value and create audit trail entry."""
    case = get_object_or_404(Case, pk=case_id)
    user = request.user
    
    # Check permissions - only technician/admin assigned to case or admin/manager
    if user not in [case.assigned_to, case.created_by]:
        if not user.is_staff or user.groups.filter(name__in=['admin', 'manager']).count() == 0:
            return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
    
    if request.method == 'POST':
        try:
            credit_value = request.POST.get('credit_value')
            reason = request.POST.get('reason', 'Manual adjustment')
            
            if not credit_value:
                return JsonResponse({'success': False, 'error': 'Credit value required'})
            
            from decimal import Decimal
            credit_value = Decimal(credit_value)
            
            # Validate range
            if credit_value < Decimal('0.5') or credit_value > Decimal('3.0'):
                return JsonResponse({'success': False, 'error': 'Credit must be between 0.5 and 3.0'})
            
            # Get current credit before update
            old_credit = case.credit_value
            
            # Update case and log
            from cases.services.credit_service import set_case_credit
            set_case_credit(case, credit_value, user, 'update', reason)
            
            messages.success(request, f'Credit value updated from {old_credit} to {credit_value}')
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': f'Credit updated to {credit_value}',
                    'new_credit': str(credit_value)
                })
            else:
                return redirect('cases:case_detail', pk=case_id)
                
        except Exception as e:
            logger.error(f'Error adjusting credit for case {case_id}: {str(e)}', exc_info=True)
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': f'Error updating credit: {str(e)}'})
            else:
                messages.error(request, f'Error updating credit: {str(e)}')
                return redirect('cases:case_detail', pk=case_id)
    
    return JsonResponse({'success': False, 'error': 'POST request required'}, status=400)


@login_required
def credit_audit_trail(request, case_id=None):
    """View credit audit trail for cases - Manager/Admin only."""
    user = request.user
    
    # Check if user is admin or manager
    if not user.is_staff and user.groups.filter(name__in=['admin', 'manager']).count() == 0:
        messages.error(request, 'You do not have permission to view credit audit trails.')
        return redirect('cases:case_list')
    
    from cases.models import CreditAuditLog
    
    if case_id:
        # Single case audit trail
        case = get_object_or_404(Case, pk=case_id)
        audit_logs = CreditAuditLog.objects.filter(case=case).order_by('-adjusted_at')
        context = {
            'case': case,
            'audit_logs': audit_logs,
            'page_title': f'Credit Audit Trail - {case.external_case_id}'
        }
        return render(request, 'cases/credit_audit_trail.html', context)
    else:
        # All cases audit trail for reporting
        audit_logs = CreditAuditLog.objects.select_related('case', 'adjusted_by').order_by('-adjusted_at')
        
        # Apply filters if provided
        filter_context = request.GET.get('context', '')
        filter_case_id = request.GET.get('case_id', '')
        filter_user = request.GET.get('user', '')
        
        if filter_context:
            audit_logs = audit_logs.filter(adjustment_context=filter_context)
        if filter_case_id:
            audit_logs = audit_logs.filter(case__external_case_id__icontains=filter_case_id)
        if filter_user:
            audit_logs = audit_logs.filter(adjusted_by__username__icontains=filter_user)
        
        # Pagination
        paginator = Paginator(audit_logs, 50)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        context = {
            'page_obj': page_obj,
            'audit_logs': page_obj.object_list,
            'filter_context': filter_context,
            'filter_case_id': filter_case_id,
            'filter_user': filter_user,
            'page_title': 'Credit Audit Trail Report'
        }
        return render(request, 'cases/credit_audit_trail_report.html', context)


# ====== CASE REVIEW & ACCEPTANCE WORKFLOW ======

@login_required
def case_review_for_acceptance(request, pk):
    """
    Review case before acceptance. Technician or admin reviews FFF, documents,
    and can adjust credit, assign tier, and select technician for assignment.
    """
    case = get_object_or_404(Case, pk=pk)
    user = request.user
    
    # Permission check: Only techs/admins/managers can review
    if user.role not in ['technician', 'administrator', 'manager']:
        return HttpResponseForbidden('Access denied. Technicians and admins only.')
    
    # Case must be in 'submitted' or 'resubmitted' status
    if case.status not in ['submitted', 'resubmitted']:
        messages.error(request, f'Case cannot be reviewed. Status: {case.get_status_display()}')
        return redirect('case_detail', pk=case.id)
    
    # Get available technicians for assignment (only those with role='technician')
    available_techs = User.objects.filter(role='technician', is_active=True).order_by('first_name')
    
    context = {
        'case': case,
        'available_techs': available_techs,
        'page_title': f'Review Case {case.external_case_id}',
    }
    
    return render(request, 'cases/case_review_and_accept.html', context)


@login_required
def accept_case(request, pk):
    """
    Accept a case and assign it to a technician.
    Updates: status → accepted, credit_value, tier, assigned_to, date_accepted
    """
    if request.method != 'POST':
        return HttpResponseForbidden('POST required.')
    
    case = get_object_or_404(Case, pk=pk)
    user = request.user
    
    # Permission check
    if user.role not in ['technician', 'administrator', 'manager']:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    try:
        # Get form data
        credit_value = request.POST.get('credit_value')
        tier = request.POST.get('tier')
        assigned_to_id = request.POST.get('assigned_to')
        
        # Validate
        if not credit_value or not tier or not assigned_to_id:
            return JsonResponse({'error': 'Missing required fields'}, status=400)
        
        # Get assigned technician
        assigned_to = get_object_or_404(User, pk=assigned_to_id, role='technician')
        
        # Update case
        case.credit_value = credit_value
        case.tier = tier
        case.assigned_to = assigned_to
        case.status = 'accepted'
        case.date_accepted = timezone.now()
        case.save()
        
        logger.info(f'Case {case.external_case_id} accepted by {user.username}. '
                   f'Assigned to {assigned_to.username}, Tier: {tier}, Credit: {credit_value}')
        
        messages.success(request, f'✓ Case {case.external_case_id} accepted and assigned to {assigned_to.get_full_name()}')
        return JsonResponse({'success': True, 'redirect': f'/cases/{case.id}/'})
        
    except User.DoesNotExist:
        logger.error(f'Technician not found: {assigned_to_id}')
        return JsonResponse({'error': 'Technician not found'}, status=404)
    except Exception as e:
        logger.error(f'Error accepting case: {str(e)}')
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def reject_case(request, pk):
    """
    Reject a case and request more information from the member.
    Status changes to 'needs_resubmission' and email sent to member.
    """
    if request.method != 'POST':
        return HttpResponseForbidden('POST required.')
    
    case = get_object_or_404(Case, pk=pk)
    user = request.user
    
    # Permission check
    if user.role not in ['technician', 'administrator', 'manager']:
        return HttpResponseForbidden('Access denied.')
    
    try:
        rejection_reason = request.POST.get('rejection_reason')
        rejection_notes = request.POST.get('rejection_notes')
        
        if not rejection_reason or not rejection_notes:
            messages.error(request, 'Please provide both a reason and detailed notes.')
            return redirect('case_review_for_acceptance', pk=case.id)
        
        # Update case
        case.status = 'needs_resubmission'
        case.rejection_reason = rejection_reason
        case.rejection_notes = rejection_notes
        case.date_rejected = timezone.now()
        case.rejected_by = user
        case.save()
        
        # Send rejection email to member
        from django.core.mail import send_mail
        from django.template.loader import render_to_string
        from django.conf import settings
        
        email_context = {
            'member': case.member,
            'case': case,
            'rejection_reason': case.get_rejection_reason_display(),
            'rejection_notes': rejection_notes,
            'case_url': f'{settings.SITE_URL}/cases/{case.id}/' if hasattr(settings, 'SITE_URL') else 'https://yoursite.com/cases/',
        }
        
        subject = f'Case {case.external_case_id} - Additional Information Needed'
        text_message = render_to_string('emails/case_rejection_notification.txt', email_context)
        html_message = render_to_string('emails/case_rejection_notification.html', email_context)
        
        send_mail(
            subject=subject,
            message=text_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[case.member.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        logger.info(f'Case {case.external_case_id} rejected by {user.username}. '
                   f'Reason: {rejection_reason}. Email sent to {case.member.email}')
        
        messages.success(request, f'✓ Case {case.external_case_id} moved to "Needs Resubmission". '
                        f'Notification sent to {case.member.get_full_name()}.')
        return redirect('case_detail', pk=case.id)
        
    except Exception as e:
        logger.error(f'Error rejecting case: {str(e)}')
        messages.error(request, f'Error: {str(e)}')
        return redirect('case_review_for_acceptance', pk=case.id)


@login_required
def reassign_case(request, pk):
    """
    Reassign an accepted case to a different technician.
    Maintains audit trail of all reassignments.
    """
    if request.method != 'POST':
        return HttpResponseForbidden('POST required.')
    
    case = get_object_or_404(Case, pk=pk)
    user = request.user
    
    # Permission check: Only admin/manager can reassign
    if user.role not in ['administrator', 'manager']:
        return JsonResponse({'error': 'Access denied. Admin/Manager only.'}, status=403)
    
    try:
        new_tech_id = request.POST.get('assigned_to')
        reason = request.POST.get('reason', 'Manual reassignment')
        
        if not new_tech_id:
            return JsonResponse({'error': 'Missing technician selection'}, status=400)
        
        new_tech = get_object_or_404(User, pk=new_tech_id, role='technician')
        old_tech = case.assigned_to
        
        # Record in audit trail
        if not isinstance(case.reassignment_history, list):
            case.reassignment_history = []
        
        case.reassignment_history.append({
            'from_tech': old_tech.username if old_tech else 'Unassigned',
            'to_tech': new_tech.username,
            'date': timezone.now().isoformat(),
            'reason': reason,
            'by_user': user.username,
        })
        
        # Update assignment
        case.assigned_to = new_tech
        case.save()
        
        logger.info(f'Case {case.external_case_id} reassigned from {old_tech.username if old_tech else "Unassigned"} '
                   f'to {new_tech.username} by {user.username}. Reason: {reason}')
        
        messages.success(request, f'✓ Case reassigned to {new_tech.get_full_name()}')
        return JsonResponse({'success': True, 'redirect': f'/cases/{case.id}/'})
        
    except User.DoesNotExist:
        return JsonResponse({'error': 'Technician not found'}, status=404)
    except Exception as e:
        logger.error(f'Error reassigning case: {str(e)}')
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def save_report_notes(request, pk):
    """
    Save report notes to member via AJAX.
    Only techs/admins/managers can save notes.
    Auto-saves as tech types in floating window.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    
    case = get_object_or_404(Case, pk=pk)
    user = request.user
    
    # Permission check: Only techs/admins/managers can save notes
    if user.role not in ['technician', 'administrator', 'manager']:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    # Case must be in appropriate status
    if case.status not in ['accepted', 'pending_review', 'completed']:
        return JsonResponse({'error': 'Cannot add notes to case in this status'}, status=400)
    
    try:
        notes_text = request.POST.get('report_notes_to_member', '').strip()
        
        # Update case notes
        case.report_notes_to_member = notes_text
        case.save()
        
        # Log the update
        logger.info(f'Report notes updated for case {case.external_case_id} by {user.username}')
        
        return JsonResponse({
            'success': True,
            'message': 'Notes saved',
            'saved_at': timezone.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f'Error saving report notes: {str(e)}')
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def upload_image_for_notes(request):
    """
    Upload image for TinyMCE editor (notes).
    Called by TinyMCE's image upload feature.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    
    user = request.user
    
    # Permission check: Only techs/admins/managers can upload images
    if user.role not in ['technician', 'administrator', 'manager']:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    try:
        # Get uploaded file
        if 'file' not in request.FILES:
            return JsonResponse({'error': 'No file provided'}, status=400)
        
        uploaded_file = request.FILES['file']
        
        # Validate file type
        allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
        if uploaded_file.content_type not in allowed_types:
            return JsonResponse({'error': 'Invalid file type. Only images allowed.'}, status=400)
        
        # Validate file size (5MB max)
        if uploaded_file.size > 5 * 1024 * 1024:
            return JsonResponse({'error': 'File too large. Max 5MB.'}, status=400)
        
        # Save file to media/notes_images/
        import uuid
        from django.core.files.storage import default_storage
        
        # Generate unique filename
        filename = f'notes_{uuid.uuid4().hex}_{uploaded_file.name}'
        file_path = f'notes_images/{filename}'
        
        # Save to storage
        path = default_storage.save(file_path, uploaded_file)
        url = default_storage.url(path)
        
        logger.info(f'Image uploaded for notes by {user.username}: {filename}')
        
        return JsonResponse({
            'location': url,
            'success': True
        })
        
    except Exception as e:
        logger.error(f'Error uploading image for notes: {str(e)}')
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def generate_report_notes_pdf(request, pk):
    """
    Generate and download report notes as PDF.
    Converts HTML notes to formatted PDF with case details.
    """
    from django.http import HttpResponse
    from weasyprint import HTML, CSS
    from io import BytesIO
    import base64
    
    case = get_object_or_404(Case, pk=pk)
    user = request.user
    
    # Permission check: User must be tech/admin/manager/or member (if released)
    can_access = False
    
    if user.role in ['technician', 'administrator', 'manager']:
        can_access = True
    elif user.role == 'member' and case.member == user:
        # Member can only access if case is completed and released
        if case.status == 'completed' and case.actual_release_date is not None:
            can_access = True
    
    if not can_access:
        return HttpResponseForbidden('Access denied')
    
    # Check if notes exist
    if not case.report_notes_to_member or case.report_notes_to_member.strip() == '':
        messages.error(request, 'No notes available for this case')
        return redirect('cases:case_detail', pk=pk)
    
    try:
        # Prepare HTML content with professional styling
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                * {{ margin: 0; padding: 0; box-sizing: border-box; }}
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    font-size: 12pt;
                    line-height: 1.6;
                    color: #333;
                    background-color: white;
                }}
                .header {{
                    background: linear-gradient(135deg, #007bff 0%, #0056b3 100%);
                    color: white;
                    padding: 30px;
                    margin-bottom: 30px;
                    border-radius: 4px;
                }}
                .header h1 {{
                    font-size: 24pt;
                    margin-bottom: 10px;
                }}
                .header p {{
                    margin: 5px 0;
                    font-size: 11pt;
                }}
                .meta-info {{
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    gap: 20px;
                    margin-bottom: 20px;
                    padding: 15px;
                    background-color: #f8f9fa;
                    border-left: 4px solid #007bff;
                }}
                .meta-item {{
                    font-size: 11pt;
                }}
                .meta-label {{
                    font-weight: bold;
                    color: #0056b3;
                    margin-bottom: 3px;
                }}
                .notes-section {{
                    margin-top: 30px;
                    padding: 20px;
                    background-color: #ffffff;
                    border: 1px solid #dee2e6;
                    border-radius: 4px;
                }}
                .notes-section h2 {{
                    font-size: 16pt;
                    color: #0056b3;
                    margin-bottom: 15px;
                    padding-bottom: 10px;
                    border-bottom: 2px solid #007bff;
                }}
                .notes-content {{
                    font-size: 11pt;
                    line-height: 1.8;
                    color: #555;
                }}
                /* Preserve TinyMCE formatting */
                .notes-content p {{ margin-bottom: 10px; }}
                .notes-content strong {{ font-weight: bold; }}
                .notes-content em {{ font-style: italic; }}
                .notes-content u {{ text-decoration: underline; }}
                .notes-content ul, .notes-content ol {{ margin-left: 20px; margin-bottom: 10px; }}
                .notes-content li {{ margin-bottom: 5px; }}
                .notes-content a {{ color: #007bff; text-decoration: underline; }}
                .notes-content img {{ max-width: 100%; height: auto; margin: 15px 0; }}
                .footer {{
                    margin-top: 40px;
                    padding-top: 20px;
                    border-top: 1px solid #dee2e6;
                    font-size: 10pt;
                    color: #999;
                    text-align: center;
                }}
                @page {{
                    margin: 0.75in;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Case Notes & Advisor Information</h1>
                <p>Generated on {timezone.now().strftime('%B %d, %Y at %I:%M %p')}</p>
            </div>
            
            <div class="meta-info">
                <div class="meta-item">
                    <div class="meta-label">Case ID:</div>
                    <div>{case.external_case_id}</div>
                </div>
                <div class="meta-item">
                    <div class="meta-label">Workshop Code:</div>
                    <div>{case.workshop_code}</div>
                </div>
                <div class="meta-item">
                    <div class="meta-label">Employee Name:</div>
                    <div>{case.employee_first_name} {case.employee_last_name}</div>
                </div>
                <div class="meta-item">
                    <div class="meta-label">Status:</div>
                    <div>{case.get_status_display()}</div>
                </div>
                <div class="meta-item">
                    <div class="meta-label">Completion Date:</div>
                    <div>{case.date_completed.strftime('%B %d, %Y') if case.date_completed else 'N/A'}</div>
                </div>
                <div class="meta-item">
                    <div class="meta-label">Report Count:</div>
                    <div>{case.num_reports_requested}</div>
                </div>
            </div>
            
            <div class="notes-section">
                <h2>Technical Notes to Advisor</h2>
                <div class="notes-content">
                    {case.report_notes_to_member}
                </div>
            </div>
            
            <div class="footer">
                <p>These notes are confidential and intended for the case advisor only.</p>
                <p>This document was automatically generated from the Advisor Portal.</p>
            </div>
        </body>
        </html>
        """
        
        # Generate PDF using weasyprint
        pdf_file = BytesIO()
        HTML(string=html_content).write_pdf(pdf_file)
        pdf_file.seek(0)
        
        # Create response
        response = HttpResponse(pdf_file.read(), content_type='application/pdf')
        filename = f'Case_{case.external_case_id}_Notes_{timezone.now().strftime("%Y%m%d")}.pdf'
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        logger.info(f'Report notes PDF generated for case {case.external_case_id} by {user.username}')
        
        return response
        
    except Exception as e:
        logger.error(f'Error generating notes PDF: {str(e)}')
        messages.error(request, f'Error generating PDF: {str(e)}')
        return redirect('cases:case_detail', pk=pk)


@login_required
def edit_case_details(request, pk):
    """
    Edit basic case details (employee name, due date, assigned tech).
    Requires tech/manager/admin role.
    Creates audit trail for all changes.
    Optional email notification to advisor.
    """
    from django.core.mail import send_mail
    from core.models import AuditLog
    
    case = get_object_or_404(Case, pk=pk)
    user = request.user
    
    # Permission check
    can_edit = False
    if user.role in ['administrator', 'manager']:
        can_edit = True
    elif user.role == 'technician':
        # Tech can edit cases assigned to them or unassigned cases
        if case.assigned_to == user or case.assigned_to is None:
            can_edit = True
    
    if not can_edit:
        return HttpResponseForbidden('Access denied')
    
    # Case must be in editable status
    if case.status not in ['draft', 'submitted', 'accepted', 'pending_review']:
        messages.error(request, 'Case cannot be edited in this status')
        return redirect('cases:case_detail', pk=pk)
    
    if request.method == 'POST':
        try:
            # Get form data
            employee_first_name = request.POST.get('employee_first_name', '').strip()
            employee_last_name = request.POST.get('employee_last_name', '').strip()
            date_due_str = request.POST.get('date_due', '')
            assigned_to_id = request.POST.get('assigned_to')
            send_notification = request.POST.get('send_notification') == 'on'
            edit_reason = request.POST.get('edit_reason', '').strip()
            
            # Validation
            if not employee_first_name or not employee_last_name:
                return JsonResponse({'error': 'Employee name is required'}, status=400)
            
            # Track changes for audit
            changes = {}
            old_values = {}
            new_values = {}
            
            # Check employee first name
            if employee_first_name != case.employee_first_name:
                changes['employee_first_name'] = True
                old_values['employee_first_name'] = case.employee_first_name
                new_values['employee_first_name'] = employee_first_name
                case.employee_first_name = employee_first_name
            
            # Check employee last name
            if employee_last_name != case.employee_last_name:
                changes['employee_last_name'] = True
                old_values['employee_last_name'] = case.employee_last_name
                new_values['employee_last_name'] = employee_last_name
                case.employee_last_name = employee_last_name
            
            # Check due date
            if date_due_str:
                from datetime import datetime
                try:
                    date_due = datetime.strptime(date_due_str, '%Y-%m-%d').date()
                    if date_due != case.date_due:
                        changes['date_due'] = True
                        old_values['date_due'] = str(case.date_due) if case.date_due else None
                        new_values['date_due'] = str(date_due)
                        case.date_due = date_due
                except ValueError:
                    return JsonResponse({'error': 'Invalid date format'}, status=400)
            
            # Check assigned technician (only if provided)
            if assigned_to_id:
                # Check if unassigning (value="0")
                if assigned_to_id == '0':
                    if case.assigned_to is not None:
                        changes['assigned_to'] = True
                        old_values['assigned_to'] = case.assigned_to.get_full_name()
                        new_values['assigned_to'] = 'Unassigned'
                        case.assigned_to = None
                else:
                    try:
                        new_tech = User.objects.get(id=assigned_to_id, role='technician')
                        if case.assigned_to != new_tech:
                            changes['assigned_to'] = True
                            old_tech_name = case.assigned_to.get_full_name() if case.assigned_to else 'Unassigned'
                            new_tech_name = new_tech.get_full_name()
                            old_values['assigned_to'] = old_tech_name
                            new_values['assigned_to'] = new_tech_name
                            case.assigned_to = new_tech
                    except User.DoesNotExist:
                        return JsonResponse({'error': 'Invalid technician'}, status=400)
            
            # If no changes, return early
            if not changes:
                messages.info(request, 'No changes were made')
                return redirect('cases:case_detail', pk=pk)
            
            # Save case
            case.save()
            
            # Create audit log entry
            audit_details = {
                'changes': changes,
                'old_values': old_values,
                'new_values': new_values,
                'reason': edit_reason if edit_reason else 'Corrected case details',
                'notification_sent': send_notification
            }
            
            AuditLog.objects.create(
                user=user,
                action_type='case_details_edited',
                case=case,
                details=audit_details
            )
            
            logger.info(f'Case {case.external_case_id} details edited by {user.username}. Changes: {changes}')
            
            # Send optional notification email
            if send_notification and case.member:
                try:
                    subject = f'Case {case.external_case_id} Details Updated'
                    
                    # Build change summary
                    change_list = []
                    if 'employee_first_name' in changes:
                        change_list.append(f"Employee First Name: '{old_values['employee_first_name']}' → '{new_values['employee_first_name']}'")
                    if 'employee_last_name' in changes:
                        change_list.append(f"Employee Last Name: '{old_values['employee_last_name']}' → '{new_values['employee_last_name']}'")
                    if 'date_due' in changes:
                        change_list.append(f"Due Date: {old_values['date_due']} → {new_values['date_due']}")
                    if 'assigned_to' in changes:
                        change_list.append(f"Assigned To: {old_values['assigned_to']} → {new_values['assigned_to']}")
                    
                    change_summary = '\n'.join([f"  • {item}" for item in change_list])
                    
                    message = f"""Dear {case.member.first_name},

Your case {case.external_case_id} has been updated with the following corrections:

{change_summary}

Reason for Update: {edit_reason if edit_reason else 'Corrected case details'}

Edited by: {user.get_full_name()}
Date: {timezone.now().strftime('%B %d, %Y at %I:%M %p')}

If you have any questions about these changes, please contact your benefits administrator.

Best regards,
Advisor Portal System"""
                    
                    send_mail(
                        subject,
                        message,
                        'noreply@profeds.com',
                        [case.member.email],
                        fail_silently=False
                    )
                    
                    logger.info(f'Case edit notification email sent to {case.member.email}')
                    
                except Exception as e:
                    logger.error(f'Error sending case edit notification: {str(e)}')
                    # Don't fail the operation if email fails
                    messages.warning(request, 'Changes saved but notification email failed to send')
            
            messages.success(request, 'Case details updated successfully')
            return redirect('cases:case_detail', pk=pk)
            
        except Exception as e:
            logger.error(f'Error editing case details: {str(e)}')
            return JsonResponse({'error': str(e)}, status=500)
    
    # GET request - return form data for modal
    available_techs = User.objects.filter(role='technician').order_by('first_name', 'last_name')
    
    context = {
        'case': case,
        'available_techs': available_techs,
        'can_edit': can_edit,
    }
    
    return render(request, 'cases/edit_case_details_modal.html', context)


@login_required
def case_audit_history(request, case_id):
    """
    Display detailed audit history for a specific case.
    Visible to managers and administrators only.
    Shows all changes made to the case in chronological order.
    """
    from core.models import AuditLog
    from django.db.models import Q
    
    user = request.user
    case = get_object_or_404(Case, pk=case_id)
    
    # Permission check - Manager/Admin only
    if user.role not in ['manager', 'administrator']:
        return HttpResponseForbidden('Access denied. Managers and administrators only.')
    
    # Get all audit logs related to this case
    audit_logs = AuditLog.objects.filter(
        Q(case=case) | Q(document__case=case)
    ).select_related('user', 'case', 'document', 'related_user').order_by('-timestamp')
    
    # Apply action type filter if provided
    action_filter = request.GET.get('action', '')
    if action_filter:
        audit_logs = audit_logs.filter(action_type=action_filter)
    
    # Apply date range filter if provided
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    if date_from:
        try:
            from datetime import datetime
            from_date = datetime.strptime(date_from, '%Y-%m-%d').date()
            audit_logs = audit_logs.filter(timestamp__date__gte=from_date)
        except ValueError:
            pass
    
    if date_to:
        try:
            from datetime import datetime
            to_date = datetime.strptime(date_to, '%Y-%m-%d').date()
            audit_logs = audit_logs.filter(timestamp__date__lte=to_date)
        except ValueError:
            pass
    
    # Get all unique action types for this case for the filter dropdown
    case_action_types = AuditLog.objects.filter(
        Q(case=case) | Q(document__case=case)
    ).values_list('action_type', flat=True).distinct()
    
    action_choices = dict(AuditLog.ACTION_CHOICES)
    available_actions = [(action, action_choices.get(action, action)) for action in sorted(case_action_types)]
    
    # Pagination
    paginator = Paginator(audit_logs, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'case': case,
        'page_obj': page_obj,
        'audit_logs': page_obj.object_list,
        'available_actions': available_actions,
        'action_filter': action_filter,
        'date_from': date_from,
        'date_to': date_to,
        'total_entries': paginator.count,
    }
    
    return render(request, 'cases/case_audit_history.html', context)


@login_required
def audit_log_dashboard(request):
    """
    Global audit log dashboard for system-wide audit trail analysis.
    Visible to managers and administrators only.
    Provides comprehensive filtering by case, action, user, and date range.
    """
    from core.models import AuditLog
    from django.db.models import Q
    
    user = request.user
    
    # Permission check - Manager/Admin only
    if user.role not in ['manager', 'administrator']:
        return HttpResponseForbidden('Access denied. Managers and administrators only.')
    
    # Start with all audit logs
    audit_logs = AuditLog.objects.select_related('user', 'case', 'document', 'related_user').order_by('-timestamp')
    
    # Apply filters
    search_query = request.GET.get('search', '').strip()
    action_filter = request.GET.get('action', '').strip()
    user_filter = request.GET.get('user', '').strip()
    date_from = request.GET.get('date_from', '').strip()
    date_to = request.GET.get('date_to', '').strip()
    case_status = request.GET.get('case_status', '').strip()
    
    # Remove 'None' string values that might come from the form
    if search_query == 'None':
        search_query = ''
    if case_status == 'None':
        case_status = ''
    
    # Search filter (case ID, employee name, case description)
    if search_query and search_query != 'None':
        audit_logs = audit_logs.filter(
            Q(case__external_case_id__icontains=search_query) |
            Q(case__employee_first_name__icontains=search_query) |
            Q(case__employee_last_name__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    # Action type filter
    if action_filter:
        audit_logs = audit_logs.filter(action_type=action_filter)
    
    # User filter
    if user_filter:
        audit_logs = audit_logs.filter(user__username__icontains=user_filter)
    
    # Date range filter
    if date_from:
        try:
            from datetime import datetime
            from_date = datetime.strptime(date_from, '%Y-%m-%d').date()
            audit_logs = audit_logs.filter(timestamp__date__gte=from_date)
        except ValueError:
            pass
    
    if date_to:
        try:
            from datetime import datetime
            to_date = datetime.strptime(date_to, '%Y-%m-%d').date()
            audit_logs = audit_logs.filter(timestamp__date__lte=to_date)
        except ValueError:
            pass
    
    # Case status filter - only apply if value is valid
    if case_status and case_status != 'None':
        audit_logs = audit_logs.filter(case__status=case_status)
    
    # Get all unique values for filter dropdowns
    action_choices_dict = dict(AuditLog.ACTION_CHOICES)
    all_actions = AuditLog.objects.values_list('action_type', flat=True).distinct()
    available_actions = [(action, action_choices_dict.get(action, action)) for action in sorted(all_actions)]
    
    all_users = AuditLog.objects.filter(user__isnull=False).values_list('user', flat=True).distinct()
    # Filter out None values that might be in the list
    valid_user_ids = [uid for uid in all_users if uid is not None]
    available_users = User.objects.filter(id__in=valid_user_ids).order_by('username') if valid_user_ids else []
    
    # Get case status choices from the Case model
    case_status_choices = dict(Case._meta.get_field('status').choices)
    case_statuses = Case.objects.values_list('status', flat=True).distinct()
    available_case_statuses = [(status, case_status_choices.get(status, status)) for status in sorted(case_statuses) if status]
    
    # Pagination
    paginator = Paginator(audit_logs, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get active filters count for display
    active_filters = sum([
        bool(search_query),
        bool(action_filter),
        bool(user_filter),
        bool(date_from),
        bool(date_to),
        bool(case_status),
    ])
    
    context = {
        'page_obj': page_obj,
        'audit_logs': page_obj.object_list,
        'available_actions': available_actions,
        'available_users': available_users,
        'available_case_statuses': available_case_statuses,
        'search_query': search_query,
        'action_filter': action_filter,
        'user_filter': user_filter,
        'date_from': date_from,
        'date_to': date_to,
        'case_status': case_status,
        'active_filters': active_filters,
        'total_entries': paginator.count,
    }

    return render(request, 'cases/audit_log_dashboard.html', context)


# Column Visibility Configuration
DASHBOARD_COLUMN_CONFIG = {
    'technician_dashboard': {
        'available_columns': [
            {'id': 'code', 'label': 'Code'},
            {'id': 'member', 'label': 'Member'},
            {'id': 'employee', 'label': 'Employee Name'},
            {'id': 'submitted', 'label': 'Submitted'},
            {'id': 'due', 'label': 'Due Date'},
            {'id': 'urgency', 'label': 'Urgency'},
            {'id': 'status', 'label': 'Status'},
            {'id': 'release_date', 'label': 'Release Date'},
            {'id': 'reports', 'label': 'Reports'},
            {'id': 'assigned_to', 'label': 'Assigned To'},
            {'id': 'date_scheduled', 'label': 'Date Scheduled'},
            {'id': 'tier', 'label': 'Tier'},
            {'id': 'reviewed_by', 'label': 'Reviewed By'},
            {'id': 'notes', 'label': 'Notes'},
            {'id': 'actions', 'label': 'Actions'},
        ],
        'default_hidden': ['reviewed_by', 'notes', 'tier', 'date_scheduled', 'reports']
    },
    'admin_dashboard': {
        'available_columns': [
            {'id': 'code', 'label': 'Code'},
            {'id': 'member', 'label': 'Member'},
            {'id': 'employee', 'label': 'Employee Name'},
            {'id': 'submitted', 'label': 'Submitted'},
            {'id': 'due', 'label': 'Due Date'},
            {'id': 'urgency', 'label': 'Urgency'},
            {'id': 'status', 'label': 'Status'},
            {'id': 'release_date', 'label': 'Release Date'},
            {'id': 'reports', 'label': 'Reports'},
            {'id': 'assigned_to', 'label': 'Assigned To'},
            {'id': 'date_scheduled', 'label': 'Date Scheduled'},
            {'id': 'tier', 'label': 'Tier'},
            {'id': 'reviewed_by', 'label': 'Reviewed By'},
            {'id': 'notes', 'label': 'Notes'},
            {'id': 'actions', 'label': 'Actions'},
        ],
        'default_hidden': ['reviewed_by', 'notes', 'tier', 'date_scheduled', 'reports']
    },
    'manager_dashboard': {
        'available_columns': [
            {'id': 'code', 'label': 'Code'},
            {'id': 'member', 'label': 'Member'},
            {'id': 'employee', 'label': 'Employee Name'},
            {'id': 'submitted', 'label': 'Submitted'},
            {'id': 'due', 'label': 'Due Date'},
            {'id': 'urgency', 'label': 'Urgency'},
            {'id': 'status', 'label': 'Status'},
            {'id': 'release_date', 'label': 'Release Date'},
            {'id': 'reports', 'label': 'Reports'},
            {'id': 'assigned_to', 'label': 'Assigned To'},
            {'id': 'date_scheduled', 'label': 'Date Scheduled'},
            {'id': 'tier', 'label': 'Tier'},
            {'id': 'reviewed_by', 'label': 'Reviewed By'},
            {'id': 'notes', 'label': 'Notes'},
            {'id': 'actions', 'label': 'Actions'},
        ],
        'default_hidden': ['notes', 'reviewed_by', 'tier']
    },
    'member_dashboard': {
        'available_columns': [
            {'id': 'workshop', 'label': 'Workshop'},
            {'id': 'employee', 'label': 'Employee Name'},
            {'id': 'reports', 'label': 'Reports'},
            {'id': 'due_date', 'label': 'Due Date'},
            {'id': 'urgency', 'label': 'Urgency'},
            {'id': 'status', 'label': 'Status'},
            {'id': 'credit', 'label': 'Credit'},
            {'id': 'submitted', 'label': 'Submitted'},
            {'id': 'accepted', 'label': 'Accepted'},
            {'id': 'completed', 'label': 'Completed'},
            {'id': 'actions', 'label': 'Actions'},
        ],
        'default_hidden': ['accepted', 'credit', 'submitted']
    }
}


def get_user_visible_columns(user, dashboard_name):
    """Get list of visible column IDs for the user on a specific dashboard"""
    from accounts.models import UserPreference
    
    # Try to get saved user preference
    try:
        pref = UserPreference.objects.get(
            user=user,
            preference_key=f'{dashboard_name}_visible_columns'
        )
        return pref.preference_value.get('visible_columns', [])
    except UserPreference.DoesNotExist:
        pass
    
    # Return default visible columns
    if dashboard_name in DASHBOARD_COLUMN_CONFIG:
        config = DASHBOARD_COLUMN_CONFIG[dashboard_name]
        all_ids = [col['id'] for col in config['available_columns']]
        hidden = config.get('default_hidden', [])
        return [col_id for col_id in all_ids if col_id not in hidden]
    
    # Fallback: all columns visible
    if dashboard_name in DASHBOARD_COLUMN_CONFIG:
        return [col['id'] for col in DASHBOARD_COLUMN_CONFIG[dashboard_name]['available_columns']]
    return []


@login_required
@require_http_methods(["POST"])
def save_column_preference(request):
    """Save user's column visibility preferences"""
    from accounts.models import UserPreference
    import json
    
    try:
        data = json.loads(request.body)
        dashboard = data.get('dashboard')
        visible_columns = data.get('visible_columns', [])
        
        if not dashboard:
            return JsonResponse({'success': False, 'error': 'Dashboard not specified'}, status=400)
        
        pref, created = UserPreference.objects.update_or_create(
            user=request.user,
            preference_key=f'{dashboard}_visible_columns',
            defaults={'preference_value': {'visible_columns': visible_columns}}
        )
        
        return JsonResponse({'success': True, 'message': 'Preferences saved'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
def get_column_config(request, dashboard_name):
    """Get column configuration for a dashboard"""
    if dashboard_name not in DASHBOARD_COLUMN_CONFIG:
        return JsonResponse({'error': 'Dashboard not found'}, status=404)
    
    config = DASHBOARD_COLUMN_CONFIG[dashboard_name]
    visible_columns = get_user_visible_columns(request.user, dashboard_name)
    
    columns = []
    for col in config['available_columns']:
        columns.append({
            'id': col['id'],
            'label': col['label'],
            'visible': col['id'] in visible_columns
        })
    
    return JsonResponse({
        'columns': columns,
        'visible_count': len(visible_columns),
        'hidden_count': len(config['available_columns']) - len(visible_columns)
    })