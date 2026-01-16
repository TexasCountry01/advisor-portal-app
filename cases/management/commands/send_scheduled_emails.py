"""
Django management command to send scheduled member notification emails.
Email sending is tied to case release dates.

Run this daily/hourly via cron:
    Daily: 0 0 * * * cd /path/to/app && python manage.py send_scheduled_emails
    Hourly: 0 * * * * cd /path/to/app && python manage.py send_scheduled_emails
"""
from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone
from django.conf import settings
from datetime import date
from cases.models import Case
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Send scheduled member notification emails for completed cases'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview what would be sent without actually sending emails',
        )
    
    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        today = date.today()
        
        # Find all completed cases that are scheduled for email notification on or before today
        cases_to_email = Case.objects.filter(
            status='completed',
            scheduled_email_date__lte=today,
            actual_email_sent_date__isnull=True,
            member__isnull=False,  # Must have a member to email
        ).select_related('member')
        
        count = cases_to_email.count()
        
        if count == 0:
            self.stdout.write(self.style.SUCCESS('No emails to send.'))
            return
        
        if dry_run:
            self.stdout.write(self.style.WARNING(f'DRY RUN: Would send {count} email(s):'))
            for case in cases_to_email:
                email_addr = case.member.email if case.member else 'N/A'
                self.stdout.write(f'  - {case.external_case_id} to {email_addr} (scheduled: {case.scheduled_email_date})')
            return
        
        # Send emails
        sent_count = 0
        failed_count = 0
        
        for case in cases_to_email:
            try:
                # Check that member has email
                if not case.member or not case.member.email:
                    logger.warning(f'Case {case.external_case_id}: No member email found')
                    failed_count += 1
                    continue
                
                # Send email
                email_result = send_case_notification_email(case)
                
                if email_result:
                    # Mark as sent
                    case.actual_email_sent_date = timezone.now()
                    case.save()
                    sent_count += 1
                    self.stdout.write(self.style.SUCCESS(
                        f'✓ Sent notification email for case {case.external_case_id} to {case.member.email}'
                    ))
                else:
                    failed_count += 1
                    logger.error(f'Failed to send email for case {case.external_case_id}')
                    
            except Exception as e:
                failed_count += 1
                logger.error(f'Error sending email for case {case.external_case_id}: {str(e)}')
                self.stdout.write(self.style.ERROR(f'✗ Error: {str(e)}'))
        
        # Summary
        self.stdout.write(self.style.SUCCESS(
            f'\nSuccessfully sent {sent_count} email(s).'
        ))
        if failed_count > 0:
            self.stdout.write(self.style.WARNING(
                f'Failed to send {failed_count} email(s).'
            ))


def send_case_notification_email(case):
    """
    Send member notification email for completed case.
    
    Args:
        case: Case object with member to notify
        
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        if not case.member or not case.member.email:
            logger.warning(f'Cannot send email: Case {case.external_case_id} has no member email')
            return False
        
        # Prepare email context
        context = {
            'member': case.member,
            'case': case,
            'case_url': f'{settings.SITE_URL}/cases/{case.id}/' if hasattr(settings, 'SITE_URL') else 'https://yoursite.com/cases/',
            'employee_name': f'{case.employee_first_name} {case.employee_last_name}',
        }
        
        # Render email templates
        subject = f'Your Case {case.external_case_id} is Now Available'
        text_message = render_to_string('emails/case_released_notification.txt', context)
        html_message = render_to_string('emails/case_released_notification.html', context)
        
        # Send email
        result = send_mail(
            subject=subject,
            message=text_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[case.member.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        logger.info(f'Sent notification email for case {case.external_case_id} to {case.member.email}')
        return result > 0
        
    except Exception as e:
        logger.error(f'Error sending email for case {case.external_case_id}: {str(e)}')
        return False
