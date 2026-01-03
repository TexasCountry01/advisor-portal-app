from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

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
    
    batch_release_time = models.TimeField(
        default='09:00',
        help_text='Time of day to process scheduled batch releases (HH:MM format, UTC)'
    )
    
    batch_release_enabled = models.BooleanField(
        default=True,
        help_text='Automatically process scheduled releases at batch_release_time'
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
