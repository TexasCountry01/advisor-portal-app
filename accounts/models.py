from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    """Custom user model with role and member-specific information"""
    
    ROLE_CHOICES = [
        ('member', 'Member (Financial Advisor)'),
        ('technician', 'Benefits Technician'),
        ('administrator', 'Administrator'),
        ('manager', 'Manager (View-Only Admin)'),
    ]
    
    USER_LEVEL_CHOICES = [
        ('level_1', 'Level 1 - New Technician'),
        ('level_2', 'Level 2 - Technician'),
        ('level_3', 'Level 3 - Senior Technician'),
    ]
    
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='member')
    contact_id = models.CharField(
        max_length=100,
        unique=True,
        null=True,
        blank=True,
        help_text='GHL (GoHighLevel) contact ID — immutable SSO identifier for sync'
    )
    user_level = models.CharField(
        max_length=10, 
        choices=USER_LEVEL_CHOICES, 
        blank=True, 
        null=True,
        help_text='For technicians only: Experience level for quality review workflow'
    )
    workshop_code = models.CharField(
        max_length=50, 
        blank=True,
        help_text='For members: Pre-assigned workshop code'
    )
    font_size = models.CharField(
        max_length=10,
        default='100',
        choices=[
            ('75', '75% (Small)'),
            ('85', '85% (Smaller)'),
            ('100', '100% (Normal)'),
            ('115', '115% (Larger)'),
            ('130', '130% (Large)'),
            ('150', '150% (X-Large)'),
        ],
        help_text='Adjustable font size for accessibility'
    )
    phone = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=True)
    is_test_account = models.BooleanField(
        default=False,
        help_text='Flag for permanent test accounts (Devops*). Excluded from data cleanup scripts.'
    )
    notification_email = models.EmailField(
        blank=True,
        default='',
        help_text='Override email for portal notifications. If set, HOLD/CHAT/READY emails go here instead of the SSO email.'
    )
    is_pure_delegate = models.BooleanField(
        default=False,
        help_text='True if user has only the "Portal access: Delegate" tag (admin assistant, no own cases). '
                  'False if also a member/advisor. Set automatically by SSO on each login.'
    )
    # ------------------------------------------------------------------
    # Global notification toggles (member/delegate self-service).
    # These control whether the user receives ANY email or in-app alerts
    # for their own cases.  Delegates additionally have per-assignment
    # toggles on MemberDelegate (email_notifications, portal_notifications).
    # ------------------------------------------------------------------
    email_notifications_enabled = models.BooleanField(
        default=True,
        help_text='Member/delegate opt-in for email notifications on their own cases.'
    )
    portal_notifications_enabled = models.BooleanField(
        default=True,
        help_text='Member/delegate opt-in for in-app (portal) notifications on their own cases.'
    )
    # ------------------------------------------------------------------
    # Granular staff permissions (independently grantable by admin/manager)
    # ------------------------------------------------------------------
    can_manage_review_settings = models.BooleanField(
        default=False,
        help_text='Can toggle review-required settings for other technicians. Granted to L3 techs at admin discretion.'
    )
    can_manage_delegates = models.BooleanField(
        default=False,
        help_text='Can access the Delegate Management page. Granted to L3 techs at admin discretion.'
    )
    ref_saved_searches = models.JSONField(
        default=list,
        blank=True,
        help_text='User-specific reference library recent searches (last 10). Shared across all cases and devices.'
    )
    last_active = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Last time this user made an authenticated request. Updated by LastActiveMiddleware (throttled 60s).'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"

    def save(self, *args, **kwargs):
        """Keep Django auth flags in sync with the custom role field."""
        if self.role == 'administrator':
            self.is_staff = True
            self.is_superuser = True
        elif self.role in {'member', 'technician', 'manager'}:
            self.is_staff = False
            self.is_superuser = False

        super().save(*args, **kwargs)
    
    def get_font_size_percentage(self):
        """Return font size as a CSS percentage value"""
        return f"{self.font_size}%"
    
    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'


