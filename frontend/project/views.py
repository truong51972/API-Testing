# Standard library imports
import json
import os
import re
import threading
import time
import uuid

# Third-party imports
import requests
import urllib3
from minio import Minio

# Django imports
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

# Local imports
from main.decorators import set_test_suites_show
from testcase_history.models import TestCaseHistory
from test_suite.models import ProjectTestSuite

from .forms import ProjectDocumentForm
from .models import DocumentSection, ProjectDocument, UserProject

# Disable SSL warnings for development
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Constants
DEBUG = True  # Set to False to disable debug prints
MINIO_ENDPOINT = "minio-api.truong51972.id.vn"
MINIO_ACCESS_KEY = "minioadmin"
MINIO_SECRET_KEY = "minioadmin"
MINIO_BUCKET_NAME = "apit-project"
MINIO_BASE_URL = "https://minio-api.truong51972.id.vn"
# MINIO_BASE_URL = "https://minio-api.truong51972.id.vn"

AGENT_API_BASE_URL = "https://api-t.truong51972.id.vn/"
DOCS_PREPROCESSING_ENDPOINT = f"{AGENT_API_BASE_URL}/agent-service/agent/api/document/docs-preprocessing"
SELECT_FR_ENDPOINT = f"{AGENT_API_BASE_URL}/agent-service/agent/api/document/select-fr-info"
GET_FR_ENDPOINT = f"{AGENT_API_BASE_URL}/agent-service/agent/api/document/get-fr-infos"
ANNOTATE_FR_ENDPOINT = f"{AGENT_API_BASE_URL}/agent-service/agent/api/document/annotate-fr"

PREPROCESSED_DOCUMENTS_ALL_ENDPOINT = f"{AGENT_API_BASE_URL}/agent-service/agent/api/document/all/"
PREPROCESSED_DOCUMENTS_DELETE_ENDPOINT = f"{AGENT_API_BASE_URL}/agent-service/agent/api/document/delete/"

# Project API endpoints
PROJECT_CREATE_ENDPOINT = f"{AGENT_API_BASE_URL}/agent-service/agent/api/project/create"
PROJECT_ALL_ENDPOINT = f"{AGENT_API_BASE_URL}/agent-service/agent/api/project/all"

# API Status Configuration
API_STATUS_CACHE_TIMEOUT = 60  # seconds - Cache for 30 seconds as requested
API_CONNECTION_TIMEOUT = 5     # seconds - Reduced for faster response
API_REQUEST_TIMEOUT = 60       # seconds

# Global variable to cache API status
_api_status_cache = {
    'status': None,
    'last_checked': None,
    'error_message': None
}

def get_minio_client():
    """Create MinIO client"""
    return Minio(
        MINIO_ENDPOINT,
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=True,
    )

def delete_file_from_minio(object_name):
    """Delete file from MinIO"""
    try:
        client = get_minio_client()
        client.remove_object(MINIO_BUCKET_NAME, object_name)
        print(f"Deleted file {object_name} from MinIO")
        return True
    except Exception as e:
        print(f"MinIO delete error: {str(e)}")
        return False

def check_file_exists_in_minio(object_name):
    """Check if file exists in MinIO"""
    try:
        client = get_minio_client()
        client.stat_object(MINIO_BUCKET_NAME, object_name)
        return True
    except Exception as e:
        print(f"MinIO stat error (file may not exist): {str(e)}")
        return False

def call_file_upload_api(file_obj, user=None, project=None):
    """Upload file lên MinIO server"""
    try:
        client = get_minio_client()

        # Create object name in structure: username/projectname/filename
        if user and project:
            username = user.username.replace(' ', '_')
            project_name = project.project_name.replace(' ', '_')
            file_name = file_obj.name.replace(' ', '_')
            object_name = f"{username}/{project_name}/{file_name}"
        else:
            # Fallback if no user/project info
            file_name = file_obj.name
            file_extension = file_name.split('.')[-1] if '.' in file_name else ''
            base_name = file_name.rsplit('.', 1)[0] if '.' in file_name else file_name
            base_name = base_name.replace(' ', '_')
            timestamp = str(int(time.time()))
            object_name = f"{base_name}_{timestamp}.{file_extension}" if file_extension else f"{base_name}_{timestamp}"

        # Check and create bucket if not exists
        found = client.bucket_exists(MINIO_BUCKET_NAME)
        if not found:
            client.make_bucket(MINIO_BUCKET_NAME)
            print(f"Created bucket: {MINIO_BUCKET_NAME}")
        else:
            print(f"Bucket {MINIO_BUCKET_NAME} already exists.")

        # Set bucket policy for public read
        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"AWS": ["*"]},
                    "Action": ["s3:GetObject"],
                    "Resource": [f"arn:aws:s3:::{MINIO_BUCKET_NAME}/*"],
                }
            ],
        }
        client.set_bucket_policy(MINIO_BUCKET_NAME, json.dumps(policy))

        # Upload file lên MinIO
        # Đọc file content
        file_content = file_obj.read()
        file_size = len(file_content) if isinstance(file_content, bytes) else len(file_content.encode('utf-8'))

        # Reset file pointer
        file_obj.seek(0)

        # Xác định content type
        import mimetypes
        content_type, _ = mimetypes.guess_type(file_obj.name)
        if not content_type:
            content_type = 'application/octet-stream'

        # Upload
        client.put_object(
            MINIO_BUCKET_NAME,
            object_name,
            file_obj,
            file_size,
            content_type=content_type
        )

        print(f"Uploaded {file_obj.name} to {MINIO_BUCKET_NAME}/{object_name}")

        return {
            'success': True,
            'file_id': object_name,  # Sử dụng object_name làm file_id
            'file_name': file_obj.name
        }

    except Exception as e:
        print(f"MinIO upload error: {str(e)}")
        raise Exception(f"Upload error: {str(e)}")


