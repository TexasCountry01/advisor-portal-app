"""
Email service for all case notifications.
All emails respect the global email_notifications_enabled setting.
"""
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.utils import timezone
from core.models import SystemSettings, AuditLog
import logging

logger = logging.getLogger(__name__)


def should_send_emails():
    """Check if email notifications are globally enabled"""
    system_settings = SystemSettings.get_settings()
    return system_settings.email_notifications_enabled


def _build_case_detail_url(case):
    """Build absolute URL to case detail page using numeric PK."""
    from django.urls import reverse
    base_url = getattr(settings, 'SITE_URL', 'https://portal.profeds.com')
    return f"{base_url}{reverse('cases:case_detail', args=[case.id])}"


def _get_notification_email(user):
    """Return the email address to use for portal notifications.
    Uses notification_email if set, otherwise falls back to the SSO email."""
    override = getattr(user, 'notification_email', '') or ''
    return override.strip() if override.strip() else user.email


def get_case_recipient_emails(case):
    """Get all email recipients for a case: member + their delegates.
    Respects notification_email overrides for each user.
    Returns a list of unique email addresses."""
    recipients = []
    if case.member and case.member.email:
        email = _get_notification_email(case.member)
        if email:
            recipients.append(email)
    
    # Add delegate emails
    try:
        from accounts.models import MemberDelegate
        delegates = MemberDelegate.objects.filter(member=case.member).select_related('delegate')
        for assignment in delegates:
            email = _get_notification_email(assignment.delegate)
            if email and email not in recipients:
                recipients.append(email)
    except Exception as e:
        logger.warning(f'Error fetching delegate emails for case {case.id}: {e}')
    
    return recipients


def send_email_notification(
    subject,
    template_name,
    context,
    recipient_email,
    case=None,
    user=None,
    action_type='email_notification_sent'
):
    """
    Send email notification with audit logging.
    
    Args:
        subject: Email subject line
        template_name: Template file name (in cases/templates/emails/)
        context: Context dict for template rendering
        recipient_email: Email address to send to
        case: Related case (for audit logging)
        user: User sending email (for audit logging)
        action_type: Audit log action type
    
    Returns:
        True if sent, False if skipped/failed
    """
    if not should_send_emails():
        logger.info(f'Email notifications disabled globally. Skipped: {subject}')
        return False
    
    if not recipient_email:
        logger.warning(f'No recipient email for: {subject}')
        return False
    
    try:
        # Render template
        html_message = render_to_string(f'emails/{template_name}', context)
        text_message = strip_tags(html_message)
        
        # Send email
        from_email = settings.DEFAULT_FROM_EMAIL
        send_mail(
            subject=subject,
            message=text_message,
            from_email=from_email,
            recipient_list=[recipient_email],
            html_message=html_message,
            fail_silently=False,
        )
        
        # Log to audit trail
        AuditLog.log_activity(
            user=user,
            action_type=action_type,
            description=f'{action_type}: {subject} sent to {recipient_email}',
            case=case,
            metadata={
                'recipient': recipient_email,
                'subject': subject,
                'template': template_name,
            }
        )
        
        logger.info(f'Email sent: {subject} to {recipient_email}')
        return True
        
    except Exception as e:
        logger.error(f'Failed to send email {subject} to {recipient_email}: {str(e)}')
        
        # Log failure to audit trail
        AuditLog.log_activity(
            user=user,
            action_type='email_notification_failed',
            description=f'Email failed: {subject} to {recipient_email} - {str(e)}',
            case=case,
            metadata={
                'recipient': recipient_email,
                'subject': subject,
                'error': str(e),
            }
        )
        return False


# ============================================================================
# MEMBER NOTIFICATIONS
# ============================================================================

def send_case_accepted_email(case):
    """Send email to member when case is accepted by technician"""
    # DISABLED per email policy — members only receive HOLD, CHAT, READY emails
    return False

    if not case.member or not case.member.email:
        return False
    
    context = {
        'member_name': case.member.get_full_name() or case.member.username,
        'case_id': case.external_case_id,
        'employee_name': f"{case.employee_first_name} {case.employee_last_name}",
        'portal_url': settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'https://portal.example.com',
        'case_detail_url': _build_case_detail_url(case),
    }
    
    employee_name = f"{case.employee_first_name} {case.employee_last_name}".strip()

    return send_email_notification(
        subject=f'Your case for {employee_name} has been accepted',
        template_name='case_accepted_member.html',
        context=context,
        recipient_email=case.member.email,
        case=case,
        user=None,
    )


