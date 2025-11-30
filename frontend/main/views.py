from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.utils import translation
from django.conf import settings
from django.http import HttpResponseRedirect
from django.urls import reverse
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

def set_language(request):
    """View to handle language switching"""
    if request.method == 'POST':
        language = request.POST.get('language')
        if language in [lang[0] for lang in settings.LANGUAGES]:
            # Activate the language for this request
            translation.activate(language)
            # Save to session (LocaleMiddleware reads from 'django_language' key)
            request.session['django_language'] = language
            # Create response and set cookie
            response = HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
            # Set cookie with language preference (LocaleMiddleware also reads from cookie)
            response.set_cookie(settings.LANGUAGE_COOKIE_NAME, language, max_age=365*24*60*60)  # 1 year
            return response
    # If GET request or invalid language, redirect to referer or home
    return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))