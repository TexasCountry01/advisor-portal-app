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
    if not case.member or not case.member.email:
        return False
    
    context = {
        'member_name': case.member.get_full_name() or case.member.username,
        'case_id': case.external_case_id,
        'employee_name': f"{case.employee_first_name} {case.employee_last_name}",
        'portal_url': settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'https://portal.example.com',
    }
    
    return send_email_notification(
        subject=f'Your case {case.external_case_id} has been accepted',
        template_name='case_accepted_member.html',
        context=context,
        recipient_email=case.member.email,
        case=case,
        user=None,
    )


def send_case_question_asked_email(case, question_text):
    """Send email to member when technician asks a question"""
    if not case.member or not case.member.email:
        return False
    
    context = {
        'member_name': case.member.get_full_name() or case.member.username,
        'case_id': case.external_case_id,
        'question': question_text,
        'portal_url': settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'https://portal.example.com',
    }
    
    return send_email_notification(
        subject=f'Question about your case {case.external_case_id}',
        template_name='case_question_asked.html',
        context=context,
        recipient_email=case.member.email,
        case=case,
        user=None,
    )


def send_case_hold_resumed_email(case):
    """Send email to member when case is resumed from hold"""
    if not case.member or not case.member.email:
        return False
    
    context = {
        'member_name': case.member.get_full_name() or case.member.username,
        'case_id': case.external_case_id,
        'employee_name': f"{case.employee_first_name} {case.employee_last_name}",
        'portal_url': settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'https://portal.example.com',
    }
    
    return send_email_notification(
        subject=f'Your case {case.external_case_id} processing has resumed',
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
    if not tech_user or not tech_user.email:
        return False
    
    context = {
        'tech_name': tech_user.get_full_name() or tech_user.username,
        'case_id': case.external_case_id,
        'member_name': case.member.get_full_name() if case.member else 'Member',
        'portal_url': settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'https://portal.example.com',
    }
    
    return send_email_notification(
        subject=f'Member response on case {case.external_case_id}',
        template_name='member_response_notification.html',
        context=context,
        recipient_email=tech_user.email,
        case=case,
        user=tech_user,
    )


def send_case_resubmitted_email(case, tech_user):
    """Send email to technician when case is resubmitted"""
    if not tech_user or not tech_user.email:
        return False
    
    context = {
        'tech_name': tech_user.get_full_name() or tech_user.username,
        'case_id': case.external_case_id,
        'member_name': case.member.get_full_name() if case.member else 'Member',
        'portal_url': settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'https://portal.example.com',
    }
    
    return send_email_notification(
        subject=f'Case {case.external_case_id} has been resubmitted',
        template_name='case_resubmitted_notification.html',
        context=context,
        recipient_email=tech_user.email,
        case=case,
        user=tech_user,
    )


def send_new_case_assigned_email(case, tech_user):
    """Send email to technician when new case is assigned"""
    if not tech_user or not tech_user.email:
        return False
    
    context = {
        'tech_name': tech_user.get_full_name() or tech_user.username,
        'case_id': case.external_case_id,
        'employee_name': f"{case.employee_first_name} {case.employee_last_name}",
        'urgency': case.get_urgency_display(),
        'tier': case.get_tier_display() if case.tier else 'Not set',
        'portal_url': settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'https://portal.example.com',
    }
    
    return send_email_notification(
        subject=f'New case assigned: {case.external_case_id}',
        template_name='new_case_assigned.html',
        context=context,
        recipient_email=tech_user.email,
        case=case,
        user=tech_user,
    )


def send_modification_created_email(original_case, modification_case, tech_user):
    """Send email to technician when member requests modification"""
    if not tech_user or not tech_user.email:
        return False
    
    context = {
        'tech_name': tech_user.get_full_name() or tech_user.username,
        'original_case_id': original_case.external_case_id,
        'modification_case_id': modification_case.external_case_id,
        'member_name': original_case.member.get_full_name() if original_case.member else 'Member',
        'portal_url': settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'https://portal.example.com',
    }
    
    return send_email_notification(
        subject=f'Modification requested for case {original_case.external_case_id}',
        template_name='modification_created_notification.html',
        context=context,
        recipient_email=tech_user.email,
        case=modification_case,
        user=tech_user,
    )
