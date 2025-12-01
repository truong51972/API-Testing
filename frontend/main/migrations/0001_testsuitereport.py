# Generated manually for TestSuiteReport model

import django.db.models.deletion
from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('project', '0001_initial_squashed_0009_functionalrequirement'),
        ('test_suite', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='TestSuiteReport',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('test_suite_report_id', models.CharField(help_text='Test Suite Report ID from API', max_length=255)),
                ('api_test_suite_id', models.CharField(blank=True, help_text='Test Suite ID from API that was executed', max_length=255, null=True)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('running', 'Running'), ('completed', 'Completed'), ('failed', 'Failed')], default='pending', max_length=20)),
                ('executed_at', models.DateTimeField(auto_now_add=True, help_text='Thời gian chạy test suite')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='test_reports', to='project.userproject')),
                ('test_suite', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='reports', to='test_suite.projecttestsuite')),
            ],
            options={
                'ordering': ['-executed_at', '-created_at'],
                'indexes': [
                    models.Index(fields=['project'], name='main_testsui_project_idx'),
                    models.Index(fields=['test_suite'], name='main_testsui_test_su_idx'),
                    models.Index(fields=['test_suite_report_id'], name='main_testsui_test_su_rep_idx'),
                    models.Index(fields=['status'], name='main_testsui_status_idx'),
                    models.Index(fields=['uuid'], name='main_testsui_uuid_idx'),
                ],
            },
        ),
    ]

