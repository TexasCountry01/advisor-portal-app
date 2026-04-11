from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import ensure_csrf_cookie
from django.contrib import messages
from django.urls import reverse
from django.http import JsonResponse
from .models import SystemSettings, BetaFeedback
import logging

logger = logging.getLogger(__name__)


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
    
    # Unauthenticated users go to login page (has both SSO button + credentials form)
    return redirect('login')


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
    
    # Build full SSO login URL for the "Switch WordPress account" link
    sso_redirect_url = request.build_absolute_uri(reverse('sso_login'))
    return render(request, 'core/login.html', {'sso_redirect_url': sso_redirect_url})


def logout_view(request):
    """Logout view"""
    logout(request)
    messages.info(request, 'You have been logged out successfully.')
    return redirect('login')


@login_required
def profile(request):
    """
    User profile page — shows profile info + notification alert settings.

    Members see:
      1. Their own alert settings (email on/off, in-app on/off)
      2. Members they are a delegate for (per-assignment email/in-app toggles)
      3. Their current delegates (read-only list)

    Pure delegates see:
      1. Members they are a delegate for (per-assignment email/in-app toggles)
    """
    user = request.user

    delegate_for_assignments = []   # MemberDelegate rows where this user IS the delegate
    my_delegates = []               # MemberDelegate rows where this user IS the member

    if user.role == 'member' or getattr(user, 'is_pure_delegate', False):
        from accounts.models import MemberDelegate

        # Members this user delegates FOR (they act on behalf of these members)
        delegate_for_assignments = list(
            MemberDelegate.objects.filter(delegate=user).select_related('member')
        )

        # This member's own delegates (read-only display)
        if user.role == 'member' and not getattr(user, 'is_pure_delegate', False):
            my_delegates = list(
                MemberDelegate.objects.filter(member=user).select_related('delegate')
            )

    return render(request, 'core/profile.html', {
        'user': user,
        'delegate_for_assignments': delegate_for_assignments,
        'my_delegates': my_delegates,
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
            settings.available_credits = request.POST.get('available_credits', '0.0,0.5,1.0,1.5,2.0,2.5,3.0')
            
            # Default Case Settings
            settings.default_case_due_days = int(request.POST.get('default_case_due_days', 7))
            settings.rush_case_threshold_days = int(request.POST.get('rush_case_threshold_days', 7))
            
            # Release Settings
            settings.enable_scheduled_releases = request.POST.get('enable_scheduled_releases') == 'on'
            settings.default_completion_delay_hours = int(request.POST.get('default_completion_delay_hours', 0))
            batch_time_str = request.POST.get('batch_release_time', '09:00').strip()
            if batch_time_str:
                from datetime import time as dt_time
                parts = batch_time_str.split(':')
                settings.batch_release_time = dt_time(int(parts[0]), int(parts[1]))
            settings.batch_release_enabled = request.POST.get('batch_release_enabled') == 'on'
            
            # Email Settings
            settings.email_notifications_enabled = request.POST.get('email_notifications_enabled') == 'on'
            settings.enable_delayed_email_notifications = request.POST.get('enable_delayed_email_notifications') == 'on'
            settings.default_email_delay_hours = int(request.POST.get('default_email_delay_hours', 0))
            settings.batch_email_enabled = request.POST.get('batch_email_enabled') == 'on'
            settings.reply_email_address = request.POST.get('reply_email_address', 'reports@profeds.com')
            
            # API Configuration
            settings.benefits_software_api_url = request.POST.get('benefits_software_api_url', '')
            settings.benefits_software_api_key = request.POST.get('benefits_software_api_key', '')
            settings.benefits_software_api_enabled = request.POST.get('benefits_software_api_enabled') == 'on'
            
            # Technical Notes Template
            settings.technical_notes_template = request.POST.get('technical_notes_template', '')
            
            # Feedback Notification Emails
            settings.feedback_email_1 = request.POST.get('feedback_email_1', '').strip()
            settings.feedback_email_1_enabled = request.POST.get('feedback_email_1_enabled') == 'on'
            settings.feedback_email_2 = request.POST.get('feedback_email_2', '').strip()
            settings.feedback_email_2_enabled = request.POST.get('feedback_email_2_enabled') == 'on'
            
            settings.updated_by = request.user
            settings.save()
            
            messages.success(request, 'System settings updated successfully!')
            # Preserve the active tab after save
            active_tab = request.POST.get('active_tab', 'credits')
            return redirect(reverse('system_settings') + f'?tab={active_tab}')
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
            # Update database for persistence across logins
            request.user.font_size = font_size
            request.user.save()
            
            # Update session immediately so all pages show the change
            request.session['user_font_size'] = font_size
            request.session.modified = True
            
            # Update password hash to refresh session (handles password changes)
            update_session_auth_hash(request, request.user)
            
            messages.success(request, f'Font size updated to {font_size}%')
        else:
            messages.error(request, 'Invalid font size value')
    
    return redirect('profile')


@login_required
def update_notification_preferences(request):
    """
    Save the member's global email/in-app notification toggles.
    Two checkboxes: email_notifications_enabled, portal_notifications_enabled.
    Unchecked = absent from POST = disabled.
    """
    if request.method != 'POST':
        return redirect('profile')

    user = request.user
    user.email_notifications_enabled = request.POST.get('email_notifications_enabled') == '1'
    user.portal_notifications_enabled = request.POST.get('portal_notifications_enabled') == '1'
    user.save(update_fields=['email_notifications_enabled', 'portal_notifications_enabled'])

    messages.success(request, 'Alert settings saved.')
    return redirect('profile')


@login_required
def update_delegate_notifications(request):
    """
    Let a delegate toggle their own email/portal flags for a specific
    MemberDelegate assignment.  Accepts POST with:
        assignment_id  — the MemberDelegate PK
        email_notifications — '1' if checked
        portal_notifications — '1' if checked
    """
    if request.method != 'POST':
        return redirect('profile')

    from accounts.models import MemberDelegate

    assignment_id = request.POST.get('assignment_id')
    if not assignment_id:
        messages.error(request, 'Missing assignment.')
        return redirect('profile')

    try:
        assignment = MemberDelegate.objects.get(pk=assignment_id, delegate=request.user)
    except MemberDelegate.DoesNotExist:
        messages.error(request, 'Delegate assignment not found.')
        return redirect('profile')

    assignment.email_notifications = request.POST.get('email_notifications') == '1'
    assignment.portal_notifications = request.POST.get('portal_notifications') == '1'
    assignment.save(update_fields=['email_notifications', 'portal_notifications'])

    member_name = assignment.member.get_full_name() or assignment.member.username
    messages.success(request, f'Notification settings updated for {member_name}.')
    return redirect('profile')


@login_required
def submit_beta_feedback(request):
    """Handle beta feedback submissions via AJAX"""
    if request.method == 'POST':
        feedback_text = request.POST.get('feedback', '').strip()
        if feedback_text:
            BetaFeedback.objects.create(
                user=request.user,
                feedback=feedback_text
            )
            
            # Send feedback notification emails if configured
            _send_feedback_notification_emails(request.user, feedback_text)
            
            return JsonResponse({'success': True, 'message': 'Thank you for your feedback!'})
        return JsonResponse({'success': False, 'message': 'Please enter some feedback.'}, status=400)
    return JsonResponse({'success': False, 'message': 'Invalid request.'}, status=405)


def _send_feedback_notification_emails(user, feedback_text):
    """Send notification emails for new portal feedback based on system settings."""
    try:
        from django.core.mail import send_mail
        from django.template.loader import render_to_string
        from django.utils.html import strip_tags
        from django.conf import settings as django_settings
        from django.utils import timezone
        
        system_settings = SystemSettings.get_settings()
        
        recipients = []
        if system_settings.feedback_email_1 and system_settings.feedback_email_1_enabled:
            recipients.append(system_settings.feedback_email_1)
        if system_settings.feedback_email_2 and system_settings.feedback_email_2_enabled:
            recipients.append(system_settings.feedback_email_2)
        
        if not recipients:
            return
        
        site_url = getattr(django_settings, 'SITE_URL', 'https://portal.profeds.com')
        context = {
            'user_name': user.get_full_name() or user.username,
            'user_email': user.email,
            'feedback_text': feedback_text,
            'submitted_at': timezone.now().strftime('%B %d, %Y at %I:%M %p CST'),
            'feedback_report_url': f'{site_url}/reports/beta-feedback/',
        }
        
        html_message = render_to_string('emails/feedback_notification.html', context)
        text_message = strip_tags(html_message)
        
        for recipient in recipients:
            send_mail(
                subject='New Portal Feedback Submitted',
                message=text_message,
                from_email=django_settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient],
                html_message=html_message,
                fail_silently=True,
            )
        
        logger.info(f'Feedback notification emails sent to {recipients}')
    except Exception as e:
        logger.error(f'Failed to send feedback notification emails: {e}')
