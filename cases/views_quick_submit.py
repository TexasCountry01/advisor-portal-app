"""
Simplified case submission - creates case and goes directly to template.
No webform needed - users download template PDF and upload completed documents.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
import uuid
from cases.models import Case

@login_required
def quick_case_submit(request):
    """
    Quick case creation - minimal fields, then redirect to template view.
    This replaces the webform entirely.
    """
    user = request.user
    
    # Ensure user is a member
    if user.role != 'member':
        messages.error(request, 'Access denied. Members only.')
        return redirect('home')
    
    if request.method == 'POST':
        # Create minimal case with just essential info
        external_case_id = f"CASE-{uuid.uuid4().hex[:8].upper()}"
        
        # Get basic info from form
        employee_name = request.POST.get('employee_name', 'Unknown')
        employee_email = request.POST.get('employee_email', user.email)
        
        # Split name
        name_parts = employee_name.split(' ', 1)
        first_name = name_parts[0] if len(name_parts) > 0 else 'Unknown'
        last_name = name_parts[1] if len(name_parts) > 1 else 'Employee'
        
        # Minimal fact finder data - will be filled in via PDF upload
        fact_finder_data = {
            'basic_information': {
                'employee_name': employee_name,
            },
        }
        
        # Create case
        case = Case(
            member=user,
            workshop_code=user.workshop_code,
            external_case_id=external_case_id,
            employee_first_name=first_name,
            employee_last_name=last_name,
            client_email=employee_email,
            urgency=request.POST.get('urgency', 'normal'),
            num_reports_requested=1,
            status='submitted',
            fact_finder_data=fact_finder_data,
            api_sync_status='pending',
        )
        case.save()
        
        messages.success(request, f'Case {external_case_id} created! Now upload your Federal Fact Finder.')
        # Redirect directly to template view
        return redirect('case_fact_finder', case_id=case.id)
    
    # GET request - show quick submission form
    return render(request, 'cases/quick_case_submit.html')
