from django.db import models
from test_suite.models import ProjectTestSuite
import uuid

# Create your models here.
class TestCaseHistory(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False)
    test_case_name = models.CharField(max_length=255, default='Unnamed Test Case')
    test_suite = models.ForeignKey(ProjectTestSuite, on_delete=models.CASCADE)
    test_case = models.JSONField()  # Assuming test_case is a JSON object
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.test_case}"
    
    class Meta:
        indexes = [
            models.Index(fields=['test_suite']),
            models.Index(fields=['uuid'])
        ]
        ordering = ['-created_at']
        