from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import ensure_csrf_cookie
from django.contrib import messages
from django.urls import reverse
from .models import SystemSettings


def is_admin(user):
    """Helper function to check if user is admin"""
    return user.is_authenticated and user.role == 'administrator'


def home(request):
    """Home page - redirects based on authentication and role"""
    if request.user.is_authenticated:
        # Redirect based on role
        if request.user.role == 'member':
            return redirect('cases:member_dashboard')
        elif request.user.role == 'technician':
            return redirect('cases:technician_dashboard')
        elif request.user.role == 'manager':
            return redirect('cases:manager_dashboard')
        elif request.user.role == 'administrator':
            return redirect('cases:admin_dashboard')
    
    return render(request, 'core/home.html')


@ensure_csrf_cookie
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
            # messages.success(request, f'Welcome back, {user.get_full_name() or user.username}!')
            
            # Get next URL or redirect based on role
            next_url = request.GET.get('next')
            if next_url:
                return redirect(next_url)
            
            # Role-based redirect
            if user.role == 'member':
                return redirect('cases:member_dashboard')
            elif user.role == 'technician':
                return redirect('cases:technician_dashboard')
            elif user.role == 'manager':
                return redirect('cases:manager_dashboard')
            elif user.role == 'administrator':
                return redirect('cases:admin_dashboard')
            
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


@login_required
def system_settings(request):
    """System settings management page - Admin only"""
    if not is_admin(request.user):
        messages.error(request, 'Access denied. Administrators only.')
        return redirect('home')
    
    settings = SystemSettings.get_settings()
    
    if request.method == 'POST':
        # Handle form submission
        try:
            # Credits
            settings.available_credits = request.POST.get('available_credits', '0.5,1.0,1.5,2.0,2.5,3.0')
            
            # Default Case Settings
            settings.default_case_due_days = int(request.POST.get('default_case_due_days', 7))
            settings.rush_case_threshold_days = int(request.POST.get('rush_case_threshold_days', 7))
            
            # Release Settings
            settings.enable_scheduled_releases = request.POST.get('enable_scheduled_releases') == 'on'
            settings.default_completion_delay_hours = int(request.POST.get('default_completion_delay_hours', 0))
            settings.batch_release_time = request.POST.get('batch_release_time', '09:00')
            settings.batch_release_enabled = request.POST.get('batch_release_enabled') == 'on'
            
            # Email Settings
            settings.enable_delayed_email_notifications = request.POST.get('enable_delayed_email_notifications') == 'on'
            settings.default_email_delay_hours = int(request.POST.get('default_email_delay_hours', 0))
            settings.batch_email_enabled = request.POST.get('batch_email_enabled') == 'on'
            settings.reply_email_address = request.POST.get('reply_email_address', 'reports@profeds.com')
            
            # API Configuration
            settings.benefits_software_api_url = request.POST.get('benefits_software_api_url', '')
            settings.benefits_software_api_key = request.POST.get('benefits_software_api_key', '')
            settings.benefits_software_api_enabled = request.POST.get('benefits_software_api_enabled') == 'on'
            
            settings.updated_by = request.user
            settings.save()
            
            messages.success(request, 'System settings updated successfully!')
            return redirect('system_settings')
        except (ValueError, Exception) as e:
            messages.error(request, f'Error updating settings: {str(e)}')
    
    context = {
        'settings': settings,
    }
    
    return render(request, 'core/system_settings.html', context)


@login_required
def update_font_size(request):
    """Update user's font size preference"""
    if request.method == 'POST':
        font_size = request.POST.get('font_size', '100')
        
        # Validate font size
        valid_sizes = ['75', '85', '100', '115', '130', '150']
        if font_size in valid_sizes:
            request.user.font_size = font_size
            request.user.save()
            # Update the session to ensure the change is reflected immediately
            update_session_auth_hash(request, request.user)
            messages.success(request, f'Font size updated to {font_size}%')
            # Add a response that includes JavaScript to update localStorage
            response = redirect('profile')
            # Store in session as well for immediate availability
            request.session['user_font_size'] = font_size
            request.session.modified = True
            return response
        else:
            messages.error(request, 'Invalid font size value')
    
    return redirect('profile')
