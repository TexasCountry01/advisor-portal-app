from django.conf import settings
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
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.cache import never_cache
from accounts.models import User
from core.models import SystemSettings
from .models import Case, CaseDocument, CaseChangeRequest, CaseMessage, UnreadMessage
import logging
import json
from datetime import timedelta
from urllib.parse import urlencode

logger = logging.getLogger(__name__)


# ============================================================================
# HELPER: Create a CaseNotification only if the member's global
# portal_notifications_enabled flag is True (User model field).
# ============================================================================

def _create_case_notification_if_allowed(*, case, member, notification_type, **kwargs):
    """
    Wrapper around CaseNotification.objects.create that checks the
    member's User.portal_notifications_enabled flag.

    Returns the created CaseNotification, or None if the member has
    disabled in-app notifications.
    """
    from cases.models import CaseNotification

    if member and not getattr(member, 'portal_notifications_enabled', True):
        logger.info(
            f'Portal notification suppressed for {member.username} '
            f'(type={notification_type}) — user disabled in-app alerts'
        )
        return None

    return CaseNotification.objects.create(
        case=case, member=member, notification_type=notification_type, **kwargs
    )


def _get_active_technicians():
    """
    Fetch active technician/administrator users for the quick tech filter.
    Managers are excluded (view-only role, not case workers).
    Returns list of dicts sorted by preferred display order, including online status.
    """
    from django.utils import timezone
    now = timezone.now()

    technicians = _exclude_super_dev_users(User.objects.filter(
        role__in=['technician', 'administrator'],
        is_active=True
    )).values('username', 'first_name', 'last_active')

    def _compute_status(last_active):
        if last_active is None:
            return 'offline', 'Never active'
        diff = (now - last_active).total_seconds()
        if diff < 300:
            return 'active', 'Active now'
        elif diff < 1800:
            return 'away', f'Away {int(diff // 60)} min ago'
        else:
            hours = int(diff // 3600)
            days = int(diff // 86400)
            if days >= 1:
                return 'offline', f'Offline {days}d ago'
            elif hours >= 1:
                return 'offline', f'Offline {hours}h ago'
            return 'offline', f'Offline {int(diff // 60)}m ago'

    # Preferred display order by first name (case-insensitive); unknowns go to end alphabetically
    _order = {'ileana': 0, 'tiffany': 1, 'chris': 2}
    result = []
    for t in technicians:
        status, label = _compute_status(t['last_active'])
        result.append({
            'username': t['username'],
            'first_name': t['first_name'],
            'status': status,
            'label': label,
        })
    return sorted(result, key=lambda t: (_order.get(t['first_name'].lower(), 99), t['first_name'].lower()))


def _get_super_dev_email():
    """Return the configured super-dev user email from system settings."""
    try:
        return (SystemSettings.get_settings().super_dev_email or '').strip().lower()
    except Exception:
        return ''


def _exclude_super_dev_users(queryset):
    """Exclude only the configured super-dev user from operational user querysets."""
    super_dev_email = _get_super_dev_email()
    if super_dev_email:
        queryset = queryset.exclude(email__iexact=super_dev_email)
    return queryset


def build_filter_params(request):
    """
    Build a URL-encoded query string with all current filter parameters.
    Used to preserve filters when paginating. Returns a string like
    'quick_filter=scheduled&quick_tech=all' safe to embed directly in hrefs.
    """
    from urllib.parse import urlencode
    params = []

    # Preserve status filters (multiple values)
    for status in request.GET.getlist('status'):
        params.append(('status', status))

    # Preserve other filters
    for param in ['urgency', 'tier', 'member', 'technician', 'date_range',
                  'date_from', 'date_to', 'search', 'workshop_code', 'quick_filter', 'quick_tech',
                  'view', 'assigned']:
        value = request.GET.get(param)
        if value:
            params.append((param, value))

    return urlencode(params)


def _apply_staff_quick_filter(queryset, quick_filter, user, quick_tech='all'):
    """Apply tile-style quick filters for technician/manager/admin dashboards."""
    from django.db.models import Exists, OuterRef

    today = timezone.localtime(timezone.now()).date()
    tomorrow = today + timedelta(days=1)

    if quick_filter == 'submitted':
        return queryset.filter(status='submitted')
    if quick_filter == 'pending':
        return queryset.exclude(status__in=['completed', 'cancelled', 'declined', 'draft'])
    if quick_filter == 'scheduled':
        return queryset.filter(
            status='completed',
            actual_release_date__isnull=True,
            scheduled_release_date__isnull=False
        )
    if quick_filter == 'need_review':
        return queryset.filter(status='pending_review')
    if quick_filter == 'on_hold':
        return queryset.filter(status='hold')
    if quick_filter == 'alerts':
        # Drafts excluded; all other statuses (including completed/cancelled/declined)
        # are included — a post-completion member chat message should still alert the tech.
        alert_qs = queryset.exclude(status='draft')
        # Technician dashboard uses quick-tech scope:
        # - All Techs: team-wide alerts
        # - Specific tech: that technician's actionable alerts
        if user.role == 'technician':
            if quick_tech and quick_tech != 'all':
                try:
                    scoped_user = User.objects.get(
                        username__iexact=quick_tech,
                        role__in=['technician', 'administrator'],
                        is_active=True,
                    )
                    _has_unread_for_scoped_user = Exists(
                        UnreadMessage.objects.filter(case=OuterRef('pk'), user=scoped_user)
                    )
                    return alert_qs.filter(
                        Q(has_member_updates=True, assigned_to=scoped_user) |
                        _has_unread_for_scoped_user
                    )
                except User.DoesNotExist:
                    pass

            _has_assigned_tech_unread = Exists(
                UnreadMessage.objects.filter(case=OuterRef('pk'), user=OuterRef('assigned_to'))
            )
            return alert_qs.filter(Q(has_member_updates=True) | _has_assigned_tech_unread)

        _has_assigned_tech_unread = Exists(
            UnreadMessage.objects.filter(case=OuterRef('pk'), user=OuterRef('assigned_to'))
        )
        return alert_qs.filter(Q(has_member_updates=True) | _has_assigned_tech_unread)
    if quick_filter == 'due_today':
        return queryset.filter(date_due=today).exclude(status__in=['completed', 'cancelled', 'declined', 'draft'])
    if quick_filter == 'due_tomorrow':
        return queryset.filter(date_due=tomorrow).exclude(status__in=['completed', 'cancelled', 'declined', 'draft'])
    if quick_filter == 'due_next_7d':
        next_7d = today + timedelta(days=7)
        return queryset.filter(date_due__gte=today, date_due__lte=next_7d).exclude(status__in=['completed', 'cancelled', 'declined', 'draft'])
    if quick_filter == 'past_due':
        return queryset.filter(date_due__lt=today).exclude(status__in=['completed', 'cancelled', 'declined', 'draft'])

    return queryset


def _build_staff_quick_tiles(queryset, user, quick_tech='all'):
    """Build tile counts for technician/manager/admin dashboards.
    Uses a single SQL aggregate instead of 10 separate COUNT queries.
    """
    from django.db.models import Sum, Case as DbCase, When, IntegerField, Exists, OuterRef

    today = timezone.localtime(timezone.now()).date()
    tomorrow = today + timedelta(days=1)
    next_7d = today + timedelta(days=7)
    inactive = Q(status__in=['completed', 'cancelled', 'declined', 'draft'])

    counts = queryset.aggregate(
        submitted=Sum(DbCase(When(status='submitted', then=1), default=0, output_field=IntegerField())),
        pending=Sum(DbCase(When(~inactive, then=1), default=0, output_field=IntegerField())),
        scheduled=Sum(DbCase(When(
            status='completed',
            actual_release_date__isnull=True,
            scheduled_release_date__isnull=False,
            then=1
        ), default=0, output_field=IntegerField())),
        need_review=Sum(DbCase(When(status='pending_review', then=1), default=0, output_field=IntegerField())),
        on_hold=Sum(DbCase(When(status='hold', then=1), default=0, output_field=IntegerField())),
        due_today=Sum(DbCase(When(
            Q(date_due=today) & ~inactive, then=1
        ), default=0, output_field=IntegerField())),
        due_tomorrow=Sum(DbCase(When(
            Q(date_due=tomorrow) & ~inactive, then=1
        ), default=0, output_field=IntegerField())),
        due_next_7d=Sum(DbCase(When(
            Q(date_due__gte=today, date_due__lte=next_7d) & ~inactive, then=1
        ), default=0, output_field=IntegerField())),
        past_due=Sum(DbCase(When(
            Q(date_due__lt=today) & ~inactive, then=1
        ), default=0, output_field=IntegerField())),
    )
    # Alerts tile: drafts excluded; all other statuses included so techs see
    # post-completion/cancellation/declined member chat messages in the tile.
    alert_qs = queryset.exclude(status='draft')
    if user.role == 'technician':
        if quick_tech and quick_tech != 'all':
            try:
                scoped_user = User.objects.get(
                    username__iexact=quick_tech,
                    role__in=['technician', 'administrator'],
                    is_active=True,
                )
                _has_unread_for_scoped_user = Exists(
                    UnreadMessage.objects.filter(case=OuterRef('pk'), user=scoped_user)
                )
                counts['alerts'] = alert_qs.filter(
                    Q(has_member_updates=True, assigned_to=scoped_user) |
                    _has_unread_for_scoped_user
                ).count()
                return {k: (v or 0) for k, v in counts.items()}
            except User.DoesNotExist:
                pass

        _has_assigned_tech_unread = Exists(
            UnreadMessage.objects.filter(case=OuterRef('pk'), user=OuterRef('assigned_to'))
        )
        counts['alerts'] = alert_qs.filter(
            Q(has_member_updates=True) | _has_assigned_tech_unread
        ).count()
        return {k: (v or 0) for k, v in counts.items()}

    _has_assigned_tech_unread = Exists(
        UnreadMessage.objects.filter(case=OuterRef('pk'), user=OuterRef('assigned_to'))
    )
    counts['alerts'] = alert_qs.filter(
        Q(has_member_updates=True) | _has_assigned_tech_unread
    ).count()
    return {k: (v or 0) for k, v in counts.items()}


def _apply_member_quick_filter(queryset, quick_filter, user):
    """Apply tile-style quick filters for member dashboard."""
    from django.db.models import Exists, OuterRef
    from cases.models import CaseNotification

    now = timezone.now()
    ready_since = now - timedelta(days=14)

    if quick_filter == 'ready_14d':
        return queryset.filter(
            status='completed',
            actual_release_date__isnull=False,
            actual_release_date__gte=ready_since
        )
    if quick_filter == 'pending':
        return queryset.exclude(status__in=['cancelled', 'declined', 'draft']).exclude(
            status='completed', actual_release_date__isnull=False
        )
    if quick_filter == 'on_hold':
        return queryset.filter(status='hold')
    if quick_filter == 'alerts':
        has_unread_msg = Exists(UnreadMessage.objects.filter(case=OuterRef('pk'), user=user))
        has_unread_notif = Exists(
            CaseNotification.objects.filter(
                case=OuterRef('pk'),
                member=OuterRef('member'),
                is_read=False
            ).exclude(notification_type='member_update_received')
        )
        return queryset.filter(has_unread_msg | has_unread_notif)
    if quick_filter == 'drafts':
        return queryset.filter(status='draft')

    return queryset


def _build_member_quick_tiles(queryset, user):
    """Build tile counts for member dashboard.
    Uses a single SQL aggregate instead of 5 separate COUNT queries.
    The 'alerts' tile requires Exists subqueries and is kept as one extra COUNT.
    """
    from django.db.models import Sum, Case as DbCase, When, IntegerField, Exists, OuterRef
    from cases.models import CaseNotification

    now = timezone.now()
    ready_since = now - timedelta(days=14)

    counts = queryset.aggregate(
        ready_14d=Sum(DbCase(When(
            status='completed',
            actual_release_date__isnull=False,
            actual_release_date__gte=ready_since,
            then=1
        ), default=0, output_field=IntegerField())),
        pending=Sum(DbCase(When(
            ~Q(status__in=['cancelled', 'declined', 'draft']) &
            ~Q(status='completed', actual_release_date__isnull=False),
            then=1
        ), default=0, output_field=IntegerField())),
        on_hold=Sum(DbCase(When(status='hold', then=1), default=0, output_field=IntegerField())),
        drafts=Sum(DbCase(When(status='draft', then=1), default=0, output_field=IntegerField())),
    )
    # Alerts requires Exists subqueries — one separate COUNT
    has_unread_msg = Exists(UnreadMessage.objects.filter(case=OuterRef('pk'), user=user))
    has_unread_notif = Exists(
        CaseNotification.objects.filter(
            case=OuterRef('pk'),
            member=OuterRef('member'),
            is_read=False
        ).exclude(notification_type='member_update_received')
    )
    counts['alerts'] = queryset.filter(has_unread_msg | has_unread_notif).count()
    return {k: (v or 0) for k, v in counts.items()}


# DEV ONLY - Form preview without authentication
def form_preview(request):
    """Development view to preview form without authentication"""
    context = {
        'workshop_code': 'DEV001',
        'member_name': 'Preview User',
        'today': timezone.localtime(timezone.now()).date(),
    }
    return render(request, 'cases/fact_finder_form.html', context)


@login_required
@ensure_csrf_cookie
def member_dashboard(request):
    """Dashboard view for Member role"""
    from django.db.models import Q
    from accounts.models import MemberDelegate
    
    user = request.user
    
    # Allow administrators to preview this dashboard
    admin_preview = (request.GET.get('preview') == 'admin' and user.role == 'administrator')
    
    # Ensure user is a member (or admin previewing)
    if user.role != 'member' and not admin_preview:
        messages.error(request, 'Access denied. Members only.')
        return redirect('home')
    
    # ====================================================================
    # DELEGATE DETECTION — determine if user is a delegate for anyone
    # ====================================================================
    delegate_assignments = MemberDelegate.objects.filter(
        delegate=user
    ).select_related('member')
    is_delegate = delegate_assignments.exists()
    
    # Get members this user is a delegate for (for delegate view queries)
    delegated_members = [da.member for da in delegate_assignments] if is_delegate else []
    delegated_member_ids = [m.id for m in delegated_members]
    
    # Check if user has their own cases (to determine pure delegate)
    has_own_cases = Case.objects.filter(member=user).exists()
    is_pure_delegate = is_delegate and not has_own_cases
    
    # Determine active view: 'my_cases' or 'delegate'
    # Pure delegates default to 'delegate' view; members default to 'my_cases'
    default_view = 'delegate' if is_pure_delegate else 'my_cases'
    active_view = request.GET.get('view', default_view)
    
    # Validate the view parameter
    if active_view == 'delegate' and not is_delegate:
        active_view = 'my_cases'
    if active_view == 'all' and not is_delegate:
        active_view = 'my_cases'
    if active_view == 'my_cases' and is_pure_delegate:
        # Pure delegates can't switch to my_cases — they have no cases
        active_view = 'delegate'
    
    # ====================================================================
    # QUERY CASES based on active view
    # ====================================================================
    if active_view == 'all':
        # All Cases view: show user's own cases + delegate cases combined
        all_member_ids = [user.id] + delegated_member_ids
        cases = Case.objects.filter(
            member_id__in=all_member_ids
        ).prefetch_related(
            'documents',
            'unread_messages_for_users'
        ).select_related(
            'assigned_to', 'member'
        ).order_by('-date_submitted')
    elif active_view == 'delegate':
        # Delegate view: show cases for all members this user is a delegate for
        cases = Case.objects.filter(
            member_id__in=delegated_member_ids
        ).prefetch_related(
            'documents',
            'unread_messages_for_users'
        ).select_related(
            'assigned_to', 'member'
        ).order_by('-date_submitted')
    else:
        # My Cases view: show user's own cases
        cases = Case.objects.filter(
            member=user
        ).prefetch_related(
            'documents',
            'unread_messages_for_users'
        ).select_related(
            'assigned_to'
        ).order_by('-date_submitted')
    
    # Apply filters BEFORE adding unread count
    allowed_admin_statuses = {
        'submitted', 'accepted', 'pending_review', 'hold',
        'completed', 'cancelled', 'declined', 'needs_resubmission'
    }
    status_filter = [s for s in request.GET.getlist('status') if s in allowed_admin_statuses]
    urgency_filter = request.GET.get('urgency')
    date_range = request.GET.get('date_range')
    custom_date_from = request.GET.get('date_from')
    custom_date_to = request.GET.get('date_to')
    search_query = request.GET.get('search')
    quick_filter = request.GET.get('quick_filter', '')
    sort_by = request.GET.get('sort')
    if sort_by:
        save_user_sort_preference(user, 'member_dashboard', sort_by)
    else:
        sort_by = get_user_sort_preference(user, 'member_dashboard', 'date_due')
    
    if status_filter:
        # Override: always include cases with unread notifications regardless of filter
        from django.db.models import Exists, OuterRef
        from cases.models import CaseNotification
        has_unread_msg = Exists(UnreadMessage.objects.filter(case=OuterRef('pk'), user=user))
        has_unread_notif = Exists(CaseNotification.objects.filter(
            case=OuterRef('pk'), member=OuterRef('member'), is_read=False
        ).exclude(notification_type='member_update_received'))
        # For members: treat completed-but-unreleased cases as 'accepted' for filtering
        status_q = Q(status__in=status_filter)
        if 'accepted' in status_filter and 'completed' not in status_filter:
            # "Accepted" filter should also match completed-but-unreleased cases
            status_q = status_q | Q(status='completed', actual_release_date__isnull=True)
        if 'completed' in status_filter and 'accepted' not in status_filter:
            # "Completed" filter should only match actually-released cases
            status_q = status_q & ~Q(status='completed', actual_release_date__isnull=True)
        cases = cases.filter(status_q | has_unread_msg | has_unread_notif)
    
    if urgency_filter:
        cases = cases.filter(urgency=urgency_filter)
    
    # Date range filter - custom dates take precedence
    if custom_date_from or custom_date_to:
        from datetime import datetime as dt_parse
        if custom_date_from:
            date_from = dt_parse.strptime(custom_date_from, '%Y-%m-%d').date()
            cases = cases.filter(date_submitted__date__gte=date_from)
        if custom_date_to:
            date_to = dt_parse.strptime(custom_date_to, '%Y-%m-%d').date()
            cases = cases.filter(date_submitted__date__lte=date_to)
    elif date_range:
        from datetime import timedelta
        today = timezone.localtime(timezone.now()).date()
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
            Q(employee_last_name__icontains=search_query)
        )

    # Apply quick tile filter after regular filters so users can combine controls.
    if quick_filter:
        cases = _apply_member_quick_filter(cases, quick_filter, user)

    if quick_filter == 'ready_14d' and not request.GET.get('sort'):
        sort_by = '-date_completed'

    # SQL-based ordering (replaces Python sort-after-list-conversion)
    from django.db.models import F as _F
    _sql_sorts = {
        'external_case_id': 'external_case_id', '-external_case_id': '-external_case_id',
        'workshop_code': 'workshop_code', '-workshop_code': '-workshop_code',
        'employee_first_name': 'employee_first_name', '-employee_first_name': '-employee_first_name',
        'date_submitted': 'date_submitted', '-date_submitted': '-date_submitted',
        'status': 'status', '-status': '-status',
        'urgency': 'urgency', '-urgency': '-urgency',
    }
    _null_sorts = {
        'date_due': _F('date_due').asc(nulls_last=True),
        '-date_due': _F('date_due').desc(nulls_last=True),
        'date_accepted': _F('date_accepted').asc(nulls_last=True),
        '-date_accepted': _F('date_accepted').desc(nulls_last=True),
        'date_completed': _F('date_completed').asc(nulls_last=True),
        '-date_completed': _F('date_completed').desc(nulls_last=True),
    }
    if sort_by in _sql_sorts:
        cases = cases.order_by(_sql_sorts[sort_by])
    elif sort_by in _null_sorts:
        cases = cases.order_by(_null_sorts[sort_by])

    # Paginate before evaluating the queryset
    paginator = Paginator(cases, 50)
    page_obj = paginator.get_page(request.GET.get('page', 1))
    page_cases = list(page_obj.object_list)

    # Batch unread counts for current page only (2 queries instead of 2×N)
    from cases.models import CaseNotification
    from django.db.models import Count as _Count
    notif_enabled_member_ids = set(
        da.member_id for da in delegate_assignments if da.portal_notifications
    )
    notif_enabled_member_ids.add(user.id)
    _chat_map = {
        row['case_id']: row['cnt']
        for row in UnreadMessage.objects
            .filter(case_id__in=[c.pk for c in page_cases], user=user)
            .values('case_id').annotate(cnt=_Count('id'))
    }
    _lifecycle_map = {
        row['case_id']: row['cnt']
        for row in CaseNotification.objects
            .filter(
                case_id__in=[c.pk for c in page_cases],
                member_id__in=notif_enabled_member_ids,
                is_read=False
            )
            .exclude(notification_type='member_update_received')
            .values('case_id').annotate(cnt=_Count('id'))
    } if notif_enabled_member_ids else {}
    for case in page_cases:
        case.unread_message_count = _chat_map.get(case.pk, 0) + _lifecycle_map.get(case.pk, 0)

    # Calculate statistics (for the active view)
    if active_view == 'all':
        all_member_ids = [user.id] + delegated_member_ids
        all_cases = Case.objects.filter(member_id__in=all_member_ids)
    elif active_view == 'delegate':
        all_cases = Case.objects.filter(member_id__in=delegated_member_ids)
    else:
        all_cases = Case.objects.filter(member=user)
    # Single aggregate replaces 8 separate COUNT queries
    from django.db.models import Sum, Case as DbCase, When, IntegerField, Count as _Count
    _s = all_cases.aggregate(
        total_cases=_Count('id'),
        draft=Sum(DbCase(When(status='draft', then=1), default=0, output_field=IntegerField())),
        submitted=Sum(DbCase(When(status='submitted', then=1), default=0, output_field=IntegerField())),
        accepted=Sum(DbCase(When(
            Q(status='accepted') | Q(status='completed', actual_release_date__isnull=True),
            then=1
        ), default=0, output_field=IntegerField())),
        resubmitted=Sum(DbCase(When(status='resubmitted', then=1), default=0, output_field=IntegerField())),
        completed=Sum(DbCase(When(status='completed', actual_release_date__isnull=False, then=1), default=0, output_field=IntegerField())),
        cancelled=Sum(DbCase(When(status='cancelled', then=1), default=0, output_field=IntegerField())),
        rush=Sum(DbCase(When(urgency='rush', then=1), default=0, output_field=IntegerField())),
    )
    stats = {k: (v or 0) for k, v in _s.items()}
    member_quick_tiles = _build_member_quick_tiles(all_cases, user)
    
    # Get column visibility settings
    visible_columns = get_user_visible_columns(user, 'member_dashboard')
    
    # Get draft cases for banner
    if active_view == 'all':
        all_member_ids_for_drafts = [user.id] + delegated_member_ids
        draft_cases = Case.objects.filter(member_id__in=all_member_ids_for_drafts, status='draft').order_by('-created_at')
    elif active_view == 'my_cases':
        draft_cases = Case.objects.filter(member=user, status='draft').order_by('-created_at')
    elif active_view == 'delegate' and delegated_member_ids:
        draft_cases = Case.objects.filter(member_id__in=delegated_member_ids, status='draft').order_by('-created_at')
    else:
        draft_cases = None
    
    context = {
        'cases': page_obj,
        'page_obj': page_obj,
        'stats': stats,
        'draft_cases': draft_cases,
        'status_filter': status_filter,
        'urgency_filter': urgency_filter,
        'date_range': date_range,
        'custom_date_from': custom_date_from,
        'custom_date_to': custom_date_to,
        'search_query': search_query,
        'sort_by': sort_by,
        'visible_columns': visible_columns,
        'all_columns': DASHBOARD_COLUMN_CONFIG['member_dashboard']['available_columns'],
        'filter_params': build_filter_params(request),
        # Delegate toggle context
        'is_delegate': is_delegate,
        'is_pure_delegate': is_pure_delegate,
        'active_view': active_view,
        'delegated_members': delegated_members,
        'admin_preview': admin_preview,
        'quick_filter': quick_filter,
        'member_quick_tiles': member_quick_tiles,
    }
    
    return render(request, 'cases/member_dashboard.html', context)


@login_required
def technician_dashboard(request):
    """Dashboard view for Benefits Technician - shows all cases (not just assigned)"""
    user = request.user
    
    # Check if admin is previewing this dashboard
    admin_preview = (user.role == 'administrator')
    
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
    # Include all non-draft statuses so declined/cancelled cases remain searchable
    # via the Status filter checkboxes even if unassigned.
    from django.db.models import Q
    cases = Case.objects.filter(
        Q(status__in=['submitted', 'resubmitted', 'accepted', 'hold', 'pending_review',
                      'completed', 'cancelled', 'declined', 'needs_resubmission']) |
        Q(assigned_to=user)  # OR cases assigned to this technician (even if draft)
    ).prefetch_related(
        'documents'
    ).select_related(
        'member', 'assigned_to', 'reviewed_by'
    ).order_by('-date_submitted')
    
    # Apply filters
    # Normalize status filters to known values only.
    allowed_statuses = {
        'submitted', 'accepted', 'pending_review', 'hold',
        'completed', 'cancelled', 'declined', 'resubmitted', 'needs_resubmission'
    }
    status_filters = [s for s in request.GET.getlist('status') if s in allowed_statuses]
    urgency_filter = request.GET.get('urgency')
    tier_filter = request.GET.get('tier')
    workshop_code_filter = request.GET.get('workshop_code')
    member_filter = request.GET.get('member')
    date_range = request.GET.get('date_range')
    custom_date_from = request.GET.get('date_from')
    custom_date_to = request.GET.get('date_to')
    search_query = request.GET.get('search')
    quick_filter = request.GET.get('quick_filter', '')
    quick_tech = request.GET.get('quick_tech', 'all')
    sort_by = request.GET.get('sort')
    if sort_by:
        save_user_sort_preference(user, 'technician_dashboard', sort_by)
    else:
        sort_by = get_user_sort_preference(user, 'technician_dashboard', 'date_due')
    assigned_filter = request.GET.get('assigned', default_view)  # Use saved preference as default

    # Detect whether any filter params are present (used by tile/filter logic below)
    _has_params = any(request.GET.get(p) for p in [
        'quick_filter', 'quick_tech', 'status', 'urgency', 'tier',
        'workshop_code', 'member', 'date_range', 'date_from', 'date_to', 'search', 'assigned', 'sort', 'page'
    ])

    # Terminal statuses (declined/cancelled) are always unassigned after our workflow
    # fix that clears assigned_to on cancellation/decline. If the user has explicitly
    # selected these statuses in the filter panel, bypass assignment constraints so
    # those cases are not silently excluded by 'mine' or quick_tech filters.
    _terminal_statuses = {'declined', 'cancelled'}
    _terminal_selected = [s for s in status_filters if s in _terminal_statuses]

    # Apply "My Cases" filter
    if assigned_filter == 'mine':
        if _terminal_selected:
            # Include user's assigned cases OR explicitly selected terminal-status cases
            cases = cases.filter(
                Q(assigned_to=user) | Q(status__in=_terminal_selected)
            )
        else:
            cases = cases.filter(assigned_to=user)

    # Apply quick technician filter from top buttons.
    # Exception: submitted cases have no assigned_to yet — skip for Need to Accept queue.
    if quick_tech and quick_tech != 'all' and quick_filter != 'submitted':
        try:
            tech_user = User.objects.get(username__iexact=quick_tech, role__in=['technician', 'administrator'], is_active=True)
            if _terminal_selected:
                # Include this tech's assigned cases OR explicitly selected terminal-status cases
                cases = cases.filter(
                    Q(assigned_to=tech_user) | Q(status__in=_terminal_selected)
                )
            else:
                cases = cases.filter(assigned_to=tech_user)
        except User.DoesNotExist:
            pass  # Filter not applied if technician doesn't exist
    
    # Apply multi-status filter strictly.
    # Do not OR in unread-chat cases here, otherwise selecting a status like
    # "cancelled" can incorrectly include cases from other statuses.
    if status_filters:
        cases = cases.filter(status__in=status_filters)
    
    if urgency_filter:
        cases = cases.filter(urgency=urgency_filter)
    
    if tier_filter:
        cases = cases.filter(tier=tier_filter)

    if workshop_code_filter:
        cases = cases.filter(workshop_code=workshop_code_filter)

    if member_filter:
        cases = cases.filter(member_id=member_filter)
    
    # Date range filter - custom dates take precedence
    if custom_date_from or custom_date_to:
        from datetime import datetime as dt_parse
        if custom_date_from:
            date_from = dt_parse.strptime(custom_date_from, '%Y-%m-%d').date()
            cases = cases.filter(date_submitted__date__gte=date_from)
        if custom_date_to:
            date_to = dt_parse.strptime(custom_date_to, '%Y-%m-%d').date()
            cases = cases.filter(date_submitted__date__lte=date_to)
    elif date_range:
        from datetime import timedelta
        today = timezone.localtime(timezone.now()).date()
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
            Q(member__last_name__icontains=search_query)
        )

    # Build tile counts before applying the active quick tile filter.
    tile_scope_cases = cases

    # Filter-panel inputs are authoritative. If users type a search or set
    # detailed filters, do not keep constraining results by a previously active
    # quick tile (e.g., pending), which can hide valid matches.
    has_detailed_filters = any([
        status_filters,
        urgency_filter,
        tier_filter,
        workshop_code_filter,
        member_filter,
        date_range,
        custom_date_from,
        custom_date_to,
        search_query,
    ])
    if quick_filter and not has_detailed_filters:
        cases = _apply_staff_quick_filter(cases, quick_filter, user, quick_tech)
    allowed_sorts = [
        'employee_first_name', '-employee_first_name',
        'employee_last_name', '-employee_last_name',
        'date_submitted', '-date_submitted',
        'date_due', '-date_due',
        'date_completed', '-date_completed',
        'status', '-status',
        'urgency', '-urgency',
        'tier', '-tier',
        'assigned_to', '-assigned_to',
        'credit_value', '-credit_value'
    ]
    if sort_by in allowed_sorts:
        cases = cases.order_by(sort_by)
    else:
        cases = cases.order_by('-date_submitted')
    
    # Single aggregate replaces 8 separate COUNT queries
    from django.db.models import Sum, Case as DbCase, When, IntegerField, Count as _Count
    _s = cases.aggregate(
        total=_Count('id'),
        submitted=Sum(DbCase(When(status='submitted', then=1), default=0, output_field=IntegerField())),
        accepted=Sum(DbCase(When(status='accepted', then=1), default=0, output_field=IntegerField())),
        resubmitted=Sum(DbCase(When(status='resubmitted', then=1), default=0, output_field=IntegerField())),
        pending_review=Sum(DbCase(When(status='pending_review', then=1), default=0, output_field=IntegerField())),
        needs_revision=Sum(DbCase(When(status='accepted', review_status='revisions_requested', then=1), default=0, output_field=IntegerField())),
        completed=Sum(DbCase(When(status='completed', then=1), default=0, output_field=IntegerField())),
        rush=Sum(DbCase(When(urgency='rush', then=1), default=0, output_field=IntegerField())),
    )
    stats = {k: (v or 0) for k, v in _s.items()}
    quick_tiles = _build_staff_quick_tiles(tile_scope_cases, user, quick_tech)
    # "Need to Accept" reflects the global unassigned queue, not a per-tech count.
    # Submitted cases have no assigned_to yet, so filtering by tech always yields 0.
    if quick_tech and quick_tech != 'all':
        quick_tiles['submitted'] = Case.objects.filter(status='submitted').count()
    paginator = Paginator(cases, 50)
    page_obj = paginator.get_page(request.GET.get('page', 1))
    page_cases = list(page_obj.object_list)
    # Badge scoped to the assigned tech's own UnreadMessage rows only.
    # All staff (admin/manager/tech) see the same count for each case because
    # the badge reflects the CASE OWNER's unread state, not the viewer's.
    from django.db.models import F as _F
    _unread_map = {
        row['case_id']: row['cnt']
        for row in UnreadMessage.objects
            .filter(
                case_id__in=[c.pk for c in page_cases],
                user=_F('case__assigned_to'),
            )
            .values('case_id').annotate(cnt=_Count('id'))
    }
    for case in page_cases:
        case.unread_message_count = _unread_map.get(case.pk, 0)

    # Get available technicians and administrators for assignment dropdown
    technicians = _exclude_super_dev_users(User.objects.filter(
        role__in=['technician', 'administrator']
    )).order_by('last_name', 'first_name')

    members = _exclude_super_dev_users(User.objects.filter(role='member', is_active=True)).order_by('username')
    workshop_codes = Case.objects.exclude(status='draft').values_list('workshop_code', flat=True).distinct().order_by('workshop_code')

    # Get active technicians for quick-filter buttons
    quick_technicians = _get_active_technicians()

    context = {
        'cases': page_obj,
        'page_obj': page_obj,
        'stats': stats,
        'members': members,
        'status_filters': status_filters,  # List of selected statuses
        'urgency_filter': urgency_filter,
        'tier_filter': tier_filter,
        'workshop_code_filter': workshop_code_filter,
        'member_filter': member_filter,
        'workshop_codes': workshop_codes,
        'date_range': date_range,
        'custom_date_from': custom_date_from,
        'custom_date_to': custom_date_to,
        'search_query': search_query,
        'sort_by': sort_by,
        'assigned_filter': assigned_filter,
        'technicians': technicians,
        'dashboard_type': 'technician',
        'filter_params': build_filter_params(request),
        'quick_filter': quick_filter,
        'quick_tech': quick_tech,
        'quick_technicians': quick_technicians,
        'quick_tiles': quick_tiles,
    }
    
    # Add column visibility data
    visible_columns = get_user_visible_columns(user, 'technician_dashboard')
    context['visible_columns'] = visible_columns
    context['all_columns'] = DASHBOARD_COLUMN_CONFIG['technician_dashboard']['available_columns']
    context['admin_preview'] = admin_preview
    
    # Review alert banners for technicians
    # 1. Cases this tech submitted that are pending review (L1 tech waiting for review)
    my_cases_pending_review = Case.objects.filter(
        assigned_to=user, status='pending_review'
    ).select_related('reviewed_by').order_by('-date_submitted')
    
    # 2. Cases with revisions requested that belong to this tech (L1 tech needs to revise)
    my_cases_needing_revision = Case.objects.filter(
        assigned_to=user, status='accepted', review_status='revisions_requested'
    ).select_related('reviewed_by').order_by('-date_submitted')
    
    # 3. Cases awaiting this tech's review (L2/L3 reviewer)
    cases_awaiting_my_review = Case.objects.filter(
        status='pending_review'
    ).exclude(assigned_to=user).select_related('assigned_to', 'reviewed_by').order_by('-date_submitted')
    
    context['my_cases_pending_review'] = my_cases_pending_review
    context['my_cases_needing_revision'] = my_cases_needing_revision
    context['cases_awaiting_my_review'] = cases_awaiting_my_review
    
    return render(request, 'cases/technician_dashboard.html', context)


