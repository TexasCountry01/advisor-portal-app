"""
Audit Log Views
Displays complete audit trail with filtering, searching, and export functionality
"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta
import csv

from core.models import AuditLog
from cases.models import Case
from accounts.models import User


def is_admin(user):
    """Helper function to check if user is admin"""
    return user.is_authenticated and user.role == 'administrator'


@login_required
def view_audit_log(request):
    """Display audit log with filtering and searching"""
    if not is_admin(request.user):
        messages.error(request, 'Access denied. Administrators only.')
        return redirect('home')
    
    # Get all audit logs
    audit_logs = AuditLog.objects.select_related(
        'user', 'case', 'document', 'related_user'
    ).all()
    
    # Apply filters
    user_filter = request.GET.get('user')
    action_filter = request.GET.get('action')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    case_id = request.GET.get('case_id')
    search_query = request.GET.get('search')
    
    # Filter by user
    if user_filter:
        audit_logs = audit_logs.filter(user_id=user_filter)
    
    # Filter by action type
    if action_filter:
        audit_logs = audit_logs.filter(action_type=action_filter)
    
    # Filter by date range
    if date_from:
        try:
            from_date = timezone.datetime.strptime(date_from, '%Y-%m-%d')
            from_date = timezone.make_aware(from_date)
            audit_logs = audit_logs.filter(timestamp__gte=from_date)
        except (ValueError, TypeError):
            pass
    
    if date_to:
        try:
            to_date = timezone.datetime.strptime(date_to, '%Y-%m-%d')
            # Add one day to include the entire day
            to_date = to_date + timedelta(days=1)
            to_date = timezone.make_aware(to_date)
            audit_logs = audit_logs.filter(timestamp__lt=to_date)
        except (ValueError, TypeError):
            pass
    
    # Filter by case ID
    if case_id:
        audit_logs = audit_logs.filter(case_id=case_id)
    
    # Search by username, case number, or description
    if search_query:
        audit_logs = audit_logs.filter(
            Q(user__username__icontains=search_query) |
            Q(case__id__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(user__email__icontains=search_query)
        )
    
    # Pagination
    page = request.GET.get('page', 1)
    try:
        page_num = int(page)
    except (ValueError, TypeError):
        page_num = 1
    
    per_page = 50
    total_logs = audit_logs.count()
    total_pages = (total_logs + per_page - 1) // per_page
    
    start_idx = (page_num - 1) * per_page
    end_idx = start_idx + per_page
    
    paginated_logs = audit_logs[start_idx:end_idx]
    
    # Get filter options
    users = User.objects.filter(role__in=['administrator', 'technician', 'member']).order_by('username')
    action_types = AuditLog.ACTION_CHOICES
    
    context = {
        'audit_logs': paginated_logs,
        'users': users,
        'action_types': action_types,
        'total_logs': total_logs,
        'page': page_num,
        'total_pages': total_pages,
        'per_page': per_page,
        # Current filters (for display)
        'user_filter': user_filter,
        'action_filter': action_filter,
        'date_from': date_from,
        'date_to': date_to,
        'case_id': case_id,
        'search_query': search_query,
    }
    
    return render(request, 'core/view_audit_log.html', context)


@login_required
def audit_log_detail(request, log_id):
    """Display detailed view of an audit log entry"""
    if not is_admin(request.user):
        messages.error(request, 'Access denied. Administrators only.')
        return redirect('home')
    
    try:
        audit_log = AuditLog.objects.select_related(
            'user', 'case', 'document', 'related_user'
        ).get(id=log_id)
    except AuditLog.DoesNotExist:
        messages.error(request, 'Audit log entry not found.')
        return redirect('view_audit_log')
    
    context = {
        'audit_log': audit_log,
    }
    
    return render(request, 'core/audit_log_detail.html', context)


@login_required
def export_audit_log_csv(request):
    """Export audit log in CSV format for compliance"""
    if not is_admin(request.user):
        messages.error(request, 'Access denied. Administrators only.')
        return redirect('home')
    
    # Get all audit logs (with filters applied if needed)
    audit_logs = AuditLog.objects.select_related(
        'user', 'case', 'document', 'related_user'
    ).all()
    
    # Apply same filters as view_audit_log
    user_filter = request.GET.get('user')
    action_filter = request.GET.get('action')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    case_id = request.GET.get('case_id')
    search_query = request.GET.get('search')
    
    if user_filter:
        audit_logs = audit_logs.filter(user_id=user_filter)
    if action_filter:
        audit_logs = audit_logs.filter(action_type=action_filter)
    if date_from:
        try:
            from_date = timezone.datetime.strptime(date_from, '%Y-%m-%d')
            from_date = timezone.make_aware(from_date)
            audit_logs = audit_logs.filter(timestamp__gte=from_date)
        except (ValueError, TypeError):
            pass
    if date_to:
        try:
            to_date = timezone.datetime.strptime(date_to, '%Y-%m-%d')
            to_date = to_date + timedelta(days=1)
            to_date = timezone.make_aware(to_date)
            audit_logs = audit_logs.filter(timestamp__lt=to_date)
        except (ValueError, TypeError):
            pass
    if case_id:
        audit_logs = audit_logs.filter(case_id=case_id)
    if search_query:
        audit_logs = audit_logs.filter(
            Q(user__username__icontains=search_query) |
            Q(case__id__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(user__email__icontains=search_query)
        )
    
    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="audit-log-{timezone.now().strftime("%Y%m%d-%H%M%S")}.csv"'
    
    writer = csv.writer(response)
    
    # Write header
    writer.writerow([
        'Timestamp',
        'User',
        'Action Type',
        'Description',
        'Case ID',
        'Related User',
        'IP Address',
        'Changes',
        'Metadata',
    ])
    
    # Write data rows
    for log in audit_logs:
        writer.writerow([
            log.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            log.user.username if log.user else 'System',
            log.get_action_type_display(),
            log.description,
            log.case_id or '',
            log.related_user.username if log.related_user else '',
            log.ip_address or '',
            str(log.changes),
            str(log.metadata),
        ])
    
    # Log this export action
    AuditLog.log_activity(
        user=request.user,
        action_type='export_generated',
        description=f'Audit log exported ({audit_logs.count()} entries)',
        metadata={
            'export_type': 'csv',
            'entry_count': audit_logs.count(),
            'filters': {
                'user': user_filter,
                'action': action_filter,
                'date_from': date_from,
                'date_to': date_to,
                'case_id': case_id,
                'search': search_query,
            }
        }
    )
    
    return response


@login_required
def case_audit_trail(request, case_id):
    """Display audit trail for a specific case"""
    if not request.user.is_authenticated:
        return redirect('login')
    
    # Check if user has access to this case
    try:
        case = Case.objects.get(id=case_id)
    except Case.DoesNotExist:
        messages.error(request, 'Case not found.')
        return redirect('home')
    
    # Check access - admin, assigned technician, or case creator can view audit trail
    is_authorized = (
        is_admin(request.user) or
        case.assigned_to_id == request.user.id or
        case.member_id == request.user.id or
        case.created_by_id == request.user.id
    )
    
    if not is_authorized and request.user.role != 'manager':
        messages.error(request, 'Access denied. You do not have permission to view this case audit trail.')
        return redirect('home')
    
    # Get audit logs for this case
    audit_logs = AuditLog.objects.filter(case_id=case_id).select_related(
        'user', 'related_user'
    ).order_by('-timestamp')
    
    context = {
        'case': case,
        'audit_logs': audit_logs,
    }
    
    return render(request, 'core/case_audit_trail.html', context)
