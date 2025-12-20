"""
Management command to retry failed API syncs to benefits-software.
Can be run manually or via cron job.
"""
from django.core.management.base import BaseCommand
from cases.services import retry_failed_cases


class Command(BaseCommand):
    help = 'Retry failed API syncs to benefits-software'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--max-age-hours',
            type=int,
            default=24,
            help='Only retry cases failed within this many hours (default: 24)'
        )
    
    def handle(self, *args, **options):
        max_age_hours = options['max_age_hours']
        
        self.stdout.write(
            self.style.WARNING(
                f'Starting retry of failed API syncs (max age: {max_age_hours} hours)...'
            )
        )
        
        success_count, fail_count = retry_failed_cases()
        
        total = success_count + fail_count
        
        if total == 0:
            self.stdout.write(
                self.style.SUCCESS('No failed cases found to retry.')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Retry complete: {success_count} succeeded, {fail_count} failed (total: {total})'
                )
            )
            
            if fail_count > 0:
                self.stdout.write(
                    self.style.WARNING(
                        f'Note: {fail_count} cases still failed. Check admin panel for details.'
                    )
                )