class AdvisorDelegate(models.Model):
    """
    DEPRECATED — replaced by MemberDelegate.
    Kept temporarily for migration compatibility.
    """
    
    delegate = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='delegate_for_advisors',
        help_text='Staff member who can submit cases'
    )
    advisor = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='advisor_delegates',
        help_text='Advisor whose cases this delegate can submit'
    )
    can_submit = models.BooleanField(default=True, help_text='Delegate can submit new cases')
    can_edit = models.BooleanField(default=True, help_text='Delegate can edit submitted cases')
    can_view = models.BooleanField(default=True, help_text='Delegate can view cases')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('delegate', 'advisor')
        verbose_name = 'Advisor Delegate'
        verbose_name_plural = 'Advisor Delegates'
    
    def __str__(self):
        return f"{self.delegate.get_full_name()} can submit for {self.advisor.get_full_name()}"


# ============================================================================
# MEMBER DELEGATE MODEL (consolidated replacement for AdvisorDelegate,
# DelegateAccess, and WorkshopDelegate)
# ============================================================================

class MemberDelegate(models.Model):
    """
    Assign a delegate to act on behalf of a specific member (advisor).
    
    This is the single source of truth for delegate assignments.
    
    Rules (decided March 1, 2026 meeting with Chris):
    - Benefits Technicians assign delegates (not members themselves)
    - Delegates get full access (submit, edit, view) — no permission levels
    - No active/inactive toggle — row exists = active, delete row = revoked
    - A member can also be a delegate for other members
    - Admin assistants (Portal: Delegate SSO tag) are pure delegates
    - No delegate-of-delegate chaining
    """
    
    member = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='delegates',
        help_text='The member (advisor) being represented'
    )
    delegate = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='delegated_members',
        help_text='The user who can act on behalf of this member'
    )
    assigned_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='delegate_assignments_made',
        help_text='Benefits Technician who created this assignment'
    )
    email_notifications = models.BooleanField(
        default=True,
        help_text='Whether this delegate receives email notifications for this member\'s cases'
    )
    portal_notifications = models.BooleanField(
        default=True,
        help_text='Whether this delegate sees in-app notification alerts for this member\'s cases'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('member', 'delegate')
        verbose_name = 'Member Delegate'
        verbose_name_plural = 'Member Delegates'
        ordering = ['member__last_name', 'member__first_name']
        indexes = [
            models.Index(fields=['member']),
            models.Index(fields=['delegate']),
        ]
    
    def __str__(self):
        return f"{self.delegate.get_full_name()} → {self.member.get_full_name()}"


class DelegateRequest(models.Model):
    """
    A member's request to add or remove a delegate.
    Staff (L3 Tech, Admin, Manager) must process this in GHL before
    granting/revoking portal access.
    """
    REQUEST_TYPE_CHOICES = [
        ('add', 'Add Delegate'),
        ('remove', 'Remove Delegate'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('denied', 'Denied'),
        ('dismissed', 'Dismissed'),
    ]

    requested_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='delegate_requests_made',
        help_text='The member who submitted the request'
    )
    request_type = models.CharField(max_length=10, choices=REQUEST_TYPE_CHOICES)
    delegate_name = models.CharField(
        max_length=200,
        help_text='Name of the person to add/remove as delegate'
    )
    delegate_email = models.EmailField(
        blank=True,
        help_text='Email of the person to add as delegate (for add requests)'
    )
    # If removing an existing delegate, link to the assignment
    existing_assignment = models.ForeignKey(
        'MemberDelegate',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='removal_requests',
        help_text='The delegate assignment to remove (for remove requests)'
    )
    notes = models.TextField(
        blank=True,
        help_text='Additional notes from the member'
    )
    still_with_firm = models.BooleanField(
        null=True,
        blank=True,
        help_text='For remove requests: True if delegate still works at the firm, False if they left'
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    processed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='delegate_requests_processed',
    )
    processed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Delegate Request'
        verbose_name_plural = 'Delegate Requests'

    def __str__(self):
        return f"{self.get_request_type_display()} - {self.delegate_name} (by {self.requested_by})"


class UserPreference(models.Model):
    """Store user dashboard preferences (column visibility, order, etc.)"""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='preferences')
    preference_key = models.CharField(max_length=100)  # e.g., 'dashboard_columns', 'column_order'
    preference_value = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('user', 'preference_key')
        verbose_name = 'User Preference'
        verbose_name_plural = 'User Preferences'
    
    def __str__(self):
        return f"{self.user.username} - {self.preference_key}"


