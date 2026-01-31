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
from .models import Case, CaseDocument, CaseChangeRequest, CaseMessage, UnreadMessage
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
    
    # Get all cases for this member with unread count annotation
    cases = Case.objects.filter(
        member=user
    ).prefetch_related(
        'documents',
        'unread_messages_for_users'
    ).select_related(
        'assigned_to'
    ).order_by('-date_submitted')
    
    # Apply filters BEFORE adding unread count
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
            Q(employee_last_name__icontains=search_query)
        )
    
    # Add unread message count to each case
    for case in cases:
        unread_count = UnreadMessage.objects.filter(
            case=case,
            user=user
        ).count()
        case.unread_message_count = unread_count
        if unread_count > 0:
            logger.info(f'Member dashboard: Case {case.external_case_id} has {unread_count} unread messages for {user.username}')
    
    # Convert to list to preserve the modified case objects with unread_message_count
    cases = list(cases)
    
    # Handle sorting on the list (after filters applied)
    if sort_by == 'external_case_id':
        cases = sorted(cases, key=lambda x: x.external_case_id or '')
    elif sort_by == '-external_case_id':
        cases = sorted(cases, key=lambda x: x.external_case_id or '', reverse=True)
    elif sort_by == 'date_submitted':
        cases = sorted(cases, key=lambda x: x.date_submitted or timezone.now())
    elif sort_by == '-date_submitted':
        cases = sorted(cases, key=lambda x: x.date_submitted or timezone.now(), reverse=True)
    elif sort_by == 'date_due':
        cases = sorted(cases, key=lambda x: x.date_due or timezone.now())
    elif sort_by == '-date_due':
        cases = sorted(cases, key=lambda x: x.date_due or timezone.now(), reverse=True)
    elif sort_by == 'status':
        cases = sorted(cases, key=lambda x: x.status or '')
    elif sort_by == '-status':
        cases = sorted(cases, key=lambda x: x.status or '', reverse=True)
    elif sort_by == 'urgency':
        cases = sorted(cases, key=lambda x: x.urgency or '')
    elif sort_by == '-urgency':
        cases = sorted(cases, key=lambda x: x.urgency or '', reverse=True)
    
    # Calculate statistics
    all_cases = Case.objects.filter(member=user)
    stats = {
        'total_cases': all_cases.count(),
        'draft': all_cases.filter(status='draft').count(),
        'submitted': all_cases.filter(status='submitted').count(),
        'accepted': all_cases.filter(status='accepted').count(),
        'resubmitted': all_cases.filter(status='resubmitted').count(),
        'completed': all_cases.filter(status='completed').count(),
        'rush': all_cases.filter(urgency='rush').count(),
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
        'resubmitted': cases.filter(status='resubmitted').count(),
        'pending_review': cases.filter(status='pending_review').count(),
        'completed': cases.filter(status='completed').count(),
        'rush': cases.filter(urgency='rush').count(),
    }
    
    # Add unread message count to each case
    for case in cases:
        unread_count = UnreadMessage.objects.filter(case=case, user=user).count()
        case.unread_message_count = unread_count
    
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
        'resubmitted': all_cases.filter(status='resubmitted').count(),
        'hold': all_cases.filter(status='hold').count(),
        'pending_review': all_cases.filter(status='pending_review').count(),
        'completed': all_cases.filter(status='completed').count(),
        'rush': all_cases.filter(urgency='rush').count(),
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
    rush_count = all_cases.filter(urgency='rush').count()
    total_count = all_cases.count()
    
    # Calculate percentages for progress bars
    if total_count > 0:
        submitted_pct = round((submitted_count + accepted_count) * 100 / total_count, 1)
        pending_review_pct = round(pending_review_count * 100 / total_count, 1)
        completed_pct = round(completed_count * 100 / total_count, 1)
        hold_pct = round(hold_count * 100 / total_count, 1)
    else:
        submitted_pct = pending_review_pct = completed_pct = hold_pct = 0
    
    # Calculate resubmitted count
    resubmitted_count = all_cases.filter(status='resubmitted').count()
    
    stats = {
        'total': total_count,
        'submitted': submitted_count,
        'accepted': accepted_count,
        'resubmitted': resubmitted_count,
        'hold': hold_count,
        'pending_review': pending_review_count,
        'completed': completed_count,
        'completion_rate': round((completed_count / total_count * 100) if total_count > 0 else 0, 1),
        'rush': rush_count,
        'normal': max(0, total_count - rush_count),
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
def accept_case(request, case_id):
    """Accept a submitted case - technician/admin initial review"""
    import json
    from django.http import JsonResponse
    from django.utils import timezone
    from core.models import AuditLog
    from cases.services.email_service import send_case_accepted_email, send_new_case_assigned_email
    
    user = request.user
    case = get_object_or_404(Case, id=case_id)
    
    # Permission check - only technician, manager, or admin
    if user.role not in ['technician', 'administrator', 'manager']:
        return JsonResponse({
            'success': False,
            'error': 'You do not have permission to accept cases.'
        }, status=403)
    
    # Case must be in submitted status
    if case.status != 'submitted':
        return JsonResponse({
            'success': False,
            'error': f'Only submitted cases can be accepted. Current status: {case.get_status_display()}'
        }, status=400)
    
    if request.method == 'POST':
        try:
            body_data = json.loads(request.body) if request.body else {}
            tier = body_data.get('tier')
            assigned_to_id = body_data.get('assigned_to')
            acceptance_notes = body_data.get('acceptance_notes', '').strip()
            docs_verified = body_data.get('docs_verified', 'no')
            tech_override_reason = body_data.get('tech_override_reason', '').strip()
            
            # Validation
            if not tier:
                return JsonResponse({
                    'success': False,
                    'error': 'Tier must be specified.'
                }, status=400)
            
            # Tier validation - check if accepting tech level matches tier capability
            if user.role == 'technician':
                # Tier 1 can be handled by any tech
                # Tier 2 requires level 2+ 
                # Tier 3 requires level 3
                if tier == '2' and user.user_level == 'level_1':
                    return JsonResponse({
                        'success': False,
                        'error': 'Your technician level (Level 1) cannot handle Tier 2 cases. Can be overridden with a note.'
                    }, status=400)
                if tier == '3' and user.user_level in ['level_1', 'level_2']:
                    return JsonResponse({
                        'success': False,
                        'error': f'Your technician level ({user.user_level.replace("_", " ").title()}) cannot handle Tier 3 cases. Can be overridden with a note.'
                    }, status=400)
            
            # Tier validation - check if assigned tech level matches tier capability
            assigned_tech = None
            if assigned_to_id:
                try:
                    assigned_tech = User.objects.get(id=assigned_to_id, role='technician')
                except User.DoesNotExist:
                    return JsonResponse({
                        'success': False,
                        'error': 'Invalid technician selected.'
                    }, status=400)
                
                # Check tech level against tier
                tech_level_num = {
                    'level_1': 1,
                    'level_2': 2,
                    'level_3': 3
                }.get(assigned_tech.user_level, 0)
                
                tier_num = int(tier)
                required_level_num = tier_num
                
                if tech_level_num < required_level_num:
                    # Tech level doesn't meet tier requirement
                    # Only admin can override
                    if user.role != 'administrator':
                        return JsonResponse({
                            'success': False,
                            'error': f'{assigned_tech.first_name} {assigned_tech.last_name} is Level {tech_level_num} but Tier {tier} requires Level {required_level_num}. Only administrators can override this.'
                        }, status=400)
                    
                    # Admin override: require reason
                    if not tech_override_reason:
                        return JsonResponse({
                            'success': False,
                            'error': 'Override reason is required when assigning tech with insufficient level.'
                        }, status=400)
            
            # Update case
            case.status = 'accepted'
            case.tier = tier
            case.date_accepted = timezone.now()
            case.accepted_by = user
            
            if assigned_tech:
                case.assigned_to = assigned_tech
            elif user.role == 'technician':
                # If no explicit assignment but accepting tech is a technician, 
                # they should be automatically assigned
                case.assigned_to = user
            
            case.save()
            
            # Get IP address for audit
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            ip_address = x_forwarded_for.split(',')[0] if x_forwarded_for else request.META.get('REMOTE_ADDR')
            
            # Create comprehensive audit log entry
            description = f"Case accepted as Tier {tier}"
            if case.assigned_to:
                description += f", assigned to {case.assigned_to.get_full_name() or case.assigned_to.username}"
            if tech_override_reason:
                description += f" (OVERRIDE: {tech_override_reason[:50]}...)"
            if not docs_verified or docs_verified == 'no':
                description += " (docs not verified)"
            if acceptance_notes:
                description += f" - Notes: {acceptance_notes[:100]}"
            
            # Build metadata with override info
            metadata = {
                'docs_verified': docs_verified,
                'acceptance_notes': acceptance_notes
            }
            
            if tech_override_reason:
                metadata['tech_override_reason'] = tech_override_reason
            
            AuditLog.log_activity(
                user=user,
                action_type='case_accepted',
                description=description,
                case=case,
                changes={
                    'status': ('submitted', 'accepted'),
                    'tier': (None, tier),
                    'accepted_by': (None, user.username),
                    'date_accepted': (None, timezone.now().isoformat()),
                    'assigned_to': (None, case.assigned_to.username if case.assigned_to else None)
                },
                ip_address=ip_address,
                metadata=metadata
            )
            
            # Send notification to assigned technician (if any and different from accepter)
            if case.assigned_to and case.assigned_to != user:
                try:
                    from django.core.mail import send_mail
                    from django.template.loader import render_to_string
                    
                    email_context = {
                        'case': case,
                        'accepted_by': user.get_full_name() or user.username,
                        'tier': tier,
                        'case_detail_url': f"{request.build_absolute_uri('/')}cases/{case.pk}/"
                    }
                    
                    html_message = render_to_string('cases/emails/case_accepted.html', email_context)
                    
                    send_mail(
                        subject=f'Case {case.external_case_id} - Accepted and Assigned to You',
                        message=f'Case {case.external_case_id} has been accepted as Tier {tier} and assigned to you.',
                        from_email='noreply@advisor-portal.com',
                        recipient_list=[case.assigned_to.email],
                        html_message=html_message,
                        fail_silently=True
                    )
                except Exception as e:
                    print(f"Error sending tech notification: {str(e)}")
            
            # Send notification to member
            try:
                from django.core.mail import send_mail
                from django.template.loader import render_to_string
                
                email_context = {
                    'case': case,
                    'tier': tier,
                    'member_name': case.member.get_full_name() or case.member.username,
                    'case_detail_url': f"{request.build_absolute_uri('/')}cases/{case.pk}/"
                }
                
                html_message = render_to_string('cases/emails/case_accepted_member.html', email_context)
                
                send_mail(
                    subject=f'Case {case.external_case_id} - Your Case Has Been Accepted',
                    message=f'Your case {case.external_case_id} has been received and accepted by our team.',
                    from_email='noreply@advisor-portal.com',
                    recipient_list=[case.member.email],
                    html_message=html_message,
                    fail_silently=True
                )
            except Exception as e:
                print(f"Error sending member notification: {str(e)}")
            
            return JsonResponse({
                'success': True,
                'message': f'Case {case.external_case_id} has been accepted and moved to Tier {tier}.'
            })
        
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    return JsonResponse({
        'success': False,
        'error': 'POST method required.'
    }, status=405)


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
    
    # Reset has_member_updates flag when technician/admin views the case detail
    # This happens only when technician starts working on it (opens the case detail page)
    if user.role in ['technician', 'administrator'] and case.has_member_updates:
        case.has_member_updates = False
        case.save(update_fields=['has_member_updates'])
        # Log this action
        from core.models import AuditLog
        AuditLog.objects.create(
            user=user,
            action_type='member_updates_viewed',
            case=case,
            details={
                'message': 'Technician/Admin viewed case with member updates, flag reset'
            }
        )
    
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
    
    # Get resubmitted/modification cases linked to this case
    resubmitted_cases = Case.objects.filter(original_case=case).order_by('-created_at')
    
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
        'user': user,
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
def put_case_on_hold(request, case_id):
    """
    Put a case on hold with comprehensive notification system.
    
    FUNCTIONALITY:
    - Changes case status from 'accepted' to 'hold'
    - Preserves case ownership (assigned_to unchanged)
    - Holds case INDEFINITELY until needed information is received
    - Sends email to member with hold reason
    - Creates in-app notification for member
    - Captures technician-provided reason for hold
    - Full audit trail of all actions
    - Enables member document uploads while on hold
    
    AUDIT TRAIL:
    - Logs action in AuditLog with action_type='case_held'
    - Records hold reason provided by technician
    - Tracks who initiated hold (user initiating action)
    - Creates CaseNotification record (also audited)
    
    MEMBER NOTIFICATION:
    - Email sent with case link and hold reason
    - In-app notification with reason
    - Member can upload documents while case is on hold
    - Notification marked as unread until member views dashboard
    
    SECURITY:
    - Requires permission: assigned technician, manager, or admin
    - Only cases in 'accepted' status can be placed on hold
    - Member email validation (case must have member)
    
    PARAMETERS (POST JSON):
    - reason (required): Why case is on hold (e.g., "More documents needed", "Awaiting client response")
    """
    from django.http import JsonResponse
    from cases.services.case_audit_service import hold_case
    from cases.models import CaseNotification
    from core.models import AuditLog
    from django.core.mail import send_mail
    from django.template.loader import render_to_string
    from django.utils import timezone
    
    user = request.user
    case = get_object_or_404(Case, id=case_id)
    
    # ============================================================================
    # PERMISSION CHECKS
    # ============================================================================
    
    # Technicians can only hold their own assigned cases
    if user.role == 'technician' and case.assigned_to != user:
        return JsonResponse({
            'success': False,
            'error': 'You can only put cases you are assigned to on hold.'
        }, status=403)
    
    # Only technician, manager, or admin roles can put cases on hold
    if user.role not in ['technician', 'administrator', 'manager']:
        return JsonResponse({
            'success': False,
            'error': 'You do not have permission to put this case on hold.'
        }, status=403)
    
    # Only cases in 'accepted' status can be placed on hold
    if case.status not in ['accepted']:
        return JsonResponse({
            'success': False,
            'error': f'Only cases in "Accepted" status can be put on hold. Current status: {case.get_status_display()}'
        }, status=400)
    
    if request.method == 'POST':
        try:
            # ====================================================================
            # PARSE REQUEST DATA
            # ====================================================================
            body_data = json.loads(request.body) if request.body else {}
            reason = body_data.get('reason', '').strip()
            
            # Validate hold reason provided by technician
            if not reason:
                return JsonResponse({
                    'success': False,
                    'error': 'Please provide a reason for putting the case on hold.'
                }, status=400)
            
            # ====================================================================
            # UPDATE CASE STATUS AND LOG IN AUDIT TRAIL
            # ====================================================================
            
            # Use the service to hold the case (indefinitely - no duration)
            success = hold_case(
                case=case,
                user=user,
                reason=reason,
                hold_duration_days=None  # Indefinite hold
            )
            
            if not success:
                return JsonResponse({
                    'success': False,
                    'error': 'Failed to place case on hold. Please try again.'
                }, status=500)
            
            # ====================================================================
            # CREATE IN-APP NOTIFICATION
            # ====================================================================
            
            # Only create notification if case has a member
            if case.member:
                notification = CaseNotification.objects.create(
                    case=case,
                    member=case.member,
                    notification_type='case_put_on_hold',
                    title=f'Your case {case.external_case_id} has been placed on hold',
                    message=f'Your case requires additional attention. Please see the hold reason below for details.',
                    hold_reason=reason,
                    is_read=False,
                    created_at=timezone.now()
                )
                
                # Log notification creation in audit trail
                AuditLog.objects.create(
                    case=case,
                    user=user,
                    action_type='notification_created',
                    status='case_put_on_hold',
                    description=f'In-app notification created for member ({case.member.email})',
                    details={
                        'notification_id': notification.id,
                        'notification_type': 'case_put_on_hold',
                        'hold_reason': reason,
                        'recipient': case.member.email,
                        'message': notification.message
                    }
                )
                
                # ================================================================
                # SEND EMAIL TO MEMBER
                # ================================================================
                
                try:
                    # Build absolute case detail URL
                    from django.urls import reverse
                    from django.contrib.sites.shortcuts import get_current_site
                    
                    protocol = 'https' if request.is_secure() else 'http'
                    domain = get_current_site(request).domain
                    case_detail_url = f"{protocol}://{domain}{reverse('cases:case_detail', args=[case.id])}"
                    
                    # Prepare email context
                    email_context = {
                        'member_name': case.member.get_full_name() or case.member.username,
                        'case_id': case.external_case_id,
                        'employee_name': f"{case.employee_first_name} {case.employee_last_name}",
                        'hold_reason': reason,
                        'case_detail_url': case_detail_url,
                        'app_name': 'Advisor Portal'
                    }
                    
                    # Render email content (both text and HTML)
                    email_subject = f'Action Required: Your Case {case.external_case_id} Requires Additional Information'
                    text_message = render_to_string('cases/emails/case_on_hold.txt', email_context)
                    html_message = render_to_string('cases/emails/case_on_hold.html', email_context)
                    
                    # Send email with both text and HTML versions
                    send_mail(
                        subject=email_subject,
                        message=text_message,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[case.member.email],
                        html_message=html_message,
                        fail_silently=False
                    )
                    
                    # Log successful email send in audit trail
                    AuditLog.objects.create(
                        case=case,
                        user=user,
                        action_type='email_sent',
                        status='case_put_on_hold',
                        description=f'Member notification email sent to {case.member.email}',
                        details={
                            'email_to': case.member.email,
                            'email_subject': email_subject,
                            'hold_reason': reason,
                            'notification_id': notification.id
                        }
                    )
                    
                except Exception as email_error:
                    # Log email failure but don't fail the entire operation
                    logger.error(f'Failed to send hold notification email for case {case_id}: {str(email_error)}')
                    
                    AuditLog.objects.create(
                        case=case,
                        user=user,
                        action_type='email_failed',
                        status='case_put_on_hold',
                        description=f'Failed to send member notification email to {case.member.email}',
                        details={
                            'email_to': case.member.email,
                            'error': str(email_error),
                            'notification_id': notification.id
                        }
                    )
            
            # ====================================================================
            # RETURN SUCCESS RESPONSE
            # ====================================================================
            
            return JsonResponse({
                'success': True,
                'message': f'Case {case.external_case_id} has been placed on hold. Member has been notified.',
                'new_status': case.status,
                'notification_sent': case.member is not None
            })
        
        except Exception as e:
            logger.error(f'Error putting case {case_id} on hold: {str(e)}', exc_info=True)
            return JsonResponse({
                'success': False,
                'error': f'An error occurred: {str(e)}'
            }, status=500)
    
    return JsonResponse({'success': False, 'error': 'Invalid request method.'}, status=405)


@login_required
def resume_case_from_hold(request, case_id):
    """Resume a case from hold - preserves ownership, returns to 'accepted' status"""
    from django.http import JsonResponse
    from cases.services.case_audit_service import resume_case
    from cases.services.email_service import send_case_hold_resumed_email
    
    user = request.user
    case = get_object_or_404(Case, id=case_id)
    
    # Permission check - only assigned technician, manager, or admin can resume
    if user.role == 'technician' and case.assigned_to != user:
        return JsonResponse({
            'success': False,
            'error': 'You can only resume cases you are assigned to.'
        }, status=403)
    
    if user.role not in ['technician', 'administrator', 'manager']:
        return JsonResponse({
            'success': False,
            'error': 'You do not have permission to resume this case.'
        }, status=403)
    
    # Check if case is actually on hold
    if case.status != 'hold':
        return JsonResponse({
            'success': False,
            'error': f'This case is not on hold. Current status: {case.get_status_display()}'
        }, status=400)
    
    if request.method == 'POST':
        try:
            body_data = json.loads(request.body) if request.body else {}
            reason = body_data.get('reason', '').strip()
            
            if not reason:
                return JsonResponse({
                    'success': False,
                    'error': 'Please provide a reason for resuming the case.'
                }, status=400)
            
            # Use the service to resume the case
            success = resume_case(
                case=case,
                user=user,
                reason=reason,
                previous_status='accepted'
            )
            
            # Send resume notification email to member
            if success:
                send_case_hold_resumed_email(case)
                return JsonResponse({
                    'success': True,
                    'message': f'Case {case.external_case_id} has been resumed from hold.',
                    'new_status': case.status
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'Failed to resume case from hold. Please try again.'
                }, status=500)
        
        except Exception as e:
            logger.error(f'Error resuming case {case_id} from hold: {str(e)}')
            return JsonResponse({
                'success': False,
                'error': f'An error occurred: {str(e)}'
            }, status=500)
    
    return JsonResponse({'success': False, 'error': 'Invalid request method.'}, status=405)


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
    """Edit case details (members can edit before or after submission)"""
    from django.utils import timezone
    from core.models import AuditLog
    
    user = request.user
    case = get_object_or_404(Case, pk=pk)
    
    # Permission check - only the member who owns the case can edit
    if user.role != 'member' or case.member != user:
        messages.error(request, 'You do not have permission to edit this case.')
        return redirect('cases:case_detail', pk=pk)
    
    # Members can edit before submission OR after submission (collaborative workflow)
    # Restriction: cannot edit after case is completed
    if case.status in ['completed', 'hold']:
        messages.error(request, 'Cannot edit a case in this status.')
        return redirect('cases:case_detail', pk=pk)
    
    if request.method == 'POST':
        # Track changes for audit log
        changes = []
        old_values = {}
        new_values = {}
        
        # Get form data
        urgency = request.POST.get('urgency', case.urgency)
        num_reports = request.POST.get('num_reports_requested', case.num_reports_requested)
        due_date = request.POST.get('date_due', case.date_due)
        special_notes_new = request.POST.get('special_notes', '')  # New notes only
        employee_first_name = request.POST.get('employee_first_name', case.employee_first_name)
        employee_last_name = request.POST.get('employee_last_name', case.employee_last_name)
        
        # Validate data
        try:
            num_reports = int(num_reports)
            if num_reports < 1 or num_reports > 10:
                num_reports = case.num_reports_requested
        except (ValueError, TypeError):
            num_reports = case.num_reports_requested
        
        # Validate urgency
        if urgency not in ['normal', 'rush']:
            urgency = case.urgency
        
        # Track changes
        if urgency != case.urgency:
            changes.append('urgency')
            old_values['urgency'] = case.urgency
            new_values['urgency'] = urgency
        
        if num_reports != case.num_reports_requested:
            changes.append('num_reports_requested')
            old_values['num_reports_requested'] = case.num_reports_requested
            new_values['num_reports_requested'] = num_reports
        
        if due_date != case.date_due:
            changes.append('date_due')
            old_values['date_due'] = str(case.date_due)
            new_values['date_due'] = str(due_date)
        
        if employee_first_name != case.employee_first_name:
            changes.append('employee_first_name')
            old_values['employee_first_name'] = case.employee_first_name
            new_values['employee_first_name'] = employee_first_name
        
        if employee_last_name != case.employee_last_name:
            changes.append('employee_last_name')
            old_values['employee_last_name'] = case.employee_last_name
            new_values['employee_last_name'] = employee_last_name
        
        if special_notes_new:
            changes.append('special_notes_added')
            old_values['special_notes_added'] = None
            new_values['special_notes_added'] = special_notes_new
        
        # Update case
        case.urgency = urgency
        case.num_reports_requested = num_reports
        if due_date:
            case.date_due = due_date
        # Append new notes to existing notes (don't overwrite)
        if special_notes_new:
            separator = '\n---\n' if case.special_notes else ''
            case.special_notes = f"{case.special_notes}{separator}[{timezone.now().strftime('%m/%d/%Y %I:%M %p')}] {special_notes_new}"
        
        # Set member updates flag if case is submitted/accepted/pending_review (after submission)
        if case.status in ['submitted', 'accepted', 'pending_review', 'resubmitted']:
            case.has_member_updates = True
            case.member_last_update_date = timezone.now()
        
        case.save()
        
        # Create audit log entry
        if changes:
            audit_details = {
                'changes': changes,
                'old_values': old_values,
                'new_values': new_values,
                'case_status': case.status,
                'is_post_submission': case.status in ['submitted', 'accepted', 'pending_review', 'resubmitted']
            }
            AuditLog.objects.create(
                user=user,
                action_type='case_edited_by_member',
                case=case,
                details=audit_details
            )
        
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
    
    # Permission check - technicians can reassign only if they own the case, managers and admins can always reassign
    if user.role == 'technician':
        if case.assigned_to != user:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': 'You can only reassign cases you own'}, status=403)
            messages.error(request, 'You can only reassign cases you own')
            return redirect('cases:case_detail', pk=case_id)
    elif user.role not in ['administrator', 'manager']:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
        messages.error(request, 'Permission denied')
        return redirect('cases:case_detail', pk=case_id)
    
    if request.method == 'POST':
        # Form sends 'assigned_to' parameter with technician ID
        new_technician_id = request.POST.get('assigned_to')
        reason = request.POST.get('reason', 'Manual reassignment')
        
        if not new_technician_id:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': 'No technician selected'}, status=400)
            messages.error(request, 'No technician selected')
            return redirect('cases:case_detail', pk=case_id)
        
        try:
            new_technician = User.objects.get(id=new_technician_id, role='technician')
            old_technician = case.assigned_to
            case.assigned_to = new_technician
            case.save()
            
            # Log to audit trail
            from core.models import AuditLog
            AuditLog.objects.create(
                action_type='case_reassigned',
                user=user,
                case=case,
                description=f'Case reassigned from {old_technician.username if old_technician else "Unassigned"} to {new_technician.username}. Reason: {reason}',
                changes={
                    'from_technician': old_technician.username if old_technician else 'Unassigned',
                    'to_technician': new_technician.username,
                    'reason': reason,
                    'reassigned_by': user.username
                }
            )
            
            logger.info(f'Case {case.id} reassigned from {old_technician.username if old_technician else "Unassigned"} '
                       f'to {new_technician.username} by {user.username}. Reason: {reason}')
            
            # Return JSON for AJAX requests, redirect for traditional form submissions
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True, 
                    'message': f'Case reassigned to {new_technician.get_full_name() or new_technician.username}',
                    'new_assignee': new_technician.get_full_name() or new_technician.username
                })
            else:
                messages.success(request, f'Case reassigned to {new_technician.get_full_name() or new_technician.username}')
                return redirect('cases:case_detail', pk=case_id)
                
        except User.DoesNotExist:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': 'Technician not found'}, status=404)
            messages.error(request, 'Technician not found')
            return redirect('cases:case_detail', pk=case_id)
    
    return redirect('cases:case_detail', pk=case_id)


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
            
            # OPTION 2: Check if urgency has changed since draft was created
            # Calculate current urgency based on today's date
            from datetime import timedelta, date
            today = date.today()
            default_due_date = today + timedelta(days=7)
            
            # Calculate what the urgency should be based on current date
            current_urgency = 'rush' if case.date_due < default_due_date else 'normal'
            stored_urgency = case.urgency
            
            # Check if urgency changed from normal to rush
            urgency_changed = (stored_urgency == 'normal' and current_urgency == 'rush')
            
            # If this is a check-only request (from frontend), return urgency status
            check_only = request.POST.get('check_only') == 'true'
            if check_only:
                return JsonResponse({
                    'success': True,
                    'urgency_changed': urgency_changed,
                    'stored_urgency': stored_urgency,
                    'current_urgency': current_urgency,
                    'message': 'This case is now marked as RUSH. Your due date is within 7 days. Continue?'
                })
            
            # Update case urgency to current value
            if current_urgency != stored_urgency:
                case.urgency = current_urgency
            
            # Update case status to submitted
            case.status = 'submitted'
            case.date_submitted = timezone.now()
            case.save()
            
            return JsonResponse({
                'success': True,
                'message': f'Case {case.external_case_id} has been submitted successfully',
                'redirect': reverse('cases:member_dashboard'),
                'urgency_updated': (current_urgency != stored_urgency)
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
    from cases.services.email_service import send_member_response_email, send_case_question_asked_email
    
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
                
                # Send notification emails
                if user.role == 'member' and case.assigned_to:
                    # Member responded - notify tech
                    send_member_response_email(case, case.assigned_to)
                elif user.role in ['technician', 'administrator'] and not is_internal and case.member:
                    # Tech asked question - notify member
                    send_case_question_asked_email(case, note_text)
                
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
            from cases.models import CaseReviewHistory
            
            # Determine if case requires review (Level 1 technician work)
            if case.assigned_to and case.assigned_to.user_level == 'level_1':
                # Level 1 technician work must go to pending_review status
                case.status = 'pending_review'
                # Log the submission for review in audit trail
                CaseReviewHistory.objects.create(
                    case=case,
                    original_technician=case.assigned_to,
                    review_action='submitted_for_review',
                    review_notes=f'Case submitted by Level 1 technician {case.assigned_to.username} for quality review'
                )
            else:
                # Level 2/3 technician work can go directly to completed
                case.status = 'completed'
            
            # Handle release scheduling - new datetime format or legacy hours format
            release_option = body_data.get('release_option', 'now')
            release_datetime_str = body_data.get('release_datetime')  # NEW: format "YYYY-MM-DD HH:MM"
            completion_delay_hours = body_data.get('completion_delay_hours')  # OLD: backward compatibility
            
            # Only apply release scheduling if case is actually completed (not pending review)
            if case.status == 'completed':
                if release_option == 'now' or (not release_datetime_str and not completion_delay_hours):
                    # Immediate release and email
                    case.scheduled_release_date = None
                    case.actual_release_date = timezone.now()
                    case.scheduled_email_date = None
                    case.actual_email_sent_date = timezone.now()
                    case.date_completed = timezone.now()
                    release_msg = "released immediately"
                else:
                    # Handle new datetime format (date + time in CST)
                    if release_datetime_str:
                        try:
                            from datetime import datetime
                            # Parse the datetime string "YYYY-MM-DD HH:MM"
                            release_dt_naive = datetime.strptime(release_datetime_str, '%Y-%m-%d %H:%M')
                            
                            # Create timezone-aware datetime in CST
                            import pytz
                            cst = pytz.timezone('US/Central')
                            release_dt_cst = cst.localize(release_dt_naive)
                            
                            # Convert to UTC for storage (Django ORM stores in UTC)
                            release_dt_utc = release_dt_cst.astimezone(pytz.UTC)
                            
                            # Store as date only for scheduled_release_date (matches existing schema)
                            case.scheduled_release_date = release_dt_utc.date()
                            case.scheduled_email_date = release_dt_utc.date()
                            case.actual_release_date = None
                            case.actual_email_sent_date = None
                            case.date_completed = None
                            
                            # Format for user display
                            release_date_str = release_dt_cst.strftime('%b %d, %Y at %I:%M %p %Z')
                            release_msg = f"scheduled for release on {release_date_str}"
                        except (ValueError, AttributeError) as e:
                            # If parsing fails, fall back to immediate release
                            case.scheduled_release_date = None
                            case.actual_release_date = timezone.now()
                            case.scheduled_email_date = None
                            case.actual_email_sent_date = timezone.now()
                            case.date_completed = timezone.now()
                            release_msg = "released immediately (invalid datetime format)"
                    else:
                        # Fall back to legacy hours format if provided
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
                            # Immediate release
                            case.scheduled_release_date = None
                            case.actual_release_date = timezone.now()
                            case.scheduled_email_date = None
                            case.actual_email_sent_date = timezone.now()
                            case.date_completed = timezone.now()
                            release_msg = "released immediately"
                        else:
                            # Calculate release time in CST with delay (legacy)
                            release_time_cst = calculate_release_time_cst(completion_delay_hours)
                            case.scheduled_release_date = convert_to_scheduled_date_cst(release_time_cst)
                            case.scheduled_email_date = convert_to_scheduled_date_cst(release_time_cst)
                            case.actual_release_date = None
                            case.actual_email_sent_date = None
                            case.date_completed = None
                            delay_label = get_delay_label(completion_delay_hours)
                            release_msg = f"scheduled for release in {delay_label} (CST)"
            else:
                # Case is pending_review - don't set release/completion dates yet
                case.scheduled_release_date = None
                case.actual_release_date = None
                case.scheduled_email_date = None
                case.actual_email_sent_date = None
                case.date_completed = None
                release_msg = "submitted for quality review"
            
            # Auto-assign modification cases to original technician
            if case.original_case and case.status == 'completed':
                # This is a modification case - auto-assign to original technician
                if case.original_case.assigned_to and not case.assigned_to:
                    case.assigned_to = case.original_case.assigned_to
                    logger.info(f'Auto-assigned modification case {case.external_case_id} to original technician {case.original_case.assigned_to.username}')
                    
                    # Create notification message for original technician
                    # This appears in the case messages so they know it's a modification of their original work
                    modification_note = (
                        f"**MODIFICATION CASE NOTIFICATION**\n\n"
                        f"This case has been auto-assigned to you as the original technician who worked case {case.original_case.external_case_id}. "
                        f"This is a modification of your original case that the member has resubmitted with additional information."
                    )
                    CaseMessage.objects.create(
                        case=case,
                        author=request.user,
                        message=modification_note
                    )
                    
                    # Mark as unread for the original technician
                    UnreadMessage.objects.create(
                        message=CaseMessage.objects.filter(case=case).latest('id'),
                        user=case.original_case.assigned_to,
                        case=case
                    )
            
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
    from django.utils import timezone
    from core.models import AuditLog
    import os
    
    user = request.user
    case = get_object_or_404(Case, id=case_id)
    
    # Permission check - only the member who owns the case can upload
    if user.role != 'member' or case.member != user:
        messages.error(request, 'You do not have permission to upload documents to this case.')
        return redirect('cases:case_detail', pk=case_id)
    
    # Check if case is in an appropriate status for member document upload
    # Allow uploads for: draft, submitted, accepted, pending_review, completed (resubmission), hold (member providing requested docs)
    allowed_statuses = ['draft', 'submitted', 'completed', 'pending_review', 'accepted', 'resubmitted', 'hold']
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
        doc = CaseDocument.objects.create(
            case=case,
            document_type='supporting',  # Using 'supporting' type for member supplements
            original_filename=filename_with_employee,
            file_size=document_file.size,
            uploaded_by=user,
            file=document_file,
            notes=document_notes if document_notes else 'Member supplementary document',
        )
        
        # Set member updates flag if case is after submission (submitted, accepted, pending_review, resubmitted, completed)
        if case.status in ['submitted', 'accepted', 'pending_review', 'resubmitted', 'completed']:
            case.has_member_updates = True
            case.member_last_update_date = timezone.now()
            case.save(update_fields=['has_member_updates', 'member_last_update_date'])
            
            # Create audit log entry
            AuditLog.objects.create(
                user=user,
                action_type='member_document_uploaded',
                case=case,
                details={
                    'filename': filename_with_employee,
                    'file_size': document_file.size,
                    'document_notes': document_notes,
                    'case_status': case.status,
                    'message': 'Member uploaded supplementary document'
                }
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
    from cases.services.email_service import send_case_resubmitted_email
    
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
            
            # Log the resubmission with audit trail
            from core.models import AuditLog
            AuditLog.log_activity(
                user=user,
                action_type='case_resubmitted',
                description=f'Case #{case.external_case_id} resubmitted by member. {change_detection["changes"]["description"]}',
                case=case,
                changes={
                    'old_status': 'completed',
                    'new_status': 'resubmitted',
                    'resubmission_count': case.resubmission_count,
                    'changes_made': change_detection['changes']
                },
                metadata={
                    'resubmission_reason': resubmission_notes,
                    'resubmission_sequence': case.resubmission_count
                }
            )
            
            # Send resubmission notification to assigned technician
            if case.assigned_to:
                send_case_resubmitted_email(case, case.assigned_to)
            
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
    
    # Check if user is admin or manager (check role field)
    if user.role not in ['administrator', 'manager']:
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
        # Handle both JSON and form data
        if request.content_type == 'application/json':
            import json
            data = json.loads(request.body)
            credit_value = data.get('credit_value')
            tier = data.get('tier')
            assigned_to_id = data.get('assigned_to')
        else:
            credit_value = request.POST.get('credit_value')
            tier = request.POST.get('tier')
            assigned_to_id = request.POST.get('assigned_to')
        
        # Validate - provide specific error messages
        if not credit_value:
            return JsonResponse({'error': 'Please select a credit value before accepting'}, status=400)
        if not tier:
            return JsonResponse({'error': 'Please assign a case tier before accepting'}, status=400)
        if not assigned_to_id:
            return JsonResponse({'error': 'Please assign a technician before accepting'}, status=400)
        
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
@require_http_methods(["POST"])
def add_case_message(request, pk):
    """
    Add a two-way communication message to a case.
    Available to both members and benefits-technicians.
    Visible to both parties throughout the case lifecycle.
    Creates UnreadMessage records for the recipient(s).
    """
    case = get_object_or_404(Case, pk=pk)
    user = request.user
    logger.info(f'add_case_message called: user={user.username} ({user.role}), case={case.external_case_id}')
    
    # Permission check: Only member or assigned technician can message
    is_member = (user.role == 'member' and case.member == user)
    is_technician = (user.role in ['technician', 'administrator', 'manager'] and 
                     (case.assigned_to == user or user.role in ['administrator', 'manager']))
    
    logger.info(f'Permission check: is_member={is_member}, is_technician={is_technician}')
    
    if not (is_member or is_technician):
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    try:
        message_text = request.POST.get('message', '').strip()
        
        if not message_text:
            return JsonResponse({'error': 'Message cannot be empty'}, status=400)
        
        # Create message
        msg = CaseMessage.objects.create(
            case=case,
            author=user,
            message=message_text
        )
        
        # Import CaseNotification for notification creation
        from cases.models import CaseNotification
        
        # Create UnreadMessage records for recipient(s)
        if is_member:
            # Member posted - mark as unread for the assigned technician
            if case.assigned_to:
                try:
                    um, created = UnreadMessage.objects.get_or_create(
                        message=msg,
                        user=case.assigned_to,
                        defaults={'case': case}
                    )
                    logger.info(f'Member {user.username} message on case {case.external_case_id} - Created UnreadMessage for technician {case.assigned_to.username}: {created}')
                except Exception as e:
                    logger.error(f'Error creating UnreadMessage for technician: {str(e)}')
        else:
            # Technician posted - mark as unread for the member
            if case.member:
                try:
                    um, created = UnreadMessage.objects.get_or_create(
                        message=msg,
                        user=case.member,
                        defaults={'case': case}
                    )
                    logger.info(f'Technician {user.username} message on case {case.external_case_id} - Created UnreadMessage for member {case.member.username}: {created}')
                    logger.info(f'UnreadMessage details: id={um.id}, case={um.case_id}, user={um.user_id}, message={um.message_id}')
                except Exception as e:
                    logger.error(f'Error creating UnreadMessage for member: {str(e)}')
                    import traceback
                    logger.error(traceback.format_exc())
                
                # Create CaseNotification for member
                try:
                    # Extract first 1-2 sentences from the message
                    import re
                    sentences = re.split(r'(?<=[.!?])\s+', message_text.strip())
                    preview = ' '.join(sentences[:2]) if sentences else message_text[:100]
                    # Ensure preview doesn't exceed 200 chars
                    if len(preview) > 200:
                        preview = preview[:197] + '...'
                    
                    # Get technician's first name
                    tech_first_name = user.first_name or user.username
                    
                    logger.info(f'Creating CaseNotification: title="Response from {tech_first_name}", message="{preview}"')
                    
                    notification = CaseNotification.objects.create(
                        case=case,
                        member=case.member,
                        notification_type='member_update_received',
                        title=f'Response from {tech_first_name}',
                        message=preview
                    )
                    logger.info(f'CaseNotification created successfully: {notification.id}')
                except Exception as e:
                    logger.error(f'Error creating CaseNotification for member: {str(e)}')
                    import traceback
                    logger.error(traceback.format_exc())
        
        logger.info(f'Message added to case {case.external_case_id} by {user.username}')
        
        return JsonResponse({
            'success': True,
            'message_id': msg.id,
            'author': user.get_full_name() or user.username,
            'author_role': user.role,
            'created_at': msg.created_at.isoformat(),
            'message': message_text
        })
        
    except Exception as e:
        logger.error(f'Error adding message: {str(e)}')
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def get_case_messages(request, pk):
    """
    Retrieve all messages for a case (paginated).
    Available to both member and assigned technician.
    """
    case = get_object_or_404(Case, pk=pk)
    user = request.user
    
    # Permission check: Only member or assigned technician can view messages
    is_member = (user.role == 'member' and case.member == user)
    is_technician = (user.role in ['technician', 'administrator', 'manager'] and 
                     (case.assigned_to == user or user.role in ['administrator', 'manager']))
    
    if not (is_member or is_technician):
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    try:
        # Get all messages for this case
        messages_qs = CaseMessage.objects.filter(case=case).select_related('author')
        
        # Paginate
        page = request.GET.get('page', 1)
        paginator = Paginator(messages_qs, 20)
        page_obj = paginator.get_page(page)
        
        messages_data = []
        for msg in page_obj:
            messages_data.append({
                'id': msg.id,
                'author': msg.author.get_full_name() or msg.author.username,
                'author_id': msg.author.id,
                'author_role': msg.author.role,
                'message': msg.message,
                'created_at': msg.created_at.isoformat(),
                'updated_at': msg.updated_at.isoformat(),
                'is_author': msg.author == user
            })
        
        return JsonResponse({
            'success': True,
            'messages': messages_data,
            'page': page_obj.number,
            'total_pages': paginator.num_pages,
            'total_messages': paginator.count
        })
        
    except Exception as e:
        logger.error(f'Error retrieving messages: {str(e)}')
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def mark_messages_as_read(request, pk):
    """
    Mark all messages in a case as read by the current user.
    Called when user views the case detail page.
    """
    case = get_object_or_404(Case, pk=pk)
    user = request.user
    
    # Permission check: Only member or assigned technician can mark as read
    is_member = (user.role == 'member' and case.member == user)
    is_technician = (user.role in ['technician', 'administrator', 'manager'] and 
                     (case.assigned_to == user or user.role in ['administrator', 'manager']))
    
    if not (is_member or is_technician):
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    try:
        # Delete all UnreadMessage records for this user on this case
        UnreadMessage.objects.filter(case=case, user=user).delete()
        
        logger.info(f'Messages marked as read for {user.username} on case {case.external_case_id}')
        
        return JsonResponse({
            'success': True,
            'message': 'Messages marked as read'
        })
        
    except Exception as e:
        logger.error(f'Error marking messages as read: {str(e)}')
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def get_unread_message_count(request):
    """
    Get count of unread messages for the current user across all cases.
    Used to display notification badges on dashboards.
    """
    user = request.user
    
    try:
        # Get count of unread messages per case
        unread_by_case = UnreadMessage.objects.filter(
            user=user
        ).values('case').annotate(
            count=models.Count('id')
        ).order_by('-count')
        
        # Also get total unread count
        total_unread = UnreadMessage.objects.filter(user=user).count()
        
        # Build response with case details
        unread_cases = []
        for item in unread_by_case:
            try:
                case = Case.objects.get(pk=item['case'])
                unread_cases.append({
                    'case_id': case.id,
                    'external_case_id': case.external_case_id,
                    'member_name': case.member.get_full_name() if case.member else 'Unknown',
                    'employee_name': f"{case.employee_first_name} {case.employee_last_name}",
                    'unread_count': item['count']
                })
            except Case.DoesNotExist:
                pass
        
        return JsonResponse({
            'success': True,
            'total_unread': total_unread,
            'unread_by_case': unread_cases
        })
        
    except Exception as e:
        logger.error(f'Error getting unread message count: {str(e)}')
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def request_modification(request, pk):
    """
    Member requests a modification to a completed case.
    Creates a new case linked to the original case.
    Stores the reason in the original case's messages.
    Auto-assigns new case to original technician when completed.
    """
    from cases.services.email_service import send_modification_created_email
    
    case = get_object_or_404(Case, pk=pk)
    user = request.user
    
    # Permission check: Only member can request modification
    if user.role != 'member' or case.member != user:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    # Case must be completed
    if case.status != 'completed' or not case.actual_release_date:
        return JsonResponse({'error': 'Can only request modification for completed cases'}, status=400)
    
    # Check 60-day limit
    from datetime import timedelta
    from django.utils import timezone as tz
    release_date = case.actual_release_date
    if isinstance(release_date, str):
        from django.utils.dateparse import parse_datetime
        release_date = parse_datetime(release_date)
    
    days_since_release = (tz.now().date() - release_date.date()).days
    if days_since_release > 60:
        return JsonResponse({'error': 'Modification requests are only available within 60 days of case completion'}, status=400)
    
    try:
        reason = request.POST.get('reason', '').strip()
        
        if not reason:
            return JsonResponse({'error': 'Reason is required'}, status=400)
        
        # Create new case as a copy of the original
        new_case = Case.objects.create(
            external_case_id=Case.objects.count() + 1000,  # Simplified ID generation
            workshop_code=case.workshop_code,
            member=case.member,
            created_by=user,
            employee_first_name=case.employee_first_name,
            employee_last_name=case.employee_last_name,
            client_email=case.client_email,
            num_reports_requested=case.num_reports_requested,
            urgency=case.urgency,
            status='submitted',  # Start as new submission
            original_case=case,  # Link to original case
            tier=case.tier,
            date_submitted=tz.now(),
        )
        
        logger.info(f'New modification case {new_case.external_case_id} created for case {case.external_case_id} by member {user.username}')
        
        # Store the modification request in the original case's messages
        modification_message = f"**MODIFICATION REQUESTED BY MEMBER**\n\nReason: {reason}\n\nNew case created: {new_case.external_case_id}"
        msg = CaseMessage.objects.create(
            case=case,
            author=user,
            message=modification_message
        )
        
        # Mark message as unread for assigned technician
        if case.assigned_to:
            UnreadMessage.objects.get_or_create(
                message=msg,
                user=case.assigned_to,
                case=case
            )
            # Send email notification about modification request
            send_modification_created_email(case, new_case, case.assigned_to)
        
        return JsonResponse({
            'success': True,
            'new_case_id': new_case.external_case_id,
            'new_case_pk': new_case.pk,
            'message': f'New case {new_case.external_case_id} created and linked to original case'
        })
        
    except Exception as e:
        logger.error(f'Error creating modification request: {str(e)}')
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


# ============================================================================
# QUALITY REVIEW SYSTEM VIEWS (Case Review Queue and Actions)
# ============================================================================

"""
DEPRECATED: review_queue and review_case_detail views are no longer used.
Quality review is now integrated directly into the case_detail view.
Review actions are performed inline via modals in the case detail template.

These views are kept for reference but no longer called.
"""

def review_queue(request):
    """DEPRECATED - Use technician_dashboard with pending_review filter instead"""
    messages.info(request, 'Review functionality is now integrated into the case detail view.')
    return redirect('cases:technician_dashboard')


def review_case_detail(request, case_id):
    """DEPRECATED - Use case_detail view instead"""
    return redirect('cases:case_detail', pk=case_id)


@login_required
@require_http_methods(["POST"])
def approve_case_review(request, case_id):
    """Approve a case pending quality review and mark as completed"""
    from cases.models import CaseReviewHistory
    
    user = request.user
    case = get_object_or_404(Case, id=case_id)
    
    # Permission check - only Level 2/3 technicians and admins
    if user.role == 'technician' and user.user_level not in ['level_2', 'level_3']:
        return JsonResponse({'success': False, 'error': 'You do not have permission to approve cases.'}, status=403)
    elif user.role not in ['technician', 'administrator', 'manager']:
        return JsonResponse({'success': False, 'error': 'You do not have permission to approve cases.'}, status=403)
    
    # Check if case is pending review
    if case.status != 'pending_review':
        return JsonResponse({'success': False, 'error': 'This case is not pending review.'}, status=400)
    
    try:
        review_notes = request.POST.get('review_notes', '').strip()
        
        # Mark case as completed
        case.status = 'completed'
        case.reviewed_by = user
        case.reviewed_at = timezone.now()
        case.review_status = 'approved'
        case.review_notes = review_notes
        case.date_completed = timezone.now()
        case.actual_release_date = timezone.now()
        case.actual_email_sent_date = timezone.now()
        case.save()
        
        # Create audit trail entry
        CaseReviewHistory.objects.create(
            case=case,
            reviewed_by=user,
            original_technician=case.assigned_to,
            review_action='approved',
            review_notes=review_notes
        )
        
        # Create notification for member that case is released
        from cases.models import CaseNotification
        CaseNotification.objects.create(
            case=case,
            member=case.member,
            notification_type='case_released',
            title='Your Case is Completed',
            message=f'Case {case.external_case_id} has been completed and is ready for you to review.'
        )
        
        # TODO: Send email notification to technician
        messages.success(request, f'Case {case.external_case_id} approved and marked as completed.')
        
        return JsonResponse({
            'success': True,
            'message': f'Case approved successfully',
            'redirect_url': str(reverse('cases:case_detail', kwargs={'pk': case_id}))
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def request_case_revisions(request, case_id):
    """Request revisions on a case pending quality review - returns case to assigned technician"""
    from cases.models import CaseReviewHistory
    
    user = request.user
    case = get_object_or_404(Case, id=case_id)
    
    # Permission check - only Level 2/3 technicians and admins
    if user.role == 'technician' and user.user_level not in ['level_2', 'level_3']:
        return JsonResponse({'success': False, 'error': 'You do not have permission to request revisions.'}, status=403)
    elif user.role not in ['technician', 'administrator', 'manager']:
        return JsonResponse({'success': False, 'error': 'You do not have permission to request revisions.'}, status=403)
    
    # Check if case is pending review
    if case.status != 'pending_review':
        return JsonResponse({'success': False, 'error': 'This case is not pending review.'}, status=400)
    
    try:
        revision_feedback = request.POST.get('revision_feedback', '').strip()
        
        if not revision_feedback:
            return JsonResponse({'success': False, 'error': 'Revision feedback is required.'}, status=400)
        
        # Return case to accepted status with feedback
        case.status = 'accepted'
        case.reviewed_by = user
        case.reviewed_at = timezone.now()
        case.review_status = 'revisions_requested'
        case.review_notes = revision_feedback
        case.save()
        
        # Create audit trail entry
        CaseReviewHistory.objects.create(
            case=case,
            reviewed_by=user,
            original_technician=case.assigned_to,
            review_action='revisions_requested',
            review_notes=revision_feedback
        )
        
        # TODO: Send email notification to technician with feedback
        messages.success(request, f'Revisions requested for case {case.external_case_id}.')
        
        return JsonResponse({
            'success': True,
            'message': f'Revisions requested - case returned to technician',
            'redirect_url': str(reverse('cases:case_detail', kwargs={'pk': case_id}))
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def correct_case_review(request, case_id):
    """Apply corrections to a case during quality review - mark as completed with corrections noted"""
    from cases.models import CaseReviewHistory
    
    user = request.user
    case = get_object_or_404(Case, id=case_id)
    
    # Permission check - only Level 2/3 technicians and admins
    if user.role == 'technician' and user.user_level not in ['level_2', 'level_3']:
        return JsonResponse({'success': False, 'error': 'You do not have permission to correct cases.'}, status=403)
    elif user.role not in ['technician', 'administrator', 'manager']:
        return JsonResponse({'success': False, 'error': 'You do not have permission to correct cases.'}, status=403)
    
    # Check if case is pending review
    if case.status != 'pending_review':
        return JsonResponse({'success': False, 'error': 'This case is not pending review.'}, status=400)
    
    try:
        correction_notes = request.POST.get('correction_notes', '').strip()
        
        if not correction_notes:
            return JsonResponse({'success': False, 'error': 'Correction notes are required.'}, status=400)
        
        # Mark case as completed with corrections
        case.status = 'completed'
        case.reviewed_by = user
        case.reviewed_at = timezone.now()
        case.review_status = 'corrections_needed'
        case.review_notes = correction_notes
        case.date_completed = timezone.now()
        case.actual_release_date = timezone.now()
        case.actual_email_sent_date = timezone.now()
        case.save()
        
        # Create audit trail entry
        CaseReviewHistory.objects.create(
            case=case,
            reviewed_by=user,
            original_technician=case.assigned_to,
            review_action='corrections_needed',
            review_notes=correction_notes
        )
        
        # TODO: Send email notification to technician about corrections
        messages.success(request, f'Corrections noted for case {case.external_case_id} - case marked as completed.')
        
        return JsonResponse({
            'success': True,
            'message': f'Corrections applied and case completed',
            'redirect_url': str(reverse('cases:case_detail', kwargs={'pk': case_id}))
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


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


# ============================================================================
# NOTIFICATION MANAGEMENT VIEWS - Option 3 Premium Features
# ============================================================================

@login_required
@require_http_methods(["GET"])
def get_member_notifications(request):
    """
    Get all notifications for the logged-in member.
    
    DOCUMENTATION:
    - Returns paginated list of CaseNotification records
    - Includes both read and unread notifications
    - Ordered by most recent first
    - Used for notification center on member dashboard
    - Full audit trail maintained via AuditLog
    
    SECURITY:
    - Members can only view their own notifications
    
    RESPONSE:
    - JSON with: notifications (list), total_count, unread_count, pages
    """
    from cases.models import CaseNotification
    from core.models import AuditLog
    
    user = request.user
    
    # Only members can view notifications
    if user.role != 'member':
        return JsonResponse({
            'success': False,
            'error': 'Only members can view notifications'
        }, status=403)
    
    try:
        # Get all notifications for this member
        notifications = CaseNotification.objects.filter(
            member=user
        ).select_related(
            'case'
        ).order_by('-created_at')
        
        # Get pagination
        page_num = request.GET.get('page', 1)
        paginator = Paginator(notifications, 10)  # 10 per page
        page_obj = paginator.get_page(page_num)
        
        # Count unread notifications
        unread_count = notifications.filter(is_read=False).count()
        
        # Format response
        notification_list = []
        for notif in page_obj.object_list:
            notification_list.append({
                'id': notif.id,
                'case_id': notif.case.id,
                'case_code': notif.case.external_case_id,
                'notification_type': notif.notification_type,  # Return raw type value for JS checking
                'notification_type_display': notif.get_notification_type_display(),
                'title': notif.title,
                'message': notif.message,
                'hold_reason': notif.hold_reason,
                'is_read': notif.is_read,
                'created_at': notif.created_at.strftime('%b %d, %Y %I:%M %p'),
                'read_at': notif.read_at.strftime('%b %d, %Y %I:%M %p') if notif.read_at else None
            })
        
        return JsonResponse({
            'success': True,
            'notifications': notification_list,
            'total_count': notifications.count(),
            'unread_count': unread_count,
            'current_page': page_num,
            'total_pages': paginator.num_pages
        })
    
    except Exception as e:
        logger.error(f'Error fetching notifications for member {user.id}: {str(e)}', exc_info=True)
        return JsonResponse({
            'success': False,
            'error': f'An error occurred: {str(e)}'
        }, status=500)


@login_required
@require_http_methods(["POST"])
def mark_notification_read(request, notification_id):
    """
    Mark a single notification as read.
    
    DOCUMENTATION:
    - Updates notification.is_read = True
    - Sets notification.read_at timestamp
    - Logs action in AuditLog for audit trail
    - Called when member clicks on notification or views case
    
    SECURITY:
    - Members can only mark their own notifications as read
    
    AUDIT TRAIL:
    - Logs action with action_type='notification_viewed'
    - Records notification_id and case_id
    """
    from cases.models import CaseNotification
    from core.models import AuditLog
    
    user = request.user
    
    # Only members can mark notifications as read
    if user.role != 'member':
        return JsonResponse({
            'success': False,
            'error': 'Only members can mark notifications as read'
        }, status=403)
    
    try:
        notification = get_object_or_404(CaseNotification, id=notification_id, member=user)
        
        # Mark as read if not already
        was_unread = not notification.is_read
        notification.mark_as_read()
        
        # Log in audit trail
        if was_unread:
            AuditLog.objects.create(
                case=notification.case,
                user=user,
                action_type='notification_viewed',
                status=notification.case.status,
                description=f'Member viewed notification for case {notification.case.external_case_id}',
                details={
                    'notification_id': notification.id,
                    'notification_type': notification.notification_type,
                    'read_at': notification.read_at.isoformat()
                }
            )
        
        return JsonResponse({
            'success': True,
            'message': 'Notification marked as read',
            'notification_id': notification.id,
            'read_at': notification.read_at.strftime('%b %d, %Y %I:%M %p')
        })
    
    except Exception as e:
        logger.error(f'Error marking notification {notification_id} as read: {str(e)}', exc_info=True)
        return JsonResponse({
            'success': False,
            'error': f'An error occurred: {str(e)}'
        }, status=500)


@login_required
@require_http_methods(["POST"])
def mark_all_notifications_read(request):
    """
    Mark all unread notifications as read for member.
    
    DOCUMENTATION:
    - Bulk update of all unread notifications for member
    - Sets is_read=True and read_at timestamp
    - Logs action in AuditLog for each notification
    - Called from notification center "Mark All Read" button
    
    SECURITY:
    - Members can only mark their own notifications as read
    
    AUDIT TRAIL:
    - Logs bulk action with action_type='all_notifications_viewed'
    - Records count of notifications marked as read
    """
    from cases.models import CaseNotification
    from core.models import AuditLog
    
    user = request.user
    
    # Only members can mark notifications as read
    if user.role != 'member':
        return JsonResponse({
            'success': False,
            'error': 'Only members can mark notifications as read'
        }, status=403)
    
    try:
        # Get all unread notifications for this member
        unread_notifications = CaseNotification.objects.filter(
            member=user,
            is_read=False
        )
        
        count = unread_notifications.count()
        
        # Mark all as read
        for notif in unread_notifications:
            notif.mark_as_read()
        
        # Log bulk action in audit trail
        if count > 0:
            AuditLog.objects.create(
                case=None,  # Bulk action - no specific case
                user=user,
                action_type='all_notifications_viewed',
                status='bulk',
                description=f'Member marked all {count} notifications as read',
                details={
                    'notifications_marked_read': count,
                    'timestamp': timezone.now().isoformat()
                }
            )
        
        return JsonResponse({
            'success': True,
            'message': f'Marked {count} notification(s) as read',
            'notifications_updated': count
        })
    
    except Exception as e:
        logger.error(f'Error marking all notifications as read for member {user.id}: {str(e)}', exc_info=True)
        return JsonResponse({
            'success': False,
            'error': f'An error occurred: {str(e)}'
        }, status=500)


@login_required
@require_http_methods(["GET"])
def get_hold_cases(request):
    """
    Get all cases currently on hold for the logged-in member.
    
    DOCUMENTATION:
    - Returns list of cases with status='hold'
    - Includes case details, hold reason, and assigned technician
    - Used for "Cases on Hold" section in member dashboard
    - Allows quick navigation to upload documents
    
    SECURITY:
    - Members can only view their own cases
    
    RESPONSE:
    - JSON with: cases (list), total_count
    """
    from cases.models import CaseNotification
    
    user = request.user
    
    # Only members can view their cases
    if user.role != 'member':
        return JsonResponse({
            'success': False,
            'error': 'Only members can view their cases'
        }, status=403)
    
    try:
        # Get all cases on hold for this member
        hold_cases = Case.objects.filter(
            member=user,
            status='hold'
        ).select_related(
            'assigned_to'
        ).order_by('-date_submitted')
        
        # Get latest notification for each case (contains hold reason)
        case_list = []
        for case in hold_cases:
            latest_notification = CaseNotification.objects.filter(
                case=case,
                notification_type='case_put_on_hold'
            ).order_by('-created_at').first()
            
            case_list.append({
                'id': case.id,
                'case_id': case.external_case_id,
                'employee': f"{case.employee_first_name} {case.employee_last_name}",
                'assigned_to': case.assigned_to.get_full_name() if case.assigned_to else 'Unassigned',
                'hold_reason': latest_notification.hold_reason if latest_notification else case.hold_reason or 'No reason provided',
                'hold_date': case.date_submitted.strftime('%b %d, %Y'),
                'case_detail_url': reverse('cases:case_detail', args=[case.id])
            })
        
        return JsonResponse({
            'success': True,
            'cases': case_list,
            'total_count': hold_cases.count()
        })
    
    except Exception as e:
        logger.error(f'Error fetching hold cases for member {user.id}: {str(e)}', exc_info=True)
        return JsonResponse({
            'success': False,
            'error': f'An error occurred: {str(e)}'
        }, status=500)

@login_required
def create_case_change_request(request, case_id):
    """Member creates a request to extend due date, cancel case, or add info"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'}, status=400)
    
    try:
        user = request.user
        case = get_object_or_404(Case, id=case_id)
        
        # Permission: Only member can create requests for their cases
        if case.member != user:
            return JsonResponse({'success': False, 'error': 'Not your case'}, status=403)
        
        # Can only create requests for submitted/in-progress cases (not draft or completed)
        if case.status not in ['submitted', 'accepted', 'hold', 'pending_review', 'resubmitted', 'needs_resubmission']:
            return JsonResponse({
                'success': False,
                'error': f'Cannot make requests for {case.get_status_display()} cases'
            }, status=400)
        
        # Get request details from POST
        request_type = request.POST.get('request_type')
        requested_due_date = request.POST.get('requested_due_date')
        cancellation_reason = request.POST.get('cancellation_reason')
        member_notes = request.POST.get('member_notes', '').strip()
        
        # Validate request type (additional_info is now handled by direct upload endpoint)
        if request_type not in ['due_date_extension', 'cancellation']:
            return JsonResponse({'success': False, 'error': 'Invalid request type'}, status=400)
        
        # Create the change request
        change_request = CaseChangeRequest(
            case=case,
            member=user,
            request_type=request_type,
            requested_due_date=requested_due_date if request_type == 'due_date_extension' else None,
            cancellation_reason=cancellation_reason if request_type == 'cancellation' else None,
            member_notes=member_notes,
            status='pending'
        )
        change_request.save()
        
        # Set flag on case
        case.has_member_change_request = True
        case.save()
        
        # Log to audit trail
        from core.models import AuditLog
        metadata = {
            'request_type': request_type,
            'member_notes': member_notes,
        }
        if request_type == 'due_date_extension':
            metadata['requested_due_date'] = str(requested_due_date) if requested_due_date else None
        elif request_type == 'cancellation':
            metadata['cancellation_reason'] = cancellation_reason
        
        AuditLog.log_activity(
            user=user,
            action_type='member_change_request_created',
            case=case,
            description=f'Member requested {request_type.replace("_", " ")}',
            metadata=metadata
        )
        
        logger.info(f'Member {user.id} created {request_type} request for case {case_id}')
        
        return JsonResponse({
            'success': True,
            'message': f'{change_request.get_request_type_display()} request created',
            'request_id': change_request.id
        })
    
    except Exception as e:
        logger.error(f'Error creating change request: {str(e)}', exc_info=True)
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
def approve_case_change_request(request, request_id):
    """Technician approves a member's change request"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'}, status=400)
    
    try:
        user = request.user
        change_req = get_object_or_404(CaseChangeRequest, id=request_id)
        case = change_req.case
        
        # Permission: Only techs/admins can approve
        if user.role not in ['technician', 'manager', 'administrator']:
            return JsonResponse({'success': False, 'error': 'Not authorized'}, status=403)
        
        # Can only approve pending requests
        if change_req.status != 'pending':
            return JsonResponse({
                'success': False,
                'error': f'Request is already {change_req.status}'
            }, status=400)
        
        tech_response_notes = request.POST.get('tech_response_notes', '').strip()
        
        # Update request
        change_req.status = 'approved'
        change_req.reviewed_by = user
        change_req.reviewed_at = timezone.now()
        change_req.technician_response_notes = tech_response_notes
        change_req.save()
        
        # Apply approval based on request type
        if change_req.request_type == 'due_date_extension':
            # Update due date and recalculate urgency
            old_due_date = case.date_due
            case.date_due = change_req.requested_due_date
            
            # Recalculate urgency
            from datetime import timedelta, date
            today = date.today()
            default_due_date = today + timedelta(days=7)
            case.urgency = 'rush' if case.date_due < default_due_date else 'normal'
            
            case.save()
            
            logger.info(f'Tech {user.id} approved extension: {old_due_date} → {change_req.requested_due_date}')
        
        elif change_req.request_type == 'cancellation':
            # Change case status to cancelled (new status)
            case.status = 'cancelled'
            case.save()
            
            logger.info(f'Tech {user.id} approved cancellation for case {case_id}')
        
        # Clear the change request flag if no more pending requests
        pending_count = CaseChangeRequest.objects.filter(case=case, status='pending').count()
        if pending_count == 0:
            case.has_member_change_request = False
            case.save()
        
        # Log to audit trail
        from core.models import AuditLog
        AuditLog.log_activity(
            user=user,
            action_type='member_change_request_approved',
            case=case,
            description=f'{change_req.get_request_type_display()} request approved',
            metadata={
                'request_type': change_req.request_type,
                'tech_response': tech_response_notes
            }
        )
        
        return JsonResponse({
            'success': True,
            'message': f'{change_req.get_request_type_display()} approved'
        })
    
    except Exception as e:
        logger.error(f'Error approving change request: {str(e)}', exc_info=True)
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
def deny_case_change_request(request, request_id):
    """Technician denies a member's change request"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'}, status=400)
    
    try:
        user = request.user
        change_req = get_object_or_404(CaseChangeRequest, id=request_id)
        case = change_req.case
        
        # Permission: Only techs/admins can deny
        if user.role not in ['technician', 'manager', 'administrator']:
            return JsonResponse({'success': False, 'error': 'Not authorized'}, status=403)
        
        # Can only deny pending requests
        if change_req.status != 'pending':
            return JsonResponse({
                'success': False,
                'error': f'Request is already {change_req.status}'
            }, status=400)
        
        tech_response_notes = request.POST.get('tech_response_notes', '').strip()
        
        # Update request
        change_req.status = 'denied'
        change_req.reviewed_by = user
        change_req.reviewed_at = timezone.now()
        change_req.technician_response_notes = tech_response_notes
        change_req.save()
        
        # Clear the change request flag if no more pending requests
        pending_count = CaseChangeRequest.objects.filter(case=case, status='pending').count()
        if pending_count == 0:
            case.has_member_change_request = False
            case.save()
        
        # Log to audit trail
        from core.models import AuditLog
        AuditLog.log_activity(
            user=user,
            action_type='member_change_request_denied',
            case=case,
            description=f'{change_req.get_request_type_display()} request denied',
            metadata={
                'request_type': change_req.request_type,
                'denial_reason': tech_response_notes
            }
        )
        
        logger.info(f'Tech {user.id} denied {change_req.request_type} for case {case.id}')
        
        return JsonResponse({
            'success': True,
            'message': f'{change_req.get_request_type_display()} denied'
        })
    
    except Exception as e:
        logger.error(f'Error denying change request: {str(e)}', exc_info=True)
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
def upload_member_documents(request, case_id):
    """Member uploads additional documents to their case (AJAX endpoint)"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'}, status=400)
    
    try:
        user = request.user
        case = get_object_or_404(Case, id=case_id)
        
        # Permission: Only member can upload to their cases
        if case.member != user:
            return JsonResponse({'success': False, 'error': 'Not your case'}, status=403)
        
        # Can only upload for submitted/in-progress cases
        if case.status not in ['submitted', 'accepted', 'hold', 'pending_review', 'resubmitted', 'needs_resubmission']:
            return JsonResponse({
                'success': False,
                'error': f'Cannot upload documents for {case.get_status_display()} cases'
            }, status=400)
        
        # Get file from request
        document_file = request.FILES.get('document_file')
        document_notes = request.POST.get('document_notes', '').strip()
        
        if not document_file:
            return JsonResponse({'success': False, 'error': 'No file provided'}, status=400)
        
        # Create CaseDocument record
        filename_with_employee = f"{case.employee_last_name}_{document_file.name}"
        
        doc = CaseDocument.objects.create(
            case=case,
            document_type='supporting',  # Member uploads are supporting docs
            original_filename=filename_with_employee,
            file_size=document_file.size,
            uploaded_by=user,
            file=document_file,
            notes=document_notes,
        )
        
        # Set flag to notify technician
        case.has_member_new_info = True
        case.save()
        
        # Log to audit trail
        from core.models import AuditLog
        AuditLog.log_activity(
            user=user,
            action_type='member_document_uploaded',
            case=case,
            description=f'Member uploaded document: {filename_with_employee}',
            metadata={
                'document_id': doc.id,
                'original_filename': document_file.name,
                'file_size': document_file.size,
                'notes': document_notes
            }
        )
        
        # Count total member-uploaded documents (supporting docs)
        document_count = CaseDocument.objects.filter(
            case=case,
            document_type='supporting',
            uploaded_by=user
        ).count()
        
        logger.info(f'Member {user.id} uploaded document to case {case_id}')
        
        return JsonResponse({
            'success': True,
            'message': f'✓ Document uploaded successfully',
            'document_count': document_count,
            'document_id': doc.id
        })
    
    except Exception as e:
        logger.error(f'Error uploading member document: {str(e)}', exc_info=True)
        return JsonResponse({'success': False, 'error': str(e)}, status=500)