@login_required
def admin_dashboard(request):
    """Dashboard view for Administrators - full system visibility and control"""
    user = request.user
    
    # Ensure user is an administrator
    if user.role != 'administrator':
        messages.error(request, 'Access denied. Administrators only.')
        return redirect('home')
    
    # Get all cases with all related data - exclude drafts (only visible to members)
    cases = Case.objects.exclude(status='draft').prefetch_related(
        'documents'
    ).select_related(
        'member', 'assigned_to', 'reviewed_by'
    ).order_by('-date_submitted')
    
    # Apply filters
    # Status filter - support multiple values (from checkboxes)
    status_filter = request.GET.getlist('status')  # Use getlist for multiple values
    urgency_filter = request.GET.get('urgency')
    tier_filter = request.GET.get('tier')
    workshop_code_filter = request.GET.get('workshop_code')
    member_filter = request.GET.get('member')
    technician_filter = request.GET.get('technician')
    date_range = request.GET.get('date_range')
    custom_date_from = request.GET.get('date_from')
    custom_date_to = request.GET.get('date_to')
    search_query = request.GET.get('search')
    quick_filter = request.GET.get('quick_filter', '')
    quick_tech = request.GET.get('quick_tech', 'all')
    sort_by = request.GET.get('sort')
    if sort_by:
        save_user_sort_preference(user, 'admin_dashboard', sort_by)
    else:
        sort_by = get_user_sort_preference(user, 'admin_dashboard', '-date_submitted')
    
    if status_filter:
        cases = cases.filter(status__in=status_filter)
    
    if urgency_filter:
        cases = cases.filter(urgency=urgency_filter)
    
    if tier_filter:
        cases = cases.filter(tier=tier_filter)

    if workshop_code_filter:
        cases = cases.filter(workshop_code=workshop_code_filter)
    
    if member_filter:
        cases = cases.filter(member_id=member_filter)
    
    if technician_filter:
        cases = cases.filter(assigned_to_id=technician_filter)

    # Exception: submitted cases have no assigned_to yet � skip for Need to Accept queue.
    if quick_tech and quick_tech != 'all' and quick_filter != 'submitted':
        try:
            tech_user = User.objects.get(username__iexact=quick_tech, role__in=['technician', 'administrator'], is_active=True)
            cases = cases.filter(assigned_to=tech_user)
        except User.DoesNotExist:
            pass  # Filter not applied if technician doesn't exist
    
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
        today = timezone.localtime(timezone.now()).date()
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

    tile_scope_cases = cases
    if quick_filter:
        cases = _apply_staff_quick_filter(cases, quick_filter, user, quick_tech)
    
    # Handle sorting
    allowed_sorts = [
        'external_case_id', '-external_case_id',
        'workshop_code', '-workshop_code',
        'employee_first_name', '-employee_first_name',
        'employee_last_name', '-employee_last_name',
        'date_submitted', '-date_submitted',
        'date_due', '-date_due',
        'date_scheduled', '-date_scheduled',
        'scheduled_release_date', '-scheduled_release_date',
        'status', '-status',
        'urgency', '-urgency',
        'tier', '-tier',
        'assigned_to', '-assigned_to',
        'date_completed', '-date_completed'
    ]
    if sort_by in allowed_sorts:
        cases = cases.order_by(sort_by)
    else:
        cases = cases.order_by('-date_submitted')
    
    # Get related data for filters
    members = _exclude_super_dev_users(User.objects.filter(role='member', is_active=True)).order_by('username')
    technicians = _exclude_super_dev_users(User.objects.filter(role='technician', is_active=True)).order_by('username')
    workshop_codes = Case.objects.exclude(status='draft').values_list('workshop_code', flat=True).distinct().order_by('workshop_code')
    
    # Calculate comprehensive statistics (exclude drafts - those are member-only)
    all_cases = Case.objects.exclude(status='draft')
    
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
    active_members = _exclude_super_dev_users(User.objects.filter(id__in=active_user_ids, role='member')).count()
    active_technicians = _exclude_super_dev_users(User.objects.filter(id__in=active_user_ids, role='technician')).count()
    
    # Single aggregate replaces 10 separate COUNT queries
    from django.db.models import Sum, Case as DbCase, When, IntegerField, Count as _Count
    _s = all_cases.aggregate(
        total=_Count('id'),
        submitted=Sum(DbCase(When(status='submitted', then=1), default=0, output_field=IntegerField())),
        accepted=Sum(DbCase(When(status='accepted', then=1), default=0, output_field=IntegerField())),
        resubmitted=Sum(DbCase(When(status='resubmitted', then=1), default=0, output_field=IntegerField())),
        hold=Sum(DbCase(When(status='hold', then=1), default=0, output_field=IntegerField())),
        pending_review=Sum(DbCase(When(status='pending_review', then=1), default=0, output_field=IntegerField())),
        completed=Sum(DbCase(When(status='completed', then=1), default=0, output_field=IntegerField())),
        rush=Sum(DbCase(When(urgency='rush', then=1), default=0, output_field=IntegerField())),
        unassigned=Sum(DbCase(When(assigned_to__isnull=True, then=1), default=0, output_field=IntegerField())),
    )
    stats = {k: (v or 0) for k, v in _s.items()}
    stats['total_members'] = active_members
    stats['total_technicians'] = active_technicians
    stats['requiring_review'] = stats['pending_review']
    quick_tiles = _build_staff_quick_tiles(tile_scope_cases, user, quick_tech)
    # "Need to Accept" reflects the global unassigned queue, not a per-tech count.
    # Submitted cases have no assigned_to yet, so filtering by tech always yields 0.
    if quick_tech and quick_tech != 'all':
        quick_tiles['submitted'] = Case.objects.filter(status='submitted').count()

    # Get active technicians for quick-filter buttons
    quick_technicians = _get_active_technicians()

    # Single batch query for unread message counts on current page only
    from django.db.models import Count as _Count
    paginator = Paginator(cases, 50)
    page_obj = paginator.get_page(request.GET.get('page', 1))
    page_cases = list(page_obj.object_list)
    # Badge scoped to the assigned tech's own UnreadMessage rows only.
    # All staff see the same number for each case (owner's unread state).
    from django.db.models import F as _F
    _unread_map = {
        row['case_id']: row['cnt']
        for row in UnreadMessage.objects
            .filter(
                case_id__in=[c.pk for c in page_cases],
                user=_F('case__assigned_to'),
            )
            .values('case_id').annotate(cnt=_Count('id'))
    }
    for case in page_cases:
        case.unread_message_count = _unread_map.get(case.pk, 0)

    context = {
        'cases': page_obj,
        'page_obj': page_obj,
        'stats': stats,
        'members': members,
        'technicians': technicians,
        'workshop_codes': workshop_codes,
        'status_filter': status_filter,
        'urgency_filter': urgency_filter,
        'tier_filter': tier_filter,
        'workshop_code_filter': workshop_code_filter,
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
        'filter_params': build_filter_params(request),
        'enable_data_sync': settings.ENABLE_DATA_SYNC,
        'quick_filter': quick_filter,
        'quick_tech': quick_tech,
        'quick_technicians': quick_technicians,
        'quick_tiles': quick_tiles,
    }
    
    return render(request, 'cases/admin_dashboard.html', context)


@login_required
def manager_dashboard(request):
    """Dashboard view for Managers - read-only visibility with analytics"""
    user = request.user
    
    # Allow administrators to preview this dashboard
    admin_preview = (request.GET.get('preview') == 'admin' and user.role == 'administrator')
    
    # Ensure user is a manager (or admin previewing)
    if user.role != 'manager' and not admin_preview:
        messages.error(request, 'Access denied. Managers only.')
        return redirect('home')
    
    # Get all cases with all related data (read-only) - exclude drafts
    cases = Case.objects.exclude(status='draft').prefetch_related(
        'documents'
    ).select_related(
        'member', 'assigned_to', 'reviewed_by'
    ).order_by('-date_submitted')
    
    # Apply filters
    status_filter = request.GET.getlist('status')  # Use getlist for multiple values
    urgency_filter = request.GET.get('urgency')
    tier_filter = request.GET.get('tier')
    workshop_code_filter = request.GET.get('workshop_code')
    member_filter = request.GET.get('member')
    technician_filter = request.GET.get('technician')
    date_range = request.GET.get('date_range')
    custom_date_from = request.GET.get('date_from')
    custom_date_to = request.GET.get('date_to')
    search_query = request.GET.get('search')
    quick_filter = request.GET.get('quick_filter', '')
    quick_tech = request.GET.get('quick_tech', 'all')
    sort_by = request.GET.get('sort')
    if sort_by:
        save_user_sort_preference(user, 'manager_dashboard', sort_by)
    else:
        sort_by = get_user_sort_preference(user, 'manager_dashboard', '-date_submitted')
    
    if status_filter:
        cases = cases.filter(status__in=status_filter)
    
    if urgency_filter:
        cases = cases.filter(urgency=urgency_filter)
    
    if tier_filter:
        cases = cases.filter(tier=tier_filter)

    if workshop_code_filter:
        cases = cases.filter(workshop_code=workshop_code_filter)
    
    if member_filter:
        cases = cases.filter(member_id=member_filter)
    
    if technician_filter:
        cases = cases.filter(assigned_to_id=technician_filter)

    # Exception: submitted cases have no assigned_to yet � skip for Need to Accept queue.
    if quick_tech and quick_tech != 'all' and quick_filter != 'submitted':
        try:
            tech_user = User.objects.get(username__iexact=quick_tech, role__in=['technician', 'administrator'], is_active=True)
            cases = cases.filter(assigned_to=tech_user)
        except User.DoesNotExist:
            pass  # Filter not applied if technician doesn't exist
    
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
        today = timezone.localtime(timezone.now()).date()
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

    tile_scope_cases = cases
    if quick_filter:
        cases = _apply_staff_quick_filter(cases, quick_filter, user, quick_tech)
    
    # Handle sorting
    allowed_sorts = [
        'external_case_id', '-external_case_id',
        'workshop_code', '-workshop_code',
        'employee_first_name', '-employee_first_name',
        'employee_last_name', '-employee_last_name',
        'date_submitted', '-date_submitted',
        'date_due', '-date_due',
        'date_scheduled', '-date_scheduled',
        'scheduled_release_date', '-scheduled_release_date',
        'status', '-status',
        'urgency', '-urgency',
        'tier', '-tier',
        'assigned_to', '-assigned_to',
        'date_completed', '-date_completed'
    ]
    if sort_by in allowed_sorts:
        cases = cases.order_by(sort_by)
    else:
        cases = cases.order_by('-date_submitted')
    
    # Get related data for filters
    members = _exclude_super_dev_users(User.objects.filter(role='member', is_active=True)).order_by('username')
    technicians = _exclude_super_dev_users(User.objects.filter(role='technician', is_active=True)).order_by('username')
    workshop_codes = Case.objects.exclude(status='draft').values_list('workshop_code', flat=True).distinct().order_by('workshop_code')
    
    # Calculate comprehensive analytics statistics (exclude drafts - those are member-only)
    all_cases = Case.objects.exclude(status='draft')
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
        'total_members': _exclude_super_dev_users(User.objects.filter(role='member', is_active=True)).count(),
        'total_technicians': _exclude_super_dev_users(User.objects.filter(role='technician', is_active=True)).count(),
        'avg_processing_time': 'N/A',  # Would require more complex calculation
        'submitted_pct': submitted_pct,
        'pending_review_pct': pending_review_pct,
        'completed_pct': completed_pct,
        'hold_pct': hold_pct,
    }
    quick_tiles = _build_staff_quick_tiles(tile_scope_cases, user, quick_tech)
    # "Need to Accept" reflects the global unassigned queue, not a per-tech count.
    # Submitted cases have no assigned_to yet, so filtering by tech always yields 0.
    if quick_tech and quick_tech != 'all':
        quick_tiles['submitted'] = Case.objects.filter(status='submitted').count()
    from django.db.models import Count as _Count, F as _F
    # Badge scoped to the assigned tech's own UnreadMessage rows only.
    # All staff see the same number for each case (owner's unread state).
    _manager_unread_map = {
        row['case_id']: row['cnt']
        for row in UnreadMessage.objects
            .filter(
                case_id__in=list(cases.values_list('pk', flat=True)),
                user=_F('case__assigned_to'),
            )
            .values('case_id').annotate(cnt=_Count('id'))
    }
    for case in cases:
        case.unread_message_count = _manager_unread_map.get(case.pk, 0)
    
    # Get active technicians for quick-filter buttons
    quick_technicians = _get_active_technicians()
    
    context = {
        'cases': cases,
        'stats': stats,
        'members': members,
        'technicians': technicians,
        'workshop_codes': workshop_codes,
        'status_filter': status_filter,
        'urgency_filter': urgency_filter,
        'tier_filter': tier_filter,
        'workshop_code_filter': workshop_code_filter,
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
        'filter_params': build_filter_params(request),
        'admin_preview': admin_preview,
        'quick_filter': quick_filter,
        'quick_tech': quick_tech,
        'quick_technicians': quick_technicians,
        'quick_tiles': quick_tiles,
    }
    
    return render(request, 'cases/manager_dashboard.html', context)


@login_required
def case_list(request):
    """Redirect to the appropriate dashboard based on user role."""
    user = request.user
    if user.role == 'administrator':
        return redirect('cases:admin_dashboard')
    elif user.role == 'manager':
        return redirect('cases:manager_dashboard')
    elif user.role == 'technician':
        return redirect('cases:technician_dashboard')
    else:
        return redirect('cases:member_dashboard')


@login_required
def delete_case(request, pk):
    """Delete a case - members can only delete draft cases, admins can delete any case"""
    case = get_object_or_404(Case, pk=pk)
    
    # Permission check
    can_delete = False
    redirect_to = 'home'
    
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
        employee_name = f'{case.employee_first_name} {case.employee_last_name}'.strip()
        
        # Get counts before deletion for the success message
        documents = case.documents.count()
        reports = case.reports.count()
        notes = case.case_notes.count()
        
        # Log deletion to audit trail BEFORE deleting
        from core.models import AuditLog
        AuditLog.log_activity(
            user=request.user,
            action_type='case_deleted',
            description=f'Case for {employee_name} permanently deleted ({documents} documents, {reports} reports, {notes} notes)',
            metadata={
                'case_id': case.id,
                'external_case_id': case.external_case_id,
                'employee_name': employee_name,
                'documents_count': documents,
                'reports_count': reports,
                'notes_count': notes,
            }
        )
        
        # Delete the case (cascade will handle related objects)
        case.delete()
        
        messages.success(request, f'Case for {employee_name} and all related data ({documents} documents, {reports} reports, {notes} notes) have been permanently deleted.')
        return redirect(redirect_to)
    
    # GET request - show confirmation page
    context = {
        'case': case,
        'documents_count': case.documents.count(),
        'reports_count': case.reports.count(),
        'notes_count': case.case_notes.count(),
    }
    return render(request, 'cases/confirm_delete_case.html', context)


def get_technical_notes_template():
    """Return the technical notes HTML template from database settings."""
    from core.models import SystemSettings
    settings = SystemSettings.get_settings()
    if settings.technical_notes_template:
        return settings.technical_notes_template
    # Fallback if DB is empty
    return """<h3><u>GENERAL</u></h3>
<p>&nbsp;</p>"""


@login_required
def get_notes_template(request):
    """AJAX endpoint: return the technical notes template from SystemSettings."""
    from django.http import JsonResponse
    if request.user.role not in ['technician', 'administrator', 'manager']:
        return JsonResponse({'success': False, 'error': 'Permission denied.'}, status=403)
    template_html = get_technical_notes_template()
    return JsonResponse({'success': True, 'template': template_html})


