from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from .forms import (
    UserCreationForm,
    MemberProfileEditForm,
    DelegateAccessForm,
    MemberCreditAllowanceForm,
    WorkshopDelegateForm
)
from .models import DelegateAccess, MemberCreditAllowance, WorkshopDelegate
from core.models import AuditLog

User = get_user_model()


def is_admin(user):
    """Check if user is an administrator"""
    return user.is_authenticated and user.role == 'administrator'


def is_technician(user):
    """Check if user is a technician"""
    return user.is_authenticated and user.role == 'technician'


def can_create_user(current_user, target_role):
    """
    Determine if current user can create a user with target_role.
    
    Rules:
    - Administrator: Can create Technician, Manager, and Member users
    - Technician: Can create Member users
    - Others: Cannot create users
    """
    if not current_user.is_authenticated:
        return False
    
    if current_user.role == 'administrator':
        # Admin can create techs, managers, and members
        return target_role in ['technician', 'manager', 'member']
    
    if current_user.role == 'technician':
        # Tech can create members
        return target_role == 'member'
    
    return False


def can_edit_user(current_user, target_user):
    """
    Determine if current user can edit target_user.
    
    Rules:
    - Super Admin: Can edit Technician and Manager users
    - Technician: Can edit Member users they created
    - Users can edit their own profile
    """
    if not current_user.is_authenticated:
        return False
    
    # Users can always edit themselves
    if current_user.id == target_user.id:
        return True
    
    if current_user.role == 'administrator':
        # Admin can edit techs and managers
        return target_user.role in ['technician', 'manager']
    
    if current_user.role == 'technician':
        # Tech can edit members
        return target_user.role == 'member'
    
    return False


@login_required
def manage_users(request):
    """Manage users - create and edit. Role-based permissions."""
    
    current_user = request.user
    
    # Check if user has any user management permissions
    if current_user.role not in ['administrator', 'technician']:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('home')
    
    # Handle form submission
    if request.method == 'POST':
        form = UserCreationForm(request.POST, current_user=current_user)
        if form.is_valid():
            target_role = form.cleaned_data.get('role')
            
            # Check permission to create this role
            if not can_create_user(current_user, target_role):
                messages.error(
                    request,
                    f'You do not have permission to create {target_role} users.'
                )
            else:
                try:
                    user = form.save()
                    messages.success(
                        request,
                        f'User {user.get_full_name()} ({user.username}) created successfully!'
                    )
                    return redirect('manage_users')
                except Exception as e:
                    messages.error(request, f'Error creating user: {str(e)}')
    else:
        form = UserCreationForm(current_user=current_user)
    
    # Get users based on current user's role
    if current_user.role == 'administrator':
        # Admin sees all technicians, managers, and members
        users = User.objects.filter(role__in=['technician', 'manager', 'member']).order_by('-created_at')
    elif current_user.role == 'technician':
        # Technician sees only members
        users = User.objects.filter(role='member').order_by('-created_at')
    else:
        users = User.objects.none()
    
    context = {
        'form': form,
        'users': users,
        'current_user_role': current_user.role,
    }
    
    return render(request, 'accounts/manage_users.html', context)


@login_required
def deactivate_user(request, user_id):
    """Deactivate a user (set inactive). Preserves all case associations."""
    
    current_user = request.user
    user_to_deactivate = get_object_or_404(User, id=user_id)
    
    # Check permission
    if not can_edit_user(current_user, user_to_deactivate):
        messages.error(request, 'You do not have permission to modify this user.')
        return redirect('manage_users')
    
    # Prevent deactivating yourself
    if current_user.id == user_to_deactivate.id:
        messages.error(request, 'You cannot deactivate your own account.')
        return redirect('manage_users')
    
    username = user_to_deactivate.get_full_name() or user_to_deactivate.username
    user_to_deactivate.is_active = False
    user_to_deactivate.save()
    
    messages.success(
        request,
        f'User {username} has been deactivated. All associated cases are preserved.'
    )
    
    return redirect('manage_users')


