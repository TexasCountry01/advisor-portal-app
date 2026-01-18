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
from django.core.paginator import Paginator
from datetime import timedelta
import csv

from core.models import AuditLog
from cases.models import Case
from accounts.models import User


def is_admin(user):
    """Helper function to check if user is admin or manager"""
    return user.is_authenticated and user.role in ['administrator', 'manager']


@login_required
def view_audit_log(request):
    """Display audit log with filtering and searching"""
    if not is_admin(request.user):
        messages.error(request, 'Access denied. Administrators and Managers only.')
        return redirect('home')
    
    # Get all audit logs
    audit_logs = AuditLog.objects.select_related(
        'user', 'case', 'document', 'related_user'
    ).all()
    
    # Apply filters
    user_filter = request.GET.get('user', '').strip()
    action_filter = request.GET.get('action', '').strip()
    date_from = request.GET.get('date_from', '').strip()
    date_to = request.GET.get('date_to', '').strip()
    case_id = request.GET.get('case_id', '').strip()
    search_query = request.GET.get('search', '').strip()
    
    # Remove 'None' string values
    if case_id == 'None':
        case_id = ''
    if search_query == 'None':
        search_query = ''
    if user_filter == 'None':
        user_filter = ''
    if action_filter == 'None':
        action_filter = ''
    
    # Filter by user
    if user_filter and user_filter != 'None':
        try:
            audit_logs = audit_logs.filter(user_id=int(user_filter))
        except (ValueError, TypeError):
            pass
    
    # Filter by action type
    if action_filter and action_filter != 'None':
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
    
    # Filter by case ID (only if valid integer)
    if case_id and case_id != 'None':
        try:
            audit_logs = audit_logs.filter(case_id=int(case_id))
        except (ValueError, TypeError):
            pass
    
    # Search by username, case number, or description
    if search_query and search_query != 'None':
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
    
    # Ensure page is within valid range
    if page_num < 1:
        page_num = 1
    elif page_num > total_pages and total_pages > 0:
        page_num = total_pages
    
    start_idx = (page_num - 1) * per_page
    end_idx = start_idx + per_page
    
    paginated_logs = audit_logs[start_idx:end_idx]
    
    # Generate page numbers for pagination (max 5 pages to display)
    page_numbers = []
    if total_pages <= 5:
        page_numbers = list(range(1, total_pages + 1))
    else:
        # Show first page, last page, and pages around current page
        if page_num <= 3:
            page_numbers = [1, 2, 3, 4, '...', total_pages]
        elif page_num >= total_pages - 2:
            page_numbers = [1, '...', total_pages - 3, total_pages - 2, total_pages - 1, total_pages]
        else:
            page_numbers = [1, '...', page_num - 1, page_num, page_num + 1, '...', total_pages]
    
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
        'page_numbers': page_numbers,
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
        messages.error(request, 'Access denied. Administrators and Managers only.')
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
        messages.error(request, 'Access denied. Administrators and Managers only.')
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

# ============================================================================
# NEW AUDIT REPORT VIEWS
# ============================================================================

@login_required
def activity_summary_report(request):
    """
    Generate a comprehensive activity summary report for admins/managers.
    Shows statistics about all audit activity.
    """
    if not is_admin(request.user):
        messages.error(request, 'Access denied. Administrators and Managers only.')
        return redirect('home')
    
    # Get date range from request
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    logs = AuditLog.objects.all()
    
    if date_from:
        try:
            from_date = timezone.datetime.strptime(date_from, '%Y-%m-%d')
            from_date = timezone.make_aware(from_date)
            logs = logs.filter(timestamp__gte=from_date)
        except:
            pass
    
    if date_to:
        try:
            to_date = timezone.datetime.strptime(date_to, '%Y-%m-%d')
            to_date = to_date + timedelta(days=1)
            to_date = timezone.make_aware(to_date)
            logs = logs.filter(timestamp__lt=to_date)
        except:
            pass
    
    # Generate summary statistics
    total_activities = logs.count()
    
    # Activities by type
    activity_by_type = {}
    for log in logs:
        action = log.get_action_type_display()
        activity_by_type[action] = activity_by_type.get(action, 0) + 1
    
    # Activities by user
    activity_by_user = {}
    for log in logs:
        user = log.user.username if log.user else 'System'
        activity_by_user[user] = activity_by_user.get(user, 0) + 1
    
    # Top 10 most active users
    top_users = sorted(activity_by_user.items(), key=lambda x: x[1], reverse=True)[:10]
    
    # Case-related activities
    case_activities = logs.filter(case__isnull=False).count()
    
    # User management activities
    user_mgmt = logs.filter(action_type__in=['user_created', 'user_updated', 'user_deleted', 'user_role_changed']).count()
    
    # Quality review activities
    review_activities = logs.filter(action_type__in=['review_submitted', 'review_updated']).count()
    
    context = {
        'total_activities': total_activities,
        'activity_by_type': sorted(activity_by_type.items(), key=lambda x: x[1], reverse=True)[:15],
        'top_users': top_users,
        'case_activities': case_activities,
        'user_mgmt_activities': user_mgmt,
        'review_activities': review_activities,
        'date_from': date_from,
        'date_to': date_to,
    }
    
    return render(request, 'core/activity_summary_report.html', context)