# ============================================================================
# NOTIFICATION PREFERENCES (per-user, per-type granular control)
# ============================================================================

class NotificationPreference(models.Model):
    """
    Per-user, per-notification-type preference for email and in-app alerts.

    Members and delegates can toggle each notification type independently.
    Preferences are checked at send-time by email_service.py and
    CaseNotification/messaging creation code.

    If no row exists for a user+type combo, the default is ENABLED for both
    channels (opt-out model — users must explicitly disable).

    Notification types mirror the active member-facing events:
      - case_on_hold:   Case placed on hold by technician
      - case_resumed:    Case resumed from hold
      - case_chat:       New message/comment from technician on a case
      - case_completed:  Case finished and released (report ready)
      - messaging_reply: Staff reply in the general messaging/Q&A system
    """

    NOTIFICATION_TYPE_CHOICES = [
        ('case_on_hold', 'Case Placed on Hold'),
        ('case_resumed', 'Case Resumed from Hold'),
        ('case_chat', 'New Case Chat Message'),
        ('case_completed', 'Case Completed (Report Ready)'),
        ('messaging_reply', 'General Messaging Reply'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notification_preferences',
        help_text='The member or delegate who owns this preference'
    )
    notification_type = models.CharField(
        max_length=30,
        choices=NOTIFICATION_TYPE_CHOICES,
        help_text='Which notification event this preference controls'
    )
    email_enabled = models.BooleanField(
        default=True,
        help_text='Receive email notifications for this event type'
    )
    portal_enabled = models.BooleanField(
        default=True,
        help_text='Receive in-app (portal) notifications for this event type'
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'notification_type')
        verbose_name = 'Notification Preference'
        verbose_name_plural = 'Notification Preferences'
        indexes = [
            models.Index(fields=['user', 'notification_type']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.notification_type} (email={self.email_enabled}, portal={self.portal_enabled})"

    # ------------------------------------------------------------------
    # Helper: look up a single preference for a user+type, returning
    # defaults (both enabled) when no row exists yet.
    # ------------------------------------------------------------------
    @classmethod
    def get_pref(cls, user, notification_type):
        """
        Return (email_enabled, portal_enabled) for the given user+type.
        Returns (True, True) if no preference row exists (opt-out model).
        """
        try:
            pref = cls.objects.get(user=user, notification_type=notification_type)
            return pref.email_enabled, pref.portal_enabled
        except cls.DoesNotExist:
            return True, True

    @classmethod
    def is_email_enabled(cls, user, notification_type):
        """Quick check: should this user get EMAIL for this type?"""
        email_on, _ = cls.get_pref(user, notification_type)
        return email_on

    @classmethod
    def is_portal_enabled(cls, user, notification_type):
        """Quick check: should this user get IN-APP alert for this type?"""
        _, portal_on = cls.get_pref(user, notification_type)
        return portal_on


class AuditLog(models.Model):
    """Track all user actions for compliance and security"""
    
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=100)  # e.g., 'case_created', 'document_uploaded'
    resource_type = models.CharField(max_length=50)  # e.g., 'case', 'document', 'user'
    resource_id = models.IntegerField(null=True, blank=True)
    details = models.JSONField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Audit Log'
        verbose_name_plural = 'Audit Logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['resource_type', 'resource_id']),
            models.Index(fields=['-created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username if self.user else 'System'} - {self.action} at {self.created_at}"


# ============================================================================
# MEMBER PROFILE MANAGEMENT MODELS
# ============================================================================
# These models support the Member Profile Enhancement feature:
# - Allow editing of member (advisor) profiles post-creation
# - Manage quarterly credit allowances
# - Control delegate access with granular permissions
# - Integrate with AuditLog for full compliance tracking
#
# WP FUSION INTEGRATION NOTES:
# - WP Fusion will eventually control the 'is_active' flag on the User model
# - Currently, 'is_active' is managed manually via the profile edit form
# - Before production, WP Fusion can be integrated to:
#   a) Override is_active based on WP membership status
#   b) Auto-sync workshop_code from WP user meta
#   c) Trigger profile updates on WP subscription changes
# - See PLACEHOLDER comments below for integration points
# ============================================================================


class MemberCreditAllowance(models.Model):
    """
    Track quarterly credit allowances per member (advisor).
    
    Credits are quarterly allowances for how many cases a member can submit.
    This model enables:
    - Per-member credit tracking
    - Quarterly reset of credit counts
    - Historical tracking of credit changes
    - Admin configuration of member credit levels
    
    WP FUSION INTEGRATION PLACEHOLDER:
    - Future: Credits could be synced from WP product pricing/subscription level
    - Currently: Benefits Tech manually sets credit allowances in admin panel
    """
    
    # ForeignKey to member (User with role='member')
    member = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='credit_allowances',
        limit_choices_to={'role': 'member'},
        help_text='Member (advisor) this credit allowance applies to'
    )
    
    # Which fiscal year/quarter this allowance covers
    fiscal_year = models.IntegerField(
        help_text='Fiscal year for this quarter (e.g., 2026)'
    )
    quarter = models.IntegerField(
        choices=[(1, 'Q1'), (2, 'Q2'), (3, 'Q3'), (4, 'Q4')],
        help_text='Quarter number (1-4)'
    )
    
    # Credit amount allowed for this quarter
    allowed_credits = models.IntegerField(
        default=100,
        help_text='Number of cases/credits allowed this quarter'
    )
    
    # Tracking and metadata
    configured_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='credit_allowances_configured',
        help_text='Admin/Manager who set this allowance'
    )
    notes = models.TextField(
        blank=True,
        help_text='Admin notes about why this credit level was set'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('member', 'fiscal_year', 'quarter')
        verbose_name = 'Member Credit Allowance'
        verbose_name_plural = 'Member Credit Allowances'
        ordering = ['-fiscal_year', '-quarter']
        indexes = [
            models.Index(fields=['member', 'fiscal_year', 'quarter']),
        ]
    
    def __str__(self):
        return f"{self.member.get_full_name()} - FY{self.fiscal_year} Q{self.quarter}: {self.allowed_credits} credits"


class DelegateAccess(models.Model):
    """
    DEPRECATED — Replaced by MemberDelegate model.
    Kept for migration compatibility. URL routes disabled.
    Use delegate_management() view + MemberDelegate instead.
    
    Original purpose: Grant delegate permissions for members to allow
    others to submit cases on their behalf.
    """
    
    # The member (advisor) who is delegating authority
    member = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='granted_delegate_access',
        limit_choices_to={'role': 'member'},
        help_text='Member (advisor) who is delegating authority'
    )
    
    # The delegate (team member) receiving the permissions
    delegate = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='delegate_access_to_members',
        help_text='Team member receiving delegate permissions'
    )
    
    # Permission level controls what delegates can do
    PERMISSION_CHOICES = [
        ('view', 'View Only - Read member cases and documents'),
        ('submit', 'Submit Cases - Can submit new cases on behalf of member'),
        ('edit', 'Edit Cases - Can submit and edit cases'),
        ('approve', 'Approve Cases - Can submit, edit, and approve cases'),  # For future admin workflows
    ]
    
    permission_level = models.CharField(
        max_length=20,
        choices=PERMISSION_CHOICES,
        default='submit',
        help_text='What actions the delegate can perform'
    )
    
    # Tracking who granted this access and when
    granted_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='delegate_access_granted',
        help_text='Admin/Manager who granted this access (usually during member profile edit)'
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text='Whether this delegate access is currently active'
    )
    
    grant_reason = models.CharField(
        max_length=200,
        blank=True,
        help_text='Why this delegate was granted access (optional)'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('member', 'delegate')
        verbose_name = 'Delegate Access'
        verbose_name_plural = 'Delegate Access'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['member', 'is_active']),
            models.Index(fields=['delegate', 'is_active']),
        ]
    
    def __str__(self):
        status = "Active" if self.is_active else "Inactive"
        return f"{self.delegate.get_full_name()} ({self.permission_level}) for {self.member.get_full_name()} [{status}]"


