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
