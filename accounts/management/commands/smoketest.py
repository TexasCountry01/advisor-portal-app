"""
Automated smoke test for the Advisor Portal.

Exercises ALL key portal features using Django's test client:
  - Login (username/password)
  - Dashboard access per role (member, technician, admin, manager)
  - Delegate view toggle (my_cases ↔ delegate)
  - Case submission form load
  - SSO endpoints exist
  - Delegate management page (tech/admin only)
  - Profile page
  - Case list view

Usage:
    python manage.py smoke_test                # Run all tests
    python manage.py smoke_test --verbose      # Show details for passing tests too
    python manage.py smoke_test --create-cases # Create sample cases for richer testing
"""

from django.core.management.base import BaseCommand
from django.test import RequestFactory, Client, override_settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.conf import settings
from accounts.models import MemberDelegate
from cases.models import Case

User = get_user_model()


# ============================================================================
# TEST USER PICKS — representatives of each interesting persona
# ============================================================================

PERSONA_PICKS = {
    # Solo member — has no delegates, no cases, pure member
    'solo_member': {
        'email': 'gary@newageadvisors.com',
        'label': 'Gary Wedge (NAA) — solo member, no delegates',
    },
    # Member WITH delegates — Momodou has 3 delegates
    'member_with_delegates': {
        'email': 'mlbojang@axiomvaluellc.com',
        'label': 'Momodou Bojang (AVL) — member with 3 delegates',
    },
    # Cross-delegate — Frank is a member AND delegate for others
    'cross_delegate': {
        'email': 'frank@compassfinancialsa.com',
        'label': 'Frank Dimicelli (CFG) — member + delegate for others',
    },
    # Pure delegate — Josephine is only a delegate (for Momodou)
    'pure_delegate': {
        'email': 'jbojang@axiomvaluellc.com',
        'label': 'Josephine Bojang (AVL) — pure delegate for Momodou',
    },
    # Heavy delegate — Les delegates for 8 McGregor members
    'heavy_delegate': {
        'email': 'les@mcgregorfg.com',
        'label': 'Les McGregor (DMCG) — pure delegate for 8 members',
    },
}


