"""
Reports and Analytics Views
Provides comprehensive reporting and analytics for administrators
"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from django.db.models import Count, Q, Avg, F, Sum, Max, Case as CaseWhen, When, Value, FloatField
from django.utils import timezone
from datetime import timedelta
import csv
from cases.models import Case
from accounts.models import User
from core.models import BetaFeedback, SystemSettings


def is_admin(user):
    """Helper function to check if user is administrator"""
    return user.is_authenticated and user.role == 'administrator'


def _get_super_dev_email():
    """Return configured super-dev email from system settings."""
    try:
        return (SystemSettings.get_settings().super_dev_email or '').strip().lower()
    except Exception:
        return ''


def _exclude_super_dev_users(queryset):
    """Exclude test accounts (is_test_account=True) and the configured super-dev
    email from report user metrics."""
    queryset = queryset.filter(is_test_account=False)
    super_dev_email = _get_super_dev_email()
    if super_dev_email:
        queryset = queryset.exclude(email__iexact=super_dev_email)
    return queryset


def _exclude_test_account_cases(qs):
    """Exclude cases where the assigned technician or submitting member is a test
    account (is_test_account=True). NULL assigned_to/member are kept."""
    return qs.exclude(assigned_to__is_test_account=True).exclude(member__is_test_account=True)


@login_required
def view_reports(request):
    """Main reports page - Admin and Manager only"""
    if not is_admin(request.user):
        messages.error(request, 'Access denied. Administrators and Managers only.')
        return redirect('home')
    
    # Get custom date range if provided
    custom_date_from = request.GET.get('date_from')
    custom_date_to = request.GET.get('date_to')
    
    # Get all report data
    context = get_all_reports_data(custom_date_from, custom_date_to)
    context['custom_date_from'] = custom_date_from
    context['custom_date_to'] = custom_date_to
    
    return render(request, 'core/view_reports.html', context)


def get_all_reports_data(date_from=None, date_to=None):
    """Compile all report data for the dashboard with optional date filtering"""
    from datetime import datetime
    
    # Build base queryset with optional date filter — exclude test account cases
    cases_qs = _exclude_test_account_cases(Case.objects.all())
    
    if date_from or date_to:
        if date_from:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
            cases_qs = cases_qs.filter(date_submitted__date__gte=date_from_obj)
        if date_to:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
            cases_qs = cases_qs.filter(date_submitted__date__lte=date_to_obj)
    
    # === CASE ANALYTICS ===
    total_cases = cases_qs.count()
    completed_cases = cases_qs.filter(status='completed').count()
    submitted_cases = cases_qs.filter(status='submitted').count()
    
    # Average processing time (days from submission to completion)
    completed_with_dates = cases_qs.filter(
        status='completed',
        date_submitted__isnull=False,
        date_completed__isnull=False
    ).annotate(
        processing_days=F('date_completed') - F('date_submitted')
    ).aggregate(avg_days=Avg('processing_days'))
    
    avg_processing_time = completed_with_dates['avg_days']
    if avg_processing_time:
        avg_processing_time = avg_processing_time.days
    
    # Rush vs Standard cases
    rush_cases = cases_qs.filter(urgency='rush').count()
    standard_cases = cases_qs.filter(urgency='normal').count()
    
    # Cases by urgency level
    cases_by_urgency = cases_qs.values('urgency').annotate(count=Count('id')).order_by('urgency')
    
    # === PERFORMANCE METRICS ===
    # Cases per technician
    cases_per_tech = cases_qs.filter(
        assigned_to__isnull=False
    ).values(
        'assigned_to__id',
        'assigned_to__username',
        'assigned_to__first_name',
        'assigned_to__last_name'
    ).annotate(
        case_count=Count('id')
    ).order_by('-case_count')
    
    # Average credits per case
    avg_credits = cases_qs.exclude(credit_value__isnull=True).aggregate(
        avg=Avg(F('credit_value'), output_field=FloatField())
    )
    
    avg_credits_value = avg_credits['avg'] or 0
    
    # Quality review metrics - approval rates
    level_1_cases = cases_qs.filter(assigned_to__user_level='level_1')
    level_1_completed = level_1_cases.filter(status='completed').count()
    level_1_pending_review = level_1_cases.filter(status='pending_review').count()
    level_1_total = level_1_cases.count()
    
    if level_1_total > 0:
        approval_rate = (level_1_completed / level_1_total) * 100
    else:
        approval_rate = 0
    
    # Member activity
    total_members = _exclude_super_dev_users(User.objects.filter(role='member')).count()
    members_with_cases = cases_qs.filter(
        member__isnull=False
    ).values('member_id').distinct().count()
    
    # === FINANCIAL REPORTS ===
    # Credits analysis - only count credits from completed or accepted cases
    financial_cases = cases_qs.filter(status__in=['accepted', 'completed'])
    total_credits_issued = financial_cases.exclude(credit_value__isnull=True).aggregate(
        total=Sum(F('credit_value'), output_field=FloatField())
    )['total'] or 0
    
    # Credits by workshop code - only from completed/accepted cases
    credits_by_workshop = financial_cases.exclude(credit_value__isnull=True).values(
        'workshop_code'
    ).annotate(
        total_credits=Sum(F('credit_value'), output_field=FloatField()),
        case_count=Count('id'),
        avg_credits=F('total_credits') / F('case_count')
    ).order_by('-total_credits')[:10]
    
    # === STATUS REPORTS ===
    status_distribution = cases_qs.values('status').annotate(
        count=Count('id')
    ).order_by('status')
    
    status_labels = {
        'draft': 'Draft',
        'submitted': 'Submitted',
        'accepted': 'Accepted',
        'hold': 'On Hold',
        'pending_review': 'Pending Review',
        'completed': 'Completed',
    }
    
    # Cases by status with readable labels
    cases_by_status = []
    for item in status_distribution:
        percentage = (item['count'] / total_cases * 100) if total_cases > 0 else 0
        cases_by_status.append({
            'status': item['status'],
            'label': status_labels.get(item['status'], item['status']),
            'count': item['count'],
            'percentage': round(percentage, 1)
        })
    
    # === TECHNICIAN WORKLOAD ===
    # Group by user level
    level_1_techs = _exclude_super_dev_users(User.objects.filter(role='technician', user_level='level_1')).count()
    level_2_techs = _exclude_super_dev_users(User.objects.filter(role='technician', user_level='level_2')).count()
    level_3_techs = _exclude_super_dev_users(User.objects.filter(role='technician', user_level='level_3')).count()
    
    # Recent cases based on date filter (use custom date range if provided, else last 30 days)
    if date_from or date_to:
        recent_cases = cases_qs.count()
    else:
        thirty_days_ago = timezone.now() - timedelta(days=30)
        recent_cases = Case.objects.filter(date_submitted__gte=thirty_days_ago).count()
    
    return {
        # Case Analytics
        'total_cases': total_cases,
        'completed_cases': completed_cases,
        'submitted_cases': submitted_cases,
        'avg_processing_time': avg_processing_time,
        'rush_cases': rush_cases,
        'standard_cases': standard_cases,
        'cases_by_urgency': cases_by_urgency,
        
        # Performance Metrics
        'cases_per_tech': cases_per_tech,
        'avg_credits': avg_credits_value,
        'level_1_approval_rate': approval_rate,
        'level_1_completed': level_1_completed,
        'level_1_pending': level_1_pending_review,
        'level_1_total': level_1_total,
        'total_members': total_members,
        'active_members': members_with_cases,
        
        # Financial Reports
        'total_credits_issued': total_credits_issued,
        'credits_by_workshop': credits_by_workshop,
        
        # Status Reports
        'cases_by_status': cases_by_status,
        
        # Technician Breakdown
        'level_1_count': level_1_techs,
        'level_2_count': level_2_techs,
        'level_3_count': level_3_techs,
        'recent_cases_30days': recent_cases,
    }


@login_required
def export_reports_csv(request):
    """Export all reports to CSV format"""
    if not is_admin(request.user):
        messages.error(request, 'Access denied. Administrators and Managers only.')
        return redirect('home')
    
    # Get all report data
    data = get_all_reports_data()
    
    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="advisor-portal-reports.csv"'
    
    writer = csv.writer(response)
    
    # === CASE ANALYTICS SECTION ===
    writer.writerow(['CASE ANALYTICS DASHBOARD'])
    writer.writerow([])
    writer.writerow(['Metric', 'Value'])
    writer.writerow(['Total Cases', data['total_cases']])
    writer.writerow(['Completed Cases', data['completed_cases']])
    writer.writerow(['Submitted Cases', data['submitted_cases']])
    if data['avg_processing_time']:
        writer.writerow(['Average Processing Time (Days)', f"{data['avg_processing_time']:.1f}"])
    writer.writerow(['Rush Cases', data['rush_cases']])
    writer.writerow(['Standard Cases', data['standard_cases']])
    writer.writerow([])
    
    # Cases by urgency
    writer.writerow(['Cases by Urgency'])
    writer.writerow(['Urgency', 'Count'])
    for item in data['cases_by_urgency']:
        writer.writerow([item['urgency'], item['count']])
    writer.writerow([])
    
    # === PERFORMANCE METRICS SECTION ===
    writer.writerow(['PERFORMANCE METRICS'])
    writer.writerow([])
    writer.writerow(['Metric', 'Value'])
    writer.writerow(['Average Credits Per Case', f"{data['avg_credits']:.2f}"])
    writer.writerow(['Level 1 Approval Rate', f"{data['level_1_approval_rate']:.1f}%"])
    writer.writerow(['Level 1 Completed', data['level_1_completed']])
    writer.writerow(['Level 1 Pending Review', data['level_1_pending']])
    writer.writerow(['Total Members', data['total_members']])
    writer.writerow(['Active Members (With Cases)', data['active_members']])
    writer.writerow([])
    
    # Cases per technician
    writer.writerow(['Cases Per Technician'])
    writer.writerow(['Technician', 'Cases'])
    for tech in data['cases_per_tech']:
        first = tech.get('assigned_to__first_name') or ''
        last = tech.get('assigned_to__last_name') or ''
        username = tech.get('assigned_to__username') or ''
        name = f"{first} {last}".strip() if (first or last) else username
        writer.writerow([name, tech['case_count']])
    writer.writerow([])
    
    # === FINANCIAL REPORTS SECTION ===
    writer.writerow(['FINANCIAL REPORTS'])
    writer.writerow([])
    writer.writerow(['Metric', 'Value'])
    writer.writerow(['Total Credits Issued', f"{data['total_credits_issued']:.1f}"])
    writer.writerow([])
    
    # Credits by workshop code
    writer.writerow(['Credits by Workshop Code'])
    writer.writerow(['Workshop Code', 'Total Credits', 'Case Count', 'Avg Credits/Case'])
    for item in data['credits_by_workshop']:
        avg = item['total_credits'] / item['case_count'] if item['case_count'] > 0 else 0
        writer.writerow([
            item['workshop_code'],
            f"{item['total_credits']:.1f}",
            item['case_count'],
            f"{avg:.2f}"
        ])
    writer.writerow([])
    
    # === STATUS REPORTS SECTION ===
    writer.writerow(['STATUS DISTRIBUTION'])
    writer.writerow([])
    writer.writerow(['Status', 'Count'])
    for item in data['cases_by_status']:
        writer.writerow([item['label'], item['count']])
    writer.writerow([])
    
    # === TECHNICIAN BREAKDOWN ===
    writer.writerow(['TECHNICIAN LEVELS'])
    writer.writerow([])
    writer.writerow(['Level', 'Count'])
    writer.writerow(['Level 1 (New)', data['level_1_count']])
    writer.writerow(['Level 2 (Independent)', data['level_2_count']])
    writer.writerow(['Level 3 (Senior)', data['level_3_count']])
    writer.writerow([])
    
    # === ACTIVITY SECTION ===
    writer.writerow(['ACTIVITY SUMMARY'])
    writer.writerow([])
    writer.writerow(['Metric', 'Value'])
    writer.writerow(['Cases Submitted (Last 30 Days)', data['recent_cases_30days']])
    writer.writerow(['Export Date', timezone.now().strftime('%Y-%m-%d %H:%M:%S UTC')])
    
    return response


@login_required
def profeds_error_tracking_report(request):
    """
    Report showing ProFeds error cases - Admin and Manager only
    
    Displays:
    - Cases flagged with ProFeds errors
    - Count of errors per technician
    - Modification details
    - Timeline of errors
    """
    if not is_admin(request.user):
        messages.error(request, 'Access denied. Administrators and Managers only.')
        return redirect('home')
    
    # Get date range from request
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    # Build queryset for cases with ProFeds errors — exclude test account cases
    error_cases_qs = _exclude_test_account_cases(Case.objects.filter(has_profeds_error=True))
    
    if date_from:
        from datetime import datetime
        date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
        error_cases_qs = error_cases_qs.filter(date_submitted__date__gte=date_from_obj)
    
    if date_to:
        from datetime import datetime
        date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
        error_cases_qs = error_cases_qs.filter(date_submitted__date__lte=date_to_obj)
    
    # Get error statistics
    total_error_cases = error_cases_qs.count()
    
    # Errors per technician
    errors_per_tech = error_cases_qs.filter(
        assigned_to__isnull=False
    ).values(
        'assigned_to__id',
        'assigned_to__username',
        'assigned_to__first_name',
        'assigned_to__last_name'
    ).annotate(
        error_count=Count('id'),
        avg_error_count=Avg('error_modification_count')
    ).order_by('-error_count')
    
    # Error trends (by week)
    from django.db.models.functions import TruncWeek
    error_trends = error_cases_qs.annotate(
        week=TruncWeek('date_submitted')
    ).values('week').annotate(
        count=Count('id')
    ).order_by('week')
    
    # Get all error cases for table
    error_cases = error_cases_qs.select_related(
        'assigned_to',
        'member',
        'original_case'
    ).order_by('-date_submitted')[:500]  # Limit to 500 recent cases
    
    context = {
        'total_error_cases': total_error_cases,
        'errors_per_tech': errors_per_tech,
        'error_trends': list(error_trends),
        'error_cases': error_cases,
        'date_from': date_from,
        'date_to': date_to,
        'report_type': 'ProFeds Error Tracking',
    }
    
    # Handle CSV export
    if request.GET.get('export') == 'csv':
        return export_error_tracking_csv(error_cases, date_from, date_to)

    return render(request, 'core/profeds_error_tracking_report.html', context)


@login_required
def profeds_error_tracking_pdf(request):
    """PDF export of the ProFeds error tracking report."""
    if not is_admin(request.user):
        return HttpResponse('Access denied.', status=403)

    from weasyprint import HTML
    from io import BytesIO
    from django.template.loader import render_to_string
    from datetime import datetime

    date_from = request.GET.get('date_from', '').strip()
    date_to = request.GET.get('date_to', '').strip()

    error_cases_qs = _exclude_test_account_cases(Case.objects.filter(has_profeds_error=True))
    if date_from:
        error_cases_qs = error_cases_qs.filter(
            date_submitted__date__gte=datetime.strptime(date_from, '%Y-%m-%d').date()
        )
    if date_to:
        error_cases_qs = error_cases_qs.filter(
            date_submitted__date__lte=datetime.strptime(date_to, '%Y-%m-%d').date()
        )

    errors_per_tech = error_cases_qs.filter(assigned_to__isnull=False).values(
        'assigned_to__first_name', 'assigned_to__last_name'
    ).annotate(error_count=Count('id'), avg_error_count=Avg('error_modification_count')).order_by('-error_count')

    error_cases = error_cases_qs.select_related('assigned_to', 'member').order_by('-date_submitted')[:500]

    period_label = ''
    if date_from and date_to:
        period_label = f"{date_from} – {date_to}"
    elif date_from:
        period_label = f"From {date_from}"
    elif date_to:
        period_label = f"Through {date_to}"
    else:
        period_label = 'All Time'

    context = {
        'total_error_cases': error_cases_qs.count(),
        'errors_per_tech': errors_per_tech,
        'error_cases': error_cases,
        'date_from': date_from,
        'date_to': date_to,
        'period_label': period_label,
        'generated_at': timezone.now(),
        'generated_by': request.user.get_full_name() or request.user.username,
    }

    html_string = render_to_string('core/profeds_error_tracking_report_pdf.html', context)
    pdf_buffer = BytesIO()
    HTML(string=html_string, base_url=request.build_absolute_uri('/')).write_pdf(pdf_buffer)
    pdf_buffer.seek(0)

    date_slug = timezone.now().strftime('%Y%m%d')
    response = HttpResponse(pdf_buffer.read(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="ProFeds_Error_Report_{date_slug}.pdf"'
    return response


def export_error_tracking_csv(error_cases, date_from, date_to):
    """Export ProFeds error tracking data to CSV"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="profeds_error_report.csv"'
    
    writer = csv.writer(response)
    
    # Header
    writer.writerow(['ProFeds Error Tracking Report'])
    writer.writerow([f'Generated: {timezone.now().strftime("%Y-%m-%d %H:%M:%S UTC")}'])
    if date_from or date_to:
        writer.writerow([f'Date Range: {date_from or "N/A"} to {date_to or "N/A"}'])
    writer.writerow([])
    
    # Error cases table
    writer.writerow(['Case ID', 'Member', 'Technician', 'Status', 'Error Count', 'Date Submitted', 'Notes'])
    for case in error_cases:
        writer.writerow([
            case.external_case_id,
            case.member.get_full_name() if case.member else 'N/A',
            case.assigned_to.get_full_name() if case.assigned_to else 'Unassigned',
            case.status,
            case.error_modification_count,
            case.date_submitted.strftime('%Y-%m-%d %H:%M') if case.date_submitted else 'N/A',
            'Original case' if case.original_case else 'Primary case'
        ])
    
    return response


@login_required
def beta_feedback_report(request):
    """View all beta feedback - Admin and Manager only"""
    if not is_admin(request.user):
        messages.error(request, 'Access denied. Administrators and Managers only.')
        return redirect('home')

    feedback_list = BetaFeedback.objects.select_related('user').all()

    # CSV export
    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="member_portal_feedback.csv"'
        writer = csv.writer(response)
        writer.writerow(['#', 'Member Name', 'Username', 'Email', 'Date Submitted', 'Feedback'])
        for i, fb in enumerate(feedback_list, start=1):
            writer.writerow([
                i,
                fb.user.get_full_name() if fb.user else '',
                fb.user.username if fb.user else '',
                fb.user.email if fb.user else '',
                fb.created_at.strftime('%Y-%m-%d %H:%M'),
                fb.feedback,
            ])
        return response

    context = {
        'feedback_list': feedback_list,
        'total_count': feedback_list.count(),
    }
    return render(request, 'core/beta_feedback_report.html', context)


