from django.db import models
from project.models import UserProject
import uuid

# Create your models here.
class ProjectTestSuite(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False)
    project = models.ForeignKey(UserProject, on_delete=models.CASCADE)
    test_suite_name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.test_suite_name
    
    class Meta:
        indexes = [
            models.Index(fields=['project']),
            models.Index(fields=['test_suite_name']),
            models.Index(fields=['uuid'])
        ]
        ordering = ['-created_at']
        unique_together = ['project', 'test_suite_name']