@login_required
def reactivate_user(request, user_id):
    """Reactivate an inactive user."""
    
    current_user = request.user
    user_to_reactivate = get_object_or_404(User, id=user_id)
    
    # Check permission
    if not can_edit_user(current_user, user_to_reactivate):
        messages.error(request, 'You do not have permission to modify this user.')
        return redirect('manage_users')
    
    username = user_to_reactivate.get_full_name() or user_to_reactivate.username
    user_to_reactivate.is_active = True
    user_to_reactivate.save()
    
    messages.success(request, f'User {username} has been reactivated.')
    
    return redirect('manage_users')


# ============================================================================
# MEMBER PROFILE MANAGEMENT VIEWS
# ============================================================================
# These views enable Benefits Technicians to edit member profiles post-creation.
#
# Key features:
# - Edit member profile information (name, email, phone, workshop code, active status)
# - Manage delegate access (who can submit cases on behalf of member)
# - Configure quarterly credit allowances
# - All changes are logged via AuditLog for compliance and debugging
#
# Permission model:
# - Only Users with role='technician' (Benefits Technicians) can access these
# - Technicians can edit any member profile
#
# WP FUSION INTEGRATION NOTES:
# - The is_active field is manually toggled here (PLACEHOLDER)
# - When WP Fusion is integrated, is_active will be synced from WP subscription status
# - See model comments in accounts/models.py for additional WP Fusion integration points
# ============================================================================


def can_edit_member_profile(user):
    """
    Check if user can edit member profiles.
    
    Only Benefits Technicians (role='technician') can edit member profiles.
    
    Note: Future enhancement could add permission-based system:
    - 'accounts.edit_member_profile' permission
    - Role-based + permission checking
    """
    return user.is_authenticated and user.role == 'technician'


@login_required
def member_profile_edit(request, member_id):
    """
    Main view for editing a member (advisor) profile.
    
    Displays:
    - Basic profile information (name, email, phone, workshop code, active status)
    - Current delegates and ability to add/remove delegates
    - Quarterly credit allowances (view/edit current and upcoming quarters)
    - Audit trail of profile changes
    
    Only accessible by Benefits Technicians (role='technician').
    
    URL: /accounts/members/{member_id}/edit/
    """
    
    current_user = request.user
    member = get_object_or_404(User, id=member_id, role='member')
    
    # PERMISSION CHECK: Only technicians can edit member profiles
    if not can_edit_member_profile(current_user):
        messages.error(request, 'You do not have permission to edit member profiles.')
        return redirect('home')
    
    # Handle profile edit form submission
    if request.method == 'POST' and 'profile_form' in request.POST:
        profile_form = MemberProfileEditForm(
            request.POST,
            instance=member,
            changed_by_user=current_user
        )
        
        if profile_form.is_valid():
            try:
                old_data = {
                    'first_name': member.first_name,
                    'last_name': member.last_name,
                    'email': member.email,
                    'phone': member.phone,
                    'workshop_code': member.workshop_code,
                    'is_active': member.is_active,
                }
                
                updated_member = profile_form.save()
                
                new_data = {
                    'first_name': updated_member.first_name,
                    'last_name': updated_member.last_name,
                    'email': updated_member.email,
                    'phone': updated_member.phone,
                    'workshop_code': updated_member.workshop_code,
                    'is_active': updated_member.is_active,
                }
                
                # LOG THE CHANGE
                # Track what changed for audit trail
                changes = {}
                for key in old_data:
                    if old_data[key] != new_data[key]:
                        changes[key] = {
                            'old': str(old_data[key]),
                            'new': str(new_data[key])
                        }
                
                # Create audit log entry
                AuditLog.objects.create(
                    user=current_user,
                    action='member_profile_updated',
                    resource_type='member',
                    resource_id=member.id,
                    details={
                        'member_name': member.get_full_name(),
                        'changes': changes,
                        'edit_type': 'profile_information'
                    }
                )
                
                messages.success(
                    request,
                    f'Profile for {updated_member.get_full_name()} has been updated successfully.'
                )
                
            except Exception as e:
                messages.error(request, f'Error updating profile: {str(e)}')
    else:
        profile_form = MemberProfileEditForm(instance=member)
    
    # Get delegate access records
    active_delegates = member.granted_delegate_access.filter(is_active=True)
    inactive_delegates = member.granted_delegate_access.filter(is_active=False)
    
    # Get recent audit logs for this member
    audit_logs = AuditLog.objects.filter(
        resource_type='member',
        resource_id=member.id
    ).order_by('-created_at')[:20]
    
    # Get current quarter credit allowance
    from datetime import datetime
    current_year = datetime.now().year
    current_quarter = (datetime.now().month - 1) // 3 + 1
    
    current_allowance = member.credit_allowances.filter(
        fiscal_year=current_year,
        quarter=current_quarter
    ).first()
    
    # Get all quarters for credit editing (current + next 4 quarters)
    quarters = []
    temp_year = current_year
    temp_quarter = current_quarter
    for i in range(5):
        quarters.append({
            'year': temp_year,
            'quarter': temp_quarter,
            'display': f'FY{temp_year} Q{temp_quarter}',
            'allowance': member.credit_allowances.filter(
                fiscal_year=temp_year,
                quarter=temp_quarter
            ).first()
        })
        temp_quarter += 1
        if temp_quarter > 4:
            temp_quarter = 1
            temp_year += 1
    
    context = {
        'member': member,
        'profile_form': profile_form,
        'active_delegates': active_delegates,
        'inactive_delegates': inactive_delegates,
        'audit_logs': audit_logs,
        'current_allowance': current_allowance,
        'quarters': quarters,
        'is_benefits_tech': can_edit_member_profile(current_user),
    }
    
    return render(request, 'accounts/member_profile_edit.html', context)


