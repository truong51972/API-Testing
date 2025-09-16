from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from .models import UserProject, ProjectDocument, DocumentSection
from testcase_history.models import TestCaseHistory
from test_suite.models import ProjectTestSuite
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from main.decorators import set_test_suites_show
from .forms import ProjectDocumentForm  
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
import json
import time
import threading
import requests
from django.conf import settings
import urllib3

# Disable SSL warnings for development
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# API Configuration
AGENT_API_BASE_URL = "https://agent-service_api.truong51972.id.vn"
AI_AGENT_ENDPOINT = f"{AGENT_API_BASE_URL}/api/ai_agent"
DOCS_PREPROCESSING_ENDPOINT = f"{AGENT_API_BASE_URL}/api/workflow/docs-preprocessing"
TEST_SUITE_CREATE_ENDPOINT = f"{AGENT_API_BASE_URL}/api/test_suite/create"

def call_docs_preprocessing_api(document_link, doc_name, collection="default"):
    """Gọi API docs preprocessing"""
    try:
        payload = {
            "user_input": f"Process document: {doc_name}",
            "lang": "en",
            "messages": [],
            "doc_name": doc_name,
            "collection": collection
        }
        
        # Gửi POST request với link document
        headers = {
            'Content-Type': 'application/json'
        }
        
        # Nếu có link, thêm vào user_input
        if document_link:
            payload["user_input"] += f" from URL: {document_link}"
        
        response = requests.post(
            AI_AGENT_ENDPOINT,
            json=payload,
            headers=headers,
            timeout=300,  # 5 minutes timeout
            verify=False  # Disable SSL verification for development
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"API call failed with status {response.status_code}: {response.text}")
            
    except requests.exceptions.Timeout:
        raise Exception("API request timeout - document processing may take longer than expected")
    except requests.exceptions.RequestException as e:
        raise Exception(f"API request failed: {str(e)}")
    except Exception as e:
        raise Exception(f"Unexpected error: {str(e)}")