def accept_case(request, pk):
    """Accept a submitted case - technician/admin initial review"""
    import json
    from django.http import JsonResponse
    from django.utils import timezone
    from core.models import AuditLog
    from cases.models import CaseNotification
    from cases.services.email_service import send_case_accepted_email, send_new_case_assigned_email
    
    user = request.user
    case = get_object_or_404(Case, id=pk)
    
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
            leave_unassigned = body_data.get('leave_unassigned', False)  # New: option to leave unassigned
            acceptance_notes = (body_data.get('acceptance_notes') or '').strip()
            docs_verified = body_data.get('docs_verified', 'no')
            tech_override_reason = (body_data.get('tech_override_reason') or '').strip()
            credit_value = body_data.get('credit_value', '')  # Handle credit_value from form
            
            # Validation
            if not tier:
                return JsonResponse({
                    'success': False,
                    'error': 'Tier must be specified.'
                }, status=400)
            
            # Tier validation - only check accepting tech's level if they are assigning to themselves
            # If leaving unassigned or assigning to someone else, the accepting tech's level doesn't matter
            if user.role == 'technician' and not leave_unassigned and not assigned_to_id:
                # Tech is implicitly assigning to themselves - check level
                if tier == '2' and user.user_level == 'level_1':
                    if not acceptance_notes:
                        return JsonResponse({
                            'success': False,
                            'error': 'Your technician level (Level 1) cannot handle Tier 2 cases. Add a note to override.'
                        }, status=400)
                
                if tier == '3' and user.user_level in ['level_1', 'level_2']:
                    if not acceptance_notes:
                        return JsonResponse({
                            'success': False,
                            'error': f'Your technician level ({user.user_level.replace("_", " ").title()}) cannot handle Tier 3 cases. Add a note to override.'
                        }, status=400)
            
            # Tier validation - check if assigned tech level matches tier capability
            assigned_tech = None
            if assigned_to_id:
                try:
                    assigned_tech = User.objects.get(id=assigned_to_id, role__in=['technician', 'administrator'])
                except User.DoesNotExist:
                    return JsonResponse({
                        'success': False,
                        'error': 'Invalid technician selected.'
                    }, status=400)
                
                # Check tech level against tier (skip for administrators)
                if assigned_tech.role != 'administrator':
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
            # Normalize tier value: form sends '1','2','3' but model expects 'tier_1','tier_2','tier_3'
            case.tier = f'tier_{tier}' if tier and not tier.startswith('tier_') else tier
            case.date_accepted = timezone.now()
            case.accepted_by = user  # Track who did the acceptance (validation review)
            
            # Set credit value from acceptance form (with audit trail)
            if credit_value:
                try:
                    from decimal import Decimal
                    from cases.services.credit_service import set_case_credit
                    set_case_credit(case, Decimal(credit_value), user, 'acceptance', f'Set to {credit_value} during case acceptance')
                except (ValueError, TypeError):
                    pass  # Keep existing credit_value if invalid
            
            # Handle assignment
            if leave_unassigned:
                # Case is accepted (reviewed) but not assigned to anyone yet
                case.assigned_to = None
            elif assigned_to_id:
                # Explicit assignment to selected technician
                case.assigned_to = assigned_tech
            else:
                # This shouldn't happen with normal flow, but be safe
                # If they didn't say leave unassigned and didn't select someone, leave it unassigned
                case.assigned_to = None
            
            case.save()
            
            # Get IP address for audit
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            ip_address = x_forwarded_for.split(',')[0] if x_forwarded_for else request.META.get('REMOTE_ADDR')
            
            # Create comprehensive audit log entry
            member_name = f"{case.employee_first_name} {case.employee_last_name}".strip()
            description = f"Case accepted as Tier {tier} — {case.external_case_id} ({member_name})"
            if case.assigned_to:
                description += f", assigned to {case.assigned_to.get_full_name() or case.assigned_to.username}"
            if tech_override_reason:
                description += f" (OVERRIDE: {tech_override_reason[:50]}...)"
            if not docs_verified or docs_verified == 'no':
                description += " (docs not verified)"
            if acceptance_notes:
                description += f" - Notes: {acceptance_notes[:100]}"
            
            # Build comprehensive metadata for audit trail and display
            metadata = {
                'tier': tier,
                'credit_value': credit_value,  # Store the credit value
                'docs_verified': docs_verified,
                'acceptance_notes': acceptance_notes,
                'accepted_by_username': user.username,
                'accepted_by_name': user.get_full_name() or user.username,
                'assigned_to_username': case.assigned_to.username if case.assigned_to else None,
                'assigned_to_name': case.assigned_to.get_full_name() if case.assigned_to else None,
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
            
            # Auto-populate Technical Notes template if empty
            if not case.report_notes_to_member or not case.report_notes_to_member.strip():
                case.report_notes_to_member = get_technical_notes_template()
                case.save(update_fields=['report_notes_to_member'])
            
            # Handle "Accept & Put on Hold" combined action
            put_on_hold = body_data.get('put_on_hold', False)
            hold_reason = (body_data.get('hold_reason') or '').strip()
            
            if put_on_hold and hold_reason:
                from cases.services.case_audit_service import hold_case as hold_case_service
                hold_case_service(
                    case=case,
                    user=user,
                    reason=hold_reason,
                    hold_duration_days=None
                )
                
                # Create hold notification for member (respects portal preference)
                if case.member:
                    employee_name = f'{case.employee_first_name} {case.employee_last_name}'.strip()
                    _create_case_notification_if_allowed(
                        case=case,
                        member=case.member,
                        notification_type='case_put_on_hold',
                        title=f'Your case for {employee_name} has been placed on hold',
                        message=f'Your case requires additional attention. Please see the hold reason below for details.',
                        hold_reason=hold_reason,
                        is_read=False,
                        created_at=timezone.now()
                    )
                
                AuditLog.log_activity(
                    user=user,
                    action_type='case_put_on_hold',
                    description=f'Case accepted and immediately put on hold: {hold_reason[:100]}',
                    case=case,
                    changes={'status': ('accepted', 'hold')},
                    ip_address=ip_address,
                    metadata={'hold_reason': hold_reason, 'combined_accept_hold': True}
                )
                
                return JsonResponse({
                    'success': True,
                    'message': f'Case {case.external_case_id} has been accepted and placed on hold.'
                })
            
            # Send notification to assigned technician (if any and different from accepter)
            # DISABLED per email policy — technicians do not receive email notifications
            # Only send if case was actually assigned to someone
            if False and case.assigned_to and case.assigned_to != user:
                try:
                    from django.core.mail import send_mail
                    from django.template.loader import render_to_string
                    from cases.services.email_service import should_send_emails
                    
                    if should_send_emails():
                        email_context = {
                            'case': case,
                            'accepted_by': user.get_full_name() or user.username,
                            'tier': tier,
                            'case_detail_url': f"{request.build_absolute_uri('/')}cases/{case.pk}/"
                        }
                        
                        html_message = render_to_string('emails/case_accepted.html', email_context)
                        
                        send_mail(
                            subject=f'Case for {case.employee_first_name} {case.employee_last_name} - Accepted and Assigned to You',
                            message=f'Case for {case.employee_first_name} {case.employee_last_name} has been accepted as Tier {tier} and assigned to you.',
                            from_email='noreply@advisor-portal.com',
                            recipient_list=[case.assigned_to.email],
                            html_message=html_message,
                            fail_silently=True
                        )
                except Exception as e:
                    print(f"Error sending tech notification: {str(e)}")
            
            # Send notification to member
            # DISABLED per email policy — members only receive HOLD, CHAT, READY emails
            try:
                from django.core.mail import send_mail
                from django.template.loader import render_to_string
                from cases.services.email_service import should_send_emails
                
                if False and should_send_emails():
                    email_context = {
                        'case': case,
                        'tier': tier,
                        'member_name': case.member.get_full_name() or case.member.username,
                        'case_detail_url': f"{request.build_absolute_uri('/')}cases/{case.pk}/"
                    }
                    
                    html_message = render_to_string('emails/case_accepted_member.html', email_context)
                    
                    send_mail(
                        subject=f'Your Case for {case.employee_first_name} {case.employee_last_name} Has Been Accepted',
                        message=f'Your case for {case.employee_first_name} {case.employee_last_name} has been received and accepted by our team.',
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


@never_cache
@login_required
def case_detail(request, pk):
    """Case detail view"""
    user = request.user
    case = get_object_or_404(Case, pk=pk)
    
    # Permission check
    can_view = False
    can_edit = False
    is_delegate_viewer = False
    
    if user.role == 'member' and case.member == user:
        can_view = True
        can_edit = True  # Members can edit their own cases (add/remove documents)
    elif user.role == 'member':
        # Check if user is a delegate for the case's member
        from accounts.models import MemberDelegate
        is_delegate_viewer = MemberDelegate.objects.filter(
            delegate=user,
            member=case.member
        ).exists()
        if is_delegate_viewer:
            can_view = True
            can_edit = True  # Delegates get full access per MemberDelegate model rules
    
    if not can_view and user.role == 'technician':
        # Technicians can view submitted cases and cases assigned to them
        if case.status in ['submitted', 'accepted', 'hold', 'pending_review', 'completed', 'cancelled', 'declined'] or case.assigned_to == user:
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
            metadata={
                'message': 'Technician/Admin viewed case with member updates, flag reset'
            }
        )
    
    # Auto-mark all notifications for this case as read when member/delegate views the case
    if user.role == 'member' and (case.member == user or is_delegate_viewer):
        from cases.models import CaseNotification
        # For delegates, mark notifications addressed to the case's member
        notif_member = case.member if is_delegate_viewer else user
        unread_notifications = CaseNotification.objects.filter(
            case=case,
            member=notif_member,
            is_read=False
        )
        marked_count = 0
        for notif in unread_notifications:
            notif.mark_as_read()
            marked_count += 1
        if marked_count > 0:
            logger.info(f'Auto-marked {marked_count} notification(s) as read for member {user.username} on case {case.external_case_id}')

    # Log member/delegate case access
    if user.role == 'member' and (case.member == user or is_delegate_viewer):
        from core.models import AuditLog
        AuditLog.objects.create(
            user=user,
            action_type='case_accessed',
            case=case,
            metadata={
                'message': f'{"Delegate" if is_delegate_viewer else "Member"} viewed case {case.external_case_id}',
                'viewer': user.username,
            }
        )

    # Handle draft edit POST requests
    if request.method == 'POST' and request.POST.get('edit_draft'):
        if case.status == 'draft' and user.role == 'member' and (case.member == user or is_delegate_viewer):
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
    # 'documents' = member-submitted docs (exclude tech 'report' and 'other' types)
    # 'tech_documents' = technician/staff uploaded docs ('other' type)
    all_documents = CaseDocument.objects.filter(case=case).order_by('document_type', '-uploaded_at')
    documents = all_documents.exclude(document_type__in=['report', 'other'])
    
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
    # Members can ONLY see reports/notes when case is completed AND released to them
    can_view_report = True
    if user.role == 'member' and (case.member == user or is_delegate_viewer):
        # For members: only show report/docs if case is completed AND has been released
        # A case is "released" when:
        # 1. actual_release_date is set (released now or in the past), OR
        # 2. scheduled_release_date has passed (scheduled release is now ready)
        case_is_released = False
        
        if case.status == 'completed':
            if case.actual_release_date:
                # Case was released immediately or the scheduled release time has passed
                case_is_released = True
            elif case.scheduled_release_date and case.scheduled_release_date <= timezone.now():
                # Case has a scheduled release date that has already passed
                case_is_released = True
        
        # Members can only view if case is completed AND released
        if not case_is_released:
            can_view_report = False
    
    # Get technician documents (resources uploaded by staff, excludes reports)
    tech_documents = all_documents.filter(document_type='other').order_by('-uploaded_at')
    
    # Get case reports
    reports = case.reports.all().order_by('report_number')
    
    # Only technicians and administrators can upload reports
    # Also allow the reviewer to upload during pending_review
    is_reviewer = (case.status == 'pending_review' and user.role in ['technician', 'administrator'] and case.assigned_to != user)
    can_upload_reports = (user.role in ['technician', 'administrator'] and can_edit) or is_reviewer

    # Calculate the next available report number for additional uploads
    existing_report_numbers = set(case.reports.values_list('report_number', flat=True))
    max_existing = max(existing_report_numbers) if existing_report_numbers else 0
    next_report_number = max(case.num_reports_requested, max_existing) + 1
    
    # Check if user can release case immediately (case owner or admin, and case is scheduled for release)
    can_release_immediately = False
    if case.status == 'completed' and case.scheduled_release_date is not None:
        # Only case owner (assigned_to) or admin can release
        if user.role == 'administrator' or (user.role == 'technician' and case.assigned_to == user):
            can_release_immediately = True
    
    # Get available technicians for reassignment dropdown
    available_techs = _exclude_super_dev_users(User.objects.filter(role__in=['technician', 'administrator'], is_active=True)).order_by('first_name')
    
    # Get audit history for this case (Manager/Admin only)
    audit_logs = []
    acceptance_details = None
    case_event_logs = []  # Track all significant case events
    
    if user.role in ['manager', 'administrator']:
        from core.models import AuditLog
        from django.db.models import Q
        audit_logs = AuditLog.objects.filter(
            Q(case=case) | Q(document__case=case)
        ).select_related('user', 'case', 'document').order_by('-timestamp')[:15]
    
    # Get ALL case lifecycle events for comprehensive history (available to all roles)
    from core.models import AuditLog
    case_event_logs = AuditLog.objects.filter(
        case=case,
        action_type__in=[
            'case_submitted',
            'case_resubmitted',
            'case_accepted',
            'case_assigned',
            'case_reassigned',
            'case_tier_changed',
            'case_held',
            'case_resumed',
            'case_completed',
            'case_incomplete',
            'case_review_approved',
            'case_review_revisions',
            'case_review_corrected',
            'case_rejected',
            'case_cancelled',
            'case_declined',
            'case_rush_downgraded',
            'case_ownership_taken',
            'admin_ownership',
            'case_submitted_for_review',
            'document_uploaded',
            'member_document_uploaded',
            'error_flag_disputed',
        ]
    ).select_related('user').order_by('-timestamp')
    
    # Get acceptance details for display (available to assigned tech and managers/admins)
    if case.status in ['accepted', 'pending_review', 'completed']:
        from core.models import AuditLog
        acceptance_log = AuditLog.objects.filter(
            case=case,
            action_type='case_accepted'
        ).first()
        if acceptance_log and acceptance_log.metadata:
            acceptance_details = acceptance_log.metadata
    
    # Get resubmitted/modification cases linked to this case
    resubmitted_cases = Case.objects.filter(original_case=case).order_by('-created_at')
    
    # Get most recent hold event for timeline display (shows even after resume)
    hold_event_log = AuditLog.objects.filter(
        case=case,
        action_type='case_held'
    ).order_by('-timestamp').first()

    # Get latest review submission event for pending_review display
    latest_review_event = None
    if case.status == 'pending_review':
        latest_review_event = AuditLog.objects.filter(
            case=case,
            action_type='case_submitted_for_review'
        ).select_related('user').order_by('-timestamp').first()
    
    context = {
        'case': case,
        'can_edit': can_edit,
        'can_upload_reports': can_upload_reports,
        'next_report_number': next_report_number,
        'can_view_report': can_view_report,
        'can_view_internal_notes': can_view_internal_notes,
        'can_release_immediately': can_release_immediately,
        'documents': documents,
        'tech_documents': tech_documents,
        'case_notes': case_notes,
        'reports': reports,
        'available_techs': available_techs,
        'audit_logs': audit_logs,
        'acceptance_details': acceptance_details,
        'case_event_logs': case_event_logs,
        'hold_event_log': hold_event_log,
        'latest_review_event': latest_review_event,
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
        
        # Create in-app notification for member (respects portal preference)
        from cases.models import CaseNotification
        employee_name = f'{case.employee_first_name} {case.employee_last_name}'.strip()
        _create_case_notification_if_allowed(
            case=case,
            member=case.member,
            notification_type='case_released',
            title=f'Your case for {employee_name} is completed',
            message=f'Your case for {employee_name} has been completed and is ready for you to review.'
        )
        
        # Send case completed email to member
        try:
            from cases.services.email_service import send_case_completed_email
            send_case_completed_email(case, request=request, user=user)
        except Exception as email_error:
            logger.error(f'Failed to send case completed email for case {case_id}: {str(email_error)}')
        
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
def change_release_date(request, case_id):
    """Change the scheduled release date for a completed case, or release immediately"""
    from django.http import JsonResponse
    from django.utils import timezone
    from core.models import AuditLog
    
    user = request.user
    case = get_object_or_404(Case, id=case_id)
    
    # Permission check - case must be completed and not yet released
    if case.status != 'completed' or case.actual_release_date is not None:
        return JsonResponse({
            'success': False,
            'error': 'This case is not pending release.'
        }, status=400)
    
    # Permission check - only assigned tech, manager, or admin
    if user.role == 'technician' and case.assigned_to != user:
        return JsonResponse({'success': False, 'error': 'You can only modify cases you own.'}, status=403)
    if user.role not in ['technician', 'administrator', 'manager']:
        return JsonResponse({'success': False, 'error': 'Not authorized.'}, status=403)
    
    if request.method == 'POST':
        try:
            body_data = json.loads(request.body) if request.body else {}
            action = body_data.get('action', 'reschedule')  # 'reschedule' or 'release_now'
            
            old_release_date = case.scheduled_release_date
            
            if action == 'release_now':
                # Release immediately - preserve original date_completed from when tech finished
                case.actual_release_date = timezone.now()
                case.scheduled_release_date = None
                case.scheduled_email_date = None
                if not case.date_completed:
                    case.date_completed = timezone.now()  # Fallback only
                case.save()
                
                AuditLog.log_activity(
                    user=user,
                    action_type='other',
                    case=case,
                    description=f'Release date changed: released immediately (was scheduled for {old_release_date})',
                    metadata={'old_release_date': str(old_release_date), 'new_action': 'release_now'}
                )
                
                # Send case completed email to member
                try:
                    from cases.services.email_service import send_case_completed_email
                    send_case_completed_email(case, request=request, user=user)
                except Exception as email_error:
                    logger.error(f'Failed to send case completed email for case {case_id}: {str(email_error)}')
                
                return JsonResponse({
                    'success': True,
                    'message': 'Case released immediately to member.'
                })
            elif action == 'reschedule_delay':
                # Short delay preset (1h / 2h / 3h / 6h) - compute from now server-side
                from cases.services.timezone_service import calculate_release_time_cst, convert_to_scheduled_date_cst
                delay_hours = int(body_data.get('completion_delay_hours', 1))
                if delay_hours not in [1, 2, 3, 6]:
                    delay_hours = 1
                release_time_cst = calculate_release_time_cst(delay_hours)
                release_dt_utc = convert_to_scheduled_date_cst(release_time_cst)
                case.scheduled_release_date = release_dt_utc
                case.scheduled_email_date = release_dt_utc
                case.save()

                import pytz
                cst = pytz.timezone('US/Central')
                release_date_str = release_dt_utc.astimezone(cst).strftime('%b %d, %Y at %I:%M %p %Z')

                AuditLog.log_activity(
                    user=user,
                    action_type='other',
                    case=case,
                    description=f'Release rescheduled: {delay_hours}h delay from now → {release_date_str} (was {old_release_date})',
                    metadata={'old_release_date': str(old_release_date), 'new_release_date': str(release_dt_utc), 'delay_hours': delay_hours}
                )

                return JsonResponse({
                    'success': True,
                    'message': f'Release rescheduled for {release_date_str}.'
                })
            else:
                # Reschedule
                new_datetime_str = body_data.get('release_datetime')
                if not new_datetime_str:
                    return JsonResponse({'success': False, 'error': 'Please provide a release date and time.'}, status=400)
                
                from datetime import datetime
                import pytz
                
                release_dt_naive = datetime.strptime(new_datetime_str, '%Y-%m-%d %H:%M')
                cst = pytz.timezone('US/Central')
                release_dt_cst = cst.localize(release_dt_naive)
                release_dt_utc = release_dt_cst.astimezone(pytz.UTC)
                
                case.scheduled_release_date = release_dt_utc
                case.scheduled_email_date = release_dt_utc
                case.save()
                
                release_date_str = release_dt_cst.strftime('%b %d, %Y at %I:%M %p %Z')
                
                AuditLog.log_activity(
                    user=user,
                    action_type='other',
                    case=case,
                    description=f'Release date changed from {old_release_date} to {release_date_str}',
                    metadata={'old_release_date': str(old_release_date), 'new_release_date': str(release_dt_utc)}
                )
                
                return JsonResponse({
                    'success': True,
                    'message': f'Release date updated to {release_date_str}.'
                })
                
        except (ValueError, AttributeError) as e:
            return JsonResponse({'success': False, 'error': f'Invalid date format: {str(e)}'}, status=400)
        except Exception as e:
            logger.error(f'Error changing release date for case {case_id}: {str(e)}', exc_info=True)
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    
    return JsonResponse({'success': False, 'error': 'POST required.'}, status=405)


@login_required
def put_case_on_hold(request, case_id):
    """
    Put a case on hold with comprehensive notification system.
    
    FUNCTIONALITY:
    - Changes case status from 'submitted' or 'accepted' to 'hold'
    - Saves original status in status_before_hold for correct resume
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
    - Only cases in 'submitted' or 'accepted' status can be placed on hold
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
    
    # Technicians can only hold their own assigned cases (or unassigned submitted cases)
    if user.role == 'technician' and case.assigned_to and case.assigned_to != user:
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
    
    # Cases in active working statuses can be placed on hold
    holdable_statuses = ['submitted', 'accepted', 'resubmitted', 'pending_review']
    if case.status not in holdable_statuses:
        return JsonResponse({
            'success': False,
            'error': f'This case cannot be put on hold because its current status is "{case.get_status_display()}". Please refresh the page to see the latest status.'
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
                employee_name = f'{case.employee_first_name} {case.employee_last_name}'.strip()
                notification = _create_case_notification_if_allowed(
                    case=case,
                    member=case.member,
                    notification_type='case_put_on_hold',
                    title=f'Your case for {employee_name} has been placed on hold',
                    message=f'Your case requires additional attention. Please see the hold reason below for details.',
                    hold_reason=reason,
                    is_read=False,
                    created_at=timezone.now()
                )
                
                # Log notification creation in audit trail
                AuditLog.objects.create(
                    case=case,
                    user=user,
                    action_type='other',
                    description=f'In-app notification created for member ({case.member.email}) - case put on hold',
                    metadata={
                        'notification_id': notification.id,
                        'notification_type': 'case_put_on_hold',
                        'hold_reason': reason,
                        'recipient': case.member.email,
                        'message': notification.message,
                        'sub_action': 'notification_created'
                    }
                )
                
                # ================================================================
                # SEND EMAIL TO MEMBER
                # ================================================================
                
                try:
                    # Build absolute case detail URL
                    from django.urls import reverse
                    from django.contrib.sites.shortcuts import get_current_site
                    from cases.services.email_service import should_send_emails
                    
                    if not should_send_emails():
                        logger.info(f'Email notifications disabled. Skipped hold email for case {case_id}')
                    else:
                        from django.conf import settings as django_settings
                        
                        protocol = 'https' if request.is_secure() else 'http'
                        domain = get_current_site(request).domain
                        base_url = f"{protocol}://{domain}"
                        case_detail_url = f"{base_url}{reverse('cases:case_detail', args=[case.id])}"
                        logo_url = f"{base_url}/static/images/RevisedCoverPageLogo.png"
                        
                        # Prepare email context
                        email_context = {
                            'member_name': case.member.get_full_name() or case.member.username,
                            'member_first_name': case.member.first_name or case.member.username,
                            'case_id': case.external_case_id,
                            'employee_name': f"{case.employee_first_name} {case.employee_last_name}",
                            'hold_reason': reason,
                            'case_detail_url': case_detail_url,
                            'logo_url': logo_url,
                            'app_name': 'Advisor Portal'
                        }
                        
                        # Render email content (both text and HTML)
                        email_subject = f'ON HOLD: The case for {case.employee_first_name} {case.employee_last_name} needs your attention!'
                        text_message = render_to_string('emails/case_on_hold.txt', email_context)
                        html_message = render_to_string('emails/case_on_hold.html', email_context)
                        
                        # Get all recipients (member + delegates)
                        from cases.services.email_service import get_case_recipient_emails
                        hold_recipients = get_case_recipient_emails(case)
                        
                        # Send email with both text and HTML versions
                        send_mail(
                            subject=email_subject,
                            message=text_message,
                            from_email=django_settings.DEFAULT_FROM_EMAIL,
                            recipient_list=hold_recipients,
                            html_message=html_message,
                            fail_silently=False
                        )
                        
                        # Log successful email send in audit trail
                        AuditLog.objects.create(
                            case=case,
                            user=user,
                            action_type='email_notification_sent',
                            description=f'Hold notification email sent to {hold_recipients} - case put on hold',
                            metadata={
                                'email_to': str(hold_recipients),
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
                        action_type='other',
                        description=f'Failed to send member notification email to {case.member.email} - case put on hold',
                        metadata={
                            'email_to': case.member.email,
                            'error': str(email_error),
                            'notification_id': notification.id,
                            'sub_action': 'email_failed'
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
    """Resume a case from hold - preserves ownership, restores pre-hold status"""
    from django.http import JsonResponse
    from cases.services.case_audit_service import resume_case
    from cases.services.email_service import send_case_hold_resumed_email
    from cases.models import CaseNotification
    from core.models import AuditLog
    
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
            
            # Use status_before_hold to restore correct pre-hold status
            restore_status = case.status_before_hold or 'accepted'
            
            # Use the service to resume the case
            success = resume_case(
                case=case,
                user=user,
                reason=reason,
                previous_status=restore_status
            )
            
            if success:
                # Create in-app notification for member (mirrors hold notification)
                employee_name = f'{case.employee_first_name} {case.employee_last_name}'.strip()
                if case.member:
                    try:
                        notification = _create_case_notification_if_allowed(
                            case=case,
                            member=case.member,
                            notification_type='case_resumed',
                            title=f'Your case for {employee_name} has been resumed',
                            message=f'Your case for {employee_name} has been resumed and is now being actively worked on. Reason: {reason}',
                            is_read=False
                        )
                        
                        AuditLog.objects.create(
                            user=user,
                            action_type='other',
                            description=f'Resume notification created for case #{case.external_case_id}',
                            case=case,
                            metadata={
                                'sub_action': 'notification_created',
                                'notification_type': 'case_resumed',
                                'notification_id': notification.id,
                                'member_id': case.member.id
                            }
                        )
                    except Exception as notif_err:
                        logger.warning(f'Failed to create resume notification for case {case_id}: {notif_err}')
                
                # Send resume notification email to member
                try:
                    send_case_hold_resumed_email(case)
                except Exception as email_err:
                    logger.warning(f'Failed to send resume email for case {case_id}: {email_err}')
                
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
def downgrade_rush_to_standard(request, case_id):
    """
    Downgrade a rush case to normal (standard 7-day) urgency without cancelling it.
    Used when ProFeds cannot honour the rush timeline but CAN process the case.
    Notifies the advisor of the new due date and records the action in the audit trail.
    """
    from django.http import JsonResponse
    from core.models import AuditLog
    from cases.utils_holidays import calculate_due_date

    user = request.user
    case = get_object_or_404(Case, id=case_id)

    if user.role not in ['administrator', 'manager', 'technician']:
        return JsonResponse({'success': False, 'error': 'Staff only.'}, status=403)

    if case.urgency != 'rush':
        return JsonResponse({'success': False, 'error': 'This case is not marked as rush.'}, status=400)

    if case.status in ['completed', 'cancelled', 'declined', 'draft']:
        return JsonResponse({'success': False, 'error': 'Cannot modify urgency on a closed case.'}, status=400)

    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method.'}, status=405)


@login_required
@require_http_methods(["POST"])
def accept_and_refuse_rush(request, case_id):
    """
    Combined action: accept a submitted rush case AND downgrade urgency to standard in one step.
    Validates the same Initial Case Review checklist as accept_case, then applies both changes.
    """
    import json
    from django.http import JsonResponse
    from core.models import AuditLog
    from cases.utils_holidays import calculate_due_date

    user = request.user
    case = get_object_or_404(Case, id=case_id)

    if user.role not in ['administrator', 'manager', 'technician']:
        return JsonResponse({'success': False, 'error': 'Staff only.'}, status=403)

    if case.status != 'submitted':
        return JsonResponse({'success': False, 'error': 'Only submitted cases can be accepted.'}, status=400)

    if case.urgency != 'rush':
        return JsonResponse({'success': False, 'error': 'This case is not marked as rush.'}, status=400)

    try:
        body_data = json.loads(request.body) if request.body else {}
        note          = body_data.get('note', '').strip()
        tier          = body_data.get('tier', '').strip()
        credit_value  = body_data.get('credit_value', '').strip()
        assigned_to_id = body_data.get('assigned_to')
        leave_unassigned = body_data.get('leave_unassigned', False)
        acceptance_notes = (body_data.get('acceptance_notes') or '').strip()
        docs_verified = body_data.get('docs_verified', 'no')
        tech_override_reason = (body_data.get('tech_override_reason') or '').strip()

        if not note:
            return JsonResponse({'success': False, 'error': 'A reason is required.'}, status=400)
        if not tier:
            return JsonResponse({'success': False, 'error': 'Tier must be selected before accepting.'}, status=400)
        if not credit_value:
            return JsonResponse({'success': False, 'error': 'Credit value must be selected before accepting.'}, status=400)

        # Validate assigned tech level vs tier
        assigned_tech = None
        if assigned_to_id:
            try:
                assigned_tech = User.objects.get(id=assigned_to_id, role__in=['technician', 'administrator'])
            except User.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Invalid technician selected.'}, status=400)

            if assigned_tech.role != 'administrator':
                tech_level_num = {'level_1': 1, 'level_2': 2, 'level_3': 3}.get(assigned_tech.user_level, 0)
                if tech_level_num < int(tier):
                    if user.role != 'administrator':
                        return JsonResponse({'success': False,
                            'error': f'{assigned_tech.get_full_name()} level does not meet Tier {tier} requirement.'}, status=400)
                    if not tech_override_reason:
                        return JsonResponse({'success': False, 'error': 'Override reason required.'}, status=400)

        # -- Step 1: Accept the case -------------------------------------------
        case.status     = 'accepted'
        case.tier       = f'tier_{tier}' if not tier.startswith('tier_') else tier
        case.date_accepted = timezone.now()
        case.accepted_by = user

        if credit_value:
            try:
                from decimal import Decimal
                from cases.services.credit_service import set_case_credit
                set_case_credit(case, Decimal(credit_value), user, 'acceptance',
                                f'Set to {credit_value} during accept & refuse rush')
            except (ValueError, TypeError):
                pass

        if leave_unassigned:
            case.assigned_to = None
        elif assigned_tech:
            case.assigned_to = assigned_tech
        else:
            case.assigned_to = None

        # -- Step 2: Downgrade rush urgency ------------------------------------
        from core.models import SystemSettings
        sys_settings = SystemSettings.get_settings()
        submitted_date = case.date_submitted.date() if case.date_submitted else timezone.localtime(timezone.now()).date()
        new_due_date, _ = calculate_due_date(submitted_date, base_days=sys_settings.default_case_due_days)

        old_due_date  = case.date_due
        case.urgency  = 'normal'
        case.date_due = new_due_date
        case.save()

        employee_name = f'{case.employee_first_name} {case.employee_last_name}'.strip()

        # Audit � acceptance
        AuditLog.objects.create(
            case=case, user=user, action_type='case_accepted',
            description=(f'Case accepted as Tier {tier} with rush refused � '
                         f'{case.external_case_id} ({employee_name})'),
            metadata={
                'tier': tier,
                'credit_value': credit_value,
                'assigned_to': assigned_tech.username if assigned_tech else None,
                'docs_verified': docs_verified,
                'acceptance_notes': acceptance_notes,
                'tech_override_reason': tech_override_reason or None,
            }
        )

        # Audit � rush downgrade
        AuditLog.objects.create(
            case=case, user=user, action_type='case_rush_downgraded',
            description=(f'Rush refused at acceptance by {user.get_full_name() or user.username}. '
                         f'New due date: {new_due_date.strftime("%m/%d/%Y")}. Note: {note}'),
            metadata={
                'downgraded_by': user.username,
                'old_due_date': str(old_due_date),
                'new_due_date': str(new_due_date),
                'note': note,
            }
        )

        # Post system message to Case Chat
        from cases.models import CaseMessage
        chat_msg = CaseMessage.objects.create(
            case=case,
            author=user,
            message=(
                f'Rush processing is not available for this case. '
                f'Your case will be processed on the standard timeline with a new due date of '
                f'{new_due_date.strftime("%m/%d/%Y")}.'
                + (f'\n\nReason: {note}' if note else '')
            )
        )
        if case.member:
            UnreadMessage.objects.get_or_create(
                message=chat_msg, user=case.member, defaults={'case': case}
            )

        # In-app notification + email to advisor
        if case.member:
            _create_case_notification_if_allowed(
                case=case, member=case.member,
                notification_type='case_on_hold',
                title=f'Update: Your case for {employee_name}',
                message=(
                    f'Rush processing is not available for this case. '
                    f'Your case has been moved to standard processing with a new due date of '
                    f'{new_due_date.strftime("%m/%d/%Y")}.'
                    + (f' Note from ProFeds: {note}' if note else '')
                ),
                hold_reason='Rush processing not available � standard 7-day turnaround applies.',
                is_read=False, created_at=timezone.now()
            )

            from cases.services.email_service import send_email_notification, get_case_recipient_emails
            from django.conf import settings as _dj_settings
            _site_url = getattr(_dj_settings, 'SITE_URL', 'https://portal.profeds.com')
            recipients = get_case_recipient_emails(case)
            for email in recipients:
                send_email_notification(
                    subject=f'UPDATE: The case for {employee_name} has a revised due date!',
                    template_name='case_rush_not_accepted.html',
                    context={
                        'member_name': case.member.get_full_name() or case.member.username,
                        'member_first_name': case.member.first_name or case.member.username,
                        'employee_name': employee_name,
                        'new_due_date': new_due_date.strftime('%B %d, %Y'),
                        'note': note,
                        'case_detail_url': f'{_site_url}/cases/{case.id}/',
                        'logo_url': f'{_site_url}/static/images/RevisedCoverPageLogo.png',
                    },
                    recipient_email=email, case=case, user=user,
                )

        return JsonResponse({
            'success': True,
            'new_due_date': new_due_date.strftime('%m/%d/%Y'),
            'message': f'Case accepted with standard timeline. New due date: {new_due_date.strftime("%m/%d/%Y")}.',
        })

    except Exception as e:
        logger.error(f'Error in accept_and_refuse_rush for case {case_id}: {e}', exc_info=True)
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
        return JsonResponse({'success': False, 'error': 'Invalid request method.'}, status=405)

    try:
        body_data = json.loads(request.body) if request.body else {}
        note = body_data.get('note', '').strip()

        from core.models import SystemSettings
        sys_settings = SystemSettings.get_settings()
        submitted_date = case.date_submitted.date() if case.date_submitted else timezone.localtime(timezone.now()).date()
        new_due_date, _ = calculate_due_date(submitted_date, base_days=sys_settings.default_case_due_days)

        old_due_date = case.date_due
        case.urgency = 'normal'
        case.date_due = new_due_date
        case.save(update_fields=['urgency', 'date_due'])

        AuditLog.objects.create(
            case=case,
            user=user,
            action_type='case_rush_downgraded',
            description=(
                f'Rush urgency downgraded to Standard by {user.get_full_name() or user.username}. '
                f'New due date: {new_due_date.strftime("%m/%d/%Y")}.'
                + (f' Note: {note}' if note else '')
            ),
            metadata={
                'downgraded_by': user.username,
                'old_due_date': str(old_due_date),
                'new_due_date': str(new_due_date),
                'note': note,
            }
        )

        # Post a system message to the Case Chat � visible to both advisor and tech
        from cases.models import CaseMessage
        chat_msg = CaseMessage.objects.create(
            case=case,
            author=user,
            message=(
                f'Rush processing is not available for this case. '
                f'Your case will be processed on the standard timeline with a new due date of '
                f'{new_due_date.strftime("%m/%d/%Y")}.'
                + (f'\n\nReason: {note}' if note else '')
            )
        )
        if case.member:
            UnreadMessage.objects.get_or_create(
                message=chat_msg, user=case.member, defaults={'case': case}
            )

        # In-app notification for advisor
        if case.member:
            employee_name = f'{case.employee_first_name} {case.employee_last_name}'.strip()
            _create_case_notification_if_allowed(
                case=case,
                member=case.member,
                notification_type='case_on_hold',
                title=f'Update: Your case for {employee_name}',
                message=(
                    f'Rush processing is not available for this case. '
                    f'Your case has been moved to standard processing with a new due date of '
                    f'{new_due_date.strftime("%m/%d/%Y")}.'
                    + (f' Note from ProFeds: {note}' if note else '')
                ),
                hold_reason='Rush processing not available � standard 7-day turnaround applies.',
                is_read=False,
                created_at=timezone.now()
            )

            # Email the advisor
            from cases.services.email_service import send_email_notification, get_case_recipient_emails
            from django.conf import settings as _dj_settings
            _site_url = getattr(_dj_settings, 'SITE_URL', 'https://portal.profeds.com')
            recipients = get_case_recipient_emails(case)
            for email in recipients:
                send_email_notification(
                    subject=f'UPDATE: The case for {employee_name} has a revised due date!',
                    template_name='case_rush_not_accepted.html',
                    context={
                        'member_name': case.member.get_full_name() or case.member.username,
                        'member_first_name': case.member.first_name or case.member.username,
                        'employee_name': employee_name,
                        'new_due_date': new_due_date.strftime('%B %d, %Y'),
                        'note': note,
                        'case_detail_url': f'{_site_url}/cases/{case.id}/',
                        'logo_url': f'{_site_url}/static/images/RevisedCoverPageLogo.png',
                    },
                    recipient_email=email,
                    case=case,
                    user=user,
                )

        return JsonResponse({
            'success': True,
            'new_due_date': new_due_date.strftime('%m/%d/%Y'),
            'message': f'Rush downgraded to Standard. New due date: {new_due_date.strftime("%m/%d/%Y")}.',
        })

    except Exception as e:
        logger.error(f'Error downgrading rush for case {case_id}: {e}', exc_info=True)
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
def decline_case(request, case_id):
    """
    Decline a case on behalf of ProFeds staff (Admin, Manager, or Technician).

    Used when a submitted case cannot be processed (e.g., NAF employee, out-of-scope
    request). Sets status to 'cancelled', notifies the member with a reason, and
    logs a full audit trail. Metadata includes declined_by_staff=True to distinguish
    this action from a member-initiated cancellation.

    POST JSON:
        reason (required): Why the case is being declined.
    """
    from django.http import JsonResponse
    from cases.models import CaseNotification
    from core.models import AuditLog
    from django.core.mail import send_mail
    from django.template.loader import render_to_string
    from django.utils import timezone

    user = request.user
    case = get_object_or_404(Case, id=case_id)

    if user.role not in ['administrator', 'manager', 'technician']:
        return JsonResponse({'success': False, 'error': 'Only staff members can decline cases.'}, status=403)

    declinable_statuses = ['submitted', 'resubmitted', 'accepted', 'hold', 'pending_review', 'needs_resubmission']
    if case.status not in declinable_statuses:
        return JsonResponse({
            'success': False,
            'error': f'This case cannot be declined because its current status is "{case.get_status_display()}".'
        }, status=400)

    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method.'}, status=405)

    try:
        body_data = json.loads(request.body) if request.body else {}
        reason = body_data.get('reason', '').strip()

        if not reason:
            return JsonResponse({'success': False, 'error': 'Please provide a reason for declining the case.'}, status=400)

        # Update case status to 'declined' (distinct from member-initiated 'cancelled')
        case.status = 'declined'
        case.urgency = 'normal'  # Clear rush urgency on terminal cases
        case.save(update_fields=['status', 'urgency'])

        # Audit log
        AuditLog.objects.create(
            case=case,
            user=user,
            action_type='case_declined',
            description=f'Case declined by {user.get_full_name() or user.username}: {reason}',
            metadata={
                'declined_by_staff': True,
                'decline_reason': reason,
                'declined_by': user.username,
            }
        )

        # In-app notification for member
        if case.member:
            employee_name = f'{case.employee_first_name} {case.employee_last_name}'.strip()
            notification = _create_case_notification_if_allowed(
                case=case,
                member=case.member,
                notification_type='case_declined',
                title=f'Your case for {employee_name} has been declined',
                message=f'Unfortunately, ProFeds is unable to process this case. Please see the reason below.',
                hold_reason=reason,
                is_read=False,
                created_at=timezone.now()
            )

            AuditLog.objects.create(
                case=case,
                user=user,
                action_type='other',
                description=f'In-app decline notification created for member ({case.member.email})',
                metadata={
                    'notification_id': notification.id,
                    'notification_type': 'case_declined',
                    'decline_reason': reason,
                    'sub_action': 'notification_created'
                }
            )

            # Post a system message to the Case Chat � visible to both advisor and tech
            from cases.models import CaseMessage
            chat_msg = CaseMessage.objects.create(
                case=case,
                author=user,
                message=f'This case has been declined by ProFeds.\n\nReason: {reason}'
            )
            UnreadMessage.objects.get_or_create(
                message=chat_msg, user=case.member, defaults={'case': case}
            )

            # Send decline email
            try:
                from django.urls import reverse
                from django.contrib.sites.shortcuts import get_current_site
                from cases.services.email_service import should_send_emails, get_case_recipient_emails
                from django.conf import settings as django_settings

                if not should_send_emails():
                    logger.info(f'Email notifications disabled. Skipped decline email for case {case_id}')
                else:
                    protocol = 'https' if request.is_secure() else 'http'
                    domain = get_current_site(request).domain
                    base_url = f"{protocol}://{domain}"
                    case_detail_url = f"{base_url}{reverse('cases:case_detail', args=[case.id])}"
                    logo_url = f"{base_url}/static/images/RevisedCoverPageLogo.png"

                    email_context = {
                        'member_name': case.member.get_full_name() or case.member.username,
                        'member_first_name': case.member.first_name or case.member.username,
                        'case_id': case.external_case_id,
                        'employee_name': f"{case.employee_first_name} {case.employee_last_name}",
                        'decline_reason': reason,
                        'case_detail_url': case_detail_url,
                        'logo_url': logo_url,
                        'app_name': 'Advisor Portal'
                    }

                    email_subject = f'Case Declined: {case.employee_first_name} {case.employee_last_name}'
                    text_message = render_to_string('emails/case_declined.txt', email_context)
                    html_message = render_to_string('emails/case_declined.html', email_context)

                    recipients = get_case_recipient_emails(case)
                    send_mail(
                        subject=email_subject,
                        message=text_message,
                        from_email=django_settings.DEFAULT_FROM_EMAIL,
                        recipient_list=recipients,
                        html_message=html_message,
                        fail_silently=False
                    )

                    AuditLog.objects.create(
                        case=case,
                        user=user,
                        action_type='email_notification_sent',
                        description=f'Decline notification email sent to {recipients}',
                        metadata={
                            'email_to': str(recipients),
                            'email_subject': email_subject,
                            'decline_reason': reason,
                        }
                    )

            except Exception as email_error:
                logger.error(f'Failed to send decline email for case {case_id}: {str(email_error)}')

        return JsonResponse({
            'success': True,
            'message': f'Case {case.external_case_id} has been declined. The member has been notified.',
            'new_status': case.status,
        })

    except Exception as e:
        logger.error(f'Error declining case {case_id}: {str(e)}', exc_info=True)
        return JsonResponse({'success': False, 'error': f'An error occurred: {str(e)}'}, status=500)


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
        # But preserve hold status if the case is currently on hold
        if case.status != 'hold':
            case.status = 'accepted'
        case.save()
        
        # Create audit log entry
        from core.models import AuditLog
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        ip_address = x_forwarded_for.split(',')[0] if x_forwarded_for else request.META.get('REMOTE_ADDR')
        
        previous_owner_name = previous_owner.get_full_name() if previous_owner else 'Unassigned'
        member_name = f"{case.employee_first_name} {case.employee_last_name}".strip()
        description = f"Admin took ownership of {case.external_case_id} — {member_name} (was: {previous_owner_name})"
        
        AuditLog.log_activity(
            user=user,
            action_type='case_ownership_taken',
            description=description,
            case=case,
            changes={
                'assigned_to': (previous_owner.username if previous_owner else None, user.username)
            },
            ip_address=ip_address,
            metadata={
                'previous_assignee': previous_owner_name,
                'new_assignee': user.get_full_name() or user.username,
                'case_tier': case.tier,
                'accepted_by': case.accepted_by.get_full_name() if case.accepted_by else None,
                'admin_override': True
            }
        )
        
        # Log the action
        messages.success(
            request, 
            f'You have taken ownership of case {case.external_case_id}. Previous owner: {previous_owner_name}. Status: {case.get_status_display()}'
        )
        
        return redirect('cases:admin_dashboard')
    
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
    
    # Permission check - only the member who owns the case (or their delegate) can edit
    is_delegate = False
    if user.role != 'member':
        messages.error(request, 'You do not have permission to edit this case.')
        return redirect('cases:case_detail', pk=pk)
    if case.member != user:
        from accounts.models import MemberDelegate
        is_delegate = MemberDelegate.objects.filter(delegate=user, member=case.member).exists()
        if not is_delegate:
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
        # Allow due date changes on draft and submitted cases
        if case.status in ['draft', 'submitted']:
            due_date_str = request.POST.get('date_due', '')
            if due_date_str:
                try:
                    from datetime import datetime as dt
                    due_date = dt.strptime(due_date_str, '%Y-%m-%d').date()
                except (ValueError, TypeError):
                    due_date = case.date_due
            else:
                due_date = case.date_due
        else:
            due_date = case.date_due  # Preserve existing due date for non-editable statuses
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

        # If due date is editable in this status, enforce urgency from due date.
        # This keeps urgency label in sync when advisor moves due date in/out of rush window.
        if case.status in ['draft', 'submitted'] and due_date:
            from datetime import timedelta
            try:
                threshold_days = int(SystemSettings.get_settings().rush_case_threshold_days or 7)
            except Exception:
                threshold_days = 7
            threshold_days = max(threshold_days, 1)
            today = timezone.localtime(timezone.now()).date()
            urgency = 'rush' if due_date < (today + timedelta(days=threshold_days)) else 'normal'
        
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
                action_type='case_updated',
                case=case,
                metadata=audit_details
            )
        
        messages.success(request, 'Case details updated successfully.')
        return redirect('cases:case_detail', pk=pk)
    
    # Get existing documents for this case
    documents = CaseDocument.objects.filter(case=case).order_by('-uploaded_at')
    
    context = {
        'case': case,
        'documents': documents,
    }
    return render(request, 'cases/edit_case.html', context)


@login_required
def reassign_case(request, case_id):
    """
    Reassign a case to a different technician/administrator.
    
    REQUIREMENTS:
    - Case must be in 'accepted', 'hold', 'pending_review', or 'completed' status
    - Technicians can only reassign cases they own
    - Managers and administrators can reassign any qualifying case
    - Full audit trail via case_audit_service.reassign_case()
    - Populates reassignment_history JSON field on Case model
    - Creates StaffNotification for the new assignee
    - Tracks event in Case Event History
    """
    from django.http import JsonResponse
    from cases.services.case_audit_service import reassign_case as reassign_case_service
    from core.models import AuditLog, StaffNotification
    
    user = request.user
    case = get_object_or_404(Case, id=case_id)
    
    # Permission check - technicians, managers, and administrators can reassign cases
    if user.role not in ['technician', 'administrator', 'manager']:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
        messages.error(request, 'Permission denied')
        return redirect('cases:case_detail', pk=case_id)
    
    # Status check — allow reassignment for active workflow cases and completed cases.
    # Completed reassignment is useful for post-release follow-up collaboration.
    if case.status not in ['accepted', 'hold', 'pending_review', 'completed']:
        error_msg = f'Only cases in Accepted, On Hold, Pending Review, or Completed status can be reassigned. Current status: {case.get_status_display()}'
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': error_msg}, status=400)
        messages.error(request, error_msg)
        return redirect('cases:case_detail', pk=case_id)
    
    if request.method == 'POST':
        new_technician_id = request.POST.get('assigned_to')
        reason = request.POST.get('reason', '').strip() or 'Manual reassignment'
        
        if not new_technician_id:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': 'No technician selected'}, status=400)
            messages.error(request, 'No technician selected')
            return redirect('cases:case_detail', pk=case_id)
        
        try:
            # Allow both technicians and administrators to be assigned
            new_technician = User.objects.get(
                id=new_technician_id,
                role__in=['technician', 'administrator'],
                is_active=True
            )
            
            # Don't reassign to the same person
            if case.assigned_to and case.assigned_to.id == new_technician.id:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'error': 'Case is already assigned to this person'}, status=400)
                messages.warning(request, 'Case is already assigned to this person')
                return redirect('cases:case_detail', pk=case_id)
            
            old_technician = case.assigned_to
            
            # Use the service layer for reassignment (audit trail + history)
            success = reassign_case_service(
                case=case,
                user=user,
                new_technician=new_technician,
                reason=reason
            )
            
            if success:
                new_name = new_technician.get_full_name() or new_technician.username
                
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': True,
                        'message': f'Case reassigned to {new_name}',
                        'new_assignee': new_name
                    })
                else:
                    messages.success(request, f'Case reassigned to {new_name}')
                    return redirect('cases:case_detail', pk=case_id)
            else:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'error': 'Failed to reassign case. Please try again.'}, status=500)
                messages.error(request, 'Failed to reassign case. Please try again.')
                return redirect('cases:case_detail', pk=case_id)
                
        except User.DoesNotExist:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': 'Selected user not found or not eligible for assignment'}, status=404)
            messages.error(request, 'Selected user not found or not eligible for assignment')
            return redirect('cases:case_detail', pk=case_id)
    
    return redirect('cases:case_detail', pk=case_id)


@login_required
@require_http_methods(["POST"])
def change_case_tier(request, case_id):
    """Allow the assigned technician to change the tier after acceptance.

    The change is limited to the assigned technician and to accepted/hold cases.
    Every change requires a reason and is written to the audit trail.
    """
    from django.http import JsonResponse
    from cases.services.case_audit_service import change_case_tier as change_case_tier_service

    user = request.user
    case = get_object_or_404(Case, id=case_id)

    try:
        body = json.loads(request.body) if request.body else {}
    except json.JSONDecodeError:
        body = {}

    new_tier = (body.get('tier') or '').strip()
    reason = (body.get('reason') or '').strip()

    if user.role != 'technician':
        return JsonResponse({'success': False, 'error': 'Only the assigned technician can change Tier.'}, status=403)

    if case.assigned_to_id != user.id:
        return JsonResponse({'success': False, 'error': 'You can only change Tier on cases assigned to you.'}, status=403)

    if case.status not in ['accepted', 'hold']:
        return JsonResponse({'success': False, 'error': f'Tier can only be changed after acceptance while the case is Accepted or On Hold. Current status: {case.get_status_display()}.'}, status=400)

    if new_tier not in dict(Case.TIER_CHOICES):
        return JsonResponse({'success': False, 'error': 'Please select a valid Tier.'}, status=400)

    if not reason:
        return JsonResponse({'success': False, 'error': 'A reason is required to change Tier.'}, status=400)

    if case.tier == new_tier:
        return JsonResponse({'success': False, 'error': 'This case is already set to that Tier.'}, status=400)

    success = change_case_tier_service(case, user, new_tier, reason)
    if success:
        return JsonResponse({
            'success': True,
            'message': f'Tier changed to {case.get_tier_display()}.'
        })

    return JsonResponse({'success': False, 'error': 'Failed to change Tier. Please try again.'}, status=500)


@login_required
def submit_case_final(request, case_id):
    """Submit a draft case to transition it from draft to submitted status"""
    if request.method == 'POST':
        try:
            user = request.user
            case = get_object_or_404(Case, pk=case_id)
            
            # Permission check: Only the case creator (member) or delegate can submit
            is_delegate = False
            if case.member != user:
                from accounts.models import MemberDelegate
                is_delegate = MemberDelegate.objects.filter(delegate=user, member=case.member).exists()
                if not is_delegate:
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
            
            # Re-evaluate urgency and due-date validity at submit time.
            # Drafts can sit for a long time; a stale due date must be refreshed.
            from datetime import timedelta
            today = timezone.localtime(timezone.now()).date()
            try:
                threshold_days = int(SystemSettings.get_settings().rush_case_threshold_days or 7)
            except Exception:
                threshold_days = 7
            threshold_days = max(threshold_days, 1)
            rush_threshold_date = today + timedelta(days=threshold_days)

            requires_due_date_refresh = (not case.date_due) or (case.date_due < today)
            
            # Calculate what the urgency should be based on current date.
            # Missing due dates are handled by the refresh requirement above.
            current_urgency = 'rush' if case.date_due and case.date_due < rush_threshold_date else 'normal'
            stored_urgency = case.urgency
            
            # Check if urgency changed from normal to rush
            urgency_changed = (stored_urgency == 'normal' and current_urgency == 'rush')
            
            # If this is a check-only request (from frontend), return urgency status
            check_only = request.POST.get('check_only') == 'true'
            if check_only:
                has_documents = case.documents.count() > 0
                return JsonResponse({
                    'success': True,
                    'urgency_changed': urgency_changed,
                    'stored_urgency': stored_urgency,
                    'current_urgency': current_urgency,
                    'rush_threshold_days': threshold_days,
                    'requires_due_date_refresh': requires_due_date_refresh,
                    'no_documents': not has_documents,
                    'message': f'This case is now marked as RUSH. Your due date is within {threshold_days} days. Continue?'
                })
            
            # Server-side document check
            if case.documents.count() == 0:
                return JsonResponse({
                    'success': False,
                    'error': 'Please attach at least one document before submitting your case.'
                }, status=400)

            # Server-side enforcement: draft due date must be current/future.
            if requires_due_date_refresh:
                return JsonResponse({
                    'success': False,
                    'error': 'Please edit this draft and select a new due date before submitting.'
                }, status=400)
            
            # Update case urgency to current value
            if current_urgency != stored_urgency:
                case.urgency = current_urgency
            
            # Update case status to submitted
            case.status = 'submitted'
            case.date_submitted = timezone.now()
            case.save()
            
            # If member included notes for benefits team, add as first chat message
            if case.special_notes and case.special_notes.strip():
                from cases.models import CaseMessage
                CaseMessage.objects.create(
                    case=case,
                    author=user,
                    message=case.special_notes.strip()
                )
            
            # Log case submission to audit trail
            from core.models import AuditLog
            AuditLog.log_activity(
                user=request.user,
                action_type='case_submitted',
                case=case,
                description=f'Case submitted for {case.employee_first_name} {case.employee_last_name}',
                metadata={
                    'urgency': case.urgency,
                    'urgency_changed': current_urgency != stored_urgency,
                    'document_count': case.documents.count(),
                }
            )
            
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
    """
    API endpoint for a technician to take ownership of an accepted-but-unassigned case.
    
    IMPORTANT: This only works on cases that have already been through the acceptance process.
    If a case is still in 'submitted' status, it must go through Review & Accept first.
    This endpoint is for claiming an already-reviewed case without re-reviewing.
    """
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
            
            # Case must already be accepted (not submitted/resubmitted)
            # This ensures the case has been reviewed for tier, docs, etc.
            if case.status not in ['accepted', 'hold']:
                return JsonResponse({
                    'success': False,
                    'error': f'This case must be accepted first. Current status: {case.get_status_display()}. Please use "Review & Accept" to formally accept the case before claiming ownership.'
                }, status=400)
            
            # Case must not already be assigned to this technician
            if case.assigned_to == user:
                return JsonResponse({
                    'success': False,
                    'error': f'You already own this case'
                }, status=400)
            
            # Verify case has been formally accepted (has tier and accepted_by)
            if not case.tier or not case.accepted_by:
                return JsonResponse({
                    'success': False,
                    'error': 'This case has not been properly accepted yet. Please contact an administrator.'
                }, status=400)
            
            # Technician level check - can they handle this tier?
            try:
                tier_num = int(case.tier) if case.tier else 0
            except (ValueError, TypeError):
                tier_num = 0
            
            tech_level_map = {
                'level_1': 1,
                'level_2': 2,
                'level_3': 3
            }
            tech_level_num = tech_level_map.get(user.user_level, 0)
            
            if tech_level_num < tier_num:
                return JsonResponse({
                    'success': False,
                    'error': f'You are Level {tech_level_num} but this Tier {tier_num} case requires Level {tier_num}. Contact your administrator if you have concerns.'
                }, status=403)
            
            # Get the old assignee for audit logging
            old_assignee = case.assigned_to
            
            # Assign the case to the current technician
            case.assigned_to = user
            case.save()
            
            # Log the ownership change
            from core.models import AuditLog
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            ip_address = x_forwarded_for.split(',')[0] if x_forwarded_for else request.META.get('REMOTE_ADDR')
            
            old_assignee_name = old_assignee.get_full_name() if old_assignee else 'Unassigned'
            member_name = f"{case.employee_first_name} {case.employee_last_name}".strip()
            description = f"Claimed ownership of {case.external_case_id} — {member_name} (was: {old_assignee_name})"
            
            AuditLog.log_activity(
                user=user,
                action_type='case_ownership_taken',
                description=description,
                case=case,
                changes={
                    'assigned_to': (old_assignee.username if old_assignee else None, user.username)
                },
                ip_address=ip_address,
                metadata={
                    'previous_assignee': old_assignee_name,
                    'new_assignee': user.get_full_name() or user.username,
                    'case_tier': case.tier,
                    'accepted_by': case.accepted_by.get_full_name() if case.accepted_by else None
                }
            )
            
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
    
    # Additional check for members - can only add notes to their own cases (or delegated cases)
    if user.role == 'member' and case.member != user:
        from accounts.models import MemberDelegate
        if not MemberDelegate.objects.filter(delegate=user, member=case.member).exists():
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
@require_http_methods(["POST"])
def delete_case_report(request, case_id, report_id):
    """Delete a report from a case (technician/admin/manager only)."""
    from cases.models import CaseReport
    
    user = request.user
    case = get_object_or_404(Case, id=case_id)
    report = get_object_or_404(CaseReport, id=report_id, case=case)
    
    if user.role not in ['technician', 'administrator', 'manager']:
        messages.error(request, 'Permission denied.')
        return redirect('cases:case_detail', pk=case_id)
    
    report_num = report.report_number
    filename = report.report_file.name if report.report_file else 'No file'
    
    # Delete the physical file
    if report.report_file:
        report.report_file.delete(save=False)
    
    # Delete the report record
    report.delete()
    
    # Audit log
    from core.models import AuditLog
    AuditLog.log_activity(
        user=user,
        action_type='case_updated',
        case=case,
        description=f'Deleted Report #{report_num} ({filename})',
        metadata={'report_number': report_num, 'filename': filename, 'deleted_by': user.username}
    )
    
    messages.success(request, f'Report #{report_num} deleted.')
    return redirect('cases:case_detail', pk=case_id)


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
    
    # Check if technician owns the case (or is the reviewer)
    if user.role == 'technician' and case.assigned_to != user:
        is_reviewer_on_pending = case.status == 'pending_review' and user.user_level in ['level_2', 'level_3']
        is_reviewer_on_completion = case.reviewed_by == user and case.review_status in ['corrections_needed', 'approved'] and case.status in ['accepted', 'hold']
        if not (is_reviewer_on_pending or is_reviewer_on_completion):
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
            # Technician must own the case, unless they're a reviewer
            is_reviewer_on_pending = case.status == 'pending_review' and user.user_level in ['level_2', 'level_3']
            is_reviewer_on_completion = case.reviewed_by == user and case.review_status in ['corrections_needed', 'approved'] and case.status in ['accepted', 'hold']
            if not (is_reviewer_on_pending or is_reviewer_on_completion):
                messages.error(request, 'You can only upload documents to cases you are assigned to.')
                return redirect('cases:case_detail', pk=case_id)
        can_upload = True
    elif user.role == 'member' and case.status in ['draft', 'submitted', 'accepted', 'hold', 'pending_review', 'resubmitted', 'needs_resubmission']:
        # Members can upload to their own cases (or delegated cases) in active statuses
        if case.member == user:
            can_upload = True
        else:
            from accounts.models import MemberDelegate
            if MemberDelegate.objects.filter(delegate=user, member=case.member).exists():
                can_upload = True
    
    if not can_upload:
        messages.error(request, 'You do not have permission to upload documents to this case.')
        return redirect('cases:case_detail', pk=case_id)
    
    if request.method == 'POST':
        document_files = request.FILES.getlist('document_file')
        document_notes = request.POST.get('document_notes', '').strip()
        
        if not document_files:
            messages.error(request, 'Please select a file to upload.')
            return redirect('cases:case_detail', pk=case_id)
        
        from cases.models import CaseDocument
        
        # Append employee last name to filename
        import os
        fed_last_name = case.employee_last_name
        
        # For members uploading to draft cases, use 'fact_finder' type
        # For members uploading after submission, use 'supporting' type
        # For technicians, use 'report' unless uploading a resource
        if user.role == 'member':
            doc_type = 'fact_finder' if case.status == 'draft' else 'supporting'
        else:
            # Allow staff to specify 'other' for additional resources vs 'report' for reports
            requested_type = request.POST.get('document_type', 'report')
            doc_type = 'other' if requested_type == 'other' else 'report'
        
        uploaded_count = 0
        for document_file in document_files:
            filename_with_employee = f"{fed_last_name}_{document_file.name}"
            
            doc = CaseDocument.objects.create(
                case=case,
                document_type=doc_type,
                original_filename=filename_with_employee,
                file_size=document_file.size,
                uploaded_by=user,
                file=document_file,
                notes=document_notes,
            )
            uploaded_count += 1
            
            # Log to audit trail
            from core.models import AuditLog
            AuditLog.log_activity(
                user=user,
                action_type='document_uploaded',
                case=case,
                description=f'{"Member" if user.role == "member" else "Technician"} uploaded document: {filename_with_employee}',
                metadata={
                    'document_id': doc.id,
                    'original_filename': document_file.name,
                    'file_size': document_file.size,
                    'document_type': doc_type,
                    'notes': document_notes
                }
            )
        
        # If member uploads after submission, flag for technician
        if user.role == 'member' and case.status != 'draft':
            case.has_member_new_info = True
            case.has_member_updates = True
            case.member_last_update_date = timezone.now()
            case.save(update_fields=['has_member_new_info', 'has_member_updates', 'member_last_update_date'])
            
            # Create StaffNotification for the assigned technician — only when case is on hold
            if case.assigned_to and case.status == 'hold':
                try:
                    from core.models import StaffNotification
                    StaffNotification.objects.create(
                        user=case.assigned_to,
                        notification_type='member_document_uploaded',
                        title=f'New Document — {case.employee_first_name} {case.employee_last_name}',
                        message=f'Member {user.get_full_name() or user.username} uploaded {uploaded_count} document(s) for {case.employee_first_name} {case.employee_last_name}.',
                        case=case,
                        is_read=False
                    )
                except Exception as notif_err:
                    logger.warning(f'Failed to create staff notification for member doc upload on case {case_id}: {notif_err}')
            # Post a system chat message so the badge increments and the tech knows what triggered it
            if case.assigned_to:
                try:
                    _uploader = user.get_full_name() or user.username
                    _upload_msg = CaseMessage.objects.create(
                        case=case,
                        author=user,
                        message=f'📎 {_uploader} uploaded {uploaded_count} document(s).'
                    )
                    UnreadMessage.objects.get_or_create(
                        message=_upload_msg,
                        user=case.assigned_to,
                        defaults={'case': case}
                    )
                except Exception as e:
                    logger.warning(f'Failed to create upload alert message for case {case_id}: {e}')
        
        # Show updated document count
        from cases.services.document_count_service import get_document_count_message
        doc_count_msg = get_document_count_message(case, include_breakdown=True)
        messages.success(request, f'{uploaded_count} document(s) uploaded successfully. {doc_count_msg}')
    
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
    
    if not required_report_numbers.issubset(uploaded_report_numbers):
        missing_reports = required_report_numbers - uploaded_report_numbers
        missing_str = ', '.join(str(r) for r in sorted(missing_reports))
        # Allow override - return warning but allow technician to proceed
        return JsonResponse({
            'valid': False,
            'canOverride': True,
            'warning': f'This case was requested with {case.num_reports_requested} report(s), but only {len(uploaded_report_numbers)} have been uploaded.'
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
    
    # Check if technician owns the case (or is the reviewer completing via approve/corrections)
    if user.role == 'technician' and case.assigned_to != user:
        if not (case.reviewed_by == user and case.review_status in ['corrections_needed', 'approved']):
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
    
    if not required_report_numbers.issubset(uploaded_report_numbers) and not override_incomplete:
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
            
            # Determine if case requires review (based on TechReviewSetting per-tech per-tier)
            # Skip review routing if reviewer is completing with corrections (already reviewed)
            if case.requires_review and case.review_status not in ['corrections_needed', 'approved']:
                # This technician's work at this tier requires review
                case.status = 'pending_review'
                # Log the submission for review in audit trail
                CaseReviewHistory.objects.create(
                    case=case,
                    original_technician=case.assigned_to,
                    review_action='submitted_for_review',
                    review_notes=f'Case submitted by {case.assigned_to.get_full_name() or case.assigned_to.username} ({case.assigned_to.get_user_level_display()}) for quality review'
                )
            else:
                # This technician's work at this tier does not require review
                case.status = 'completed'
            
            # Handle release scheduling - new datetime format or legacy hours format
            release_option = body_data.get('release_option', 'now')
            release_datetime_str = body_data.get('release_datetime')  # NEW: format "YYYY-MM-DD HH:MM"
            completion_delay_hours = body_data.get('completion_delay_hours')  # OLD: backward compatibility
            
            # If scheduled releases are disabled globally, force immediate release
            global_settings = SystemSettings.get_settings()
            if not global_settings.enable_scheduled_releases:
                release_option = 'now'
                release_datetime_str = None
                completion_delay_hours = None
            
            # Only apply release scheduling if case is actually completed (not pending review)
            if case.status == 'completed':
                if release_option == 'now' or (not release_datetime_str and not completion_delay_hours):
                    # Immediate release and email
                    case.scheduled_release_date = None
                    case.actual_release_date = timezone.now()
                    case.scheduled_email_date = None
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
                            
                            # Store full datetime for scheduled release (supports same-day time-based scheduling)
                            case.scheduled_release_date = release_dt_utc
                            case.scheduled_email_date = release_dt_utc
                            case.actual_release_date = None
                            case.actual_email_sent_date = None
                            case.date_completed = timezone.now()  # Tech completed now, release scheduled for later
                            
                            # Format for user display
                            release_date_str = release_dt_cst.strftime('%b %d, %Y at %I:%M %p %Z')
                            release_msg = f"scheduled for release on {release_date_str}"
                        except (ValueError, AttributeError) as e:
                            # If parsing fails, fall back to immediate release
                            case.scheduled_release_date = None
                            case.actual_release_date = timezone.now()
                            case.scheduled_email_date = None
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
                            case.date_completed = timezone.now()
                            release_msg = "released immediately"
                        else:
                            # Calculate release time in CST with delay (legacy)
                            release_time_cst = calculate_release_time_cst(completion_delay_hours)
                            case.scheduled_release_date = convert_to_scheduled_date_cst(release_time_cst)
                            case.scheduled_email_date = convert_to_scheduled_date_cst(release_time_cst)
                            case.actual_release_date = None
                            case.actual_email_sent_date = None
                            case.date_completed = timezone.now()  # Tech completed now, release delayed
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
            
            # Handle credit adjustment from pre-completion review (atomic with completion)
            if body_data.get('completion_review') and body_data.get('credit_adjusted') and body_data.get('credit_value'):
                try:
                    from decimal import Decimal
                    from cases.services.credit_service import set_case_credit
                    new_credit = Decimal(body_data['credit_value'])
                    if Decimal('0.0') <= new_credit <= Decimal('3.0'):
                        set_case_credit(case, new_credit, request.user, 'completion',
                                        body_data.get('credit_reason', 'Adjusted during pre-completion review'))
                except Exception as credit_err:
                    logger.warning(f'Credit adjustment during completion failed for case {case_id}: {credit_err}')
            
            # Log case completion to audit trail
            from core.models import AuditLog
            completion_metadata = {
                'status': case.status,
                'release_msg': release_msg,
                'release_option': release_option,
                'scheduled_release_date': str(case.scheduled_release_date) if case.scheduled_release_date else None,
                'actual_release_date': str(case.actual_release_date) if case.actual_release_date else None,
                'external_case_id': case.external_case_id,
                'employee_name': f'{case.employee_first_name} {case.employee_last_name}',
            }
            
            # Include pre-completion review checklist data if submitted from the review page
            if body_data.get('completion_review'):
                completion_metadata['completion_review'] = True
                completion_metadata['completion_checklist'] = body_data.get('completion_checklist', {})
                completion_metadata['credit_adjusted_at_completion'] = body_data.get('credit_adjusted', False)
                completion_metadata['credit_value_at_completion'] = str(case.credit_value) if case.credit_value is not None else None
                completion_metadata['reports_requested'] = case.num_reports_requested
                completion_metadata['reports_uploaded'] = len(uploaded_report_numbers)
                completion_metadata['has_tech_notes'] = bool(case.report_notes_to_member and case.report_notes_to_member.strip())
            
            AuditLog.log_activity(
                user=request.user,
                action_type='case_completed',
                case=case,
                description=f'Case marked as {case.status} — {case.external_case_id} ({case.employee_first_name} {case.employee_last_name}) - {release_msg}',
                metadata=completion_metadata,
                ip_address=request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', '')).split(',')[0].strip(),
            )
            
            # Add case note for completion (audit trail in case notes timeline)
            from cases.models import CaseNote
            complete_note = f'[Case Completed] Marked as {case.status} by {request.user.get_full_name() or request.user.username}. {release_msg}'
            CaseNote.objects.create(case=case, author=request.user, note=complete_note, is_internal=True)
            
            # Create notification and send email to member (only if immediately released)
            if case.actual_release_date and case.status == 'completed':
                # Create in-app notification for member (respects portal preference)
                from cases.models import CaseNotification
                employee_name = f'{case.employee_first_name} {case.employee_last_name}'.strip()
                _create_case_notification_if_allowed(
                    case=case,
                    member=case.member,
                    notification_type='case_released',
                    title=f'Your case for {employee_name} is completed',
                    message=f'Your case for {employee_name} has been completed and is ready for you to review.'
                )
                
                # Send case completed email to member
                try:
                    from cases.services.email_service import send_case_completed_email
                    send_case_completed_email(case, request=request, user=request.user)
                except Exception as email_error:
                    logger.error(f'Failed to send case completed email for case {case_id}: {str(email_error)}')
            
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
def completion_review(request, case_id):
    """
    Pre-completion review page. Technician reviews credit value, report counts,
    technical notes, and completes a checklist before marking the case complete.
    Modeled after the Initial Case Review (case_review_for_acceptance).
    """
    case = get_object_or_404(Case, id=case_id)
    user = request.user

    # Permission check
    if user.role not in ['technician', 'administrator', 'manager']:
        messages.error(request, 'You do not have permission to complete cases.')
        return redirect('cases:case_detail', pk=case_id)

    # Technicians must own the case (or be the reviewer completing via approve/corrections)
    if user.role == 'technician' and case.assigned_to != user:
        if not (case.reviewed_by == user and case.review_status in ['corrections_needed', 'approved']):
            messages.error(request, 'You can only complete cases assigned to you.')
            return redirect('cases:case_detail', pk=case_id)

    # Case must be in a completable status
    if case.status not in ['accepted', 'hold']:
        messages.error(request, f'Case cannot be completed from status: {case.get_status_display()}')
        return redirect('cases:case_detail', pk=case_id)

    # Report counts
    from cases.models import CaseReport
    uploaded_reports = CaseReport.objects.filter(case=case).order_by('report_number')
    uploaded_count = uploaded_reports.count()
    requested_count = case.num_reports_requested
    reports_match = uploaded_count >= requested_count

    # Check if tech notes exist and have content
    has_tech_notes = bool(case.report_notes_to_member and case.report_notes_to_member.strip())

    # Documents
    documents = case.documents.all().order_by('document_type', '-uploaded_at')
    tech_documents = documents.filter(document_type='other')

    # Credit info
    from cases.services.credit_service import calculate_default_credit
    default_credit = calculate_default_credit(requested_count)

    context = {
        'case': case,
        'uploaded_reports': uploaded_reports,
        'uploaded_count': uploaded_count,
        'requested_count': requested_count,
        'reports_match': reports_match,
        'has_tech_notes': has_tech_notes,
        'documents': documents,
        'tech_documents': tech_documents,
        'default_credit': default_credit,
        'report_number_choices': range(1, max(requested_count, uploaded_count) + 2),
        'page_title': f'Pre-Completion Review - {case.external_case_id}',
    }

    return render(request, 'cases/case_completion_review.html', context)


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
            case.status = 'accepted'  # Return to accepted (tech is pulling back to work on it)
            case.date_completed = None  # Clear completion date
            case.save()
            
            # Log to audit trail
            from core.models import AuditLog
            AuditLog.log_activity(
                user=request.user,
                action_type='case_incomplete',
                case=case,
                description=f'Case marked as incomplete and reactivated',
                changes={'status': {'from': 'completed', 'to': 'accepted'}}
            )
            
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
def clear_profeds_error(request, case_id):
    """Clear the ProFeds error flag on a case with a mandatory justification (tech/manager/admin only)"""

    user = request.user
    case = get_object_or_404(Case, id=case_id)

    if user.role not in ['technician', 'administrator', 'manager']:
        return JsonResponse({'success': False, 'error': 'You do not have permission to perform this action.'}, status=403)

    if not case.has_profeds_error:
        return JsonResponse({'success': False, 'error': 'This case does not have an active error flag.'}, status=400)

    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)

    justification = request.POST.get('justification', '').strip()
    if not justification:
        messages.error(request, 'Justification is required to clear the error flag.')
        return redirect('cases:case_detail', pk=case_id)

    try:
        case.has_profeds_error = False
        case.save()

        # Also clear the flag on the paired case so the banner goes away on both sides
        if case.original_case and case.original_case.has_profeds_error:
            case.original_case.has_profeds_error = False
            case.original_case.save()
        # If this IS the original, clear any linked mod cases too
        case.resubmitted_cases.filter(has_profeds_error=True).update(has_profeds_error=False)

        from core.models import AuditLog
        AuditLog.log_activity(
            user=user,
            action_type='error_flag_disputed',
            case=case,
            description=f'ProFeds error flag cleared by {user.get_full_name() or user.username}. Justification: {justification}',
            metadata={
                'cleared_by': user.username,
                'justification': justification,
            }
        )

        messages.success(request, 'Error flag has been cleared. Justification recorded in the audit trail.')
    except Exception as e:
        messages.error(request, f'Failed to clear error flag: {str(e)}')

    return redirect('cases:case_detail', pk=case_id)


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
    from core.models import AuditLog, StaffNotification
    import os
    
    user = request.user
    case = get_object_or_404(Case, id=case_id)
    
    # Permission check - member who owns the case, or their delegate, can upload
    is_case_delegate = False
    if user.role != 'member':
        messages.error(request, 'You do not have permission to upload documents to this case.')
        return redirect('cases:case_detail', pk=case_id)
    if case.member != user:
        from accounts.models import MemberDelegate
        is_case_delegate = MemberDelegate.objects.filter(
            delegate=user, member=case.member
        ).exists()
        if not is_case_delegate:
            messages.error(request, 'You do not have permission to upload documents to this case.')
            return redirect('cases:case_detail', pk=case_id)
    
    # Check if case is in an appropriate status for member document upload
    # Allow uploads for: draft, submitted, accepted, pending_review, completed (resubmission), hold (member providing requested docs)
    allowed_statuses = ['draft', 'submitted', 'completed', 'pending_review', 'accepted', 'resubmitted', 'hold']
    if case.status not in allowed_statuses:
        messages.error(request, f'You cannot upload documents to cases in {case.get_status_display()} status.')
        return redirect('cases:case_detail', pk=case_id)
    
    if request.method == 'POST':
        document_files = request.FILES.getlist('document_file')
        document_notes = request.POST.get('document_notes', '').strip()
        
        if not document_files:
            messages.error(request, 'Please select a file to upload.')
            return redirect('cases:case_detail', pk=case_id)
        
        # Validate file sizes (max 50MB each)
        for document_file in document_files:
            if document_file.size > 50 * 1024 * 1024:
                messages.error(request, f'File "{document_file.name}" exceeds 50MB limit.')
                return redirect('cases:case_detail', pk=case_id)
        
        # Append employee last name to filename
        fed_last_name = case.employee_last_name
        
        uploaded_count = 0
        for document_file in document_files:
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
            uploaded_count += 1
            
            # Create audit log entry for each file
            upload_meta = {
                'filename': filename_with_employee,
                'file_size': document_file.size,
                'document_notes': document_notes,
                'case_status': case.status,
            }
            upload_desc = f'Member uploaded supplementary document: {filename_with_employee}'
            
            # Add delegate context if uploading on behalf of another member
            if is_case_delegate:
                upload_meta['uploaded_by_delegate'] = True
                upload_meta['delegate_id'] = user.id
                upload_meta['delegate_name'] = user.get_full_name()
                upload_meta['on_behalf_of'] = case.member.get_full_name()
                upload_desc = f'Delegate {user.get_full_name()} uploaded supplementary document: {filename_with_employee} on behalf of {case.member.get_full_name()}'
            
            AuditLog.objects.create(
                user=user,
                action_type='member_document_uploaded',
                description=upload_desc,
                case=case,
                metadata=upload_meta,
            )
        
        # Set member updates flag if case is after submission
        if case.status in ['submitted', 'accepted', 'pending_review', 'resubmitted', 'completed', 'hold']:
            case.has_member_updates = True
            case.has_member_new_info = True
            case.member_last_update_date = timezone.now()
            case.save(update_fields=['has_member_updates', 'has_member_new_info', 'member_last_update_date'])
            
            # Create StaffNotification for the assigned technician — only when case is on hold
            if case.assigned_to and case.status == 'hold':
                try:
                    StaffNotification.objects.create(
                        user=case.assigned_to,
                        notification_type='member_document_uploaded',
                        title=f'New Document — {case.employee_first_name} {case.employee_last_name}',
                        message=f'Member {user.get_full_name() or user.username} uploaded {uploaded_count} document(s) for {case.employee_first_name} {case.employee_last_name}',
                        case=case,
                        is_read=False
                    )
                except Exception as notif_err:
                    logger.warning(f'Failed to create staff notification for member doc upload on case {case_id}: {notif_err}')
            # Post a system chat message so the badge increments and the tech knows what triggered it
            if case.assigned_to:
                try:
                    _uploader = user.get_full_name() or user.username
                    _upload_msg = CaseMessage.objects.create(
                        case=case,
                        author=user,
                        message=f'📎 {_uploader} uploaded {uploaded_count} document(s).'
                    )
                    UnreadMessage.objects.get_or_create(
                        message=_upload_msg,
                        user=case.assigned_to,
                        defaults={'case': case}
                    )
                except Exception as e:
                    logger.warning(f'Failed to create upload alert message for case {case_id}: {e}')
        
        # Show updated document count
        from cases.services.document_count_service import get_document_count_message
        doc_count_msg = get_document_count_message(case, include_breakdown=True)
        messages.success(request, f'{uploaded_count} document(s) uploaded successfully. {doc_count_msg} You can upload more documents before resubmitting.')
    
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
    
    # Permission check - only the member who owns the case (or their delegate) can resubmit
    if user.role != 'member':
        messages.error(request, 'You do not have permission to resubmit this case.')
        return redirect('cases:case_detail', pk=case_id)
    if case.member != user:
        from accounts.models import MemberDelegate
        if not MemberDelegate.objects.filter(delegate=user, member=case.member).exists():
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
    
    # Check permissions - any technician, admin, or manager can adjust credit
    if user.role not in ['technician', 'administrator', 'manager']:
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
            if credit_value < Decimal('0.0') or credit_value > Decimal('3.0'):
                return JsonResponse({'success': False, 'error': 'Credit must be between 0.0 and 3.0'})
            
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
def adjust_reports_requested(request, case_id):
    """Adjust the number of reports requested for a case."""
    case = get_object_or_404(Case, pk=case_id)
    user = request.user
    
    if user.role not in ['technician', 'administrator', 'manager']:
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
    
    if request.method == 'POST':
        try:
            num_reports = int(request.POST.get('num_reports_requested', 0))
            reason = request.POST.get('reason', 'Manual adjustment')
            
            if num_reports < 1 or num_reports > 9:
                return JsonResponse({'success': False, 'error': 'Number of reports must be between 1 and 9'})
            
            old_value = case.num_reports_requested
            case.num_reports_requested = num_reports
            case.save(update_fields=['num_reports_requested'])
            
            from core.models import AuditLog
            AuditLog.log_activity(
                user=user,
                action_type='case_updated',
                case=case,
                description=f'Reports requested changed from {old_value} to {num_reports}. Reason: {reason}',
                changes={'num_reports_requested': {'from': old_value, 'to': num_reports}},
                metadata={'reason': reason, 'updated_by': user.username}
            )
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': f'Reports requested updated to {num_reports}',
                    'new_value': num_reports
                })
            else:
                return redirect('cases:case_detail', pk=case_id)
                
        except (ValueError, TypeError):
            return JsonResponse({'success': False, 'error': 'Invalid number'})
        except Exception as e:
            logger.error(f'Error adjusting reports requested for case {case_id}: {str(e)}', exc_info=True)
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'POST request required'}, status=400)


@login_required
def edit_employee_name(request, case_id):
    """Edit the federal employee's name on a case (inline pencil edit)."""
    case = get_object_or_404(Case, pk=case_id)
    user = request.user

    if user.role not in ['technician', 'administrator', 'manager']:
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)

    if request.method == 'POST':
        first_name = request.POST.get('employee_first_name', '').strip()
        last_name = request.POST.get('employee_last_name', '').strip()
        reason = request.POST.get('reason', 'Name correction')

        if not first_name or not last_name:
            return JsonResponse({'success': False, 'error': 'Both first name and last name are required.'})

        old_first = case.employee_first_name
        old_last = case.employee_last_name

        if old_first == first_name and old_last == last_name:
            return JsonResponse({'success': False, 'error': 'No changes detected.'})

        case.employee_first_name = first_name
        case.employee_last_name = last_name
        case.save(update_fields=['employee_first_name', 'employee_last_name'])

        from core.models import AuditLog
        changes = {}
        if old_first != first_name:
            changes['employee_first_name'] = {'from': old_first, 'to': first_name}
        if old_last != last_name:
            changes['employee_last_name'] = {'from': old_last, 'to': last_name}

        AuditLog.log_activity(
            user=user,
            action_type='case_updated',
            case=case,
            description=f'Employee name changed from "{old_first} {old_last}" to "{first_name} {last_name}". Reason: {reason}',
            changes=changes,
            metadata={'reason': reason, 'updated_by': user.username}
        )

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': f'Employee name updated to {first_name} {last_name}',
                'first_name': first_name,
                'last_name': last_name,
            })
        else:
            return redirect('cases:case_detail', pk=case_id)

    return JsonResponse({'success': False, 'error': 'POST request required'}, status=400)


