from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
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
    all_documents = ProjectDocument.objects.filter(project__user=request.user).order_by('-uploaded_at')
    
    # Pagination: 12 rows per page
    paginator = Paginator(all_documents, 12)
    page_number = request.GET.get('page', 1)
    documents = paginator.get_page(page_number)

    context = {
        'documents': documents,
        'paginator': paginator,
    }
    return render(request, 'main/library.html', context)