@login_required
def beta_feedback_pdf(request):
    """Download Member Portal Feedback report as PDF."""
    if not is_admin(request.user):
        return HttpResponse('Access denied.', status=403)

    from weasyprint import HTML
    from io import BytesIO
    from django.template.loader import render_to_string

    feedback_list = BetaFeedback.objects.select_related('user').all()
    html_string = render_to_string('core/beta_feedback_report_pdf.html', {
        'feedback_list': feedback_list,
        'total_count': feedback_list.count(),
        'generated_at': timezone.now(),
        'generated_by': request.user.get_full_name() or request.user.username,
    })
    pdf_buffer = BytesIO()
    HTML(string=html_string, base_url=request.build_absolute_uri('/')).write_pdf(pdf_buffer)
    pdf_buffer.seek(0)
    response = HttpResponse(pdf_buffer.read(), content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="member_portal_feedback.pdf"'
    return response


# ---------------------------------------------------------------------------
# Technician Productivity Report
# ---------------------------------------------------------------------------

def get_technician_productivity_data(tech_id=None, date_from=None, date_to=None):
    """
    Compile productivity metrics for one technician or all technicians.
    Date range is applied on date_accepted (when the tech took the case).
    Returns a list of per-technician dicts.
    """
    from django.db.models.functions import TruncWeek
    from django.db.models import DurationField

    if tech_id and str(tech_id) != 'all':
        try:
            techs = User.objects.filter(id=int(tech_id), role='technician')
        except (ValueError, TypeError):
            techs = User.objects.none()
    else:
        techs = _exclude_super_dev_users(
            User.objects.filter(role='technician')
        ).order_by('first_name', 'last_name')

    results = []
    for tech in techs:
        qs = Case.objects.filter(assigned_to=tech)

        if date_from:
            qs = qs.filter(date_accepted__date__gte=date_from)
        if date_to:
            qs = qs.filter(date_accepted__date__lte=date_to)

        # ── Core counts ──────────────────────────────────────────────────────
        total_accepted = qs.count()
        completed_qs = qs.filter(status='completed')
        completed_count = completed_qs.count()
        in_progress_count = qs.filter(status='accepted').count()
        on_hold_count = qs.filter(status='hold').count()
        pending_review_count = qs.filter(status='pending_review').count()
        rush_count = qs.filter(urgency='rush').count()
        error_count = qs.filter(has_profeds_error=True).count()
        completion_rate = round((completed_count / total_accepted * 100), 1) if total_accepted else 0

        # ── Completion time ──────────────────────────────────────────────────
        timed_qs = completed_qs.filter(
            date_accepted__isnull=False,
            date_completed__isnull=False,
        ).annotate(duration=F('date_completed') - F('date_accepted'))

        avg_agg = timed_qs.aggregate(avg=Avg('duration'))
        avg_days = avg_agg['avg'].days if avg_agg['avg'] else None

        durations = [r.duration.days for r in timed_qs if r.duration is not None and r.duration.days >= 0]
        fastest_days = min(durations) if durations else None
        slowest_days = max(durations) if durations else None

        # ── On-time rate ─────────────────────────────────────────────────────
        on_time_count = completed_qs.filter(
            date_completed__isnull=False,
            date_due__isnull=False,
            date_completed__lte=F('date_due'),
        ).count()
        on_time_rate = round(on_time_count / completed_count * 100, 1) if completed_count else 0

        # ── Tier breakdown ───────────────────────────────────────────────────
        tier_counts = {}
        for tier_val, tier_label in [('tier_1', 'Tier 1'), ('tier_2', 'Tier 2'), ('tier_3', 'Tier 3')]:
            tier_counts[tier_label] = qs.filter(
                tier__in=[tier_val, tier_val.replace('tier_', '')]
            ).count()

        # ── Credits ─────────────────────────────────────────────────────────
        credit_agg = completed_qs.exclude(credit_value__isnull=True).aggregate(
            total=Sum(F('credit_value'), output_field=FloatField()),
            avg=Avg(F('credit_value'), output_field=FloatField()),
        )
        total_credits = round(float(credit_agg['total'] or 0), 2)
        avg_credits = round(float(credit_agg['avg'] or 0), 2)

        # ── Weekly velocity (completed cases per week) ───────────────────────
        weekly_velocity = list(
            completed_qs.filter(date_completed__isnull=False)
            .annotate(week=TruncWeek('date_completed'))
            .values('week')
            .annotate(count=Count('id'))
            .order_by('week')
        )

        # ── Review activity from AuditLog ────────────────────────────────────
        from core.models import AuditLog
        review_sent = AuditLog.objects.filter(
            user=tech,
            action_type='case_submitted_for_review',
        )
        review_approved = AuditLog.objects.filter(
            user=tech,
            action_type='case_review_approved',
        )
        if date_from:
            review_sent = review_sent.filter(timestamp__date__gte=date_from)
            review_approved = review_approved.filter(timestamp__date__gte=date_from)
        if date_to:
            review_sent = review_sent.filter(timestamp__date__lte=date_to)
            review_approved = review_approved.filter(timestamp__date__lte=date_to)

        results.append({
            'tech': tech,
            'total_accepted': total_accepted,
            'completed_count': completed_count,
            'completion_rate': completion_rate,
            'in_progress_count': in_progress_count,
            'on_hold_count': on_hold_count,
            'pending_review_count': pending_review_count,
            'rush_count': rush_count,
            'error_count': error_count,
            'avg_days': avg_days,
            'fastest_days': fastest_days,
            'slowest_days': slowest_days,
            'on_time_count': on_time_count,
            'on_time_rate': on_time_rate,
            'tier_counts': tier_counts,
            'total_credits': total_credits,
            'avg_credits': avg_credits,
            'weekly_velocity': weekly_velocity,
            'reviews_sent': review_sent.count(),
            'reviews_approved': review_approved.count(),
        })

    return results


@login_required
def technician_productivity_report(request):
    """Technician productivity report - Admin and Manager only"""
    if not is_admin(request.user):
        messages.error(request, 'Access denied. Administrators and Managers only.')
        return redirect('home')

    all_techs = _exclude_super_dev_users(
        User.objects.filter(role='technician')
    ).order_by('first_name', 'last_name')

    tech_id = request.GET.get('tech_id', '').strip()
    date_from_str = request.GET.get('date_from', '').strip()
    date_to_str = request.GET.get('date_to', '').strip()

    report_data = None
    selected_tech = None
    error_msg = None

    # Only run if the form was actually submitted (at least one param present)
    form_submitted = bool(tech_id or date_from_str or date_to_str)

    if form_submitted:
        from datetime import datetime
        try:
            date_from = datetime.strptime(date_from_str, '%Y-%m-%d').date() if date_from_str else None
            date_to = datetime.strptime(date_to_str, '%Y-%m-%d').date() if date_to_str else None
        except ValueError:
            date_from = date_to = None
            error_msg = 'Invalid date format. Please use YYYY-MM-DD.'

        if not error_msg:
            report_data = get_technician_productivity_data(
                tech_id=tech_id or 'all',
                date_from=date_from,
                date_to=date_to,
            )
            if tech_id and tech_id != 'all':
                try:
                    selected_tech = User.objects.get(id=int(tech_id), role='technician')
                except (User.DoesNotExist, ValueError):
                    pass

    # CSV export
    if form_submitted and not error_msg and report_data and request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv')
        filename = f"technician_productivity_{date_from_str or 'all'}_{date_to_str or 'all'}.csv"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        writer = csv.writer(response)
        writer.writerow([
            'Technician', 'Total Accepted', 'Completed', 'Completion Rate %',
            'On-Time Count', 'On-Time Rate %',
            'In Progress', 'On Hold', 'Pending Review', 'Rush Cases', 'Error Cases',
            'Avg Days', 'Fastest Days', 'Slowest Days',
            'Tier 1', 'Tier 2', 'Tier 3', 'Total Credits', 'Avg Credits',
            'Reviews Sent', 'Reviews Approved',
        ])
        for row in report_data:
            tech = row['tech']
            writer.writerow([
                f"{tech.first_name} {tech.last_name}",
                row['total_accepted'], row['completed_count'], row['completion_rate'],
                row['on_time_count'], row['on_time_rate'],
                row['in_progress_count'], row['on_hold_count'], row['pending_review_count'],
                row['rush_count'], row['error_count'],
                row['avg_days'] if row['avg_days'] is not None else '',
                row['fastest_days'] if row['fastest_days'] is not None else '',
                row['slowest_days'] if row['slowest_days'] is not None else '',
                row['tier_counts'].get('Tier 1', 0),
                row['tier_counts'].get('Tier 2', 0),
                row['tier_counts'].get('Tier 3', 0),
                row['total_credits'], row['avg_credits'],
                row['reviews_sent'], row['reviews_approved'],
            ])
        return response

    context = {
        'all_techs': all_techs,
        'tech_id': tech_id,
        'date_from': date_from_str,
        'date_to': date_to_str,
        'report_data': report_data,
        'selected_tech': selected_tech,
        'is_all_techs': not tech_id or tech_id == 'all',
        'form_submitted': form_submitted,
        'error_msg': error_msg,
        'generated_at': timezone.now(),
    }
    return render(request, 'core/technician_productivity_report.html', context)


@login_required
def technician_productivity_pdf(request):
    """Generate and download a technician productivity report as PDF."""
    if not is_admin(request.user):
        return HttpResponse('Access denied.', status=403)

    from datetime import datetime
    from weasyprint import HTML
    from io import BytesIO
    from django.template.loader import render_to_string

    tech_id = request.GET.get('tech_id', '').strip()
    date_from_str = request.GET.get('date_from', '').strip()
    date_to_str = request.GET.get('date_to', '').strip()

    try:
        date_from = datetime.strptime(date_from_str, '%Y-%m-%d').date() if date_from_str else None
        date_to = datetime.strptime(date_to_str, '%Y-%m-%d').date() if date_to_str else None
    except ValueError:
        return HttpResponse('Invalid date format.', status=400)

    report_data = get_technician_productivity_data(
        tech_id=tech_id or 'all',
        date_from=date_from,
        date_to=date_to,
    )

    selected_tech = None
    if tech_id and tech_id != 'all':
        try:
            selected_tech = User.objects.get(id=int(tech_id), role='technician')
        except (User.DoesNotExist, ValueError):
            pass

    period_label = ''
    if date_from and date_to:
        period_label = f"{date_from.strftime('%B %d, %Y')} – {date_to.strftime('%B %d, %Y')}"
    elif date_from:
        period_label = f"From {date_from.strftime('%B %d, %Y')}"
    elif date_to:
        period_label = f"Through {date_to.strftime('%B %d, %Y')}"
    else:
        period_label = 'All Time'

    context = {
        'report_data': report_data,
        'selected_tech': selected_tech,
        'is_all_techs': not tech_id or tech_id == 'all',
        'date_from': date_from_str,
        'date_to': date_to_str,
        'period_label': period_label,
        'generated_at': timezone.now(),
        'generated_by': request.user.get_full_name() or request.user.username,
        'pdf_mode': True,
    }

    html_string = render_to_string('core/technician_productivity_report_pdf.html', context)

    pdf_buffer = BytesIO()
    HTML(string=html_string, base_url=request.build_absolute_uri('/')).write_pdf(pdf_buffer)
    pdf_buffer.seek(0)

    tech_slug = selected_tech.get_full_name().replace(' ', '_') if selected_tech else 'All_Technicians'
    date_slug = timezone.now().strftime('%Y%m%d')
    filename = f'Productivity_Report_{tech_slug}_{date_slug}.pdf'

    response = HttpResponse(pdf_buffer.read(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


# ---------------------------------------------------------------------------
# R1 — Pipeline Health Dashboard (live snapshot, no date range)
# ---------------------------------------------------------------------------

@login_required
def pipeline_health_report(request):
    """Live pipeline snapshot — admin/manager only."""
    if not is_admin(request.user):
        messages.error(request, 'Access denied. Administrators and Managers only.')
        return redirect('home')

    today = timezone.now().date()

    # ── Queue: submitted but not yet accepted ──────────────────────────────
    queue_qs = Case.objects.filter(status='submitted').order_by('date_submitted').select_related('assigned_to', 'member')
    queue_cases = []
    for c in queue_qs:
        queue_cases.append({
            'case': c,
            'hours_waiting': round((timezone.now() - c.date_submitted).total_seconds() / 3600, 1),
        })

    # ── Unassigned active cases ────────────────────────────────────────────
    unassigned_qs = Case.objects.filter(
        status__in=['submitted', 'accepted', 'pending_review', 'hold'],
        assigned_to__isnull=True,
    ).order_by('date_submitted').select_related('member')

    # ── Active by staff member (any role, active, has cases) ──────────────
    active_by_tech = []
    staff_qs = _exclude_super_dev_users(
        User.objects.filter(role__in=['technician', 'administrator', 'manager'], is_active=True)
    ).order_by('first_name', 'last_name')
    for person in staff_qs:
        active = Case.objects.filter(assigned_to=person, status__in=['accepted', 'pending_review']).count()
        on_hold = Case.objects.filter(assigned_to=person, status='hold').count()
        if active or on_hold:
            active_by_tech.append({
                'name': person.get_full_name() or person.username,
                'role': person.role,
                'level': person.user_level,
                'active': active,
                'on_hold': on_hold,
            })

    # ── Due in 3 and 7 days ───────────────────────────────────────────────
    active_statuses = ['accepted', 'pending_review', 'hold']
    due_3 = Case.objects.filter(
        status__in=active_statuses, date_due__isnull=False,
        date_due__lte=today + timedelta(days=3), date_due__gte=today,
    ).order_by('date_due').select_related('assigned_to')

    due_7 = Case.objects.filter(
        status__in=active_statuses, date_due__isnull=False,
        date_due__lte=today + timedelta(days=7), date_due__gt=today + timedelta(days=3),
    ).order_by('date_due').select_related('assigned_to')

    # ── Overdue ───────────────────────────────────────────────────────────
    overdue_qs = Case.objects.filter(
        status__in=['accepted', 'pending_review', 'hold', 'submitted'],
        date_due__isnull=False, date_due__lt=today,
    ).order_by('date_due').select_related('assigned_to')

    # ── On hold ───────────────────────────────────────────────────────────
    hold_cases = []
    for c in Case.objects.filter(status='hold').order_by('hold_start_date').select_related('assigned_to', 'member'):
        days_held = (timezone.now() - c.hold_start_date).days if c.hold_start_date else None
        hold_cases.append({'case': c, 'days_held': days_held})

    # ── Pending review ────────────────────────────────────────────────────
    pending_review_qs = Case.objects.filter(status='pending_review').order_by('date_submitted').select_related('assigned_to', 'reviewed_by')

    # ── Rush in flight ────────────────────────────────────────────────────
    rush_active = Case.objects.filter(
        status__in=['submitted', 'accepted', 'pending_review'], urgency='rush',
    ).order_by('date_due').select_related('assigned_to')

    total_active = Case.objects.filter(status__in=['submitted', 'accepted', 'pending_review', 'hold']).count()

    context = {
        'generated_at': timezone.now(),
        'today': today,
        'queue_cases': queue_cases,
        'queue_count': len(queue_cases),
        'unassigned_qs': unassigned_qs,
        'unassigned_count': unassigned_qs.count(),
        'active_by_tech': active_by_tech,
        'due_3': due_3,
        'due_3_count': due_3.count(),
        'due_7': due_7,
        'due_7_count': due_7.count(),
        'overdue_qs': overdue_qs,
        'overdue_count': overdue_qs.count(),
        'hold_cases': hold_cases,
        'hold_count': len(hold_cases),
        'pending_review_qs': pending_review_qs,
        'pending_review_count': pending_review_qs.count(),
        'rush_active': rush_active,
        'rush_active_count': rush_active.count(),
        'total_active': total_active,
    }
    return render(request, 'core/pipeline_health_report.html', context)


# ---------------------------------------------------------------------------
# R2 — Due Date Compliance Report
# ---------------------------------------------------------------------------

def _normalize_tier(tier_val):
    """Return display label regardless of legacy '1'/'2'/'3' or 'tier_1'/'tier_2'/'tier_3'."""
    mapping = {
        '1': 'Tier 1', 'tier_1': 'Tier 1',
        '2': 'Tier 2', 'tier_2': 'Tier 2',
        '3': 'Tier 3', 'tier_3': 'Tier 3',
    }
    return mapping.get(str(tier_val).lower(), str(tier_val).capitalize() if tier_val else 'Unknown')


def get_due_date_compliance_data(date_from=None, date_to=None):
    """
    Compile due-date compliance metrics for completed cases.
    date_from / date_to applied to date_completed.
    """
    from django.db.models.functions import TruncWeek

    qs = _exclude_test_account_cases(Case.objects.filter(
        status='completed',
        date_due__isnull=False,
        date_completed__isnull=False,
    ))

    if date_from:
        qs = qs.filter(date_completed__date__gte=date_from)
    if date_to:
        qs = qs.filter(date_completed__date__lte=date_to)

    total = qs.count()

    # on-time vs late
    on_time_qs = qs.filter(date_completed__date__lte=F('date_due'))
    late_qs = qs.filter(date_completed__date__gt=F('date_due'))
    on_time_count = on_time_qs.count()
    late_count = late_qs.count()
    on_time_rate = round(on_time_count / total * 100, 1) if total else 0

    # avg days early (on-time cases only) and avg days late (late cases only)
    early_diffs = []
    late_diffs = []
    for case in qs.only('id', 'date_due', 'date_completed'):
        if case.date_completed and case.date_due:
            completed_date = case.date_completed.date() if hasattr(case.date_completed, 'date') else case.date_completed
            diff = (case.date_due - completed_date).days
            if diff >= 0:
                early_diffs.append(diff)
            else:
                late_diffs.append(abs(diff))

    avg_days_early = round(sum(early_diffs) / len(early_diffs), 1) if early_diffs else 0
    avg_days_late = round(sum(late_diffs) / len(late_diffs), 1) if late_diffs else 0

    # by technician
    tech_stats = {}
    for case in qs.select_related('assigned_to'):
        tech = case.assigned_to
        name = tech.get_full_name() if tech else 'Unassigned'
        if name not in tech_stats:
            tech_stats[name] = {'total': 0, 'on_time': 0, 'late': 0}
        completed_date = case.date_completed.date() if hasattr(case.date_completed, 'date') else case.date_completed
        tech_stats[name]['total'] += 1
        if completed_date <= case.date_due:
            tech_stats[name]['on_time'] += 1
        else:
            tech_stats[name]['late'] += 1
    for v in tech_stats.values():
        v['rate'] = round(v['on_time'] / v['total'] * 100, 1) if v['total'] else 0
    by_tech = sorted(tech_stats.items(), key=lambda x: x[1]['total'], reverse=True)

    # by tier
    tier_stats = {}
    for case in qs:
        label = _normalize_tier(case.tier)
        if label not in tier_stats:
            tier_stats[label] = {'total': 0, 'on_time': 0, 'late': 0}
        completed_date = case.date_completed.date() if hasattr(case.date_completed, 'date') else case.date_completed
        tier_stats[label]['total'] += 1
        if completed_date <= case.date_due:
            tier_stats[label]['on_time'] += 1
        else:
            tier_stats[label]['late'] += 1
    for v in tier_stats.values():
        v['rate'] = round(v['on_time'] / v['total'] * 100, 1) if v['total'] else 0
    by_tier = sorted(tier_stats.items())

    # by urgency
    urgency_stats = {}
    for case in qs:
        label = (case.urgency or 'standard').capitalize()
        if label not in urgency_stats:
            urgency_stats[label] = {'total': 0, 'on_time': 0, 'late': 0}
        completed_date = case.date_completed.date() if hasattr(case.date_completed, 'date') else case.date_completed
        urgency_stats[label]['total'] += 1
        if completed_date <= case.date_due:
            urgency_stats[label]['on_time'] += 1
        else:
            urgency_stats[label]['late'] += 1
    for v in urgency_stats.values():
        v['rate'] = round(v['on_time'] / v['total'] * 100, 1) if v['total'] else 0
    by_urgency = sorted(urgency_stats.items())

    # weekly trend (last 16 weeks)
    weekly_qs = qs.filter(date_completed__isnull=False).annotate(
        week=TruncWeek('date_completed')
    ).values('week').annotate(
        total=Count('id'),
        on_time=Count('id', filter=Q(date_completed__date__lte=F('date_due'))),
    ).order_by('week')

    weekly_trend = []
    for row in weekly_qs:
        rate = round(row['on_time'] / row['total'] * 100, 1) if row['total'] else 0
        weekly_trend.append({
            'week': row['week'],
            'total': row['total'],
            'on_time': row['on_time'],
            'rate': rate,
        })

    # late case detail
    late_cases = late_qs.select_related('assigned_to', 'member').order_by('date_due')[:100]

    return {
        'total': total,
        'on_time_count': on_time_count,
        'late_count': late_count,
        'on_time_rate': on_time_rate,
        'avg_days_early': avg_days_early,
        'avg_days_late': avg_days_late,
        'by_tech': by_tech,
        'by_tier': by_tier,
        'by_urgency': by_urgency,
        'weekly_trend': weekly_trend,
        'late_cases': late_cases,
    }


@login_required
def due_date_compliance_report(request):
    """Due Date Compliance Report — admin/manager only."""
    if not is_admin(request.user):
        messages.error(request, 'Access denied. Administrators and Managers only.')
        return redirect('home')

    from datetime import datetime

    date_from_str = request.GET.get('date_from', '').strip()
    date_to_str = request.GET.get('date_to', '').strip()

    try:
        date_from = datetime.strptime(date_from_str, '%Y-%m-%d').date() if date_from_str else None
        date_to = datetime.strptime(date_to_str, '%Y-%m-%d').date() if date_to_str else None
    except ValueError:
        date_from = date_to = None

    data = get_due_date_compliance_data(date_from=date_from, date_to=date_to)

    # CSV export
    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv')
        filename = f"due_date_compliance_{date_from_str or 'all'}_{date_to_str or 'all'}.csv"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        writer = csv.writer(response)
        writer.writerow(['Due Date Compliance Report'])
        writer.writerow(['Period', f"{date_from_str or 'All time'} – {date_to_str or 'present'}"])
        writer.writerow(['On-Time Rate', f"{data['on_time_rate']}%"])
        writer.writerow(['Avg Days Early (on-time cases)', data['avg_days_early']])
        writer.writerow(['Avg Days Late (late cases)', data['avg_days_late']])
        writer.writerow([])
        writer.writerow(['Case ID', 'Client', 'Advisor', 'Technician', 'Tier', 'Urgency',
                         'Date Due', 'Date Completed', 'Days Diff', 'On Time'])
        for case in Case.objects.filter(
            status='completed', date_due__isnull=False, date_completed__isnull=False,
        ).select_related('assigned_to', 'member').order_by('date_completed'):
            completed_date = case.date_completed.date() if hasattr(case.date_completed, 'date') else case.date_completed
            days_diff = (case.date_due - completed_date).days
            writer.writerow([
                case.external_case_id,
                f"{case.employee_first_name} {case.employee_last_name}",
                case.member.get_full_name() if case.member else '',
                case.assigned_to.get_full_name() if case.assigned_to else '',
                _normalize_tier(case.tier),
                (case.urgency or '').capitalize(),
                case.date_due.strftime('%Y-%m-%d') if case.date_due else '',
                completed_date.strftime('%Y-%m-%d') if completed_date else '',
                days_diff,
                'Yes' if days_diff >= 0 else 'No',
            ])
        return response

    period_label = f"{date_from_str or 'All time'} – {date_to_str or 'present'}"
    context = {
        **data,
        'date_from': date_from_str,
        'date_to': date_to_str,
        'period_label': period_label,
        'generated_at': timezone.now(),
    }
    return render(request, 'core/due_date_compliance_report.html', context)


@login_required
def due_date_compliance_pdf(request):
    """PDF export for Due Date Compliance Report."""
    if not is_admin(request.user):
        return HttpResponse('Access denied.', status=403)

    from datetime import datetime
    from weasyprint import HTML
    from io import BytesIO
    from django.template.loader import render_to_string

    date_from_str = request.GET.get('date_from', '').strip()
    date_to_str = request.GET.get('date_to', '').strip()

    try:
        date_from = datetime.strptime(date_from_str, '%Y-%m-%d').date() if date_from_str else None
        date_to = datetime.strptime(date_to_str, '%Y-%m-%d').date() if date_to_str else None
    except ValueError:
        date_from = date_to = None

    data = get_due_date_compliance_data(date_from=date_from, date_to=date_to)
    period_label = f"{date_from_str or 'All time'} – {date_to_str or 'present'}"

    html_string = render_to_string('core/due_date_compliance_report_pdf.html', {
        **data,
        'date_from': date_from_str,
        'date_to': date_to_str,
        'period_label': period_label,
        'generated_at': timezone.now(),
        'generated_by': request.user.get_full_name() or request.user.username,
    })
    pdf_buffer = BytesIO()
    HTML(string=html_string, base_url=request.build_absolute_uri('/')).write_pdf(pdf_buffer)
    pdf_buffer.seek(0)
    response = HttpResponse(pdf_buffer.read(), content_type='application/pdf')
    filename = f"due_date_compliance_{date_from_str or 'all'}_{date_to_str or 'all'}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


# ---------------------------------------------------------------------------
# R3 — Quality Review Analytics Report
# ---------------------------------------------------------------------------

def get_quality_review_data(date_from=None, date_to=None):
    """Compile quality review outcome metrics from CaseReviewHistory."""
    from django.db.models.functions import TruncWeek
    from cases.models import CaseReviewHistory

    OUTCOME_ACTIONS = ('approved', 'revisions_requested', 'corrections_needed')

    qs = CaseReviewHistory.objects.filter(
        review_action__in=OUTCOME_ACTIONS,
    ).select_related('case', 'reviewed_by', 'original_technician')

    if date_from:
        qs = qs.filter(reviewed_at__date__gte=date_from)
    if date_to:
        qs = qs.filter(reviewed_at__date__lte=date_to)

    total = qs.count()
    approved = qs.filter(review_action='approved').count()
    revisions = qs.filter(review_action='revisions_requested').count()
    corrections = qs.filter(review_action='corrections_needed').count()
    approval_rate = round(approved / total * 100, 1) if total else 0

    # by reviewer (who reviewed)
    reviewer_stats = {}
    for r in qs:
        name = r.reviewed_by.get_full_name() if r.reviewed_by else 'Unknown'
        if name not in reviewer_stats:
            reviewer_stats[name] = {'total': 0, 'approved': 0, 'revisions': 0, 'corrections': 0}
        reviewer_stats[name]['total'] += 1
        if r.review_action == 'approved':
            reviewer_stats[name]['approved'] += 1
        elif r.review_action == 'revisions_requested':
            reviewer_stats[name]['revisions'] += 1
        else:
            reviewer_stats[name]['corrections'] += 1
    for v in reviewer_stats.values():
        v['rate'] = round(v['approved'] / v['total'] * 100, 1) if v['total'] else 0
    by_reviewer = sorted(reviewer_stats.items(), key=lambda x: x[1]['total'], reverse=True)

    # by original technician (whose work was reviewed)
    tech_stats = {}
    for r in qs:
        name = r.original_technician.get_full_name() if r.original_technician else 'Unknown'
        if name not in tech_stats:
            tech_stats[name] = {'total': 0, 'approved': 0, 'revisions': 0, 'corrections': 0}
        tech_stats[name]['total'] += 1
        if r.review_action == 'approved':
            tech_stats[name]['approved'] += 1
        elif r.review_action == 'revisions_requested':
            tech_stats[name]['revisions'] += 1
        else:
            tech_stats[name]['corrections'] += 1
    for v in tech_stats.values():
        v['rate'] = round(v['approved'] / v['total'] * 100, 1) if v['total'] else 0
    by_tech = sorted(tech_stats.items(), key=lambda x: x[1]['total'], reverse=True)

    # weekly trend
    weekly_qs = (
        CaseReviewHistory.objects.filter(review_action__in=OUTCOME_ACTIONS)
        .filter(**({'reviewed_at__date__gte': date_from} if date_from else {}))
        .filter(**({'reviewed_at__date__lte': date_to} if date_to else {}))
        .annotate(week=TruncWeek('reviewed_at'))
        .values('week')
        .annotate(
            total=Count('id'),
            approved=Count('id', filter=Q(review_action='approved')),
        )
        .order_by('week')
    )
    weekly_trend = []
    for row in weekly_qs:
        rate = round(row['approved'] / row['total'] * 100, 1) if row['total'] else 0
        weekly_trend.append({'week': row['week'], 'total': row['total'],
                              'approved': row['approved'], 'rate': rate})

    # recent reviews detail
    recent_reviews = qs.order_by('-reviewed_at')[:100]

    # Avg review turnaround: time from submitted_for_review → outcome decision
    from django.db.models import Min as _Min
    submitted_map = {
        r['case_id']: r['sub_at']
        for r in CaseReviewHistory.objects.filter(review_action='submitted_for_review')
        .values('case_id').annotate(sub_at=_Min('reviewed_at'))
    }
    outcome_map = {
        r['case_id']: r['out_at']
        for r in CaseReviewHistory.objects.filter(review_action__in=OUTCOME_ACTIONS)
        .values('case_id').annotate(out_at=_Min('reviewed_at'))
    }
    turnaround_hours = []
    for case_id, sub_at in submitted_map.items():
        out_at = outcome_map.get(case_id)
        if out_at and out_at >= sub_at:
            turnaround_hours.append((out_at - sub_at).total_seconds() / 3600)
    avg_review_turnaround = round(sum(turnaround_hours) / len(turnaround_hours) / 24, 1) if turnaround_hours else None

    return {
        'total': total,
        'approved': approved,
        'revisions': revisions,
        'corrections': corrections,
        'approval_rate': approval_rate,
        'by_reviewer': by_reviewer,
        'by_tech': by_tech,
        'weekly_trend': weekly_trend,
        'recent_reviews': recent_reviews,
        'avg_review_turnaround': avg_review_turnaround,
    }


@login_required
def quality_review_analytics_report(request):
    """Quality Review Analytics — admin/manager only."""
    if not is_admin(request.user):
        messages.error(request, 'Access denied. Administrators and Managers only.')
        return redirect('home')

    from datetime import datetime
    from cases.models import CaseReviewHistory

    date_from_str = request.GET.get('date_from', '').strip()
    date_to_str = request.GET.get('date_to', '').strip()
    outcome_filter = request.GET.get('outcome', '').strip()

    try:
        date_from = datetime.strptime(date_from_str, '%Y-%m-%d').date() if date_from_str else None
        date_to = datetime.strptime(date_to_str, '%Y-%m-%d').date() if date_to_str else None
    except ValueError:
        date_from = date_to = None

    data = get_quality_review_data(date_from=date_from, date_to=date_to)

    # CSV export
    if request.GET.get('export') == 'csv':
        OUTCOME_ACTIONS = ('approved', 'revisions_requested', 'corrections_needed')
        reviews = CaseReviewHistory.objects.filter(
            review_action__in=OUTCOME_ACTIONS,
        ).select_related('case', 'reviewed_by', 'original_technician').order_by('-reviewed_at')
        if date_from:
            reviews = reviews.filter(reviewed_at__date__gte=date_from)
        if date_to:
            reviews = reviews.filter(reviewed_at__date__lte=date_to)
        if outcome_filter:
            reviews = reviews.filter(review_action=outcome_filter)
        response = HttpResponse(content_type='text/csv')
        filename = f"quality_review_analytics_{date_from_str or 'all'}_{date_to_str or 'all'}.csv"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        writer = csv.writer(response)
        writer.writerow(['Quality Review Analytics Report'])
        writer.writerow(['Period', f"{date_from_str or 'All time'} – {date_to_str or 'present'}"])
        writer.writerow(['First-Pass Approval Rate', f"{data['approval_rate']}%"])
        writer.writerow(['Avg Review Turnaround (days)', data['avg_review_turnaround'] if data['avg_review_turnaround'] is not None else 'N/A'])
        writer.writerow([])
        writer.writerow(['Reviewed At', 'Case ID', 'Outcome', 'Reviewed By',
                         'Original Technician', 'Notes'])
        for r in reviews:
            writer.writerow([
                r.reviewed_at.strftime('%Y-%m-%d %H:%M') if r.reviewed_at else '',
                r.case.external_case_id if r.case else '',
                r.get_review_action_display(),
                r.reviewed_by.get_full_name() if r.reviewed_by else '',
                r.original_technician.get_full_name() if r.original_technician else '',
                r.review_notes or '',
            ])
        return response

    period_label = f"{date_from_str or 'All time'} – {date_to_str or 'present'}"
    context = {
        **data,
        'date_from': date_from_str,
        'date_to': date_to_str,
        'outcome_filter': outcome_filter,
        'period_label': period_label,
        'generated_at': timezone.now(),
    }
    return render(request, 'core/quality_review_analytics_report.html', context)


@login_required
def quality_review_analytics_pdf(request):
    """PDF export for Quality Review Analytics."""
    if not is_admin(request.user):
        return HttpResponse('Access denied.', status=403)

    from datetime import datetime
    from weasyprint import HTML
    from io import BytesIO
    from django.template.loader import render_to_string

    date_from_str = request.GET.get('date_from', '').strip()
    date_to_str = request.GET.get('date_to', '').strip()

    try:
        date_from = datetime.strptime(date_from_str, '%Y-%m-%d').date() if date_from_str else None
        date_to = datetime.strptime(date_to_str, '%Y-%m-%d').date() if date_to_str else None
    except ValueError:
        date_from = date_to = None

    data = get_quality_review_data(date_from=date_from, date_to=date_to)
    period_label = f"{date_from_str or 'All time'} – {date_to_str or 'present'}"

    html_string = render_to_string('core/quality_review_analytics_report_pdf.html', {
        **data,
        'date_from': date_from_str,
        'date_to': date_to_str,
        'period_label': period_label,
        'generated_at': timezone.now(),
        'generated_by': request.user.get_full_name() or request.user.username,
    })
    pdf_buffer = BytesIO()
    HTML(string=html_string, base_url=request.build_absolute_uri('/')).write_pdf(pdf_buffer)
    pdf_buffer.seek(0)
    response = HttpResponse(pdf_buffer.read(), content_type='application/pdf')
    filename = f"quality_review_analytics_{date_from_str or 'all'}_{date_to_str or 'all'}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


# ---------------------------------------------------------------------------
# R4 — Member / Advisor Activity Report
# ---------------------------------------------------------------------------

def get_member_activity_data(date_from=None, date_to=None):
    """Compile per-advisor submission activity."""
    from django.db.models.functions import TruncWeek

    # All active members
    all_members = User.objects.filter(role='member', is_active=True).order_by('first_name', 'last_name')
    total_members = all_members.count()

    # Case queryset scoped to date range
    super_dev_email = _get_super_dev_email()
    case_qs = Case.objects.filter(member__isnull=False).select_related('member')
    if super_dev_email:
        case_qs = case_qs.exclude(member__email__iexact=super_dev_email)
    if date_from:
        case_qs = case_qs.filter(date_submitted__date__gte=date_from)
    if date_to:
        case_qs = case_qs.filter(date_submitted__date__lte=date_to)

    # Per-member stats
    member_counts = (
        case_qs.values('member__id', 'member__first_name', 'member__last_name',
                       'member__workshop_code', 'member__email')
        .annotate(
            case_count=Count('id'),
            rush_count=Count('id', filter=Q(urgency='rush')),
            multi_report_count=Count('id', filter=Q(num_reports_requested__gte=2)),
            last_submitted=Max('date_submitted'),
        )
        .order_by('-case_count')
    )

    # Members who submitted at least once
    active_submitter_ids = set(case_qs.values_list('member__id', flat=True).distinct())
    never_submitted_count = total_members - len(active_submitter_ids)

    # Workshop code breakdown (top 15)
    workshop_counts = (
        case_qs.exclude(member__workshop_code='')
        .exclude(member__workshop_code__isnull=True)
        .values('member__workshop_code')
        .annotate(count=Count('id'))
        .order_by('-count')[:15]
    )

    # Submission distribution buckets
    buckets = {'1': 0, '2–5': 0, '6–10': 0, '11–20': 0, '21–50': 0, '51+': 0}
    for row in member_counts:
        c = row['case_count']
        if c == 1:
            buckets['1'] += 1
        elif c <= 5:
            buckets['2–5'] += 1
        elif c <= 10:
            buckets['6–10'] += 1
        elif c <= 20:
            buckets['11–20'] += 1
        elif c <= 50:
            buckets['21–50'] += 1
        else:
            buckets['51+'] += 1

    # Weekly unique submitters
    weekly_qs = (
        case_qs.annotate(week=TruncWeek('date_submitted'))
        .values('week')
        .annotate(
            total_cases=Count('id'),
            unique_submitters=Count('member__id', distinct=True),
        )
        .order_by('week')
    )

    # Inactive submitters: submitted before but not in the last 30 days
    ref_date = date_to if date_to else timezone.now().date()
    cutoff_date = ref_date - timedelta(days=30)
    member_counts_list = list(member_counts)
    inactive_submitters = []
    for row in member_counts_list:
        ls = row['last_submitted']
        if ls is None:
            continue
        ls_date = ls.date() if hasattr(ls, 'date') else ls
        if ls_date < cutoff_date:
            inactive_submitters.append(row)
    inactive_submitters.sort(key=lambda x: x['last_submitted'])

    return {
        'total_members': total_members,
        'never_submitted_count': never_submitted_count,
        'active_submitter_count': len(active_submitter_ids),
        'member_counts': member_counts_list,
        'inactive_submitters': inactive_submitters,
        'workshop_counts': list(workshop_counts),
        'buckets': buckets,
        'weekly_qs': list(weekly_qs),
        'total_cases_in_range': case_qs.count(),
    }


@login_required
def member_activity_report(request):
    """Member / Advisor Activity Report — admin/manager only."""
    if not is_admin(request.user):
        messages.error(request, 'Access denied. Administrators and Managers only.')
        return redirect('home')

    from datetime import datetime

    date_from_str = request.GET.get('date_from', '').strip()
    date_to_str = request.GET.get('date_to', '').strip()

    try:
        date_from = datetime.strptime(date_from_str, '%Y-%m-%d').date() if date_from_str else None
        date_to = datetime.strptime(date_to_str, '%Y-%m-%d').date() if date_to_str else None
    except ValueError:
        date_from = date_to = None

    data = get_member_activity_data(date_from=date_from, date_to=date_to)

    # CSV export
    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv')
        filename = f"member_activity_{date_from_str or 'all'}_{date_to_str or 'all'}.csv"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        writer = csv.writer(response)
        writer.writerow(['Advisor Name', 'Email', 'Workshop Code', 'Total Cases',
                         'Rush Cases', 'Multi-Report Cases', 'Last Submitted'])
        for row in data['member_counts']:
            writer.writerow([
                f"{row['member__first_name']} {row['member__last_name']}",
                row['member__email'] or '',
                row['member__workshop_code'] or '',
                row['case_count'],
                row['rush_count'],
                row.get('multi_report_count', 0),
                row['last_submitted'].strftime('%Y-%m-%d') if row['last_submitted'] else '',
            ])
        writer.writerow([])
        writer.writerow(['Inactive Submitters (30+ days dormant)'])
        writer.writerow(['Advisor Name', 'Workshop Code', 'Last Submitted'])
        for row in data.get('inactive_submitters', []):
            ls = row['last_submitted']
            ls_date = ls.date() if hasattr(ls, 'date') else ls
            writer.writerow([
                f"{row['member__first_name']} {row['member__last_name']}",
                row['member__workshop_code'] or '',
                ls_date.strftime('%Y-%m-%d') if ls_date else '',
            ])
        return response

    period_label = f"{date_from_str or 'All time'} – {date_to_str or 'present'}"
    context = {
        **data,
        'date_from': date_from_str,
        'date_to': date_to_str,
        'period_label': period_label,
        'generated_at': timezone.now(),
    }
    return render(request, 'core/member_activity_report.html', context)


@login_required
def member_activity_pdf(request):
    """PDF export for Member / Advisor Activity Report."""
    if not is_admin(request.user):
        return HttpResponse('Access denied.', status=403)

    from datetime import datetime
    from weasyprint import HTML
    from io import BytesIO
    from django.template.loader import render_to_string

    date_from_str = request.GET.get('date_from', '').strip()
    date_to_str = request.GET.get('date_to', '').strip()

    try:
        date_from = datetime.strptime(date_from_str, '%Y-%m-%d').date() if date_from_str else None
        date_to = datetime.strptime(date_to_str, '%Y-%m-%d').date() if date_to_str else None
    except ValueError:
        date_from = date_to = None

    data = get_member_activity_data(date_from=date_from, date_to=date_to)
    period_label = f"{date_from_str or 'All time'} – {date_to_str or 'present'}"

    html_string = render_to_string('core/member_activity_report_pdf.html', {
        **data,
        'date_from': date_from_str,
        'date_to': date_to_str,
        'period_label': period_label,
        'generated_at': timezone.now(),
        'generated_by': request.user.get_full_name() or request.user.username,
    })
    pdf_buffer = BytesIO()
    HTML(string=html_string, base_url=request.build_absolute_uri('/')).write_pdf(pdf_buffer)
    pdf_buffer.seek(0)
    response = HttpResponse(pdf_buffer.read(), content_type='application/pdf')
    filename = f"member_activity_{date_from_str or 'all'}_{date_to_str or 'all'}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


# ─── R5: Credit Distribution & Integrity ────────────────────────────────────

def get_credit_distribution_data(date_from=None, date_to=None):
    """Aggregate credit_value statistics across cases."""
    qs = Case.objects.all()
    if date_from:
        qs = qs.filter(date_submitted__date__gte=date_from)
    if date_to:
        qs = qs.filter(date_submitted__date__lte=date_to)

    total_cases = qs.count()
    unassigned_credit = qs.filter(credit_value__isnull=True).count()

    # Distribution by credit value
    credit_dist_raw = (
        qs.exclude(credit_value__isnull=True)
        .values('credit_value')
        .annotate(count=Count('id'))
        .order_by('credit_value')
    )
    credit_dist = list(credit_dist_raw)
    total_with_credit = sum(r['count'] for r in credit_dist)
    for r in credit_dist:
        r['pct'] = round(r['count'] / total_with_credit * 100, 1) if total_with_credit else 0
        r['credit_value'] = float(r['credit_value'])

    # Aggregate stats
    agg = qs.exclude(credit_value__isnull=True).aggregate(
        avg_credit=Avg('credit_value'),
        total_credit=Sum('credit_value'),
    )
    avg_credit_overall = round(float(agg['avg_credit'] or 0), 2)
    total_credit_sum = round(float(agg['total_credit'] or 0), 1)

    # By tier (normalize raw tier strings)
    tier_raw = (
        qs.exclude(credit_value__isnull=True)
        .values('tier')
        .annotate(count=Count('id'), total_credit=Sum('credit_value'))
    )
    tier_merged = {}
    for row in tier_raw:
        norm = _normalize_tier(row['tier'])
        if norm not in tier_merged:
            tier_merged[norm] = {'tier': norm, 'count': 0, 'total_credit': 0.0}
        tier_merged[norm]['count'] += row['count']
        tier_merged[norm]['total_credit'] += float(row['total_credit'] or 0)
    for v in tier_merged.values():
        v['avg_credit'] = round(v['total_credit'] / v['count'], 2) if v['count'] else 0.0
    tier_avg = sorted(tier_merged.values(), key=lambda x: x['tier'])

    # Zero-credit completed cases
    zero_credit_completed = qs.filter(status='completed', credit_value=0.0).count()
    zero_credit_null_completed = qs.filter(status='completed', credit_value__isnull=True).count()

    # High-credit cases (>= 2.0)
    high_credit_qs = (
        qs.filter(credit_value__gte=2.0)
        .values(
            'external_case_id', 'credit_value', 'tier', 'status',
            'assigned_to__first_name', 'assigned_to__last_name',
            'member__first_name', 'member__last_name', 'date_submitted',
        )
        .order_by('-credit_value', 'date_submitted')[:50]
    )
    high_credit_cases = []
    for r in high_credit_qs:
        r['tier_display'] = _normalize_tier(r['tier'])
        r['credit_value'] = float(r['credit_value'])
        high_credit_cases.append(r)

    # Monthly credit trend (completed/accepted cases)
    from django.db.models.functions import TruncMonth
    monthly_raw = (
        qs.filter(status__in=['accepted', 'completed'])
        .exclude(credit_value__isnull=True)
        .annotate(month=TruncMonth('date_submitted'))
        .values('month')
        .annotate(count=Count('id'), avg_credit=Avg('credit_value'), total_credits=Sum('credit_value'))
        .order_by('month')
    )
    credit_monthly_trend = []
    for r in monthly_raw:
        credit_monthly_trend.append({
            'month': r['month'],
            'count': r['count'],
            'avg_credit': round(float(r['avg_credit'] or 0), 2),
            'total_credits': round(float(r['total_credits'] or 0), 1),
        })

    return {
        'total_cases': total_cases,
        'total_with_credit': total_with_credit,
        'unassigned_credit': unassigned_credit,
        'avg_credit_overall': avg_credit_overall,
        'total_credit_sum': total_credit_sum,
        'credit_dist': credit_dist,
        'tier_avg': tier_avg,
        'zero_credit_completed': zero_credit_completed,
        'zero_credit_null_completed': zero_credit_null_completed,
        'high_credit_cases': high_credit_cases,
        'credit_monthly_trend': credit_monthly_trend,
    }


@login_required
def credit_distribution_report(request):
    """R5: Credit Distribution & Integrity — HTML + inline CSV."""
    if not is_admin(request.user):
        return HttpResponse('Access denied.', status=403)

    from datetime import datetime

    date_from_str = request.GET.get('date_from', '').strip()
    date_to_str = request.GET.get('date_to', '').strip()

    try:
        date_from = datetime.strptime(date_from_str, '%Y-%m-%d').date() if date_from_str else None
        date_to = datetime.strptime(date_to_str, '%Y-%m-%d').date() if date_to_str else None
    except ValueError:
        date_from = date_to = None

    data = get_credit_distribution_data(date_from=date_from, date_to=date_to)

    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv')
        fname = f"credit_distribution_{date_from_str or 'all'}_{date_to_str or 'all'}.csv"
        response['Content-Disposition'] = f'attachment; filename="{fname}"'
        writer = csv.writer(response)

        writer.writerow(['Credit Distribution Report'])
        writer.writerow(['Period', f"{date_from_str or 'All time'} – {date_to_str or 'present'}"])
        writer.writerow([])

        writer.writerow(['Summary'])
        writer.writerow(['Total Cases', data['total_cases']])
        writer.writerow(['Cases with Credit Assigned', data['total_with_credit']])
        writer.writerow(['Cases without Credit', data['unassigned_credit']])
        writer.writerow(['Average Credit', data['avg_credit_overall']])
        writer.writerow(['Total Credits Issued', data['total_credit_sum']])
        writer.writerow(['Zero-credit Completed Cases', data['zero_credit_completed']])
        writer.writerow([])

        writer.writerow(['Credit Value', 'Cases', 'Percentage'])
        for row in data['credit_dist']:
            writer.writerow([row['credit_value'], row['count'], f"{row['pct']}%"])
        writer.writerow([])

        writer.writerow(['Tier', 'Cases', 'Avg Credit', 'Total Credits'])
        for row in data['tier_avg']:
            writer.writerow([row['tier'], row['count'], row['avg_credit'], round(row['total_credit'], 1)])
        writer.writerow([])

        writer.writerow(['High-Credit Cases (2.0+)'])
        writer.writerow(['Case ID', 'Credit', 'Tier', 'Status', 'Technician', 'Advisor', 'Submitted'])
        for r in data['high_credit_cases']:
            writer.writerow([
                r['external_case_id'],
                r['credit_value'],
                r['tier_display'],
                r['status'],
                f"{r.get('assigned_to__first_name') or ''} {r.get('assigned_to__last_name') or ''}".strip(),
                f"{r.get('member__first_name') or ''} {r.get('member__last_name') or ''}".strip(),
                r['date_submitted'].strftime('%m/%d/%Y') if r['date_submitted'] else '',
            ])
        writer.writerow([])
        writer.writerow(['Monthly Credit Trend (Completed/Accepted)'])
        writer.writerow(['Month', 'Cases', 'Avg Credit', 'Total Credits'])
        for r in data.get('credit_monthly_trend', []):
            writer.writerow([
                r['month'].strftime('%Y-%m') if r['month'] else '',
                r['count'],
                r['avg_credit'],
                r['total_credits'],
            ])
        return response

    context = {
        **data,
        'date_from': date_from_str,
        'date_to': date_to_str,
    }
    return render(request, 'core/credit_distribution_report.html', context)


@login_required
def credit_distribution_pdf(request):
    """PDF export for Credit Distribution Report."""
    if not is_admin(request.user):
        return HttpResponse('Access denied.', status=403)

    from datetime import datetime
    from weasyprint import HTML
    from io import BytesIO
    from django.template.loader import render_to_string

    date_from_str = request.GET.get('date_from', '').strip()
    date_to_str = request.GET.get('date_to', '').strip()

    try:
        date_from = datetime.strptime(date_from_str, '%Y-%m-%d').date() if date_from_str else None
        date_to = datetime.strptime(date_to_str, '%Y-%m-%d').date() if date_to_str else None
    except ValueError:
        date_from = date_to = None

    data = get_credit_distribution_data(date_from=date_from, date_to=date_to)
    period_label = f"{date_from_str or 'All time'} – {date_to_str or 'present'}"

    html_string = render_to_string('core/credit_distribution_report_pdf.html', {
        **data,
        'period_label': period_label,
        'generated_at': timezone.now(),
        'generated_by': request.user.get_full_name() or request.user.username,
    })
    pdf_buffer = BytesIO()
    HTML(string=html_string, base_url=request.build_absolute_uri('/')).write_pdf(pdf_buffer)
    pdf_buffer.seek(0)
    response = HttpResponse(pdf_buffer.read(), content_type='application/pdf')
    fname = f"credit_distribution_{date_from_str or 'all'}_{date_to_str or 'all'}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{fname}"'
    return response


# ─── R6: Hold Analysis ──────────────────────────────────────────────────────

def get_hold_analysis_data(date_from=None, date_to=None):
    """Aggregate hold statistics across cases."""
    from core.models import AuditLog

    # Cases ever placed on hold (have a hold_start_date)
    qs = Case.objects.filter(hold_start_date__isnull=False)
    if date_from:
        qs = qs.filter(hold_start_date__date__gte=date_from)
    if date_to:
        qs = qs.filter(hold_start_date__date__lte=date_to)

    total_holds = qs.count()
    currently_on_hold = qs.filter(status='hold').count()
    resolved_holds = qs.filter(hold_end_date__isnull=False).count()

    # Duration stats (hold_duration_days is Decimal; cast to float for aggregation)
    dur_agg = qs.exclude(hold_duration_days__isnull=True).aggregate(
        avg_dur=Avg('hold_duration_days'),
        max_dur=Max('hold_duration_days'),
        total_dur=Sum('hold_duration_days'),
    )
    avg_duration = round(float(dur_agg['avg_dur'] or 0), 1)
    max_duration = round(float(dur_agg['max_dur'] or 0), 1)

    # Distribution by hold_reason (top reasons)
    reason_dist = (
        qs.exclude(hold_reason='')
        .exclude(hold_reason__isnull=True)
        .values('hold_reason')
        .annotate(count=Count('id'))
        .order_by('-count')[:15]
    )
    reason_list = list(reason_dist)
    reason_total = sum(r['count'] for r in reason_list)
    for r in reason_list:
        r['pct'] = round(r['count'] / reason_total * 100, 1) if reason_total else 0

    # Distribution by status_before_hold
    status_dist = (
        qs.exclude(status_before_hold='')
        .values('status_before_hold')
        .annotate(count=Count('id'))
        .order_by('-count')
    )
    status_list = list(status_dist)

    # Duration buckets
    buckets = {
        '< 1 day': qs.filter(hold_duration_days__lt=1).count(),
        '1–3 days': qs.filter(hold_duration_days__gte=1, hold_duration_days__lt=3).count(),
        '3–7 days': qs.filter(hold_duration_days__gte=3, hold_duration_days__lt=7).count(),
        '7–14 days': qs.filter(hold_duration_days__gte=7, hold_duration_days__lt=14).count(),
        '14–30 days': qs.filter(hold_duration_days__gte=14, hold_duration_days__lt=30).count(),
        '30+ days': qs.filter(hold_duration_days__gte=30).count(),
    }

    # Longest active/recent holds
    longest_holds_qs = (
        qs.select_related('assigned_to', 'member')
        .values(
            'external_case_id', 'status', 'hold_reason', 'hold_duration_days',
            'hold_start_date', 'hold_end_date', 'status_before_hold',
            'assigned_to__first_name', 'assigned_to__last_name',
            'member__first_name', 'member__last_name',
        )
        .order_by(F('hold_duration_days').desc(nulls_last=True))[:30]
    )
    longest_holds = []
    for r in longest_holds_qs:
        r['hold_duration_days'] = float(r['hold_duration_days'] or 0)
        longest_holds.append(r)

    # AuditLog events
    audit_held = AuditLog.objects.filter(action_type='case_held')
    audit_resumed = AuditLog.objects.filter(action_type='case_resumed')
    if date_from:
        audit_held = audit_held.filter(timestamp__date__gte=date_from)
        audit_resumed = audit_resumed.filter(timestamp__date__gte=date_from)
    if date_to:
        audit_held = audit_held.filter(timestamp__date__lte=date_to)
        audit_resumed = audit_resumed.filter(timestamp__date__lte=date_to)
    audit_held_count = audit_held.count()
    audit_resumed_count = audit_resumed.count()

    # Holds by technician
    holds_by_tech_qs = (
        qs.filter(assigned_to__isnull=False)
        .values('assigned_to__first_name', 'assigned_to__last_name')
        .annotate(hold_count=Count('id'))
        .order_by('-hold_count')
    )
    holds_by_tech = [
        {
            'name': f"{r['assigned_to__first_name'] or ''} {r['assigned_to__last_name'] or ''}".strip() or 'Unassigned',
            'count': r['hold_count'],
        }
        for r in holds_by_tech_qs
    ]

    return {
        'total_holds': total_holds,
        'currently_on_hold': currently_on_hold,
        'resolved_holds': resolved_holds,
        'avg_duration': avg_duration,
        'max_duration': max_duration,
        'reason_list': reason_list,
        'status_list': status_list,
        'buckets': buckets,
        'longest_holds': longest_holds,
        'audit_held_count': audit_held_count,
        'audit_resumed_count': audit_resumed_count,
        'holds_by_tech': holds_by_tech,
    }


@login_required
def hold_analysis_report(request):
    """R6: Hold Analysis — HTML + inline CSV."""
    if not is_admin(request.user):
        return HttpResponse('Access denied.', status=403)

    from datetime import datetime

    date_from_str = request.GET.get('date_from', '').strip()
    date_to_str = request.GET.get('date_to', '').strip()

    try:
        date_from = datetime.strptime(date_from_str, '%Y-%m-%d').date() if date_from_str else None
        date_to = datetime.strptime(date_to_str, '%Y-%m-%d').date() if date_to_str else None
    except ValueError:
        date_from = date_to = None

    data = get_hold_analysis_data(date_from=date_from, date_to=date_to)

    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv')
        fname = f"hold_analysis_{date_from_str or 'all'}_{date_to_str or 'all'}.csv"
        response['Content-Disposition'] = f'attachment; filename="{fname}"'
        writer = csv.writer(response)

        writer.writerow(['Hold Analysis Report'])
        writer.writerow(['Period', f"{date_from_str or 'All time'} – {date_to_str or 'present'}"])
        writer.writerow([])

        writer.writerow(['Summary'])
        writer.writerow(['Total Cases Held', data['total_holds']])
        writer.writerow(['Currently On Hold', data['currently_on_hold']])
        writer.writerow(['Resolved Holds', data['resolved_holds']])
        writer.writerow(['Average Duration (days)', data['avg_duration']])
        writer.writerow(['Max Duration (days)', data['max_duration']])
        writer.writerow(['Audit: case_held events', data['audit_held_count']])
        writer.writerow(['Audit: case_resumed events', data['audit_resumed_count']])
        writer.writerow([])

        writer.writerow(['Hold Reason', 'Cases', '%'])
        for r in data['reason_list']:
            writer.writerow([r['hold_reason'], r['count'], f"{r['pct']}%"])
        writer.writerow([])

        writer.writerow(['Duration Bucket', 'Cases'])
        for bucket, count in data['buckets'].items():
            writer.writerow([bucket, count])
        writer.writerow([])

        writer.writerow(['Longest Holds'])
        writer.writerow(['Case ID', 'Status', 'Duration (days)', 'Hold Start', 'Hold End', 'Reason', 'Technician'])
        for r in data['longest_holds']:
            writer.writerow([
                r['external_case_id'],
                r['status'],
                r['hold_duration_days'],
                r['hold_start_date'].strftime('%m/%d/%Y') if r['hold_start_date'] else '',
                r['hold_end_date'].strftime('%m/%d/%Y') if r['hold_end_date'] else 'Active',
                (r['hold_reason'] or '')[:80],
                f"{r.get('assigned_to__first_name') or ''} {r.get('assigned_to__last_name') or ''}".strip(),
            ])
        writer.writerow([])
        writer.writerow(['Holds by Technician'])
        writer.writerow(['Technician', 'Hold Count'])
        for r in data.get('holds_by_tech', []):
            writer.writerow([r['name'], r['count']])
        return response

    context = {
        **data,
        'date_from': date_from_str,
        'date_to': date_to_str,
    }
    return render(request, 'core/hold_analysis_report.html', context)


@login_required
def hold_analysis_pdf(request):
    """PDF export for Hold Analysis Report."""
    if not is_admin(request.user):
        return HttpResponse('Access denied.', status=403)

    from datetime import datetime
    from weasyprint import HTML
    from io import BytesIO
    from django.template.loader import render_to_string

    date_from_str = request.GET.get('date_from', '').strip()
    date_to_str = request.GET.get('date_to', '').strip()

    try:
        date_from = datetime.strptime(date_from_str, '%Y-%m-%d').date() if date_from_str else None
        date_to = datetime.strptime(date_to_str, '%Y-%m-%d').date() if date_to_str else None
    except ValueError:
        date_from = date_to = None

    data = get_hold_analysis_data(date_from=date_from, date_to=date_to)
    period_label = f"{date_from_str or 'All time'} – {date_to_str or 'present'}"

    html_string = render_to_string('core/hold_analysis_report_pdf.html', {
        **data,
        'period_label': period_label,
        'generated_at': timezone.now(),
        'generated_by': request.user.get_full_name() or request.user.username,
    })
    pdf_buffer = BytesIO()
    HTML(string=html_string, base_url=request.build_absolute_uri('/')).write_pdf(pdf_buffer)
    pdf_buffer.seek(0)
    response = HttpResponse(pdf_buffer.read(), content_type='application/pdf')
    fname = f"hold_analysis_{date_from_str or 'all'}_{date_to_str or 'all'}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{fname}"'
    return response


# ─── R7: Advisor Engagement Trend ───────────────────────────────────────────

def get_advisor_engagement_data(date_from=None, date_to=None):
    """Aggregate advisor engagement and submission trend data."""
    from django.db.models.functions import TruncWeek, TruncMonth
    from django.db.models import Min

    # All active members
    total_members = User.objects.filter(role='member', is_active=True).count()

    # Members who ever submitted (all-time, not filtered)
    ever_submitted_ids = set(
        Case.objects.values_list('member_id', flat=True).distinct()
    )
    ever_submitted = len(ever_submitted_ids)
    never_submitted = total_members - ever_submitted

    # Period-scoped base queryset
    qs = Case.objects.all()
    if date_from:
        qs = qs.filter(date_submitted__date__gte=date_from)
    if date_to:
        qs = qs.filter(date_submitted__date__lte=date_to)

    total_cases_period = qs.count()

    # Active in period (unique submitters)
    active_in_period_ids = set(qs.values_list('member_id', flat=True).distinct())
    active_in_period = len(active_in_period_ids)

    # Repeat submitters (2+ cases) within period
    repeat_qs = (
        qs.values('member_id')
        .annotate(cnt=Count('id'))
        .filter(cnt__gte=2)
    )
    repeat_submitters = repeat_qs.count()
    repeat_rate = round(repeat_submitters / active_in_period * 100, 1) if active_in_period else 0
    never_rate = round(never_submitted / total_members * 100, 1) if total_members else 0

    # New submitters in period = members whose very first-ever case is within period
    first_sub_per_member = (
        Case.objects.values('member_id')
        .annotate(first_date=Min('date_submitted'))
    )
    new_submitter_ids = set()
    for row in first_sub_per_member:
        fd = row['first_date']
        if fd is None:
            continue
        fd_date = fd.date() if hasattr(fd, 'date') else fd
        if date_from and fd_date < date_from:
            continue
        if date_to and fd_date > date_to:
            continue
        new_submitter_ids.add(row['member_id'])
    new_submitters = len(new_submitter_ids)

    # Weekly trend (last 26 weeks if no filter)
    weekly_qs = (
        qs.annotate(week=TruncWeek('date_submitted'))
        .values('week')
        .annotate(total_cases=Count('id'), unique_submitters=Count('member_id', distinct=True))
        .order_by('week')
    )
    weekly_trend = list(weekly_qs)

    # Monthly trend
    monthly_qs = (
        qs.annotate(month=TruncMonth('date_submitted'))
        .values('month')
        .annotate(total_cases=Count('id'), unique_submitters=Count('member_id', distinct=True))
        .order_by('month')
    )
    monthly_trend = list(monthly_qs)

    # Top 15 most active advisors in period
    top_advisors = (
        qs.values(
            'member_id',
            'member__first_name',
            'member__last_name',
            'member__workshop_code',
        )
        .annotate(case_count=Count('id'))
        .order_by('-case_count')[:15]
    )
    top_advisors_list = list(top_advisors)

    # Submission frequency buckets (in period)
    freq_qs = (
        qs.values('member_id')
        .annotate(cnt=Count('id'))
    )
    freq_buckets = {'1 case': 0, '2–5 cases': 0, '6–10 cases': 0, '11–20 cases': 0, '21+ cases': 0}
    for row in freq_qs:
        c = row['cnt']
        if c == 1:
            freq_buckets['1 case'] += 1
        elif c <= 5:
            freq_buckets['2–5 cases'] += 1
        elif c <= 10:
            freq_buckets['6–10 cases'] += 1
        elif c <= 20:
            freq_buckets['11–20 cases'] += 1
        else:
            freq_buckets['21+ cases'] += 1

    # 30-day dormancy list: submitted at some point but not in the last 30 days
    ref_date = date_to if date_to else timezone.now().date()
    dormancy_cutoff = ref_date - timedelta(days=30)
    all_last_sub = (
        Case.objects.filter(member__isnull=False)
        .values('member__first_name', 'member__last_name', 'member__workshop_code')
        .annotate(last_submitted=Max('date_submitted'))
    )
    dormant_list = []
    for row in all_last_sub:
        ls = row['last_submitted']
        if ls is None:
            continue
        ls_date = ls.date() if hasattr(ls, 'date') else ls
        if ls_date < dormancy_cutoff:
            dormant_list.append({
                'name': f"{row['member__first_name'] or ''} {row['member__last_name'] or ''}".strip() or '—',
                'workshop': row['member__workshop_code'] or '—',
                'last_submitted': ls_date,
                'days_dormant': (ref_date - ls_date).days,
            })
    dormant_list.sort(key=lambda x: x['last_submitted'])

    return {
        'total_members': total_members,
        'ever_submitted': ever_submitted,
        'never_submitted': never_submitted,
        'never_rate': never_rate,
        'active_in_period': active_in_period,
        'new_submitters': new_submitters,
        'repeat_submitters': repeat_submitters,
        'repeat_rate': repeat_rate,
        'total_cases_period': total_cases_period,
        'weekly_trend': weekly_trend,
        'monthly_trend': monthly_trend,
        'top_advisors': top_advisors_list,
        'freq_buckets': freq_buckets,
        'dormant_list': dormant_list,
    }


@login_required
def advisor_engagement_report(request):
    """R7: Advisor Engagement Trend — HTML + inline CSV."""
    if not is_admin(request.user):
        return HttpResponse('Access denied.', status=403)

    from datetime import datetime

    date_from_str = request.GET.get('date_from', '').strip()
    date_to_str = request.GET.get('date_to', '').strip()

    try:
        date_from = datetime.strptime(date_from_str, '%Y-%m-%d').date() if date_from_str else None
        date_to = datetime.strptime(date_to_str, '%Y-%m-%d').date() if date_to_str else None
    except ValueError:
        date_from = date_to = None

    data = get_advisor_engagement_data(date_from=date_from, date_to=date_to)

    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv')
        fname = f"advisor_engagement_{date_from_str or 'all'}_{date_to_str or 'all'}.csv"
        response['Content-Disposition'] = f'attachment; filename="{fname}"'
        writer = csv.writer(response)

        writer.writerow(['Advisor Engagement Trend Report'])
        writer.writerow(['Period', f"{date_from_str or 'All time'} – {date_to_str or 'present'}"])
        writer.writerow([])

        writer.writerow(['Summary'])
        writer.writerow(['Total Active Members', data['total_members']])
        writer.writerow(['Ever Submitted (all-time)', data['ever_submitted']])
        writer.writerow(['Never Submitted', data['never_submitted']])
        writer.writerow(['Never-Submitted Rate', f"{data['never_rate']}%"])
        writer.writerow(['Active in Period', data['active_in_period']])
        writer.writerow(['New Submitters in Period', data['new_submitters']])
        writer.writerow(['Repeat Submitters in Period', data['repeat_submitters']])
        writer.writerow(['Repeat Rate', f"{data['repeat_rate']}%"])
        writer.writerow(['Total Cases in Period', data['total_cases_period']])
        writer.writerow([])

        writer.writerow(['Monthly Trend'])
        writer.writerow(['Month', 'Total Cases', 'Unique Submitters'])
        for row in data['monthly_trend']:
            writer.writerow([
                row['month'].strftime('%Y-%m') if row['month'] else '',
                row['total_cases'],
                row['unique_submitters'],
            ])
        writer.writerow([])

        writer.writerow(['Weekly Trend'])
        writer.writerow(['Week of', 'Total Cases', 'Unique Submitters'])
        for row in data['weekly_trend']:
            writer.writerow([
                row['week'].strftime('%Y-%m-%d') if row['week'] else '',
                row['total_cases'],
                row['unique_submitters'],
            ])
        writer.writerow([])

        writer.writerow(['Top Advisors in Period'])
        writer.writerow(['Advisor', 'Workshop', 'Cases'])
        for r in data['top_advisors']:
            writer.writerow([
                f"{r.get('member__first_name') or ''} {r.get('member__last_name') or ''}".strip(),
                r.get('member__workshop_code') or '',
                r['case_count'],
            ])
        writer.writerow([])
        writer.writerow(['30-Day Dormancy List'])
        writer.writerow(['Advisor', 'Workshop', 'Last Submitted', 'Days Dormant'])
        for r in data.get('dormant_list', []):
            writer.writerow([
                r['name'],
                r['workshop'],
                r['last_submitted'].strftime('%Y-%m-%d') if r['last_submitted'] else '',
                r['days_dormant'],
            ])
        return response

    context = {
        **data,
        'date_from': date_from_str,
        'date_to': date_to_str,
    }
    return render(request, 'core/advisor_engagement_report.html', context)


@login_required
def advisor_engagement_pdf(request):
    """PDF export for Advisor Engagement Trend Report."""
    if not is_admin(request.user):
        return HttpResponse('Access denied.', status=403)

    from datetime import datetime
    from weasyprint import HTML
    from io import BytesIO
    from django.template.loader import render_to_string

    date_from_str = request.GET.get('date_from', '').strip()
    date_to_str = request.GET.get('date_to', '').strip()

    try:
        date_from = datetime.strptime(date_from_str, '%Y-%m-%d').date() if date_from_str else None
        date_to = datetime.strptime(date_to_str, '%Y-%m-%d').date() if date_to_str else None
    except ValueError:
        date_from = date_to = None

    data = get_advisor_engagement_data(date_from=date_from, date_to=date_to)
    period_label = f"{date_from_str or 'All time'} – {date_to_str or 'present'}"

    html_string = render_to_string('core/advisor_engagement_report_pdf.html', {
        **data,
        'period_label': period_label,
        'generated_at': timezone.now(),
        'generated_by': request.user.get_full_name() or request.user.username,
    })
    pdf_buffer = BytesIO()
    HTML(string=html_string, base_url=request.build_absolute_uri('/')).write_pdf(pdf_buffer)
    pdf_buffer.seek(0)
    response = HttpResponse(pdf_buffer.read(), content_type='application/pdf')
    fname = f"advisor_engagement_{date_from_str or 'all'}_{date_to_str or 'all'}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{fname}"'
    return response


# ─── R8: System Health & Ops ────────────────────────────────────────────────

def get_system_health_data(date_from=None, date_to=None):
    """Aggregate system health metrics from AuditLog and Case fields."""
    from core.models import AuditLog
    from cases.models import CaseDocument

    def _audit_count(action_type):
        qs = AuditLog.objects.filter(action_type=action_type)
        if date_from:
            qs = qs.filter(timestamp__date__gte=date_from)
        if date_to:
            qs = qs.filter(timestamp__date__lte=date_to)
        return qs.count()

    # SSO metrics
    sso_failures = _audit_count('sso_login_failed')
    sso_provisions = _audit_count('sso_auto_provision')
    sso_syncs = _audit_count('sso_sync')

    # Email metrics
    email_sent = _audit_count('email_notification_sent')
    email_failed = _audit_count('email_notification_failed')
    email_total = email_sent + email_failed
    email_failure_rate = round(email_failed / email_total * 100, 1) if email_total else 0

    # Cron jobs
    cron_executions = _audit_count('cron_job_executed')

    # Logins
    total_logins = _audit_count('login')

    # API sync status (all-time, not filtered by date)
    api_pending = Case.objects.filter(api_sync_status='pending').count()
    api_synced = Case.objects.filter(api_sync_status='synced').count()
    api_failed = Case.objects.filter(api_sync_status='failed').count()
    api_total = api_pending + api_synced + api_failed

    # PDF generation status
    pdf_pending = Case.objects.filter(fact_finder_pdf_status='pending').count()
    pdf_completed = Case.objects.filter(fact_finder_pdf_status='completed').count()
    pdf_failed = Case.objects.filter(fact_finder_pdf_status='failed').count()

    # Zero-document cases (non-cancelled, non-draft)
    zero_doc_cases = (
        Case.objects.exclude(status__in=['cancelled', 'draft'])
        .annotate(doc_count=Count('documents'))
        .filter(doc_count=0)
        .count()
    )

    # ProFeds error-flagged cases
    profeds_errors = Case.objects.filter(has_profeds_error=True).count()

    # Recent SSO failures (last 20)
    sso_failure_log = (
        AuditLog.objects.filter(action_type='sso_login_failed')
        .order_by('-timestamp')
        .values('timestamp', 'description', 'user__email')[:20]
    )
    if date_from:
        sso_failure_log = (
            AuditLog.objects.filter(action_type='sso_login_failed', timestamp__date__gte=date_from)
            .order_by('-timestamp')
            .values('timestamp', 'description', 'user__email')[:20]
        )

    # Recent email failures (last 20)
    email_failure_log = (
        AuditLog.objects.filter(action_type='email_notification_failed')
        .order_by('-timestamp')
        .values('timestamp', 'description', 'user__email')[:20]
    )
    if date_from:
        email_failure_log = (
            AuditLog.objects.filter(action_type='email_notification_failed', timestamp__date__gte=date_from)
            .order_by('-timestamp')
            .values('timestamp', 'description', 'user__email')[:20]
        )

    # Recent cron executions (last 10)
    cron_log = (
        AuditLog.objects.filter(action_type='cron_job_executed')
        .order_by('-timestamp')
        .values('timestamp', 'description')[:10]
    )

    return {
        'sso_failures': sso_failures,
        'sso_provisions': sso_provisions,
        'sso_syncs': sso_syncs,
        'email_sent': email_sent,
        'email_failed': email_failed,
        'email_failure_rate': email_failure_rate,
        'cron_executions': cron_executions,
        'total_logins': total_logins,
        'api_pending': api_pending,
        'api_synced': api_synced,
        'api_failed': api_failed,
        'api_total': api_total,
        'pdf_pending': pdf_pending,
        'pdf_completed': pdf_completed,
        'pdf_failed': pdf_failed,
        'zero_doc_cases': zero_doc_cases,
        'profeds_errors': profeds_errors,
        'sso_failure_log': list(sso_failure_log),
        'email_failure_log': list(email_failure_log),
        'cron_log': list(cron_log),
    }


@login_required
def system_health_report(request):
    """R8: System Health & Ops — HTML + inline CSV."""
    if not is_admin(request.user):
        return HttpResponse('Access denied.', status=403)

    from datetime import datetime

    date_from_str = request.GET.get('date_from', '').strip()
    date_to_str = request.GET.get('date_to', '').strip()

    try:
        date_from = datetime.strptime(date_from_str, '%Y-%m-%d').date() if date_from_str else None
        date_to = datetime.strptime(date_to_str, '%Y-%m-%d').date() if date_to_str else None
    except ValueError:
        date_from = date_to = None

    data = get_system_health_data(date_from=date_from, date_to=date_to)

    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv')
        fname = f"system_health_{date_from_str or 'all'}_{date_to_str or 'all'}.csv"
        response['Content-Disposition'] = f'attachment; filename="{fname}"'
        writer = csv.writer(response)

        writer.writerow(['System Health & Ops Report'])
        writer.writerow(['Period', f"{date_from_str or 'All time'} – {date_to_str or 'present'}"])
        writer.writerow([])

        writer.writerow(['SSO'])
        writer.writerow(['SSO Login Failures', data['sso_failures']])
        writer.writerow(['SSO Auto-Provisions', data['sso_provisions']])
        writer.writerow(['SSO Profile Syncs', data['sso_syncs']])
        writer.writerow([])

        writer.writerow(['Email'])
        writer.writerow(['Emails Sent', data['email_sent']])
        writer.writerow(['Email Failures', data['email_failed']])
        writer.writerow(['Failure Rate', f"{data['email_failure_rate']}%"])
        writer.writerow([])

        writer.writerow(['Cases'])
        writer.writerow(['Zero-Document Cases', data['zero_doc_cases']])
        writer.writerow(['ProFeds Error-Flagged', data['profeds_errors']])
        writer.writerow([])

        writer.writerow(['API Sync Status'])
        writer.writerow(['Pending', data['api_pending']])
        writer.writerow(['Synced', data['api_synced']])
        writer.writerow(['Failed', data['api_failed']])
        writer.writerow([])

        writer.writerow(['PDF Generation Status'])
        writer.writerow(['Pending', data['pdf_pending']])
        writer.writerow(['Completed', data['pdf_completed']])
        writer.writerow(['Failed', data['pdf_failed']])
        writer.writerow([])

        writer.writerow(['Recent SSO Failures'])
        writer.writerow(['Timestamp', 'User', 'Description'])
        for r in data['sso_failure_log']:
            writer.writerow([
                r['timestamp'].strftime('%m/%d/%Y %H:%M') if r['timestamp'] else '',
                r.get('user__email') or '',
                r.get('description') or '',
            ])
        writer.writerow([])

        writer.writerow(['Recent Email Failures'])
        writer.writerow(['Timestamp', 'User', 'Description'])
        for r in data['email_failure_log']:
            writer.writerow([
                r['timestamp'].strftime('%m/%d/%Y %H:%M') if r['timestamp'] else '',
                r.get('user__email') or '',
                r.get('description') or '',
            ])
        return response

    context = {
        **data,
        'date_from': date_from_str,
        'date_to': date_to_str,
    }
    return render(request, 'core/system_health_report.html', context)


@login_required
def system_health_pdf(request):
    """PDF export for System Health & Ops Report."""
    if not is_admin(request.user):
        return HttpResponse('Access denied.', status=403)

    from datetime import datetime
    from weasyprint import HTML
    from io import BytesIO
    from django.template.loader import render_to_string

    date_from_str = request.GET.get('date_from', '').strip()
    date_to_str = request.GET.get('date_to', '').strip()

    try:
        date_from = datetime.strptime(date_from_str, '%Y-%m-%d').date() if date_from_str else None
        date_to = datetime.strptime(date_to_str, '%Y-%m-%d').date() if date_to_str else None
    except ValueError:
        date_from = date_to = None

    data = get_system_health_data(date_from=date_from, date_to=date_to)
    period_label = f"{date_from_str or 'All time'} – {date_to_str or 'present'}"

    html_string = render_to_string('core/system_health_report_pdf.html', {
        **data,
        'period_label': period_label,
        'generated_at': timezone.now(),
        'generated_by': request.user.get_full_name() or request.user.username,
    })
    pdf_buffer = BytesIO()
    HTML(string=html_string, base_url=request.build_absolute_uri('/')).write_pdf(pdf_buffer)
    pdf_buffer.seek(0)
    response = HttpResponse(pdf_buffer.read(), content_type='application/pdf')
    fname = f"system_health_{date_from_str or 'all'}_{date_to_str or 'all'}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{fname}"'
    return response


# ─── R9: Case Reassignment Analysis ─────────────────────────────────────────

def get_reassignment_data(date_from=None, date_to=None):
    """Parse reassignment_history JSON from Case records into analytics."""
    from core.models import AuditLog
    from datetime import datetime as dt

    cases_with_history = (
        Case.objects.exclude(reassignment_history=[])
        .select_related('member')
        .values(
            'external_case_id', 'status', 'tier',
            'member__first_name', 'member__last_name',
            'reassignment_history',
        )
    )

    all_events = []
    reason_counts = {}
    from_tech_counts = {}
    to_tech_counts = {}
    case_event_counts = {}

    for case in cases_with_history:
        history = case['reassignment_history']
        if not isinstance(history, list) or not history:
            continue
        case_counted = 0
        for entry in history:
            if not isinstance(entry, dict):
                continue
            # Date-range filter
            event_date_str = entry.get('date', '')
            event_date = None
            if event_date_str:
                try:
                    event_date = dt.fromisoformat(
                        event_date_str.replace('Z', '+00:00')
                    ).date()
                    if date_from and event_date < date_from:
                        continue
                    if date_to and event_date > date_to:
                        continue
                except (ValueError, TypeError):
                    pass

            reason = (entry.get('reason') or 'Manual reassignment').strip()
            from_tech = (entry.get('from_tech_name') or '—').strip()
            to_tech = (entry.get('to_tech_name') or '—').strip()

            all_events.append({
                'case_id': case['external_case_id'],
                'case_status': case['status'],
                'tier': _normalize_tier(case['tier']),
                'member': f"{case['member__first_name'] or ''} {case['member__last_name'] or ''}".strip() or '—',
                'from_tech': from_tech,
                'to_tech': to_tech,
                'reason': reason,
                'reassigned_by': (entry.get('reassigned_by') or '').strip(),
                'date': event_date_str,
                'date_sort': event_date.isoformat() if event_date else event_date_str,
            })
            reason_counts[reason] = reason_counts.get(reason, 0) + 1
            from_tech_counts[from_tech] = from_tech_counts.get(from_tech, 0) + 1
            to_tech_counts[to_tech] = to_tech_counts.get(to_tech, 0) + 1
            case_counted += 1

        if case_counted:
            case_event_counts[case['external_case_id']] = case_counted

    # Sort events newest first
    all_events.sort(key=lambda x: x['date_sort'], reverse=True)

    reason_list = sorted(reason_counts.items(), key=lambda x: x[1], reverse=True)
    from_tech_list = sorted(from_tech_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    to_tech_list = sorted(to_tech_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    most_reassigned = sorted(case_event_counts.items(), key=lambda x: x[1], reverse=True)[:10]

    # AuditLog cross-reference
    audit_qs = AuditLog.objects.filter(action_type='case_reassigned')
    if date_from:
        audit_qs = audit_qs.filter(timestamp__date__gte=date_from)
    if date_to:
        audit_qs = audit_qs.filter(timestamp__date__lte=date_to)
    audit_count = audit_qs.count()

    # Turnaround comparison: do reassigned cases take longer?
    reassigned_ids = list(case_event_counts.keys())
    avg_reassigned_turnaround = None
    avg_normal_turnaround = None
    turnaround_delta = None
    if reassigned_ids:
        r_agg = Case.objects.filter(
            external_case_id__in=reassigned_ids,
            status='completed',
            date_submitted__isnull=False,
            date_completed__isnull=False,
        ).annotate(days=F('date_completed') - F('date_submitted')).aggregate(avg=Avg('days'))
        n_agg = Case.objects.exclude(
            external_case_id__in=reassigned_ids,
        ).filter(
            status='completed',
            date_submitted__isnull=False,
            date_completed__isnull=False,
        ).annotate(days=F('date_completed') - F('date_submitted')).aggregate(avg=Avg('days'))
        if r_agg['avg']:
            avg_reassigned_turnaround = round(r_agg['avg'].days, 1)
        if n_agg['avg']:
            avg_normal_turnaround = round(n_agg['avg'].days, 1)
        if avg_reassigned_turnaround is not None and avg_normal_turnaround is not None:
            turnaround_delta = round(avg_reassigned_turnaround - avg_normal_turnaround, 1)

    return {
        'total_events': len(all_events),
        'unique_cases': len(case_event_counts),
        'audit_count': audit_count,
        'all_events': all_events[:100],
        'reason_list': reason_list,
        'from_tech_list': from_tech_list,
        'to_tech_list': to_tech_list,
        'most_reassigned': most_reassigned,
        'avg_reassigned_turnaround': avg_reassigned_turnaround,
        'avg_normal_turnaround': avg_normal_turnaround,
        'turnaround_delta': turnaround_delta,
    }


@login_required
def reassignment_analysis_report(request):
    """R9: Case Reassignment Analysis — HTML + inline CSV."""
    if not is_admin(request.user):
        return HttpResponse('Access denied.', status=403)

    from datetime import datetime

    date_from_str = request.GET.get('date_from', '').strip()
    date_to_str = request.GET.get('date_to', '').strip()

    try:
        date_from = datetime.strptime(date_from_str, '%Y-%m-%d').date() if date_from_str else None
        date_to = datetime.strptime(date_to_str, '%Y-%m-%d').date() if date_to_str else None
    except ValueError:
        date_from = date_to = None

    data = get_reassignment_data(date_from=date_from, date_to=date_to)

    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv')
        fname = f"reassignments_{date_from_str or 'all'}_{date_to_str or 'all'}.csv"
        response['Content-Disposition'] = f'attachment; filename="{fname}"'
        writer = csv.writer(response)

        writer.writerow(['Case Reassignment Analysis'])
        writer.writerow(['Period', f"{date_from_str or 'All time'} – {date_to_str or 'present'}"])
        writer.writerow([])

        writer.writerow(['Summary'])
        writer.writerow(['Total Reassignment Events', data['total_events']])
        writer.writerow(['Unique Cases Reassigned', data['unique_cases']])
        writer.writerow(['Audit Log Events (cross-ref)', data['audit_count']])
        writer.writerow(['Avg Turnaround — Reassigned Cases (days)', data['avg_reassigned_turnaround'] if data['avg_reassigned_turnaround'] is not None else 'N/A'])
        writer.writerow(['Avg Turnaround — Non-Reassigned Cases (days)', data['avg_normal_turnaround'] if data['avg_normal_turnaround'] is not None else 'N/A'])
        writer.writerow(['Turnaround Delta (reassigned − normal)', data['turnaround_delta'] if data['turnaround_delta'] is not None else 'N/A'])
        writer.writerow([])

        writer.writerow(['Reassignment Reasons'])
        writer.writerow(['Reason', 'Count'])
        for reason, count in data['reason_list']:
            writer.writerow([reason, count])
        writer.writerow([])

        writer.writerow(['Cases Most Often Reassigned'])
        writer.writerow(['Case ID', 'Reassignment Count'])
        for case_id, cnt in data['most_reassigned']:
            writer.writerow([case_id, cnt])
        writer.writerow([])

        writer.writerow(['All Reassignment Events'])
        writer.writerow(['Date', 'Case ID', 'Status', 'Tier', 'From Tech', 'To Tech', 'Reason', 'Reassigned By'])
        for ev in data['all_events']:
            writer.writerow([
                ev['date'][:10] if ev['date'] else '',
                ev['case_id'],
                ev['case_status'],
                ev['tier'],
                ev['from_tech'],
                ev['to_tech'],
                ev['reason'],
                ev['reassigned_by'],
            ])
        return response

    context = {
        **data,
        'date_from': date_from_str,
        'date_to': date_to_str,
    }
    return render(request, 'core/reassignment_analysis_report.html', context)


@login_required
def reassignment_analysis_pdf(request):
    """PDF export for Case Reassignment Analysis."""
    if not is_admin(request.user):
        return HttpResponse('Access denied.', status=403)

    from datetime import datetime
    from weasyprint import HTML
    from io import BytesIO
    from django.template.loader import render_to_string

    date_from_str = request.GET.get('date_from', '').strip()
    date_to_str = request.GET.get('date_to', '').strip()

    try:
        date_from = datetime.strptime(date_from_str, '%Y-%m-%d').date() if date_from_str else None
        date_to = datetime.strptime(date_to_str, '%Y-%m-%d').date() if date_to_str else None
    except ValueError:
        date_from = date_to = None

    data = get_reassignment_data(date_from=date_from, date_to=date_to)
    period_label = f"{date_from_str or 'All time'} – {date_to_str or 'present'}"

    html_string = render_to_string('core/reassignment_analysis_report_pdf.html', {
        **data,
        'period_label': period_label,
        'generated_at': timezone.now(),
        'generated_by': request.user.get_full_name() or request.user.username,
    })
    pdf_buffer = BytesIO()
    HTML(string=html_string, base_url=request.build_absolute_uri('/')).write_pdf(pdf_buffer)
    pdf_buffer.seek(0)
    response = HttpResponse(pdf_buffer.read(), content_type='application/pdf')
    fname = f"reassignments_{date_from_str or 'all'}_{date_to_str or 'all'}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{fname}"'
    return response


# ── Case Analytics Report ────────────────────────────────────────────────────

def _get_case_analytics_data(date_from=None, date_to=None):
    from datetime import datetime as dt
    cases_qs = _exclude_test_account_cases(Case.objects.all())
    if date_from:
        cases_qs = cases_qs.filter(date_submitted__date__gte=date_from)
    if date_to:
        cases_qs = cases_qs.filter(date_submitted__date__lte=date_to)

    total_cases = cases_qs.count()
    completed_cases = cases_qs.filter(status='completed').count()
    submitted_cases = cases_qs.filter(status='submitted').count()
    rush_cases = cases_qs.filter(urgency='rush').count()
    standard_cases = cases_qs.filter(urgency='normal').count()

    completed_rate = round(completed_cases / total_cases * 100, 1) if total_cases else 0

    completed_with_dates = cases_qs.filter(
        status='completed',
        date_submitted__isnull=False,
        date_completed__isnull=False,
    ).annotate(
        processing_days=F('date_completed') - F('date_submitted')
    ).aggregate(avg_days=Avg('processing_days'))
    avg_proc = completed_with_dates['avg_days']
    avg_processing_time = avg_proc.days if avg_proc else None

    cases_by_urgency = []
    for item in cases_qs.values('urgency').annotate(count=Count('id')).order_by('urgency'):
        pct = round(item['count'] / total_cases * 100, 1) if total_cases else 0
        cases_by_urgency.append({'urgency': item['urgency'], 'count': item['count'], 'pct': pct})

    return {
        'total_cases': total_cases,
        'completed_cases': completed_cases,
        'completed_rate': completed_rate,
        'submitted_cases': submitted_cases,
        'rush_cases': rush_cases,
        'standard_cases': standard_cases,
        'avg_processing_time': avg_processing_time,
        'cases_by_urgency': cases_by_urgency,
    }


@login_required
def case_analytics_report(request):
    if not is_admin(request.user):
        messages.error(request, 'Access denied. Administrators and Managers only.')
        return redirect('home')

    from datetime import datetime as dt
    date_from_str = request.GET.get('date_from', '').strip()
    date_to_str = request.GET.get('date_to', '').strip()

    try:
        date_from = dt.strptime(date_from_str, '%Y-%m-%d').date() if date_from_str else None
        date_to = dt.strptime(date_to_str, '%Y-%m-%d').date() if date_to_str else None
    except ValueError:
        date_from = date_to = None

    if request.GET.get('export') == 'csv':
        data = _get_case_analytics_data(date_from=date_from, date_to=date_to)
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="case_analytics_{date_from_str or "all"}_{date_to_str or "all"}.csv"'
        writer = csv.writer(response)
        writer.writerow(['Case Analytics Report'])
        writer.writerow(['Period', f"{date_from_str or 'All time'} to {date_to_str or 'present'}"])
        writer.writerow([])
        writer.writerow(['Summary'])
        writer.writerow(['Metric', 'Value'])
        writer.writerow(['Total Cases', data['total_cases']])
        writer.writerow(['Completed Cases', data['completed_cases']])
        writer.writerow(['Completion Rate %', data['completed_rate']])
        writer.writerow(['Submitted (in-progress)', data['submitted_cases']])
        writer.writerow(['Rush Cases', data['rush_cases']])
        writer.writerow(['Standard Cases', data['standard_cases']])
        writer.writerow(['Avg Processing Time (days)', data['avg_processing_time'] or 'N/A'])
        writer.writerow([])
        writer.writerow(['Cases by Urgency'])
        writer.writerow(['Urgency', 'Count', '%'])
        for row in data['cases_by_urgency']:
            writer.writerow([row['urgency'].capitalize(), row['count'], row['pct']])
        return response

    data = _get_case_analytics_data(date_from=date_from, date_to=date_to)
    return render(request, 'core/case_analytics_report.html', {
        **data,
        'date_from': date_from_str,
        'date_to': date_to_str,
        'now': timezone.now(),
    })


@login_required
def case_analytics_pdf(request):
    if not is_admin(request.user):
        return HttpResponse('Access denied.', status=403)

    from datetime import datetime as dt
    from weasyprint import HTML
    from io import BytesIO
    from django.template.loader import render_to_string

    date_from_str = request.GET.get('date_from', '').strip()
    date_to_str = request.GET.get('date_to', '').strip()

    try:
        date_from = dt.strptime(date_from_str, '%Y-%m-%d').date() if date_from_str else None
        date_to = dt.strptime(date_to_str, '%Y-%m-%d').date() if date_to_str else None
    except ValueError:
        date_from = date_to = None

    data = _get_case_analytics_data(date_from=date_from, date_to=date_to)
    html_string = render_to_string('core/case_analytics_report_pdf.html', {
        **data,
        'period_label': f"{date_from_str or 'All time'} – {date_to_str or 'present'}",
        'generated_at': timezone.now(),
        'generated_by': request.user.get_full_name() or request.user.username,
    })
    pdf_buffer = BytesIO()
    HTML(string=html_string, base_url=request.build_absolute_uri('/')).write_pdf(pdf_buffer)
    pdf_buffer.seek(0)
    response = HttpResponse(pdf_buffer.read(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="case_analytics_{date_from_str or "all"}_{date_to_str or "all"}.pdf"'
    return response


# ── Status Distribution Report ───────────────────────────────────────────────

def _get_status_distribution_data(date_from=None, date_to=None):
    cases_qs = _exclude_test_account_cases(Case.objects.all())
    if date_from:
        cases_qs = cases_qs.filter(date_submitted__date__gte=date_from)
    if date_to:
        cases_qs = cases_qs.filter(date_submitted__date__lte=date_to)

    total_cases = cases_qs.count()
    status_labels = {
        'draft': 'Draft',
        'submitted': 'Submitted',
        'accepted': 'Accepted',
        'hold': 'On Hold',
        'pending_review': 'Pending Review',
        'completed': 'Completed',
    }
    status_colors = {
        'draft': '#6c757d',
        'submitted': '#0d6efd',
        'accepted': '#0dcaf0',
        'hold': '#ffc107',
        'pending_review': '#fd7e14',
        'completed': '#198754',
    }

    cases_by_status = []
    for item in cases_qs.values('status').annotate(count=Count('id')).order_by('status'):
        pct = round(item['count'] / total_cases * 100, 1) if total_cases else 0
        cases_by_status.append({
            'status': item['status'],
            'label': status_labels.get(item['status'], item['status']),
            'count': item['count'],
            'percentage': pct,
            'color': status_colors.get(item['status'], '#6c757d'),
        })

    return {
        'total_cases': total_cases,
        'cases_by_status': cases_by_status,
    }


@login_required
def status_distribution_report(request):
    if not is_admin(request.user):
        messages.error(request, 'Access denied. Administrators and Managers only.')
        return redirect('home')

    from datetime import datetime as dt
    date_from_str = request.GET.get('date_from', '').strip()
    date_to_str = request.GET.get('date_to', '').strip()

    try:
        date_from = dt.strptime(date_from_str, '%Y-%m-%d').date() if date_from_str else None
        date_to = dt.strptime(date_to_str, '%Y-%m-%d').date() if date_to_str else None
    except ValueError:
        date_from = date_to = None

    if request.GET.get('export') == 'csv':
        data = _get_status_distribution_data(date_from=date_from, date_to=date_to)
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="status_distribution_{date_from_str or "all"}_{date_to_str or "all"}.csv"'
        writer = csv.writer(response)
        writer.writerow(['Status Distribution Report'])
        writer.writerow(['Period', f"{date_from_str or 'All time'} to {date_to_str or 'present'}"])
        writer.writerow(['Total Cases', data['total_cases']])
        writer.writerow([])
        writer.writerow(['Status', 'Count', '% of Total'])
        for row in data['cases_by_status']:
            writer.writerow([row['label'], row['count'], row['percentage']])
        return response

    data = _get_status_distribution_data(date_from=date_from, date_to=date_to)
    return render(request, 'core/status_distribution_report.html', {
        **data,
        'date_from': date_from_str,
        'date_to': date_to_str,
        'now': timezone.now(),
    })


@login_required
def status_distribution_pdf(request):
    if not is_admin(request.user):
        return HttpResponse('Access denied.', status=403)

    from datetime import datetime as dt
    from weasyprint import HTML
    from io import BytesIO
    from django.template.loader import render_to_string

    date_from_str = request.GET.get('date_from', '').strip()
    date_to_str = request.GET.get('date_to', '').strip()

    try:
        date_from = dt.strptime(date_from_str, '%Y-%m-%d').date() if date_from_str else None
        date_to = dt.strptime(date_to_str, '%Y-%m-%d').date() if date_to_str else None
    except ValueError:
        date_from = date_to = None

    data = _get_status_distribution_data(date_from=date_from, date_to=date_to)
    html_string = render_to_string('core/status_distribution_report_pdf.html', {
        **data,
        'period_label': f"{date_from_str or 'All time'} – {date_to_str or 'present'}",
        'generated_at': timezone.now(),
        'generated_by': request.user.get_full_name() or request.user.username,
    })
    pdf_buffer = BytesIO()
    HTML(string=html_string, base_url=request.build_absolute_uri('/')).write_pdf(pdf_buffer)
    pdf_buffer.seek(0)
    response = HttpResponse(pdf_buffer.read(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="status_distribution_{date_from_str or "all"}_{date_to_str or "all"}.pdf"'
    return response


# ── Team Performance Dashboard (Demo) ────────────────────────────────────────

def get_performance_metrics(date_from=None, date_to=None, tech_user=None):
    """
    Compute all 7 team performance metrics for the given date window.
    All case-based metrics filter on date_completed within the window.
    Errors filter on the mod case's date_submitted (when the error was reported).
    If tech_user is provided, all metrics are scoped to that technician only.
    """
    from cases.models import CaseReviewHistory

    date_from_obj = None
    date_to_obj = None
    if date_from:
        from datetime import datetime as _dt
        date_from_obj = _dt.strptime(date_from, '%Y-%m-%d').date()
    if date_to:
        from datetime import datetime as _dt
        date_to_obj = _dt.strptime(date_to, '%Y-%m-%d').date()

    # Base queryset: completed cases filtered by date_completed — exclude test account cases
    completed_qs = _exclude_test_account_cases(Case.objects.filter(status='completed'))
    if date_from_obj:
        completed_qs = completed_qs.filter(date_completed__date__gte=date_from_obj)
    if date_to_obj:
        completed_qs = completed_qs.filter(date_completed__date__lte=date_to_obj)
    if tech_user:
        completed_qs = completed_qs.filter(assigned_to=tech_user)

    # 1. Reports Generated
    reports_generated = completed_qs.count()

    # 2. Reports Submitted for Review (count events, not unique cases)
    review_qs = CaseReviewHistory.objects.filter(review_action='submitted_for_review')
    if date_from_obj:
        review_qs = review_qs.filter(reviewed_at__date__gte=date_from_obj)
    if date_to_obj:
        review_qs = review_qs.filter(reviewed_at__date__lte=date_to_obj)
    if tech_user:
        review_qs = review_qs.filter(original_technician=tech_user)
    submitted_for_review = review_qs.count()

    # 3. On-Time Delivery %
    completed_with_due = completed_qs.filter(date_due__isnull=False, date_completed__isnull=False)
    on_time_total = completed_with_due.count()
    on_time_count = completed_with_due.filter(date_completed__date__lte=F('date_due')).count()
    on_time_pct = round(on_time_count / on_time_total * 100, 1) if on_time_total > 0 else None

    # 4. Errors (mod cases flagged as ProFeds errors, filtered by mod case date_submitted)
    error_qs = _exclude_test_account_cases(Case.objects.filter(has_profeds_error=True, original_case__isnull=False))
    if date_from_obj:
        error_qs = error_qs.filter(date_submitted__date__gte=date_from_obj)
    if date_to_obj:
        error_qs = error_qs.filter(date_submitted__date__lte=date_to_obj)
    if tech_user:
        error_qs = error_qs.filter(assigned_to=tech_user)
    errors_count = error_qs.count()

    # 5. Production Cycle Time — avg days from member submission to tech finish
    cycle_qs = completed_qs.filter(date_submitted__isnull=False, date_completed__isnull=False)
    cycle_agg = cycle_qs.annotate(
        cycle=F('date_completed') - F('date_submitted')
    ).aggregate(avg=Avg('cycle'))
    avg_cycle_days = round(cycle_agg['avg'].total_seconds() / 86400, 1) if cycle_agg['avg'] else None

    # 6. Readiness Window — avg days BEFORE due date the tech finished (positive = early)
    readiness_qs = completed_qs.filter(date_due__isnull=False, date_completed__isnull=False)
    early_diffs = []
    for case in readiness_qs.only('date_due', 'date_completed'):
        completed_date = case.date_completed.date() if hasattr(case.date_completed, 'date') else case.date_completed
        early_diffs.append((case.date_due - completed_date).days)
    avg_readiness_days = round(sum(early_diffs) / len(early_diffs), 1) if early_diffs else None

    # 7. Report Accuracy — % of completed cases with no PF error flag
    total_completed = completed_qs.count()
    error_free = completed_qs.filter(has_profeds_error=False).count()
    accuracy_pct = round(error_free / total_completed * 100, 1) if total_completed > 0 else None

    return {
        'reports_generated': reports_generated,
        'submitted_for_review': submitted_for_review,
        'on_time_pct': on_time_pct,
        'on_time_count': on_time_count,
        'on_time_total': on_time_total,
        'errors_count': errors_count,
        'avg_cycle_days': avg_cycle_days,
        'avg_readiness_days': avg_readiness_days,
        'accuracy_pct': accuracy_pct,
        'accuracy_error_free': error_free,
        'accuracy_total': total_completed,
    }


@login_required
def performance_dashboard(request):
    """Team Performance Dashboard — demo, admin-only."""
    if not is_admin(request.user):
        messages.error(request, 'Access denied. Administrators only.')
        return redirect('home')

    date_to = request.GET.get('date_to', '').strip()
    date_from = request.GET.get('date_from', '').strip()

    # Default: last 7 days
    if not date_from and not date_to:
        date_to = timezone.now().date().strftime('%Y-%m-%d')
        date_from = (timezone.now().date() - timedelta(days=7)).strftime('%Y-%m-%d')

    metrics = get_performance_metrics(date_from or None, date_to or None)

    # Per-technician breakdown (Step 3) — merge performance + review accuracy + returns/corrections
    techs = _exclude_super_dev_users(
        User.objects.filter(role__in=['technician', 'administrator'], is_active=True)
    ).order_by('first_name', 'last_name')

    # Parse dates once for helpers
    from datetime import datetime as _dt2
    date_from_obj = _dt2.strptime(date_from, '%Y-%m-%d').date() if date_from else None
    date_to_obj   = _dt2.strptime(date_to,   '%Y-%m-%d').date() if date_to   else None

    review_acc_data   = _get_review_accuracy_by_tech(date_from_obj, date_to_obj)
    returns_corr_data = _get_returns_corrections_by_tech(date_from_obj, date_to_obj)
    advisor_data      = _get_advisor_submissions(date_from_obj, date_to_obj)

    per_tech = []
    for tech in techs:
        t = get_performance_metrics(date_from or None, date_to or None, tech_user=tech)
        t['tech'] = tech
        acc = review_acc_data['per_tech'].get(tech.id, {})
        t['review_accuracy_pct'] = acc.get('review_accuracy_pct')
        t['review_total']        = acc.get('total', 0)
        t['review_revisions']    = acc.get('revisions', 0)
        t['review_corrections']  = acc.get('corrections', 0)
        rc = returns_corr_data['per_tech'].get(tech.id, {})
        t['returned']         = rc.get('returned', 0)
        t['corrected_by_l3']  = rc.get('corrected_by_l3', 0)
        per_tech.append(t)

    context = {
        **metrics,
        'date_from': date_from,
        'date_to': date_to,
        'per_tech': per_tech,
        # Team-level tiles for the 3 new sections
        'team_accuracy_pct':    review_acc_data['team_accuracy_pct'],
        'team_returned':        returns_corr_data['team_returned'],
        'team_corrected_by_l3': returns_corr_data['team_corrected_by_l3'],
        'total_submissions':    advisor_data['total_submissions'],
        'advisor_stats':        advisor_data['advisor_stats'],
        'advisor_totals':       advisor_data['totals'],
    }
    return render(request, 'core/performance_dashboard.html', context)


# ── Drill-Down Detail View ────────────────────────────────────────────────────

# Implemented slugs and their display titles.
# Add new slugs here as each drill-down step is completed.
_DETAIL_TITLES = {
    'reports-generated':      'Reports Generated',
    'initial-submissions':    'Initial Submissions',
    'submitted-for-review':   'Submitted for Review',
    'on-time-delivery':       'On-Time Delivery',
    'profeds-errors':         'ProFeds Errors',
    'production-cycle-time':  'Avg Production Cycle Time',
    'readiness-window':       'Avg Readiness Window',
    'report-accuracy':        'Report Accuracy',
    # Added incrementally
}

@login_required
def performance_detail(request, metric_slug):
    """
    Drill-down detail page for a Benefits Team Portal Metrics tile.
    URL: /reports/performance/detail/<metric_slug>/?date_from=&date_to=
    Each slug returns the individual records behind that metric tile.
    """
    if not is_admin(request.user):
        messages.error(request, 'Access denied.')
        return redirect('home')

    if metric_slug not in _DETAIL_TITLES:
        from django.http import Http404
        raise Http404(f"Unknown metric slug: {metric_slug}")

    date_from = request.GET.get('date_from', '').strip()
    date_to   = request.GET.get('date_to',   '').strip()
    if not date_from and not date_to:
        date_to   = timezone.now().date().strftime('%Y-%m-%d')
        date_from = (timezone.now().date() - timedelta(days=7)).strftime('%Y-%m-%d')

    from datetime import datetime as _dt
    date_from_obj = _dt.strptime(date_from, '%Y-%m-%d').date() if date_from else None
    date_to_obj   = _dt.strptime(date_to,   '%Y-%m-%d').date() if date_to   else None

    title   = _DETAIL_TITLES[metric_slug]
    headers = []
    rows    = []
    extra_context = {}

    # ── Step B: Reports Generated ─────────────────────────────────────────
    if metric_slug == 'reports-generated':
        headers = ['Case ID', 'Advisor', 'Employee', 'Technician',
                   'Submitted', 'Finished', 'Due Date', 'Urgency']
        qs = _exclude_test_account_cases(
            Case.objects.filter(status='completed')
        ).select_related('member', 'assigned_to')
        if date_from_obj:
            qs = qs.filter(date_completed__date__gte=date_from_obj)
        if date_to_obj:
            qs = qs.filter(date_completed__date__lte=date_to_obj)
        for c in qs.order_by('-date_completed'):
            rows.append({
                'case_pk': c.pk,
                'cells': [
                    c.external_case_id,
                    c.member.get_full_name() if c.member else '—',
                    f'{c.employee_first_name} {c.employee_last_name}'.strip(),
                    c.assigned_to.get_full_name() if c.assigned_to else '—',
                    c.date_submitted.strftime('%m/%d/%y') if c.date_submitted else '—',
                    c.date_completed.strftime('%m/%d/%y') if c.date_completed else '—',
                    c.date_due.strftime('%m/%d/%y') if c.date_due else '—',
                    c.urgency.capitalize(),
                ],
                'highlight': 'danger' if c.urgency == 'rush' else '',
            })

    # ── Report Accuracy ───────────────────────────────────────────────────
    elif metric_slug == 'report-accuracy':
        headers = ['Case ID', 'Employee', 'Technician', 'Finished', 'ProFeds Error']
        qs = _exclude_test_account_cases(
            Case.objects.filter(status='completed')
        ).select_related('member', 'assigned_to')
        if date_from_obj:
            qs = qs.filter(date_completed__date__gte=date_from_obj)
        if date_to_obj:
            qs = qs.filter(date_completed__date__lte=date_to_obj)
        # Sort: errors first, then error-free
        for c in qs.order_by('-has_profeds_error', '-date_completed'):
            has_error = c.has_profeds_error
            rows.append({
                'case_pk': c.pk,
                'cells': [
                    c.external_case_id,
                    f'{c.employee_first_name} {c.employee_last_name}'.strip() or '—',
                    c.assigned_to.get_full_name() if c.assigned_to else '—',
                    c.date_completed.strftime('%m/%d/%y') if c.date_completed else '—',
                    'Yes' if has_error else 'No',
                ],
                'highlight': 'danger' if has_error else '',
            })

    # ── Readiness Window ────────────────────────────────────────────────
    elif metric_slug == 'readiness-window':
        headers = ['Case ID', 'Employee', 'Technician', 'Due Date', 'Finished', 'Days Early/Late']
        qs = _exclude_test_account_cases(
            Case.objects.filter(
                status='completed',
                date_due__isnull=False,
                date_completed__isnull=False,
            )
        ).select_related('member', 'assigned_to')
        if date_from_obj:
            qs = qs.filter(date_completed__date__gte=date_from_obj)
        if date_to_obj:
            qs = qs.filter(date_completed__date__lte=date_to_obj)
        cases_with_readiness = []
        for c in qs:
            delta = (c.date_due - c.date_completed.date()).days
            cases_with_readiness.append((delta, c))
        # Sort: most late first (lowest delta first)
        cases_with_readiness.sort(key=lambda x: x[0])
        for delta, c in cases_with_readiness:
            rows.append({
                'case_pk': c.pk,
                'cells': [
                    c.external_case_id,
                    f'{c.employee_first_name} {c.employee_last_name}'.strip() or '—',
                    c.assigned_to.get_full_name() if c.assigned_to else '—',
                    c.date_due.strftime('%m/%d/%y'),
                    c.date_completed.strftime('%m/%d/%y'),
                    f'+{delta}d' if delta > 0 else f'{delta}d',
                ],
                'highlight': 'danger' if delta < 0 else ('warning' if delta == 0 else ''),
            })

    # ── Production Cycle Time ────────────────────────────────────────────
    elif metric_slug == 'production-cycle-time':
        headers = ['Case ID', 'Employee', 'Technician', 'Submitted', 'Finished', 'Cycle Time']
        qs = _exclude_test_account_cases(
            Case.objects.filter(
                status='completed',
                date_submitted__isnull=False,
                date_completed__isnull=False,
            )
        ).select_related('member', 'assigned_to')
        if date_from_obj:
            qs = qs.filter(date_completed__date__gte=date_from_obj)
        if date_to_obj:
            qs = qs.filter(date_completed__date__lte=date_to_obj)
        cases_with_cycle = []
        for c in qs:
            delta = (c.date_completed.date() - c.date_submitted.date()).days
            cases_with_cycle.append((delta, c))
        # Sort longest cycle first
        cases_with_cycle.sort(key=lambda x: x[0], reverse=True)
        for delta, c in cases_with_cycle:
            rows.append({
                'case_pk': c.pk,
                'cells': [
                    c.external_case_id,
                    f'{c.employee_first_name} {c.employee_last_name}'.strip() or '—',
                    c.assigned_to.get_full_name() if c.assigned_to else '—',
                    c.date_submitted.strftime('%m/%d/%y'),
                    c.date_completed.strftime('%m/%d/%y'),
                    f'{delta}d',
                ],
                'highlight': 'warning' if delta < 0 else '',
            })

    # ── ProFeds Errors ────────────────────────────────────────────────────
    elif metric_slug == 'profeds-errors':
        headers = ['Mod Case ID', 'Original Case ID', 'Employee', 'Technician', 'Error Reported']
        qs = _exclude_test_account_cases(
            Case.objects.filter(
                has_profeds_error=True,
                original_case__isnull=False,
            )
        ).select_related('member', 'assigned_to', 'original_case')
        if date_from_obj:
            qs = qs.filter(date_submitted__date__gte=date_from_obj)
        if date_to_obj:
            qs = qs.filter(date_submitted__date__lte=date_to_obj)
        for c in qs.order_by('-date_submitted'):
            rows.append({
                'case_pk': c.pk,
                'cells': [
                    c.external_case_id,
                    c.original_case.external_case_id if c.original_case else '—',
                    f'{c.employee_first_name} {c.employee_last_name}'.strip() or '—',
                    c.assigned_to.get_full_name() if c.assigned_to else '—',
                    c.date_submitted.strftime('%m/%d/%y') if c.date_submitted else '—',
                ],
                'highlight': 'danger',
            })

    # ── On-Time Delivery ─────────────────────────────────────────────────
    elif metric_slug == 'on-time-delivery':
        headers = ['Case ID', 'Employee', 'Technician', 'Due Date', 'Finished', 'Days Early/Late', 'Status']
        qs = _exclude_test_account_cases(
            Case.objects.filter(
                status='completed',
                date_due__isnull=False,
                date_completed__isnull=False,
            )
        ).select_related('member', 'assigned_to')
        if date_from_obj:
            qs = qs.filter(date_completed__date__gte=date_from_obj)
        if date_to_obj:
            qs = qs.filter(date_completed__date__lte=date_to_obj)
        for c in qs.order_by('-date_completed'):
            delta = (c.date_due - c.date_completed.date()).days
            on_time = delta >= 0
            rows.append({
                'case_pk': c.pk,
                'cells': [
                    c.external_case_id,
                    f'{c.employee_first_name} {c.employee_last_name}'.strip() or '—',
                    c.assigned_to.get_full_name() if c.assigned_to else '—',
                    c.date_due.strftime('%m/%d/%y'),
                    c.date_completed.strftime('%m/%d/%y'),
                    f'+{delta}d' if delta >= 0 else f'{delta}d',
                    'On Time' if on_time else 'Late',
                ],
                'highlight': '' if on_time else 'danger',
            })

    # ── Step D: Submitted for Review ─────────────────────────────────────
    elif metric_slug == 'submitted-for-review':
        from cases.models import CaseReviewHistory
        headers = ['Case ID', 'Employee', 'Technician', 'Submitted At']
        qs = CaseReviewHistory.objects.filter(
            review_action='submitted_for_review'
        ).select_related('case', 'case__member', 'original_technician')
        if date_from_obj:
            qs = qs.filter(reviewed_at__date__gte=date_from_obj)
        if date_to_obj:
            qs = qs.filter(reviewed_at__date__lte=date_to_obj)
        for r in qs.order_by('-reviewed_at'):
            c = r.case
            rows.append({
                'case_pk': c.pk,
                'cells': [
                    c.external_case_id,
                    f'{c.employee_first_name} {c.employee_last_name}'.strip() or '—',
                    r.original_technician.get_full_name() if r.original_technician else '—',
                    r.reviewed_at.strftime('%m/%d/%y %I:%M %p'),
                ],
            })

    # ── Step C: Initial Submissions ───────────────────────────────────────
    elif metric_slug == 'initial-submissions':
        headers = ['Advisor', 'Workshop', 'Submitted', 'Completed', 'In Progress', 'Pending Accept', 'PF Errors']
        data = _get_advisor_submissions(date_from_obj, date_to_obj)
        for row in data['advisor_stats']:
            name = (f"{row['member__first_name'] or ''} {row['member__last_name'] or ''}".strip()
                    or row['member__username'])
            rows.append({
                'cells': [
                    name,
                    row['workshop_code'] or '—',
                    str(row['total_submitted']),
                    str(row['completed']),
                    str(row['in_progress']),
                    str(row['pending_accept']),
                    str(row['errors']),
                ],
            })
        # Pass totals for footer row
        t = data['totals']
        extra_context = {
            'totals_row': [
                'TOTALS', '',
                str(t['total_submitted'] or 0),
                str(t['completed'] or 0),
                str(t['in_progress'] or 0),
                str(t['pending_accept'] or 0),
                str(t['errors'] or 0),
            ]
        }

    context = {
        'title':        title,
        'metric_slug':  metric_slug,
        'date_from':    date_from,
        'date_to':      date_to,
        'headers':      headers,
        'rows':         rows,
        'total':        len(rows),
    }
    context.update(extra_context)
    return render(request, 'core/performance_detail.html', context)


# ── Helper data functions for expanded dashboard ─────────────────────────────

def _get_review_accuracy_by_tech(date_from_obj=None, date_to_obj=None):
    """First-pass approval rate per tech keyed by user ID, plus team totals."""
    from cases.models import CaseReviewHistory
    OUTCOMES = ['approved', 'revisions_requested', 'corrections_needed']
    qs = CaseReviewHistory.objects.filter(
        review_action__in=OUTCOMES,
        original_technician__isnull=False,
        original_technician__is_test_account=False,
    )
    if date_from_obj:
        qs = qs.filter(reviewed_at__date__gte=date_from_obj)
    if date_to_obj:
        qs = qs.filter(reviewed_at__date__lte=date_to_obj)

    result = {}
    for r in qs.select_related('original_technician'):
        tid = r.original_technician.id
        if tid not in result:
            result[tid] = {'total': 0, 'approved': 0, 'revisions': 0, 'corrections': 0}
        result[tid]['total'] += 1
        if r.review_action == 'approved':
            result[tid]['approved'] += 1
        elif r.review_action == 'revisions_requested':
            result[tid]['revisions'] += 1
        else:
            result[tid]['corrections'] += 1
    for v in result.values():
        v['review_accuracy_pct'] = round(v['approved'] / v['total'] * 100, 1) if v['total'] else None

    total    = sum(v['total']       for v in result.values())
    approved = sum(v['approved']    for v in result.values())
    return {
        'per_tech':          result,
        'team_total':        total,
        'team_approved':     approved,
        'team_revisions':    sum(v['revisions']   for v in result.values()),
        'team_corrections':  sum(v['corrections'] for v in result.values()),
        'team_accuracy_pct': round(approved / total * 100, 1) if total else None,
    }


def _get_returns_corrections_by_tech(date_from_obj=None, date_to_obj=None):
    """Returns and L3 corrections keyed by tech user ID, plus team totals."""
    from cases.models import CaseReviewHistory
    qs = CaseReviewHistory.objects.filter(
        review_action__in=['revisions_requested', 'corrections_needed'],
        original_technician__isnull=False,
        original_technician__is_test_account=False,
    )
    if date_from_obj:
        qs = qs.filter(reviewed_at__date__gte=date_from_obj)
    if date_to_obj:
        qs = qs.filter(reviewed_at__date__lte=date_to_obj)

    result = {}
    for r in qs.select_related('original_technician'):
        tid = r.original_technician.id
        if tid not in result:
            result[tid] = {'returned': 0, 'corrected_by_l3': 0}
        if r.review_action == 'revisions_requested':
            result[tid]['returned'] += 1
        else:
            result[tid]['corrected_by_l3'] += 1

    return {
        'per_tech':           result,
        'team_returned':      sum(v['returned']         for v in result.values()),
        'team_corrected_by_l3': sum(v['corrected_by_l3'] for v in result.values()),
    }


def _get_advisor_submissions(date_from_obj=None, date_to_obj=None):
    """Case submission stats per advisor for the date window."""
    cases_qs = _exclude_test_account_cases(
        Case.objects.exclude(status='draft').filter(member__isnull=False)
    )
    if date_from_obj:
        cases_qs = cases_qs.filter(date_submitted__date__gte=date_from_obj)
    if date_to_obj:
        cases_qs = cases_qs.filter(date_submitted__date__lte=date_to_obj)

    advisor_stats = list(
        cases_qs
        .values('member__id', 'member__first_name', 'member__last_name',
                'member__username', 'workshop_code')
        .annotate(
            total_submitted=Count('id'),
            completed=Count('id', filter=Q(status='completed')),
            in_progress=Count('id', filter=Q(status__in=['accepted', 'pending_review', 'hold'])),
            pending_accept=Count('id', filter=Q(status__in=['submitted', 'resubmitted'])),
            errors=Count('id', filter=Q(has_profeds_error=True)),
        )
        .order_by('-total_submitted')
    )
    totals = cases_qs.aggregate(
        total_submitted=Count('id'),
        completed=Count('id', filter=Q(status='completed')),
        in_progress=Count('id', filter=Q(status__in=['accepted', 'pending_review', 'hold'])),
        pending_accept=Count('id', filter=Q(status__in=['submitted', 'resubmitted'])),
        errors=Count('id', filter=Q(has_profeds_error=True)),
    )
    return {
        'advisor_stats':    advisor_stats,
        'totals':           totals,
        'total_submissions': totals['total_submitted'] or 0,
    }


# ── Report 1: Advisor Case Submission Report ─────────────────────────────────

@login_required
def advisor_submission_report(request):
    """Cases submitted by each advisor in the selected date window. Admin/Manager only."""
    if not is_admin(request.user):
        messages.error(request, 'Access denied. Administrators and Managers only.')
        return redirect('home')

    from datetime import datetime as _dt

    date_from_str = request.GET.get('date_from', '').strip()
    date_to_str = request.GET.get('date_to', '').strip()

    # Default: last 30 days
    if not date_from_str and not date_to_str:
        date_to_str = timezone.now().date().strftime('%Y-%m-%d')
        date_from_str = (timezone.now().date() - timedelta(days=30)).strftime('%Y-%m-%d')

    try:
        date_from = _dt.strptime(date_from_str, '%Y-%m-%d').date() if date_from_str else None
        date_to = _dt.strptime(date_to_str, '%Y-%m-%d').date() if date_to_str else None
    except ValueError:
        date_from = date_to = None

    # Base: non-draft cases submitted in window, excluding test accounts
    cases_qs = _exclude_test_account_cases(
        Case.objects.exclude(status='draft').filter(member__isnull=False)
    )
    if date_from:
        cases_qs = cases_qs.filter(date_submitted__date__gte=date_from)
    if date_to:
        cases_qs = cases_qs.filter(date_submitted__date__lte=date_to)

    # Aggregate per advisor
    from django.db.models import IntegerField as _IntField
    advisor_stats = (
        cases_qs
        .values('member__id', 'member__first_name', 'member__last_name',
                'member__username', 'workshop_code')
        .annotate(
            total_submitted=Count('id'),
            completed=Count('id', filter=Q(status='completed')),
            in_progress=Count('id', filter=Q(status__in=['accepted', 'pending_review', 'hold'])),
            pending_accept=Count('id', filter=Q(status__in=['submitted', 'resubmitted'])),
            errors=Count('id', filter=Q(has_profeds_error=True)),
        )
        .order_by('-total_submitted')
    )

    totals = cases_qs.aggregate(
        total_submitted=Count('id'),
        completed=Count('id', filter=Q(status='completed')),
        in_progress=Count('id', filter=Q(status__in=['accepted', 'pending_review', 'hold'])),
        pending_accept=Count('id', filter=Q(status__in=['submitted', 'resubmitted'])),
        errors=Count('id', filter=Q(has_profeds_error=True)),
    )

    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="advisor_submissions_{date_from_str}_{date_to_str}.csv"'
        writer = csv.writer(response)
        writer.writerow(['Advisor Case Submission Report'])
        writer.writerow([f'Period: {date_from_str or "All time"} to {date_to_str or "present"}'])
        writer.writerow([])
        writer.writerow(['Workshop Code', 'Advisor', 'Total Submitted', 'Completed',
                         'In Progress', 'Pending Accept', 'ProFeds Errors'])
        for row in advisor_stats:
            name = f"{row['member__first_name'] or ''} {row['member__last_name'] or ''}".strip() or row['member__username']
            writer.writerow([row['workshop_code'], name, row['total_submitted'],
                             row['completed'], row['in_progress'], row['pending_accept'], row['errors']])
        writer.writerow([])
        writer.writerow(['TOTALS', '', totals['total_submitted'], totals['completed'],
                         totals['in_progress'], totals['pending_accept'], totals['errors']])
        return response

    context = {
        'advisor_stats': list(advisor_stats),
        'totals': totals,
        'date_from': date_from_str,
        'date_to': date_to_str,
    }
    return render(request, 'core/advisor_submission_report.html', context)


# ── Report 2: L1/L2 Review Accuracy ─────────────────────────────────────────

@login_required
def review_accuracy_report(request):
    """First-pass approval rate for L1 and L2 technicians. Admin/Manager only."""
    if not is_admin(request.user):
        messages.error(request, 'Access denied. Administrators and Managers only.')
        return redirect('home')

    from datetime import datetime as _dt
    from cases.models import CaseReviewHistory

    date_from_str = request.GET.get('date_from', '').strip()
    date_to_str = request.GET.get('date_to', '').strip()

    if not date_from_str and not date_to_str:
        date_to_str = timezone.now().date().strftime('%Y-%m-%d')
        date_from_str = (timezone.now().date() - timedelta(days=30)).strftime('%Y-%m-%d')

    try:
        date_from = _dt.strptime(date_from_str, '%Y-%m-%d').date() if date_from_str else None
        date_to = _dt.strptime(date_to_str, '%Y-%m-%d').date() if date_to_str else None
    except ValueError:
        date_from = date_to = None

    OUTCOME_ACTIONS = ['approved', 'revisions_requested', 'corrections_needed']

    # Outcome review events for L1/L2 original technicians only
    qs = CaseReviewHistory.objects.filter(
        review_action__in=OUTCOME_ACTIONS,
        original_technician__isnull=False,
        original_technician__user_level__in=['level_1', 'level_2'],
        original_technician__is_test_account=False,
    )
    if date_from:
        qs = qs.filter(reviewed_at__date__gte=date_from)
    if date_to:
        qs = qs.filter(reviewed_at__date__lte=date_to)

    # Team totals
    total_reviews = qs.count()
    total_approved = qs.filter(review_action='approved').count()
    total_revisions = qs.filter(review_action='revisions_requested').count()
    total_corrections = qs.filter(review_action='corrections_needed').count()
    team_accuracy = round(total_approved / total_reviews * 100, 1) if total_reviews else None

    # Per-technician breakdown
    tech_rows = {}
    for r in qs.select_related('original_technician', 'reviewed_by', 'case'):
        tech = r.original_technician
        key = tech.id
        if key not in tech_rows:
            tech_rows[key] = {
                'tech': tech,
                'total': 0, 'approved': 0, 'revisions': 0, 'corrections': 0,
            }
        tech_rows[key]['total'] += 1
        if r.review_action == 'approved':
            tech_rows[key]['approved'] += 1
        elif r.review_action == 'revisions_requested':
            tech_rows[key]['revisions'] += 1
        else:
            tech_rows[key]['corrections'] += 1

    per_tech = []
    for row in sorted(tech_rows.values(), key=lambda x: x['tech'].get_full_name()):
        row['accuracy_pct'] = round(row['approved'] / row['total'] * 100, 1) if row['total'] else None
        per_tech.append(row)

    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="review_accuracy_{date_from_str}_{date_to_str}.csv"'
        writer = csv.writer(response)
        writer.writerow(['L1/L2 Review Accuracy Report'])
        writer.writerow([f'Period: {date_from_str or "All time"} to {date_to_str or "present"}'])
        writer.writerow([])
        writer.writerow(['Technician', 'Level', 'Total Reviews', 'Approved',
                         'Revisions Requested', 'Corrections by L3', 'Accuracy %'])
        for row in per_tech:
            writer.writerow([
                row['tech'].get_full_name(), row['tech'].get_user_level_display(),
                row['total'], row['approved'], row['revisions'], row['corrections'],
                row['accuracy_pct'] or 'N/A',
            ])
        writer.writerow([])
        writer.writerow(['TEAM TOTAL', '', total_reviews, total_approved,
                         total_revisions, total_corrections, team_accuracy or 'N/A'])
        return response

    context = {
        'per_tech': per_tech,
        'total_reviews': total_reviews,
        'total_approved': total_approved,
        'total_revisions': total_revisions,
        'total_corrections': total_corrections,
        'team_accuracy': team_accuracy,
        'date_from': date_from_str,
        'date_to': date_to_str,
    }
    return render(request, 'core/review_accuracy_report.html', context)


# ── Report 3: Returns & L3 Corrections Tracker ───────────────────────────────

@login_required
def review_returns_corrections_report(request):
    """Cases returned to L1/L2 for revision vs cases corrected directly by L3. Admin/Manager only."""
    if not is_admin(request.user):
        messages.error(request, 'Access denied. Administrators and Managers only.')
        return redirect('home')

    from datetime import datetime as _dt
    from cases.models import CaseReviewHistory

    date_from_str = request.GET.get('date_from', '').strip()
    date_to_str = request.GET.get('date_to', '').strip()

    if not date_from_str and not date_to_str:
        date_to_str = timezone.now().date().strftime('%Y-%m-%d')
        date_from_str = (timezone.now().date() - timedelta(days=30)).strftime('%Y-%m-%d')

    try:
        date_from = _dt.strptime(date_from_str, '%Y-%m-%d').date() if date_from_str else None
        date_to = _dt.strptime(date_to_str, '%Y-%m-%d').date() if date_to_str else None
    except ValueError:
        date_from = date_to = None

    base_qs = CaseReviewHistory.objects.filter(
        review_action__in=['revisions_requested', 'corrections_needed'],
        original_technician__isnull=False,
        original_technician__is_test_account=False,
    ).select_related('case', 'original_technician', 'reviewed_by')

    if date_from:
        base_qs = base_qs.filter(reviewed_at__date__gte=date_from)
    if date_to:
        base_qs = base_qs.filter(reviewed_at__date__lte=date_to)

    returned_qs = base_qs.filter(review_action='revisions_requested').order_by('-reviewed_at')
    corrected_qs = base_qs.filter(review_action='corrections_needed').order_by('-reviewed_at')

    # Per-tech summary
    tech_summary = {}
    for r in base_qs:
        tech = r.original_technician
        key = tech.id
        if key not in tech_summary:
            tech_summary[key] = {'tech': tech, 'returned': 0, 'corrected_by_l3': 0}
        if r.review_action == 'revisions_requested':
            tech_summary[key]['returned'] += 1
        else:
            tech_summary[key]['corrected_by_l3'] += 1

    per_tech = sorted(tech_summary.values(), key=lambda x: x['tech'].get_full_name())

    totals = {
        'returned': returned_qs.count(),
        'corrected_by_l3': corrected_qs.count(),
        'total': base_qs.count(),
    }

    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="returns_corrections_{date_from_str}_{date_to_str}.csv"'
        writer = csv.writer(response)
        writer.writerow(['Returns & L3 Corrections Tracker'])
        writer.writerow([f'Period: {date_from_str or "All time"} to {date_to_str or "present"}'])
        writer.writerow([])
        writer.writerow(['--- Cases Returned to Tech (Revisions Requested) ---'])
        writer.writerow(['Date', 'Case ID', 'Original Tech', 'Reviewed By', 'Notes'])
        for r in returned_qs:
            writer.writerow([
                r.reviewed_at.strftime('%Y-%m-%d'),
                r.case.external_case_id,
                r.original_technician.get_full_name() if r.original_technician else '—',
                r.reviewed_by.get_full_name() if r.reviewed_by else '—',
                r.review_notes[:200] if r.review_notes else '',
            ])
        writer.writerow([])
        writer.writerow(['--- Cases Corrected by L3 (No Return) ---'])
        writer.writerow(['Date', 'Case ID', 'Original Tech', 'Corrected By', 'Notes'])
        for r in corrected_qs:
            writer.writerow([
                r.reviewed_at.strftime('%Y-%m-%d'),
                r.case.external_case_id,
                r.original_technician.get_full_name() if r.original_technician else '—',
                r.reviewed_by.get_full_name() if r.reviewed_by else '—',
                r.review_notes[:200] if r.review_notes else '',
            ])
        return response

    context = {
        'returned_qs': returned_qs[:200],
        'corrected_qs': corrected_qs[:200],
        'per_tech': per_tech,
        'totals': totals,
        'date_from': date_from_str,
        'date_to': date_to_str,
    }
    return render(request, 'core/review_returns_corrections_report.html', context)
