"""
Django management command to release scheduled cases
Run this daily via cron: 0 0 * * * cd /path/to/app && python manage.py release_scheduled_cases
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date
from cases.models import Case


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
        for case in cases_to_release:
            case.actual_release_date = timezone.now()
            case.save()
            self.stdout.write(
                self.style.SUCCESS(
                    f'✓ Released case {case.external_case_id} (was scheduled for {case.scheduled_release_date})'
                )
            )
        
        self.stdout.write(
            self.style.SUCCESS(f'\nSuccessfully released {count} case(s).')
        )
