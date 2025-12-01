from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.utils import translation
from django.conf import settings
from django.http import HttpResponseRedirect
from django.urls import reverse
from project.models import ProjectDocument, UserProject
from main.models import TestSuiteReport
import requests
import urllib3

# Disable SSL warnings for development
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Import API endpoint from project views
AGENT_API_BASE_URL = "https://api-t.truong51972.id.vn/"
GET_TEST_REPORT_ENDPOINT = f"{AGENT_API_BASE_URL}api/v1/execute-and-report/report"

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

def check_and_update_report_status(report):
    """Kiểm tra và cập nhật status của report từ API"""
    if report.status in ['completed', 'failed']:
        return  # Đã hoàn thành, không cần check
    
    try:
        headers = {
            'Content-Type': 'application/json',
            'accept': 'application/json',
            'X-Service-Name': 'agent-service',
            'Authorization': 'Basic YWRtaW46YWRtaW4='
        }
        
        # Gọi API để lấy report
        url = f"{GET_TEST_REPORT_ENDPOINT}/{report.test_suite_report_id}"
        response = requests.get(url, headers=headers, verify=False, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            result = data.get('result', {})
            code = result.get('code', '')
            
            # Code có thể là string hoặc array, normalize về list để check
            if isinstance(code, str):
                code_list = [code]
            elif isinstance(code, list):
                code_list = code
            else:
                code_list = []
            
            # Nếu report đã ready (code chứa '0000' hoặc có data)
            if '0000' in code_list or data.get('data'):
                # Kiểm tra xem có lỗi không
                report_data = data.get('data', [])
                if isinstance(report_data, list) and len(report_data) > 0:
                    # Có kết quả, check xem có test nào failed không
                    has_failed = False
                    for test in report_data:
                        if isinstance(test, dict):
                            # Check status field của test case
                            test_status = test.get('status', '').lower()
                            if test_status == 'failed':
                                has_failed = True
                                break
                            
                            # Check response_status_code nếu có
                            response_status_code = test.get('response_status_code')
                            if response_status_code and response_status_code >= 400:
                                has_failed = True
                                break
                            
                            # Check result.code field nếu có
                            test_result = test.get('result', {})
                            if isinstance(test_result, dict):
                                test_code = test_result.get('code', '')
                                if isinstance(test_code, list):
                                    if '0000' not in test_code:
                                        has_failed = True
                                        break
                                elif test_code and test_code != '0000':
                                    has_failed = True
                                    break
                    
                    report.status = 'failed' if has_failed else 'completed'
                elif report_data:
                    # Có data nhưng không phải list
                    report.status = 'completed'
                else:
                    # Có response nhưng chưa có data cụ thể
                    report.status = 'completed'
                report.save()
            elif code_list and '0000' not in code_list:
                # Có lỗi từ API (code không phải '0000')
                report.status = 'failed'
                report.save()
        elif response.status_code == 404:
            # Report chưa sẵn sàng hoặc không tồn tại, giữ nguyên status
            pass
        else:
            # Lỗi khác, có thể đánh dấu failed nếu cần
            pass
    except requests.exceptions.Timeout:
        # Timeout, giữ nguyên status
        pass
    except requests.exceptions.RequestException:
        # Lỗi kết nối, giữ nguyên status
        pass
    except Exception as e:
        # Lỗi khác, giữ nguyên status
        pass

def reports(request):
    """Hiển thị danh sách các report đã chạy của user"""
    if not request.user.is_authenticated:
        messages.warning(request, 'Please log in to access the Reports.')
        return redirect('home')

    # Lấy tất cả reports của user (qua project.user)
    all_reports = TestSuiteReport.objects.filter(project__user=request.user).order_by('-executed_at', '-created_at')
    
    # Filter theo project nếu có query parameter
    project_uuid = request.GET.get('project_uuid')
    selected_project = None
    if project_uuid:
        try:
            selected_project = UserProject.objects.get(uuid=project_uuid, user=request.user)
            all_reports = all_reports.filter(project=selected_project)
        except (UserProject.DoesNotExist, ValueError):
            messages.warning(request, 'Dự án không tồn tại hoặc bạn không có quyền truy cập.')
    
    # Kiểm tra và cập nhật status cho các reports đang chạy (chỉ check 10 reports gần nhất để tránh timeout)
    running_reports = all_reports.filter(status__in=['running', 'pending'])[:10]
    for report in running_reports:
        check_and_update_report_status(report)
    
    # Pagination: 12 rows per page
    paginator = Paginator(all_reports, 12)
    page_number = request.GET.get('page', 1)
    reports_page = paginator.get_page(page_number)
    
    # Lấy danh sách projects để hiển thị trong filter dropdown
    user_projects = UserProject.objects.filter(user=request.user).order_by('-created_at')

    context = {
        'reports': reports_page,
        'paginator': paginator,
        'projects': user_projects,
        'selected_project_uuid': selected_project.uuid if selected_project else None,
    }
    return render(request, 'main/reports.html', context)

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