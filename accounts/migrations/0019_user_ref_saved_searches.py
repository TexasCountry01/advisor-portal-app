from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0018_user_can_manage_delegates_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='ref_saved_searches',
            field=models.JSONField(
                default=list,
                blank=True,
                help_text='User-specific reference library recent searches (last 10).',
            ),
        ),
    ]
