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
    phone = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"
    
    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'


class AdvisorDelegate(models.Model):
    """
    Allow delegates (staff members) to submit and manage cases on behalf of advisors.
    This enables team members to help with case submissions.
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
    Grant delegate permissions for members to allow others to submit cases on their behalf.
    
    This model enables:
    - Delegating case submission authority to team members within same office
    - Granular permission control (submit, edit, view, approve)
    - Workshop code-based visibility (only see delegates in same workshop)
    - Audit trail of all delegate changes (who granted, when, by whom)
    
    NOTE: No expiration is currently set. Delegates remain active until manually revoked
    or the member's account is deactivated.
    
    WP FUSION INTEGRATION PLACEHOLDER:
    - Future: Could auto-revoke delegates when member's WP subscription expires
    - Future: Could validate delegate office/workshop against WP user meta
    - Currently: Benefits Tech manually manages delegates in member profile
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
