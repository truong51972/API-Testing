from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.utils import translation
from django.conf import settings
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.db.models import Count, Q
from datetime import datetime, timedelta
from django.utils import timezone
from project.models import ProjectDocument, UserProject, GeneratedTestCase
from main.models import TestSuiteReport, UserActivity
from test_suite.models import ProjectTestSuite
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
    user = request.user
    current_username = user.username
    
    # Calculate statistics
    # Total projects
    total_projects = UserProject.objects.filter(user=user).count()
    
    # Total test suites
    user_projects = UserProject.objects.filter(user=user)
    total_test_suites = ProjectTestSuite.objects.filter(project__in=user_projects).count()
    
    # Total test cases
    total_test_cases = GeneratedTestCase.objects.filter(project__in=user_projects).count()
    selected_test_cases = GeneratedTestCase.objects.filter(project__in=user_projects, is_selected=True).count()
    
    # Test reports statistics
    test_reports = TestSuiteReport.objects.filter(project__in=user_projects)
    total_reports = test_reports.count()
    completed_reports = test_reports.filter(status='completed').count()
    running_reports = test_reports.filter(status='running').count()
    failed_reports = test_reports.filter(status='failed').count()
    pending_reports = test_reports.filter(status='pending').count()
    
    # Calculate test success rate (if we have completed reports)
    # Note: This is a simplified calculation. In reality, you might need to fetch report details from API
    test_success_rate = 0
    if completed_reports > 0:
        # For now, we'll use a simple calculation based on completed vs failed
        # In production, you'd want to fetch actual test results from API
        test_success_rate = round((completed_reports / total_reports * 100) if total_reports > 0 else 0)
    
    # Recent projects pagination (5 items per page)
    all_recent_projects = UserProject.objects.filter(user=user).order_by('-created_at')
    projects_paginator = Paginator(all_recent_projects, 5)
    projects_page_number = request.GET.get('projects_page', 1)
    recent_projects_page = projects_paginator.get_page(projects_page_number)
    
    # Recent documents pagination (5 items per page)
    all_recent_documents = ProjectDocument.objects.filter(project__in=user_projects).order_by('-uploaded_at')
    documents_paginator = Paginator(all_recent_documents, 5)
    documents_page_number = request.GET.get('documents_page', 1)
    recent_documents_page = documents_paginator.get_page(documents_page_number)
    
    # All test reports pagination (5 items per page)
    all_reports_queryset = test_reports.order_by('-executed_at')
    reports_paginator = Paginator(all_reports_queryset, 6)
    reports_page_number = request.GET.get('reports_page', 1)
    all_reports_page = reports_paginator.get_page(reports_page_number)
    
    # Weekly statistics (last 7 days)
    seven_days_ago = timezone.now() - timedelta(days=7)
    projects_this_week = UserProject.objects.filter(user=user, created_at__gte=seven_days_ago).count()
    test_suites_this_week = ProjectTestSuite.objects.filter(
        project__in=user_projects, 
        created_at__gte=seven_days_ago
    ).count()
    test_cases_this_week = GeneratedTestCase.objects.filter(
        project__in=user_projects, 
        created_at__gte=seven_days_ago
    ).count()
    reports_this_week = test_reports.filter(executed_at__gte=seven_days_ago).count()
    
    # Calculate percentage change (simplified - comparing with previous week)
    fourteen_days_ago = timezone.now() - timedelta(days=14)
    projects_previous_week = UserProject.objects.filter(
        user=user, 
        created_at__gte=fourteen_days_ago,
        created_at__lt=seven_days_ago
    ).count()
    
    projects_change = 0
    if projects_previous_week > 0:
        projects_change = round(((projects_this_week - projects_previous_week) / projects_previous_week) * 100, 1)
    elif projects_this_week > 0:
        projects_change = 100
    
    # Documents statistics
    total_documents = ProjectDocument.objects.filter(project__in=user_projects).count()
    completed_documents = ProjectDocument.objects.filter(
        project__in=user_projects, 
        ai_processing_status='completed'
    ).count()
    
    # Request frequency statistics (last 30 days)
    # Read from UserActivity model (much simpler and more accurate)
    now_local = timezone.localtime(timezone.now())
    thirty_days_ago = now_local - timedelta(days=30)
    
    # Get daily activity counts for the last 30 days from UserActivity
    request_frequency_data = []
    for i in range(30):
        day = now_local - timedelta(days=29-i)
        day_start = timezone.make_aware(datetime.combine(day.date(), datetime.min.time()))
        day_end = day_start + timedelta(days=1)
        
        # Count activities by type for this day from UserActivity using timezone-aware range
        day_activities = UserActivity.objects.filter(
            user=user,
            created_at__gte=day_start,
            created_at__lt=day_end
        )
        
        projects_count = day_activities.filter(activity_type='project_created').count()
        documents_count = day_activities.filter(activity_type='document_uploaded').count()
        test_reports_count = day_activities.filter(activity_type='test_suite_executed').count()
        test_cases_count = day_activities.filter(activity_type='test_cases_generated').count()
        
        total_activities = day_activities.count()
        
        request_frequency_data.append({
            'date': day.strftime('%Y-%m-%d'),
            'date_display': day.strftime('%m/%d'),
            'projects': projects_count,
            'test_reports': test_reports_count,
            'test_cases': test_cases_count,
            'documents': documents_count,
            'total': total_activities
        })
    
    # Calculate statistics
    total_activities_30_days = sum(item['total'] for item in request_frequency_data)
    avg_daily_activities = round(total_activities_30_days / 30, 1) if total_activities_30_days > 0 else 0
    max_daily_activities = max(item['total'] for item in request_frequency_data) if request_frequency_data else 0
    
    # Weekly activity (last 7 days)
    last_7_days_activities = sum(item['total'] for item in request_frequency_data[-7:])
    
    context = {
        'current_username': current_username,
        # Main statistics
        'total_projects': total_projects,
        'total_test_suites': total_test_suites,
        'total_test_cases': total_test_cases,
        'selected_test_cases': selected_test_cases,
        'total_reports': total_reports,
        'completed_reports': completed_reports,
        'running_reports': running_reports,
        'failed_reports': failed_reports,
        'pending_reports': pending_reports,
        'test_success_rate': test_success_rate,
        # Recent data with pagination
        'recent_projects_page': recent_projects_page,
        'recent_documents_page': recent_documents_page,
        'all_reports_page': all_reports_page,
        # Weekly statistics
        'projects_this_week': projects_this_week,
        'test_suites_this_week': test_suites_this_week,
        'test_cases_this_week': test_cases_this_week,
        'reports_this_week': reports_this_week,
        'projects_change': projects_change,
        # Documents
        'total_documents': total_documents,
        'completed_documents': completed_documents,
        # Request frequency
        'request_frequency_data': request_frequency_data,  # Will be converted to JSON by json_script filter
        'total_activities_30_days': total_activities_30_days,
        'avg_daily_activities': avg_daily_activities,
        'max_daily_activities': max_daily_activities,
        'last_7_days_activities': last_7_days_activities,
    }
    
    return render(request, 'main/home.html', context)

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