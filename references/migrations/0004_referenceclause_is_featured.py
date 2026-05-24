from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('references', '0003_subcategory_to_textfield'),
    ]

    operations = [
        migrations.AddField(
            model_name='referenceclause',
            name='is_featured',
            field=models.BooleanField(default=False, db_index=True),
        ),
    ]