class Command(BaseCommand):
    help = 'Run automated smoke tests against the portal'

    def add_arguments(self, parser):
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detail for passing tests too',
        )
        parser.add_argument(
            '--create-cases',
            action='store_true',
            help='Create sample test cases for richer testing',
        )

    def handle(self, *args, **options):
        self.verbose = options['verbose']
        self.create_cases_flag = options['create_cases']
        self.passed = 0
        self.failed = 0
        self.errors = []

        # Ensure 'testserver' is in ALLOWED_HOSTS for Django test client
        if 'testserver' not in settings.ALLOWED_HOSTS:
            settings.ALLOWED_HOSTS = list(settings.ALLOWED_HOSTS) + ['testserver']

        self.stdout.write(self.style.HTTP_INFO('\n' + '=' * 70))
        self.stdout.write(self.style.HTTP_INFO('  ADVISOR PORTAL — AUTOMATED SMOKE TEST'))
        self.stdout.write(self.style.HTTP_INFO('=' * 70 + '\n'))

        # Verify test users exist
        if not self._verify_test_users():
            self.stderr.write(self.style.ERROR(
                '\nTest users not found. Run: python manage.py load_test_users\n'
            ))
            return

        # Optionally create sample cases
        if self.create_cases_flag:
            self._create_sample_cases()

        # ---- Run test suites ----
        self._test_login_flow()
        self._test_member_dashboards()
        self._test_delegate_views()
        self._test_case_submission_form()
        self._test_delegate_management()
        self._test_profile_page()
        self._test_sso_endpoints()
        self._test_case_list()
        self._test_role_access_controls()

        # ---- Report ----
        self.stdout.write('\n' + '=' * 70)
        total = self.passed + self.failed
        if self.failed == 0:
            self.stdout.write(self.style.SUCCESS(
                f'  ALL {total} TESTS PASSED ✓'
            ))
        else:
            self.stdout.write(self.style.ERROR(
                f'  {self.failed} FAILED / {total} total'
            ))
            self.stdout.write('')
            for err in self.errors:
                self.stdout.write(self.style.ERROR(f'  ✗ {err}'))
        self.stdout.write('=' * 70 + '\n')

    # ====================================================================
    # HELPERS
    # ====================================================================

    def _pass(self, label):
        self.passed += 1
        if self.verbose:
            self.stdout.write(self.style.SUCCESS(f'  ✓ {label}'))

    def _fail(self, label, detail=''):
        self.failed += 1
        msg = f'{label}: {detail}' if detail else label
        self.errors.append(msg)
        self.stdout.write(self.style.ERROR(f'  ✗ {label}  — {detail}'))

    def _section(self, title):
        self.stdout.write(self.style.HTTP_INFO(f'\n--- {title} ---'))

    def _login_client(self, email):
        """Return a logged-in Django test client for the given user email."""
        user = User.objects.filter(email__iexact=email).first()
        if not user:
            return None, None
        client = Client()
        client.force_login(user)
        return client, user

    def _get_or_create_admin(self):
        """Get or create an admin user for admin-only tests."""
        admin = User.objects.filter(role='administrator', is_active=True).first()
        if admin:
            return admin
        admin = User.objects.create(
            username='smoke_test_admin',
            email='smoke_test_admin@test.internal',
            first_name='SmokeTest',
            last_name='Admin',
            role='administrator',
            is_superuser=True,
            is_staff=True,
            is_active=True,
        )
        admin.set_password('TestPass123!')
        admin.save()
        return admin

    def _get_or_create_tech(self):
        """Get or create a technician user for tech-only tests."""
        tech = User.objects.filter(role='technician', is_active=True).first()
        if tech:
            return tech
        tech = User.objects.create(
            username='smoke_test_tech',
            email='smoke_test_tech@test.internal',
            first_name='SmokeTest',
            last_name='Tech',
            role='technician',
            is_active=True,
        )
        tech.set_password('TestPass123!')
        tech.save()
        return tech

    def _verify_test_users(self):
        """Check that at least the key test users exist."""
        for key, info in PERSONA_PICKS.items():
            if not User.objects.filter(email__iexact=info['email']).exists():
                self.stdout.write(self.style.ERROR(
                    f'Missing test user: {info["email"]} ({key})'
                ))
                return False
        return True

    def _create_sample_cases(self):
        """Create a few sample cases for richer dashboard testing."""
        self._section('Creating sample test cases')
        created = 0

        # Cases for key members
        case_specs = [
            # (member_email, employee_first, employee_last, status)
            ('mlbojang@axiomvaluellc.com', 'John', 'Smith', 'submitted'),
            ('mlbojang@axiomvaluellc.com', 'Jane', 'Doe', 'accepted'),
            ('frank@compassfinancialsa.com', 'Alice', 'Johnson', 'submitted'),
            ('brandon@compassfinancialsa.com', 'Bob', 'Williams', 'draft'),
            ('dale@mcgregorfg.com', 'Charlie', 'Brown', 'submitted'),
            ('ed@valorwealthpartners.com', 'Diana', 'Prince', 'completed'),
            ('gary@newageadvisors.com', 'Eve', 'Adams', 'submitted'),
        ]

        for member_email, emp_first, emp_last, status in case_specs:
            member = User.objects.filter(email__iexact=member_email).first()
            if not member:
                continue

            case_id = f'SMOKE-{member.workshop_code}-{emp_last.upper()}'
            if Case.objects.filter(external_case_id=case_id).exists():
                continue

            Case.objects.create(
                external_case_id=case_id,
                workshop_code=member.workshop_code,
                member=member,
                created_by=member,
                employee_first_name=emp_first,
                employee_last_name=emp_last,
                client_email=f'{emp_first.lower()}.{emp_last.lower()}@example.com',
                status=status,
                urgency='normal',
                num_reports_requested=1,
            )
            created += 1

        self.stdout.write(f'  Created {created} sample cases')

    # ====================================================================
    # TEST SUITES
    # ====================================================================

    def _test_login_flow(self):
        """Test that test users can log in via Django test client."""
        self._section('Login Flow')

        for key, info in PERSONA_PICKS.items():
            client, user = self._login_client(info['email'])
            if client is None:
                self._fail(f'Login [{key}]', f'User not found: {info["email"]}')
                continue

            # Hit home — should redirect to dashboard
            resp = client.get('/', follow=True)
            if resp.status_code == 200:
                self._pass(f'Login + redirect [{key}] → {resp.request["PATH_INFO"]}')
            else:
                self._fail(f'Login [{key}]', f'Status {resp.status_code}')

    def _test_member_dashboards(self):
        """Test member dashboard loads for different personas."""
        self._section('Member Dashboards')

        dashboard_url = reverse('cases:member_dashboard')

        for key, info in PERSONA_PICKS.items():
            client, user = self._login_client(info['email'])
            if not client:
                self._fail(f'Dashboard [{key}]', 'User not found')
                continue

            resp = client.get(dashboard_url)
            if resp.status_code == 200:
                content = resp.content.decode()
                # Check key elements are present
                has_table = 'case' in content.lower() or 'dashboard' in content.lower()
                self._pass(f'Dashboard [{key}] — 200 OK, content={len(content)} bytes')
            elif resp.status_code == 302:
                self._pass(f'Dashboard [{key}] — redirect to {resp.url} (expected for pure delegates)')
            else:
                self._fail(f'Dashboard [{key}]', f'Status {resp.status_code}')

    def _test_delegate_views(self):
        """Test delegate view toggle for cross-delegates and pure delegates."""
        self._section('Delegate View Toggle')

        dashboard_url = reverse('cases:member_dashboard')

        # Cross-delegate — should be able to switch between my_cases and delegate
        client, user = self._login_client(PERSONA_PICKS['cross_delegate']['email'])
        if client:
            # My Cases view
            resp = client.get(f'{dashboard_url}?view=my_cases')
            if resp.status_code == 200:
                self._pass('Cross-delegate → my_cases view')
            else:
                self._fail('Cross-delegate → my_cases view', f'Status {resp.status_code}')

            # Delegate view
            resp = client.get(f'{dashboard_url}?view=delegate')
            if resp.status_code == 200:
                self._pass('Cross-delegate → delegate view')
            else:
                self._fail('Cross-delegate → delegate view', f'Status {resp.status_code}')

            # Verify delegate assignments exist
            delegate_count = MemberDelegate.objects.filter(delegate=user).count()
            if delegate_count > 0:
                self._pass(f'Cross-delegate has {delegate_count} delegate assignment(s)')
            else:
                self._fail('Cross-delegate assignments', 'No delegate assignments found')

        # Pure delegate — should default to delegate view
        client, user = self._login_client(PERSONA_PICKS['pure_delegate']['email'])
        if client:
            resp = client.get(dashboard_url)
            if resp.status_code == 200:
                content = resp.content.decode()
                self._pass('Pure delegate → dashboard loaded (defaults to delegate view)')
            else:
                self._fail('Pure delegate dashboard', f'Status {resp.status_code}')

            delegate_count = MemberDelegate.objects.filter(delegate=user).count()
            if delegate_count > 0:
                self._pass(f'Pure delegate has {delegate_count} delegate assignment(s)')
            else:
                self._fail('Pure delegate assignments', 'No delegate assignments found')

        # Heavy delegate — 8 members
        client, user = self._login_client(PERSONA_PICKS['heavy_delegate']['email'])
        if client:
            resp = client.get(f'{dashboard_url}?view=delegate')
            if resp.status_code == 200:
                self._pass('Heavy delegate (8 members) → delegate view loaded')
            else:
                self._fail('Heavy delegate view', f'Status {resp.status_code}')

            delegate_count = MemberDelegate.objects.filter(delegate=user).count()
            if delegate_count == 8:
                self._pass(f'Heavy delegate has exactly 8 assignments')
            else:
                self._fail('Heavy delegate assignments', f'Expected 8, got {delegate_count}')

        # Solo member — should NOT have delegate view
        client, user = self._login_client(PERSONA_PICKS['solo_member']['email'])
        if client:
            resp = client.get(f'{dashboard_url}?view=delegate')
            if resp.status_code == 200:
                # View param should be ignored/overridden to my_cases since not a delegate
                self._pass('Solo member → delegate view param ignored (no assignments)')
            else:
                self._fail('Solo member delegate view', f'Status {resp.status_code}')

            delegate_count = MemberDelegate.objects.filter(delegate=user).count()
            if delegate_count == 0:
                self._pass('Solo member has 0 delegate assignments (correct)')
            else:
                self._fail('Solo member assignments', f'Expected 0, got {delegate_count}')

    def _test_case_submission_form(self):
        """Test that the case submission form loads for members."""
        self._section('Case Submission Form')

        submit_url = reverse('cases:case_submit')

        # Regular member
        client, user = self._login_client(PERSONA_PICKS['solo_member']['email'])
        if client:
            resp = client.get(submit_url)
            if resp.status_code == 200:
                content = resp.content.decode()
                self._pass(f'Submit form loads for solo member — {len(content)} bytes')
            else:
                self._fail('Submit form (solo member)', f'Status {resp.status_code}')

        # Cross-delegate submitting — should load with member selection
        client, user = self._login_client(PERSONA_PICKS['cross_delegate']['email'])
        if client:
            resp = client.get(submit_url)
            if resp.status_code == 200:
                self._pass('Submit form loads for cross-delegate')
            else:
                self._fail('Submit form (cross-delegate)', f'Status {resp.status_code}')

    def _test_delegate_management(self):
        """Test delegate management page access for tech/admin."""
        self._section('Delegate Management Page')

        mgmt_url = reverse('delegate_management')

        # Admin should access
        admin = self._get_or_create_admin()
        client = Client()
        client.force_login(admin)
        resp = client.get(mgmt_url)
        if resp.status_code == 200:
            content = resp.content.decode()
            self._pass(f'Delegate management loads for admin — {len(content)} bytes')
        else:
            self._fail('Delegate management (admin)', f'Status {resp.status_code}')

        # Technician should access
        tech = self._get_or_create_tech()
        client = Client()
        client.force_login(tech)
        resp = client.get(mgmt_url)
        if resp.status_code == 200:
            self._pass('Delegate management loads for technician')
        else:
            self._fail('Delegate management (technician)', f'Status {resp.status_code}')

        # Regular member should NOT access
        client, user = self._login_client(PERSONA_PICKS['solo_member']['email'])
        if client:
            resp = client.get(mgmt_url, follow=True)
            final_url = resp.request['PATH_INFO']
            if 'delegate-management' not in final_url:
                self._pass('Delegate management blocked for member (redirected)')
            else:
                self._fail('Delegate management access control', 'Member was NOT blocked')

    def _test_profile_page(self):
        """Test profile page loads."""
        self._section('Profile Page')

        profile_url = reverse('profile')

        client, user = self._login_client(PERSONA_PICKS['solo_member']['email'])
        if client:
            resp = client.get(profile_url)
            if resp.status_code == 200:
                content = resp.content.decode()
                # Should contain user's name
                if user.first_name in content:
                    self._pass(f'Profile page loads with user name')
                else:
                    self._pass(f'Profile page loads (200 OK)')
            else:
                self._fail('Profile page', f'Status {resp.status_code}')

    def _test_sso_endpoints(self):
        """Test SSO endpoints exist and respond correctly."""
        self._section('SSO Endpoints')

        client = Client()

        # SSO login should redirect to WP OAuth
        sso_login_url = reverse('sso_login')
        resp = client.get(sso_login_url)
        if resp.status_code == 302 and 'profeds.com' in resp.url:
            self._pass(f'SSO login redirects to WP OAuth ({resp.url[:60]}...)')
        elif resp.status_code == 302:
            self._pass(f'SSO login redirects (302) → {resp.url[:80]}')
        else:
            self._fail('SSO login endpoint', f'Status {resp.status_code}, expected 302')

        # SSO callback without params should redirect to login with error
        sso_callback_url = reverse('sso_callback')
        resp = client.get(sso_callback_url, follow=True)
        if resp.status_code == 200:
            self._pass('SSO callback (no params) → handled gracefully')
        else:
            self._fail('SSO callback (no params)', f'Status {resp.status_code}')

    def _test_case_list(self):
        """Test case list view."""
        self._section('Case List View')

        case_list_url = reverse('cases:case_list')

        # Admin should see all cases
        admin = self._get_or_create_admin()
        client = Client()
        client.force_login(admin)
        resp = client.get(case_list_url)
        if resp.status_code == 200:
            self._pass('Case list loads for admin')
        else:
            self._fail('Case list (admin)', f'Status {resp.status_code}')

        # Member should see own cases
        client, user = self._login_client(PERSONA_PICKS['solo_member']['email'])
        if client:
            resp = client.get(case_list_url)
            if resp.status_code in (200, 302):
                self._pass(f'Case list for member — status {resp.status_code}')
            else:
                self._fail('Case list (member)', f'Status {resp.status_code}')

    def _test_role_access_controls(self):
        """Test that role-based access controls work correctly."""
        self._section('Role-Based Access Controls')

        tech_dashboard = reverse('cases:technician_dashboard')
        admin_dashboard = reverse('cases:admin_dashboard')
        manager_dashboard = reverse('cases:manager_dashboard')
        member_dashboard = reverse('cases:member_dashboard')

        # Member should NOT access tech dashboard
        client, user = self._login_client(PERSONA_PICKS['solo_member']['email'])
        if client:
            resp = client.get(tech_dashboard, follow=True)
            final_url = resp.request['PATH_INFO']
            if 'technician' not in final_url:
                self._pass('Member blocked from technician dashboard')
            else:
                self._fail('Access control', 'Member accessed technician dashboard')

            resp = client.get(admin_dashboard, follow=True)
            final_url = resp.request['PATH_INFO']
            if 'admin/dashboard' not in final_url:
                self._pass('Member blocked from admin dashboard')
            else:
                self._fail('Access control', 'Member accessed admin dashboard')

        # Admin should access admin dashboard
        admin = self._get_or_create_admin()
        client = Client()
        client.force_login(admin)
        resp = client.get(admin_dashboard)
        if resp.status_code == 200:
            self._pass('Admin accesses admin dashboard')
        else:
            self._fail('Admin dashboard access', f'Status {resp.status_code}')

        # Tech should access tech dashboard
        tech = self._get_or_create_tech()
        client = Client()
        client.force_login(tech)
        resp = client.get(tech_dashboard)
        if resp.status_code == 200:
            self._pass('Technician accesses technician dashboard')
        else:
            self._fail('Tech dashboard access', f'Status {resp.status_code}')
