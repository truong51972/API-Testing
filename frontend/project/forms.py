from django import forms
from .models import ProjectDocument

class ProjectDocumentForm(forms.ModelForm):
    class Meta:
        model = ProjectDocument
        fields = ["file", "link"]