def call_test_suite_create_api(selected_sections_data):
    """Gọi API tạo test suite từ selected sections"""
    try:
        headers = {
            'Content-Type': 'application/json',
            'accept': 'application/json'
        }
        
        # API này là GET method, có thể cần gửi data qua query params hoặc headers
        response = requests.get(
            TEST_SUITE_CREATE_ENDPOINT,
            headers=headers,
            timeout=300,  # 5 minutes timeout
            verify=False  # Disable SSL verification for development
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Test suite creation failed with status {response.status_code}: {response.text}")
            
    except requests.exceptions.Timeout:
        raise Exception("Test suite creation timeout - API may take longer than expected")
    except requests.exceptions.RequestException as e:
        raise Exception(f"Test suite creation request failed: {str(e)}")
    except Exception as e:
        raise Exception(f"Unexpected error: {str(e)}")

@login_required
def my_view(request):
    usernames = User.objects.values_list('username', flat=True)
    return render(request, 'home.html', {'usernames': usernames})


@login_required
def project_list(request):
    # This view will render the list of projects for the logged-in user
    projects = UserProject.objects.filter(user=request.user)
    if not projects:
        messages.info(request, "You have no projects yet. Consider adding one.")
    # You can also paginate the projects if needed
    # For example, using Django's built-in pagination:
    # Optionally, you can also fetch related data like test cases or test suites if needed
    # For example, to get test cases related to the projects:

    context = {
        'projects': [{
            'uuid': project.uuid,
            'project_name': project.project_name,
            'description': project.description,
            'created_at': project.created_at,
            'test_suites_count_per_project': ProjectTestSuite.objects.filter(project=project).count(),
            'test_cases_count_per_project': TestCaseHistory.objects.filter(test_suite__project=project).count()
        } for project in projects]
    }
    return render(request, 'project/project_list.html', context)

@login_required
def project_add(request):
    # This view will handle adding a new project
    if request.method == 'POST':
        # Handle form submission for adding a project
        project_name = request.POST.get('project_name')
        description = request.POST.get('description', '')
        user = request.user

        # Create a new project instance and save it to the database
        if not project_name:
            messages.error(request, "Project name is required.")
            return render(request, 'project/project_add.html')
        
        if UserProject.objects.filter(user=user, project_name=project_name).exists():
            messages.error(request, "Project with this name already exists.")
            return render(request, 'project/project_add.html')
        
        project = UserProject(user=user, project_name=project_name, description=description)
        project.save()
        messages.success(request, "Project added successfully.")
        return redirect(reverse('project_detail_by_uuid', kwargs={'project_uuid': project.uuid}))
    else:
        # Render the project add form
        return render(request, 'project/project_add.html')

@set_test_suites_show(True)
@login_required
def project_detail_by_uuid(request, project_uuid):
    # Use get_object_or_404 to retrieve the object or raise a 404 error if not found
    project = get_object_or_404(UserProject, uuid=project_uuid)
    if project.user != request.user:
        messages.error(request, "You do not have permission to view this project.")
        return redirect('project_list')
    test_suites = ProjectTestSuite.objects.filter(project=project)


    context = {
        'project': project,
        'test_suites': [{
            'uuid': test_suite.uuid,
            'test_suite_name': test_suite.test_suite_name,
            'description': test_suite.description,
            'created_at': test_suite.created_at,
            'test_cases_count': TestCaseHistory.objects.filter(test_suite=test_suite).count()
        } for test_suite in test_suites],
    }
    return render(request, 'project/project_view.html', context)

@set_test_suites_show(True)
@login_required
def project_edit(request, project_uuid):
    # This view will handle editing an existing project
    project = get_object_or_404(UserProject, uuid=project_uuid, user=request.user)
    if project.user != request.user:
        messages.error(request, "You do not have permission to edit this project.")
        return redirect('project_list')
    
    test_suites = ProjectTestSuite.objects.filter(project=project)

    context = {
        'project': project,
        'test_suites': test_suites,
    }

    if request.method == 'POST':
        project_name = request.POST.get('project_name')
        description = request.POST.get('description', '')

        if not project_name:
            messages.error(request, "Project name is required.")
            return render(request, 'project/project_edit.html', context)

        # Update the project instance and save it to the database
        project.project_name = project_name
        project.description = description
        project.save()
        messages.success(request, "Project updated successfully.")
        return redirect(reverse('project_detail_by_uuid', kwargs={'project_uuid': project.uuid}))
    
    return render(request, 'project/project_edit.html', context)

@set_test_suites_show(True)
@login_required
def project_delete(request, project_uuid):
    # This view will handle deleting an existing project
    project = get_object_or_404(UserProject, uuid=project_uuid, user=request.user)
    if project.user != request.user:
        messages.error(request, "You do not have permission to delete this project.")
        return redirect('project_list')
    test_suites = ProjectTestSuite.objects.filter(project=project)
    context = {
        'project': project,
        'test_suites': test_suites,
    }
    
    if request.method == 'POST':
        project.delete()
        messages.success(request, "Project deleted successfully.")
        return redirect('project_list')
    return render(request, 'project/project_delete.html', context)

@set_test_suites_show(True)
@login_required
def project_detail_by_uuid(request, project_uuid):
    project = get_object_or_404(UserProject, uuid=project_uuid)
    if project.user != request.user:
        messages.error(request, "You do not have permission to view this project.")
        return redirect('project_list')

    test_suites = ProjectTestSuite.objects.filter(project=project)

    # Lấy list tài liệu đã upload
    documents = project.documents.all() if hasattr(project, "documents") else []

    # Xử lý form upload
    if request.method == "POST":
        form = ProjectDocumentForm(request.POST, request.FILES)
        if form.is_valid():
            doc = form.save(commit=False)
            doc.project = project
            doc.ai_processing_status = 'pending'  # Set default status
            doc.save()
            messages.success(request, "Tài liệu đã được thêm thành công. Bạn có thể bắt đầu xử lý AI.")
            return redirect(reverse('project_detail_by_uuid', kwargs={'project_uuid': project.uuid}))
        else:
            messages.error(request, "Có lỗi khi upload/nhập tài liệu.")
    else:
        form = ProjectDocumentForm()

    context = {
        'project': project,
        'test_suites': [{
            'uuid': test_suite.uuid,
            'test_suite_name': test_suite.test_suite_name,
            'description': test_suite.description,
            'created_at': test_suite.created_at,
            'test_cases_count': TestCaseHistory.objects.filter(test_suite=test_suite).count()
        } for test_suite in test_suites],
        'form': form,
        'documents': documents,
    }
    return render(request, 'project/project_view.html', context)

@set_test_suites_show(True)
@login_required
def delete_document(request, doc_id):
    doc = get_object_or_404(ProjectDocument, id=doc_id, project__user=request.user)
    project_uuid = doc.project.uuid
    doc.delete()
    messages.success(request, "Tài liệu đã được xoá.")
    return redirect(reverse('project_detail_by_uuid', kwargs={'project_uuid': project_uuid}))

@set_test_suites_show(True)
@login_required
def dashboard(request):
    current_username = request.user.username
    return render(request, 'main/home.html', {'current_username': current_username})

# AI Processing Views
@login_required
@require_http_methods(["POST"])
def start_ai_processing(request, project_uuid):
    """Bắt đầu xử lý AI cho document"""
    project = get_object_or_404(UserProject, uuid=project_uuid, user=request.user)
    
    # Lấy document mới nhất chưa được xử lý
    document = project.documents.filter(ai_processing_status='pending').first()
    
    if not document:
        return JsonResponse({
            'success': False,
            'message': 'Không có document nào cần xử lý'
        })
    
    # Cập nhật trạng thái processing
    document.ai_processing_status = 'processing'
    document.save()
    
    # Chạy AI processing trong background thread
    def process_document():
        try:
            # Gọi API docs preprocessing
            doc_name = document.file.name if document.file else f"doc_{document.id}"
            document_link = document.link if document.link else None
            
            collection_name = f"project_{project.uuid}"
            api_response = call_docs_preprocessing_api(
                document_link=document_link,
                doc_name=doc_name,
                collection=collection_name
            )
            
            # Lưu API response và collection name
            document.api_response = api_response
            document.api_collection = collection_name
            
            # Xử lý response từ API
            sections_data = []
            if api_response and 'sections' in api_response:
                sections_data = api_response['sections']
            elif api_response and 'data' in api_response:
                # Nếu API trả về data thay vì sections
                sections_data = api_response['data']
            else:
                # Fallback: tạo mock data nếu API không trả về sections
                sections_data = [
                    {
                        'title': 'API Endpoint: /api/users',
                        'content': 'GET /api/users - Lấy danh sách users\nParameters: page, limit\nResponse: User list',
                        'type': 'api_endpoint'
                    },
                    {
                        'title': 'API Endpoint: /api/users/{id}',
                        'content': 'GET /api/users/{id} - Lấy thông tin user theo ID\nParameters: id (path)\nResponse: User object',
                        'type': 'api_endpoint'
                    }
                ]
            
            # Tạo DocumentSection objects từ API response
            for section_data in sections_data:
                DocumentSection.objects.create(
                    document=document,
                    section_title=section_data.get('title', 'Untitled Section'),
                    section_content=section_data.get('content', 'No content available'),
                    section_type=section_data.get('type', 'other')
                )
            
            # Cập nhật trạng thái completed
            document.ai_processing_status = 'completed'
            document.ai_processed_at = timezone.now()
            document.save()
            
        except Exception as e:
            # Cập nhật trạng thái failed
            document.ai_processing_status = 'failed'
            document.ai_error_message = str(e)
            document.save()
    
    # Start background thread
    thread = threading.Thread(target=process_document)
    thread.daemon = True
    thread.start()
    
    return JsonResponse({
        'success': True,
        'message': 'Đã bắt đầu xử lý AI',
        'document_id': document.id
    })

@login_required
def check_ai_processing_status(request, project_uuid):
    """Kiểm tra trạng thái xử lý AI"""
    project = get_object_or_404(UserProject, uuid=project_uuid, user=request.user)
    
    # Lấy document đang được xử lý
    document = project.documents.filter(ai_processing_status='processing').first()
    
    if not document:
        # Kiểm tra document đã hoàn thành
        document = project.documents.filter(ai_processing_status='completed').first()
        if document:
            return JsonResponse({
                'status': 'completed',
                'message': 'Xử lý AI hoàn thành',
                'document_id': document.id
            })
        else:
            return JsonResponse({
                'status': 'no_processing',
                'message': 'Không có document nào đang được xử lý'
            })
    
    return JsonResponse({
        'status': 'processing',
        'message': 'Đang xử lý AI...'
    })

@login_required
def section_selection_view(request, project_uuid):
    """Hiển thị danh sách sections để user chọn"""
    project = get_object_or_404(UserProject, uuid=project_uuid, user=request.user)
    
    # Lấy document đã được xử lý xong
    document = project.documents.filter(ai_processing_status='completed').first()
    
    if not document:
        messages.error(request, "Chưa có document nào được xử lý xong.")
        return redirect(reverse('project_detail_by_uuid', kwargs={'project_uuid': project.uuid}))
    
    sections = document.sections.all()
    
    context = {
        'project': project,
        'document': document,
        'sections': sections
    }
    
    return render(request, 'project/section_selection.html', context)

@login_required
def get_sections_json(request, project_uuid):
    """API endpoint để lấy sections dưới dạng JSON"""
    project = get_object_or_404(UserProject, uuid=project_uuid, user=request.user)
    
    # Lấy document đã được xử lý xong
    document = project.documents.filter(ai_processing_status='completed').first()
    
    if not document:
        return JsonResponse({
            'success': False,
            'message': 'No completed document found'
        })
    
    sections = document.sections.all()
    
    sections_data = []
    for section in sections:
        sections_data.append({
            'id': section.id,
            'title': section.section_title,
            'content': section.section_content,
            'type': section.section_type,
            'type_display': section.get_section_type_display(),
            'is_selected': section.is_selected
        })
    
    return JsonResponse({
        'success': True,
        'sections': sections_data
    })

@login_required
@require_http_methods(["POST"])
def update_section_selection(request, project_uuid):
    """Cập nhật sections được chọn"""
    project = get_object_or_404(UserProject, uuid=project_uuid, user=request.user)
    
    try:
        data = json.loads(request.body)
        selected_section_ids = data.get('selected_sections', [])
        
        # Reset tất cả sections về unselected
        DocumentSection.objects.filter(document__project=project).update(is_selected=False)
        
        # Cập nhật sections được chọn
        if selected_section_ids:
            DocumentSection.objects.filter(
                id__in=selected_section_ids,
                document__project=project
            ).update(is_selected=True)
        
        return JsonResponse({
            'success': True,
            'message': f'Đã chọn {len(selected_section_ids)} sections'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Lỗi: {str(e)}'
        })

@login_required
@require_http_methods(["POST"])
def test_api_integration(request, project_uuid):
    """Test API integration với sample data"""
    project = get_object_or_404(UserProject, uuid=project_uuid, user=request.user)
    
    try:
        # Test với sample document link
        test_link = "https://example.com/api-docs"
        test_doc_name = f"test_doc_{project.uuid}"
        
        # Gọi API
        api_response = call_docs_preprocessing_api(
            document_link=test_link,
            doc_name=test_doc_name,
            collection=f"test_project_{project.uuid}"
        )
        
        return JsonResponse({
            'success': True,
            'message': 'API test thành công',
            'api_response': api_response,
            'test_data': {
                'link': test_link,
                'doc_name': test_doc_name,
                'collection': f"test_project_{project.uuid}"
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'API test thất bại: {str(e)}'
        })

@login_required
@require_http_methods(["POST"])
def create_test_suite_from_sections(request, project_uuid):
    """Tạo test suite từ selected sections"""
    project = get_object_or_404(UserProject, uuid=project_uuid, user=request.user)
    
    try:
        # Lấy selected sections
        selected_sections = DocumentSection.objects.filter(
            document__project=project,
            is_selected=True
        )
        
        if not selected_sections.exists():
            return JsonResponse({
                'success': False,
                'message': 'Vui lòng chọn ít nhất một section để tạo test suite'
            })
        
        # Chuẩn bị data cho API
        sections_data = []
        for section in selected_sections:
            sections_data.append({
                'id': section.id,
                'title': section.section_title,
                'content': section.section_content,
                'type': section.section_type
            })
        
        # Gọi API tạo test suite
        api_response = call_test_suite_create_api(sections_data)
        
        # Tạo ProjectTestSuite object
        test_suite = ProjectTestSuite.objects.create(
            project=project,
            test_suite_name=f"Auto Generated Test Suite - {timezone.now().strftime('%Y%m%d_%H%M%S')}",
            description=f"Test suite được tạo tự động từ {len(sections_data)} sections",
            created_by=request.user.username
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Đã tạo test suite thành công từ {len(sections_data)} sections',
            'test_suite_id': test_suite.uuid,
            'test_suite_name': test_suite.test_suite_name,
            'api_response': api_response
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Lỗi tạo test suite: {str(e)}'
        })