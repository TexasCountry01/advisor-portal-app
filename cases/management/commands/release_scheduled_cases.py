"""
Django management command to release scheduled cases
Run this daily via cron: 0 0 * * * cd /path/to/app && python manage.py release_scheduled_cases
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date
from cases.models import Case
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Release scheduled cases that have reached their release date'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be released without actually doing it',
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        today = date.today()
        
        # Check if batch processing is enabled
        from core.models import SystemSettings
        settings = SystemSettings.get_settings()
        if not settings.batch_release_enabled:
            self.stdout.write(self.style.WARNING('Automated batch processing is disabled in System Settings. Skipping.'))
            return
        
        # Find all completed cases that are scheduled for release on or before today
        cases_to_release = Case.objects.filter(
            status='completed',
            scheduled_release_date__lte=today,
            actual_release_date__isnull=True
        )
        
        count = cases_to_release.count()
        
        if count == 0:
            self.stdout.write(self.style.SUCCESS('No cases to release.'))
            return
        
        if dry_run:
            self.stdout.write(self.style.WARNING(f'DRY RUN: Would release {count} case(s):'))
            for case in cases_to_release:
                self.stdout.write(f'  - {case.external_case_id} (scheduled: {case.scheduled_release_date})')
            return
        
        # Release the cases
        from cases.models import CaseNotification
        for case in cases_to_release:
            case.actual_release_date = timezone.now()
            if not case.date_completed:
                case.date_completed = timezone.now()  # Fallback: should already be set when tech completed
            case.save()
            self.stdout.write(
                self.style.SUCCESS(
                    f'✓ Released case {case.external_case_id} (was scheduled for {case.scheduled_release_date})'
                )
            )
            
            # Create in-app notification for member
            try:
                employee_name = f'{case.employee_first_name} {case.employee_last_name}'.strip()
                CaseNotification.objects.create(
                    case=case,
                    member=case.member,
                    notification_type='case_released',
                    title=f'Your case for {employee_name} is completed',
                    message=f'Your case for {employee_name} has been completed and is ready for you to review.'
                )
                self.stdout.write(f'  🔔 Notification created for {case.member.username}')
            except Exception as e:
                logger.error(f'Failed to create notification for {case.external_case_id}: {str(e)}')
            
            # Send case completed email to member
            try:
                from cases.services.email_service import send_case_completed_email
                send_case_completed_email(case)
                self.stdout.write(f'  ✉ Completed email sent to {case.member.email}')
            except Exception as e:
                logger.error(f'Failed to send case completed email for {case.external_case_id}: {str(e)}')
                self.stdout.write(self.style.WARNING(f'  ✗ Email failed for {case.external_case_id}: {str(e)}'))
        
        self.stdout.write(
            self.style.SUCCESS(f'\nSuccessfully released {count} case(s).')
        )
