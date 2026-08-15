"""
Tests for SSO tag parsing, role mapping, delegate model, and dashboard toggle logic.
Run with: python manage.py test accounts
"""
from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from accounts.sso import (
    _normalize_tags,
    determine_role_from_tags,
    _extract_user_data,
    TAG_ROLE_MAP,
    DELEGATE_TAGS,
    MEMBER_TAGS,
    generate_state_token,
)
from accounts.models import MemberDelegate

User = get_user_model()


# ============================================================================
# TAG NORMALIZATION
# ============================================================================

class NormalizeTagsTest(TestCase):
    """Test _normalize_tags handles all input formats."""

    def test_list_of_strings(self):
        result = _normalize_tags(['Portal access: Member', 'Portal access: Delegate'])
        self.assertEqual(result, ['Portal access: Member', 'Portal access: Delegate'])

    def test_single_string(self):
        result = _normalize_tags('Portal access: Member')
        self.assertEqual(result, ['Portal access: Member'])

    def test_comma_separated_string(self):
        result = _normalize_tags('Portal access: Member, Portal access: Delegate')
        self.assertEqual(result, ['Portal access: Member', 'Portal access: Delegate'])

    def test_list_of_dicts(self):
        result = _normalize_tags([
            {'name': 'Portal access: Member'},
            {'name': 'Portal access: Delegate'},
        ])
        self.assertEqual(result, ['Portal access: Member', 'Portal access: Delegate'])

    def test_empty_list(self):
        self.assertEqual(_normalize_tags([]), [])

    def test_none(self):
        self.assertEqual(_normalize_tags(None), [])

    def test_empty_string(self):
        self.assertEqual(_normalize_tags(''), [])

    def test_strips_whitespace(self):
        result = _normalize_tags('  Portal access: Member  ,  Portal access: Delegate  ')
        self.assertEqual(result, ['Portal access: Member', 'Portal access: Delegate'])

    def test_mixed_dict_formats(self):
        """Dicts with 'tag_name' or 'label' key instead of 'name'."""
        result = _normalize_tags([
            {'tag_name': 'Portal access: Member'},
            {'label': 'Portal access: Delegate'},
        ])
        # Should extract from whichever key is present
        self.assertIn('Portal access: Member', result)


# ============================================================================
# ROLE DETERMINATION
# ============================================================================

class DetermineRoleTest(TestCase):
    """Test determine_role_from_tags maps correctly."""

    def test_member_tag(self):
        role, is_pure_delegate, has_access = determine_role_from_tags(['Portal access: Member'])
        self.assertEqual(role, 'member')
        self.assertFalse(is_pure_delegate)
        self.assertTrue(has_access)

    def test_delegate_tag(self):
        role, is_pure_delegate, has_access = determine_role_from_tags(['Portal access: Delegate'])
        self.assertEqual(role, 'member')  # delegates get member role
        self.assertTrue(is_pure_delegate)
        self.assertTrue(has_access)

    def test_both_tags(self):
        role, is_pure_delegate, has_access = determine_role_from_tags(['Portal access: Member', 'Portal access: Delegate'])
        self.assertEqual(role, 'member')
        self.assertFalse(is_pure_delegate)  # Member tag takes priority
        self.assertTrue(has_access)

    def test_no_portal_tags(self):
        """No portal tags should deny access."""
        role, is_pure_delegate, has_access = determine_role_from_tags(['Some Other Tag'])
        self.assertIsNone(role)
        self.assertFalse(has_access)

    def test_empty_tags(self):
        role, is_pure_delegate, has_access = determine_role_from_tags([])
        self.assertIsNone(role)
        self.assertFalse(has_access)

    def test_extra_tags_ignored(self):
        """Non-portal tags mixed in should be harmless."""
        role, is_pure_delegate, has_access = determine_role_from_tags([
            'Portal access: Member',
            'Active Subscriber',
            'VIP Client',
        ])
        self.assertEqual(role, 'member')
        self.assertTrue(has_access)


# ============================================================================
# EXTRACT USER DATA
# ============================================================================

