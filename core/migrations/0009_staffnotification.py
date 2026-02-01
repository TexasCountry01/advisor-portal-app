# Generated migration for StaffNotification model

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('cases', '0032_case_error_modification_count_case_has_profeds_error'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='StaffNotification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('notification_type', models.CharField(choices=[('case_modification_error', 'Case Modification Error Flagged'), ('case_assigned', 'Case Assigned to You'), ('quality_review_feedback', 'Quality Review Feedback'), ('case_on_hold', 'Case Placed on Hold'), ('system_alert', 'System Alert')], help_text='Type of notification', max_length=50)),
                ('title', models.CharField(help_text='Notification title', max_length=255)),
                ('message', models.TextField(help_text='Notification message content')),
                ('is_read', models.BooleanField(default=False, help_text='Whether staff member has viewed this notification')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('read_at', models.DateTimeField(blank=True, help_text='When notification was viewed', null=True)),
                ('case', models.ForeignKey(blank=True, help_text='Related case (if applicable)', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='staff_notifications', to='cases.case')),
                ('user', models.ForeignKey(help_text='Staff member receiving this notification', on_delete=django.db.models.deletion.CASCADE, related_name='staff_notifications', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='staffnotification',
            index=models.Index(fields=['user', '-created_at'], name='core_staffno_user_id_created_idx'),
        ),
        migrations.AddIndex(
            model_name='staffnotification',
            index=models.Index(fields=['user', 'is_read'], name='core_staffno_user_id_is_read_idx'),
        ),
    ]