def download_and_upload_from_url(url, user, project):
    """Download file từ URL và upload lên MinIO.
    Hỗ trợ chuẩn hoá các dạng link (bao gồm Google Drive share links).
    """
    try:
        # Sanitize raw input (loại bỏ khoảng trắng, ký tự '@' do copy/paste)
        if url:
            url = url.strip()
            if url.startswith('@'):
                url = url[1:].strip()

        # Chuẩn hoá Google Drive links thành direct download
        try:
            from urllib.parse import urlparse, parse_qs, urlencode
            parsed = urlparse(url)
            if 'drive.google.com' in parsed.netloc:
                # Các pattern phổ biến:
                # - https://drive.google.com/file/d/<id>/view
                # - https://drive.google.com/open?id=<id>
                # - https://drive.google.com/uc?id=<id>&export=download
                file_id = None

                # /file/d/<id>/...
                m = re.search(r"/file/d/([^/]+)", parsed.path)
                if m:
                    file_id = m.group(1)
                else:
                    # open?id=... hoặc uc?id=...
                    qs = parse_qs(parsed.query)
                    if 'id' in qs and qs['id']:
                        file_id = qs['id'][0]

                if file_id:
                    # Dùng endpoint direct download ổn định hơn cho lấy bytes
                    url = f"https://drive.google.com/uc?export=download&id={file_id}"
        except Exception:
            pass

        # Download file từ URL
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36',
            'Accept': '*/*',
        }
        response = requests.get(url, timeout=60, verify=False, headers=headers, allow_redirects=True)
        response.raise_for_status()

        # Lấy filename từ URL hoặc header
        content_disposition = response.headers.get('content-disposition')
        filename = None

        if content_disposition:
            # Parse filename từ header - thử nhiều pattern khác nhau
            patterns = [
                r'filename\*=UTF-8\'\'([^;]+)',  # filename*=UTF-8''encoded_filename
                r'filename\*=([^;]+)',  # filename*=charset''encoded_filename
                r'filename[^;=\n]*=(([\'"]).*?\2|[^;\n]*)',  # filename="file.pdf" or filename=file.pdf
            ]

            for pattern in patterns:
                match = re.search(pattern, content_disposition, re.IGNORECASE)
                if match:
                    filename = match.group(1).strip('\'"')
                    # Decode URL encoding if present
                    if '%20' in filename or '%2F' in filename:
                        from urllib.parse import unquote
                        filename = unquote(filename)
                    break

        # Nếu không có filename từ header, thử lấy từ URL
        if not filename:
            url_path = url.split('?')[0]  # Remove query parameters
            url_filename = os.path.basename(url_path)
            if url_filename and '.' in url_filename:  # Chỉ lấy nếu có extension
                filename = url_filename
            else:
                # Thử lấy từ Content-Type header
                content_type = response.headers.get('content-type', '').lower()
                if 'pdf' in content_type:
                    filename = 'document.pdf'
                elif 'word' in content_type or 'docx' in content_type:
                    filename = 'document.docx'
                elif 'msword' in content_type or 'vnd.openxmlformats-officedocument.wordprocessingml.document' in content_type:
                    filename = 'document.docx'
                else:
                    filename = 'downloaded_file'

        # Validate file extension
        allowed_extensions = ['.pdf', '.docx']
        file_extension = os.path.splitext(filename)[1].lower()
        if file_extension not in allowed_extensions:
            # Thử thêm .pdf nếu không có extension
            if not file_extension:
                filename += '.pdf'
            else:
                raise Exception(f"Unsupported file type: {file_extension}")

        # Tạo ContentFile từ response content
        file_content = ContentFile(response.content, name=filename)

        # Upload lên MinIO
        upload_result = call_file_upload_api(file_content, user, project)

        return {
            'success': True,
            'file_id': upload_result.get('file_id'),
            'original_filename': filename
        }

    except Exception as e:
        return {
            'success': False,
            'error': f"Download failed: {str(e)}"
        }


def check_api_server_status():
    """
    Check if the API server is running and responsive.
    Returns cached result if within timeout period.
    Enhanced with better error messages and logging.
    """
    import time

    current_time = time.time()

    # Return cached result if still valid
    if (_api_status_cache['status'] is not None and
        _api_status_cache['last_checked'] is not None and
        current_time - _api_status_cache['last_checked'] < API_STATUS_CACHE_TIMEOUT):
        return _api_status_cache['status'], _api_status_cache['error_message']

    try:
        # Try to connect to the API server with a simple health check
        # Use the health check endpoint for proper status checking
        test_url = f"{AGENT_API_BASE_URL}/agent-service/agent/api/common/health"
        headers = {'accept': 'application/json'}

        if DEBUG:
            print(f"=== API STATUS CHECK DEBUG ===")
            print(f"Checking API server at: {test_url}")
            print(f"Timeout: {API_CONNECTION_TIMEOUT}s")
            print(f"==============================")

        response = requests.get(
            test_url,
            headers=headers,
            timeout=API_CONNECTION_TIMEOUT,
            verify=False
        )

        if DEBUG:
            print(f"=== API STATUS RESPONSE ===")
            print(f"Status Code: {response.status_code}")
            print(f"Response Headers: {dict(response.headers)}")
            if response.text:
                print(f"Response Text: {response.text}")
            print(f"===========================")

        if response.status_code == 200:
            try:
                response_data = response.json()
                if response_data.get('status') == 'ok':
                    _api_status_cache['status'] = True
                    _api_status_cache['last_checked'] = current_time
                    _api_status_cache['error_message'] = None
                    if DEBUG:
                        print("API server is ONLINE")
                    return True, None
                else:
                    error_msg = f"API server health check trả về status không hợp lệ: {response_data.get('status')}"
            except json.JSONDecodeError:
                error_msg = "API server health check không trả về JSON hợp lệ"
        else:
            error_msg = f"API server health check trả về mã lỗi {response.status_code}"
            if response.status_code == 404:
                error_msg += " - Endpoint không tồn tại"
            elif response.status_code >= 500:
                error_msg += " - Lỗi server nội bộ"
            elif response.status_code >= 400:
                error_msg += " - Lỗi yêu cầu từ client"

        _api_status_cache['status'] = False
        _api_status_cache['last_checked'] = current_time
        _api_status_cache['error_message'] = error_msg
        if DEBUG:
            print(f"API server returned error: {error_msg}")
        return False, error_msg

    except requests.exceptions.ConnectionError as e:
        error_msg = "Không thể kết nối đến API server - server có thể chưa được khởi chạy hoặc địa chỉ không đúng"
        if DEBUG:
            print(f"=== CONNECTION ERROR ===")
            print(f"Error: {str(e)}")
            print(f"API Base URL: {AGENT_API_BASE_URL}")
            print(f"=========================")
        _api_status_cache['status'] = False
        _api_status_cache['last_checked'] = current_time
        _api_status_cache['error_message'] = error_msg
        return False, error_msg

    except requests.exceptions.Timeout as e:
        error_msg = "API server không phản hồi - server có thể quá tải hoặc chưa khởi chạy"
        if DEBUG:
            print(f"=== TIMEOUT ERROR ===")
            print(f"Error: {str(e)}")
            print(f"Timeout after: {API_CONNECTION_TIMEOUT}s")
            print(f"=====================")
        _api_status_cache['status'] = False
        _api_status_cache['last_checked'] = current_time
        _api_status_cache['error_message'] = error_msg
        return False, error_msg

    except Exception as e:
        error_msg = f"Lỗi không xác định khi kiểm tra API server: {str(e)}"
        if DEBUG:
            print(f"=== UNEXPECTED ERROR ===")
            print(f"Error: {str(e)}")
            print(f"Error type: {type(e)}")
            print(f"=========================")
        _api_status_cache['status'] = False
        _api_status_cache['last_checked'] = current_time
        _api_status_cache['error_message'] = error_msg
        return False, error_msg


def call_api_with_retry(url, method='GET', headers=None, json_data=None, max_retries=2, retry_delay=1):
    """
    Call API with retry mechanism and proper error handling.
    Returns (success, response_data, error_message)
    """
    import time

    last_exception = None

    for attempt in range(max_retries + 1):
        try:
            if DEBUG and attempt > 0:
                print(f"API call attempt {attempt + 1}/{max_retries + 1} for {url}")

            if method.upper() == 'GET':
                response = requests.get(url, headers=headers, timeout=API_REQUEST_TIMEOUT, verify=False)
            elif method.upper() == 'POST':
                response = requests.post(url, headers=headers, json=json_data, timeout=API_REQUEST_TIMEOUT, verify=False)
            else:
                return False, None, f"Unsupported HTTP method: {method}"

            if response.status_code == 200:
                return True, response.json(), None
            else:
                return False, None, f"API call failed with status {response.status_code}: {response.text}"

        except requests.exceptions.ConnectionError as e:
            last_exception = e
            if attempt < max_retries:
                if DEBUG:
                    print(f"Connection error on attempt {attempt + 1}, retrying in {retry_delay}s...")
                time.sleep(retry_delay)
                continue
            return False, None, "Không thể kết nối đến API server - server có thể chưa được khởi chạy"

        except requests.exceptions.Timeout as e:
            last_exception = e
            if attempt < max_retries:
                if DEBUG:
                    print(f"Timeout error on attempt {attempt + 1}, retrying in {retry_delay}s...")
                time.sleep(retry_delay)
                continue
            return False, None, "API server không phản hồi - server có thể quá tải hoặc chưa khởi chạy"

        except Exception as e:
            return False, None, f"Lỗi không xác định: {str(e)}"

    # If we get here, all retries failed
    return False, None, f"API call failed after {max_retries + 1} attempts: {str(last_exception)}"