class ExtractUserDataTest(TestCase):
    """Test _extract_user_data extracts and normalizes fields."""

    def test_standard_payload(self):
        """Test with real WP resource endpoint format."""
        data = _extract_user_data({
            'id': 1424,
            'ID': 1424,
            'sub': 1424,
            'email': 'John.Doe@example.com',
            'first_name': 'John',
            'last_name': 'Doe',
            'username': 'johndoe',
            'member_code': 'ws101',
            'contact_id': 'Kzqrc450LtP3s461wVAz',
            'wpf_tags': ['portal access: member'],
        })
        self.assertEqual(data['contact_id'], 'Kzqrc450LtP3s461wVAz')
        self.assertEqual(data['email'], 'john.doe@example.com')
        self.assertEqual(data['first_name'], 'John')
        self.assertEqual(data['last_name'], 'Doe')
        self.assertEqual(data['username'], 'johndoe')
        self.assertEqual(data['workshop_code'], 'WS101')
        self.assertEqual(data['tags'], ['portal access: member'])

    def test_real_wp_response(self):
        """Test with actual sample from WP developer."""
        data = _extract_user_data({
            'id': 1424,
            'ID': 1424,
            'sub': 1424,
            'email': 'kennedy+testwpcreateuser128@profeds.com',
            'username': 'MikeTestWPCreateUser128',
            'first_name': 'Mike',
            'last_name': 'TestWPCreateUser128',
            'nickname': 'MikeTestWPCreateUser128',
            'display_name': 'Mike TestWPCreateUser128',
            'member_code': 'ABC',
            'secondary_contact_type': '',
            'contact_id': 'Kzqrc450LtP3s461wVAz',
            'wpf_tags': [
                'dup check: [02. history] 01. dup check complete',
                'portal access: delegate',
                'portal access: member',
            ],
        })
        self.assertEqual(data['contact_id'], 'Kzqrc450LtP3s461wVAz')
        self.assertEqual(data['email'], 'kennedy+testwpcreateuser128@profeds.com')
        self.assertEqual(data['username'], 'miketestwpcreateuser128')
        self.assertEqual(data['workshop_code'], 'ABC')
        self.assertIn('portal access: delegate', data['tags'])
        self.assertIn('portal access: member', data['tags'])

    def test_missing_fields_return_defaults(self):
        data = _extract_user_data({})
        self.assertEqual(data['contact_id'], '')
        self.assertEqual(data['email'], '')
        self.assertEqual(data['first_name'], '')
        self.assertEqual(data['tags'], [])


# ============================================================================
# STATE TOKEN
# ============================================================================

class StateTokenTest(TestCase):
    def test_token_is_string(self):
        token = generate_state_token()
        self.assertIsInstance(token, str)

    def test_tokens_are_unique(self):
        t1 = generate_state_token()
        t2 = generate_state_token()
        self.assertNotEqual(t1, t2)


# ============================================================================
# MEMBER DELEGATE MODEL
# ============================================================================

class AdminRoleFlagsTest(TestCase):
    """Administrator accounts must retain Django staff/superuser flags."""

    def test_admin_role_sets_staff_and_superuser_flags(self):
        admin = User.objects.create_user(
            username='admin_role_flag_test',
            email='admin-role-flag@test.com',
            password='testpass',
            role='administrator',
            first_name='Admin',
            last_name='User',
        )

        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)

    def test_non_admin_role_clears_staff_and_superuser_flags(self):
        tech = User.objects.create_user(
            username='tech_role_flag_test',
            email='tech-role-flag@test.com',
            password='testpass',
            role='technician',
            first_name='Tech',
            last_name='User',
            is_staff=True,
            is_superuser=True,
        )

        self.assertFalse(tech.is_staff)
        self.assertFalse(tech.is_superuser)


