"""
Tests for the GHL user-provisioning enhancements:
  1. Manager provisioning authority (GHL Sync Review, create-user, link,
     manual sync, Manage Delegates entry point).
  2. Name normalization (smart_case) at the GHL -> Portal data boundary.
  3. Existing-Portal-user refresh from GHL (first_name, last_name, email,
     workshop_code only -- role/permissions/delegate relationships protected,
     never creates a new User).

Kept in a dedicated module (accounts/tests_ghl_provisioning.py) rather than
appended to accounts/tests.py, matching this project's existing multi-file-
per-app test convention (see e.g. advisor-portal-app's fact_finder_content
app: tests.py + tests_rules.py + tests_api.py).

GHL is never actually called -- every test patches
accounts.services.provisioning_sync.fetch_ghl_contacts (the single lowest-
level dependency), so these tests need no GHL_PRIVATE_TOKEN/GHL_LOCATION_ID
configuration and never make a real network call.
"""
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse

from accounts.models import MemberDelegate, ProvisioningAlert
from accounts.name_utils import smart_case
from accounts.views import can_create_user, can_manage_provisioning
from accounts.ghl_client import normalize_contact
from accounts.sso import _extract_user_data
from accounts.services.provisioning_sync import (
    compute_new_ghl_contacts,
    compute_missing_tag_users,
    sync_existing_user_ghl_fields,
)

User = get_user_model()


def ghl_contact(contact_id='', email='', first_name='', last_name='',
                 workshop_code='', tags=None):
    """Build a GHL contact dict already shaped like ghl_client.normalize_contact()'s
    output -- the exact shape accounts.services.provisioning_sync consumes."""
    return {
        'contact_id': contact_id,
        'email': email,
        'first_name': first_name,
        'last_name': last_name,
        'workshop_code': workshop_code,
        'tags': tags if tags is not None else ['Portal access: Member'],
    }


# ============================================================================
# AUTHORIZATION (items 1-6)
# ============================================================================

class CanManageProvisioningHelperTest(TestCase):
    """Unit tests for the shared can_manage_provisioning() helper itself."""

    def test_administrator_can_manage_provisioning(self):
        user = User.objects.create_user(username='admin_auth', password='x', role='administrator')
        self.assertTrue(can_manage_provisioning(user))

    def test_manager_can_manage_provisioning(self):
        user = User.objects.create_user(username='manager_auth', password='x', role='manager')
        self.assertTrue(can_manage_provisioning(user))

    def test_technician_cannot_manage_provisioning(self):
        user = User.objects.create_user(username='tech_auth', password='x', role='technician')
        self.assertFalse(can_manage_provisioning(user))

    def test_member_cannot_manage_provisioning(self):
        user = User.objects.create_user(username='member_auth', password='x', role='member')
        self.assertFalse(can_manage_provisioning(user))


class GhlSyncAuthorizationTest(TestCase):
    """Server-side authorization for the GHL Sync Review page (items 1, 2, 5, 6)."""

    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_user(username='admin_ghl', password='x', role='administrator')
        self.manager = User.objects.create_user(username='manager_ghl', password='x', role='manager')
        self.technician = User.objects.create_user(username='tech_ghl', password='x', role='technician')
        self.member = User.objects.create_user(username='member_ghl', password='x', role='member')

    @patch('accounts.services.provisioning_sync.fetch_ghl_contacts')
    def test_administrator_can_access_ghl_sync(self, mock_fetch):
        mock_fetch.return_value = []
        self.client.force_login(self.admin)
        response = self.client.get(reverse('sync_ghl_contacts'))
        self.assertEqual(response.status_code, 200)

    @patch('accounts.services.provisioning_sync.fetch_ghl_contacts')
    def test_manager_can_access_ghl_sync(self, mock_fetch):
        mock_fetch.return_value = []
        self.client.force_login(self.manager)
        response = self.client.get(reverse('sync_ghl_contacts'))
        self.assertEqual(response.status_code, 200)

    def test_member_cannot_access_ghl_sync(self):
        self.client.force_login(self.member)
        response = self.client.get(reverse('sync_ghl_contacts'))
        self.assertEqual(response.status_code, 302)
        response = self.client.get(reverse('sync_ghl_contacts'), follow=True)
        messages = [str(m) for m in response.context['messages']]
        self.assertTrue(any('permission' in m.lower() for m in messages))

    def test_technician_does_not_gain_provisioning_authority_from_this_change(self):
        """A pre-existing, unrelated role must not newly gain this privilege."""
        self.client.force_login(self.technician)
        response = self.client.get(reverse('sync_ghl_contacts'))
        self.assertEqual(response.status_code, 302)
        response = self.client.get(reverse('sync_ghl_contacts'), follow=True)
        messages = [str(m) for m in response.context['messages']]
        self.assertTrue(any('permission' in m.lower() for m in messages))