def call_docs_preprocessing(doc_url, project_id):
    """Gọi API docs preprocessing với format mới và error handling cải tiến"""
    # Check API server status first
    api_status, error_message = check_api_server_status()
    if not api_status:
        user_friendly_error = "Không thể xử lý tài liệu vì API server hiện không khả dụng. Vui lòng kiểm tra trạng thái server và thử lại sau."
        if DEBUG:
            user_friendly_error += f" (Chi tiết: {error_message})"
        raise Exception(user_friendly_error)

    try:
        payload = {
            "doc_url": doc_url,
            "project_id": str(project_id)
        }

        # Gửi POST request với link document
        headers = {
            'Content-Type': 'application/json',
            'accept': 'application/json'
        }

        # Use retry mechanism for API calls
        success, response_data, error_msg = call_api_with_retry(
            url=DOCS_PREPROCESSING_ENDPOINT,
            method='POST',
            headers=headers,
            json_data=payload,
            max_retries=2,
            retry_delay=2
        )

        if success:
            return response_data
        else:
            raise Exception(error_msg)

    except Exception as e:
        if DEBUG:
            print(f"=== DOCS PREPROCESSING ERROR ===")
            print(f"Error: {str(e)}")
            print(f"Doc URL: {doc_url}")
            print(f"Project ID: {project_id}")
            print(f"===============================")
        raise Exception(f"Lỗi xử lý document: {str(e)}")


def call_docs_preprocessing_file(file, project_id):
    """Gọi API docs preprocessing với file upload"""
    try:
        payload = {
            "file": str(file),  # file_id từ upload API
            "project_id": str(project_id)
        }

        # Gửi POST request với file
        headers = {
            'Content-Type': 'application/json',
            'accept': 'application/json'
        }

        if DEBUG:
            print(f"=== API REQUEST DEBUG ===")
            print(f"Endpoint: {DOCS_PREPROCESSING_ENDPOINT}")
            print(f"Payload: {payload}")
            print(f"Headers: {headers}")
            print(f"=========================")

        response = requests.post(
            DOCS_PREPROCESSING_ENDPOINT,
            json=payload,
            headers=headers,
            timeout=300,
            verify=False
        )

        if DEBUG:
            print(f"=== API RESPONSE DEBUG ===")
            print(f"Status Code: {response.status_code}")
            print(f"Response Headers: {dict(response.headers)}")
            print(f"Response Text: {response.text}")

            try:
                response_json = response.json()
                print(f"Response JSON: {response_json}")
            except Exception as json_error:
                print(f"JSON Parse Error: {json_error}")
                print(f"Raw Response: {response.text}")

            print(f"=========================")

        if response.status_code == 200:
            return response.json()
        elif response.status_code == 422:
            # Validation error
            error_detail = response.json().get('detail', [])
            raise Exception(f"Validation error: {error_detail}")
        else:
            raise Exception(f"API call failed with status {response.status_code}: {response.text}")

    except requests.exceptions.Timeout:
        if DEBUG:
            print(f"=== TIMEOUT ERROR ===")
            print(f"Request timed out after 300 seconds")
            print(f"=====================")
        raise Exception("API request timeout - document processing may take longer than expected")
    except requests.exceptions.RequestException as e:
        if DEBUG:
            print(f"=== REQUEST ERROR ===")
            print(f"Request Exception: {str(e)}")
            print(f"====================")
        raise Exception(f"API request failed: {str(e)}")
    except Exception as e:
        if DEBUG:
            print(f"=== UNEXPECTED ERROR ===")
            print(f"Error: {str(e)}")
            print(f"========================")
        raise Exception(f"Unexpected error: {str(e)}")

@login_required
def my_view(request):
    usernames = User.objects.values_list('username', flat=True)
    return render(request, 'home.html', {'usernames': usernames})


@login_required
def api_status_view(request):
    """View to check and display API server status"""
    api_status, error_message = check_api_server_status()

    context = {
        'api_status': api_status,
        'error_message': error_message,
        'last_checked': _api_status_cache['last_checked'],
        'cache_timeout': API_STATUS_CACHE_TIMEOUT
    }

    return render(request, 'project/api_status.html', context)


@require_http_methods(["GET"])
def api_health_check(request):
    """Simple API endpoint to check if the Django server is running"""
    return JsonResponse({
        'status': 'ok'
    })


@require_http_methods(["GET"])
def api_server_status(request):
    """API endpoint to check external API server status"""
    api_status, error_message = check_api_server_status()

    status_code = 200 if api_status else 503  # 503 Service Unavailable if API server is down

    return JsonResponse({
        'api_server_status': 'online' if api_status else 'offline',
        'status': api_status,
        'error_message': error_message,
        'last_checked': _api_status_cache['last_checked'],
        'cache_timeout': API_STATUS_CACHE_TIMEOUT,
        'timestamp': timezone.now().isoformat()
    }, status=status_code)


@login_required
def project_list(request):
    # This view will render the list of projects from external API with improved error handling
    try:
        # Check API server status first
        api_status, error_message = check_api_server_status()
        if not api_status:
            user_friendly_message = "Không thể kết nối đến API server để tải danh sách dự án. Vui lòng kiểm tra trạng thái server hoặc liên hệ administrator."
            messages.error(request, user_friendly_message)

            if DEBUG:
                messages.info(request, f"Chi tiết lỗi: {error_message}")

            context = {
                'projects': [],
                'api_count': 0,
                'api_server_offline': True,
                'error_message': error_message,
                'user_message': user_friendly_message
            }
            return render(request, 'project/project_list.html', context)

        headers = {
            'accept': 'application/json'
        }

        # Update endpoint to include user_id
        user_projects_endpoint = f"{PROJECT_ALL_ENDPOINT}/{request.user.id}"

        if DEBUG:
            print(f"Fetching projects for user ID: {request.user.id} from {user_projects_endpoint}")

        # Use retry mechanism for API calls
        success, api_projects, error_msg = call_api_with_retry(
            url=user_projects_endpoint,
            method='GET',
            headers=headers,
            max_retries=2,
            retry_delay=1
        )

        if not success:
            messages.error(request, f"Không thể tải danh sách dự án: {error_msg}")
            context = {
                'projects': [],
                'api_count': 0,
                'api_error': True,
                'error_message': error_msg
            }
            return render(request, 'project/project_list.html', context)

        if DEBUG:
            print(f"API Projects Response: {api_projects}")

        # Sync API projects to local database for sidebar
        for project_data in api_projects:
            project_id = project_data.get('project_id')
            project_name = project_data.get('project_name', '')
            description = project_data.get('description', '')

            if DEBUG:
                print(f"Processing project: {project_name}")
                print(f"Raw project_id from API: {project_id} (type: {type(project_id)})")

            if project_id and project_name:
                # Ensure project_id is a string
                if isinstance(project_id, str):
                    # Validate UUID format
                    import uuid
                    try:
                        uuid.UUID(project_id)  # This will raise ValueError if invalid
                        if DEBUG:
                            print(f"Valid UUID string: {project_id}")
                    except ValueError:
                        if DEBUG:
                            print(f"Invalid UUID format: {project_id}")
                        continue
                else:
                    if DEBUG:
                        print(f"Project_id is not a string: {project_id}")
                    continue

                # First try to find existing project by user and project_name
                existing_project = UserProject.objects.filter(
                    user=request.user,
                    project_name=project_name
                ).first()

                if existing_project:
                    # Update existing project
                    if DEBUG:
                        print(f"Updating existing project {project_name} with UUID: {project_id}")
                    existing_project.uuid = project_id  # Update UUID if different
                    existing_project.description = description
                    existing_project.save()
                    if DEBUG:
                        print(f"After save, project.uuid: {existing_project.uuid}")
                else:
                    # Create new project only if name doesn't exist
                    try:
                        if DEBUG:
                            print(f"Creating new project {project_name} with UUID: {project_id}")
                        new_project = UserProject.objects.create(
                            uuid=project_id,
                            user=request.user,
                            project_name=project_name,
                            description=description
                        )
                        if DEBUG:
                            print(f"After create, project.uuid: {new_project.uuid}")
                    except Exception as e:
                        # Log the error but continue processing other projects
                        if DEBUG:
                            print(f"Error creating project {project_name}: {str(e)}")
                        continue

        context = {
            'projects': api_projects,
            'api_count': len(api_projects),
            'api_server_online': True
        }
        return render(request, 'project/project_list.html', context)

    except Exception as e:
        if DEBUG:
            print(f"=== PROJECT LIST ERROR ===")
            print(f"Error: {str(e)}")
            print(f"==========================")
        messages.error(request, f"Lỗi hệ thống: {str(e)}")
        context = {
            'projects': [],
            'api_count': 0,
            'api_error': True,
            'error_message': str(e)
        }
        return render(request, 'project/project_list.html', context)

