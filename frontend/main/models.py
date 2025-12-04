from django.db import models
from django.contrib.auth.models import User
from project.models import UserProject
from test_suite.models import ProjectTestSuite
import uuid

# Create your models here.
class UserActivity(models.Model):
    """Model để lưu các hoạt động/request của user"""
    ACTIVITY_TYPES = [
        ('project_created', 'Project Created'),
        ('document_uploaded', 'Document Uploaded'),
        ('test_suite_executed', 'Test Suite Executed'),
        ('test_cases_generated', 'Test Cases Generated'),
    ]
    
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activities')
    activity_type = models.CharField(max_length=50, choices=ACTIVITY_TYPES)
    project = models.ForeignKey(UserProject, on_delete=models.CASCADE, null=True, blank=True, related_name='activities')
    description = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.get_activity_type_display()} - {self.created_at}"
    
    class Meta:
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['activity_type']),
            models.Index(fields=['created_at']),
            models.Index(fields=['project']),
        ]
        ordering = ['-created_at']

class TestSuiteReport(models.Model):
    """Model để lưu lịch sử các test suite reports đã chạy"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    project = models.ForeignKey(UserProject, on_delete=models.CASCADE, related_name='test_reports')
    test_suite = models.ForeignKey(ProjectTestSuite, on_delete=models.SET_NULL, null=True, blank=True, related_name='reports')
    test_suite_report_id = models.CharField(max_length=255, help_text="Test Suite Report ID from API")
    api_test_suite_id = models.CharField(max_length=255, blank=True, null=True, help_text="Test Suite ID from API that was executed")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    executed_at = models.DateTimeField(auto_now_add=True, help_text="Thời gian chạy test suite")
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Report {self.test_suite_report_id} - {self.project.project_name}"
    
    class Meta:
        indexes = [
            models.Index(fields=['project']),
            models.Index(fields=['test_suite']),
            models.Index(fields=['test_suite_report_id']),
            models.Index(fields=['status']),
            models.Index(fields=['uuid']),
        ]
        ordering = ['-executed_at', '-created_at']
