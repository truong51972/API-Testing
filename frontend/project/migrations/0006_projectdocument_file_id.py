# Generated manually for file_id field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('project', '0005_projectdocument_api_collection_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='projectdocument',
            name='file_id',
            field=models.CharField(blank=True, help_text='File ID from upload API', max_length=255, null=True),
        ),
    ]