# ============================================================================
# MANAGER PROVISIONING WORKFLOW (items 3, 4, 28)
# ============================================================================

class ManagerProvisioningWorkflowTest(TestCase):
    """Manager can perform the create-user step of the provisioning workflow;
    Administrator retains full existing capability (regression, item 28)."""

    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_user(username='admin_wf', password='x', role='administrator')
        self.manager = User.objects.create_user(username='manager_wf', password='x', role='manager')

    def test_manager_can_create_member_user_via_manage_users(self):
        self.client.force_login(self.manager)
        response = self.client.post(reverse('manage_users'), {
            'username': 'new_member_by_manager',
            'email': 'new_member_by_manager@example.com',
            'first_name': 'New',
            'last_name': 'Member',
            'password': 'Password123!',
            'role': 'member',
            'workshop_code': 'ABC',
        }, follow=True)
        self.assertTrue(User.objects.filter(username='new_member_by_manager').exists())
        messages = [str(m) for m in response.context['messages']]
        self.assertTrue(any('created successfully' in m for m in messages))

    def test_manager_cannot_create_non_member_role(self):
        """Provisioning authority is scoped to Member -- not broadened to
        Administrator's full create scope."""
        self.assertFalse(can_create_user(self.manager, 'technician'))
        self.assertFalse(can_create_user(self.manager, 'administrator'))
        self.assertFalse(can_create_user(self.manager, 'manager'))
        self.assertTrue(can_create_user(self.manager, 'member'))

    def test_administrator_can_still_create_any_role(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse('manage_users'), {
            'username': 'new_tech_by_admin',
            'email': 'new_tech_by_admin@example.com',
            'first_name': 'New',
            'last_name': 'Tech',
            'password': 'Password123!',
            'role': 'technician',
            'user_level': 'level_1',
        }, follow=True)
        self.assertTrue(User.objects.filter(username='new_tech_by_admin', role='technician').exists())
        messages = [str(m) for m in response.context['messages']]
        self.assertTrue(any('created successfully' in m for m in messages))


class ManagerLinkAndManualSyncTest(TestCase):
    """Manager can perform the link-GHL-contact and manual "Run Now" actions (item 4)."""

    def setUp(self):
        self.client = Client()
        self.manager = User.objects.create_user(username='manager_actions', password='x', role='manager')

    @patch('accounts.services.provisioning_sync.fetch_ghl_contacts')
    def test_manager_can_trigger_run_provisioning_alerts_now(self, mock_fetch):
        mock_fetch.return_value = []
        self.client.force_login(self.manager)
        response = self.client.post(reverse('run_provisioning_alerts_now'), follow=True)
        messages = [str(m) for m in response.context['messages']]
        self.assertFalse(any('do not have permission' in m.lower() for m in messages))

    def test_manager_can_link_ghl_contact(self):
        target = User.objects.create_user(
            username='needs_link', password='x', role='member',
            email='needs_link@example.com',
        )
        self.client.force_login(self.manager)
        response = self.client.post(
            reverse('link_ghl_contact', args=[target.id]),
            {'contact_id': 'ManagerLinkedContact123'},
            follow=True,
        )
        target.refresh_from_db()
        self.assertEqual(target.contact_id, 'ManagerLinkedContact123')
        messages = [str(m) for m in response.context['messages']]
        self.assertFalse(any('do not have permission' in m.lower() for m in messages))


# ============================================================================
# NAME NORMALIZATION (items 7, 8, 9)
# ============================================================================

