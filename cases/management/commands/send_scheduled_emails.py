"""
Django management command to send scheduled member notification emails.
Email sending is tied to case release dates.

Run this daily/hourly via cron:
    Daily: 0 0 * * * cd /path/to/app && python manage.py send_scheduled_emails
    Hourly: 0 * * * * cd /path/to/app && python manage.py send_scheduled_emails
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
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
        now = timezone.now()
        
        # Find all completed cases that need email notification
        # Includes: scheduled emails past due AND released cases where email failed
        cases_to_email = Case.objects.filter(
            status='completed',
            actual_release_date__isnull=False,
            actual_email_sent_date__isnull=True,
            member__isnull=False,
        ).select_related('member')
        
        count = cases_to_email.count()
        
        if count == 0:
            self.stdout.write(self.style.SUCCESS('No emails to send.'))
            return
        
        if dry_run:
            self.stdout.write(self.style.WARNING(f'DRY RUN: Would send {count} email(s):'))
            for case in cases_to_email:
                email_addr = case.member.email if case.member else 'N/A'
                self.stdout.write(f'  - {case.external_case_id} to {email_addr} (released: {case.actual_release_date})')
            return
        
        # Send emails using the central email service
        from cases.services.email_service import send_case_completed_email
        
        sent_count = 0
        failed_count = 0
        
        for case in cases_to_email:
            try:
                # send_case_completed_email handles actual_email_sent_date and audit logging
                result = send_case_completed_email(case)
                
                if result:
                    sent_count += 1
                    self.stdout.write(self.style.SUCCESS(
                        f'✓ Sent notification email for case {case.external_case_id} to {case.member.email}'
                    ))
                else:
                    failed_count += 1
                    self.stdout.write(self.style.WARNING(
                        f'✗ Failed to send email for case {case.external_case_id}'
                    ))
                    
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