def send_case_question_asked_email(case, question_text):
    """Send email to member when technician asks a question"""
    # DISABLED per email policy — members only receive HOLD, CHAT, READY emails
    return False

    if not case.member or not case.member.email:
        return False
    
    context = {
        'member_name': case.member.get_full_name() or case.member.username,
        'case_id': case.external_case_id,
        'question': question_text,
        'portal_url': settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'https://portal.example.com',
        'case_detail_url': _build_case_detail_url(case),
    }
    
    employee_name = f"{case.employee_first_name} {case.employee_last_name}".strip()

    return send_email_notification(
        subject=f'Question about your case for {employee_name}',
        template_name='case_question_asked.html',
        context=context,
        recipient_email=case.member.email,
        case=case,
        user=None,
    )


def send_case_hold_resumed_email(case):
    """Send email to member when case is resumed from hold"""
    # DISABLED per email policy — members only receive HOLD, CHAT, READY emails
    return False

    if not case.member or not case.member.email:
        return False
    
    context = {
        'member_name': case.member.get_full_name() or case.member.username,
        'case_id': case.external_case_id,
        'employee_name': f"{case.employee_first_name} {case.employee_last_name}",
        'portal_url': settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'https://portal.example.com',
        'case_detail_url': _build_case_detail_url(case),
    }
    
    employee_name = f"{case.employee_first_name} {case.employee_last_name}".strip()

    return send_email_notification(
        subject=f'Your case for {employee_name} processing has resumed',
        template_name='case_hold_resumed.html',
        context=context,
        recipient_email=case.member.email,
        case=case,
        user=None,
    )


# ============================================================================
# TECHNICIAN NOTIFICATIONS
# ============================================================================

def send_member_response_email(case, tech_user):
    """Send email to technician when member responds to question/uploads doc"""
    # DISABLED per email policy — technicians do not receive email notifications
    return False

    if not tech_user or not tech_user.email:
        return False
    
    context = {
        'tech_name': tech_user.get_full_name() or tech_user.username,
        'case_id': case.external_case_id,
        'member_name': case.member.get_full_name() if case.member else 'Member',
        'portal_url': settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'https://portal.example.com',
        'case_detail_url': _build_case_detail_url(case),
    }
    
    employee_name = f"{case.employee_first_name} {case.employee_last_name}".strip()

    return send_email_notification(
        subject=f'Member response on case for {employee_name}',
        template_name='member_response_notification.html',
        context=context,
        recipient_email=tech_user.email,
        case=case,
        user=tech_user,
    )


def send_case_resubmitted_email(case, tech_user):
    """Send email to technician when case is resubmitted"""
    # DISABLED per email policy — technicians do not receive email notifications
    return False

    if not tech_user or not tech_user.email:
        return False
    
    context = {
        'tech_name': tech_user.get_full_name() or tech_user.username,
        'case_id': case.external_case_id,
        'member_name': case.member.get_full_name() if case.member else 'Member',
        'portal_url': settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'https://portal.example.com',
        'case_detail_url': _build_case_detail_url(case),
    }
    
    employee_name = f"{case.employee_first_name} {case.employee_last_name}".strip()

    return send_email_notification(
        subject=f'Case for {employee_name} has been resubmitted',
        template_name='case_resubmitted_notification.html',
        context=context,
        recipient_email=tech_user.email,
        case=case,
        user=tech_user,
    )


def send_new_case_assigned_email(case, tech_user):
    """Send email to technician when new case is assigned"""
    # DISABLED per email policy — technicians do not receive email notifications
    return False

    if not tech_user or not tech_user.email:
        return False
    
    context = {
        'tech_name': tech_user.get_full_name() or tech_user.username,
        'case_id': case.external_case_id,
        'employee_name': f"{case.employee_first_name} {case.employee_last_name}",
        'urgency': case.get_urgency_display(),
        'tier': case.get_tier_display() if case.tier else 'Not set',
        'portal_url': settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'https://portal.example.com',
        'case_detail_url': _build_case_detail_url(case),
    }
    
    return send_email_notification(
        subject=f'New case assigned: {case.employee_first_name} {case.employee_last_name}',
        template_name='new_case_assigned.html',
        context=context,
        recipient_email=tech_user.email,
        case=case,
        user=tech_user,
    )


def send_modification_created_email(original_case, modification_case, tech_user):
    """Send email to technician when member requests modification"""
    # DISABLED per email policy — technicians do not receive email notifications
    return False

    if not tech_user or not tech_user.email:
        return False
    
    context = {
        'tech_name': tech_user.get_full_name() or tech_user.username,
        'original_case_id': original_case.external_case_id,
        'modification_case_id': modification_case.external_case_id,
        'member_name': original_case.member.get_full_name() if original_case.member else 'Member',
        'portal_url': settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'https://portal.example.com',
        'case_detail_url': _build_case_detail_url(modification_case),
    }
    
    employee_name = f"{original_case.employee_first_name} {original_case.employee_last_name}".strip()

    return send_email_notification(
        subject=f'Modification requested for case for {employee_name}',
        template_name='modification_created_notification.html',
        context=context,
        recipient_email=tech_user.email,
        case=modification_case,
        user=tech_user,
    )


