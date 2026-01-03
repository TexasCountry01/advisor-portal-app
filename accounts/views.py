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


@login_required
def manage_users(request):
    """Manage users - create and delete. Admin only."""
    
    # Check if user is admin
    if not is_admin(request.user):
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('home')
    
    # Handle form submission
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
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
        form = UserCreationForm()
    
    # Get all users sorted by date created (newest first)
    users = User.objects.all().order_by('-created_at')
    
    context = {
        'form': form,
        'users': users,
    }
    
    return render(request, 'accounts/manage_users.html', context)


@login_required
def delete_user(request, user_id):
    """Delete a user. Admin only."""
    
    # Check if user is admin
    if not is_admin(request.user):
        messages.error(request, 'You do not have permission to delete users.')
        return redirect('home')
    
    # Prevent admin from deleting themselves
    user_to_delete = get_object_or_404(User, id=user_id)
    
    if request.user.id == user_to_delete.id:
        messages.error(request, 'You cannot delete your own account.')
        return redirect('manage_users')
    
    username = user_to_delete.get_full_name() or user_to_delete.username
    user_to_delete.delete()
    messages.success(request, f'User {username} has been deleted.')
    
    return redirect('manage_users')
