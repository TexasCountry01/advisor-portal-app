# Generated migration for case resubmission feature
# This file should be saved as: cases/migrations/XXXX_add_resubmission_fields.py
# Replace XXXX with the next migration number in sequence

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cases', '[PREVIOUS_MIGRATION_NAME]'),  # Update with actual previous migration
    ]

    operations = [
        migrations.AddField(
            model_name='case',
            name='is_resubmitted',
            field=models.BooleanField(
                default=False,
                help_text='Indicates if this case has been resubmitted after completion'
            ),
        ),
        migrations.AddField(
            model_name='case',
            name='resubmission_count',
            field=models.PositiveIntegerField(
                default=0,
                help_text='Number of times this case has been resubmitted'
            ),
        ),
        migrations.AddField(
            model_name='case',
            name='previous_status',
            field=models.CharField(
                blank=True,
                choices=[
                    ('draft', 'Draft'),
                    ('submitted', 'Submitted'),
                    ('accepted', 'Accepted'),
                    ('hold', 'Hold'),
                    ('pending_review', 'Pending Review'),
                    ('completed', 'Completed'),
                ],
                max_length=20,
                help_text='Previous status before resubmission'
            ),
        ),
        migrations.AddField(
            model_name='case',
            name='resubmission_date',
            field=models.DateTimeField(
                blank=True,
                null=True,
                help_text='When the case was resubmitted by the member'
            ),
        ),
        migrations.AddField(
            model_name='case',
            name='resubmission_notes',
            field=models.TextField(
                blank=True,
                help_text='Notes from member explaining why the case is being resubmitted'
            ),
        ),
    ]
