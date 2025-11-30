# Generated migration to add is_selected field to GeneratedTestCase

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('project', '0010_generatedtestcase'),
    ]

    operations = [
        migrations.AddField(
            model_name='generatedtestcase',
            name='is_selected',
            field=models.BooleanField(default=False, help_text='Whether test case is selected by user'),
        ),
    ]