@login_required
def project_add(request):
    # This view will handle adding a new project via API
    if request.method == 'POST':
        # Handle form submission for adding a project
        project_name = request.POST.get('project_name')
        description = request.POST.get('description', '')

        if not project_name:
            messages.error(request, "Project name is required.")
            return render(request, 'project/project_add.html')

        # Check if project name already exists for this user
        if UserProject.objects.filter(user=request.user, project_name=project_name).exists():
            messages.error(request, f"Dự án với tên '{project_name}' đã tồn tại.")
            return render(request, 'project/project_add.html')

        # Use external API to create project
        try:
            import requests
            payload = {
                'project_name': project_name,
                'description': description,
                'user_id': str(request.user.id)  # Add user_id from logged-in user
            }

            headers = {
                'Content-Type': 'application/json',
                'accept': 'application/json'
            }

            response = requests.post(
                PROJECT_CREATE_ENDPOINT,
                json=payload,
                headers=headers,
                timeout=30,
                verify=False
            )

            if response.status_code == 200:
                result = response.json()
                # Also save to local database for sidebar and detail views
                local_project = UserProject.objects.create(
                    user=request.user,
                    project_name=project_name,
                    description=description
                )
                messages.success(request, f"Dự án đã được tạo thành công. ID dự án: {local_project.uuid}")
                return redirect('project_list')
            else:
                messages.error(request, f"Không thể tạo dự án qua API: {response.text}")
                return render(request, 'project/project_add.html')

        except Exception as e:
            messages.error(request, f"API Error: {str(e)}")
            return render(request, 'project/project_add.html')
    else:
        # Render the project add form
        return render(request, 'project/project_add.html')


@set_test_suites_show(True)
@login_required
def project_edit(request, project_uuid):
    # This view will handle editing an existing project
    project = get_object_or_404(UserProject, uuid=project_uuid, user=request.user)
    if project.user != request.user:
        messages.error(request, "Bạn không có quyền chỉnh sửa dự án này.")
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
        messages.success(request, "Dự án đã được cập nhật thành công.")
        return redirect(reverse('project_detail_by_uuid', kwargs={'project_uuid': project.uuid}))
    
    return render(request, 'project/project_edit.html', context)

@set_test_suites_show(True)
@login_required
def project_delete(request, project_uuid):
    # This view will handle deleting a project via API
    try:
        delete_url = f"{AGENT_API_BASE_URL}/api/project/delete/{project_uuid}"

        headers = {
            'accept': 'application/json'
        }

        response = requests.post(
            delete_url,
            headers=headers,
            timeout=30,
            verify=False
        )

        if response.status_code == 200:
            # Delete from local database as well
            try:
                project = UserProject.objects.filter(uuid=project_uuid, user=request.user).first()
                if project:
                    project.delete()
                    messages.success(request, f"Dự án {project_uuid} đã được xóa thành công.")
                else:
                    messages.warning(request, f"Dự án {project_uuid} đã được xóa từ API nhưng không tìm thấy trong cơ sở dữ liệu cục bộ.")
            except Exception as db_error:
                messages.warning(request, f"Dự án {project_uuid} đã được xóa từ API nhưng không thể xóa khỏi cơ sở dữ liệu cục bộ: {str(db_error)}")
            return redirect('project_list')
        else:
            messages.error(request, f"Không thể xóa dự án qua API: {response.text}")
            return redirect('project_list')

    except Exception as e:
        messages.error(request, f"API Error: {str(e)}")
        return redirect('project_list')

@set_test_suites_show(True)
@login_required
def project_detail_by_uuid(request, project_uuid):
    project = get_object_or_404(UserProject, uuid=project_uuid)
    if project.user != request.user:
        messages.error(request, "Bạn không có quyền xem dự án này.")
        return redirect('project_list')

    test_suites = ProjectTestSuite.objects.filter(project=project)

    # Lấy list tài liệu đã upload
    documents = project.documents.all() if hasattr(project, "documents") else []

    # Khởi tạo context trước
    context = {
        'project': project,
        'test_suites': [{
            'uuid': test_suite.uuid,
            'test_suite_name': test_suite.test_suite_name,
            'description': test_suite.description,
            'created_at': test_suite.created_at,
            'test_cases_count': TestCaseHistory.objects.filter(test_suite=test_suite).count()
        } for test_suite in test_suites],
        'documents': documents,
    }

    # Xử lý form upload
    if request.method == "POST":
        # Xử lý multiple files
        uploaded_files = request.FILES.getlist('file')
        link = request.POST.get('link')

        if uploaded_files:
            # Upload multiple files
            success_count = 0
            error_messages = []

            for file_obj in uploaded_files:
                try:
                    # Tạo ProjectDocument cho mỗi file
                    doc = ProjectDocument(project=project, ai_processing_status='pending')

                    # Lưu tên file gốc trước khi upload
                    original_filename = file_obj.name
                    upload_result = call_file_upload_api(file_obj, request.user, project)
                    if upload_result['success']:
                        doc.file_id = upload_result['file_id']
                        doc.original_filename = original_filename
                        doc.save()
                        success_count += 1
                    else:
                        error_messages.append(f"Lỗi upload {file_obj.name}: {upload_result.get('error', 'Unknown error')}")
                except Exception as e:
                    error_messages.append(f"Lỗi upload {file_obj.name}: {str(e)}")

            if success_count > 0:
                    messages.success(request, f"Đã tải lên thành công {success_count} file(s).")
            if error_messages:
                for error_msg in error_messages:
                    messages.error(request, error_msg)

            if success_count > 0:
                messages.success(request, "Tài liệu đã được thêm thành công. Bạn có thể bắt đầu xử lý AI.")
                return redirect(reverse('project_detail_by_uuid', kwargs={'project_uuid': project.uuid}))
            else:
                # Nếu không có file nào upload thành công, hiển thị form lại
                form = ProjectDocumentForm()
                context['form'] = form
                return render(request, 'project/project_view.html', context)

        elif link:
            # Xử lý link URL (giữ nguyên logic cũ)
            form = ProjectDocumentForm(request.POST, request.FILES)
            if form.is_valid():
                doc = form.save(commit=False)
                doc.project = project
                doc.ai_processing_status = 'pending'

                try:
                    download_result = download_and_upload_from_url(doc.link, request.user, project)
                    if download_result['success']:
                        doc.file_id = download_result['file_id']
                        doc.original_filename = download_result['original_filename']
                        doc.link = None  # Xóa link sau khi download thành công
                        doc.save()
                        messages.success(request, f"Đã tải xuống và tải lên file từ URL lên server thành công.")
                        messages.success(request, "Tài liệu đã được thêm thành công. Bạn có thể bắt đầu xử lý AI.")
                        return redirect(reverse('project_detail_by_uuid', kwargs={'project_uuid': project.uuid}))
                    else:
                        messages.error(request, f"Lỗi tải xuống file: {download_result.get('error')}")
                        context['form'] = form
                        return render(request, 'project/project_view.html', context)
                except Exception as e:
                    messages.error(request, f"Lỗi tải xuống file: {str(e)}")
                    context['form'] = form
                    return render(request, 'project/project_view.html', context)
            else:
                messages.error(request, "Có lỗi khi nhập URL.")
                context['form'] = form
        else:
            messages.error(request, "Vui lòng chọn file hoặc nhập URL.")
            form = ProjectDocumentForm()
            context['form'] = form
    else:
        form = ProjectDocumentForm()
        context['form'] = form
    # return render(request, 'project/chat_project.html', context)
    return render(request, 'project/project_view.html', context)

