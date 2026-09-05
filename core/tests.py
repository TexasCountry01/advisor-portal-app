from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from cases.models import Case


class CaseMetricsReportSortingTest(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username='admin_sort_test',
            email='admin_sort_test@example.com',
            password='testpass123',
            role='administrator',
            first_name='Admin',
            last_name='User',
        )

        self.member_a = User.objects.create_user(
            username='member_a_sort',
            email='member_a_sort@example.com',
            password='testpass123',
            role='member',
            first_name='Zed',
            last_name='Member',
        )
        self.member_b = User.objects.create_user(
            username='member_b_sort',
            email='member_b_sort@example.com',
            password='testpass123',
            role='member',
            first_name='Amy',
            last_name='Member',
        )

        self.case_1 = Case.objects.create(
            external_case_id='SORT-CASE-001',
            workshop_code='W-001',
            member=self.member_a,
            employee_first_name='First',
            employee_last_name='Employee',
            client_email='first@example.com',
            status='completed',
            assigned_to=self.admin,
            date_submitted=timezone.now() - timezone.timedelta(days=3),
            date_completed=timezone.now() - timezone.timedelta(days=1),
            date_due=timezone.now() + timezone.timedelta(days=5),
            urgency='normal',
            actual_release_date=timezone.now(),
        )
        self.case_2 = Case.objects.create(
            external_case_id='SORT-CASE-002',
            workshop_code='W-002',
            member=self.member_b,
            employee_first_name='Second',
            employee_last_name='Employee',
            client_email='second@example.com',
            status='completed',
            assigned_to=self.admin,
            date_submitted=timezone.now() - timezone.timedelta(days=2),
            date_completed=timezone.now() - timezone.timedelta(days=2),
            date_due=timezone.now() + timezone.timedelta(days=3),
            urgency='rush',
            actual_release_date=timezone.now() - timezone.timedelta(days=1),
        )

    def test_case_metrics_report_can_sort_by_member_name(self):
        self.client.force_login(self.admin)

        response = self.client.get(reverse('performance_metrics_report'), {'sort': 'member'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Amy Member')
        self.assertContains(response, 'Zed Member')
        self.assertLess(response.content.index(b'Amy Member'), response.content.index(b'Zed Member'))

    def test_case_metrics_report_has_employee_find_shortcut(self):
        self.client.force_login(self.admin)

        response = self.client.get(reverse('performance_metrics_report'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Find employee')
        self.assertContains(response, 'employee-find-input')

    def test_case_metrics_report_defaults_end_date_to_yesterday(self):
        self.client.force_login(self.admin)

        response = self.client.get(reverse('performance_metrics_report'))

        self.assertEqual(response.status_code, 200)
        expected_yesterday = (timezone.localtime(timezone.now()).date() - timezone.timedelta(days=1)).strftime('%Y-%m-%d')
        self.assertContains(response, f'value="{expected_yesterday}"')

    def test_case_metrics_report_shows_tech_notes_to_reviewer(self):
        from cases.models import CaseReviewHistory

        CaseReviewHistory.objects.create(
            case=self.case_1,
            original_technician=self.admin,
            review_action='submitted_for_review',
            review_notes='Case submitted for review by Admin User — Notes: Please double-check the survivor benefit election.',
            tech_notes='Please double-check the survivor benefit election.',
        )

        self.client.force_login(self.admin)

        response = self.client.get(reverse('performance_metrics_report'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Please double-check the survivor benefit election.')

    def test_case_metrics_report_review_count_excludes_reviewer_responses(self):
        from cases.models import CaseReviewHistory

        # One full review cycle: tech submits, reviewer requests revisions,
        # tech resubmits, reviewer approves. The tech only sent it for review
        # twice — the count should be 2, not 4.
        CaseReviewHistory.objects.create(
            case=self.case_1,
            original_technician=self.admin,
            review_action='submitted_for_review',
            review_notes='Case submitted for review by Admin User',
        )
        CaseReviewHistory.objects.create(
            case=self.case_1,
            original_technician=self.admin,
            reviewed_by=self.admin,
            review_action='revisions_requested',
            review_notes='Please fix the date.',
        )
        CaseReviewHistory.objects.create(
            case=self.case_1,
            original_technician=self.admin,
            review_action='resubmitted',
            review_notes='Case resubmitted for review by Admin User',
        )
        CaseReviewHistory.objects.create(
            case=self.case_1,
            original_technician=self.admin,
            reviewed_by=self.admin,
            review_action='approved',
            review_notes='Looks good.',
        )

        self.client.force_login(self.admin)

        response = self.client.get(reverse('performance_metrics_report'))

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        row_start = content.index('W-001')
        # Grab a chunk of the row content following the workshop code to inspect nearby cells
        row_chunk = content[row_start:row_start + 4000]
        self.assertIn('>2<', row_chunk)
        self.assertNotIn('>4<', row_chunk)

    def test_case_metrics_report_sorts_due_date_chronologically_across_year_boundary(self):
        from datetime import date

        # Both complete "today" so they land in the default report window,
        # but their due dates straddle a year boundary. A naive string sort
        # would incorrectly place 01/05/26 before 12/28/25.
        Case.objects.create(
            external_case_id='SORT-CASE-JAN',
            workshop_code='W-JAN',
            member=self.member_a,
            employee_first_name='January',
            employee_last_name='Case',
            client_email='january@example.com',
            status='completed',
            assigned_to=self.admin,
            date_submitted=timezone.now() - timezone.timedelta(days=3),
            date_completed=timezone.now(),
            date_due=timezone.make_aware(timezone.datetime(2026, 1, 5)).date(),
            urgency='normal',
        )
        Case.objects.create(
            external_case_id='SORT-CASE-DEC',
            workshop_code='W-DEC',
            member=self.member_a,
            employee_first_name='December',
            employee_last_name='Case',
            client_email='december@example.com',
            status='completed',
            assigned_to=self.admin,
            date_submitted=timezone.now() - timezone.timedelta(days=3),
            date_completed=timezone.now(),
            date_due=timezone.make_aware(timezone.datetime(2025, 12, 28)).date(),
            urgency='normal',
        )

        self.client.force_login(self.admin)

        today_str = timezone.localtime(timezone.now()).date().strftime('%Y-%m-%d')
        response = self.client.get(reverse('performance_metrics_report'), {
            'sort': 'due',
            'date_from': today_str,
            'date_to': today_str,
        })

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        # Ascending sort: December 2025 due date should come before January 2026
        self.assertLess(content.index('12/28/25'), content.index('01/05/26'))

    def test_case_metrics_report_reviewer_action_summarizes_full_history(self):
        from cases.models import CaseReviewHistory

        # case_1: submitted straight to approved — no kickbacks.
        CaseReviewHistory.objects.create(
            case=self.case_1,
            original_technician=self.admin,
            review_action='submitted_for_review',
            review_notes='Case submitted for review by Admin User',
        )
        CaseReviewHistory.objects.create(
            case=self.case_1,
            original_technician=self.admin,
            reviewed_by=self.admin,
            review_action='approved',
            review_notes='Looks good.',
        )

        # case_2: reviewer sent it back once, then approved after resubmission.
        CaseReviewHistory.objects.create(
            case=self.case_2,
            original_technician=self.admin,
            review_action='submitted_for_review',
            review_notes='Case submitted for review by Admin User',
        )
        CaseReviewHistory.objects.create(
            case=self.case_2,
            original_technician=self.admin,
            reviewed_by=self.admin,
            review_action='revisions_requested',
            review_notes='Please fix the date.',
        )
        CaseReviewHistory.objects.create(
            case=self.case_2,
            original_technician=self.admin,
            review_action='resubmitted',
            review_notes='Case resubmitted for review by Admin User',
        )
        CaseReviewHistory.objects.create(
            case=self.case_2,
            original_technician=self.admin,
            reviewed_by=self.admin,
            review_action='approved',
            review_notes='Approved now.',
        )

        self.client.force_login(self.admin)

        response = self.client.get(reverse('performance_metrics_report'))

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn('Approved As-Is', content)
        self.assertIn('Approved After Revisions', content)
        # The old generic "Approved" label (without qualifier) should no
        # longer appear on its own for either case.
        self.assertNotIn('>Approved<', content)

    def test_case_metrics_report_reviewer_notes_include_earlier_feedback(self):
        from cases.models import CaseReviewHistory

        # Case kicked back once with substantive feedback, then approved
        # with no additional notes on the final approval (the common case,
        # since notes are optional on approval but required on revisions).
        CaseReviewHistory.objects.create(
            case=self.case_1,
            original_technician=self.admin,
            review_action='submitted_for_review',
            review_notes='Case submitted for review by Admin User',
        )
        CaseReviewHistory.objects.create(
            case=self.case_1,
            original_technician=self.admin,
            reviewed_by=self.admin,
            review_action='revisions_requested',
            review_notes='Please correct the survivor benefit percentage.',
        )
        CaseReviewHistory.objects.create(
            case=self.case_1,
            original_technician=self.admin,
            review_action='resubmitted',
            review_notes='Case resubmitted for review by Admin User',
        )
        CaseReviewHistory.objects.create(
            case=self.case_1,
            original_technician=self.admin,
            reviewed_by=self.admin,
            review_action='approved',
            review_notes='',
        )

        self.client.force_login(self.admin)

        response = self.client.get(reverse('performance_metrics_report'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Please correct the survivor benefit percentage.')

    def test_case_metrics_report_distinguishes_mod_from_pf_error(self):
        # A routine mod (member-requested change), no ProFeds error.
        Case.objects.create(
            external_case_id='SORT-CASE-MOD',
            workshop_code='W-MOD',
            member=self.member_a,
            employee_first_name='Regular',
            employee_last_name='Mod',
            client_email='regularmod@example.com',
            status='completed',
            assigned_to=self.admin,
            date_submitted=timezone.now() - timezone.timedelta(days=2),
            date_completed=timezone.now() - timezone.timedelta(days=1),
            date_due=timezone.now() + timezone.timedelta(days=5),
            urgency='normal',
            original_case=self.case_1,
            has_profeds_error=False,
        )
        # A mod caused by a ProFeds error.
        Case.objects.create(
            external_case_id='SORT-CASE-PFERR',
            workshop_code='W-PFERR',
            member=self.member_a,
            employee_first_name='Error',
            employee_last_name='Mod',
            client_email='errormod@example.com',
            status='completed',
            assigned_to=self.admin,
            date_submitted=timezone.now() - timezone.timedelta(days=2),
            date_completed=timezone.now() - timezone.timedelta(days=1),
            date_due=timezone.now() + timezone.timedelta(days=5),
            urgency='normal',
            original_case=self.case_2,
            has_profeds_error=True,
        )

        self.client.force_login(self.admin)

        response = self.client.get(reverse('performance_metrics_report'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '>MOD<')
        self.assertContains(response, '>PF ERR<')
