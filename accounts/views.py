from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from .forms import UserCreationForm

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
    - Super Admin: Can create Technician and Manager users
    - Technician: Can create Member users
    - Others: Cannot create users
    """
    if not current_user.is_authenticated:
        return False
    
    if current_user.role == 'administrator':
        # Admin can create techs and managers
        return target_role in ['technician', 'manager']
    
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
        # Admin sees all technicians and managers
        users = User.objects.filter(role__in=['technician', 'manager']).order_by('-created_at')
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