@set_test_suites_show(True)
@login_required
def delete_document(request, doc_id):
    doc = get_object_or_404(ProjectDocument, id=doc_id, project__user=request.user)
    project = doc.project
    project_uuid = project.uuid

    # Xóa file từ MinIO nếu có file_id
    if doc.file_id:
        delete_success = delete_file_from_minio(doc.file_id)
        if delete_success:
            print(f"Đã xóa file {doc.file_id} từ MinIO")
        else:
            print(f"Không thể xóa file {doc.file_id} từ MinIO")

    # Xóa preprocessed document từ server nếu có doc_id
    if doc.doc_id:
        try:
            delete_url = f"{PREPROCESSED_DOCUMENTS_DELETE_ENDPOINT}{doc.doc_id}"
            headers = {
                'accept': 'application/json'
            }
            response = requests.post(
                delete_url,
                headers=headers,
                timeout=30,
                verify=False
            )
            if response.status_code == 200:
                print(f"Đã xóa preprocessed document {doc.doc_id} từ server")
            else:
                print(f"Không thể xóa preprocessed document {doc.doc_id} từ server: {response.text}")
        except Exception as e:
            print(f"Lỗi khi xóa preprocessed document từ server: {str(e)}")

    # Xóa document từ database
    doc.delete()
    messages.success(request, "Tài liệu đã được xóa.")
    return redirect(reverse('project_detail_by_uuid', kwargs={'project_uuid': project_uuid}))

@login_required
@require_http_methods(["POST"])
def delete_preprocessed_document(request, project_uuid, doc_id):
    """Delete preprocessed document via API"""
    project = get_object_or_404(UserProject, uuid=project_uuid, user=request.user)

    try:
        # Call the API to delete preprocessed document
        delete_url = f"{PREPROCESSED_DOCUMENTS_DELETE_ENDPOINT}{doc_id}"

        headers = {
            'accept': 'application/json'
        }

        response = requests.post(
            delete_url,
            headers=headers,
            timeout=30,
            verify=False
        )

        if response.status_code == 200:
            # Also delete from local database if it exists
            try:
                doc = ProjectDocument.objects.filter(
                    project=project,
                    doc_id=doc_id
                ).first()
                if doc:
                    # Delete associated sections
                    doc.sections.all().delete()
                    # Delete the document
                    doc.delete()
                    messages.success(request, f"Tài liệu đã xử lý {doc_id} đã được xóa thành công.")
                else:
                    messages.success(request, f"Tài liệu đã xử lý {doc_id} đã được xóa từ API.")
            except Exception as db_error:
                messages.warning(request, f"Tài liệu {doc_id} đã được xóa từ API nhưng không thể xóa khỏi cơ sở dữ liệu cục bộ: {str(db_error)}")

            return JsonResponse({
                'success': True,
                'message': f'Tài liệu đã xử lý {doc_id} đã được xóa thành công'
            })
        else:
            return JsonResponse({
                'success': False,
                'message': f'Không thể xóa tài liệu đã xử lý: {response.text}'
            })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Lỗi API: {str(e)}'
        })

@set_test_suites_show(True)
@login_required
def dashboard(request):
    current_username = request.user.username
    return render(request, 'main/home.html', {'current_username': current_username})

# AI Processing Views
@login_required
@require_http_methods(["POST"])
def start_ai_processing(request, project_uuid):
    """Bắt đầu xử lý AI cho tất cả documents pending"""
    project = get_object_or_404(UserProject, uuid=project_uuid, user=request.user)

    # Lấy tất cả documents chưa được xử lý
    pending_documents = list(project.documents.filter(ai_processing_status='pending'))

    if not pending_documents:
        return JsonResponse({
            'success': False,
            'message': 'Không có document nào cần xử lý'
        })

    # Check API server status before starting processing
    api_status, error_message = check_api_server_status()
    if not api_status:
        user_friendly_message = "Không thể bắt đầu xử lý AI vì API server hiện không khả dụng. Vui lòng kiểm tra trạng thái server và thử lại."
        if DEBUG:
            user_friendly_message += f" (Chi tiết: {error_message})"

        return JsonResponse({
            'success': False,
            'message': user_friendly_message,
            'api_offline': True,
            'error_message': error_message
        })

    # Cập nhật trạng thái processing cho tất cả documents
    for doc in pending_documents:
        doc.ai_processing_status = 'processing'
        doc.save()

    # Chạy AI processing trong background thread
    def process_all_documents():
        total_docs = len(pending_documents)
        processed_count = 0

        for i, document in enumerate(pending_documents):
            try:
                if DEBUG:
                    print(f"=== AI PROCESSING DEBUG ===")
                    print(f"Processing document {i+1}/{total_docs}: {document.original_filename or document.file_id}")
                    print(f"Document ID: {document.id}")
                    print(f"Document file_id: {document.file_id}")
                    print(f"Document file: {document.file}")
                    print(f"Document link: {document.link}")
                    print(f"Project UUID: {project.uuid}")

                # Prepare doc_url from document
                if document.file_id:
                    doc_url = f"{MINIO_BASE_URL}/{MINIO_BUCKET_NAME}/{document.file_id}"
                    if DEBUG:
                        print(f"Using MinIO URL: {doc_url}")
                elif document.file:
                    doc_url = f"file:{document.file.name}"
                    if DEBUG:
                        print(f"Using file: {doc_url}")
                else:
                    doc_url = document.link if document.link else f"https://example.com/document_{document.id}.pdf"
                    if DEBUG:
                        print(f"Using link: {doc_url}")

                if DEBUG:
                    print(f"Final doc_url: {doc_url}")
                    print(f"===========================")

                api_response = call_docs_preprocessing(
                    doc_url=doc_url,
                    project_id=project.uuid
                )

                # Lưu API response
                document.api_response = api_response
                # Extract doc_id from API response if available
                if api_response and 'doc_id' in api_response:
                    document.doc_id = api_response['doc_id']
                if DEBUG:
                    print(f"API Response saved: {api_response}")
                    print(f"Doc ID extracted: {document.doc_id}")

                # Process response from API
                sections_data = []
                if api_response and 'sections' in api_response:
                    sections_data = api_response['sections']
                    if DEBUG:
                        print(f"Found sections in response: {len(sections_data)} sections")
                elif api_response and 'data' in api_response:
                    # If API returns data instead of sections
                    sections_data = api_response['data']
                    if DEBUG:
                        print(f"Found data in response: {len(sections_data)} items")
                else:
                    # Fallback: create mock data if API doesn't return sections
                    if DEBUG:
                        print("No sections or data found in response, using fallback data")
                    sections_data = [
                        {
                            'title': 'API Endpoint: /api/users',
                            'content': 'GET /api/users - Get list of users\nParameters: page, limit\nResponse: User list',
                            'type': 'api_endpoint'
                        },
                        {
                            'title': 'API Endpoint: /api/users/{id}',
                            'content': 'GET /api/users/{id} - Get user info by ID\nParameters: id (path)\nResponse: User object',
                            'type': 'api_endpoint'
                        }
                    ]

                if DEBUG:
                    print(f"Processing {len(sections_data)} sections...")

                # Create DocumentSection objects from API response
                for j, section_data in enumerate(sections_data):
                    if DEBUG:
                        print(f"Creating section {j+1}: {section_data.get('title', 'Untitled Section')}")
                    DocumentSection.objects.create(
                        document=document,
                        section_title=section_data.get('title', 'Untitled Section'),
                        section_content=section_data.get('content', 'No content available'),
                        section_type=section_data.get('type', 'other')
                    )

                if DEBUG:
                    print(f"Successfully created {len(sections_data)} sections")

                # Update status to completed
                document.ai_processing_status = 'completed'
                document.ai_processed_at = timezone.now()
                document.save()
                processed_count += 1
                if DEBUG:
                    print(f"Document {i+1}/{total_docs} processing completed successfully")

            except Exception as e:
                if DEBUG:
                    print(f"=== AI PROCESSING ERROR ===")
                    print(f"Error processing document {i+1}: {str(e)}")
                    print(f"Error type: {type(e)}")
                    print(f"===========================")
                # Update status to failed
                document.ai_processing_status = 'failed'
                document.ai_error_message = str(e)
                document.save()
                if DEBUG:
                    print(f"Document {i+1} processing failed: {str(e)}")

        if DEBUG:
            print(f"AI processing completed. Processed {processed_count}/{total_docs} documents successfully")

    # Start background thread
    thread = threading.Thread(target=process_all_documents)
    thread.daemon = True
    thread.start()

    return JsonResponse({
        'success': True,
        'message': f'Đã bắt đầu xử lý AI cho {len(pending_documents)} documents',
        'document_count': len(pending_documents)
    })