@login_required
def user_activity_report(request):
    """
    Detailed report of activities performed by a specific user.
    """
    if not is_admin(request.user):
        messages.error(request, 'Access denied. Administrators and Managers only.')
        return redirect('home')
    
    user_id = request.GET.get('user_id', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    target_user = None
    logs = AuditLog.objects.all()
    
    if user_id:
        try:
            target_user = User.objects.get(id=int(user_id))
            logs = logs.filter(user=target_user)
        except (ValueError, User.DoesNotExist):
            messages.error(request, 'User not found.')
            return redirect('core:view_audit_log')
    
    if date_from:
        try:
            from_date = timezone.datetime.strptime(date_from, '%Y-%m-%d')
            from_date = timezone.make_aware(from_date)
            logs = logs.filter(timestamp__gte=from_date)
        except:
            pass
    
    if date_to:
        try:
            to_date = timezone.datetime.strptime(date_to, '%Y-%m-%d')
            to_date = to_date + timedelta(days=1)
            to_date = timezone.make_aware(to_date)
            logs = logs.filter(timestamp__lt=to_date)
        except:
            pass
    
    # Statistics for this user
    activity_by_type = {}
    for log in logs:
        action = log.get_action_type_display()
        activity_by_type[action] = activity_by_type.get(action, 0) + 1
    
    total_activities = logs.count()
    
    # Pagination
    page = request.GET.get('page', 1)
    per_page = 30
    paginator = Paginator(logs.order_by('-timestamp'), per_page)
    
    try:
        logs_page = paginator.page(page)
    except:
        logs_page = paginator.page(1)
    
    users = User.objects.filter(role__in=['administrator', 'technician', 'manager']).order_by('username')
    
    context = {
        'target_user': target_user,
        'logs': logs_page,
        'users': users,
        'activity_by_type': sorted(activity_by_type.items(), key=lambda x: x[1], reverse=True),
        'total_activities': total_activities,
        'date_from': date_from,
        'date_to': date_to,
    }
    
    return render(request, 'core/user_activity_report.html', context)


@login_required
def case_change_history_report(request):
    """
    Report showing all changes to cases (status, tier, credit, assignments, etc.)
    """
    if not is_admin(request.user):
        messages.error(request, 'Access denied. Administrators and Managers only.')
        return redirect('home')
    
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    change_type = request.GET.get('change_type', '')  # status, tier, assignment, credit
    
    logs = AuditLog.objects.filter(case__isnull=False).select_related('user', 'case')
    
    # Filter by change type
    if change_type == 'status':
        logs = logs.filter(action_type__in=['case_status_changed', 'case_held', 'case_resumed'])
    elif change_type == 'tier':
        logs = logs.filter(action_type='case_tier_changed')
    elif change_type == 'assignment':
        logs = logs.filter(action_type__in=['case_assigned', 'case_reassigned'])
    elif change_type == 'resubmission':
        logs = logs.filter(action_type='case_resubmitted')
    
    if date_from:
        try:
            from_date = timezone.datetime.strptime(date_from, '%Y-%m-%d')
            from_date = timezone.make_aware(from_date)
            logs = logs.filter(timestamp__gte=from_date)
        except:
            pass
    
    if date_to:
        try:
            to_date = timezone.datetime.strptime(date_to, '%Y-%m-%d')
            to_date = to_date + timedelta(days=1)
            to_date = timezone.make_aware(to_date)
            logs = logs.filter(timestamp__lt=to_date)
        except:
            pass
    
    # Pagination
    page = request.GET.get('page', 1)
    per_page = 40
    paginator = Paginator(logs.order_by('-timestamp'), per_page)
    
    try:
        logs_page = paginator.page(page)
    except:
        logs_page = paginator.page(1)
    
    context = {
        'logs': logs_page,
        'total_changes': logs.count(),
        'change_type': change_type,
        'date_from': date_from,
        'date_to': date_to,
    }
    
    return render(request, 'core/case_change_history_report.html', context)


@login_required
def quality_review_audit_report(request):
    """
    Report of all quality review activities (submissions, approvals, revisions, corrections).
    """
    if not is_admin(request.user):
        messages.error(request, 'Access denied. Administrators and Managers only.')
        return redirect('home')
    
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    review_status = request.GET.get('review_status', '')  # approved, revisions_requested, corrections
    
    from cases.models import CaseReviewHistory
    reviews = CaseReviewHistory.objects.select_related('case', 'reviewed_by', 'original_technician').all()
    
    if review_status:
        action_map = {
            'approved': 'approved',
            'revisions': 'revisions_requested',
            'corrections': 'corrections_needed',
        }
        if review_status in action_map:
            reviews = reviews.filter(review_action=action_map[review_status])
    
    if date_from:
        try:
            from_date = timezone.datetime.strptime(date_from, '%Y-%m-%d')
            from_date = timezone.make_aware(from_date)
            reviews = reviews.filter(reviewed_at__gte=from_date)
        except:
            pass
    
    if date_to:
        try:
            to_date = timezone.datetime.strptime(date_to, '%Y-%m-%d')
            to_date = to_date + timedelta(days=1)
            to_date = timezone.make_aware(to_date)
            reviews = reviews.filter(reviewed_at__lt=to_date)
        except:
            pass
    
    # Statistics
    total_reviews = reviews.count()
    approved = reviews.filter(review_action='approved').count()
    revisions_requested = reviews.filter(review_action='revisions_requested').count()
    corrections = reviews.filter(review_action='corrections_needed').count()
    
    # Reviewers stats
    reviewer_stats = {}
    for review in reviews:
        if review.reviewed_by:
            reviewer = review.reviewed_by.username
            if reviewer not in reviewer_stats:
                reviewer_stats[reviewer] = {'approved': 0, 'revisions': 0, 'corrections': 0}
            
            if review.review_action == 'approved':
                reviewer_stats[reviewer]['approved'] += 1
            elif review.review_action == 'revisions_requested':
                reviewer_stats[reviewer]['revisions'] += 1
            elif review.review_action == 'corrections_needed':
                reviewer_stats[reviewer]['corrections'] += 1
    
    # Pagination
    page = request.GET.get('page', 1)
    per_page = 30
    paginator = Paginator(reviews.order_by('-reviewed_at'), per_page)
    
    try:
        reviews_page = paginator.page(page)
    except:
        reviews_page = paginator.page(1)
    
    context = {
        'reviews': reviews_page,
        'total_reviews': total_reviews,
        'approved': approved,
        'revisions_requested': revisions_requested,
        'corrections': corrections,
        'reviewer_stats': reviewer_stats,
        'review_status': review_status,
        'date_from': date_from,
        'date_to': date_to,
    }
    
    return render(request, 'core/quality_review_audit_report.html', context)


@login_required
def system_event_audit_report(request):
    """
    Report of system-level events (cron jobs, credit resets, settings changes, bulk operations).
    """
    if not is_admin(request.user):
        messages.error(request, 'Access denied. Administrators and Managers only.')
        return redirect('home')
    
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    event_type = request.GET.get('event_type', '')
    
    logs = AuditLog.objects.filter(
        action_type__in=[
            'cron_job_executed',
            'quarterly_credit_reset',
            'bulk_credit_reset',
            'settings_updated',
            'bulk_export',
            'report_generated'
        ]
    ).select_related('user').order_by('-timestamp')
    
    if event_type:
        logs = logs.filter(action_type=event_type)
    
    if date_from:
        try:
            from_date = timezone.datetime.strptime(date_from, '%Y-%m-%d')
            from_date = timezone.make_aware(from_date)
            logs = logs.filter(timestamp__gte=from_date)
        except:
            pass
    
    if date_to:
        try:
            to_date = timezone.datetime.strptime(date_to, '%Y-%m-%d')
            to_date = to_date + timedelta(days=1)
            to_date = timezone.make_aware(to_date)
            logs = logs.filter(timestamp__lt=to_date)
        except:
            pass
    
    # Pagination
    page = request.GET.get('page', 1)
    per_page = 40
    paginator = Paginator(logs, per_page)
    
    try:
        logs_page = paginator.page(page)
    except:
        logs_page = paginator.page(1)
    
    # Event type statistics
    event_stats = {}
    for log in logs:
        action = log.get_action_type_display()
        event_stats[action] = event_stats.get(action, 0) + 1
    
    context = {
        'logs': logs_page,
        'total_events': logs.count(),
        'event_stats': event_stats,
        'event_type': event_type,
        'date_from': date_from,
        'date_to': date_to,
    }
    
    return render(request, 'core/system_event_audit_report.html', context)