@login_required
def member_delegate_add(request, member_id):
    """
    Add a new delegate for a member.
    
    Delegates are team members who can submit cases on behalf of the member.
    Benefits Technicians control who has access and what permissions they have.
    
    URL: POST /accounts/members/{member_id}/delegate/add/
    """
    
    current_user = request.user
    member = get_object_or_404(User, id=member_id, role='member')
    
    # PERMISSION CHECK
    if not can_edit_member_profile(current_user):
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    if request.method == 'POST':
        form = DelegateAccessForm(
            member,
            request.POST,
            changed_by_user=current_user
        )
        
        if form.is_valid():
            try:
                delegate_access = form.save()
                
                # LOG THE CHANGE
                AuditLog.objects.create(
                    user=current_user,
                    action='delegate_access_granted',
                    resource_type='member',
                    resource_id=member.id,
                    details={
                        'member_name': member.get_full_name(),
                        'delegate_name': delegate_access.delegate.get_full_name(),
                        'permission_level': delegate_access.permission_level,
                        'reason': delegate_access.grant_reason
                    }
                )
                
                messages.success(
                    request,
                    f'{delegate_access.delegate.get_full_name()} now has {delegate_access.permission_level} '
                    f'access for {member.get_full_name()}'
                )
                
                return redirect('member_profile_edit', member_id=member.id)
                
            except Exception as e:
                messages.error(request, f'Error adding delegate: {str(e)}')
                return redirect('member_profile_edit', member_id=member.id)
    else:
        form = DelegateAccessForm(member)
    
    context = {
        'member': member,
        'form': form,
        'action': 'add'
    }
    return render(request, 'accounts/member_delegate_form.html', context)


