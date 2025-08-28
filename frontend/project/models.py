from django.db import models
from django.contrib.auth.models import User
import uuid
from django.conf import settings

# Create your models here.
class UserProject(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    project_name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.project_name
    
    class Meta:
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['project_name']),
            models.Index(fields=['uuid'])
        ]
        ordering = ['-created_at']
        unique_together = ['user', 'project_name']

class ProjectDocument(models.Model):
    project = models.ForeignKey("UserProject", on_delete=models.CASCADE, related_name="documents")
    file = models.FileField(upload_to="uploads/", blank=True, null=True)
    link = models.URLField(blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.file.name if self.file else self.link