@login_required
def credit_audit_trail(request, case_id=None):
    """View credit audit trail for cases - Manager/Admin only."""
    user = request.user
    
    # Check if user is admin or manager (check role field)
    if user.role not in ['administrator', 'manager']:
        messages.error(request, 'You do not have permission to view credit audit trails.')
        return redirect('home')
    
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
    
    # Get available technicians for assignment (technicians and administrators)
    available_techs = _exclude_super_dev_users(User.objects.filter(role__in=['technician', 'administrator'], is_active=True)).order_by('first_name')
    
    context = {
        'case': case,
        'available_techs': available_techs,
        'page_title': f'Review Case {case.external_case_id}',
    }
    
    return render(request, 'cases/case_review_and_accept.html', context)


@login_required



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
        
        # Log rejection to audit trail
        from core.models import AuditLog
        AuditLog.log_activity(
            user=user,
            action_type='case_rejected',
            case=case,
            description=f'Case rejected - needs resubmission. Reason: {rejection_reason}',
            metadata={
                'rejection_reason': rejection_reason,
                'rejection_notes': rejection_notes,
            }
        )
        
        # Send rejection email to member
        # DISABLED per email policy — members only receive HOLD, CHAT, READY emails
        from django.core.mail import send_mail
        from django.template.loader import render_to_string
        from django.conf import settings
        from cases.services.email_service import should_send_emails
        
        if False and should_send_emails():
            email_context = {
                'member': case.member,
                'case': case,
                'rejection_reason': case.get_rejection_reason_display(),
                'rejection_notes': rejection_notes,
                'case_url': f'{settings.SITE_URL}/cases/{case.id}/' if hasattr(settings, 'SITE_URL') else 'https://yoursite.com/cases/',
            }
            
            subject = f'Case for {case.employee_first_name} {case.employee_last_name} - Additional Information Needed'
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
        else:
            logger.info(f'Case {case.external_case_id} rejected by {user.username}. '
                       f'Reason: {rejection_reason}. Email skipped (notifications disabled)')
        
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
    if case.status not in ['accepted', 'pending_review', 'completed', 'hold']:
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
    
    # Permission check: Only member, delegate, or staff can message
    is_member = (user.role == 'member' and case.member == user)
    is_technician = (user.role in ['technician', 'administrator', 'manager'])
    is_delegate = False
    if not is_member and user.role == 'member':
        from accounts.models import MemberDelegate
        is_delegate = MemberDelegate.objects.filter(delegate=user, member=case.member).exists()
    
    logger.info(f'Permission check: is_member={is_member}, is_technician={is_technician}, is_delegate={is_delegate}')
    
    if not (is_member or is_technician or is_delegate):
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    try:
        message_text = request.POST.get('message', '').strip()
        image_file = request.FILES.get('image')
        
        if not message_text and not image_file:
            return JsonResponse({'error': 'Message or image is required'}, status=400)
        
        # Validate image if provided
        if image_file:
            from cases.models import ALLOWED_CHAT_IMAGE_TYPES, MAX_CHAT_IMAGE_SIZE
            if image_file.content_type not in ALLOWED_CHAT_IMAGE_TYPES:
                return JsonResponse({'error': 'Only PNG, JPEG, GIF, and WebP images are allowed.'}, status=400)
            if image_file.size > MAX_CHAT_IMAGE_SIZE:
                return JsonResponse({'error': 'Image must be under 5 MB.'}, status=400)
        
        # Create message
        msg = CaseMessage.objects.create(
            case=case,
            author=user,
            message=message_text,
            image=image_file
        )
        
        # Import CaseNotification for notification creation
        from cases.models import CaseNotification
        
        # Create UnreadMessage records for recipient(s)
        # Delegates act on behalf of the member, so treat them like the member
        if is_member or is_delegate:
            # Member (or delegate) posted - mark as unread for the assigned technician
            if case.assigned_to:
                try:
                    um, created = UnreadMessage.objects.get_or_create(
                        message=msg,
                        user=case.assigned_to,
                        defaults={'case': case}
                    )
                    logger.info(f'{"Delegate" if is_delegate else "Member"} {user.username} message on case {case.external_case_id} - Created UnreadMessage for technician {case.assigned_to.username}: {created}')
                except Exception as e:
                    logger.error(f'Error creating UnreadMessage for technician: {str(e)}')

                # Create StaffNotification for case chat message
                try:
                    from core.models import StaffNotification
                    preview = message_text[:150] + ('...' if len(message_text) > 150 else '')
                    StaffNotification.objects.create(
                        user=case.assigned_to,
                        case=case,
                        notification_type='case_chat_message',
                        title=f'New message — {case.employee_first_name} {case.employee_last_name}',
                        message=f'{user.get_full_name() or user.username}: {preview}',
                        is_read=False
                    )
                except Exception as e:
                    logger.error(f'Error creating StaffNotification for chat message: {str(e)}')
            else:
                # Case is unassigned — create UnreadMessage for all techs and admins
                # so the chat shows as a red unread bubble for whoever picks it up
                from accounts.models import User as UserModel
                staff_users = UserModel.objects.filter(role__in=['technician', 'administrator'], is_active=True)
                for staff_user in staff_users:
                    try:
                        UnreadMessage.objects.get_or_create(
                            message=msg,
                            user=staff_user,
                            defaults={'case': case}
                        )
                    except Exception as e:
                        logger.error(f'Error creating UnreadMessage for staff {staff_user.username}: {str(e)}')
                logger.info(f'Member {user.username} message on unassigned case {case.external_case_id} - Created UnreadMessage for {staff_users.count()} staff users')
            
            # NOTE: Do NOT set has_member_updates here — that flag is only for
            # document uploads / resubmissions. Chat messages use UnreadMessage
            # which drives the red unread bubble on the View button.
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
                    
                    # Get employee name for notification title
                    employee_name = f"{case.employee_first_name} {case.employee_last_name}".strip()
                    
                    logger.info(f'Creating CaseNotification: title="New Chat for {employee_name} case", message="{preview}"')
                    
                    # Respects member's portal preference for case_chat
                    notification = _create_case_notification_if_allowed(
                        case=case,
                        member=case.member,
                        notification_type='member_update_received',
                        title=f'New Chat for {employee_name} case',
                        message=preview
                    )
                    if notification:
                        logger.info(f'CaseNotification created successfully: {notification.id}')
                    else:
                        logger.info(f'CaseNotification suppressed by member preference (case_chat)')
                except Exception as e:
                    logger.error(f'Error creating CaseNotification for member: {str(e)}')
                    import traceback
                    logger.error(traceback.format_exc())
                
                # ============================================================
                # SEND EMAIL TO MEMBER — Tech Comment Notification
                # ============================================================
                try:
                    from cases.services.email_service import should_send_emails
                    from core.models import AuditLog
                    
                    if not should_send_emails():
                        logger.info(f'Email notifications disabled. Skipped tech comment email for case {case.external_case_id}')
                    elif case.member and case.member.email:
                        from django.core.mail import send_mail
                        from django.template.loader import render_to_string
                        from django.conf import settings as django_settings
                        from django.contrib.sites.shortcuts import get_current_site
                        
                        protocol = 'https' if request.is_secure() else 'http'
                        domain = get_current_site(request).domain
                        base_url = f"{protocol}://{domain}"
                        case_detail_url = f"{base_url}{reverse('cases:case_detail', args=[case.id])}"
                        logo_url = f"{base_url}/static/images/RevisedCoverPageLogo.png"
                        
                        employee_name = f"{case.employee_first_name} {case.employee_last_name}"
                        email_subject = f'UPDATE: The case for {employee_name} has a new note!'
                        
                        email_context = {
                            'member_first_name': case.member.first_name or case.member.username,
                            'employee_name': employee_name,
                            'case_detail_url': case_detail_url,
                            'logo_url': logo_url,
                        }
                        
                        text_message = render_to_string('emails/tech_comment_notification.txt', email_context)
                        html_message = render_to_string('emails/tech_comment_notification.html', email_context)
                        
                        # Get all recipients (member + delegates) — respects case_chat preference
                        from cases.services.email_service import get_case_recipient_emails
                        chat_recipients = get_case_recipient_emails(case, notification_type='case_chat')
                        
                        send_mail(
                            subject=email_subject,
                            message=text_message,
                            from_email=django_settings.DEFAULT_FROM_EMAIL,
                            recipient_list=chat_recipients,
                            html_message=html_message,
                            fail_silently=False
                        )
                        
                        AuditLog.objects.create(
                            case=case,
                            user=user,
                            action_type='email_notification_sent',
                            description=f'Tech comment email sent to {chat_recipients} for case {case.external_case_id}',
                            metadata={
                                'email_to': str(chat_recipients),
                                'email_subject': email_subject,
                            }
                        )
                        logger.info(f'Tech comment email sent to {case.member.email} for case {case.external_case_id}')
                    
                except Exception as email_error:
                    logger.error(f'Failed to send tech comment email for case {case.external_case_id}: {str(email_error)}')
                    AuditLog.objects.create(
                        case=case,
                        user=user,
                        action_type='other',
                        description=f'Failed to send tech comment email to {case.member.email}',
                        metadata={
                            'email_to': case.member.email if case.member else 'unknown',
                            'error': str(email_error),
                            'sub_action': 'email_failed'
                        }
                    )
        
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
    
    # Permission check: Only member, delegate, or staff can view messages
    is_member = (user.role == 'member' and case.member == user)
    is_technician = (user.role in ['technician', 'administrator', 'manager'])
    is_delegate = False
    if not is_member and user.role == 'member':
        from accounts.models import MemberDelegate
        is_delegate = MemberDelegate.objects.filter(delegate=user, member=case.member).exists()
    
    if not (is_member or is_technician or is_delegate):
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    try:
        # Get all messages for this case
        messages_qs = CaseMessage.objects.filter(case=case).select_related('author')
        
        # Paginate
        page = request.GET.get('page', 1)
        paginator = Paginator(messages_qs, 20)
        page_obj = paginator.get_page(page)
        
        messages_data = []
        import pytz
        cst_tz = pytz.timezone('America/Chicago')
        for msg in page_obj:
            # Convert timestamps to CST (Central Time Zone)
            created_at_cst = msg.created_at.astimezone(cst_tz) if msg.created_at.tzinfo else pytz.UTC.localize(msg.created_at).astimezone(cst_tz)
            updated_at_cst = msg.updated_at.astimezone(cst_tz) if msg.updated_at.tzinfo else pytz.UTC.localize(msg.updated_at).astimezone(cst_tz)

            # Show the actual sender's name; the role badge in the template
            # already indicates member vs staff context.
            author_display = msg.author.get_full_name() or msg.author.username
            
            messages_data.append({
                'id': msg.id,
                'author': author_display,
                'author_id': msg.author.id,
                'author_role': msg.author.role,
                'message': msg.message,
                'image_url': msg.image.url if msg.image else None,
                'created_at': created_at_cst.strftime('%b %d, %Y %I:%M %p %Z'),
                'updated_at': updated_at_cst.strftime('%b %d, %Y %I:%M %p %Z'),
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
    
    # Permission check: Only member, delegate, or staff can mark as read
    is_member = (user.role == 'member' and case.member == user)
    is_technician = (user.role in ['technician', 'administrator', 'manager'])
    is_delegate = False
    if not is_member and user.role == 'member':
        from accounts.models import MemberDelegate
        is_delegate = MemberDelegate.objects.filter(delegate=user, member=case.member).exists()
    
    if not (is_member or is_technician or is_delegate):
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    try:
        if user.role in ['technician', 'administrator', 'manager']:
            if case.assigned_to == user:
                # Case owner: globally clear all staff UnreadMessage rows for this case.
                # Badge is scoped to the assigned tech, so this drops the badge to 0
                # for every staff viewer simultaneously.
                UnreadMessage.objects.filter(
                    case=case,
                    user__role__in=['technician', 'administrator', 'manager'],
                ).delete()
                logger.info(f'Case owner {user.username} globally cleared staff UnreadMessage rows for case {case.external_case_id}')
            # else: non-owning staff — badge is the assigned tech's count; nothing to clear.
        else:
            # Member/delegate: clear own rows only (member badge is personal, not case-scoped)
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
    _inactive_statuses = ['completed', 'cancelled', 'declined', 'draft']
    
    try:
        from cases.models import CaseNotification
        
        # Get count of unread chat messages per case.
        # Staff roles (tech/admin/manager) use case-wide counts so all staff see
        # the same red badge regardless of who the individual UnreadMessage rows
        # were created for.  Members keep personal (per-user) counts.
        if user.role in ['technician', 'administrator', 'manager']:
            from django.db.models import F as _F
            unread_by_case = UnreadMessage.objects.filter(
                user=_F('case__assigned_to'),
            ).values('case').annotate(
                count=models.Count('id')
            ).order_by('-count')
        else:
            unread_by_case = UnreadMessage.objects.filter(
                user=user
            ).values('case').annotate(
                count=models.Count('id')
            ).order_by('-count')

        # Build lookup of chat unreads per case
        chat_unread_lookup = {item['case']: item['count'] for item in unread_by_case}
        
        # For members: also count unread lifecycle CaseNotifications (hold, resume, release)
        # Exclude 'member_update_received' to avoid double-counting with UnreadMessage
        notif_unread_lookup = {}
        if user.role == 'member':
            from accounts.models import MemberDelegate
            # Get member IDs this user acts as (own ID + delegated members)
            member_ids = [user.id]
            delegate_member_ids = list(
                MemberDelegate.objects.filter(delegate=user).values_list('member_id', flat=True)
            )
            member_ids.extend(delegate_member_ids)
            
            notif_unreads = CaseNotification.objects.filter(
                member_id__in=member_ids,
                is_read=False
            ).exclude(
                notification_type='member_update_received'
            ).values('case').annotate(
                count=models.Count('id')
            )
            notif_unread_lookup = {item['case']: item['count'] for item in notif_unreads}
        
        # Merge all case IDs that have any unreads
        all_case_ids = set(chat_unread_lookup.keys()) | set(notif_unread_lookup.keys())
        total_unread = sum(chat_unread_lookup.values()) + sum(notif_unread_lookup.values())
        
        # Build response with case details
        unread_cases = []
        for case_id in all_case_ids:
            try:
                case = Case.objects.get(pk=case_id)
                combined_count = chat_unread_lookup.get(case_id, 0) + notif_unread_lookup.get(case_id, 0)
                unread_cases.append({
                    'case_id': case.id,
                    'external_case_id': case.external_case_id,
                    'member_name': case.member.get_full_name() if case.member else 'Unknown',
                    'employee_name': f"{case.employee_first_name} {case.employee_last_name}",
                    'unread_count': combined_count,
                    'has_member_updates': case.has_member_updates,
                })
            except Case.DoesNotExist:
                pass
        
        # Also include cases with has_member_updates=True but no unread messages
        updated_cases = Case.objects.filter(
            has_member_updates=True
        ).exclude(id__in=all_case_ids)
        if user.role in ['technician', 'administrator', 'manager']:
            updated_cases = updated_cases.exclude(status__in=_inactive_statuses)
        for case in updated_cases:
            unread_cases.append({
                'case_id': case.id,
                'external_case_id': case.external_case_id,
                'member_name': case.member.get_full_name() if case.member else 'Unknown',
                'employee_name': f"{case.employee_first_name} {case.employee_last_name}",
                'unread_count': 0,
                'has_member_updates': True,
            })
        
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
    
    # Permission check: Only member (or delegate) can request modification
    if user.role != 'member':
        return JsonResponse({'error': 'Access denied'}, status=403)
    if case.member != user:
        from accounts.models import MemberDelegate
        if not MemberDelegate.objects.filter(delegate=user, member=case.member).exists():
            return JsonResponse({'error': 'Access denied'}, status=403)
    
    # Case must be completed
    if case.status != 'completed' or not case.actual_release_date:
        return JsonResponse({'error': 'Can only request modification for completed cases'}, status=400)
    
    # Prevent duplicate rapid-fire submissions (within 60 seconds)
    from datetime import timedelta
    from django.utils import timezone as tz
    recent_mod = Case.objects.filter(
        original_case=case,
        date_submitted__gte=tz.now() - timedelta(seconds=60)
    ).exists()
    if recent_mod:
        return JsonResponse({'error': 'A modification request was already submitted for this case. Please wait.'}, status=400)
    
    # Check 60-day limit
    release_date = case.actual_release_date
    if isinstance(release_date, str):
        from django.utils.dateparse import parse_datetime
        release_date = parse_datetime(release_date)
    
    days_since_release = (tz.now().date() - release_date.date()).days
    if days_since_release > 60:
        return JsonResponse({'error': 'Modification requests are only available within 60 days of case completion'}, status=400)
    
    try:
        reason = request.POST.get('reason', '').strip()
        is_profeds_error = request.POST.get('is_profeds_error', 'false').lower() == 'true'
        
        if not reason:
            return JsonResponse({'error': 'Reason is required'}, status=400)
        
        # Create new case as a copy of the original
        from cases.services.case_id_generator import generate_case_id
        from datetime import date
        
        # ProFeds error → 3-day turnaround (not rush — ProFeds absorbs the cost, no Rush badge shown)
        if is_profeds_error:
            mod_due_date = date.today() + timedelta(days=3)
            mod_urgency = 'normal'
        else:
            mod_due_date = date.today() + timedelta(days=7)
            mod_urgency = 'normal'
        
        new_case = Case.objects.create(
            external_case_id=generate_case_id(case.workshop_code),
            workshop_code=case.workshop_code,
            member=case.member,
            created_by=user,
            employee_first_name=case.employee_first_name,
            employee_last_name=case.employee_last_name,
            client_email=case.client_email,
            num_reports_requested=case.num_reports_requested,
            urgency=mod_urgency,
            date_due=mod_due_date,
            status='submitted',  # Start as new submission
            original_case=case,  # Link to original case
            tier=case.tier,
            date_submitted=tz.now(),
            assigned_to=case.assigned_to,  # Auto-assign to original technician
            has_profeds_error=is_profeds_error,  # Carry the error flag onto the mod case
            resubmission_notes=reason,  # Store modification reason so Tech can see it without visiting original case
        )
        
        logger.info(f'New modification case {new_case.external_case_id} created for case {case.external_case_id} by member {user.username} (assigned to: {case.assigned_to})')
        
        # Log modification case creation to audit trail
        from core.models import AuditLog
        AuditLog.log_activity(
            user=user,
            action_type='case_submitted',
            case=new_case,
            description=f'Modification case submitted for {case.employee_first_name} {case.employee_last_name} (original case: {case.external_case_id})',
            metadata={
                'is_modification': True,
                'original_case_id': case.id,
                'original_case_number': case.external_case_id,
                'urgency': mod_urgency,
                'is_profeds_error': is_profeds_error,
                'submitted_by': user.get_full_name(),
                'assigned_to': case.assigned_to.username if case.assigned_to else None,
            }
        )
        
        # If member flagged as ProFeds error, also mark original case and log to audit trail
        if is_profeds_error:
            case.has_profeds_error = True
            case.error_modification_count += 1
            case.save()
            
            # Log to audit trail
            from core.models import AuditLog
            AuditLog.objects.create(
                user=user,
                case=case,
                action_type='case_updated',
                description=f'Member flagged modification request as ProFeds error. Modification case: {new_case.external_case_id}. Original technician: {case.assigned_to.username if case.assigned_to else "Unassigned"}'
            )
            logger.warning(f'ProFeds error flagged on case {case.external_case_id} (assigned to: {case.assigned_to}). Modification: {new_case.external_case_id}')
        
        # Store the modification request in the original case's messages
        error_flag_text = "\n\n⚠️ **MEMBER FLAGGED AS PROFEDS ERROR**" if is_profeds_error else ""
        modification_message = f"**MODIFICATION REQUESTED BY MEMBER**\n\nReason: {reason}\n\nNew case created: {new_case.external_case_id}{error_flag_text}"
        msg = CaseMessage.objects.create(
            case=case,
            author=user,
            message=modification_message
        )
        
        # Also post the modification reason to the NEW case's chat so the Tech sees it immediately
        CaseMessage.objects.create(
            case=new_case,
            author=user,
            message=f"**MODIFICATION REQUEST REASON**\n\n{reason}{error_flag_text}"
        )
        
        return JsonResponse({
            'success': True,
            'new_case_id': new_case.external_case_id,
            'new_case_pk': new_case.pk,
            'employee_name': f'{new_case.employee_first_name} {new_case.employee_last_name}'.strip(),
            'message': f'New case created for {new_case.employee_first_name} {new_case.employee_last_name} and linked to original case'
        })
        
    except Exception as e:
        logger.error(f'Error creating modification request: {str(e)}')
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def create_modification_staff(request, pk):
    """
    Staff creates a modification case on behalf of the advisor for a completed case.
    Requires a justification and optionally flags the modification as a ProFeds error.
    """
    case = get_object_or_404(Case, pk=pk)
    user = request.user

    # Permission check: staff only
    if user.role not in ['technician', 'manager', 'administrator']:
        return JsonResponse({'error': 'Access denied'}, status=403)

    # Case must be completed and released
    if case.status != 'completed' or not case.actual_release_date:
        return JsonResponse({'error': 'Can only create modification for completed cases'}, status=400)

    # Avoid duplicate rapid-fire submissions
    from datetime import timedelta, date
    from django.utils import timezone as tz
    recent_mod = Case.objects.filter(
        original_case=case,
        date_submitted__gte=tz.now() - timedelta(seconds=60)
    ).exists()
    if recent_mod:
        return JsonResponse({'error': 'A modification was already created for this case. Please wait.'}, status=400)

    try:
        justification = request.POST.get('justification', '').strip()
        is_profeds_error = request.POST.get('is_profeds_error', 'false').lower() == 'true'

        if not justification:
            return JsonResponse({'error': 'Justification is required'}, status=400)

        from cases.services.case_id_generator import generate_case_id
        from core.models import AuditLog, StaffNotification
        from accounts.models import User as AccountUser

        # ProFeds error -> 3-day turnaround; otherwise 7-day
        if is_profeds_error:
            mod_due_date = date.today() + timedelta(days=3)
            mod_urgency = 'normal'
        else:
            mod_due_date = date.today() + timedelta(days=7)
            mod_urgency = 'normal'

        new_case = Case.objects.create(
            external_case_id=generate_case_id(case.workshop_code),
            workshop_code=case.workshop_code,
            member=case.member,
            created_by=user,
            employee_first_name=case.employee_first_name,
            employee_last_name=case.employee_last_name,
            client_email=case.client_email,
            num_reports_requested=case.num_reports_requested,
            urgency=mod_urgency,
            date_due=mod_due_date,
            status='submitted',
            original_case=case,
            tier=case.tier,
            date_submitted=tz.now(),
            assigned_to=case.assigned_to,
            has_profeds_error=is_profeds_error,
            resubmission_notes=justification,
        )

        AuditLog.log_activity(
            user=user,
            action_type='case_submitted',
            case=new_case,
            description=(
                f'Staff-created modification case submitted for '
                f'{case.employee_first_name} {case.employee_last_name} '
                f'(original case: {case.external_case_id})'
            ),
            metadata={
                'is_modification': True,
                'created_by_staff': True,
                'staff_username': user.username,
                'original_case_id': case.id,
                'original_case_number': case.external_case_id,
                'urgency': mod_urgency,
                'is_profeds_error': is_profeds_error,
                'justification': justification,
                'assigned_to': case.assigned_to.username if case.assigned_to else None,
            }
        )

        if is_profeds_error:
            case.has_profeds_error = True
            case.error_modification_count += 1
            case.save(update_fields=['has_profeds_error', 'error_modification_count'])
            AuditLog.objects.create(
                user=user,
                case=case,
                action_type='case_updated',
                description=(
                    f'Staff flagged modification as ProFeds error. '
                    f'Modification case: {new_case.external_case_id}. '
                    f'Created by: {user.get_full_name() or user.username}.'
                ),
                metadata={
                    'created_by_staff': True,
                    'staff_username': user.username,
                    'justification': justification,
                    'is_profeds_error': True,
                    'modification_case_id': new_case.id,
                    'modification_case_number': new_case.external_case_id,
                }
            )

        # Messages on original and new case
        error_flag_text = "\n\n⚠️ **FLAGGED AS PROFEDS ERROR**" if is_profeds_error else ""
        original_msg = CaseMessage.objects.create(
            case=case,
            author=user,
            message=(
                f"**MODIFICATION CREATED BY PRO FEDS STAFF**\n\n"
                f"Justification: {justification}\n\n"
                f"New case created: {new_case.external_case_id}{error_flag_text}"
            )
        )
        CaseMessage.objects.create(
            case=new_case,
            author=user,
            message=(
                f"**MODIFICATION REQUEST JUSTIFICATION (STAFF-CREATED)**\n\n"
                f"{justification}{error_flag_text}"
            )
        )

        return JsonResponse({
            'success': True,
            'new_case_id': new_case.external_case_id,
            'new_case_pk': new_case.pk,
            'employee_name': f'{new_case.employee_first_name} {new_case.employee_last_name}'.strip(),
            'message': f'New case created for {new_case.employee_first_name} {new_case.employee_last_name} and linked to original case'
        })

    except Exception as e:
        logger.error(f'Error creating staff modification: {str(e)}', exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def upload_image_for_notes(request):

    """
    Upload image for TinyMCE editor (notes).
    Images are automatically compressed to reduce file size.
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
        
        # Validate file size (10MB max - will be compressed to ~2MB or less)
        if uploaded_file.size > 10 * 1024 * 1024:
            return JsonResponse({'error': 'File too large. Max 10MB.'}, status=400)
        
        # Compress image
        from PIL import Image
        from io import BytesIO
        from django.core.files.base import ContentFile
        
        try:
            # Open image
            img = Image.open(uploaded_file)
            
            # Apply EXIF orientation (fixes rotated phone photos)
            from PIL import ImageOps
            img = ImageOps.exif_transpose(img)
            
            # Always convert to RGB for JPEG output (best compression for notes)
            if img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'RGBA':
                    background.paste(img, mask=img.split()[3])
                elif img.mode == 'P' and 'transparency' in img.info:
                    img = img.convert('RGBA')
                    background.paste(img, mask=img.split()[3])
                else:
                    background.paste(img)
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Resize if larger than max dimensions (1200x900 for notes - no need for huge images)
            max_width, max_height = 1200, 900
            if img.width > max_width or img.height > max_height:
                img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
            
            # Save as JPEG with good compression (best size reduction for notes/screenshots)
            compressed_io = BytesIO()
            img.save(compressed_io, format='JPEG', quality=70, optimize=True)
            compressed_io.seek(0)
            
            # Create new file with compressed data
            import uuid
            import os
            base_name = os.path.splitext(uploaded_file.name)[0]
            filename = f'notes_{uuid.uuid4().hex}_{base_name}.jpg'
            compressed_file = ContentFile(compressed_io.getvalue(), name=filename)
            
            # Save file to media/notes_images/
            from django.core.files.storage import default_storage
            file_path = f'notes_images/{filename}'
            
            # Save to storage
            path = default_storage.save(file_path, compressed_file)
            url = default_storage.url(path)
            
            # Log compression details
            original_size_mb = uploaded_file.size / (1024 * 1024)
            compressed_size = len(compressed_io.getvalue()) / (1024 * 1024)
            compression_ratio = (1 - (len(compressed_io.getvalue()) / uploaded_file.size)) * 100
            
            logger.info(f'Image uploaded & compressed by {user.username}: {filename} - Original: {original_size_mb:.2f}MB → Compressed: {compressed_size:.2f}MB ({compression_ratio:.1f}% reduction)')
            
            return JsonResponse({
                'location': url,
                'success': True
            })
        
        except Exception as compress_error:
            logger.error(f'Error compressing image: {str(compress_error)}')
            return JsonResponse({'error': f'Failed to process image: {str(compress_error)}'}, status=400)
        
    except Exception as e:
        logger.error(f'Error uploading image for notes: {str(e)}')
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def generate_report_notes_pdf(request, pk):
    """
    Generate and download report notes as PDF.
    Converts HTML notes to formatted PDF with case details and embedded images.
    """
    from django.http import HttpResponse
    from weasyprint import HTML
    from io import BytesIO
    import base64
    import re
    import os
    
    case = get_object_or_404(Case, pk=pk)
    user = request.user
    
    # Permission check: User must be tech/admin/manager/or member/delegate (if released)
    can_access = False
    
    if user.role in ['technician', 'administrator', 'manager']:
        can_access = True
    elif user.role == 'member':
        # Check if user is the case owner or a delegate for the case owner
        is_owner = (case.member == user)
        is_delegate = False
        if not is_owner:
            from accounts.models import MemberDelegate
            is_delegate = MemberDelegate.objects.filter(delegate=user, member=case.member).exists()
        
        if is_owner or is_delegate:
            # Member/delegate can only access if case is completed and released
            if case.status == 'completed':
                if case.actual_release_date is not None:
                    can_access = True
                elif case.scheduled_release_date and case.scheduled_release_date <= timezone.now():
                    can_access = True
    
    if not can_access:
        return HttpResponseForbidden('Access denied')
    
    # Check if notes exist
    if not case.report_notes_to_member or case.report_notes_to_member.strip() == '':
        messages.error(request, 'No notes available for this case')
        return redirect('cases:case_detail', pk=pk)
    
    try:
        # Convert image URLs in notes to base64 data URIs so they embed in the PDF
        notes_html = case.report_notes_to_member
        
        from django.conf import settings as django_settings
        
        def resolve_image_to_base64(match):
            """Convert an img src URL to a base64 data URI for PDF embedding."""
            full_tag = match.group(0)
            src = match.group(1)
            
            try:
                file_path = None
                
                # Handle relative URLs like /media/notes_images/...
                if src.startswith('/media/'):
                    file_path = os.path.join(str(django_settings.BASE_DIR), src.lstrip('/'))
                elif src.startswith('media/'):
                    file_path = os.path.join(str(django_settings.BASE_DIR), src)
                elif 'notes_images/' in src:
                    # Try to extract the path from full URL
                    parts = src.split('notes_images/')
                    if len(parts) > 1:
                        file_path = os.path.join(str(django_settings.BASE_DIR), 'media', 'notes_images', parts[1])
                
                if file_path and os.path.exists(file_path):
                    with open(file_path, 'rb') as f:
                        img_data = f.read()
                    b64 = base64.b64encode(img_data).decode('utf-8')
                    # Detect mime type
                    ext = os.path.splitext(file_path)[1].lower()
                    mime = {'jpg': 'image/jpeg', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png', '.gif': 'image/gif', '.webp': 'image/webp'}.get(ext, 'image/jpeg')
                    return full_tag.replace(src, f'data:{mime};base64,{b64}')
                
                return full_tag
            except Exception as e:
                logger.warning(f'Could not embed image {src}: {e}')
                return full_tag
        
        # Replace all img src attributes with base64 data URIs
        notes_html = re.sub(r'<img[^>]+src=["\']([^"\']+)["\']', resolve_image_to_base64, notes_html)
        
        # Build employee name
        employee_name = f'{case.employee_first_name} {case.employee_last_name}'.strip()
        
        # Get member name with workshop code
        member_display = 'N/A'
        if case.member:
            member_name = case.member.get_full_name() or case.member.username
            member_display = f'{member_name} ({case.workshop_code})' if case.workshop_code else member_name
        
        # Completion date
        completion_date = case.date_completed.strftime('%B %d, %Y') if case.date_completed else 'N/A'
        
        # Embed the cover page logo as base64
        logo_b64 = ''
        logo_path = os.path.join(str(django_settings.BASE_DIR), 'static', 'images', 'RevisedCoverPageLogo.png')
        try:
            if os.path.exists(logo_path):
                with open(logo_path, 'rb') as f:
                    logo_b64 = base64.b64encode(f.read()).decode('utf-8')
        except Exception as e:
            logger.warning(f'Could not load PDF logo: {e}')
        
        logo_img = f'<img src="data:image/png;base64,{logo_b64}" alt="FedImpact Logo" class="header-logo">' if logo_b64 else ''
        
        # Prepare HTML content with professional styling
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                @page {{
                    size: letter;
                    margin: 0.4in 0.75in 1in 0.75in;
                    @bottom-center {{
                        content: "Page " counter(page) " of " counter(pages);
                        font-size: 9pt;
                        color: #999;
                    }}
                }}
                * {{ margin: 0; padding: 0; box-sizing: border-box; }}
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    font-size: 11pt;
                    line-height: 1.5;
                    color: #333;
                    background-color: white;
                }}
                
                /* Header */
                .header {{
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    padding: 0 0 10px 0;
                    margin-bottom: 0;
                }}
                .header-text {{
                    flex: 1;
                }}
                .header-text h1 {{
                    font-size: 18pt;
                    font-weight: bold;
                    color: #333;
                    line-height: 1.2;
                    margin: 0;
                }}
                .header-logo {{
                    height: 70px;
                    width: auto;
                    margin-left: 20px;
                }}
                
                /* Case Info Bar */
                .case-info-bar {{
                    display: flex;
                    border: 1px solid #ccc;
                    border-left: 5px solid #2563eb;
                    padding: 12px 20px;
                    margin: 8px 0 25px 0;
                    background-color: #fff;
                }}
                .case-info-bar .info-item {{
                    flex: 1;
                }}
                .case-info-bar .info-label {{
                    font-size: 9pt;
                    font-weight: 700;
                    color: #333;
                    margin-bottom: 2px;
                }}
                .case-info-bar .info-value {{
                    font-size: 11pt;
                    color: #333;
                }}
                
                /* Notes Section */
                .notes-section {{
                    margin-top: 20px;
                    padding-top: 15px;
                }}
                .notes-section h2 {{
                    font-size: 13pt;
                    font-weight: 700;
                    color: #000000;
                    margin-bottom: 15px;
                    padding-bottom: 0;
                    letter-spacing: 0.5px;
                }}
                .notes-content {{
                    font-size: 11pt;
                    line-height: 1.75;
                    color: #333;
                }}
                
                /* Preserve TinyMCE formatting */
                .notes-content p {{ margin-bottom: 10px; }}
                .notes-content strong {{ font-weight: bold; }}
                .notes-content em {{ font-style: italic; }}
                .notes-content u {{ text-decoration: underline; }}
                .notes-content ul, .notes-content ol {{ margin-left: 25px; margin-bottom: 12px; }}
                .notes-content li {{ margin-bottom: 5px; }}
                .notes-content a {{ color: #2563eb; text-decoration: underline; }}
                .notes-content h1 {{ font-size: 16pt; margin: 18px 0 10px; color: #000000; }}
                .notes-content h2 {{ font-size: 14pt; margin: 15px 0 8px; color: #000000; }}
                .notes-content h3 {{ font-size: 12pt; margin: 12px 0 6px; color: #000000; }}
                .notes-content blockquote {{
                    border-left: 3px solid #2563eb;
                    padding: 8px 15px;
                    margin: 12px 0;
                    background-color: #f8f9fa;
                    color: #555;
                    font-style: italic;
                }}
                .notes-content pre {{
                    background-color: #f4f4f4;
                    padding: 10px 15px;
                    border-radius: 4px;
                    font-family: 'Courier New', monospace;
                    font-size: 10pt;
                    overflow-wrap: break-word;
                    margin: 10px 0;
                }}
                .notes-content table {{
                    border-collapse: collapse;
                    width: 100%;
                    margin: 12px 0;
                }}
                .notes-content table td, .notes-content table th {{
                    border: 1px solid #dee2e6;
                    padding: 8px 12px;
                    text-align: left;
                }}
                .notes-content table th {{
                    background-color: #f0f4f8;
                    font-weight: 600;
                }}
                .notes-content hr {{
                    border: none;
                    border-top: 1px solid #dee2e6;
                    margin: 15px 0;
                }}
                
                /* Image handling */
                .notes-content img {{
                    max-width: 100%;
                    height: auto;
                    display: block;
                    margin: 15px auto;
                    border: 1px solid #dee2e6;
                    border-radius: 4px;
                    box-shadow: 0 1px 4px rgba(0,0,0,0.1);
                    page-break-inside: avoid;
                }}
                
                /* Footer */
                .footer {{
                    margin-top: 40px;
                    padding-top: 15px;
                    border-top: 1px solid #dee2e6;
                    font-size: 9pt;
                    color: #999;
                    text-align: center;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <div class="header-text">
                    <h1>Technical Notes from the<br>ProFeds Benefits Team</h1>
                </div>
                {logo_img}
            </div>
            
            <div class="case-info-bar">
                <div class="info-item">
                    <div class="info-label">Federal Employee:</div>
                    <div class="info-value">{employee_name}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">Completion Date:</div>
                    <div class="info-value">{completion_date}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">Member Name (Code):</div>
                    <div class="info-value">{member_display}</div>
                </div>
            </div>
            
            <div class="notes-section">
                <h2>Notes to the ProFeds Member</h2>
                <div class="notes-content">
                    {notes_html}
                </div>
            </div>
            
            <div class="footer">
                <p>Confidential &mdash; Prepared for {employee_name} | ProFeds Advisor Portal</p>
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
        filename = f'{case.employee_last_name}_{case.employee_first_name}_Notes_{timezone.now().strftime("%Y%m%d")}.pdf'
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
                metadata=audit_details
            )
            
            logger.info(f'Case {case.external_case_id} details edited by {user.username}. Changes: {changes}')
            
            # Send optional notification email
            # DISABLED per email policy — members only receive HOLD, CHAT, READY emails
            if False and send_notification and case.member:
                try:
                    from cases.services.email_service import should_send_emails
                    
                    if not should_send_emails():
                        logger.info(f'Email notifications disabled. Skipped edit notification for case {case.external_case_id}')
                    else:
                        subject = f'Case for {case.employee_first_name} {case.employee_last_name} Details Updated'
                        
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

Your case for {case.employee_first_name} {case.employee_last_name} has been updated with the following corrections:

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
    available_techs = _exclude_super_dev_users(User.objects.filter(role__in=['technician', 'administrator'])).order_by('first_name', 'last_name')
    
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
            {'id': 'reports', 'label': 'Reports'},
            {'id': 'urgency', 'label': 'Urgency'},
            {'id': 'submitted', 'label': 'Submitted'},
            {'id': 'due', 'label': 'Due Date'},
            {'id': 'completed', 'label': 'Completed'},
            {'id': 'status', 'label': 'Status'},
            {'id': 'assigned_to', 'label': 'Assigned To'},
            {'id': 'tier', 'label': 'Tier'},
            {'id': 'credits', 'label': 'Credits'},
            {'id': 'actions', 'label': 'Actions'},
        ],
        'default_hidden': []
    },
    # NOTE - 02/14/2026: Admin dashboard columns have NOT been reordered to match the tech dashboard spec.
    # The tech dashboard was reordered to: Code, Member, Employee Name, Reports, Urgency, Submitted,
    # Due, Completed, Status, Assigned To, Tier, Actions (with Release Date, Date Scheduled, Notes,
    # Reviewed By, and On-Time/Late removed entirely).
    #
    # IMPORTANT DISTINCTION - Release Date vs Date Finalized:
    #   - 'date_completed' (labeled "Date Finalized") = The date the technician finishes working on the case (e.g., day 4)
    #   - 'release_date' (labeled "Release Date") = The date the case is released/available to the member (e.g., day 6)
    #   These are two different dates. A tech might finalize a case on day 4 but schedule it
    #   for release on day 6. Both are important for productivity tracking.
    #   Admin/Manager dashboards retain both columns for this reason.
    #
    # TODO: If admin/manager dashboards need the same reorder treatment, follow the tech dashboard
    # pattern: reorder config below, reorder <th> and <td> in admin_dashboard.html/manager_dashboard.html,
    # and remove unwanted columns from allowed_sorts in admin_dashboard()/manager_dashboard() views.
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
            {'id': 'credits', 'label': 'Credits'},
            {'id': 'reviewed_by', 'label': 'Reviewed By'},
            {'id': 'on_time', 'label': 'On-Time/Late'},
            {'id': 'date_completed', 'label': 'Date Finalized'},
            {'id': 'notes', 'label': 'Notes'},
            {'id': 'actions', 'label': 'Actions'},
        ],
        'default_hidden': ['reviewed_by', 'notes', 'tier', 'date_scheduled', 'reports']
    },
    # NOTE - 02/14/2026: Manager dashboard columns have NOT been reordered (same as admin above).
    # See admin_dashboard comment block for full context on Release Date vs Date Completed distinction
    # and future reorder instructions.
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
            {'id': 'on_time', 'label': 'On-Time/Late'},
            {'id': 'date_completed', 'label': 'Date Finalized'},
            {'id': 'notes', 'label': 'Notes'},
            {'id': 'actions', 'label': 'Actions'},
        ],
        'default_hidden': ['notes', 'reviewed_by', 'tier']
    },
    'member_dashboard': {
        'available_columns': [
            {'id': 'workshop', 'label': 'Code'},
            {'id': 'member', 'label': 'Member Name'},
            {'id': 'employee', 'label': 'Employee Name'},
            {'id': 'reports', 'label': 'Reports'},
            {'id': 'urgency', 'label': 'Urgency'},
            {'id': 'submitted', 'label': 'Submitted'},
            {'id': 'due_date', 'label': 'Due Date'},
            {'id': 'completed', 'label': 'Completed'},
            {'id': 'status', 'label': 'Status'},
            {'id': 'credit', 'label': 'Credit'},
            {'id': 'actions', 'label': 'Actions'},
        ],
        'default_hidden': ['workshop']
    }
}


def get_user_sort_preference(user, dashboard_name, default='-date_submitted'):
    """Get saved sort preference for user on a specific dashboard"""
    from accounts.models import UserPreference
    try:
        pref = UserPreference.objects.get(
            user=user,
            preference_key=f'{dashboard_name}_sort'
        )
        return pref.preference_value.get('sort', default)
    except UserPreference.DoesNotExist:
        return default


def save_user_sort_preference(user, dashboard_name, sort_value):
    """Save sort preference for user on a specific dashboard"""
    from accounts.models import UserPreference
    try:
        UserPreference.objects.update_or_create(
            user=user,
            preference_key=f'{dashboard_name}_sort',
            defaults={'preference_value': {'sort': sort_value}}
        )
    except Exception:
        pass  # Don't break the page if preference save fails


def get_user_visible_columns(user, dashboard_name):
    """Get list of visible column IDs for the user on a specific dashboard"""
    from accounts.models import UserPreference
    
    # Try to get saved user preference
    try:
        pref = UserPreference.objects.get(
            user=user,
            preference_key=f'{dashboard_name}_visible_columns'
        )
        saved_columns = pref.preference_value.get('visible_columns', [])
        
        # Auto-include any new columns added to config that the user hasn't seen yet
        # (i.e. columns not in their saved list AND not default-hidden)
        if dashboard_name in DASHBOARD_COLUMN_CONFIG:
            config = DASHBOARD_COLUMN_CONFIG[dashboard_name]
            all_ids = [col['id'] for col in config['available_columns']]
            hidden = config.get('default_hidden', [])
            for col_id in all_ids:
                if col_id not in saved_columns and col_id not in hidden:
                    saved_columns.append(col_id)
        
        return saved_columns
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
def _review_error(request, case_id, error_msg, status_code=400):
    """Helper to return error for review actions - redirect for form POST, JSON for AJAX."""
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': False, 'error': error_msg}, status=status_code)
    messages.error(request, error_msg)
    return redirect('cases:case_detail', pk=case_id)


@login_required
@require_http_methods(["POST"])
def approve_case_review(request, case_id):
    """Approve a case pending quality review — records approval then redirects to completion review."""
    from cases.models import CaseReviewHistory
    
    user = request.user
    case = get_object_or_404(Case, id=case_id)
    
    # Permission check - only Level 2/3 technicians and admins
    if user.role == 'technician' and user.user_level not in ['level_2', 'level_3']:
        return _review_error(request, case_id, 'You do not have permission to approve cases.', 403)
    elif user.role not in ['technician', 'administrator', 'manager']:
        return _review_error(request, case_id, 'You do not have permission to approve cases.', 403)
    
    # Check if case is pending review
    if case.status != 'pending_review':
        return _review_error(request, case_id, 'This case is not pending review.')
    
    try:
        review_notes = request.POST.get('review_notes', '').strip()
        
        # Record the approval but transition to completion review for credit/notes/scheduling
        case.status = 'accepted'  # Allow completion_review to process
        case.reviewed_by = user
        case.reviewed_at = timezone.now()
        case.review_status = 'approved'
        case.review_notes = review_notes
        case.save()
        
        # Create audit trail entry
        CaseReviewHistory.objects.create(
            case=case,
            reviewed_by=user,
            original_technician=case.assigned_to,
            review_action='approved',
            review_notes=review_notes
        )
        
        # Create internal note for the approval
        from cases.models import CaseNote
        approve_note = f'[Review Approved] Case approved by {user.get_full_name() or user.username}'
        if review_notes:
            approve_note += f'\nNotes: {review_notes}'
        CaseNote.objects.create(case=case, author=user, note=approve_note, is_internal=True)

        # Log to audit trail
        from core.models import AuditLog
        AuditLog.log_activity(
            user=user,
            action_type='case_review_approved',
            case=case,
            description=f'Case review approved by {user.get_full_name() or user.username}',
            changes={'status': {'from': 'pending_review', 'to': 'accepted'}},
            metadata={
                'review_notes': review_notes,
                'reviewed_by': user.username,
                'external_case_id': case.external_case_id,
                'employee_name': f'{case.employee_first_name} {case.employee_last_name}',
            },
            ip_address=request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', '')).split(',')[0].strip(),
        )
        
        messages.success(request, f'Case approved. Please verify credits, tech notes, and schedule the release.')
        return redirect('cases:completion_review', case_id=case_id)
    except Exception as e:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
        messages.error(request, f'Error approving case: {str(e)}')
        return redirect('cases:case_detail', pk=case_id)


@login_required
@require_http_methods(["POST"])
def request_case_revisions(request, case_id):
    """Request revisions on a case pending quality review - returns case to assigned technician"""
    from cases.models import CaseReviewHistory
    
    user = request.user
    case = get_object_or_404(Case, id=case_id)
    
    # Permission check - only Level 2/3 technicians and admins
    if user.role == 'technician' and user.user_level not in ['level_2', 'level_3']:
        return _review_error(request, case_id, 'You do not have permission to request revisions.', 403)
    elif user.role not in ['technician', 'administrator', 'manager']:
        return _review_error(request, case_id, 'You do not have permission to request revisions.', 403)
    
    # Check if case is pending review
    if case.status != 'pending_review':
        return _review_error(request, case_id, 'This case is not pending review.')
    
    try:
        revision_feedback = request.POST.get('revision_feedback', '').strip()
        
        if not revision_feedback:
            return _review_error(request, case_id, 'Revision feedback is required.')
        
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
        
        # Send email notification to Level 1 technician
        if case.assigned_to and case.assigned_to.email:
            try:
                from django.core.mail import send_mail
                from django.template.loader import render_to_string
                from cases.services.email_service import should_send_emails
                
                if should_send_emails():
                    email_context = {
                        'technician_name': case.assigned_to.get_full_name() or case.assigned_to.username,
                        'case_id': case.external_case_id,
                        'employee_name': f'{case.employee_first_name} {case.employee_last_name}',
                        'reviewer_name': user.get_full_name() or user.username,
                        'reviewed_at': timezone.now(),
                        'revision_feedback': revision_feedback,
                        'case_detail_url': f"{request.build_absolute_uri('/')}cases/{case.pk}/"
                    }
                    html_message = render_to_string('emails/case_revisions_needed_notification.html', email_context)
                    send_mail(
                        subject=f'Case for {case.employee_first_name} {case.employee_last_name} - Revisions Requested',
                        message=f'Revisions have been requested for case for {case.employee_first_name} {case.employee_last_name}. Feedback: {revision_feedback}',
                        from_email='noreply@advisor-portal.com',
                        recipient_list=[case.assigned_to.email],
                        html_message=html_message,
                        fail_silently=True
                    )
            except Exception as e:
                print(f'Error sending revision request email: {str(e)}')
        
        # Create internal note for the revision request
        from cases.models import CaseNote
        revision_note = f'[Revisions Requested] Revisions requested by {user.get_full_name() or user.username}\nFeedback: {revision_feedback}'
        CaseNote.objects.create(case=case, author=user, note=revision_note, is_internal=True)

        messages.success(request, f'Revisions requested for {case.employee_first_name} {case.employee_last_name} case.')
        
        # Log to audit trail
        from core.models import AuditLog
        AuditLog.log_activity(
            user=user,
            action_type='case_review_revisions',
            case=case,
            description=f'Revisions requested by {user.get_full_name() or user.username}',
            changes={'status': {'from': 'pending_review', 'to': 'accepted'}},
            metadata={
                'revision_feedback': revision_feedback,
                'reviewed_by': user.username,
                'external_case_id': case.external_case_id,
                'employee_name': f'{case.employee_first_name} {case.employee_last_name}',
            },
            ip_address=request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', '')).split(',')[0].strip(),
        )
        
        # Return redirect for standard form POST, JSON for AJAX
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': f'Revisions requested - case returned to technician',
                'redirect_url': str(reverse('cases:case_detail', kwargs={'pk': case_id}))
            })
        return redirect('cases:case_detail', pk=case_id)
    except Exception as e:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
        messages.error(request, f'Error requesting revisions: {str(e)}')
        return redirect('cases:case_detail', pk=case_id)


@login_required
@require_http_methods(["POST"])
def correct_case_review(request, case_id):
    """Apply corrections to a case during quality review - mark as completed with corrections noted"""
    from cases.models import CaseReviewHistory
    
    user = request.user
    case = get_object_or_404(Case, id=case_id)
    
    # Permission check - only Level 2/3 technicians and admins
    if user.role == 'technician' and user.user_level not in ['level_2', 'level_3']:
        return _review_error(request, case_id, 'You do not have permission to correct cases.', 403)
    elif user.role not in ['technician', 'administrator', 'manager']:
        return _review_error(request, case_id, 'You do not have permission to correct cases.', 403)
    
    # Check if case is pending review
    if case.status != 'pending_review':
        return _review_error(request, case_id, 'This case is not pending review.')
    
    try:
        correction_notes = request.POST.get('correction_notes', '').strip()
        
        if not correction_notes:
            return _review_error(request, case_id, 'Correction notes are required.')
        
        # Record corrections but transition to completion review instead of auto-completing
        case.status = 'accepted'  # Allow completion_review to process
        case.reviewed_by = user
        case.reviewed_at = timezone.now()
        case.review_status = 'corrections_needed'
        case.review_notes = correction_notes
        case.save()
        
        # Create audit trail entry
        CaseReviewHistory.objects.create(
            case=case,
            reviewed_by=user,
            original_technician=case.assigned_to,
            review_action='corrections_needed',
            review_notes=correction_notes
        )
        
        # Create internal note for the corrections
        from cases.models import CaseNote
        correction_note = f'[Corrections Applied] Corrections applied by {user.get_full_name() or user.username}\nNotes: {correction_notes}'
        CaseNote.objects.create(case=case, author=user, note=correction_note, is_internal=True)

        # Log to audit trail
        from core.models import AuditLog
        AuditLog.log_activity(
            user=user,
            action_type='case_review_corrected',
            case=case,
            description=f'Case corrected by {user.get_full_name() or user.username} — proceeding to completion review',
            changes={'status': {'from': 'pending_review', 'to': 'accepted'}},
            metadata={
                'correction_notes': correction_notes,
                'reviewed_by': user.username,
                'external_case_id': case.external_case_id,
                'employee_name': f'{case.employee_first_name} {case.employee_last_name}',
            },
            ip_address=request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', '')).split(',')[0].strip(),
        )
        
        messages.success(request, f'Corrections recorded. Please review and complete the case.')
        return redirect('cases:completion_review', case_id=case_id)
    except Exception as e:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
        messages.error(request, f'Error applying corrections: {str(e)}')
        return redirect('cases:case_detail', pk=case_id)


@login_required
@require_http_methods(["POST"])
def submit_for_review(request, case_id):
    """Technician submits case for quality review by a senior tech."""
    from cases.models import CaseReviewHistory
    from core.models import AuditLog, StaffNotification
    
    user = request.user
    case = get_object_or_404(Case, id=case_id)
    
    # Permission check - only the assigned technician can submit for review
    if user.role not in ['technician', 'administrator', 'manager']:
        return JsonResponse({'success': False, 'error': 'Permission denied.'}, status=403)
    if user.role == 'technician' and case.assigned_to != user:
        return JsonResponse({'success': False, 'error': 'You can only submit cases assigned to you.'}, status=403)
    
    # Case must be in accepted status (or accepted after revision)
    if case.status not in ['accepted']:
        return JsonResponse({'success': False, 'error': f'Case must be in Accepted status to submit for review. Current: {case.get_status_display()}'}, status=400)
    
    if request.method == 'POST':
        try:
            # Parse optional notes and reviewer from request body
            try:
                body = json.loads(request.body) if request.body else {}
            except json.JSONDecodeError:
                body = {}
            
            tech_notes = body.get('notes', '').strip()
            reviewer_id = body.get('reviewer_id')
            
            # Resolve optional reviewer
            reviewer = None
            if reviewer_id:
                reviewer = User.objects.filter(pk=reviewer_id).first()
                # Server-side guard: ensure super dev cannot be assigned as reviewer
                if reviewer and reviewer.email.lower() == _get_super_dev_email():
                    return JsonResponse({'success': False, 'error': 'Selected reviewer is not eligible.'}, status=400)
            
            # Set case to pending_review
            case.status = 'pending_review'
            case.review_status = None  # Clear any previous revision status
            case.scheduled_release_date = None
            case.actual_release_date = None
            case.scheduled_email_date = None
            case.actual_email_sent_date = None
            case.date_completed = None
            case.save()
            
            # Determine if this is a resubmission after revisions
            previous_reviews = CaseReviewHistory.objects.filter(
                case=case, review_action='revisions_requested'
            ).count()
            
            if previous_reviews > 0:
                review_notes = f'Case resubmitted for review by {user.get_full_name() or user.username} after revisions (revision #{previous_reviews})'
                action = 'resubmitted'
            else:
                review_notes = f'Case submitted for review by {user.get_full_name() or user.username}'
                action = 'submitted_for_review'
            
            if tech_notes:
                review_notes += f' — Notes: {tech_notes}'
            
            CaseReviewHistory.objects.create(
                case=case,
                original_technician=user,
                review_action=action,
                review_notes=review_notes
            )
            
            # Notify reviewer(s)
            employee_name = f'{case.employee_first_name} {case.employee_last_name}'.strip()
            notification_msg = f'{user.get_full_name() or user.username} submitted the case for {employee_name} for review.'
            if tech_notes:
                notification_msg += f' Notes: {tech_notes}'
            
            # Create internal note for the review submission
            from cases.models import CaseNote
            note_text = f'[Review Submitted] Case submitted for quality review by {user.get_full_name() or user.username}'
            if reviewer:
                note_text += f' — Reviewer: {reviewer.get_full_name() or reviewer.username}'
            if tech_notes:
                note_text += f'\nNotes: {tech_notes}'
            CaseNote.objects.create(case=case, author=user, note=note_text, is_internal=True)

            # Log to audit trail
            AuditLog.log_activity(
                user=user,
                action_type='case_submitted_for_review',
                case=case,
                description=review_notes,
                changes={'status': {'from': 'accepted', 'to': 'pending_review'}},
                metadata={
                    'submitted_by': user.username,
                    'resubmission': previous_reviews > 0,
                    'reviewer': reviewer.username if reviewer else None,
                    'notes': tech_notes or None,
                    'external_case_id': case.external_case_id,
                    'employee_name': f'{case.employee_first_name} {case.employee_last_name}',
                },
                ip_address=request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', '')).split(',')[0].strip(),
            )
            
            return JsonResponse({
                'success': True,
                'message': f'Case for {case.employee_first_name} {case.employee_last_name} submitted for quality review.'
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)


# ============================================================================
# AD-HOC REVIEW REQUEST VIEWS (Any technician can request a review)
# ============================================================================

@login_required
@require_http_methods(["POST"])
def request_review(request, case_id):
    """Any technician can request an ad-hoc review from a senior tech/admin/manager."""
    from cases.models import CaseReviewRequest
    from core.models import AuditLog, StaffNotification

    user = request.user
    case = get_object_or_404(Case, id=case_id)

    # Permission: only the assigned technician can request a review
    if user.role != 'technician' or case.assigned_to != user:
        return JsonResponse({'success': False, 'error': 'Only the assigned technician can request a review.'}, status=403)

    # Case must be in a workable status
    if case.status not in ('accepted', 'hold'):
        return JsonResponse({
            'success': False,
            'error': f'Cannot request review when case is in {case.get_status_display()} status.'
        }, status=400)

    try:
        body = json.loads(request.body) if request.body else {}
    except json.JSONDecodeError:
        body = {}

    reviewer_id = body.get('reviewer_id')
    notes = body.get('notes', '').strip()

    if not notes:
        return JsonResponse({'success': False, 'error': 'Please provide notes explaining what you need reviewed.'}, status=400)

    # Resolve reviewer (optional – None means "any senior")
    reviewer = None
    if reviewer_id:
        reviewer = User.objects.filter(pk=reviewer_id).first()
        if not reviewer or (reviewer.role == 'technician' and reviewer.user_level not in ('level_2', 'level_3')):
            return JsonResponse({'success': False, 'error': 'Selected reviewer is not a senior technician, administrator, or manager.'}, status=400)
        # Server-side guard: ensure super dev cannot be assigned as reviewer
        if reviewer.email.lower() == _get_super_dev_email():
            return JsonResponse({'success': False, 'error': 'Selected reviewer is not eligible.'}, status=400)

    review_request = CaseReviewRequest.objects.create(
        case=case,
        requested_by=user,
        reviewer=reviewer,
        notes=notes,
        status='pending',
    )

    # Audit log
    AuditLog.log_activity(
        user=user,
        action_type='review_requested',
        case=case,
        description=f'{user.get_full_name() or user.username} requested a review' + (f' from {reviewer.get_full_name() or reviewer.username}' if reviewer else ' from any senior technician'),
        metadata={
            'review_request_id': review_request.pk,
            'reviewer': reviewer.username if reviewer else None,
            'notes': notes,
        },
    )

    # Notify the reviewer (or all eligible reviewers)
    employee_name = f'{case.employee_first_name} {case.employee_last_name}'.strip()

    return JsonResponse({
        'success': True,
        'message': f'Review request submitted for {employee_name}.',
        'review_request_id': review_request.pk,
    })


@login_required
@require_http_methods(["POST"])
def respond_to_review_request(request, review_request_id):
    """Respond to an ad-hoc review request: approve, push_back, release, escalate, or cancel."""
    from cases.models import CaseReviewRequest
    from core.models import AuditLog, StaffNotification

    user = request.user
    review_request = get_object_or_404(CaseReviewRequest, pk=review_request_id)
    case = review_request.case

    # Permission: senior techs, admins, managers, or the original requester (for cancel)
    try:
        body = json.loads(request.body) if request.body else {}
    except json.JSONDecodeError:
        body = {}

    action = body.get('action')  # approved, pushed_back, released, escalated, cancelled
    response_notes = body.get('response_notes', '').strip()

    valid_actions = ['approved', 'pushed_back', 'released', 'escalated', 'cancelled']
    if action not in valid_actions:
        return JsonResponse({'success': False, 'error': f'Invalid action. Must be one of: {", ".join(valid_actions)}'}, status=400)

    # Cancel can only be done by the requester
    if action == 'cancelled':
        if user != review_request.requested_by and user.role not in ('administrator', 'manager'):
            return JsonResponse({'success': False, 'error': 'Only the requester or an admin/manager can cancel a review request.'}, status=403)
    else:
        # Other actions require reviewer privileges
        is_reviewer = (user.role == 'technician' and user.user_level in ('level_2', 'level_3')) or user.role in ('administrator', 'manager')
        if not is_reviewer:
            return JsonResponse({'success': False, 'error': 'You do not have permission to respond to review requests.'}, status=403)

    if not review_request.is_pending:
        return JsonResponse({'success': False, 'error': 'This review request has already been responded to.'}, status=400)

    # Require notes for push_back and escalate
    if action in ('pushed_back', 'escalated') and not response_notes:
        return JsonResponse({'success': False, 'error': 'Notes are required when pushing back or escalating.'}, status=400)

    # Handle escalation — create a new chained request
    escalate_to_id = body.get('escalate_to_id')
    if action == 'escalated':
        escalate_to = None
        if escalate_to_id:
            escalate_to = User.objects.filter(pk=escalate_to_id).first()
            if not escalate_to:
                return JsonResponse({'success': False, 'error': 'Escalation target user not found.'}, status=400)

        # Close the current request
        review_request.status = 'escalated'
        review_request.response_notes = response_notes
        review_request.responded_by = user
        review_request.responded_at = timezone.now()
        review_request.save()

        # Create a new chained request
        new_request = CaseReviewRequest.objects.create(
            case=case,
            requested_by=user,
            reviewer=escalate_to,
            notes=f'Escalated from {user.get_full_name() or user.username}: {response_notes}',
            status='pending',
            parent_request=review_request,
        )

        # Audit
        AuditLog.log_activity(
            user=user,
            action_type='review_escalated',
            case=case,
            description=f'{user.get_full_name() or user.username} escalated review request' + (f' to {escalate_to.get_full_name() or escalate_to.username}' if escalate_to else ''),
            metadata={
                'original_request_id': review_request.pk,
                'new_request_id': new_request.pk,
                'escalated_to': escalate_to.username if escalate_to else None,
                'notes': response_notes,
            },
        )

        employee_name = f'{case.employee_first_name} {case.employee_last_name}'.strip()

        return JsonResponse({
            'success': True,
            'message': f'Review request escalated.',
            'new_review_request_id': new_request.pk,
        })

    # Handle all other actions (approved, pushed_back, released, cancelled)
    review_request.status = action
    review_request.response_notes = response_notes
    review_request.responded_by = user
    review_request.responded_at = timezone.now()
    review_request.save()

    # Map action to audit action_type
    action_type_map = {
        'approved': 'review_requested',
        'pushed_back': 'review_pushed_back',
        'released': 'review_released',
        'cancelled': 'review_requested',
    }
    action_label_map = {
        'approved': 'approved',
        'pushed_back': 'pushed back',
        'released': 'released to member',
        'cancelled': 'cancelled',
    }

    AuditLog.log_activity(
        user=user,
        action_type=action_type_map.get(action, 'review_requested'),
        case=case,
        description=f'Review request {action_label_map.get(action, action)} by {user.get_full_name() or user.username}',
        metadata={
            'review_request_id': review_request.pk,
            'action': action,
            'response_notes': response_notes,
        },
    )

    employee_name = f'{case.employee_first_name} {case.employee_last_name}'.strip()
    label = action_label_map.get(action, action)

    # If released, mark case as completed and release to member
    if action == 'released':
        case.status = 'completed'
        case.reviewed_by = user
        case.reviewed_at = timezone.now()
        case.actual_release_date = timezone.now()
        case.date_completed = timezone.now()
        case.scheduled_release_date = None
        case.scheduled_email_date = None
        case.save()

        # Create notification for member
        from cases.models import CaseNotification
        _create_case_notification_if_allowed(
            case=case,
            member=case.member,
            notification_type='case_released',
            title=f'Your case for {employee_name} is completed',
            message=f'Your case for {employee_name} has been completed and is ready for you to review.',
        )

        # Send case completed email
        try:
            from cases.services.email_service import send_case_completed_email
            send_case_completed_email(case, request=request, user=user)
        except Exception as email_error:
            logger.error(f'Failed to send case completed email for case {case.pk}: {email_error}')

    return JsonResponse({
        'success': True,
        'message': f'Review request {label}.',
    })


@login_required
@require_http_methods(["GET"])
def get_review_requests(request, case_id):
    """Get all review requests for a case (used by case detail page)."""
    from cases.models import CaseReviewRequest

    user = request.user
    case = get_object_or_404(Case, id=case_id)

    # Permission: assigned tech, admins, managers, or L2/L3 techs
    if user.role == 'technician' and user.user_level not in ('level_2', 'level_3') and case.assigned_to != user:
        return JsonResponse({'success': False, 'error': 'Permission denied.'}, status=403)

    requests_qs = CaseReviewRequest.objects.filter(case=case).select_related(
        'requested_by', 'reviewer', 'responded_by', 'parent_request'
    ).order_by('-created_at')

    data = []
    for rr in requests_qs:
        data.append({
            'id': rr.pk,
            'requested_by': rr.requested_by.get_full_name() or rr.requested_by.username,
            'requested_by_id': rr.requested_by.pk,
            'reviewer': (rr.reviewer.get_full_name() or rr.reviewer.username) if rr.reviewer else 'Any Senior',
            'reviewer_id': rr.reviewer.pk if rr.reviewer else None,
            'notes': rr.notes,
            'status': rr.status,
            'status_display': rr.get_status_display(),
            'response_notes': rr.response_notes or '',
            'responded_by': (rr.responded_by.get_full_name() or rr.responded_by.username) if rr.responded_by else None,
            'responded_at': rr.responded_at.isoformat() if rr.responded_at else None,
            'created_at': rr.created_at.isoformat(),
            'parent_request_id': rr.parent_request.pk if rr.parent_request else None,
            'is_pending': rr.is_pending,
        })

    return JsonResponse({'success': True, 'review_requests': data})


@login_required
@require_http_methods(["GET"])
def get_eligible_reviewers(request):
    """Return list of eligible reviewers (higher-level techs + admins) for the reviewer dropdown.
    
    Reviewers must be at a higher level than the submitter:
    - L1 submitter → L2, L3 techs + admins
    - L2 submitter → L3 techs + admins
    - L3 submitter → admins only
    - Admin submitter → other admins
    """
    user = request.user
    if user.role not in ('technician', 'administrator', 'manager'):
        return JsonResponse({'success': False, 'error': 'Permission denied.'}, status=403)

    # Build filter based on submitter's level
    if user.role == 'technician' and user.user_level == 'level_1':
        # L1 can be reviewed by L2, L3, or admin
        eligible = User.objects.filter(
            Q(role='technician', user_level__in=['level_2', 'level_3']) |
            Q(role='administrator'),
            is_active=True,
        ).exclude(pk=user.pk)
    elif user.role == 'technician' and user.user_level == 'level_2':
        # L2 can be reviewed by L3 or admin
        eligible = User.objects.filter(
            Q(role='technician', user_level='level_3') |
            Q(role='administrator'),
            is_active=True,
        ).exclude(pk=user.pk)
    elif user.role == 'technician' and user.user_level == 'level_3':
        # L3 can only be reviewed by admin
        eligible = User.objects.filter(
            role='administrator',
            is_active=True,
        ).exclude(pk=user.pk)
    else:
        # Admin/manager submitting — show other admins
        eligible = User.objects.filter(
            role='administrator',
            is_active=True,
        ).exclude(pk=user.pk)

    # Exclude designated super-dev account globally (all environments)
    eligible = _exclude_super_dev_users(eligible)

    eligible = eligible.order_by('first_name', 'last_name')

    data = [{
        'id': u.pk,
        'name': u.get_full_name() or u.username,
        'role': u.get_role_display() if hasattr(u, 'get_role_display') else u.role,
        'level': u.get_user_level_display() if u.role == 'technician' else '',
    } for u in eligible]

    return JsonResponse({'success': True, 'reviewers': data})


# ============================================================================
# REVIEW SETTINGS MANAGEMENT (Admin/Manager toggle per-tech per-tier)
# ============================================================================

@login_required
@require_http_methods(["GET"])
def review_settings_page(request):
    """Page for admins/managers to manage per-tech per-tier review settings."""
    from cases.models import TechReviewSetting

    user = request.user
    if user.role not in ('administrator', 'manager') and not user.can_manage_review_settings:
        return HttpResponseForbidden('You do not have permission to manage review settings.')

    technicians = User.objects.filter(role='technician', is_active=True).order_by('first_name', 'last_name')
    settings_qs = TechReviewSetting.objects.select_related('technician', 'set_by').all()

    # Build a lookup: {tech_id: {tier: requires_review}}
    settings_map = {}
    for s in settings_qs:
        settings_map.setdefault(s.technician_id, {})[s.tier] = {
            'requires_review': s.requires_review,
            'set_by': s.set_by.get_full_name() or s.set_by.username if s.set_by else 'System Default',
            'updated_at': s.updated_at,
        }

    tiers = [('tier_1', 'Tier 1'), ('tier_2', 'Tier 2'), ('tier_3', 'Tier 3')]
    # Default review requirements: tier_1=True, tier_2/tier_3=False
    tier_defaults = {'tier_1': True, 'tier_2': False, 'tier_3': False}

    tech_data = []
    for tech in technicians:
        tech_settings = settings_map.get(tech.pk, {})
        tier_info = []
        for tier_key, tier_label in tiers:
            explicit = tech_settings.get(tier_key)
            if explicit:
                requires_review = explicit['requires_review']
                set_by = explicit['set_by']
                updated_at = explicit['updated_at']
                is_default = False
            else:
                requires_review = tier_defaults.get(tier_key, False)
                set_by = 'System Default'
                updated_at = None
                is_default = True
            tier_info.append({
                'tier_key': tier_key,
                'tier_label': tier_label,
                'requires_review': requires_review,
                'set_by': set_by,
                'updated_at': updated_at,
                'is_default': is_default,
            })
        tech_data.append({
            'user': tech,
            'tiers': tier_info,
        })

    context = {
        'tech_data': tech_data,
        'tiers': tiers,
    }
    return render(request, 'cases/review_settings.html', context)


@login_required
@require_http_methods(["POST"])
def update_review_setting(request):
    """Toggle a single per-tech per-tier review setting via AJAX."""
    from cases.models import TechReviewSetting
    from core.models import AuditLog

    user = request.user
    if user.role not in ('administrator', 'manager') and not user.can_manage_review_settings:
        return JsonResponse({'success': False, 'error': 'Permission denied.'}, status=403)

    try:
        body = json.loads(request.body) if request.body else {}
    except json.JSONDecodeError:
        body = {}

    tech_id = body.get('technician_id')
    tier = body.get('tier')
    requires_review = body.get('requires_review')

    if not tech_id or not tier or requires_review is None:
        return JsonResponse({'success': False, 'error': 'Missing required fields.'}, status=400)

    if tier not in ('tier_1', 'tier_2', 'tier_3'):
        return JsonResponse({'success': False, 'error': 'Invalid tier.'}, status=400)

    technician = User.objects.filter(pk=tech_id, role='technician').first()
    if not technician:
        return JsonResponse({'success': False, 'error': 'Technician not found.'}, status=400)

    setting, created = TechReviewSetting.objects.update_or_create(
        technician=technician,
        tier=tier,
        defaults={
            'requires_review': bool(requires_review),
            'set_by': user,
        },
    )

    AuditLog.log_activity(
        user=user,
        action_type='review_setting_changed',
        description=f'Review setting for {technician.get_full_name() or technician.username} {tier} set to {"required" if requires_review else "not required"}',
        metadata={
            'technician_id': technician.pk,
            'technician': technician.username,
            'tier': tier,
            'requires_review': bool(requires_review),
            'was_created': created,
        },
    )

    return JsonResponse({
        'success': True,
        'message': f'Review {"required" if requires_review else "not required"} for {technician.get_full_name() or technician.username} at {tier}.',
    })


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
    - Delegates see notifications for their delegated members' cases
    
    SECURITY:
    - Members can only view their own notifications
    - Delegates can view notifications for their delegated members' cases
    
    RESPONSE:
    - JSON with: notifications (list), total_count, unread_count, pages
    """
    from cases.models import CaseNotification
    from core.models import AuditLog
    from accounts.models import MemberDelegate
    
    user = request.user
    
    # Only members can view notifications
    if user.role != 'member':
        return JsonResponse({
            'success': False,
            'error': 'Only members can view notifications'
        }, status=403)
    
    try:
        # Build list of member IDs whose notifications this user can see
        member_ids = [user.id]
        delegate_assignments = MemberDelegate.objects.filter(
            delegate=user, portal_notifications=True
        ).select_related('member')
        for da in delegate_assignments:
            member_ids.append(da.member.id)
        
        # Get all notifications for self and delegated members
        notifications = CaseNotification.objects.filter(
            member_id__in=member_ids
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
        import pytz
        cst_tz = pytz.timezone('America/Chicago')
        for notif in page_obj.object_list:
            # Convert timestamps to CST (Central Time Zone)
            created_at_cst = notif.created_at.astimezone(cst_tz) if notif.created_at.tzinfo else pytz.UTC.localize(notif.created_at).astimezone(cst_tz)
            read_at_cst = notif.read_at.astimezone(cst_tz) if notif.read_at and notif.read_at.tzinfo else (pytz.UTC.localize(notif.read_at).astimezone(cst_tz) if notif.read_at else None)
            
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
                'created_at': created_at_cst.strftime('%b %d, %Y %I:%M %p %Z'),
                'read_at': read_at_cst.strftime('%b %d, %Y %I:%M %p %Z') if read_at_cst else None
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
        # Allow marking notifications for self or delegated members
        from accounts.models import MemberDelegate
        member_ids = [user.id]
        for da in MemberDelegate.objects.filter(delegate=user):
            member_ids.append(da.member_id)
        
        notification = get_object_or_404(CaseNotification, id=notification_id, member_id__in=member_ids)
        
        # Mark as read if not already
        was_unread = not notification.is_read
        notification.mark_as_read()
        
        # Log in audit trail
        if was_unread:
            AuditLog.objects.create(
                case=notification.case,
                user=user,
                action_type='other',
                description=f'Member viewed notification for case {notification.case.external_case_id}',
                metadata={
                    'notification_id': notification.id,
                    'notification_type': notification.notification_type,
                    'read_at': notification.read_at.isoformat(),
                    'sub_action': 'notification_viewed'
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
        # Get all unread notifications for self and delegated members
        from accounts.models import MemberDelegate
        member_ids = [user.id]
        for da in MemberDelegate.objects.filter(delegate=user):
            member_ids.append(da.member_id)
        
        unread_notifications = CaseNotification.objects.filter(
            member_id__in=member_ids,
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
                action_type='other',
                description=f'Member marked all {count} notifications as read',
                metadata={
                    'notifications_marked_read': count,
                    'timestamp': timezone.now().isoformat(),
                    'sub_action': 'all_notifications_viewed'
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
def api_technician_status(request):
    """
    Return online-status for all active technicians/administrators.
    Accessible to: technician, administrator, manager roles only.
    Status thresholds:
        active  — last_active within 5 minutes
        away    — last_active 5-30 minutes ago
        offline — last_active > 30 minutes ago or never
    """
    if request.user.role not in ('technician', 'administrator', 'manager'):
        return JsonResponse({'error': 'Forbidden'}, status=403)

    from django.utils import timezone
    now = timezone.now()

    techs = _exclude_super_dev_users(
        User.objects.filter(role__in=['technician', 'administrator'], is_active=True)
    ).values('username', 'first_name', 'last_active')

    result = []
    for tech in techs:
        last_active = tech['last_active']
        if last_active is None:
            status = 'offline'
            label = 'Never active'
        else:
            diff = (now - last_active).total_seconds()
            if diff < 300:
                status = 'active'
                label = 'Active now'
            elif diff < 1800:
                minutes = int(diff // 60)
                status = 'away'
                label = f'Away {minutes} min ago'
            else:
                hours = int(diff // 3600)
                days = int(diff // 86400)
                status = 'offline'
                if days >= 1:
                    label = f'Offline {days}d ago'
                elif hours >= 1:
                    label = f'Offline {hours}h ago'
                else:
                    label = f'Offline {int(diff // 60)}m ago'
        result.append({
            'username': tech['username'],
            'first_name': tech['first_name'],
            'status': status,
            'label': label,
        })

    return JsonResponse({'techs': result})


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
        # Get all cases on hold for this member + delegated members
        from accounts.models import MemberDelegate
        delegate_member_ids = list(
            MemberDelegate.objects.filter(delegate=user).values_list('member_id', flat=True)
        )
        hold_cases = Case.objects.filter(
            Q(member=user) | Q(member_id__in=delegate_member_ids),
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
        
        # Permission: Only member (or delegate) can create requests for their cases
        if case.member != user:
            from accounts.models import MemberDelegate
            if not MemberDelegate.objects.filter(delegate=user, member=case.member).exists():
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
        
        # Handle cancellation immediately (no approval needed)
        if request_type == 'cancellation':
            previous_assigned_to = case.assigned_to
            case.status = 'cancelled'
            case.urgency = 'normal'  # Clear rush urgency on terminal cases
            case.assigned_to = None
            case.save(update_fields=['status', 'urgency', 'assigned_to'])
            
            # Notify the assigned technician
            if previous_assigned_to:
                from cases.models import CaseNotification
                CaseNotification.objects.create(
                    case=case,
                    member=case.member,
                    notification_type='case_released',
                    title=f'Case Canceled by Member',
                    message=f'{user.get_full_name() or user.username} canceled {case.employee_first_name} {case.employee_last_name} case. Reason: {cancellation_reason}',
                )
                # Also create an UnreadMessage-style alert for the tech
                try:
                    from cases.models import CaseMessage
                    msg = CaseMessage.objects.create(
                        case=case,
                        sender=user,
                        message=f'[Case Canceled] Reason: {cancellation_reason}' + (f'\nNotes: {member_notes}' if member_notes else ''),
                    )
                    UnreadMessage.objects.get_or_create(
                        message=msg,
                        user=previous_assigned_to,
                        defaults={'case': case}
                    )
                except Exception as e:
                    logger.error(f'Error creating cancellation message: {str(e)}')
            
            # Log to audit trail
            from core.models import AuditLog
            AuditLog.log_activity(
                user=user,
                action_type='case_cancelled',
                case=case,
                description=f'Member canceled case: {cancellation_reason}',
                metadata={
                    'request_type': 'cancellation',
                    'cancellation_reason': cancellation_reason,
                    'member_notes': member_notes,
                }
            )
            
            logger.info(f'Member {user.id} canceled case {case_id}: {cancellation_reason}')
            
            return JsonResponse({
                'success': True,
                'message': 'Case has been canceled.',
            })
        
        # For other request types (e.g., due_date_extension), create a pending change request
        change_request = CaseChangeRequest(
            case=case,
            member=user,
            request_type=request_type,
            requested_due_date=requested_due_date if request_type == 'due_date_extension' else None,
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
            case.assigned_to = None
            case.status = 'cancelled'
            case.urgency = 'normal'  # Clear rush urgency on terminal cases
            case.save()
            
            # Log cancellation to audit trail
            from core.models import AuditLog
            AuditLog.log_activity(
                user=user,
                action_type='case_cancelled',
                case=case,
                description=f'Case canceled via approved member request',
                changes={'status': {'from': 'submitted', 'to': 'cancelled'}},
                metadata={'change_request_id': change_req.id}
            )
            
            logger.info(f'Tech {user.id} approved cancellation for case {case.id}')
        
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
        
        # Permission: Member or delegate can upload to the case
        is_case_delegate = False
        if case.member != user:
            from accounts.models import MemberDelegate
            is_case_delegate = MemberDelegate.objects.filter(
                delegate=user, member=case.member
            ).exists()
            if not is_case_delegate:
                return JsonResponse({'success': False, 'error': 'Not your case'}, status=403)
        
        # Can only upload for submitted/in-progress cases
        if case.status not in ['submitted', 'accepted', 'hold', 'pending_review', 'resubmitted', 'needs_resubmission']:
            return JsonResponse({
                'success': False,
                'error': f'Cannot upload documents for {case.get_status_display()} cases'
            }, status=400)
        
        # Get files from request
        document_files = request.FILES.getlist('document_file')
        document_notes = request.POST.get('document_notes', '').strip()
        
        if not document_files:
            return JsonResponse({'success': False, 'error': 'No file provided'}, status=400)
        
        uploaded_count = 0
        last_doc_id = None
        for document_file in document_files:
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
            uploaded_count += 1
            last_doc_id = doc.id
            
            # Log to audit trail
            from core.models import AuditLog
            upload_metadata = {
                'document_id': doc.id,
                'original_filename': document_file.name,
                'file_size': document_file.size,
                'notes': document_notes
            }
            upload_description = f'Member uploaded document: {filename_with_employee}'
            
            # Add delegate context if uploading on behalf of another member
            if is_case_delegate:
                upload_metadata['uploaded_by_delegate'] = True
                upload_metadata['delegate_id'] = user.id
                upload_metadata['delegate_name'] = user.get_full_name()
                upload_metadata['on_behalf_of'] = case.member.get_full_name()
                upload_description = f'Delegate {user.get_full_name()} uploaded document: {filename_with_employee} on behalf of {case.member.get_full_name()}'
            
            AuditLog.log_activity(
                user=user,
                action_type='member_document_uploaded',
                case=case,
                description=upload_description,
                metadata=upload_metadata
            )
        
        # Set flags to notify technician (has_member_updates drives "New Info" badge)
        case.has_member_new_info = True
        case.has_member_updates = True
        case.member_last_update_date = timezone.now()
        case.save(update_fields=['has_member_new_info', 'has_member_updates', 'member_last_update_date'])
        
        # Create StaffNotification for the assigned technician — only when case is on hold
        if case.assigned_to and case.status == 'hold':
            try:
                from core.models import StaffNotification
                StaffNotification.objects.create(
                    user=case.assigned_to,
                    notification_type='member_document_uploaded',
                    title=f'New Document — {case.employee_first_name} {case.employee_last_name}',
                    message=f'Member {user.get_full_name() or user.username} uploaded {uploaded_count} document(s) for {case.employee_first_name} {case.employee_last_name}.',
                    case=case,
                    is_read=False
                )
            except Exception as notif_err:
                logger.warning(f'Failed to create staff notification for member doc upload on case {case_id}: {notif_err}')
        # Post a system chat message so the badge increments and the tech knows what triggered it
        if case.assigned_to:
            try:
                _uploader = user.get_full_name() or user.username
                _upload_msg = CaseMessage.objects.create(
                    case=case,
                    author=user,
                    message=f'📎 {_uploader} uploaded {uploaded_count} document(s).'
                )
                UnreadMessage.objects.get_or_create(
                    message=_upload_msg,
                    user=case.assigned_to,
                    defaults={'case': case}
                )
            except Exception as e:
                logger.warning(f'Failed to create upload alert message for case {case_id}: {e}')
        
        # Count total member-uploaded documents (supporting docs)
        document_count = CaseDocument.objects.filter(
            case=case,
            document_type='supporting',
            uploaded_by=user
        ).count()
        
        logger.info(f'Member {user.id} uploaded {uploaded_count} document(s) to case {case_id}')
        
        return JsonResponse({
            'success': True,
            'message': f'✓ {uploaded_count} document(s) uploaded successfully',
            'document_count': document_count,
            'document_id': last_doc_id
        })
    
    except Exception as e:
        logger.error(f'Error uploading member document: {str(e)}', exc_info=True)
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# URL Routing Wrappers - connect URL names to view functions
@login_required
def approve_change_request(request, request_id):
    """Wrapper for approve_case_change_request for URL routing"""
    return approve_case_change_request(request, request_id)


@login_required
def deny_change_request(request, request_id):
    """Wrapper for deny_case_change_request for URL routing"""
    return deny_case_change_request(request, request_id)


# ============================================================================
# STAFF NOTIFICATION API VIEWS
# ============================================================================

@login_required
@require_http_methods(["GET"])
def get_staff_notifications(request):
    """
    Get staff notifications for the logged-in user.
    Each staff member only sees notifications addressed to them.
    """
    from core.models import StaffNotification

    user = request.user
    if user.role not in ('technician', 'administrator', 'manager'):
        return JsonResponse({'success': False, 'error': 'Staff only'}, status=403)

    try:
        notifications = StaffNotification.objects.filter(user=user).order_by('-created_at')

        page_num = request.GET.get('page', 1)
        paginator = Paginator(notifications, 20)
        page_obj = paginator.get_page(page_num)

        unread_count = notifications.filter(is_read=False).count()

        import pytz
        cst_tz = pytz.timezone('America/Chicago')
        notification_list = []
        for notif in page_obj.object_list:
            created_cst = notif.created_at.astimezone(cst_tz) if notif.created_at.tzinfo else pytz.UTC.localize(notif.created_at).astimezone(cst_tz)
            notification_list.append({
                'id': notif.id,
                'case_id': notif.case_id,
                'employee_name': f'{notif.case.employee_first_name} {notif.case.employee_last_name}' if notif.case else None,
                'notification_type': notif.notification_type,
                'notification_type_display': notif.get_notification_type_display(),
                'title': notif.title,
                'message': notif.message,
                'is_read': notif.is_read,
                'created_at': created_cst.strftime('%b %d, %Y %I:%M %p %Z'),
            })

        return JsonResponse({
            'success': True,
            'notifications': notification_list,
            'total_count': notifications.count(),
            'unread_count': unread_count,
            'pages': paginator.num_pages,
        })
    except Exception as e:
        logger.error(f'Error loading staff notifications: {e}', exc_info=True)
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def mark_staff_notification_read(request, notification_id):
    """Mark a single staff notification as read and clear the user's own UnreadMessage
    rows for that case so the dashboard row badge reflects the acknowledgement.
    Only the requesting user's own rows are removed; other staff unread state is untouched.
    """
    from core.models import StaffNotification

    user = request.user
    if user.role not in ('technician', 'administrator', 'manager'):
        return JsonResponse({'success': False, 'error': 'Staff only'}, status=403)

    try:
        notif = get_object_or_404(StaffNotification, id=notification_id, user=user)
        if not notif.is_read:
            notif.is_read = True
            notif.read_at = timezone.now()
            notif.save(update_fields=['is_read', 'read_at'])
        # Clear this user's UnreadMessage rows for this case so the row badge clears.
        # Scoped to user=user — admin/manager cannot clear another tech's unread rows.
        if notif.case_id:
            UnreadMessage.objects.filter(case_id=notif.case_id, user=user).delete()
        return JsonResponse({'success': True, 'notification_id': notif.id})
    except Exception as e:
        logger.error(f'Error marking staff notification {notification_id} read: {e}', exc_info=True)
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def mark_all_staff_notifications_read(request):
    """Mark all unread staff notifications as read and clear all of the user's own
    UnreadMessage rows so every case row badge reflects the bulk-acknowledge.
    Scoped entirely to the requesting user — no other staff member's rows are touched.
    """
    from core.models import StaffNotification

    user = request.user
    if user.role not in ('technician', 'administrator', 'manager'):
        return JsonResponse({'success': False, 'error': 'Staff only'}, status=403)

    try:
        now = timezone.now()
        count = StaffNotification.objects.filter(
            user=user, is_read=False
        ).update(is_read=True, read_at=now)
        # Clear all UnreadMessage rows for this user so all case row badges clear.
        # Only affects the requesting user's own rows.
        UnreadMessage.objects.filter(user=user).delete()
        return JsonResponse({'success': True, 'marked_count': count})
    except Exception as e:
        logger.error(f'Error marking all staff notifications read: {e}', exc_info=True)
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
