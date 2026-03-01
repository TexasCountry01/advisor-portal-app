"""
Set temporary passwords on test users so they can log in via browser.

Usage:
    python manage.py set_test_passwords                  # Set default password on all 27 test users
    python manage.py set_test_passwords --password XYZ   # Set custom password
    python manage.py set_test_passwords --user frank@compassfinancialsa.com  # Single user
    python manage.py set_test_passwords --list           # Just list test users (no changes)

Default password: TestPass123!
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from .load_test_users import TEST_USERS

User = get_user_model()

DEFAULT_PASSWORD = 'TestPass123!'


class Command(BaseCommand):
    help = 'Set temporary passwords on test users for manual browser testing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--password',
            default=DEFAULT_PASSWORD,
            help=f'Password to set (default: {DEFAULT_PASSWORD})',
        )
        parser.add_argument(
            '--user',
            help='Set password for a single user (by email)',
        )
        parser.add_argument(
            '--list',
            action='store_true',
            help='Just list test users and their login status',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Set passwords on ALL users (not just test users)',
        )

    def handle(self, *args, **options):
        password = options['password']
        single_user = options['user']
        list_only = options['list']
        all_users = options['all']

        # Determine which users to process
        if single_user:
            users = User.objects.filter(email__iexact=single_user)
            if not users.exists():
                self.stderr.write(self.style.ERROR(f'No user found with email: {single_user}'))
                return
        elif all_users:
            users = User.objects.filter(is_active=True).order_by('role', 'email')
        else:
            # Only test users (by contact_id)
            contact_ids = [u['contact_id'] for u in TEST_USERS]
            users = User.objects.filter(contact_id__in=contact_ids).order_by('workshop_code', 'email')

        if list_only:
            self._list_users(users)
            return

        count = 0
        for user in users:
            user.set_password(password)
            user.save(update_fields=['password'])
            count += 1
            self.stdout.write(
                f'  ✓ {user.email:40s}  (username: {user.username}, '
                f'role: {user.role}, ws: {user.workshop_code})'
            )

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            f'Password set on {count} user(s). '
            f'Password: {password}'
        ))
        self.stdout.write(self.style.WARNING(
            'Remember to remove these passwords before production use!'
        ))

    def _list_users(self, users):
        self.stdout.write(self.style.HTTP_INFO('\n--- Test Users ---'))
        self.stdout.write(f'{"Email":42s} {"Username":22s} {"Role":10s} {"WS":6s} {"Has PW":8s}')
        self.stdout.write('-' * 92)
        for u in users:
            has_pw = '✓ yes' if u.has_usable_password() else '✗ no'
            self.stdout.write(
                f'{u.email:42s} {u.username:22s} {u.role:10s} {u.workshop_code or "-":6s} {has_pw:8s}'
            )
        self.stdout.write(f'\nTotal: {users.count()} users')