@login_required
def member_delegate_edit(request, delegate_id):
    """
    Edit delegate access permissions.
    
    Allows Benefits Technicians to modify permission levels or revoke access.
    
    URL: /accounts/delegates/{delegate_id}/edit/
    """
    
    current_user = request.user
    delegate_access = get_object_or_404(DelegateAccess, id=delegate_id)
    member = delegate_access.member
    
    # PERMISSION CHECK
    if not can_edit_member_profile(current_user):
        messages.error(request, 'Permission denied')
        return redirect('home')
    
    if request.method == 'POST':
        old_permission = delegate_access.permission_level
        old_active = delegate_access.is_active
        
        form = DelegateAccessForm(
            member,
            request.POST,
            instance=delegate_access,
            changed_by_user=current_user
        )
        
        if form.is_valid():
            try:
                updated_access = form.save()
                
                # LOG THE CHANGE
                changes = {}
                if old_permission != updated_access.permission_level:
                    changes['permission_level'] = {
                        'old': old_permission,
                        'new': updated_access.permission_level
                    }
                if old_active != updated_access.is_active:
                    changes['is_active'] = {
                        'old': old_active,
                        'new': updated_access.is_active
                    }
                
                AuditLog.objects.create(
                    user=current_user,
                    action='delegate_access_modified',
                    resource_type='member',
                    resource_id=member.id,
                    details={
                        'member_name': member.get_full_name(),
                        'delegate_name': updated_access.delegate.get_full_name(),
                        'changes': changes
                    }
                )
                
                messages.success(
                    request,
                    'Delegate access has been updated.'
                )
                
                return redirect('member_profile_edit', member_id=member.id)
                
            except Exception as e:
                messages.error(request, f'Error updating delegate: {str(e)}')
    else:
        form = DelegateAccessForm(member, instance=delegate_access)
    
    context = {
        'member': member,
        'delegate_access': delegate_access,
        'form': form,
        'action': 'edit'
    }
    return render(request, 'accounts/member_delegate_form.html', context)


@login_required
def member_delegate_revoke(request, delegate_id):
    """
    Revoke delegate access by marking it as inactive.
    
    This is a soft delete - the record is preserved for audit purposes.
    
    URL: POST /accounts/delegates/{delegate_id}/revoke/
    """
    
    current_user = request.user
    delegate_access = get_object_or_404(DelegateAccess, id=delegate_id)
    member = delegate_access.member
    
    # PERMISSION CHECK
    if not can_edit_member_profile(current_user):
        messages.error(request, 'Permission denied')
        return redirect('home')
    
    if request.method == 'POST':
        try:
            delegate_name = delegate_access.delegate.get_full_name()
            delegate_access.is_active = False
            delegate_access.save()
            
            # LOG THE CHANGE
            AuditLog.objects.create(
                user=current_user,
                action='delegate_access_revoked',
                resource_type='member',
                resource_id=member.id,
                details={
                    'member_name': member.get_full_name(),
                    'delegate_name': delegate_name,
                    'permission_level': delegate_access.permission_level
                }
            )
            
            messages.success(
                request,
                f'Access for {delegate_name} has been revoked.'
            )
            
        except Exception as e:
            messages.error(request, f'Error revoking access: {str(e)}')
    
    return redirect('member_profile_edit', member_id=member.id)


@login_required
def member_credit_allowance_edit(request, member_id, fiscal_year, quarter):
    """
    Edit quarterly credit allowance for a member.
    
    Allows Benefits Technicians to configure how many cases a member can submit
    in a given quarter.
    
    Future enhancement: This could be synced from WP product/membership tier.
    
    URL: /accounts/members/{member_id}/credits/{fiscal_year}/q{quarter}/edit/
    """
    
    current_user = request.user
    member = get_object_or_404(User, id=member_id, role='member')
    
    # PERMISSION CHECK
    if not can_edit_member_profile(current_user):
        messages.error(request, 'Permission denied')
        return redirect('home')
    
    # Get or create the credit allowance for this quarter
    allowance, created = MemberCreditAllowance.objects.get_or_create(
        member=member,
        fiscal_year=fiscal_year,
        quarter=quarter,
        defaults={
            'allowed_credits': 100,
            'configured_by': current_user
        }
    )
    
    if request.method == 'POST':
        old_credits = allowance.allowed_credits
        
        form = MemberCreditAllowanceForm(
            member,
            fiscal_year,
            quarter,
            request.POST,
            instance=allowance,
            changed_by_user=current_user
        )
        
        if form.is_valid():
            try:
                updated_allowance = form.save()
                
                # LOG THE CHANGE
                AuditLog.objects.create(
                    user=current_user,
                    action='credit_allowance_updated',
                    resource_type='member',
                    resource_id=member.id,
                    details={
                        'member_name': member.get_full_name(),
                        'fiscal_year': fiscal_year,
                        'quarter': quarter,
                        'old_credits': old_credits,
                        'new_credits': updated_allowance.allowed_credits,
                        'notes': updated_allowance.notes
                    }
                )
                
                messages.success(
                    request,
                    f'Credit allowance for FY{fiscal_year} Q{quarter} has been updated.'
                )
                
                return redirect('member_profile_edit', member_id=member.id)
                
            except Exception as e:
                messages.error(request, f'Error updating credit allowance: {str(e)}')
    else:
        form = MemberCreditAllowanceForm(member, fiscal_year, quarter, instance=allowance)
    
    context = {
        'member': member,
        'allowance': allowance,
        'form': form,
        'fiscal_year': fiscal_year,
        'quarter': quarter,
    }
    return render(request, 'accounts/member_credit_allowance_form.html', context)