def send_case_completed_email(case, request=None, user=None):
    """
    Send email to member when their case is completed and released.
    Can be called from views (with request) or from cron job (without request).
    
    On success, sets case.actual_email_sent_date and saves the case.
    On failure, ensures actual_email_sent_date remains None so retries can pick it up.
    
    Args:
        case: The Case object that has been completed/released
        request: Optional HttpRequest (for URL building in views)
        user: Optional User who triggered the completion (for audit logging)
    
    Returns:
        True if sent, False if skipped/failed
    """
    if not should_send_emails():
        logger.info(f'Email notifications disabled. Skipped completed email for case {case.external_case_id}')
        return False

    if not case.member or not case.member.email:
        logger.warning(f'No member email for case {case.external_case_id}. Skipped completed email.')
        return False

    try:
        from django.urls import reverse

        # Build base URL from request if available, otherwise from settings
        if request:
            from django.contrib.sites.shortcuts import get_current_site
            protocol = 'https' if request.is_secure() else 'http'
            domain = get_current_site(request).domain
            base_url = f"{protocol}://{domain}"
        else:
            base_url = getattr(settings, 'SITE_URL', 'https://portal.profeds.com')

        case_detail_url = f"{base_url}{reverse('cases:case_detail', args=[case.id])}"
        logo_url = f"{base_url}/static/images/RevisedCoverPageLogo.png"
        employee_name = f"{case.employee_first_name} {case.employee_last_name}".strip()

        email_context = {
            'member_first_name': case.member.first_name or case.member.username,
            'employee_name': employee_name,
            'case_detail_url': case_detail_url,
            'logo_url': logo_url,
        }

        email_subject = f'REPORT: The case for {employee_name} is ready for you!'
        text_message = render_to_string('emails/case_completed.txt', email_context)
        html_message = render_to_string('emails/case_completed.html', email_context)

        recipient_list = get_case_recipient_emails(case)

        send_mail(
            subject=email_subject,
            message=text_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipient_list,
            html_message=html_message,
            fail_silently=False,
        )

        # Mark email as sent on the case
        case.actual_email_sent_date = timezone.now()
        case.save(update_fields=['actual_email_sent_date'])

        # Audit trail
        AuditLog.log_activity(
            user=user,
            action_type='email_notification_sent',
            description=f'Case completed email sent to {recipient_list} for case {case.external_case_id}',
            case=case,
            metadata={
                'email_to': case.member.email,
                'email_subject': email_subject,
                'trigger': 'case_completed_released',
            }
        )

        logger.info(f'Case completed email sent to {case.member.email} for case {case.external_case_id}')
        return True

    except Exception as e:
        logger.error(f'Failed to send case completed email for {case.external_case_id}: {str(e)}')

        # Ensure email date is cleared so retries can pick it up
        if case.actual_email_sent_date is not None:
            case.actual_email_sent_date = None
            case.save(update_fields=['actual_email_sent_date'])

        AuditLog.log_activity(
            user=user,
            action_type='email_notification_failed',
            description=f'Case completed email failed for {case.external_case_id} to {case.member.email}: {str(e)}',
            case=case,
            metadata={
                'email_to': case.member.email if case.member else 'N/A',
                'error': str(e),
            }
        )
        return False


# ============================================================================
# DELEGATE NOTIFICATIONS
# ============================================================================

def send_delegate_assigned_email(member, delegate, assigned_by):
    """Send email to member when a delegate is assigned to their account."""
    # DISABLED per email policy — members only receive HOLD, CHAT, READY emails
    return False

    if not member or not member.email:
        return False

    portal_url = getattr(settings, 'SITE_URL', 'https://portal.profeds.com')
    context = {
        'member_name': member.get_full_name() or member.username,
        'delegate_name': delegate.get_full_name() or delegate.username,
        'delegate_email': delegate.email,
        'assigned_by_name': assigned_by.get_full_name() or assigned_by.username,
        'portal_url': portal_url,
    }

    return send_email_notification(
        subject='A delegate has been assigned to your account',
        template_name='delegate_assigned_notification.html',
        context=context,
        recipient_email=member.email,
        user=assigned_by,
    )


def send_delegate_removed_email(member, delegate, removed_by):
    """Send email to member when a delegate is removed from their account."""
    # DISABLED per email policy — members only receive HOLD, CHAT, READY emails
    return False

    if not member or not member.email:
        return False

    portal_url = getattr(settings, 'SITE_URL', 'https://portal.profeds.com')
    context = {
        'member_name': member.get_full_name() or member.username,
        'delegate_name': delegate.get_full_name() or delegate.username,
        'delegate_email': delegate.email,
        'removed_by_name': removed_by.get_full_name() or removed_by.username,
        'portal_url': portal_url,
    }

    return send_email_notification(
        subject='A delegate has been removed from your account',
        template_name='delegate_removed_notification.html',
        context=context,
        recipient_email=member.email,
        user=removed_by,
    )