class WorkshopDelegate(models.Model):
    """
    DEPRECATED — Replaced by MemberDelegate model.
    Kept for migration compatibility. URL routes disabled.
    Use delegate_management() view + MemberDelegate instead.
    
    Original purpose: Assign delegates to workshop codes for case
    submission authority (workshop-centric vs member-centric).
    """
    
    # The workshop code this delegate is assigned to
    workshop_code = models.CharField(
        max_length=50,
        db_index=True,
        help_text='Workshop code this delegate has access to'
    )
    
    # The delegate (staff member) receiving permissions
    delegate = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='workshop_delegates',
        help_text='Team member who can submit cases for this workshop'
    )
    
    # Permission level controls what delegates can do
    PERMISSION_CHOICES = [
        ('view', 'View Only - Read workshop cases and documents'),
        ('submit', 'Submit Cases - Can submit new cases for workshop members'),
        ('edit', 'Edit Cases - Can submit and edit cases'),
        ('approve', 'Approve Cases - Can submit, edit, and approve cases'),  # For future workflows
    ]
    
    permission_level = models.CharField(
        max_length=20,
        choices=PERMISSION_CHOICES,
        default='submit',
        help_text='What actions the delegate can perform for this workshop'
    )
    
    # Tracking who granted this access and when
    granted_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='workshop_delegates_granted',
        help_text='Tech/Admin who granted this access'
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text='Whether this delegate access is currently active'
    )
    
    grant_reason = models.CharField(
        max_length=200,
        blank=True,
        help_text='Why this delegate was assigned to this workshop (optional)'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('workshop_code', 'delegate')
        verbose_name = 'Workshop Delegate'
        verbose_name_plural = 'Workshop Delegates'
        ordering = ['workshop_code', '-created_at']
        indexes = [
            models.Index(fields=['workshop_code', 'is_active']),
            models.Index(fields=['delegate', 'is_active']),
        ]
    
    def __str__(self):
        status = "Active" if self.is_active else "Inactive"
        return f"{self.delegate.get_full_name()} ({self.permission_level}) for workshop {self.workshop_code} [{status}]"


# ============================================================================
# WP FUSION PLACEHOLDER NOTES:
# ============================================================================
# When integrating WP Fusion, consider these integration points:
#
# 1. User.is_active field:
#    - Will be synced from WP membership status
#    - Currently: Manual toggle in member profile edit
#    - Add WP Fusion subscriber check before allowing case submission
#
# 2. User.workshop_code field:
#    - Could be auto-populated from WP user meta field
#    - Currently: Set during member profile edit by Benefits Tech
#    - Add sync method triggered on WP subscription update
#
# 3. MemberCreditAllowance.allowed_credits:
#    - Could be derived from WP product/membership tier
#    - Currently: Set manually by Benefits Tech per quarter
#    - Add product-to-credits mapping in settings
#
# 4. DelegateAccess.is_active:
#    - Could auto-deactivate if delegate loses WP subscription
#    - Could auto-deactivate if member loses WP subscription
#    - Currently: Manual revocation only
#
# 5. AuditLog integration:
#    - Ensure all WP Fusion-driven changes are logged
#    - Track sync operations, not just UI changes
#    - Link back to WP user ID for debugging
# ============================================================================


# ============================================================================
# SSO EMAIL ALLOWLIST — restrict SSO access on non-production environments
# ============================================================================

class SSOAllowedEmail(models.Model):
    """
    Email allowlist for SSO access control.
    
    When this table has rows, ONLY listed emails can SSO into this portal instance.
    When empty, ALL tagged WP users can SSO in (production behavior).
    
    Use case: Restrict TEST server access while sharing the same WP OAuth.
    Managed via Django Admin (superuser only).
    """
    email = models.EmailField(
        unique=True,
        help_text='Email address allowed to SSO into this portal instance'
    )
    note = models.CharField(
        max_length=200,
        blank=True,
        help_text='Optional note (e.g. "Tester - Chris", "Dev account")'
    )
    added_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'SSO Allowed Email'
        verbose_name_plural = 'SSO Allowed Emails'
        ordering = ['email']
    
    def __str__(self):
        return f'{self.email} ({self.note})' if self.note else self.email
    
    def save(self, *args, **kwargs):
        self.email = self.email.strip().lower()
        super().save(*args, **kwargs)


# ============================================================================
# PROVISIONING SYNC ALERTS — persistent tracking of GHL/portal drift
# ============================================================================

class ProvisioningAlert(models.Model):
    """
    Tracks GHL <-> portal provisioning drift across daily sync runs.

    Two kinds of drift are tracked:
      - new_ghl_contact: a GHL contact has a portal-access tag but no
        matching portal User record yet (needs Provision).
      - missing_ghl_tag: an active, role='member' portal User no longer
        has a portal-access tag in GHL (needs Deactivate).

    first_detected_at/last_seen_at/resolved_at give the daily cron job
    (and the GHL Sync Review page) a stable "when did we first notice
    this" timestamp, so the same 8 unmatched contacts found today don't
    look brand-new again tomorrow -- only genuinely new drift is badged
    NEW. When drift is no longer detected on a run (provisioned, tag
    restored, or account deactivated), the alert is marked resolved
    automatically -- no manual cleanup needed.
    """
    ALERT_TYPES = [
        ('new_ghl_contact', 'New GHL Contact Not Provisioned'),
        ('missing_ghl_tag', 'Active Portal User Missing GHL Tag'),
    ]

    alert_type = models.CharField(max_length=30, choices=ALERT_TYPES)

    # For new_ghl_contact alerts: the GHL contact_id (immutable identifier).
    # For missing_ghl_tag alerts: the contact_id on file for the portal user
    # (may be blank if the user was never linked to a GHL contact at all).
    contact_id = models.CharField(max_length=100, blank=True, null=True)

    # For missing_ghl_tag alerts: the portal User in question.
    # Null for new_ghl_contact alerts (no portal user exists yet).
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='provisioning_alerts'
    )

    email = models.EmailField(blank=True, default='')

    # Snapshot of relevant details at detection time (name, workshop_code,
    # ghl_role, tags, etc.) -- kept even after resolution for audit history.
    details = models.JSONField(default=dict, blank=True)

    first_detected_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    last_notified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Provisioning Alert'
        verbose_name_plural = 'Provisioning Alerts'
        ordering = ['-first_detected_at']
        indexes = [
            models.Index(fields=['alert_type', 'resolved_at']),
        ]

    def __str__(self):
        status = 'resolved' if self.resolved_at else 'open'
        return f'{self.get_alert_type_display()} ({status}) - {self.email or self.contact_id}'

    @property
    def is_open(self):
        return self.resolved_at is None
