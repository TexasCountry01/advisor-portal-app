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
from .ghl_client import fetch_ghl_contacts
from .sso import determine_role_from_tags
from core.models import AuditLog
from cases.services.email_service import send_delegate_assigned_email, send_delegate_removed_email

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
    - Administrator: Can create Administrator, Technician, Manager, and Member users
    - Technician: Can create Member users
    - Others: Cannot create users
    """
    if not current_user.is_authenticated:
        return False
    
    if current_user.role == 'administrator':
        # Admin can create admins, techs, managers, and members
        return target_role in ['administrator', 'technician', 'manager', 'member']
    
    if current_user.role == 'technician':
        # Tech can create members
        return target_role == 'member'
    
    return False


def can_edit_user(current_user, target_user):
    """
    Determine if current user can edit target_user.
    
    Rules:
    - Administrator: Can edit Administrator, Technician, Manager, and Member users
    - Technician: Can edit Member users
    - Users can edit their own profile
    """
    if not current_user.is_authenticated:
        return False
    
    # Users can always edit themselves
    if current_user.id == target_user.id:
        return True
    
    if current_user.role == 'administrator':
        # Admin can edit admins, techs, managers, and members
        return target_user.role in ['administrator', 'technician', 'manager', 'member']
    
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
        # Pre-fill from GHL Sync Review "Provision" link, if present.
        # This lets the admin assign a role now using the immutable contact_id,
        # so the real first SSO login matches this record instantly — no impersonation needed.
        initial = {}
        if request.GET.get('contact_id'):
            initial = {
                'contact_id': request.GET.get('contact_id', ''),
                'email': request.GET.get('email', ''),
                'first_name': request.GET.get('first_name', ''),
                'last_name': request.GET.get('last_name', ''),
                'workshop_code': request.GET.get('workshop_code', ''),
                'username': (request.GET.get('email', '').split('@')[0] or ''),
            }
            ghl_role = request.GET.get('role', '')
            if ghl_role in dict(User.ROLE_CHOICES):
                initial['role'] = ghl_role
            messages.info(
                request,
                'Pre-filled from GHL. Set a role and password, then save — '
                'the user will be matched automatically on their first login.'
            )
        form = UserCreationForm(current_user=current_user, initial=initial)
    
    # Get users based on current user's role
    if current_user.role == 'administrator':
        # Admin sees all users (administrators, technicians, managers, and members)
        users = User.objects.filter(role__in=['administrator', 'technician', 'manager', 'member']).order_by('-created_at')
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
def sync_ghl_contacts(request):
    """Hybrid provisioning: pull GHL contacts for admin review without overriding app role assignment."""
    if request.user.role != 'administrator':
        messages.error(request, 'Only administrators can sync from GHL.')
        return redirect('manage_users')

    try:
        raw_contacts = fetch_ghl_contacts(limit=100, max_total=1000)
    except Exception as exc:
        messages.error(request, f'GHL sync failed: {exc}')
        return redirect('manage_users')

    # Only contacts with a portal access tag are relevant for provisioning —
    # everything else is generic CRM/marketing noise. Reuses the same tag
    # matching logic as SSO login so results are always consistent.
    contacts = []
    for contact in raw_contacts:
        role, is_pure_delegate, has_access = determine_role_from_tags(contact.get('tags', []))
        if has_access:
            contact['ghl_role'] = role
            contact['is_pure_delegate'] = is_pure_delegate
            contacts.append(contact)

    matched = []
    unmatched = []

    for contact in contacts:
        contact_id = contact.get('contact_id')
        email = contact.get('email')
        portal_user = None
        if contact_id:
            portal_user = User.objects.filter(contact_id=contact_id).first()
        if not portal_user and email:
            portal_user = User.objects.filter(email__iexact=email).first()

        row = {
            'contact_id': contact_id,
            'name': f"{contact.get('first_name', '').strip()} {contact.get('last_name', '').strip()}".strip() or 'Unknown',
            'first_name': contact.get('first_name', ''),
            'last_name': contact.get('last_name', ''),
            'email': email,
            'workshop_code': contact.get('workshop_code', ''),
            'tags': ', '.join(contact.get('tags', [])[:10]) or '—',
            'ghl_role': contact.get('ghl_role'),
            'portal_user': portal_user,
            'portal_role': portal_user.role if portal_user else None,
            'needs_link': bool(portal_user and not portal_user.contact_id and contact_id),
        }

        if portal_user:
            matched.append(row)
        else:
            unmatched.append(row)

    context = {
        'matched': matched,
        'unmatched': unmatched,
        'total_contacts': len(contacts),
        'matched_count': len(matched),
        'unmatched_count': len(unmatched),
        'current_user_role': request.user.role,
    }
    return render(request, 'accounts/ghl_sync.html', context)


@login_required
def link_ghl_contact(request, user_id):
    """Backfill contact_id on an existing portal user matched via email fallback.
    Does NOT change role or any other field — just links the immutable GHL ID
    so future logins match reliably instead of relying on email.
    """
    if request.user.role != 'administrator':
        messages.error(request, 'Only administrators can link GHL contacts.')
        return redirect('manage_users')

    if request.method != 'POST':
        return redirect('sync_ghl_contacts')

    contact_id = (request.POST.get('contact_id') or '').strip()
    if not contact_id:
        messages.error(request, 'Missing contact ID.')
        return redirect('sync_ghl_contacts')

    target_user = get_object_or_404(User, id=user_id)

    if target_user.contact_id:
        messages.error(request, f'{target_user.get_full_name()} is already linked to a GHL contact.')
        return redirect('sync_ghl_contacts')

    if User.objects.filter(contact_id=contact_id).exclude(id=target_user.id).exists():
        messages.error(request, 'This GHL contact is already linked to a different portal user.')
        return redirect('sync_ghl_contacts')

    target_user.contact_id = contact_id
    target_user.save(update_fields=['contact_id'])

    AuditLog.objects.create(
        user=request.user,
        action_type='ghl_link',
        description=f'Linked GHL contact {contact_id} to existing user {target_user.get_full_name()} ({target_user.email})',
        related_user=target_user,
        metadata={'contact_id': contact_id},
    )
    messages.success(request, f'Linked {target_user.get_full_name()} to their GHL contact.')
    return redirect('sync_ghl_contacts')


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


@login_required
def edit_user_role(request, user_id):
    """Edit a user's role and level. Administrator-only."""
    
    current_user = request.user
    target_user = get_object_or_404(User, id=user_id)
    
    # Only administrators can change roles
    if current_user.role != 'administrator':
        messages.error(request, 'Only administrators can change user roles.')
        return redirect('manage_users')
    
    # Prevent editing yourself (to avoid locking yourself out)
    if current_user.id == target_user.id:
        messages.error(request, 'You cannot change your own role.')
        return redirect('manage_users')
    
    if request.method == 'POST':
        new_role = request.POST.get('role', '').strip()
        new_level = request.POST.get('user_level', '').strip()
        
        # Validate role
        valid_roles = [r[0] for r in User.ROLE_CHOICES]
        if new_role not in valid_roles:
            messages.error(request, f'Invalid role: {new_role}')
            return redirect('manage_users')
        
        old_role = target_user.role
        old_level = target_user.user_level
        changes = []
        
        # Update role
        if new_role != old_role:
            target_user.role = new_role
            changes.append(f'role: {old_role} → {new_role}')
            
            # Set staff/superuser flags for admin role
            if new_role == 'administrator':
                target_user.is_staff = True
                target_user.is_superuser = True
            elif old_role == 'administrator':
                # Demoting from admin — remove staff/superuser
                target_user.is_staff = False
                target_user.is_superuser = False
        
        # Update technician level
        if new_role == 'technician':
            valid_levels = [l[0] for l in User.USER_LEVEL_CHOICES]
            if new_level in valid_levels and new_level != old_level:
                target_user.user_level = new_level
                changes.append(f'level: {old_level or "none"} → {new_level}')
            
            # Update staff permissions (only for technicians)
            new_can_manage_review = request.POST.get('can_manage_review_settings') == 'on'
            new_can_manage_delegates = request.POST.get('can_manage_delegates') == 'on'
            
            if target_user.can_manage_review_settings != new_can_manage_review:
                target_user.can_manage_review_settings = new_can_manage_review
                changes.append(f'can_manage_review_settings: {"on" if new_can_manage_review else "off"}')
            if target_user.can_manage_delegates != new_can_manage_delegates:
                target_user.can_manage_delegates = new_can_manage_delegates
                changes.append(f'can_manage_delegates: {"on" if new_can_manage_delegates else "off"}')
        elif target_user.user_level:
            # Clear level and permissions if no longer a technician
            changes.append(f'level: {target_user.user_level} → cleared')
            target_user.user_level = ''
            if target_user.can_manage_review_settings:
                target_user.can_manage_review_settings = False
                changes.append('can_manage_review_settings: off')
            if target_user.can_manage_delegates:
                target_user.can_manage_delegates = False
                changes.append('can_manage_delegates: off')
        
        if changes:
            target_user.save()
            username = target_user.get_full_name() or target_user.username
            messages.success(
                request,
                f'Updated {username}: {", ".join(changes)}'
            )
        else:
            messages.info(request, 'No changes made.')
    
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


