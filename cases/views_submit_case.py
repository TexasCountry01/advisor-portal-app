"""
Enhanced case submission view with all required fields.
Replaces the quick_case_submit with a more comprehensive form.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from datetime import timedelta, datetime
import json
from cases.models import Case
from accounts.models import User
from cases.services.case_id_generator import generate_case_id

@login_required
def submit_case(request):
    """
    Submit New Case page with all required fields:
    - Advisor Name (pre-populated for advisors, dropdown for delegates)
    - Fed First Name
    - Fed Last Name
    - Due date (default 7 days, rushed notification if less)
    - # of reports requested
    - Notes/Comments
    - Document upload (multiple files)
    """
    user = request.user
    
    # Ensure user is a member (advisor or delegate)
    if user.role != 'member':
        messages.error(request, 'Access denied. Members only.')
        return redirect('home')
    
    # Get advisors this user can submit cases for
    advisors_list = []
    from accounts.models import AdvisorDelegate, WorkshopDelegate
    
    # Check if user is a workshop delegate (has workshop codes they can submit for)
    workshop_delegates = WorkshopDelegate.objects.filter(
        delegate=user, 
        is_active=True,
        permission_level__in=['submit', 'edit', 'approve']
    )
    
    if workshop_delegates.exists():
        # User is a delegate - they can submit for ANY member in those workshops
        # Get all members in those workshop codes
        workshop_codes = list(workshop_delegates.values_list('workshop_code', flat=True).distinct())
        advisors_list = list(User.objects.filter(role='member', workshop_code__in=workshop_codes).distinct())
        # Also add themselves if they have a role as member (unlikely but safe)
        if user.role == 'member' and user not in advisors_list:
            advisors_list.append(user)
    else:
        # Check legacy AdvisorDelegate (if user is old delegate system)
        delegate_relationships = AdvisorDelegate.objects.filter(delegate=user, can_submit=True)
        if delegate_relationships.exists():
            advisors_list = [rel.advisor for rel in delegate_relationships]
        else:
            # User is an advisor - they can submit for themselves
            if user.role == 'member':
                advisors_list = [user]
    
    # Prepare context for form rendering
    context = {
        'advisors': advisors_list,
        'current_user': user,
        'default_due_date': (timezone.now().date() + timedelta(days=7)).isoformat(),
        'today': timezone.now().date().isoformat(),
    }
    
    if request.method == 'POST':
        try:
            # Get the action (draft or submit)
            action = request.POST.get('action', 'draft')
            
            # Get form data
            advisor_id = request.POST.get('advisor_id')
            workshop_code = request.POST.get('workshop_code', '').strip().upper()
            fed_first_name = request.POST.get('fed_first_name', '').strip()
            fed_last_name = request.POST.get('fed_last_name', '').strip()
            due_date_str = request.POST.get('due_date')
            num_reports = request.POST.get('num_reports_requested', '1')
            notes = request.POST.get('notes', '').strip()
            
            # Validate required fields
            if not fed_first_name or not fed_last_name:
                messages.error(request, 'Federal employee first and last name are required.')
                return render(request, 'cases/submit_case.html', context)
            
            if not workshop_code:
                messages.error(request, 'Workshop code is required.')
                return render(request, 'cases/submit_case.html', context)
            
            # Validate workshop code format (2-5 characters, alphanumeric)
            if not (2 <= len(workshop_code) <= 5 and workshop_code.isalnum()):
                messages.error(request, 'Workshop code must be 2-5 alphanumeric characters (e.g., ABCD, XYZ).')
                return render(request, 'cases/submit_case.html', context)
            
            if not advisor_id:
                messages.error(request, 'Advisor selection is required.')
                return render(request, 'cases/submit_case.html', context)
            
            # Get advisor
            try:
                advisor = User.objects.get(id=int(advisor_id), role='member')
            except (User.DoesNotExist, ValueError):
                messages.error(request, 'Invalid advisor selected.')
                return render(request, 'cases/submit_case.html', context)
            
            # Verify permission - user must be the advisor or have delegation access
            if user.id != advisor.id and advisor not in advisors_list:
                messages.error(request, 'You do not have permission to submit cases for this advisor.')
                return render(request, 'cases/submit_case.html', context)
            
            # If user is not the advisor, verify they have workshop delegate access for this workshop code
            if user.id != advisor.id:
                from accounts.models import WorkshopDelegate
                has_workshop_access = WorkshopDelegate.objects.filter(
                    delegate=user,
                    workshop_code=workshop_code,
                    is_active=True,
                    permission_level__in=['submit', 'edit', 'approve']
                ).exists()
                
                if not has_workshop_access:
                    messages.error(request, f'You do not have delegate access to workshop {workshop_code}.')
                    return render(request, 'cases/submit_case.html', context)
            
            
            # Parse and validate due date
            try:
                due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date() if due_date_str else None
            except (ValueError, TypeError):
                due_date = None
            
            # Get urgency from form (member selection)
            urgency = request.POST.get('urgency', 'normal')
            if urgency not in ['normal', 'rush']:
                urgency = 'normal'
            
            # Validate num_reports
            try:
                num_reports = int(num_reports)
                if num_reports < 1 or num_reports > 10:
                    num_reports = 1
            except (ValueError, TypeError):
                num_reports = 1
            
            # Create case with meaningful ID
            external_case_id = generate_case_id(workshop_code)
            
            fact_finder_data = {
                'basic_information': {
                    'employee_name': f"{fed_first_name} {fed_last_name}",
                    'first_name': fed_first_name,
                    'last_name': fed_last_name,
                },
                'case_notes': notes,
            }
            
            case = Case(
                member=advisor,
                workshop_code=workshop_code,  # Use submitted workshop code
                external_case_id=external_case_id,
                employee_first_name=fed_first_name,
                employee_last_name=fed_last_name,
                client_email=request.POST.get('fed_email', ''),
                urgency=urgency,
                num_reports_requested=num_reports,
                date_due=due_date,
                status='draft' if action == 'draft' else 'submitted',
                fact_finder_data=fact_finder_data,
                api_sync_status='pending',
                created_by=user,  # Track who created it (could be delegate)
                special_notes=notes,  # Save notes to special_notes field
                date_submitted=timezone.now() if action == 'submit' else None,
            )
            case.save()
            
            # Calculate and set default credit value
            from cases.services.credit_service import calculate_default_credit, set_case_credit
            default_credit = calculate_default_credit(num_reports)
            set_case_credit(case, default_credit, user, 'submission', f'Default: {num_reports} report(s) requested')
            
            # Handle file uploads - Combined document upload
            # All documents are now stored together as one unified type
            if 'case_documents' in request.FILES:
                files = request.FILES.getlist('case_documents')
                for file in files:
                    from cases.models import CaseDocument
                    import os
                    
                    # Append employee last name to filename
                    filename_with_employee = f"{fed_last_name}_{file.name}"
                    
                    # All documents stored as 'fact_finder' type (unified document type)
                    CaseDocument.objects.create(
                        case=case,
                        document_type='fact_finder',
                        original_filename=filename_with_employee,
                        file_size=file.size,
                        uploaded_by=user,
                        file=file,
                    )
            
            # Get document count message using helper function
            from cases.services.document_count_service import get_document_count_message
            doc_count_msg = get_document_count_message(case, include_breakdown=True)
            
            # Determine if this is rushed
            if urgency == 'rush':
                messages.warning(
                    request,
                    f'WARNING: This report has been marked as RUSHED (due date less than 7 days). '
                    f'A rush fee may apply. Case ID: {external_case_id}. '
                    f'{doc_count_msg}'
                )
            else:
                if action == 'draft':
                    messages.success(
                        request,
                        f'Case saved as draft! Case ID: {external_case_id}. '
                        f'{doc_count_msg} You can submit it later.'
                    )
                else:
                    messages.success(
                        request,
                        f'Case submitted successfully! Case ID: {external_case_id}. '
                        f'{doc_count_msg}'
                    )
            
            # Redirect to member dashboard
            return redirect('cases:member_dashboard')
        
        except Exception as e:
            messages.error(request, f'Error creating case: {str(e)}')
            return render(request, 'cases/submit_case.html', context)
    
    # GET request - show form
    return render(request, 'cases/submit_case.html', context)


@login_required
def api_calculate_rushed_fee(request):
    """
    AJAX endpoint to check if due date qualifies as rushed
    and calculate potential fee.
    """
    try:
        due_date_str = request.GET.get('due_date')
        if not due_date_str:
            return JsonResponse({'is_rushed': False, 'fee': 0})
        
        due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
        default_due_date = timezone.now().date() + timedelta(days=7)
        
        is_rushed = due_date < default_due_date
        
        # Flat $20 fee for rushed requests (less than 7 days)
        fee = 20 if is_rushed else 0
        
        return JsonResponse({
            'is_rushed': is_rushed,
            'fee': fee,
            'message': 'Rushed request - $20 fee applies' if is_rushed else 'Standard processing - no rush fee',
        })
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)
