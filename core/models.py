from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone


class AuditLog(models.Model):
    """
    Complete audit trail of all user actions in the system.
    Tracks all activities with timestamp, user, action type, and details.
    """
    
    # Action type choices
    ACTION_CHOICES = [
        ('login', 'User Login'),
        ('logout', 'User Logout'),
        ('case_created', 'Case Created'),
        ('case_updated', 'Case Updated'),
        ('case_submitted', 'Case Submitted'),
        ('case_assigned', 'Case Assigned'),
        ('case_reassigned', 'Case Reassigned'),
        ('case_status_changed', 'Status Changed'),
        ('document_uploaded', 'Document Uploaded'),
        ('document_viewed', 'Document Viewed'),
        ('document_downloaded', 'Document Downloaded'),
        ('document_deleted', 'Document Deleted'),
        ('note_added', 'Note Added'),
        ('note_deleted', 'Note Deleted'),
        ('review_submitted', 'Quality Review Submitted'),
        ('review_updated', 'Quality Review Updated'),
        ('user_created', 'User Created'),
        ('user_updated', 'User Updated'),
        ('user_deleted', 'User Deleted'),
        ('settings_updated', 'Settings Updated'),
        ('export_generated', 'Export Generated'),
        ('other', 'Other Activity'),
    ]
    
    # User who performed the action
    user = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
        help_text='User who performed the action'
    )
    
    # Action type
    action_type = models.CharField(
        max_length=50,
        choices=ACTION_CHOICES,
        help_text='Type of action performed'
    )
    
    # Timestamp of action (auto-set to current time)
    timestamp = models.DateTimeField(
        default=timezone.now,
        db_index=True,
        help_text='When the action occurred'
    )
    
    # Description of what happened
    description = models.TextField(
        help_text='Human-readable description of the action'
    )
    
    # Related case (if applicable)
    case = models.ForeignKey(
        'cases.Case',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
        help_text='Related case (if applicable)'
    )
    
    # Related document (if applicable)
    document = models.ForeignKey(
        'cases.CaseDocument',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
        help_text='Related document (if applicable)'
    )
    
    # Related user (if action is about another user)
    related_user = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs_about',
        help_text='Related user (if action is about another user)'
    )
    
    # Detailed change data (JSON for flexibility)
    changes = models.JSONField(
        default=dict,
        blank=True,
        help_text='Dictionary of field changes (before/after for updates)'
    )
    
    # IP address (if available)
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text='IP address from which action was performed'
    )
    
    # Additional metadata
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text='Additional metadata about the action'
    )
    
    class Meta:
        verbose_name = 'Audit Log'
        verbose_name_plural = 'Audit Logs'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['action_type', '-timestamp']),
            models.Index(fields=['case', '-timestamp']),
            models.Index(fields=['-timestamp']),
        ]
    
    def __str__(self):
        return f"{self.get_action_type_display()} by {self.user} at {self.timestamp}"
    
    @classmethod
    def log_activity(cls, user, action_type, description, case=None, document=None, 
                     related_user=None, changes=None, ip_address=None, metadata=None):
        """
        Helper method to create an audit log entry.
        
        Args:
            user: User who performed the action
            action_type: Type of action from ACTION_CHOICES
            description: Human-readable description
            case: Related case (optional)
            document: Related document (optional)
            related_user: Related user if action is about another user (optional)
            changes: Dictionary of field changes (optional)
            ip_address: IP address of request (optional)
            metadata: Additional metadata dictionary (optional)
        """
        return cls.objects.create(
            user=user,
            action_type=action_type,
            description=description,
            case=case,
            document=document,
            related_user=related_user,
            changes=changes or {},
            ip_address=ip_address,
            metadata=metadata or {}
        )



class SystemSettings(models.Model):
    """
    Global system configuration settings for the advisor portal.
    Uses a singleton pattern - only one instance should exist.
    """
    
    # Credits Management
    CREDIT_CHOICES = [
        ('0.5', '0.5'),
        ('1.0', '1.0'),
        ('1.5', '1.5'),
        ('2.0', '2.0'),
        ('2.5', '2.5'),
        ('3.0', '3.0'),
    ]
    
    # Default available credit values (comma-separated)
    available_credits = models.CharField(
        max_length=50,
        default='0.5,1.0,1.5,2.0,2.5,3.0',
        help_text='Comma-separated list of available credit values (e.g., 0.5,1.0,1.5,2.0,2.5,3.0)'
    )
    
    # Default Case Settings
    default_case_due_days = models.PositiveIntegerField(
        default=7,
        validators=[MinValueValidator(1), MaxValueValidator(90)],
        help_text='Default number of days for case due date (1-90 days)'
    )
    
    rush_case_threshold_days = models.PositiveIntegerField(
        default=7,
        validators=[MinValueValidator(1), MaxValueValidator(90)],
        help_text='Threshold in days: cases with fewer days are marked as Rush'
    )
    
    # Release Settings (Scheduled Release)
    enable_scheduled_releases = models.BooleanField(
        default=True,
        help_text='Allow technicians to schedule delayed releases'
    )
    
    default_completion_delay_hours = models.PositiveIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(5)],
        choices=[(0, 'Immediate'), (1, '1 Hour'), (2, '2 Hours'), (3, '3 Hours'), (4, '4 Hours'), (5, '5 Hours')],
        help_text='Default delay (in hours, CST) before case shows as completed to member (0 = immediate)'
    )
    
    batch_release_time = models.TimeField(
        default='09:00',
        help_text='Time of day to process scheduled batch releases (HH:MM format, UTC)'
    )
    
    batch_release_enabled = models.BooleanField(
        default=True,
        help_text='Automatically process scheduled releases at batch_release_time'
    )
    
    # Email Notification Settings (tied to release schedule)
    enable_delayed_email_notifications = models.BooleanField(
        default=True,
        help_text='Send member notification emails when case is released'
    )
    
    default_email_delay_hours = models.PositiveIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(24)],
        choices=[
            (0, 'Immediately'),
            (1, '1 Hour'),
            (2, '2 Hours'),
            (3, '3 Hours'),
            (4, '4 Hours'),
            (5, '5 Hours'),
            (6, '6 Hours'),
            (12, '12 Hours'),
            (24, '24 Hours'),
        ],
        help_text='Default delay (in hours, CST) before sending member notification email (tied to release date)'
    )
    
    batch_email_enabled = models.BooleanField(
        default=True,
        help_text='Automatically send scheduled emails via batch job'
    )
    
    # API Configuration - Benefits Software
    benefits_software_api_url = models.CharField(
        max_length=500,
        blank=True,
        default='',
        help_text='Benefits-software API endpoint URL (placeholder for future integration)'
    )
    
    benefits_software_api_key = models.CharField(
        max_length=500,
        blank=True,
        default='',
        help_text='API key for benefits-software authentication (placeholder for future integration)'
    )
    
    benefits_software_api_enabled = models.BooleanField(
        default=False,
        help_text='Enable benefits-software API integration'
    )
    
    # Metadata
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='settings_updates'
    )
    
    class Meta:
        verbose_name = 'System Settings'
        verbose_name_plural = 'System Settings'
    
    def __str__(self):
        return 'System Settings'
    
    @classmethod
    def get_settings(cls):
        """Get or create the singleton settings instance"""
        obj, created = cls.objects.get_or_create(pk=1)
        return obj
    
    def get_available_credits_list(self):
        """Return available credits as a list of floats"""
        return [float(x.strip()) for x in self.available_credits.split(',')]