@login_required
def check_ai_processing_status(request, project_uuid):
    """Kiểm tra trạng thái xử lý AI cho tất cả documents"""
    project = get_object_or_404(UserProject, uuid=project_uuid, user=request.user)

    # Đếm số lượng documents theo trạng thái
    processing_count = project.documents.filter(ai_processing_status='processing').count()
    completed_count = project.documents.filter(ai_processing_status='completed').count()
    failed_count = project.documents.filter(ai_processing_status='failed').count()
    total_pending = project.documents.filter(ai_processing_status__in=['pending', 'processing', 'completed', 'failed']).count()

    if processing_count > 0:
        # Còn documents đang xử lý
        return JsonResponse({
            'status': 'processing',
            'message': f'Đang xử lý AI... ({processing_count} documents đang xử lý)',
            'processing_count': processing_count,
            'completed_count': completed_count,
            'total_count': total_pending
        })
    elif completed_count > 0:
        # Tất cả documents đã hoàn thành (có thể có một số failed)
        success_message = f'Xử lý AI hoàn thành! ({completed_count} documents thành công'
        if failed_count > 0:
            success_message += f', {failed_count} documents thất bại'
        success_message += ')'

        return JsonResponse({
            'status': 'completed',
            'message': success_message,
            'completed_count': completed_count,
            'failed_count': failed_count,
            'total_count': total_pending
        })
    else:
        return JsonResponse({
            'status': 'no_processing',
            'message': 'Không có document nào đang được xử lý'
        })


@login_required
def section_selection_view(request, project_uuid):
    """Hiển thị danh sách sections từ tất cả documents đã xử lý xong"""
    project = get_object_or_404(UserProject, uuid=project_uuid, user=request.user)

    # Lấy tất cả documents đã được xử lý xong
    completed_documents = project.documents.filter(ai_processing_status='completed')

    if not completed_documents.exists():
        messages.error(request, "Chưa có tài liệu nào được xử lý xong.")
        return redirect(reverse('project_detail_by_uuid', kwargs={'project_uuid': project.uuid}))

    # Lấy tất cả sections từ tất cả completed documents
    all_sections = []
    for document in completed_documents:
        sections = document.sections.all()
        for section in sections:
            # Thêm thông tin document để phân biệt
            section.document_name = document.original_filename or document.file_id or f"Document {document.id}"
            all_sections.append(section)

    context = {
        'project': project,
        'documents': completed_documents,
        'sections': all_sections,
        'total_sections': len(all_sections),
        'documents_count': completed_documents.count()
    }

    return render(request, 'project/section_selection.html', context)

