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

    # Pending delegate requests for this member
    pending_delegate_requests = []
    if user.role == 'member' and not getattr(user, 'is_pure_delegate', False):
        from accounts.models import DelegateRequest
        pending_delegate_requests = list(
            DelegateRequest.objects.filter(requested_by=user, status='pending')
        )

    return render(request, 'core/profile.html', {
        'user': user,
        'delegate_for_assignments': delegate_for_assignments,
        'my_delegates': my_delegates,
        'pending_delegate_requests': pending_delegate_requests,
    })


@login_required
def system_settings(request):
    """System settings management page - Admin only"""
    if not is_admin(request.user):
        messages.error(request, 'Access denied. Administrators only.')
        return redirect('home')

    from core.models import Holiday
    from cases.utils_holidays import sync_federal_holidays
    from datetime import date as dt_date

    # Auto-sync federal holidays for current + next year on every page load
    # (get_or_create means it only writes rows that don't already exist)
    sync_federal_holidays()

    settings = SystemSettings.get_settings()

    if request.method == 'POST':
        action = request.POST.get('holiday_action', '')

        # --- Holiday CRUD actions ---
        if action == 'toggle_holiday':
            try:
                h = Holiday.objects.get(pk=int(request.POST.get('holiday_id')))
                h.active = not h.active
                h.save()
                messages.success(request, f'Holiday "{h.name}" {"enabled" if h.active else "disabled"}.')
            except (Holiday.DoesNotExist, ValueError):
                messages.error(request, 'Holiday not found.')
            active_tab = request.POST.get('active_tab', 'case-settings')
            return redirect(reverse('system_settings') + f'?tab={active_tab}')

        if action == 'add_holiday':
            try:
                new_date_str = request.POST.get('new_holiday_date', '').strip()
                new_name = request.POST.get('new_holiday_name', '').strip()
                if not new_date_str or not new_name:
                    raise ValueError('Date and name are required.')
                new_date = dt_date.fromisoformat(new_date_str)
                _, created = Holiday.objects.get_or_create(
                    date=new_date,
                    defaults={'name': new_name, 'is_custom': True, 'active': True},
                )
                if created:
                    messages.success(request, f'Custom holiday "{new_name}" added.')
                else:
                    messages.warning(request, f'A holiday already exists for {new_date_str}.')
            except ValueError as e:
                messages.error(request, f'Error adding holiday: {e}')
            active_tab = request.POST.get('active_tab', 'case-settings')
            return redirect(reverse('system_settings') + f'?tab={active_tab}')

        if action == 'delete_holiday':
            try:
                h = Holiday.objects.get(pk=int(request.POST.get('holiday_id')), is_custom=True)
                h.delete()
                messages.success(request, 'Custom holiday removed.')
            except (Holiday.DoesNotExist, ValueError):
                messages.error(request, 'Custom holiday not found.')
            active_tab = request.POST.get('active_tab', 'case-settings')
            return redirect(reverse('system_settings') + f'?tab={active_tab}')

        # --- Standard settings save ---
        try:
            # Credits
            settings.available_credits = request.POST.get('available_credits', '0.0,0.5,1.0,1.5,2.0,2.5,3.0') or '0.0,0.5,1.0,1.5,2.0,2.5,3.0'

            # Default Case Settings — use `or` so an empty POST value falls back to the safe default
            settings.default_case_due_days = int(request.POST.get('default_case_due_days') or 7)
            settings.rush_case_threshold_days = int(request.POST.get('rush_case_threshold_days') or 7)

            # Release Settings
            settings.enable_scheduled_releases = request.POST.get('enable_scheduled_releases') == 'on'
            settings.default_completion_delay_hours = int(request.POST.get('default_completion_delay_hours') or 0)
            batch_time_str = (request.POST.get('batch_release_time') or '09:00').strip()
            if batch_time_str:
                from datetime import time as dt_time
                parts = batch_time_str.split(':')
                settings.batch_release_time = dt_time(int(parts[0]), int(parts[1]))
            settings.batch_release_enabled = request.POST.get('batch_release_enabled') == 'on'

            # Email Settings
            settings.email_notifications_enabled = request.POST.get('email_notifications_enabled') == 'on'
            settings.enable_delayed_email_notifications = request.POST.get('enable_delayed_email_notifications') == 'on'
            settings.default_email_delay_hours = int(request.POST.get('default_email_delay_hours') or 0)
            settings.batch_email_enabled = request.POST.get('batch_email_enabled') == 'on'
            settings.reply_email_address = request.POST.get('reply_email_address') or 'reports@profeds.com'

            # API Configuration
            settings.benefits_software_api_url = request.POST.get('benefits_software_api_url', '')
            settings.benefits_software_api_key = request.POST.get('benefits_software_api_key', '')
            settings.benefits_software_api_enabled = request.POST.get('benefits_software_api_enabled') == 'on'

            # Technical Notes Template
            # Use whichever field arrived in the POST — prefer the main textarea;
            # fall back to the hidden sync field. Both are populated by JS before submit.
            # An empty string is a valid save (user deliberately cleared the template).
            if 'technical_notes_template' in request.POST:
                posted_template = request.POST['technical_notes_template']
            elif 'technical_notes_template_fallback' in request.POST:
                posted_template = request.POST['technical_notes_template_fallback']
            else:
                posted_template = None
            if posted_template is not None:
                settings.technical_notes_template = posted_template
                logger.info(
                    f'technical_notes_template saved: length={len(posted_template)}, '
                    f'user={request.user.username}'
                )

            # Feedback Notification Emails
            settings.feedback_email_1 = request.POST.get('feedback_email_1', '').strip()
            settings.feedback_email_1_enabled = request.POST.get('feedback_email_1_enabled') == 'on'
            settings.feedback_email_2 = request.POST.get('feedback_email_2', '').strip()
            settings.feedback_email_2_enabled = request.POST.get('feedback_email_2_enabled') == 'on'

            # Super-dev account policy
            settings.super_dev_email = request.POST.get('super_dev_email', '').strip().lower()

            settings.updated_by = request.user
            settings.save()

            messages.success(request, 'System settings updated successfully!')
            active_tab = request.POST.get('active_tab', 'credits')
            return redirect(reverse('system_settings') + f'?tab={active_tab}')
        except Exception as e:
            logger.exception('system_settings POST failed')
            messages.error(request, f'Error updating settings: {str(e)}')

    # Gather holidays for current + next year to display in admin UI
    today_year = dt_date.today().year
    holidays_display = Holiday.objects.filter(
        date__year__in=[today_year, today_year + 1]
    ).order_by('date')

    context = {
        'settings': settings,
        'holidays': holidays_display,
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
    old_email = user.email_notifications_enabled
    new_email = request.POST.get('email_notifications_enabled') == '1'

    user.email_notifications_enabled = new_email
    user.portal_notifications_enabled = True  # Always enabled — not user-controllable
    user.save(update_fields=['email_notifications_enabled', 'portal_notifications_enabled'])

    # Audit log if email preference actually changed
    if old_email != new_email:
        from core.models import AuditLog
        user_name = user.get_full_name() or user.username
        status = 'ON' if new_email else 'OFF'
        AuditLog.objects.create(
            user=user,
            action_type='notification_preferences_changed',
            description=f'{user_name} turned email notifications {status}.',
            ip_address=request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', '')).split(',')[0].strip() or None,
            metadata={
                'preference': 'email_notifications_enabled',
                'old_value': old_email,
                'new_value': new_email,
            },
        )

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

    old_email = assignment.email_notifications
    old_portal = assignment.portal_notifications
    new_email = request.POST.get('email_notifications') == '1'
    new_portal = request.POST.get('portal_notifications') == '1'

    assignment.email_notifications = new_email
    assignment.portal_notifications = new_portal
    assignment.save(update_fields=['email_notifications', 'portal_notifications'])

    member_name = assignment.member.get_full_name() or assignment.member.username

    # Audit log if any preference changed
    changes = {}
    if old_email != new_email:
        changes['email_notifications'] = {'old': old_email, 'new': new_email}
    if old_portal != new_portal:
        changes['portal_notifications'] = {'old': old_portal, 'new': new_portal}

    if changes:
        from core.models import AuditLog
        delegate_name = request.user.get_full_name() or request.user.username
        changed_items = ', '.join(
            f"{k.replace('_', ' ')} {'ON' if v['new'] else 'OFF'}" for k, v in changes.items()
        )
        AuditLog.objects.create(
            user=request.user,
            action_type='notification_preferences_changed',
            description=(
                f'Delegate {delegate_name} changed alert settings for member {member_name}: {changed_items}.'
            ),
            related_user=assignment.member,
            ip_address=request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', '')).split(',')[0].strip() or None,
            metadata={
                'assignment_id': assignment.pk,
                'member_id': assignment.member.pk,
                'member_name': member_name,
                'changes': changes,
            },
        )

    messages.success(request, f'Notification settings updated for {member_name}.')
    return redirect('profile')


@login_required
def request_add_delegate(request):
    """Member requests to add a new delegate. Sends email to staff."""
    if request.method != 'POST':
        return redirect('profile')

    from accounts.models import DelegateRequest
    from core.models import AuditLog

    delegate_name = request.POST.get('delegate_name', '').strip()
    delegate_email = request.POST.get('delegate_email', '').strip()
    notes = request.POST.get('notes', '').strip()

    if not delegate_name:
        messages.error(request, 'Delegate name is required.')
        return redirect('profile')

    dr = DelegateRequest.objects.create(
        requested_by=request.user,
        request_type='add',
        delegate_name=delegate_name,
        delegate_email=delegate_email,
        notes=notes,
    )

    # Audit log
    member_name = request.user.get_full_name() or request.user.username
    AuditLog.objects.create(
        user=request.user,
        action_type='delegate_add_requested',
        description=(
            f'{member_name} requested to add delegate "{delegate_name}" ({delegate_email}).'
        ),
        ip_address=request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', '')).split(',')[0].strip() or None,
        metadata={
            'delegate_request_id': dr.pk,
            'delegate_name': delegate_name,
            'delegate_email': delegate_email,
            'notes': notes,
            'member_id': request.user.pk,
            'member_name': member_name,
        },
    )

    _send_delegate_request_email(request.user, dr)
    messages.success(request, f'Request to add "{delegate_name}" as a delegate has been submitted. You will be notified when it is processed.')
    return redirect('profile')


@login_required
def request_remove_delegate(request):
    """Member requests to remove a delegate. Immediately disconnects + emails staff."""
    if request.method != 'POST':
        return redirect('profile')

    from accounts.models import DelegateRequest, MemberDelegate
    from core.models import AuditLog

    assignment_id = request.POST.get('assignment_id')
    if not assignment_id:
        messages.error(request, 'Missing delegate assignment.')
        return redirect('profile')

    try:
        assignment = MemberDelegate.objects.get(pk=assignment_id, member=request.user)
    except MemberDelegate.DoesNotExist:
        messages.error(request, 'Delegate assignment not found.')
        return redirect('profile')

    # Capture delegate info before deletion
    delegate_user = assignment.delegate
    delegate_name = delegate_user.get_full_name() or delegate_user.username
    delegate_email = delegate_user.email or ''
    still_with_firm_val = request.POST.get('still_with_firm')
    still_with_firm = still_with_firm_val == 'yes' if still_with_firm_val else None
    notes = request.POST.get('notes', '').strip()

    # Create the request record (before deleting assignment)
    dr = DelegateRequest.objects.create(
        requested_by=request.user,
        request_type='remove',
        delegate_name=delegate_name,
        delegate_email=delegate_email,
        existing_assignment=None,  # Will be deleted, so don't FK
        still_with_firm=still_with_firm,
        notes=notes,
        status='approved',  # Immediately processed
    )

    # Immediately delete the delegate assignment
    assignment.delete()

    # Audit log — verbose
    member_name = request.user.get_full_name() or request.user.username
    firm_status = 'Still with firm' if still_with_firm else 'No longer with firm' if still_with_firm is not None else 'Not specified'
    AuditLog.objects.create(
        user=request.user,
        action_type='delegate_remove_requested',
        description=(
            f'{member_name} requested removal of delegate "{delegate_name}" ({delegate_email}). '
            f'Firm status: {firm_status}. Assignment immediately disconnected.'
        ),
        related_user=delegate_user,
        ip_address=request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', '')).split(',')[0].strip() or None,
        metadata={
            'delegate_request_id': dr.pk,
            'delegate_name': delegate_name,
            'delegate_email': delegate_email,
            'still_with_firm': still_with_firm,
            'notes': notes,
            'member_id': request.user.pk,
            'member_name': member_name,
        },
    )

    # If delegate is no longer with the firm, deactivate their account
    # (only if they have no remaining delegate assignments)
    account_deactivated = False
    if still_with_firm is False:
        remaining = MemberDelegate.objects.filter(delegate=delegate_user).count()
        if remaining == 0 and delegate_user.is_active:
            delegate_user.is_active = False
            delegate_user.save(update_fields=['is_active'])
            account_deactivated = True
            AuditLog.objects.create(
                user=request.user,
                action_type='delegate_remove_requested',
                description=(
                    f'Delegate account "{delegate_name}" ({delegate_email}) automatically deactivated. '
                    f'Reason: reported as no longer with firm by {member_name}, and no remaining delegate assignments.'
                ),
                related_user=delegate_user,
                ip_address=request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', '')).split(',')[0].strip() or None,
                metadata={
                    'delegate_request_id': dr.pk,
                    'action': 'account_deactivated',
                    'delegate_user_id': delegate_user.pk,
                    'delegate_name': delegate_name,
                    'delegate_email': delegate_email,
                    'remaining_assignments': 0,
                    'deactivated_by_member_id': request.user.pk,
                    'deactivated_by_member_name': member_name,
                },
            )
            logger.info(f'Delegate user {delegate_user.pk} ({delegate_name}) deactivated — no longer with firm, 0 remaining assignments')

    # Email staff so they can update GHL
    _send_delegate_request_email(request.user, dr, account_deactivated=account_deactivated)

    messages.success(request, f'"{delegate_name}" has been removed as your delegate. Our team has been notified.')
    return redirect('profile')


def _send_delegate_request_email(member, delegate_request, account_deactivated=False):
    """Send notification email to L3 techs, admins, and managers about a delegate request."""
    try:
        from django.core.mail import send_mail
        from django.conf import settings as django_settings
        from accounts.models import User

        # Recipients: L3 techs + admins + managers
        staff = User.objects.filter(
            is_active=True,
            role__in=['administrator', 'manager'],
        ).values_list('email', flat=True)

        l3_techs = User.objects.filter(
            is_active=True,
            role='technician',
            user_level='level_3',
        ).values_list('email', flat=True)

        recipients = list(set(list(staff) + list(l3_techs)))
        recipients = [e for e in recipients if e]

        # Exclude super dev account — it has full portal access but is not an operational recipient
        try:
            from core.models import SystemSettings
            super_dev_email = (SystemSettings.get_settings().super_dev_email or '').strip().lower()
            if super_dev_email:
                recipients = [e for e in recipients if e.lower() != super_dev_email]
        except Exception:
            pass

        if not recipients:
            logger.warning('No staff recipients for delegate request email')
            return

        member_name = member.get_full_name() or member.username
        action = 'ADD' if delegate_request.request_type == 'add' else 'REMOVE'

        subject = f'Delegate Request: {action} — {delegate_request.delegate_name} (from {member_name})'

        lines = [
            f'A member has submitted a request to {action.lower()} a delegate.',
            '',
            f'Member: {member_name} ({member.email})',
            f'Request Type: {action}',
            f'Delegate Name: {delegate_request.delegate_name}',
        ]
        if delegate_request.delegate_email:
            lines.append(f'Delegate Email: {delegate_request.delegate_email}')

        # Include firm status for removal requests
        if delegate_request.request_type == 'remove' and delegate_request.still_with_firm is not None:
            if delegate_request.still_with_firm:
                lines.append('Still with firm: YES — still works at the firm, just removed from member\'s cases')
            else:
                lines.append('Still with firm: NO — no longer works at the firm (remove ALL portal + website access)')

        if delegate_request.notes:
            lines.append(f'Notes: {delegate_request.notes}')

        if delegate_request.request_type == 'remove':
            lines += [
                '',
                'Portal Access Update:',
                f'- The delegate assignment has ALREADY been removed in the portal.',
                f'- {delegate_request.delegate_name} can no longer view or manage cases for {member_name}.',
                '',
                'GHL Action Required:',
            ]
            if delegate_request.still_with_firm is False:
                lines.append('- Remove ALL GHL access (contact no longer with firm)')
                if account_deactivated:
                    lines += [
                        '',
                        'ACCOUNT DEACTIVATED:',
                        f'- {delegate_request.delegate_name} portal account has been AUTOMATICALLY DEACTIVATED.',
                        '- They had no remaining delegate assignments.',
                        '- Their account and full audit history are preserved (not deleted).',
                        '- To reactivate, go to the admin panel and set is_active=True.',
                    ]
            else:
                lines.append('- Update GHL delegate tags as needed')
        else:
            lines += [
                '',
                'Action Required:',
                '1. Process in GHL (GoHighLevel) first',
                '2. Then add the delegate assignment in the portal',
                '',
                'This request is pending until processed by staff.',
            ]

        text_message = '\n'.join(lines)

        send_mail(
            subject=subject,
            message=text_message,
            from_email=django_settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipients,
            fail_silently=True,
        )
        logger.info(f'Delegate request email sent to {recipients} for {delegate_request}')
    except Exception as e:
        logger.error(f'Error sending delegate request email: {e}')


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
