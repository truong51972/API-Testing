from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from project.models import ProjectDocument

# Create your views here.
@login_required
def home(request):
    return render(request, 'main/home.html')

def library(request):
    """Hiển thị thư viện tài liệu của user"""
    if not request.user.is_authenticated:
        messages.warning(request, 'Please log in to access the Library.')
        return redirect('home')

    # Lấy tất cả documents của user
    documents = ProjectDocument.objects.filter(project__user=request.user).order_by('-uploaded_at')

    context = {
        'documents': documents,
    }
    return render(request, 'main/library.html', context)