from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.db import models
from django.utils import timezone
from django.http import HttpResponseForbidden, JsonResponse
from django.urls import reverse
from accounts.models import User
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
def technician_dashboard(request):
    """Dashboard view for Benefits Technician - shows all cases (not just assigned)"""
    user = request.user
    
    # Ensure user is a technician, manager, or admin
    if user.role not in ['technician', 'manager', 'administrator']:
        messages.error(request, 'Access denied. Technicians and Admins only.')
        return redirect('home')
    
    # Get all cases (technicians see all, not just assigned)
    cases = Case.objects.all().prefetch_related(
        'documents'
    ).select_related(
        'member', 'assigned_to', 'reviewed_by'
    ).order_by('-date_submitted')
    
    # Apply filters
    status_filter = request.GET.get('status')
    urgency_filter = request.GET.get('urgency')
    tier_filter = request.GET.get('tier')
    search_query = request.GET.get('search')
    sort_by = request.GET.get('sort', '-date_submitted')
    assigned_filter = request.GET.get('assigned', 'all')  # 'all' or 'mine'
    
    # Apply "My Cases" filter
    if assigned_filter == 'mine':
        cases = cases.filter(assigned_to=user)
    
    if status_filter:
        cases = cases.filter(status=status_filter)
    
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
    
    # Calculate statistics
    all_cases = Case.objects.all()
    stats = {
        'total': all_cases.count(),
        'submitted': all_cases.filter(status='submitted').count(),
        'accepted': all_cases.filter(status='accepted').count(),
        'pending_review': all_cases.filter(status='pending_review').count(),
        'completed': all_cases.filter(status='completed').count(),
        'urgent': all_cases.filter(urgency='urgent').count(),
    }
    
    # Get available technicians and administrators for assignment dropdown
    technicians = User.objects.filter(
        role__in=['technician', 'administrator']
    ).order_by('last_name', 'first_name')
    
    context = {
        'cases': cases,
        'stats': stats,
        'status_filter': status_filter,
        'urgency_filter': urgency_filter,
        'tier_filter': tier_filter,
        'search_query': search_query,
        'sort_by': sort_by,
        'assigned_filter': assigned_filter,
        'technicians': technicians,
        'dashboard_type': 'technician',
    }
    
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
    
    # Date range filter
    if date_range:
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
    stats = {
        'total': all_cases.count(),
        'submitted': all_cases.filter(status='submitted').count(),
        'accepted': all_cases.filter(status='accepted').count(),
        'hold': all_cases.filter(status='hold').count(),
        'pending_review': all_cases.filter(status='pending_review').count(),
        'completed': all_cases.filter(status='completed').count(),
        'urgent': all_cases.filter(urgency='urgent').count(),
        'total_members': User.objects.filter(role='member', is_active=True).count(),
        'total_technicians': User.objects.filter(role='technician', is_active=True).count(),
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
        'search_query': search_query,
        'sort_by': sort_by,
        'dashboard_type': 'admin',
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
    
    # Date range filter
    if date_range:
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
        'search_query': search_query,
        'sort_by': sort_by,
        'dashboard_type': 'manager',
        'is_readonly': True,
    }
    
    return render(request, 'cases/manager_dashboard.html', context)


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
    
    # Permission check - only members can delete their own cases (any status)
    if request.user.role == 'member' and case.member == request.user:
        case_id = case.external_case_id
        case.delete()
        messages.success(request, f'Case {case_id} has been deleted.')
        return redirect('member_dashboard')
    
    # Redirect based on user role
    if request.user.role == 'member':
        messages.error(request, 'You do not have permission to delete this case.')
        return redirect('member_dashboard')
    elif request.user.role == 'technician':
        return redirect('technician_dashboard')
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
                'redirect': reverse('member_dashboard')
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
            
            # Assign the case to the current technician
            case.assigned_to = user
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