# ============================================================================
# WORKSHOP DELEGATE MANAGEMENT VIEWS
# ============================================================================
# These views allow Benefits Technicians and Admins to assign delegates to
# workshop codes. Delegates can submit cases on behalf of ANY member in
# that workshop.
# ============================================================================


def can_manage_workshop_delegates(user):
    """Check if user can manage workshop delegates."""
    return user.is_authenticated and user.role in ['technician', 'administrator']


@login_required
def workshop_delegate_list(request):
    """
    List all workshop delegate assignments.
    
    Technicians/Admins can view, edit, and revoke delegate assignments.
    Supports filtering by workshop code and delegate status.
    
    URL: /accounts/workshop-delegates/
    """
    current_user = request.user
    
    # PERMISSION CHECK
    if not can_manage_workshop_delegates(current_user):
        messages.error(request, 'You do not have permission to manage workshop delegates.')
        return redirect('home')
    
    # Get all active delegates
    delegates = WorkshopDelegate.objects.filter(is_active=True).select_related('delegate', 'granted_by')
    
    # Optional filters
    workshop_filter = request.GET.get('workshop_code', '').strip().upper()
    status_filter = request.GET.get('status', 'active')
    
    if workshop_filter:
        delegates = delegates.filter(workshop_code=workshop_filter)
    
    if status_filter == 'inactive':
        delegates = WorkshopDelegate.objects.filter(is_active=False).select_related('delegate', 'granted_by')
    elif status_filter == 'all':
        delegates = WorkshopDelegate.objects.all().select_related('delegate', 'granted_by')
    
    # Get unique workshop codes for filter dropdown
    workshop_codes = WorkshopDelegate.objects.filter(
        is_active=True
    ).values_list('workshop_code', flat=True).distinct().order_by('workshop_code')
    
    context = {
        'delegates': delegates,
        'workshop_codes': workshop_codes,
        'workshop_filter': workshop_filter,
        'status_filter': status_filter,
        'can_manage': can_manage_workshop_delegates(current_user),
    }
    
    return render(request, 'accounts/workshop_delegate_list.html', context)


@login_required
def workshop_delegate_add(request):
    """
    Add a new workshop delegate assignment.
    
    URL: /accounts/workshop-delegates/add/
    """
    current_user = request.user
    
    # PERMISSION CHECK
    if not can_manage_workshop_delegates(current_user):
        messages.error(request, 'You do not have permission to manage workshop delegates.')
        return redirect('home')
    
    if request.method == 'POST':
        form = WorkshopDelegateForm(
            request.POST,
            changed_by_user=current_user
        )
        
        if form.is_valid():
            try:
                delegate_access = form.save()
                
                # LOG THE CHANGE
                AuditLog.objects.create(
                    user=current_user,
                    action='workshop_delegate_assigned',
                    resource_type='workshop',
                    resource_id=None,
                    details={
                        'workshop_code': delegate_access.workshop_code,
                        'delegate_name': delegate_access.delegate.get_full_name(),
                        'permission_level': delegate_access.permission_level,
                        'reason': delegate_access.grant_reason
                    }
                )
                
                messages.success(
                    request,
                    f'{delegate_access.delegate.get_full_name()} has been assigned to workshop {delegate_access.workshop_code} '
                    f'with {delegate_access.permission_level} access.'
                )
                
                return redirect('workshop_delegate_list')
                
            except Exception as e:
                messages.error(request, f'Error adding delegate: {str(e)}')
    else:
        form = WorkshopDelegateForm(changed_by_user=current_user)
    
    context = {
        'form': form,
        'action': 'add'
    }
    return render(request, 'accounts/workshop_delegate_form.html', context)