class MemberDelegateModelTest(TestCase):
    """Test the MemberDelegate model constraints and behavior."""

    def setUp(self):
        self.member = User.objects.create_user(
            username='advisor1',
            email='advisor1@test.com',
            password='testpass',
            role='member',
            first_name='Jane',
            last_name='Advisor',
            workshop_code='WS100',
        )
        self.delegate = User.objects.create_user(
            username='delegate1',
            email='delegate1@test.com',
            password='testpass',
            role='member',
            first_name='Sam',
            last_name='Helper',
        )
        self.technician = User.objects.create_user(
            username='tech1',
            email='tech1@test.com',
            password='testpass',
            role='technician',
            first_name='Bob',
            last_name='Tech',
        )

    def test_create_assignment(self):
        md = MemberDelegate.objects.create(
            member=self.member,
            delegate=self.delegate,
            assigned_by=self.technician,
        )
        self.assertEqual(md.member, self.member)
        self.assertEqual(md.delegate, self.delegate)
        self.assertEqual(md.assigned_by, self.technician)

    def test_unique_constraint(self):
        """Cannot assign the same delegate to the same member twice."""
        MemberDelegate.objects.create(
            member=self.member,
            delegate=self.delegate,
            assigned_by=self.technician,
        )
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            MemberDelegate.objects.create(
                member=self.member,
                delegate=self.delegate,
                assigned_by=self.technician,
            )

    def test_delegate_for_multiple_members(self):
        """One delegate can be assigned to multiple members."""
        member2 = User.objects.create_user(
            username='advisor2', email='advisor2@test.com',
            password='testpass', role='member',
        )
        MemberDelegate.objects.create(
            member=self.member, delegate=self.delegate, assigned_by=self.technician,
        )
        MemberDelegate.objects.create(
            member=member2, delegate=self.delegate, assigned_by=self.technician,
        )
        self.assertEqual(
            MemberDelegate.objects.filter(delegate=self.delegate).count(), 2
        )

    def test_delete_assignment(self):
        md = MemberDelegate.objects.create(
            member=self.member, delegate=self.delegate, assigned_by=self.technician,
        )
        md.delete()
        self.assertEqual(MemberDelegate.objects.count(), 0)


# ============================================================================
# DASHBOARD TOGGLE LOGIC
# ============================================================================

class DashboardToggleTest(TestCase):
    """Test the is_delegate / is_pure_delegate detection logic used by member_dashboard."""

    def setUp(self):
        self.member = User.objects.create_user(
            username='member_toggle', email='mt@test.com',
            password='testpass', role='member',
        )
        self.other_member = User.objects.create_user(
            username='other_member', email='om@test.com',
            password='testpass', role='member',
        )
        self.pure_delegate_user = User.objects.create_user(
            username='pure_del', email='pd@test.com',
            password='testpass', role='member',
        )
        self.tech = User.objects.create_user(
            username='tech_toggle', email='tt@test.com',
            password='testpass', role='technician',
        )

    def _is_delegate(self, user):
        """Mirror the logic in member_dashboard view."""
        return MemberDelegate.objects.filter(delegate=user).exists()

    def test_pure_member_no_toggle(self):
        """Member with no delegate assignments should not see toggle."""
        self.assertFalse(self._is_delegate(self.member))

    def test_member_who_is_delegate_sees_toggle(self):
        """Member assigned as delegate for another member should see toggle."""
        MemberDelegate.objects.create(
            member=self.other_member, delegate=self.member, assigned_by=self.tech,
        )
        self.assertTrue(self._is_delegate(self.member))

    def test_pure_delegate_is_detected(self):
        """User with only delegate assignments is detected."""
        MemberDelegate.objects.create(
            member=self.other_member, delegate=self.pure_delegate_user, assigned_by=self.tech,
        )
        self.assertTrue(self._is_delegate(self.pure_delegate_user))


# ============================================================================
# TAG CONSTANT VALIDATION
# ============================================================================

class TagConstantsTest(TestCase):
    """Verify consistency of tag constants."""

    def test_delegate_tags_subset_of_role_map(self):
        for tag in DELEGATE_TAGS:
            self.assertIn(tag, TAG_ROLE_MAP)

    def test_member_tags_subset_of_role_map(self):
        for tag in MEMBER_TAGS:
            self.assertIn(tag, TAG_ROLE_MAP)

    def test_exactly_two_tags(self):
        self.assertEqual(len(TAG_ROLE_MAP), 2)