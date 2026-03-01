"""
Load test users and delegate assignments into the database.

Usage:
    python manage.py load_test_users --dry-run     # Preview what would be created
    python manage.py load_test_users               # Actually create users & assignments
    python manage.py load_test_users --clear        # Remove test users first, then reload

These are real GHL contacts with portal access tags set up for SSO testing.
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from accounts.models import MemberDelegate

User = get_user_model()


# ============================================================================
# TEST USER DATA (from GHL / WP Fusion — March 1, 2026)
# ============================================================================

TEST_USERS = [
    # AVL workshop — Momodou (member) + 3 delegates
    {'contact_id': 'mjEakV4mHGjIv8p5Vxh0', 'first_name': 'Momodou', 'last_name': 'Bojang',
     'workshop_code': 'AVL', 'email': 'mlbojang@axiomvaluellc.com', 'role': 'member'},
    {'contact_id': 'CPjAdYm6H1yhaqkhCl0b', 'first_name': 'Josephine', 'last_name': 'Bojang',
     'workshop_code': 'AVL', 'email': 'jbojang@axiomvaluellc.com', 'role': 'member'},
    {'contact_id': 'MnywFVrCH02O5PneWYqI', 'first_name': 'Peter', 'last_name': 'Gerlach-Mack',
     'workshop_code': 'AVL', 'email': 'pgerlachmack@axiomvaluellc.com', 'role': 'member'},
    {'contact_id': 'bO0fquuajBHGU7Wn9TXi', 'first_name': 'Alex', 'last_name': 'String',
     'workshop_code': 'AVL', 'email': 'astring@axiomvaluellc.com', 'role': 'member'},

    # CFG workshop — 3 members (cross-delegates) + 2 pure delegates
    {'contact_id': 'fsPepBLPtCBFCsb6aFp2', 'first_name': 'Frank', 'last_name': 'Dimicelli',
     'workshop_code': 'CFG', 'email': 'frank@compassfinancialsa.com', 'role': 'member'},
    {'contact_id': 'ww010xmTYAWf6C42Fhhp', 'first_name': 'Brandon', 'last_name': 'Dimicelli',
     'workshop_code': 'CFG', 'email': 'brandon@compassfinancialsa.com', 'role': 'member'},
    {'contact_id': 'szpdPQ8GwSYsYxX4lCF1', 'first_name': 'Jaylon', 'last_name': 'Dukes',
     'workshop_code': 'CFG', 'email': 'support@compassfinancialsa.com', 'role': 'member'},
    {'contact_id': 'LigENB5Cnmq6rctm5SUE', 'first_name': 'Sabra', 'last_name': 'Singleton',
     'workshop_code': 'CFG', 'email': 'sabra@compassfinancialsa.com', 'role': 'member'},
    {'contact_id': 'TeCSIxysrPLt3fU9CjFv', 'first_name': 'Janae', 'last_name': 'Lickert',
     'workshop_code': 'CFG', 'email': 'janae@compassfinancialsa.com', 'role': 'member'},

    # HFR workshop — Patricia (member) + 3 delegates
    {'contact_id': 'uYgsHYzbPs9wVPSJuJpq', 'first_name': 'Patricia', 'last_name': 'Lavy',
     'workshop_code': 'HFR', 'email': 'patricia@heritagefinancialus.com', 'role': 'member'},
    {'contact_id': 'MyA5W8NGfnzoWfcxnH65', 'first_name': 'Evan', 'last_name': 'Hicks',
     'workshop_code': 'HFR', 'email': 'evan@heritagefinancialus.com', 'role': 'member'},
    {'contact_id': 'SWty2rcC3wAngiyEAjh5', 'first_name': 'James', 'last_name': 'Lavy',
     'workshop_code': 'HFR', 'email': 'james@heritagefinancialus.com', 'role': 'member'},
    {'contact_id': 'eXKcvHE7PNXyRLwnDJ2w', 'first_name': 'Shawn', 'last_name': 'Hicks',
     'workshop_code': 'HFR', 'email': 'shawn@heritagefinancialus.com', 'role': 'member'},

    # DMCG/AMCG/VMCG/etc workshops — McGregor group
    {'contact_id': 'kD6boGq23Tku2bqWqJnr', 'first_name': 'Dale', 'last_name': 'McGregor',
     'workshop_code': 'DMCG', 'email': 'dale@mcgregorfg.com', 'role': 'member'},
    {'contact_id': '3iLK1XHiyWf64q1m3Xvl', 'first_name': 'Virginia', 'last_name': 'Nixon',
     'workshop_code': 'AMCG', 'email': 'vnixon@mcgregorfg.com', 'role': 'member'},
    {'contact_id': '6gNXQX9k35QzJfgjYs4Z', 'first_name': 'Maurice', 'last_name': 'McMillan',
     'workshop_code': 'VMCG', 'email': 'mmcmillan@mcgregorfg.com', 'role': 'member'},
    {'contact_id': 'H2ovkzldIVXiqnjY5knw', 'first_name': 'Tan', 'last_name': 'Nguyen',
     'workshop_code': 'TMCG', 'email': 'tan@mcgregorfg.com', 'role': 'member'},
    {'contact_id': 'ODMPVOXG9enUhB94geWO', 'first_name': 'Josh', 'last_name': 'Carapina',
     'workshop_code': 'JMCG', 'email': 'jcarapina@mcgregorfg.com', 'role': 'member'},
    {'contact_id': 'Qyxv7NQEnm642g84F1ad', 'first_name': 'Rebecca', 'last_name': 'Ricks',
     'workshop_code': 'RMCG', 'email': 'rricks@mcgregorfg.com', 'role': 'member'},
    {'contact_id': 'S3mAbd3vMzBxP5GcGDdm', 'first_name': 'Donovan', 'last_name': 'Golden',
     'workshop_code': 'GMCG', 'email': 'dgolden@mcgregorfg.com', 'role': 'member'},
    {'contact_id': 'ybvScfCNgKaCEhyIgFNc', 'first_name': 'Madison', 'last_name': 'McGregor',
     'workshop_code': 'DMCG', 'email': 'madison@mcgregorfg.com', 'role': 'member'},
    {'contact_id': 'zG7XLd9Q0UIJF6oBiEPz', 'first_name': 'Les', 'last_name': 'McGregor',
     'workshop_code': 'DMCG', 'email': 'les@mcgregorfg.com', 'role': 'member'},
    {'contact_id': '2BRUhnhph3yh1QzD2n4X', 'first_name': 'Autumn', 'last_name': 'Chartier',
     'workshop_code': 'DMCG', 'email': 'achartier@mcgregorfg.com', 'role': 'member'},

    # VWP workshop — Ed & Zubin (members) + Amanda (delegate)
    {'contact_id': 'xjuGUnrPlRCw25sAafV8', 'first_name': 'Ed', 'last_name': 'Smith',
     'workshop_code': 'VWP', 'email': 'ed@valorwealthpartners.com', 'role': 'member'},
    {'contact_id': 'rX8gxeFheWWCNnBFPPUT', 'first_name': 'Zubin', 'last_name': 'Kapur',
     'workshop_code': 'VWP', 'email': 'zubink@valorwealthpartners.com', 'role': 'member'},
    {'contact_id': 'uHyohNnS9mX7LfuVjE41', 'first_name': 'Amanda', 'last_name': 'Lique',
     'workshop_code': 'VWP', 'email': 'amandal@valorwealthpartners.com', 'role': 'member'},

    # NAA workshop — Gary (solo member)
    {'contact_id': 'qwR9xs2dOmtLmbMjqpGE', 'first_name': 'Gary', 'last_name': 'Wedge',
     'workshop_code': 'NAA', 'email': 'gary@newageadvisors.com', 'role': 'member'},
]


# ============================================================================
# DELEGATE ASSIGNMENTS
# delegate_email → [member_email, member_email, ...]
# ============================================================================

DELEGATE_ASSIGNMENTS = {
    # AVL: Josephine, Peter, Alex → delegate for Momodou
    'jbojang@axiomvaluellc.com': ['mlbojang@axiomvaluellc.com'],
    'pgerlachmack@axiomvaluellc.com': ['mlbojang@axiomvaluellc.com'],
    'astring@axiomvaluellc.com': ['mlbojang@axiomvaluellc.com'],

    # CFG: Frank, Brandon, Jaylon are members AND delegates for each other
    'frank@compassfinancialsa.com': [
        'brandon@compassfinancialsa.com',
        'support@compassfinancialsa.com',  # Jaylon
    ],
    'brandon@compassfinancialsa.com': [
        'frank@compassfinancialsa.com',
        'support@compassfinancialsa.com',  # Jaylon
    ],
    'support@compassfinancialsa.com': [  # Jaylon
        'frank@compassfinancialsa.com',
        'brandon@compassfinancialsa.com',
    ],
    # CFG: Sabra and Janae → pure delegates for all 3 CFG members
    'sabra@compassfinancialsa.com': [
        'frank@compassfinancialsa.com',
        'brandon@compassfinancialsa.com',
        'support@compassfinancialsa.com',
    ],
    'janae@compassfinancialsa.com': [
        'frank@compassfinancialsa.com',
        'brandon@compassfinancialsa.com',
        'support@compassfinancialsa.com',
    ],

    # HFR: Evan, James, Shawn → delegates for Patricia
    'evan@heritagefinancialus.com': ['patricia@heritagefinancialus.com'],
    'james@heritagefinancialus.com': ['patricia@heritagefinancialus.com'],
    'shawn@heritagefinancialus.com': ['patricia@heritagefinancialus.com'],

    # McGregor group: Dale is delegate for 7 other members
    'dale@mcgregorfg.com': [
        'vnixon@mcgregorfg.com',
        'mmcmillan@mcgregorfg.com',
        'tan@mcgregorfg.com',
        'jcarapina@mcgregorfg.com',
        'rricks@mcgregorfg.com',
        'dgolden@mcgregorfg.com',
        'madison@mcgregorfg.com',
    ],
    # Madison is delegate for Dale + same 6 others
    'madison@mcgregorfg.com': [
        'dale@mcgregorfg.com',
        'vnixon@mcgregorfg.com',
        'mmcmillan@mcgregorfg.com',
        'tan@mcgregorfg.com',
        'jcarapina@mcgregorfg.com',
        'rricks@mcgregorfg.com',
        'dgolden@mcgregorfg.com',
    ],
    # Les and Autumn are pure delegates for all 8 McGregor members
    'les@mcgregorfg.com': [
        'dale@mcgregorfg.com',
        'vnixon@mcgregorfg.com',
        'mmcmillan@mcgregorfg.com',
        'tan@mcgregorfg.com',
        'jcarapina@mcgregorfg.com',
        'rricks@mcgregorfg.com',
        'dgolden@mcgregorfg.com',
        'madison@mcgregorfg.com',
    ],
    'achartier@mcgregorfg.com': [
        'dale@mcgregorfg.com',
        'vnixon@mcgregorfg.com',
        'mmcmillan@mcgregorfg.com',
        'tan@mcgregorfg.com',
        'jcarapina@mcgregorfg.com',
        'rricks@mcgregorfg.com',
        'dgolden@mcgregorfg.com',
        'madison@mcgregorfg.com',
    ],

    # VWP: Ed is delegate for Zubin
    'ed@valorwealthpartners.com': ['zubink@valorwealthpartners.com'],
    # Amanda is delegate for Ed and Zubin
    'amandal@valorwealthpartners.com': [
        'ed@valorwealthpartners.com',
        'zubink@valorwealthpartners.com',
    ],
}


class Command(BaseCommand):
    help = 'Load test users and delegate assignments for SSO testing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview what would be created without making changes',
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Remove existing test users (by contact_id) before loading',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        clear = options['clear']

        if dry_run:
            self.stdout.write(self.style.WARNING('=== DRY RUN — no changes will be made ===\n'))

        # Step 1: Clear if requested
        if clear:
            contact_ids = [u['contact_id'] for u in TEST_USERS]
            existing = User.objects.filter(contact_id__in=contact_ids)
            count = existing.count()
            if dry_run:
                self.stdout.write(f'Would delete {count} existing test users')
            else:
                # Deleting users cascades to MemberDelegate
                existing.delete()
                self.stdout.write(self.style.WARNING(f'Deleted {count} existing test users'))

        # Step 2: Create users
        self.stdout.write(self.style.HTTP_INFO('\n--- Creating Users ---'))
        users_created = 0
        users_updated = 0
        users_skipped = 0

        for u in TEST_USERS:
            existing = User.objects.filter(contact_id=u['contact_id']).first()
            if not existing:
                existing = User.objects.filter(email__iexact=u['email']).first()

            if existing and not clear:
                # Update fields if they differ
                changed = False
                for field in ['first_name', 'last_name', 'workshop_code', 'role']:
                    if getattr(existing, field) != u[field]:
                        if dry_run:
                            self.stdout.write(
                                f'  Would update {u["email"]}: {field} '
                                f'{getattr(existing, field)!r} → {u[field]!r}'
                            )
                        else:
                            setattr(existing, field, u[field])
                        changed = True
                if not existing.contact_id and u['contact_id']:
                    if not dry_run:
                        existing.contact_id = u['contact_id']
                    changed = True
                if changed:
                    if not dry_run:
                        existing.save()
                    users_updated += 1
                else:
                    users_skipped += 1
                continue

            if dry_run:
                self.stdout.write(
                    f'  Would create: {u["first_name"]} {u["last_name"]} '
                    f'({u["email"]}) role={u["role"]} ws={u["workshop_code"]}'
                )
            else:
                username = u['email'].split('@')[0].lower()
                # Ensure unique username
                base = username
                counter = 1
                while User.objects.filter(username=username).exists():
                    username = f'{base}{counter}'
                    counter += 1

                user = User.objects.create(
                    username=username,
                    email=u['email'],
                    first_name=u['first_name'],
                    last_name=u['last_name'],
                    contact_id=u['contact_id'],
                    role=u['role'],
                    workshop_code=u['workshop_code'],
                    is_active=True,
                )
                user.set_unusable_password()
                user.save()
                self.stdout.write(
                    f'  Created: {user.get_full_name()} ({user.email}) '
                    f'role={user.role} ws={user.workshop_code}'
                )
            users_created += 1

        self.stdout.write(
            f'\nUsers: {users_created} created, {users_updated} updated, '
            f'{users_skipped} unchanged'
        )

        # Step 3: Create delegate assignments
        self.stdout.write(self.style.HTTP_INFO('\n--- Creating Delegate Assignments ---'))
        assignments_created = 0
        assignments_skipped = 0

        for delegate_email, member_emails in DELEGATE_ASSIGNMENTS.items():
            delegate_user = User.objects.filter(email__iexact=delegate_email).first()
            if not delegate_user:
                self.stdout.write(
                    self.style.ERROR(f'  Delegate not found: {delegate_email}')
                )
                continue

            for member_email in member_emails:
                member_user = User.objects.filter(email__iexact=member_email).first()
                if not member_user:
                    self.stdout.write(
                        self.style.ERROR(f'  Member not found: {member_email}')
                    )
                    continue

                exists = MemberDelegate.objects.filter(
                    member=member_user, delegate=delegate_user
                ).exists()

                if exists:
                    assignments_skipped += 1
                    continue

                if dry_run:
                    self.stdout.write(
                        f'  Would assign: {delegate_user.get_full_name()} '
                        f'→ {member_user.get_full_name()}'
                    )
                else:
                    MemberDelegate.objects.create(
                        member=member_user,
                        delegate=delegate_user,
                    )
                    self.stdout.write(
                        f'  Assigned: {delegate_user.get_full_name()} '
                        f'→ {member_user.get_full_name()}'
                    )
                assignments_created += 1

        self.stdout.write(
            f'\nDelegates: {assignments_created} created, '
            f'{assignments_skipped} already existed'
        )

        # Summary
        self.stdout.write(self.style.SUCCESS(
            f'\n=== Done: {users_created} users, {assignments_created} assignments ==='
        ))
        if dry_run:
            self.stdout.write(self.style.WARNING('(DRY RUN — nothing was actually created)'))