@login_required
def get_sections_json(request, project_uuid):
    """API endpoint để lấy sections từ tất cả documents đã xử lý xong"""
    project = get_object_or_404(UserProject, uuid=project_uuid, user=request.user)

    # Lấy tất cả documents đã được xử lý xong
    completed_documents = project.documents.filter(ai_processing_status='completed')

    if not completed_documents.exists():
        return JsonResponse({
            'success': False,
            'message': 'No completed documents found'
        })

    sections_data = []
    for document in completed_documents:
        doc_sections = document.sections.all()
        for section in doc_sections:
            sections_data.append({
                'id': section.id,
                'title': section.section_title,
                'content': section.section_content,
                'type': section.section_type,
                'type_display': section.get_section_type_display(),
                'is_selected': section.is_selected,
                'document_name': document.original_filename or document.file_id or f"Document {document.id}"
            })

    return JsonResponse({
        'success': True,
        'sections': sections_data,
        'total_sections': len(sections_data),
        'documents_count': completed_documents.count()
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
        test_doc_url = "https://example.com/api-docs"
        
        # Gọi API
        api_response = call_docs_preprocessing(
            doc_url=test_doc_url,
            project_id=project.uuid
        )
        
        return JsonResponse({
            'success': True,
            'message': 'API test thành công',
            'api_response': api_response,
            'test_data': {
                'doc_url': test_doc_url,
                'project_id': str(project.uuid)
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
            'test_suite_name': test_suite.test_suite_name
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Lỗi tạo test suite: {str(e)}'
        })

# API Integration Views
@login_required
@require_http_methods(["POST"])
def api_create_project(request):
    """Tạo project mới qua API"""
    try:
        data = json.loads(request.body)
        project_name = data.get('project_name')
        description = data.get('description', '')

        if not project_name:
            return JsonResponse({
                'success': False,
                'message': 'Project name is required'
            })

        # Gọi API tạo project
        payload = {
            'project_name': project_name,
            'description': description,
            'user_id': str(request.user.id)  # Add user_id from logged-in user
        }

        headers = {
            'Content-Type': 'application/json',
            'accept': 'application/json'
        }

        response = requests.post(
            PROJECT_CREATE_ENDPOINT,
            json=payload,
            headers=headers,
            timeout=30,
            verify=False
        )

        if response.status_code == 200:
            result = response.json()
            if DEBUG:
                print(f"API Create Project Response: {result}")
                print(f"Project ID returned by API: {result.get('project_id', 'N/A')}")
            return JsonResponse({
                'success': True,
                'message': 'Project created successfully via API',
                'project_id': result.get('project_id', ''),
                'data': result
            })
        else:
            error_msg = f"API call failed with status {response.status_code}: {response.text}"
            return JsonResponse({
                'success': False,
                'message': error_msg
            })

    except requests.exceptions.Timeout:
        return JsonResponse({
            'success': False,
            'message': 'API request timeout'
        })
    except requests.exceptions.RequestException as e:
        return JsonResponse({
            'success': False,
            'message': f'API request failed: {str(e)}'
        })
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Invalid JSON data'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Unexpected error: {str(e)}'
        })

@login_required
def api_get_all_projects(request):
    """Lấy tất cả projects qua API"""
    try:
        headers = {
            'accept': 'application/json'
        }

        response = requests.get(
            PROJECT_ALL_ENDPOINT,
            headers=headers,
            timeout=30,
            verify=False
        )

        if response.status_code == 200:
            result = response.json()
            return JsonResponse({
                'success': True,
                'message': 'Projects retrieved successfully via API',
                'projects': result,
                'count': len(result)
            })
        else:
            error_msg = f"API call failed with status {response.status_code}: {response.text}"
            return JsonResponse({
                'success': False,
                'message': error_msg
            })

    except requests.exceptions.Timeout:
        return JsonResponse({
            'success': False,
            'message': 'API request timeout'
        })
    except requests.exceptions.RequestException as e:
        return JsonResponse({
            'success': False,
            'message': f'API request failed: {str(e)}'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Unexpected error: {str(e)}'
        })

@login_required
@require_http_methods(["POST"])
def api_delete_project(request, project_id):
    """Xóa project qua API"""
    try:
        # Gọi API xóa project
        delete_url = f"{AGENT_API_BASE_URL}/api/project/delete/{project_id}"

        headers = {
            'accept': 'application/json'
        }

        response = requests.post(
            delete_url,
            headers=headers,
            timeout=30,
            verify=False
        )

        if response.status_code == 200:
            return JsonResponse({
                'success': True,
                'message': 'Project deleted successfully via API',
                'project_id': project_id
            })
        else:
            error_msg = f"API call failed with status {response.status_code}: {response.text}"
            return JsonResponse({
                'success': False,
                'message': error_msg
            })

    except requests.exceptions.Timeout:
        return JsonResponse({
            'success': False,
            'message': 'API request timeout'
        })
    except requests.exceptions.RequestException as e:
        return JsonResponse({
            'success': False,
            'message': f'API request failed: {str(e)}'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Unexpected error: {str(e)}'
        })


@csrf_exempt
@require_http_methods(["POST"])
def upload_document_file(request):
    """
    API endpoint để upload file và xử lý document preprocessing
    POST /api/workflow/docs-preprocessing/file
    """
    try:
        # Kiểm tra request có file không
        if 'file' not in request.FILES:
            return JsonResponse({
                'detail': [{
                    'loc': ['file'],
                    'msg': 'No file provided',
                    'type': 'value_error'
                }]
            }, status=422)

        # Lấy file và project_id từ request
        file_obj = request.FILES['file']
        project_id = request.POST.get('project_id')

        if not project_id:
            return JsonResponse({
                'detail': [{
                    'loc': ['project_id'],
                    'msg': 'project_id is required',
                    'type': 'value_error'
                }]
            }, status=422)

        # Validate project_id format (UUID)
        try:
            import uuid
            uuid.UUID(project_id)
        except ValueError:
            return JsonResponse({
                'detail': [{
                    'loc': ['project_id'],
                    'msg': 'Invalid project_id format. Must be a valid UUID.',
                    'type': 'value_error'
                }]
            }, status=422)

        if DEBUG:
            print(f"=== FILE UPLOAD DEBUG ===")
            print(f"File name: {file_obj.name}")
            print(f"File size: {file_obj.size}")
            print(f"Project ID: {project_id}")
            print(f"=========================")

        # Gọi API upload file trước
        upload_result = call_file_upload_api(file_obj)

        if not upload_result.get('success'):
            return JsonResponse({
                'detail': [{
                    'loc': ['file'],
                    'msg': f'File upload failed: {upload_result.get("message", "Unknown error")}',
                    'type': 'value_error'
                }]
            }, status=500)

        file_id = upload_result.get('file_id')
        if not file_id:
            return JsonResponse({
                'detail': [{
                    'loc': ['file'],
                    'msg': 'File upload succeeded but no file_id returned',
                    'type': 'value_error'
                }]
            }, status=500)

        # Gọi API docs preprocessing với file_id
        preprocessing_result = call_docs_preprocessing_file(file_id, project_id)

        if preprocessing_result:
            # Trả về đúng format theo yêu cầu API
            doc_id = preprocessing_result.get('doc_id', file_id)
            return JsonResponse({
                'doc_id': doc_id
            })
        else:
            return JsonResponse({
                'detail': [{
                    'loc': ['file'],
                    'msg': 'Document preprocessing failed',
                    'type': 'value_error'
                }]
            }, status=500)
    
    except Exception as e:
        if DEBUG:
            print(f"=== UPLOAD ERROR ===")
            print(f"Error: {str(e)}")
            print(f"===================")
        return JsonResponse({
            'detail': [{
                'loc': ['file'],
                'msg': f'Unexpected error: {str(e)}',
                'type': 'value_error'
            }]
        }, status=500)

@login_required
def annotate_fr_view(request, project_uuid):
        """Display Functional Requirements from annotate-fr API"""
        project = get_object_or_404(UserProject, uuid=project_uuid, user=request.user)
    
        try:
            # Call the annotate-fr API
            payload = {
                "project_id": str(project.uuid),
                "lang": "vi"
            }
    
            headers = {
                'Content-Type': 'application/json',
                'accept': 'application/json'
            }
    
            response = requests.post(
                GET_FR_ENDPOINT,
                json=payload,
                headers=headers,
                timeout=60,
                verify=False
            )
    
            if response.status_code == 200:
                api_data = response.json()
                fr_annotations = api_data.get('fr_annotations', {})
    
                # Convert to list format for template
                fr_list = []
                for fr_key, fr_data in fr_annotations.items():
                    fr_list.append({
                        'fr_id': fr_key,
                        'name': fr_key.split(': ', 1)[1] if ': ' in fr_key else fr_key,
                        'full_name': fr_key,
                        'documents': fr_data
                    })
    
                context = {
                    'project': project,
                    'fr_annotations': fr_list,
                    'api_success': True
                }
            else:
                context = {
                    'project': project,
                    'fr_annotations': [],
                    'api_success': False,
                    'error_message': f"API call failed: {response.status_code} - {response.text}"
                }
    
        except Exception as e:
            context = {
                'project': project,
                'fr_annotations': [],
                'api_success': False,
                'error_message': f"Error calling API: {str(e)}"
            }
    

@login_required
@require_http_methods(["POST"])
def get_fr_infors(request, project_uuid):
    """Call the get-fr-infos API to get FR annotations - let server handle caching"""
    from .models import FunctionalRequirement

    project = get_object_or_404(UserProject, uuid=project_uuid, user=request.user)

    try:
        # Get parameters from request
        data = json.loads(request.body) if request.body else {}
        lang = data.get('lang', 'vi')
        analyze = data.get('analyze', False)  # Default to False for cached mode

        # Check if we have cached data in DB when analyze=False
        if not analyze:
            existing_frs = FunctionalRequirement.objects.filter(project=project)
            if existing_frs.exists():
                if DEBUG:
                    print(f"Using cached FR data from DB: {existing_frs.count()} FRs")

                # Return cached data from DB
                fr_list = []
                for fr_obj in existing_frs:
                    fr_list.append({
                        'fr_info_id': str(fr_obj.fr_info_id),
                        'fr_group': fr_obj.fr_group,
                        'name': fr_obj.fr_group.split(':', 1)[1].strip() if ':' in fr_obj.fr_group else fr_obj.fr_group,
                        'full_name': fr_obj.fr_group,
                        'description': fr_obj.description,
                        'is_selected': fr_obj.is_selected,
                        'documents': []  # Document locations not stored in DB, could be enhanced later
                    })

                return JsonResponse({
                    'success': True,
                    'fr_annotations': fr_list,
                    'count': len(fr_list),
                    'cached': True
                })

        # Call the API when analyze=True or no cached data exists
        payload = {
            "project_id": str(project.uuid),
            "lang": lang
        }

        headers = {
            'Content-Type': 'application/json',
            'accept': 'application/json'
        }

        # Use the get-fr-infos endpoint with analyze parameter
        url = f"{GET_FR_ENDPOINT}?analyze={str(analyze).lower()}"

        if DEBUG:
            print(f"=== ANNOTATE FR API DEBUG ===")
            print(f"Endpoint: {url}")
            print(f"Payload: {payload}")
            print(f"Analyze: {analyze}")
            print(f"=============================")

        response = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=60,
            verify=False
        )

        if DEBUG:
            print(f"=== ANNOTATE FR RESPONSE ===")
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.text}")
            print(f"============================")

        if response.status_code == 200:
            api_data = response.json()

            # Handle different response formats
            if isinstance(api_data, list):
                # Direct array response (like get-fr-infos)
                fr_annotations = api_data
            elif isinstance(api_data, dict) and 'fr_annotations' in api_data:
                # annotate-fr format: object with fr_annotations key containing FR objects
                fr_annotations_obj = api_data['fr_annotations']
                if isinstance(fr_annotations_obj, dict):
                    # Convert object format to array format
                    fr_annotations = []
                    for fr_key, fr_docs in fr_annotations_obj.items():
                        fr_annotations.append({
                            'fr_group': fr_key,
                            'documents': fr_docs if isinstance(fr_docs, list) else []
                        })
                else:
                    fr_annotations = fr_annotations_obj if isinstance(fr_annotations_obj, list) else []
            else:
                fr_annotations = []

            # Process FR annotations
            fr_list = []
            if isinstance(fr_annotations, list):
                # Always update local database for selection state tracking
                # Clear existing FRs for this project before saving new ones
                FunctionalRequirement.objects.filter(project=project).delete()

                for fr_item in fr_annotations:
                    fr_group = fr_item.get('fr_group', '')
                    # For annotate-fr format, we don't have fr_id, so generate one from fr_group
                    fr_info_id_str = fr_item.get('fr_info_id', fr_item.get('fr_id', ''))

                    # If no ID provided, generate from fr_group (e.g., "m-fr-001: Register" -> "m-fr-001")
                    if not fr_info_id_str and fr_group:
                        fr_info_id_str = fr_group.split(':')[0].strip()

                    # Convert to UUID if it's a string
                    try:
                        fr_info_id = uuid.UUID(fr_info_id_str)
                    except (ValueError, TypeError):
                        if DEBUG:
                            print(f"Invalid UUID format for fr_id: {fr_info_id_str}, generating new one")
                        fr_info_id = uuid.uuid4()

                    # Parse FR group to extract ID and name
                    fr_name = fr_group.split(':', 1)[1].strip() if ':' in fr_group else fr_group

                    # Always save/update to local database for selection tracking
                    fr_obj, created = FunctionalRequirement.objects.get_or_create(
                        project=project,
                        fr_info_id=fr_info_id,
                        defaults={
                            'fr_group': fr_group,
                            'description': f"Functional Requirement: {fr_name}",
                            'is_selected': False
                        }
                    )
                    if not created and DEBUG:
                        print(f"Updated existing FR: {fr_group}")

                    fr_list.append({
                        'fr_info_id': str(fr_info_id),  # Use fr_info_id for frontend compatibility
                        'fr_group': fr_group,
                        'name': fr_name,
                        'full_name': fr_group,
                        'description': f"Functional Requirement: {fr_name}",
                        'is_selected': fr_obj.is_selected,  # Include selection state from DB
                        'documents': fr_item.get('documents', [])  # Include document locations
                    })

            return JsonResponse({
                'success': True,
                'fr_annotations': fr_list,
                'count': len(fr_list),
                'cached': not analyze
            })
        else:
            return JsonResponse({
                'success': False,
                'message': f"API call failed with status {response.status_code}: {response.text}"
            }, status=response.status_code)

    except requests.exceptions.Timeout:
        return JsonResponse({
            'success': False,
            'message': 'API request timeout'
        }, status=504)
    except requests.exceptions.RequestException as e:
        return JsonResponse({
            'success': False,
            'message': f'API request failed: {str(e)}'
        }, status=500)
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        if DEBUG:
            print(f"=== ANNOTATE FR ERROR ===")
            print(f"Error: {str(e)}")
            print(f"=========================")
        return JsonResponse({
            'success': False,
            'message': f'Unexpected error: {str(e)}'
        }, status=500)