class SmartCaseNormalizationTest(TestCase):

    def test_all_lowercase_name_is_title_cased(self):
        self.assertEqual(smart_case('john'), 'John')
        self.assertEqual(smart_case('smith'), 'Smith')

    def test_mixed_case_name_is_preserved(self):
        self.assertEqual(smart_case('McGregor'), 'McGregor')
        self.assertEqual(smart_case('DeLuca'), 'DeLuca')

    def test_blank_name_is_returned_unchanged(self):
        self.assertEqual(smart_case(''), '')
        self.assertEqual(smart_case(None), None)

    def test_ghl_client_normalize_contact_applies_smart_case(self):
        raw = {'id': 'c1', 'email': 'a@b.com', 'firstName': 'dale', 'lastName': 'mcgregor', 'tags': []}
        result = normalize_contact(raw)
        self.assertEqual(result['first_name'], 'Dale')
        # 'mcgregor' is all-lowercase input -- smart_case title-cases it the
        # same as any other all-lowercase name (it has no way to know the
        # legitimate 'McGregor' capitalization from lowercase input alone).
        self.assertEqual(result['last_name'], 'Mcgregor')

    def test_ghl_client_normalize_contact_preserves_existing_mixed_case(self):
        raw = {'id': 'c2', 'email': 'a@b.com', 'firstName': 'Dale', 'lastName': 'McGregor', 'tags': []}
        result = normalize_contact(raw)
        self.assertEqual(result['first_name'], 'Dale')
        self.assertEqual(result['last_name'], 'McGregor')

    def test_sso_and_ghl_client_paths_use_identical_smart_case_behavior(self):
        """Both GHL-adjacent paths (SSO login-time, direct GHL API) must
        normalize the same raw lowercase name identically -- proves they
        share one implementation rather than two divergent copies."""
        sso_result = _extract_user_data({
            'contact_id': 'c3', 'email': 'a@b.com', 'first_name': 'dale', 'last_name': 'mcgregor',
            'username': 'dale', 'member_code': 'ABC', 'wpf_tags': [],
        })
        ghl_result = normalize_contact({
            'id': 'c3', 'email': 'a@b.com', 'firstName': 'dale', 'lastName': 'mcgregor', 'tags': [],
        })
        self.assertEqual(sso_result['first_name'], ghl_result['first_name'])
        self.assertEqual(sso_result['last_name'], ghl_result['last_name'])


# ============================================================================
# EXISTING-USER SYNC + PORTAL OWNERSHIP PROTECTION + IDENTITY SAFETY
# (items 10-25)
# ============================================================================

