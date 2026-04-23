from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0020_alter_auditlog_action_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='systemsettings',
            name='super_dev_email',
            field=models.EmailField(blank=True, default='', help_text='Optional dev/monitor account email to exclude from reviewer dropdowns and user counts.', max_length=254),
        ),
    ]