# ==========================================================================
# DEPRECATED: DelegateAccess-based views below
# Replaced by MemberDelegate model + delegate_management() view.
# URL routes have been commented out. Code kept for reference/migration.
# ==========================================================================

@login_required
def member_delegate_add(request, member_id):
    """
    DEPRECATED — Replaced by delegate_management() view.
    Uses old DelegateAccess model. URL route disabled.
    
    Add a new delegate for a member.
    
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
    DEPRECATED — Replaced by delegate_management() view.
    Uses old DelegateAccess model. URL route disabled.
    
    Edit delegate access permissions.
    
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
    DEPRECATED — Replaced by delegate_management() view.
    Uses old DelegateAccess model. URL route disabled.
    
    Revoke delegate access by marking it as inactive.
    
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
# DELEGATE MANAGEMENT VIEW (Member-to-Delegate assignments)
# ============================================================================
# Benefits Technicians assign delegates to members.
# Rules:
# - Any member can be a delegate for any other member
# - A delegate can be assigned to multiple members
# - No delegate can be a delegate of another delegate (no chaining)
# - Only Benefits Technicians can assign delegates
# - Delegate must have an existing portal account
# ============================================================================

@login_required
def delegate_management(request):
    """Delegate management page for Benefits Technicians — assign delegates to members."""
    user = request.user
    
    # Permission check
    if user.role in ('administrator', 'manager'):
        pass  # Always allowed
    elif user.role == 'technician' and user.can_manage_delegates:
        pass  # Explicitly granted
    elif user.role == 'technician':
        messages.error(request, 'You do not have permission to manage delegates. Contact an administrator to grant access.')
        return redirect('cases:technician_dashboard')
    else:
        messages.error(request, 'You do not have permission to manage delegates.')
        return redirect('cases:member_dashboard')
    
    User = get_user_model()

    # Single query for all active members — reused for both dropdowns
    all_members = list(User.objects.filter(
        role='member', is_active=True
    ).order_by('workshop_code', 'last_name', 'first_name'))
    
    # Get existing delegate assignments from MemberDelegate model
    from accounts.models import MemberDelegate
    assignments_qs = MemberDelegate.objects.select_related(
        'delegate', 'member', 'assigned_by'
    ).all().order_by('member__workshop_code', 'member__last_name', 'member__first_name')
    
    # Apply GET filters
    member_filter = request.GET.get('member', '')
    delegate_filter = request.GET.get('delegate', '')
    if member_filter:
        assignments_qs = assignments_qs.filter(member_id=member_filter)
    if delegate_filter:
        assignments_qs = assignments_qs.filter(delegate_id=delegate_filter)
    
    # Build assignment data for template
    assignments = []
    for a in assignments_qs:
        assignments.append({
            'id': a.id,
            'member_name': f'{a.member.first_name} {a.member.last_name}',
            'member_email': a.member.email,
            'workshop_code': a.member.workshop_code,
            'delegate_name': f'{a.delegate.first_name} {a.delegate.last_name}',
            'delegate_email': a.delegate.email,
            'delegate_is_also_member': not a.delegate.is_pure_delegate,
            'assigned_by': a.assigned_by.get_full_name() if a.assigned_by else '—',
            'assigned_date': a.created_at.strftime('%b %d, %Y') if a.created_at else '—',
            'email_notifications': a.email_notifications,
            'portal_notifications': a.portal_notifications,
        })
    
    # Handle POST — assign or remove delegates
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'assign':
            member_id = request.POST.get('member_id')
            delegate_id = request.POST.get('delegate_id')
            
            if member_id and delegate_id:
                try:
                    member = User.objects.get(id=member_id, role='member')
                    delegate_user = User.objects.get(id=delegate_id)
                    
                    if member.id == delegate_user.id:
                        messages.error(request, 'A member cannot be their own delegate.')
                    elif MemberDelegate.objects.filter(member=member, delegate=delegate_user).exists():
                        messages.warning(request, f'{delegate_user.get_full_name()} is already a delegate for {member.get_full_name()}.')
                    else:
                        MemberDelegate.objects.create(
                            member=member,
                            delegate=delegate_user,
                            assigned_by=user
                        )
                        messages.success(request, f'{delegate_user.get_full_name()} assigned as delegate for {member.get_full_name()}.')
                        
                        # Audit log
                        AuditLog.objects.create(
                            user=user,
                            action_type='delegate_assigned',
                            description=f'{user.get_full_name()} assigned {delegate_user.get_full_name()} as delegate for {member.get_full_name()}',
                            related_user=delegate_user,
                            changes={
                                'member_id': member.id,
                                'member_name': member.get_full_name(),
                                'member_email': member.email,
                                'delegate_id': delegate_user.id,
                                'delegate_name': delegate_user.get_full_name(),
                                'delegate_email': delegate_user.email,
                            },
                            ip_address=request.META.get('REMOTE_ADDR'),
                        )
                        
                        # Email notification to member
                        send_delegate_assigned_email(member, delegate_user, user)
                except User.DoesNotExist:
                    messages.error(request, 'Invalid member or delegate selected.')
            else:
                messages.error(request, 'Both member and delegate are required.')
            
            return redirect('delegate_management')
        
        elif action == 'remove':
            assignment_id = request.POST.get('assignment_id')
            try:
                assignment = MemberDelegate.objects.get(id=assignment_id)
                delegate_name = assignment.delegate.get_full_name()
                member_name = assignment.member.get_full_name()
                
                # Audit log before delete
                AuditLog.objects.create(
                    user=user,
                    action_type='delegate_removed',
                    description=f'{user.get_full_name()} removed {delegate_name} as delegate for {member_name}',
                    related_user=assignment.delegate,
                    changes={
                        'member_id': assignment.member.id,
                        'member_name': member_name,
                        'member_email': assignment.member.email,
                        'delegate_id': assignment.delegate.id,
                        'delegate_name': delegate_name,
                        'delegate_email': assignment.delegate.email,
                    },
                    ip_address=request.META.get('REMOTE_ADDR'),
                )
                
                # Email notification to member
                member_obj = assignment.member
                delegate_obj = assignment.delegate
                
                assignment.delete()
                messages.success(request, f'Removed {delegate_name} as delegate for {member_name}.')
                
                send_delegate_removed_email(member_obj, delegate_obj, user)
            except MemberDelegate.DoesNotExist:
                messages.error(request, 'Assignment not found.')
            
            return redirect('delegate_management')
    
    # Stats
    unique_delegates = set(a['delegate_name'] for a in assignments)
    unique_members = set(a['member_name'] for a in assignments)
    
    context = {
        'assignments': assignments,
        'all_members': all_members,
        'all_possible_delegates': all_members,  # same list, no second query
        'total_assignments': len(assignments),
        'total_delegates': len(unique_delegates),
        'total_members_with_delegates': len(unique_members),
        'total_members': len(all_members),  # len() — list already in memory, no COUNT query
    }
    
    return render(request, 'accounts/delegate_management.html', context)


@login_required
def clear_delegate_request(request, request_id):
    """Dismiss a pending delegate request from the admin dashboard banner."""
    from django.utils import timezone
    from core.models import AuditLog
    from accounts.models import DelegateRequest

    if request.method != 'POST':
        return redirect('cases:admin_dashboard')

    if request.user.role not in ['administrator', 'manager'] and not (
        request.user.role == 'technician' and request.user.can_manage_delegates
    ):
        messages.error(request, 'You do not have permission to clear delegate requests.')
        return redirect('cases:admin_dashboard')

    delegate_request = get_object_or_404(DelegateRequest, pk=request_id)
    delegate_request.status = 'dismissed'
    delegate_request.processed_by = request.user
    delegate_request.processed_at = timezone.now()
    delegate_request.save(update_fields=['status', 'processed_by', 'processed_at'])

    AuditLog.objects.create(
        user=request.user,
        action_type='alert_dismissed',
        description=(
            f'{request.user.get_full_name()} dismissed pending delegate request for '
            f'{delegate_request.requested_by.get_full_name()} to {delegate_request.get_request_type_display().lower()} '
            f'{delegate_request.delegate_name}.'
        ),
        related_user=delegate_request.requested_by,
        ip_address=request.META.get('REMOTE_ADDR'),
        metadata={
            'delegate_request_id': delegate_request.pk,
            'member_id': delegate_request.requested_by.pk,
            'delegate_name': delegate_request.delegate_name,
            'status': 'dismissed',
        },
    )

    messages.info(request, 'Delegate request cleared from the banner.')
    return redirect('cases:admin_dashboard')


@login_required
def toggle_delegate_email(request, assignment_id):
    """AJAX endpoint to toggle email or portal notifications for a delegate assignment."""
    from django.http import JsonResponse
    from accounts.models import MemberDelegate

    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    if request.user.role not in ('technician', 'administrator', 'manager'):
        return JsonResponse({'error': 'Permission denied'}, status=403)

    try:
        assignment = MemberDelegate.objects.select_related('delegate', 'member').get(id=assignment_id)
    except MemberDelegate.DoesNotExist:
        return JsonResponse({'error': 'Assignment not found'}, status=404)

    field = request.POST.get('field', 'email_notifications')
    if field not in ('email_notifications', 'portal_notifications'):
        return JsonResponse({'error': 'Invalid field'}, status=400)

    current_value = getattr(assignment, field)
    setattr(assignment, field, not current_value)
    assignment.save(update_fields=[field])

    label = 'email' if field == 'email_notifications' else 'portal'
    new_value = getattr(assignment, field)

    AuditLog.objects.create(
        user=request.user,
        action_type='delegate_alert_toggled',
        description=(
            f'{request.user.get_full_name()} {"enabled" if new_value else "disabled"} '
            f'{label} notifications for delegate {assignment.delegate.get_full_name()} '
            f'on member {assignment.member.get_full_name()}'
        ),
        related_user=assignment.delegate,
        changes={
            'assignment_id': assignment.id,
            'member_name': assignment.member.get_full_name(),
            'delegate_name': assignment.delegate.get_full_name(),
            'field': field,
            field: new_value,
        },
        ip_address=request.META.get('REMOTE_ADDR'),
    )

    return JsonResponse({field: new_value})


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


# ==========================================================================
# DEPRECATED: WorkshopDelegate-based views below
# Replaced by MemberDelegate model + delegate_management() view.
# URL routes have been commented out. Code kept for reference/migration.
# ==========================================================================

@login_required
def workshop_delegate_list(request):
    """
    DEPRECATED — Replaced by delegate_management() view.
    Uses old WorkshopDelegate model. URL route disabled.
    
    List all workshop delegate assignments.
    
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
    DEPRECATED — Replaced by delegate_management() view.
    Uses old WorkshopDelegate model. URL route disabled.
    
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
    DEPRECATED — Replaced by delegate_management() view.
    Uses old WorkshopDelegate model. URL route disabled.
    
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
    DEPRECATED — Replaced by delegate_management() view.
    Uses old WorkshopDelegate model. URL route disabled.
    
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