class SyncExistingUserGhlFieldsTest(TestCase):

    @patch('accounts.services.provisioning_sync.fetch_ghl_contacts')
    def test_updates_first_last_name_and_workshop_code_when_matched_by_contact_id(self, mock_fetch):
        user = User.objects.create_user(
            username='refresh_target', password='x', role='member',
            contact_id='CID-1', first_name='oldfirst', last_name='oldlast',
            email='refresh_target@example.com', workshop_code='OLD',
        )
        mock_fetch.return_value = [ghl_contact(
            contact_id='CID-1', email='refresh_target@example.com',
            first_name='Newfirst', last_name='Newlast', workshop_code='NEW',
        )]

        result = sync_existing_user_ghl_fields()

        user.refresh_from_db()
        self.assertEqual(user.first_name, 'Newfirst')
        self.assertEqual(user.last_name, 'Newlast')
        self.assertEqual(user.workshop_code, 'NEW')
        self.assertEqual(len(result['updated']), 1)
        self.assertEqual(result['updated'][0]['user_id'], user.id)

    @patch('accounts.services.provisioning_sync.fetch_ghl_contacts')
    def test_updates_email_when_safe(self, mock_fetch):
        user = User.objects.create_user(
            username='email_refresh', password='x', role='member',
            contact_id='CID-2', email='old@example.com',
        )
        mock_fetch.return_value = [ghl_contact(contact_id='CID-2', email='new@example.com')]

        sync_existing_user_ghl_fields()

        user.refresh_from_db()
        self.assertEqual(user.email, 'new@example.com')

    @patch('accounts.services.provisioning_sync.fetch_ghl_contacts')
    def test_missing_empty_incoming_values_do_not_erase_existing_values(self, mock_fetch):
        user = User.objects.create_user(
            username='no_erase', password='x', role='member',
            contact_id='CID-3', first_name='Keep', last_name='Me',
            email='no_erase@example.com', workshop_code='KEEP',
        )
        # GHL contact has a blank workshop_code -- must not blank out 'KEEP'.
        mock_fetch.return_value = [ghl_contact(
            contact_id='CID-3', email='no_erase@example.com',
            first_name='Keep', last_name='Me', workshop_code='',
        )]

        sync_existing_user_ghl_fields()

        user.refresh_from_db()
        self.assertEqual(user.workshop_code, 'KEEP')

    @patch('accounts.services.provisioning_sync.fetch_ghl_contacts')
    def test_unchanged_fields_are_not_rewritten(self, mock_fetch):
        user = User.objects.create_user(
            username='already_current', password='x', role='member',
            contact_id='CID-4', first_name='Already', last_name='Current',
            email='already_current@example.com', workshop_code='CUR',
        )
        mock_fetch.return_value = [ghl_contact(
            contact_id='CID-4', email='already_current@example.com',
            first_name='Already', last_name='Current', workshop_code='CUR',
        )]

        result = sync_existing_user_ghl_fields()

        self.assertEqual(result['updated'], [])
        self.assertEqual(result['unchanged_count'], 1)

    @patch('accounts.services.provisioning_sync.fetch_ghl_contacts')
    def test_role_is_never_changed(self, mock_fetch):
        user = User.objects.create_user(
            username='role_protect', password='x', role='member',
            contact_id='CID-5', email='role_protect@example.com',
        )
        # Tags imply 'member' already, but this proves role is never WRITTEN
        # by this function regardless of what the tags say.
        mock_fetch.return_value = [ghl_contact(
            contact_id='CID-5', email='role_protect@example.com', first_name='Changed',
        )]

        sync_existing_user_ghl_fields()

        user.refresh_from_db()
        self.assertEqual(user.role, 'member')

    @patch('accounts.services.provisioning_sync.fetch_ghl_contacts')
    def test_staff_roles_remain_untouched(self, mock_fetch):
        """Administrator/Manager/Technician roles are never changed by this
        refresh path, even if the user happens to have a linked GHL contact."""
        for role in ('administrator', 'manager', 'technician'):
            user = User.objects.create_user(
                username=f'staff_{role}', password='x', role=role,
                contact_id=f'CID-STAFF-{role}', first_name='old', email=f'staff_{role}@example.com',
            )
            mock_fetch.return_value = [ghl_contact(
                contact_id=f'CID-STAFF-{role}', email=f'staff_{role}@example.com', first_name='New',
            )]

            sync_existing_user_ghl_fields()

            user.refresh_from_db()
            self.assertEqual(user.role, role)
            self.assertEqual(user.first_name, 'New')  # name still refreshed

    @patch('accounts.services.provisioning_sync.fetch_ghl_contacts')
    def test_permissions_remain_untouched(self, mock_fetch):
        user = User.objects.create_user(
            username='perm_protect', password='x', role='technician',
            contact_id='CID-6', email='perm_protect@example.com',
            can_manage_delegates=True, can_manage_review_settings=True,
        )
        mock_fetch.return_value = [ghl_contact(
            contact_id='CID-6', email='perm_protect@example.com', first_name='New',
        )]

        sync_existing_user_ghl_fields()

        user.refresh_from_db()
        self.assertTrue(user.can_manage_delegates)
        self.assertTrue(user.can_manage_review_settings)

    @patch('accounts.services.provisioning_sync.fetch_ghl_contacts')
    def test_member_delegate_relationships_remain_untouched(self, mock_fetch):
        member = User.objects.create_user(
            username='md_member', password='x', role='member',
            contact_id='CID-7', email='md_member@example.com',
        )
        delegate = User.objects.create_user(username='md_delegate', password='x', role='member')
        assigned_by = User.objects.create_user(username='md_tech', password='x', role='technician')
        assignment = MemberDelegate.objects.create(member=member, delegate=delegate, assigned_by=assigned_by)

        mock_fetch.return_value = [ghl_contact(
            contact_id='CID-7', email='md_member@example.com', first_name='New',
        )]

        sync_existing_user_ghl_fields()

        self.assertTrue(MemberDelegate.objects.filter(pk=assignment.pk).exists())
        refreshed = MemberDelegate.objects.get(pk=assignment.pk)
        self.assertEqual(refreshed.member_id, member.id)
        self.assertEqual(refreshed.delegate_id, delegate.id)

    @patch('accounts.services.provisioning_sync.fetch_ghl_contacts')
    def test_is_pure_delegate_remains_untouched(self, mock_fetch):
        user = User.objects.create_user(
            username='pure_delegate_protect', password='x', role='member',
            contact_id='CID-8', email='pure_delegate_protect@example.com',
            is_pure_delegate=True,
        )
        mock_fetch.return_value = [ghl_contact(
            contact_id='CID-8', email='pure_delegate_protect@example.com',
            first_name='New', tags=['Portal access: Member'],  # implies non-delegate in GHL now
        )]

        sync_existing_user_ghl_fields()

        user.refresh_from_db()
        self.assertTrue(user.is_pure_delegate)

    @patch('accounts.services.provisioning_sync.fetch_ghl_contacts')
    def test_never_creates_a_new_user(self, mock_fetch):
        mock_fetch.return_value = [ghl_contact(
            contact_id='CID-NOBODY', email='nobody@example.com', first_name='Nobody',
        )]
        before_count = User.objects.count()

        result = sync_existing_user_ghl_fields()

        self.assertEqual(User.objects.count(), before_count)
        self.assertEqual(result['updated'], [])

    @patch('accounts.services.provisioning_sync.fetch_ghl_contacts')
    def test_unmatched_contact_remains_subject_to_normal_provisioning_discovery(self, mock_fetch):
        contacts = [ghl_contact(contact_id='CID-NOBODY2', email='nobody2@example.com', first_name='Nobody')]
        mock_fetch.return_value = contacts

        sync_existing_user_ghl_fields(contacts=contacts)
        new_contacts = compute_new_ghl_contacts(contacts=contacts)

        self.assertEqual(len(new_contacts), 1)
        self.assertEqual(new_contacts[0]['contact_id'], 'CID-NOBODY2')

    @patch('accounts.services.provisioning_sync.fetch_ghl_contacts')
    def test_contact_id_match_takes_precedence_even_with_ambiguous_email_elsewhere(self, mock_fetch):
        user = User.objects.create_user(
            username='precedence_user', password='x', role='member',
            contact_id='CID-9', email='precedence@example.com', first_name='old',
        )
        # Two OTHER relevant contacts share one email -- would be ambiguous for
        # an email-only match, but must not interfere with the contact_id match above.
        mock_fetch.return_value = [
            ghl_contact(contact_id='CID-9', email='precedence@example.com', first_name='Updated'),
            ghl_contact(contact_id='CID-OTHER-A', email='shared@example.com', first_name='A'),
            ghl_contact(contact_id='CID-OTHER-B', email='shared@example.com', first_name='B'),
        ]

        sync_existing_user_ghl_fields()

        user.refresh_from_db()
        self.assertEqual(user.first_name, 'Updated')

    @patch('accounts.services.provisioning_sync.fetch_ghl_contacts')
    def test_ambiguous_email_only_match_is_skipped(self, mock_fetch):
        user = User.objects.create_user(
            username='ambiguous_user', password='x', role='member',
            email='shared@example.com', first_name='Original',  # no contact_id on file
        )
        mock_fetch.return_value = [
            ghl_contact(contact_id='CID-AMBIG-A', email='shared@example.com', first_name='A'),
            ghl_contact(contact_id='CID-AMBIG-B', email='shared@example.com', first_name='B'),
        ]

        result = sync_existing_user_ghl_fields()

        user.refresh_from_db()
        self.assertEqual(user.first_name, 'Original')
        self.assertTrue(any(s['user_id'] == user.id for s in result['skipped']))

    @patch('accounts.services.provisioning_sync.fetch_ghl_contacts')
    def test_unambiguous_email_fallback_updates_existing_user(self, mock_fetch):
        """Complements test_ambiguous_email_only_match_is_skipped: when exactly
        one relevant GHL contact shares the user's email (no contact_id on
        file for either side), the email fallback match IS trusted and the
        GHL-owned fields ARE refreshed."""
        user = User.objects.create_user(
            username='unambiguous_email_user', password='x', role='member',
            email='only_one_match@example.com', first_name='Original',
            last_name='Name', workshop_code='OLD',
        )
        before_count = User.objects.count()
        mock_fetch.return_value = [ghl_contact(
            contact_id='CID-UNAMBIG-1', email='only_one_match@example.com',
            first_name='Updated', last_name='Surname', workshop_code='NEW',
        )]

        result = sync_existing_user_ghl_fields()

        user.refresh_from_db()
        self.assertEqual(user.first_name, 'Updated')
        self.assertEqual(user.last_name, 'Surname')
        self.assertEqual(user.workshop_code, 'NEW')
        self.assertEqual(len(result['updated']), 1)
        self.assertEqual(result['updated'][0]['user_id'], user.id)

        # No new User was created by this refresh path.
        self.assertEqual(User.objects.count(), before_count)

        # Portal-owned fields are untouched.
        self.assertEqual(user.role, 'member')
        self.assertFalse(user.can_manage_delegates)
        self.assertFalse(user.can_manage_review_settings)
        self.assertFalse(user.is_pure_delegate)

        # contact_id is not written by this function -- that is existing,
        # established behavior (only link_ghl_contact()/SSO provisioning set
        # it), confirmed by 'contact_id' never appearing in update_fields.
        self.assertIsNone(user.contact_id)
        self.assertNotIn('contact_id', result['updated'][0]['changes'])

    @patch('accounts.services.provisioning_sync.fetch_ghl_contacts')
    def test_email_collision_with_another_user_skips_email_field_only(self, mock_fetch):
        other_user = User.objects.create_user(
            username='collision_other', password='x', role='member',
            email='taken@example.com',
        )
        user = User.objects.create_user(
            username='collision_subject', password='x', role='member',
            contact_id='CID-10', email='original@example.com', first_name='old',
        )
        mock_fetch.return_value = [ghl_contact(
            contact_id='CID-10', email='taken@example.com', first_name='Updated',
        )]

        result = sync_existing_user_ghl_fields()

        user.refresh_from_db()
        other_user.refresh_from_db()
        # Email collision -> email field skipped, but other fields still refresh.
        self.assertEqual(user.email, 'original@example.com')
        self.assertEqual(user.first_name, 'Updated')
        # The other (colliding) user is completely untouched.
        self.assertEqual(other_user.email, 'taken@example.com')
        self.assertTrue(any(s.get('reason') == 'email_already_belongs_to_another_portal_user' for s in result['skipped']))