@login_required
@require_http_methods(["POST"])
def select_fr_info(request, project_uuid):
    """Call the select-fr-info API to select/deselect FRs and update local DB"""
    from .models import FunctionalRequirement

    project = get_object_or_404(UserProject, uuid=project_uuid, user=request.user)

    try:
        # Get data from request
        data = json.loads(request.body) if request.body else {}
        fr_info_ids = data.get('fr_info_ids', [])
        is_selected = data.get('is_selected', True)

        if not fr_info_ids:
            return JsonResponse({
                'success': False,
                'message': 'fr_info_ids is required'
            }, status=400)

        # First update local database
        updated_count = 0
        for fr_info_id_str in fr_info_ids:
            try:
                fr_info_id = uuid.UUID(fr_info_id_str)
                fr_obj = FunctionalRequirement.objects.filter(
                    project=project,
                    fr_info_id=fr_info_id
                ).first()

                if fr_obj:
                    fr_obj.is_selected = is_selected
                    fr_obj.save()
                    updated_count += 1
                    if DEBUG:
                        print(f"Updated FR {fr_info_id} selection to {is_selected}")
            except (ValueError, TypeError) as e:
                if DEBUG:
                    print(f"Invalid UUID format for fr_info_id: {fr_info_id_str}")

        if DEBUG:
            print(f"Updated {updated_count} FRs in local database")

        # Then call the external API
        payload = {
            "fr_info_ids": fr_info_ids,
            "is_selected": is_selected
        }

        headers = {
            'Content-Type': 'application/json',
            'accept': 'application/json'
        }

        if DEBUG:
            print(f"=== SELECT FR INFO API DEBUG ===")
            print(f"Endpoint: {SELECT_FR_ENDPOINT}")
            print(f"Payload: {payload}")
            print(f"=============================")

        response = requests.post(
            SELECT_FR_ENDPOINT,
            json=payload,
            headers=headers,
            timeout=30,
            verify=False
        )

        if DEBUG:
            print(f"=== SELECT FR INFO RESPONSE ===")
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.text}")
            print(f"============================")

        if response.status_code == 200:
            # API returns a string response
            result = response.text.strip()
            return JsonResponse({
                'success': True,
                'message': f'FR selections saved successfully ({updated_count} local records updated)',
                'result': result,
                'updated_count': updated_count
            })
        else:
            return JsonResponse({
                'success': False,
                'message': f"API call failed with status {response.status_code}: {response.text}"
            }, status=response.status_code)

    except requests.exceptions.Timeout:
        return JsonResponse({
            'success': False,
            'message': 'API request timeout'
        }, status=504)
    except requests.exceptions.RequestException as e:
        return JsonResponse({
            'success': False,
            'message': f'API request failed: {str(e)}'
        }, status=500)
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        if DEBUG:
            print(f"=== SELECT FR INFO ERROR ===")
            print(f"Error: {str(e)}")
            print(f"=========================")
        return JsonResponse({
            'success': False,
            'message': f'Unexpected error: {str(e)}'
        }, status=500)

        return render(request, 'project/main/section_selection.html', context)

