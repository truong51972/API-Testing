# Generated manually for adding doc_id field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('project', '0007_projectdocument_original_filename'),
    ]

    operations = [
        migrations.AddField(
            model_name='projectdocument',
            name='doc_id',
            field=models.CharField(blank=True, help_text='Document ID from preprocessing API', max_length=255, null=True),
        ),
    ]