# ============================================================================
# REGRESSION (items 26, 27)
# ============================================================================

class ProvisioningAlertRegressionTest(TestCase):
    """Pre-existing alert-detection behavior must still work after adding
    the existing-user-sync category alongside it."""

    @patch('accounts.services.provisioning_sync.fetch_ghl_contacts')
    def test_new_contact_provisioning_alert_behavior_still_works(self, mock_fetch):
        mock_fetch.return_value = [ghl_contact(contact_id='CID-REG-1', email='reg1@example.com', first_name='Reg')]

        new_contacts = compute_new_ghl_contacts()

        self.assertEqual(len(new_contacts), 1)
        self.assertEqual(new_contacts[0]['contact_id'], 'CID-REG-1')

    @patch('accounts.services.provisioning_sync.fetch_ghl_contacts')
    def test_missing_tag_alert_behavior_still_works(self, mock_fetch):
        member = User.objects.create_user(
            username='reg_missing_tag', password='x', role='member',
            contact_id='CID-REG-2', email='reg2@example.com', is_active=True,
        )
        # Contact exists but no longer carries a portal-access tag.
        mock_fetch.return_value = [ghl_contact(contact_id='CID-REG-2', email='reg2@example.com', tags=[])]

        missing = compute_missing_tag_users()

        self.assertTrue(any(m['user_id'] == member.id for m in missing))
