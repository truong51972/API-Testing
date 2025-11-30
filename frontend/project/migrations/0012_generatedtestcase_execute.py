# Generated migration to add execute field to GeneratedTestCase

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('project', '0011_generatedtestcase_is_selected'),
    ]

    operations = [
        migrations.AddField(
            model_name='generatedtestcase',
            name='execute',
            field=models.BooleanField(default=False, help_text='Whether test case should be executed'),
        ),
    ]

