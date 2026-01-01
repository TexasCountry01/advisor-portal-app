from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse


def home(request):
    """Home page - redirects based on authentication and role"""
    if request.user.is_authenticated:
        # Redirect based on role
        if request.user.role == 'member':
            return redirect('member_dashboard')
        elif request.user.role == 'technician':
            return redirect('technician_dashboard')
        elif request.user.role == 'manager':
            return redirect('manager_dashboard')
        elif request.user.role == 'administrator':
            return redirect('admin_dashboard')
    
    return render(request, 'core/home.html')


def login_view(request):
    """Custom login view with role-based redirects"""
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            messages.success(request, f'Welcome back, {user.get_full_name() or user.username}!')
            
            # Get next URL or redirect based on role
            next_url = request.GET.get('next')
            if next_url:
                return redirect(next_url)
            
            # Role-based redirect
            if user.role == 'member':
                return redirect('member_dashboard')
            elif user.role == 'technician':
                return redirect('technician_dashboard')
            elif user.role == 'manager':
                return redirect('manager_dashboard')
            elif user.role == 'administrator':
                return redirect('admin_dashboard')
            
            return redirect('home')
        else:
            messages.error(request, 'Invalid username or password.')
    
    return render(request, 'core/login.html')


def logout_view(request):
    """Logout view"""
    logout(request)
    messages.info(request, 'You have been logged out successfully.')
    return redirect('home')


@login_required
def profile(request):
    """User profile page"""
    return render(request, 'core/profile.html', {
        'user': request.user
    })

