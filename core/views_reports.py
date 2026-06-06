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
    """Helper function to check if user is admin or manager"""
    return user.is_authenticated and user.role in ['administrator', 'manager']


def _get_super_dev_email():
    """Return configured super-dev email from system settings."""
    try:
        return (SystemSettings.get_settings().super_dev_email or '').strip().lower()
    except Exception:
        return ''


def _exclude_super_dev_users(queryset):
    """Exclude configured super-dev account from report user metrics."""
    super_dev_email = _get_super_dev_email()
    if not super_dev_email:
        return queryset
    return queryset.exclude(email__iexact=super_dev_email)


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
    
    # Build base queryset with optional date filter
    cases_qs = Case.objects.all()
    
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
    
    # Build queryset for cases with ProFeds errors
    error_cases_qs = Case.objects.filter(has_profeds_error=True)
    
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

    error_cases_qs = Case.objects.filter(has_profeds_error=True)
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

    qs = Case.objects.filter(
        status='completed',
        date_due__isnull=False,
        date_completed__isnull=False,
    )

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

    # avg days early (positive = early)
    days_diff_list = []
    for case in qs.only('id', 'date_due', 'date_completed'):
        if case.date_completed and case.date_due:
            completed_date = case.date_completed.date() if hasattr(case.date_completed, 'date') else case.date_completed
            diff = (case.date_due - completed_date).days
            days_diff_list.append(diff)

    avg_days_early = round(sum(days_diff_list) / len(days_diff_list), 1) if days_diff_list else 0

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
    case_qs = _exclude_super_dev_users(
        Case.objects.filter(member__isnull=False).select_related('member')
    )
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

    return {
        'total_members': total_members,
        'never_submitted_count': never_submitted_count,
        'active_submitter_count': len(active_submitter_ids),
        'member_counts': list(member_counts),
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
                         'Rush Cases', 'Last Submitted'])
        for row in data['member_counts']:
            writer.writerow([
                f"{row['member__first_name']} {row['member__last_name']}",
                row['member__email'] or '',
                row['member__workshop_code'] or '',
                row['case_count'],
                row['rush_count'],
                row['last_submitted'].strftime('%Y-%m-%d') if row['last_submitted'] else '',
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
