from django.test import TestCase, Client
from django.urls import reverse

from accounts.models import User, DelegateRequest, MemberDelegate
from cases.models import Case


class DashboardSearchTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username='admin1',
            password='Password123!',
            role='administrator',
            first_name='System',
            last_name='Admin',
        )
        self.case = Case.objects.create(
            external_case_id='WS-2026-0001',
            workshop_code='WS007',
            employee_first_name='Jane',
            employee_last_name='Smith',
            client_email='jane.smith@example.com',
        )

    def test_admin_dashboard_search_ignores_case_id_but_matches_workshop_and_employee_name(self):
        client = Client()
        client.force_login(self.admin)

        response = client.get(reverse('cases:admin_dashboard'), {'search': 'WS-2026-0001'})
        self.assertEqual(list(response.context['cases'].object_list), [])

        response = client.get(reverse('cases:admin_dashboard'), {'search': 'WS007'})
        self.assertIn(self.case, response.context['cases'].object_list)

        response = client.get(reverse('cases:admin_dashboard'), {'search': 'Jane Smith'})
        self.assertIn(self.case, response.context['cases'].object_list)

    def test_admin_dashboard_shows_pending_delegate_requests_banner(self):
        member = User.objects.create_user(
            username='member1',
            password='Password123!',
            role='member',
            first_name='Alice',
            last_name='Member',
        )
        request = DelegateRequest.objects.create(
            requested_by=member,
            request_type='add',
            delegate_name='Bob Delegate',
            delegate_email='bob@example.com',
            notes='Please add Bob as a delegate for my workshop account.',
            status='pending',
        )

        client = Client()
        client.force_login(self.admin)

        response = client.get(reverse('cases:admin_dashboard'))

        self.assertIn('pending_delegate_requests', response.context)
        self.assertIn(request, response.context['pending_delegate_requests'])
        self.assertContains(response, 'Delegate Action Pending')
        self.assertContains(response, 'Bob Delegate')

    def test_admin_can_clear_pending_delegate_request_from_dashboard(self):
        member = User.objects.create_user(
            username='member2',
            password='Password123!',
            role='member',
            first_name='Carol',
            last_name='Member',
        )
        request = DelegateRequest.objects.create(
            requested_by=member,
            request_type='add',
            delegate_name='Bob Delegate',
            delegate_email='bob@example.com',
            notes='Add Bob as my delegate.',
            status='pending',
        )

        client = Client()
        client.force_login(self.admin)

        response = client.post(
            reverse('clear_delegate_request', args=[request.pk]),
            follow=True,
        )

        request.refresh_from_db()
        self.assertEqual(request.status, 'dismissed')
        self.assertEqual(request.processed_by, self.admin)
        self.assertRedirects(response, reverse('cases:admin_dashboard'))