@login_required
def workshop_delegate_edit(request, delegate_id):
    """
    Edit workshop delegate assignment.
    
    URL: /accounts/workshop-delegates/{delegate_id}/edit/
    """
    current_user = request.user
    delegate_access = get_object_or_404(WorkshopDelegate, id=delegate_id)
    
    # PERMISSION CHECK
    if not can_manage_workshop_delegates(current_user):
        messages.error(request, 'Permission denied')
        return redirect('home')
    
    if request.method == 'POST':
        old_permission = delegate_access.permission_level
        old_active = delegate_access.is_active
        old_workshop = delegate_access.workshop_code
        
        form = WorkshopDelegateForm(
            request.POST,
            instance=delegate_access,
            changed_by_user=current_user
        )
        
        if form.is_valid():
            try:
                updated_access = form.save()
                
                # LOG THE CHANGE
                changes = {}
                if old_permission != updated_access.permission_level:
                    changes['permission_level'] = {
                        'old': old_permission,
                        'new': updated_access.permission_level
                    }
                if old_active != updated_access.is_active:
                    changes['is_active'] = {
                        'old': old_active,
                        'new': updated_access.is_active
                    }
                if old_workshop != updated_access.workshop_code:
                    changes['workshop_code'] = {
                        'old': old_workshop,
                        'new': updated_access.workshop_code
                    }
                
                AuditLog.objects.create(
                    user=current_user,
                    action='workshop_delegate_modified',
                    resource_type='workshop',
                    resource_id=None,
                    details={
                        'workshop_code': updated_access.workshop_code,
                        'delegate_name': updated_access.delegate.get_full_name(),
                        'changes': changes
                    }
                )
                
                messages.success(request, 'Workshop delegate assignment has been updated.')
                return redirect('workshop_delegate_list')
                
            except Exception as e:
                messages.error(request, f'Error updating delegate: {str(e)}')
    else:
        form = WorkshopDelegateForm(instance=delegate_access, changed_by_user=current_user)
    
    context = {
        'delegate_access': delegate_access,
        'form': form,
        'action': 'edit'
    }
    return render(request, 'accounts/workshop_delegate_form.html', context)


@login_required
def workshop_delegate_revoke(request, delegate_id):
    """
    Revoke workshop delegate access.
    
    URL: POST /accounts/workshop-delegates/{delegate_id}/revoke/
    """
    current_user = request.user
    delegate_access = get_object_or_404(WorkshopDelegate, id=delegate_id)
    
    # PERMISSION CHECK
    if not can_manage_workshop_delegates(current_user):
        messages.error(request, 'Permission denied')
        return redirect('home')
    
    if request.method == 'POST':
        try:
            delegate_name = delegate_access.delegate.get_full_name()
            workshop_code = delegate_access.workshop_code
            delegate_access.is_active = False
            delegate_access.save()
            
            # LOG THE CHANGE
            AuditLog.objects.create(
                user=current_user,
                action='workshop_delegate_revoked',
                resource_type='workshop',
                resource_id=None,
                details={
                    'workshop_code': workshop_code,
                    'delegate_name': delegate_name,
                    'permission_level': delegate_access.permission_level
                }
            )
            
            messages.success(
                request,
                f'Access for {delegate_name} in workshop {workshop_code} has been revoked.'
            )
            
        except Exception as e:
            messages.error(request, f'Error revoking access: {str(e)}')
    
    return redirect('workshop_delegate_list')
