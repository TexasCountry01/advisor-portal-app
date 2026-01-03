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


def is_admin(user):
    """Helper function to check if user is admin"""
    return user.is_authenticated and user.role == 'administrator'


@login_required
def view_reports(request):
    """Main reports page - Admin only"""
    if not is_admin(request.user):
        messages.error(request, 'Access denied. Administrators only.')
        return redirect('home')
    
    # Get all report data
    context = get_all_reports_data()
    
    return render(request, 'core/view_reports.html', context)


def get_all_reports_data():
    """Compile all report data for the dashboard"""
    
    # === CASE ANALYTICS ===
    total_cases = Case.objects.count()
    completed_cases = Case.objects.filter(status='completed').count()
    submitted_cases = Case.objects.filter(status='submitted').count()
    
    # Average processing time (days from submission to completion)
    completed_with_dates = Case.objects.filter(
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
    rush_cases = Case.objects.filter(urgency='urgent').count()
    standard_cases = Case.objects.filter(urgency='normal').count()
    
    # Cases by urgency level
    cases_by_urgency = Case.objects.values('urgency').annotate(count=Count('id')).order_by('urgency')
    
    # === PERFORMANCE METRICS ===
    # Cases per technician
    cases_per_tech = Case.objects.filter(
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
    avg_credits = Case.objects.exclude(credits__isnull=True).exclude(
        credits=''
    ).aggregate(avg=Avg(F('credits'), output_field=FloatField()))
    
    avg_credits_value = avg_credits['avg'] or 0
    
    # Quality review metrics - approval rates
    level_1_cases = Case.objects.filter(assigned_to__user_level='level_1')
    level_1_completed = level_1_cases.filter(status='completed').count()
    level_1_pending_review = level_1_cases.filter(status='pending_review').count()
    level_1_total = level_1_cases.count()
    
    if level_1_total > 0:
        approval_rate = (level_1_completed / level_1_total) * 100
    else:
        approval_rate = 0
    
    # Member activity
    total_members = User.objects.filter(role='member').count()
    members_with_cases = Case.objects.filter(
        member__isnull=False
    ).values('member_id').distinct().count()
    
    # === FINANCIAL REPORTS ===
    # Credits analysis
    total_credits_issued = Case.objects.exclude(credits__isnull=True).exclude(
        credits=''
    ).aggregate(total=Sum(F('credits'), output_field=FloatField()))['total'] or 0
    
    # Credits by workshop code
    credits_by_workshop = Case.objects.exclude(credits__isnull=True).exclude(
        credits=''
    ).values('workshop_code').annotate(
        total_credits=Sum(F('credits'), output_field=FloatField()),
        case_count=Count('id')
    ).order_by('-total_credits')[:10]
    
    # === STATUS REPORTS ===
    status_distribution = Case.objects.values('status').annotate(
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
    level_1_techs = User.objects.filter(role='technician', user_level='level_1').count()
    level_2_techs = User.objects.filter(role='technician', user_level='level_2').count()
    level_3_techs = User.objects.filter(role='technician', user_level='level_3').count()
    
    # Recent cases (last 30 days)
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
        messages.error(request, 'Access denied. Administrators only.')
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
        name = f"{tech['first_name']} {tech['last_name']}" if tech['first_name'] else tech['username']
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
