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
    from accounts.models import MemberDelegate
    
    # Check if user is a delegate for any members (via MemberDelegate)
    delegate_assignments = MemberDelegate.objects.filter(delegate=user).select_related('member')
    assigned_members = [da.member for da in delegate_assignments]
    
    if assigned_members:
        # User is a delegate — start with assigned members
        advisors_list = list(assigned_members)
        # Include themselves only if they are also an advisor (not a pure delegate)
        # A pure delegate has no one delegating TO them and no cases of their own
        if user not in advisors_list:
            is_also_advisor = (
                MemberDelegate.objects.filter(member=user).exists()
                or Case.objects.filter(member=user).exists()
            )
            if is_also_advisor:
                advisors_list.insert(0, user)
    else:
        # User is a regular advisor — submit for themselves only
        if user.role == 'member':
            advisors_list = [user]
    
    # Determine if advisor/workshop fields should be locked (single choice)
    # Only lock when there's truly one advisor — delegates with multiple advisors
    # always need a dropdown even if all share the same workshop code
    is_single_choice = len(advisors_list) <= 1
    
    # Prepare context for form rendering
    context = {
        'advisors': advisors_list,
        'current_user': user,
        'default_due_date': (timezone.now().date() + timedelta(days=7)).isoformat(),
        'today': timezone.now().date().isoformat(),
        'is_single_choice': is_single_choice,
        'is_delegate': len(assigned_members) > 0,
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
            
            # If user is not the advisor, verify they have delegate access via MemberDelegate
            if user.id != advisor.id:
                from accounts.models import MemberDelegate
                has_delegate_access = MemberDelegate.objects.filter(
                    delegate=user,
                    member=advisor,
                ).exists()
                
                if not has_delegate_access:
                    messages.error(request, f'You do not have delegate access for {advisor.get_full_name()}.')
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
            
            # If member included notes for benefits team, add as first chat message
            if action == 'submit' and notes and notes.strip():
                from cases.models import CaseMessage
                CaseMessage.objects.create(
                    case=case,
                    author=user,
                    message=notes.strip()
                )
            
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
            
            # Get document count
            doc_count = case.documents.count()
            
            # Log case submission to audit trail (after file uploads so document_count is accurate)
            if action == 'submit':
                from core.models import AuditLog
                submit_metadata = {
                    'urgency': urgency,
                    'document_count': doc_count,
                }
                submit_description = f'Case submitted for {fed_first_name} {fed_last_name}'
                
                # Add delegate context if submitting on behalf of another member
                if user.id != advisor.id:
                    submit_metadata['submitted_by_delegate'] = True
                    submit_metadata['delegate_id'] = user.id
                    submit_metadata['delegate_name'] = user.get_full_name()
                    submit_metadata['delegate_email'] = user.email
                    submit_metadata['on_behalf_of'] = advisor.get_full_name()
                    submit_description = f'Case submitted for {fed_first_name} {fed_last_name} by delegate {user.get_full_name()} on behalf of {advisor.get_full_name()}'
                
                AuditLog.log_activity(
                    user=user,
                    action_type='case_submitted',
                    case=case,
                    description=submit_description,
                    metadata=submit_metadata
                )
            doc_count_msg = f'Documents uploaded: {doc_count}.' if doc_count > 0 else 'No documents uploaded.'
            
            # Determine if this is rushed
            if urgency == 'rush':
                messages.warning(
                    request,
                    f'WARNING: Case for {fed_first_name} {fed_last_name} has been marked as RUSHED (due date less than 7 days). '
                    f'A rush fee may apply. '
                    f'{doc_count_msg}'
                )
            else:
                if action == 'draft':
                    messages.success(
                        request,
                        f'Case for {fed_first_name} {fed_last_name} saved as draft! '
                        f'{doc_count_msg} You can submit it later.'
                    )
                else:
                    messages.success(
                        request,
                        f'Case for {fed_first_name} {fed_last_name} submitted successfully! '
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
