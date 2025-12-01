from django.db import models
from project.models import UserProject
from test_suite.models import ProjectTestSuite
import uuid

# Create your models here.
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
