"""
Reports and Analytics Views
Provides comprehensive reporting and analytics for administrators
"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from django.db.models import Count, Q, Avg, F, Sum, Case as CaseWhen, When, Value, FloatField
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
