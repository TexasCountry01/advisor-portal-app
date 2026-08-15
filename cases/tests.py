from django.test import TestCase, Client
from django.urls import reverse

from accounts.models import User
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
