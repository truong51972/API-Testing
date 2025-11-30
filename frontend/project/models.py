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
    file_id = models.CharField(max_length=255, blank=True, null=True, help_text="File ID from upload API")
    original_filename = models.CharField(max_length=255, blank=True, null=True, help_text="Original filename before upload")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    # AI Processing fields
    ai_processing_status = models.CharField(
        max_length=20, 
        choices=[
            ('pending', 'Pending'),
            ('processing', 'Processing'),
            ('completed', 'Completed'),
            ('failed', 'Failed')
        ],
        default='pending'
    )
    ai_processed_at = models.DateTimeField(blank=True, null=True)
    ai_error_message = models.TextField(blank=True, null=True)
    
    # API Integration fields
    api_collection = models.CharField(max_length=255, blank=True, null=True, help_text="Collection name used in API")
    api_response = models.JSONField(blank=True, null=True, help_text="Full API response data")
    doc_id = models.CharField(max_length=255, blank=True, null=True, help_text="Document ID from preprocessing API")

    def __str__(self):
        return self.file.name if self.file else self.link

class DocumentSection(models.Model):
    """Model để lưu các sections được AI extract từ document"""
    document = models.ForeignKey(ProjectDocument, on_delete=models.CASCADE, related_name="sections")
    section_title = models.CharField(max_length=500)
    section_content = models.TextField()
    section_type = models.CharField(
        max_length=50,
        choices=[
            ('api_endpoint', 'API Endpoint'),
            ('function', 'Function'),
            ('class', 'Class'),
            ('method', 'Method'),
            ('parameter', 'Parameter'),
            ('response', 'Response'),
            ('example', 'Example'),
            ('other', 'Other')
        ],
        default='other'
    )
    page_number = models.IntegerField(blank=True, null=True)
    is_selected = models.BooleanField(default=False)  # User có chọn section này không
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.document} - {self.section_title}"

class FunctionalRequirement(models.Model):
    """Model để lưu các Functional Requirements được AI annotate"""
    project = models.ForeignKey("UserProject", on_delete=models.CASCADE, related_name="functional_requirements")
    fr_info_id = models.UUIDField(unique=True, help_text="FR info ID from API")
    fr_group = models.CharField(max_length=255, help_text="FR group like 'u-fr-001: User Service'")
    description = models.TextField(blank=True, help_text="FR description")
    is_selected = models.BooleanField(default=False, help_text="Whether FR is selected by user")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.fr_group

    class Meta:
        unique_together = ['project', 'fr_info_id']
        ordering = ['fr_group']

class GeneratedTestCase(models.Model):
    """Model để lưu các test cases được AI generate"""
    uuid = models.UUIDField(default=uuid.uuid4, editable=False)
    project = models.ForeignKey("UserProject", on_delete=models.CASCADE, related_name="generated_test_cases")
    
    # API Endpoint information
    api_name = models.CharField(max_length=255, help_text="API endpoint name like 'Create Project', 'Delete Project'")
    http_method = models.CharField(max_length=10, default='POST', help_text="HTTP method: GET, POST, PUT, DELETE, etc.")
    request_url = models.CharField(max_length=500, blank=True, null=True, help_text="Full request URL")
    request_headers = models.JSONField(default=dict, blank=True, help_text="Request headers as JSON object")
    
    # Test case data
    test_case_id = models.IntegerField(help_text="Test case ID from API")
    test_case_name = models.CharField(max_length=500, help_text="Test case description")
    test_category = models.CharField(
        max_length=50,
        choices=[
            ('basic_validation', 'Basic Validation'),
            ('business_logic', 'Business Logic')
        ],
        default='basic_validation'
    )
    
    # Request and response data
    request_body_template = models.JSONField(default=dict, blank=True, help_text="Original request body template")
    request_mapping = models.JSONField(default=dict, blank=True, help_text="Request mapping with specific values")
    expected_output = models.JSONField(default=dict, blank=True, help_text="Expected response output")
    
    # Full test case data as JSON for flexibility
    test_case_data = models.JSONField(default=dict, blank=True, help_text="Complete test case data as JSON")
    
    # Selection status
    is_selected = models.BooleanField(default=False, help_text="Whether test case is selected by user")
    execute = models.BooleanField(default=False, help_text="Whether test case should be executed")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.api_name} - TC-{self.test_case_id}: {self.test_case_name[:50]}"
    
    class Meta:
        indexes = [
            models.Index(fields=['project']),
            models.Index(fields=['api_name']),
            models.Index(fields=['test_category']),
            models.Index(fields=['uuid']),
            models.Index(fields=['created_at'])
        ]
        ordering = ['api_name', 'test_category', 'test_case_id']