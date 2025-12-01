# Standard library imports
import json
import logging
import os
import re
import sys
import threading
import time
import uuid
from urllib.parse import quote

# Third-party imports
import requests
import urllib3
from minio import Minio

# Django imports
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

# Local imports
from main.decorators import set_test_suites_show
from main.models import TestSuiteReport
from testcase_history.models import TestCaseHistory
from test_suite.models import ProjectTestSuite

from .forms import ProjectDocumentForm
from .models import DocumentSection, ProjectDocument, UserProject, GeneratedTestCase

# Disable SSL warnings for development
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Setup logger for debug output
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Create console handler if not exists
if not logger.handlers:
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

# Constants
DEBUG = True  # Set to False to disable debug prints

def debug_print(message):
    """Print debug message to both logger and stdout with flush"""
    if DEBUG:
        logger.debug(message)
        print(message, flush=True)
        sys.stdout.flush()
MINIO_ENDPOINT = "minio-api.truong51972.id.vn"
MINIO_ACCESS_KEY = "minioadmin"
MINIO_SECRET_KEY = "minioadmin"
MINIO_BUCKET_NAME = "apit-project"
MINIO_BASE_URL = "https://minio-api.truong51972.id.vn"
# MINIO_BASE_URL = "https://minio-api.truong51972.id.vn"

AGENT_API_BASE_URL = "https://api-t.truong51972.id.vn/"
DOCS_PREPROCESSING_ENDPOINT = f"{AGENT_API_BASE_URL}api/v1/document/docs-preprocessing"
SELECT_FR_ENDPOINT = f"{AGENT_API_BASE_URL}api/v1/document/select-fr-info"
GET_FR_ENDPOINT = f"{AGENT_API_BASE_URL}api/v1/document/get-fr-infos"

# New async test entities endpoints
GENERATE_TEST_ENTITIES_ENDPOINT = f"{AGENT_API_BASE_URL}api/v1/test-entities/generate"
GET_TEST_SUITES_ENDPOINT = f"{AGENT_API_BASE_URL}api/v1/test-entities/test-suites"
GET_TEST_CASES_ENDPOINT = f"{AGENT_API_BASE_URL}api/v1/test-entities/test-cases"
SELECT_TEST_CASES_ENDPOINT = f"{AGENT_API_BASE_URL}api/v1/test-entities/test-cases/select"

# Execute and Report endpoints
EXECUTE_TEST_SUITE_ENDPOINT = f"{AGENT_API_BASE_URL}api/v1/execute-and-report/execute"
GET_TEST_REPORT_ENDPOINT = f"{AGENT_API_BASE_URL}api/v1/execute-and-report/report"

# Preprocessed Document API endpoints
PREPROCESSED_DOCUMENTS_ALL_ENDPOINT = f"{AGENT_API_BASE_URL}/agent-service/agent/api/document/all/"
PREPROCESSED_DOCUMENTS_DELETE_ENDPOINT = f"{AGENT_API_BASE_URL}api/v1/document/delete/"

# Project API endpoints
PROJECT_CREATE_ENDPOINT = f"{AGENT_API_BASE_URL}api/v1/projects/"
PROJECT_ALL_ENDPOINT = f"{AGENT_API_BASE_URL}api/v1/projects/all"
PROJECT_DELETE_ENDPOINT = f"{AGENT_API_BASE_URL}api/v1/projects/"

# API Status Configuration
API_STATUS_CACHE_TIMEOUT = 60  # seconds - Cache for 30 seconds as requested
API_CONNECTION_TIMEOUT = 5     # seconds - Reduced for faster response
API_REQUEST_TIMEOUT = 500       # seconds

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
        # Sử dụng quote để encode URL đúng chuẩn (xử lý khoảng trắng và ký tự đặc biệt)

        username = user.username
        project_name = project.project_name
        file_name = file_obj.name
        object_name = f"{username}/{project_name}/{file_name}"

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
            'Authorization': 'Basic YWRtaW46YWRtaW4='
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
        test_url = f"{AGENT_API_BASE_URL}/api/v1/common/health"
        headers = {
            'accept': 'application/json', 
            'X-Service-Name': 'agent-service',
            'Authorization': 'Basic YWRtaW46YWRtaW4='
        }

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

    # Ensure headers dict exists and add Authorization header if not present
    if headers is None:
        headers = {}
    if 'Authorization' not in headers:
        headers['Authorization'] = 'Basic YWRtaW46YWRtaW4='

    for attempt in range(max_retries + 1):
        try:
            if DEBUG and attempt > 0:
                print(f"API call attempt {attempt + 1}/{max_retries + 1} for {url}")

            if method.upper() == 'GET':
                response = requests.get(url, headers=headers, timeout=API_REQUEST_TIMEOUT, verify=False)
            elif method.upper() == 'POST':
                response = requests.post(url, headers=headers, json=json_data, timeout=API_REQUEST_TIMEOUT, verify=False)
            elif method.upper() == 'PUT':
                response = requests.put(url, headers=headers, json=json_data, timeout=API_REQUEST_TIMEOUT, verify=False)
            elif method.upper() == 'DELETE':
                response = requests.delete(url, headers=headers, json=json_data, timeout=API_REQUEST_TIMEOUT, verify=False)
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


def call_docs_preprocessing(doc_url, project_id, doc_name=None):
    """Gọi API docs preprocessing với format mới và error handling cải tiến"""
    # Check API server status first
    api_status, error_message = check_api_server_status()
    if not api_status:
        user_friendly_error = "Không thể xử lý tài liệu vì API server hiện không khả dụng. Vui lòng kiểm tra trạng thái server và thử lại sau."
        if DEBUG:
            user_friendly_error += f" (Chi tiết: {error_message})"
        raise Exception(user_friendly_error)

    try:
        # Sử dụng doc_name gốc nếu được truyền vào, nếu không thì lấy từ URL
        if not doc_name:
            from urllib.parse import urlparse, unquote
            parsed_url = urlparse(doc_url)
            doc_name = os.path.basename(parsed_url.path)
            doc_name = unquote(doc_name)
        
        from urllib.parse import quote
        safe_doc_url = quote(doc_url, safe=':/?#[]@!$&\'()*+,;=')
        
        payload = {
            "doc_name": doc_name,  # Tên file gốc không qua xử lý
            "doc_url": safe_doc_url,  # URL đã safe
            "lang": "en",
            "project_id": str(project_id),
        }

        # Debug: In request body
        if DEBUG:
            import json
            print(f"=== DOCS PREPROCESSING REQUEST BODY ===")
            print(f"Endpoint: {DOCS_PREPROCESSING_ENDPOINT}")
            print(f"Request Body (JSON):")
            print(json.dumps(payload, indent=2, ensure_ascii=False))
            print(f"======================================")

        # Gửi POST request với link document
        headers = {
            'Content-Type': 'application/json',
            'accept': 'application/json',
            'X-Service-Name': 'agent-service'
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
            print(f"Doc Name: {doc_name}")
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
            'accept': 'application/json',
            'X-Service-Name': 'agent-service',
            'Authorization': 'Basic YWRtaW46YWRtaW4='
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
                'paginator': None,
                'api_count': 0,
                'api_server_offline': True,
                'error_message': error_message,
                'user_message': user_friendly_message
            }
            return render(request, 'project/project_list.html', context)

        headers = {
            'accept': 'application/json',
            'X-Service-Name': 'agent-service',
            'Authorization': 'Basic YWRtaW46YWRtaW4='
        }

        # Update endpoint to include user_id
        user_projects_endpoint = f"{PROJECT_ALL_ENDPOINT}"

        # Prepare request body for POST request
        request_body = {
            'user_id': str(request.user.id),
            'page_no': 0,
            'page_size': 0
        }

        # Use retry mechanism for API calls with POST method
        success, api_response, error_msg = call_api_with_retry(
            url=user_projects_endpoint,
            method='POST',
            headers=headers,
            json_data=request_body,
            max_retries=2,
            retry_delay=1
        )

        if not success:
            messages.error(request, f"Không thể tải danh sách dự án: {error_msg}")
            context = {
                'projects': [],
                'paginator': None,
                'api_count': 0,
                'api_error': True,
                'error_message': error_msg
            }
            return render(request, 'project/project_list.html', context)

        if DEBUG:
            print(f"API Projects Response: {api_response}")

        # Parse response format: handle both wrapped format {result: {...}, data: {projects: [...]}} and direct list
        api_projects = []
        if isinstance(api_response, list):
            # Direct list format
            api_projects = api_response
        elif isinstance(api_response, dict):
            # Wrapped format: {result: {...}, data: {projects: [...]}}
            result_info = api_response.get('result', {})
            data = api_response.get('data', {})
            api_projects = data.get('projects', [])
            
            # Check result code
            result_code = result_info.get('code', [])
            if result_code and result_code[0] != "0000":
                error_msg = result_info.get('description', 'API returned error')
                messages.error(request, f"Lỗi từ API: {error_msg}")
                context = {
                    'projects': [],
                    'paginator': None,
                    'api_count': 0,
                    'api_error': True,
                    'error_message': error_msg
                }
                return render(request, 'project/project_list.html', context)
        else:
            # Unknown format
            api_projects = []

        if DEBUG:
            print(f"Parsed projects count: {len(api_projects)}")

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

        # Pagination: 12 projects per page
        paginator = Paginator(api_projects, 12)
        page_number = request.GET.get('page', 1)
        projects_page = paginator.get_page(page_number)

        context = {
            'projects': projects_page,
            'paginator': paginator,
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
            'paginator': None,
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
                'accept': 'application/json',
                'X-Service-Name': 'agent-service',
                'Authorization': 'Basic YWRtaW46YWRtaW4='
            }

            response = requests.put(
                PROJECT_CREATE_ENDPOINT,
                json=payload,
                headers=headers,
                timeout=30,
                verify=False
            )

            if DEBUG:
                print(f"=== PROJECT ADD API RESPONSE DEBUG ===")
                print(f"Status Code: {response.status_code}")
                print(f"Response Headers: {dict(response.headers)}")
                print(f"Response Text: {response.text}")
                print(f"=====================================")

            if response.status_code == 200:
                result = response.json()
                
                if DEBUG:
                    print(f"=== PROJECT ADD API RESULT ===")
                    print(f"API Response JSON:")
                    print(json.dumps(result, indent=2, ensure_ascii=False))
                    print(f"=============================")
                
                # Check API response format: {"result": {"code": ["0000"], ...}, "data": {"project_id": "..."}}
                api_result = result.get('result', {})
                api_code = api_result.get('code', [])
                
                # Check if API call was successful
                if api_code != ['0000']:
                    error_description = api_result.get('description', 'Unknown error')
                    messages.error(request, f"API trả về lỗi: {error_description}")
                    return render(request, 'project/project_add.html')
                
                # Get project_id from data field
                api_data = result.get('data', {})
                api_project_id = api_data.get('project_id')
                
                if not api_project_id:
                    messages.error(request, "API không trả về project_id. Vui lòng thử lại.")
                    return render(request, 'project/project_add.html')
                
                if DEBUG:
                    print(f"Project ID from API: {api_project_id}")
                    print(f"=============================")
                
                # Validate UUID format
                try:
                    api_project_uuid = uuid.UUID(str(api_project_id))
                except (ValueError, TypeError) as e:
                    if DEBUG:
                        print(f"Invalid UUID format from API: {api_project_id}, error: {str(e)}")
                    messages.error(request, f"Project ID từ API không hợp lệ: {api_project_id}")
                    return render(request, 'project/project_add.html')
                
                # Also save to local database for sidebar and detail views
                # Use the UUID from API response instead of generating a new one
                local_project = UserProject.objects.create(
                    uuid=api_project_uuid,  # Use UUID from API response
                    user=request.user,
                    project_name=project_name,
                    description=description
                )
                
                if DEBUG:
                    print(f"=== LOCAL PROJECT CREATED ===")
                    print(f"Local Project UUID: {local_project.uuid}")
                    print(f"API Project ID: {api_project_id}")
                    print(f"Match: {str(local_project.uuid) == str(api_project_id)}")
                    print(f"============================")
                
                messages.success(request, f"Dự án đã được tạo thành công. ID dự án: {local_project.uuid}")
                return redirect('project_detail_by_uuid', project_uuid=local_project.uuid)
            else:
                if DEBUG:
                    print(f"=== PROJECT ADD API ERROR ===")
                    print(f"Status Code: {response.status_code}")
                    print(f"Error Response: {response.text}")
                    print(f"=============================")
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
@require_http_methods(["POST"])
def project_delete(request, project_uuid):
    # This view will handle deleting a project via API
    if DEBUG:
        print(f"=== PROJECT DELETE DEBUG ===")
        print(f"Request Method: {request.method}")
        print(f"User: {request.user}")
        print(f"User Authenticated: {request.user.is_authenticated}")
        print(f"Project UUID: {project_uuid}")
        print(f"CSRF Token Present: {'csrftoken' in request.COOKIES}")
        print(f"POST Data: {request.POST}")
        print(f"Headers: {dict(request.headers)}")
        print(f"=============================")
    
    try:
        delete_url = PROJECT_DELETE_ENDPOINT

        headers = {
            'Content-Type': 'application/json',
            'accept': 'application/json',
            'X-Service-Name': 'agent-service',
            'Authorization': 'Basic YWRtaW46YWRtaW4='
        }

        payload = {
            'project_id': str(project_uuid)
        }

        response = requests.delete(
            delete_url,
            json=payload,
            headers=headers,
            timeout=30,
            verify=False
        )

        if DEBUG:
            print(f"=== API DELETE RESPONSE ===")
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.text}")
            print(f"===========================")

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
                'accept': 'application/json',
                'X-Service-Name': 'agent-service',
                'Authorization': 'Basic YWRtaW46YWRtaW4='
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
            'accept': 'application/json',
            'X-Service-Name': 'agent-service',
            'Authorization': 'Basic YWRtaW46YWRtaW4='
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

                # Sử dụng tên file gốc không qua xử lý
                original_doc_name = document.original_filename if hasattr(document, 'original_filename') and document.original_filename else None
                
                api_response = call_docs_preprocessing(
                    doc_url=doc_url,
                    project_id=project.uuid,
                    doc_name=original_doc_name,
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
            'accept': 'application/json',
            'X-Service-Name': 'agent-service',
            'Authorization': 'Basic YWRtaW46YWRtaW4='
        }

        response = requests.put(
            PROJECT_CREATE_ENDPOINT,
            json=payload,
            headers=headers,
            timeout=30,
            verify=False
        )

        if response.status_code == 200:
            result = response.json()
            
            # Check API response format: {"result": {"code": ["0000"], ...}, "data": {"project_id": "..."}}
            api_result = result.get('result', {})
            api_code = api_result.get('code', [])
            
            if DEBUG:
                print(f"API Create Project Response: {result}")
                print(f"API Code: {api_code}")
            
            # Check if API call was successful
            if api_code == ['0000']:
                # Get project_id from data field
                api_data = result.get('data', {})
                project_id = api_data.get('project_id', '')
                
                if DEBUG:
                    print(f"Project ID returned by API: {project_id}")
                
                return JsonResponse({
                    'success': True,
                    'message': api_result.get('description', 'Project created successfully via API'),
                    'project_id': project_id,
                    'data': result
                })
            else:
                error_description = api_result.get('description', 'Unknown error')
                return JsonResponse({
                    'success': False,
                    'message': f'API trả về lỗi: {error_description}',
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
@require_http_methods(["POST"])
def api_get_all_projects(request):
    """Lấy tất cả projects qua API"""
    if DEBUG:
        timestamp = timezone.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        debug_print("=" * 80)
        debug_print(f"[DEBUG] [{timestamp}] api_get_all_projects - START")
        debug_print(f"[DEBUG] User ID: {request.user.id}")
        debug_print(f"[DEBUG] User: {request.user.username}")
    
    try:
        headers = {
            'accept': 'application/json',
            'Content-Type': 'application/json',
            'X-Service-Name': 'agent-service',
            'Authorization': 'Basic YWRtaW46YWRtaW4='
        }

        # Get parameters from request body (POST)
        user_id = str(request.user.id)
        page_no = 0
        page_size = 0
        
        try:
            if request.body:
                data = json.loads(request.body)
                user_id = data.get('user_id', user_id)
                page_no = int(data.get('page_no', 0))
                page_size = int(data.get('page_size', 0))
        except:
            # Fallback to GET params if body parsing fails
            page_no = int(request.GET.get('page_no', 0))
            page_size = int(request.GET.get('page_size', 0))

        request_body = {
            'user_id': user_id,
            'page_no': page_no,
            'page_size': page_size
        }

        if DEBUG:
            debug_print("-" * 80)
            debug_print("[DEBUG] ========== REQUEST INFO ==========")
            debug_print(f"[DEBUG] Method: POST")
            debug_print(f"[DEBUG] URL: {PROJECT_ALL_ENDPOINT}")
            debug_print(f"[DEBUG] Headers:")
            for key, value in headers.items():
                # Mask authorization token for security
                if key.lower() == 'authorization':
                    debug_print(f"  {key}: {value[:20]}...")
                else:
                    debug_print(f"  {key}: {value}")
            debug_print(f"[DEBUG] Request Body:")
            debug_print(json.dumps(request_body, indent=2, ensure_ascii=False))
            debug_print("[DEBUG] ==================================")
            debug_print("-" * 80)
            debug_print(f"[DEBUG] Making POST request to: {PROJECT_ALL_ENDPOINT}")

        response = requests.post(
            PROJECT_ALL_ENDPOINT,
            headers=headers,
            json=request_body,
            timeout=30,
            verify=False
        )

        if DEBUG:
            debug_print("-" * 80)
            debug_print("[DEBUG] ========== RESPONSE INFO ==========")
            debug_print(f"[DEBUG] Status Code: {response.status_code}")
            debug_print(f"[DEBUG] Response Headers:")
            for key, value in response.headers.items():
                debug_print(f"  {key}: {value}")
            debug_print(f"[DEBUG] Response Size: {len(response.content)} bytes")
            debug_print("-" * 80)

        if response.status_code == 200:
            if DEBUG:
                debug_print("[DEBUG] ========== RAW RESPONSE ==========")
                try:
                    # Try to print raw response text first
                    debug_print(f"[DEBUG] Raw Response Text (first 500 chars):")
                    debug_print(response.text[:500])
                    if len(response.text) > 500:
                        debug_print(f"... (truncated, total length: {len(response.text)} chars)")
                except:
                    debug_print("[DEBUG] Could not read raw response text")
                debug_print("-" * 80)
            
            try:
                response_data = response.json()
            except json.JSONDecodeError as e:
                if DEBUG:
                    debug_print(f"[DEBUG] JSON Decode Error: {str(e)}")
                    debug_print(f"[DEBUG] Response text: {response.text}")
                return JsonResponse({
                    'success': False,
                    'message': f'Invalid JSON response: {str(e)}'
                })
            
            if DEBUG:
                debug_print("[DEBUG] ========== PARSED JSON RESPONSE ==========")
                debug_print(json.dumps(response_data, indent=2, ensure_ascii=False))
                debug_print("[DEBUG] ============================================")
                debug_print("-" * 80)
            
            # Handle different response formats:
            # 1. Direct list format from agent-service: [...]
            # 2. Wrapped format from gateway: { "result": {...}, "data": { "projects": [...] } }
            projects = []
            result_code = None
            result_description = ''
            
            if isinstance(response_data, list):
                # Direct list format
                projects = response_data
                result_description = 'Projects retrieved successfully'
            elif isinstance(response_data, dict):
                # Wrapped format
                result_info = response_data.get('result', {})
                data = response_data.get('data', {})
                projects = data.get('projects', [])
                result_code = result_info.get('code', [])
                result_description = result_info.get('description', '')
            else:
                # Unknown format
                projects = []
            
            if DEBUG:
                debug_print("[DEBUG] ========== PROCESSED DATA ==========")
                debug_print(f"[DEBUG] Response Format: {'List' if isinstance(response_data, list) else 'Wrapped' if isinstance(response_data, dict) else 'Unknown'}")
                debug_print(f"[DEBUG] Result Code: {result_code}")
                debug_print(f"[DEBUG] Result Description: {result_description}")
                debug_print(f"[DEBUG] Number of projects: {len(projects)}")
                if projects:
                    debug_print(f"[DEBUG] First project sample:")
                    debug_print(json.dumps(projects[0] if len(projects) > 0 else {}, indent=2, ensure_ascii=False))
                    if len(projects) > 1:
                        debug_print(f"[DEBUG] ... and {len(projects) - 1} more projects")
                debug_print("[DEBUG] ===================================")
                debug_print("[DEBUG] api_get_all_projects - SUCCESS")
                debug_print("=" * 80)
            
            # Return success if we got projects or if result code indicates success
            if projects or (result_code and result_code[0] == "0000") or not result_code:
                return JsonResponse({
                    'success': True,
                    'message': result_description or 'Projects retrieved successfully via API',
                    'projects': projects,
                    'count': len(projects)
                })
            else:
                # API returned error code
                error_msg = f"API returned error code: {result_code}, description: {result_description}"
                if DEBUG:
                    debug_print(f"[DEBUG] API returned error code!")
                    debug_print(f"[DEBUG] {error_msg}")
                    debug_print("=" * 80)
                
                return JsonResponse({
                    'success': False,
                    'message': error_msg,
                    'projects': [],
                    'count': 0
                })
        else:
            error_msg = f"API call failed with status {response.status_code}: {response.text}"
            if DEBUG:
                debug_print("[DEBUG] ========== ERROR RESPONSE ==========")
                debug_print(f"[DEBUG] Status Code: {response.status_code}")
                debug_print(f"[DEBUG] Status Text: {response.reason}")
                debug_print(f"[DEBUG] Response URL: {response.url}")
                try:
                    error_response = response.json()
                    debug_print("[DEBUG] Error Response JSON:")
                    debug_print(json.dumps(error_response, indent=2, ensure_ascii=False))
                except:
                    debug_print(f"[DEBUG] Response Text (first 1000 chars):")
                    debug_print(response.text[:1000])
                    if len(response.text) > 1000:
                        debug_print(f"... (truncated, total length: {len(response.text)} chars)")
                debug_print("[DEBUG] ====================================")
                debug_print("[DEBUG] api_get_all_projects - FAILED")
                debug_print("=" * 80)
            
            return JsonResponse({
                'success': False,
                'message': error_msg
            })

    except requests.exceptions.Timeout:
        if DEBUG:
            debug_print("[DEBUG] ========== TIMEOUT EXCEPTION ==========")
            debug_print(f"[DEBUG] Exception Type: requests.exceptions.Timeout")
            debug_print(f"[DEBUG] Endpoint: {PROJECT_ALL_ENDPOINT}")
            debug_print(f"[DEBUG] Timeout: 30 seconds")
            debug_print("[DEBUG] api_get_all_projects - TIMEOUT")
            debug_print("=" * 80)
        
        return JsonResponse({
            'success': False,
            'message': 'API request timeout'
        })
    except requests.exceptions.RequestException as e:
        if DEBUG:
            debug_print("[DEBUG] ========== REQUEST EXCEPTION ==========")
            debug_print(f"[DEBUG] Exception Type: requests.exceptions.RequestException")
            debug_print(f"[DEBUG] Error: {str(e)}")
            debug_print(f"[DEBUG] Error Class: {type(e).__name__}")
            debug_print(f"[DEBUG] Endpoint: {PROJECT_ALL_ENDPOINT}")
            if hasattr(e, 'request'):
                debug_print(f"[DEBUG] Request URL: {e.request.url if e.request else 'N/A'}")
                debug_print(f"[DEBUG] Request Method: {e.request.method if e.request else 'N/A'}")
            import traceback
            debug_print(f"[DEBUG] Traceback:\n{traceback.format_exc()}")
            debug_print("[DEBUG] api_get_all_projects - REQUEST EXCEPTION")
            debug_print("=" * 80)
        
        return JsonResponse({
            'success': False,
            'message': f'API request failed: {str(e)}'
        })
    except Exception as e:
        if DEBUG:
            debug_print("[DEBUG] ========== UNEXPECTED ERROR ==========")
            debug_print(f"[DEBUG] Exception Type: {type(e).__name__}")
            debug_print(f"[DEBUG] Error: {str(e)}")
            debug_print(f"[DEBUG] Endpoint: {PROJECT_ALL_ENDPOINT}")
            import traceback
            debug_print(f"[DEBUG] Full Traceback:\n{traceback.format_exc()}")
            debug_print("[DEBUG] api_get_all_projects - UNEXPECTED ERROR")
            debug_print("=" * 80)
        
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
        delete_url = PROJECT_DELETE_ENDPOINT

        headers = {
            'Content-Type': 'application/json',
            'accept': 'application/json',
            'X-Service-Name': 'agent-service',
            'Authorization': 'Basic YWRtaW46YWRtaW4='
        }

        payload = {
            'project_id': str(project_id)
        }

        response = requests.delete(
            delete_url,
            json=payload,
            headers=headers,
            timeout=30,
            verify=False
        )

        if DEBUG:
            print(f"=== PROJECT DELETE RESPONSE ===")
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.text}")
            print(f"=============================")

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
                'accept': 'application/json',
                'X-Service-Name': 'agent-service',
                'Authorization': 'Basic YWRtaW46YWRtaW4='
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
                    # Only include FRs that start with 'm' (m-fr) instead of 'u' (u-fr)
                    if fr_obj.fr_group.startswith('m-fr') or fr_obj.fr_group.startswith('m'):
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
            'accept': 'application/json',
            'X-Service-Name': 'agent-service',
            'Authorization': 'Basic YWRtaW46YWRtaW4='
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
                    
                    # Only process FRs that start with 'm' (m-fr) instead of 'u' (u-fr)
                    if not (fr_group.startswith('m-fr') or fr_group.startswith('m')):
                        continue
                    
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
            'accept': 'application/json',
            'X-Service-Name': 'agent-service',
            'Authorization': 'Basic YWRtaW46YWRtaW4='
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


# Test Case Generation Endpoints
@login_required
@require_http_methods(["GET"])
def check_test_suite_exists(request, project_uuid):
    """Check if test suite already exists for this project"""
    project = get_object_or_404(UserProject, uuid=project_uuid, user=request.user)
    
    try:
        # Check if test cases exist in database
        test_cases_count = GeneratedTestCase.objects.filter(project=project).count()
        
        if DEBUG:
            print(f"=== CHECK TEST SUITE EXISTS ===")
            print(f"Project UUID: {project_uuid}")
            print(f"Test cases count: {test_cases_count}")
            print(f"==============================")
        
        exists = test_cases_count > 0
        
        return JsonResponse({
            'success': True,
            'exists': exists,
            'test_cases_count': test_cases_count,
            'message': f'Test suite exists with {test_cases_count} test cases' if exists else 'No test suite found'
        })
        
    except Exception as e:
        if DEBUG:
            print(f"=== CHECK TEST SUITE EXISTS ERROR ===")
            print(f"Error: {str(e)}")
            print(f"====================================")
        return JsonResponse({
            'success': False,
            'exists': False,
            'message': f'Unexpected error: {str(e)}'
        }, status=500)


@login_required
@require_http_methods(["POST"])
def generate_test_cases(request, project_uuid):
    """Generate test cases from selected FRs - requires at least one FR to be selected"""
    from .models import FunctionalRequirement
    
    project = get_object_or_404(UserProject, uuid=project_uuid, user=request.user)
    
    try:
        # Check if at least one FR is selected
        selected_frs = FunctionalRequirement.objects.filter(
            project=project,
            is_selected=True
        )
        
        if not selected_frs.exists():
            return JsonResponse({
                'success': False,
                'message': 'Vui lòng chọn ít nhất một Functional Requirement (FR) trước khi tạo test cases.'
            }, status=400)
        
        # Get request body for lang parameter (default to 'en')
        data = json.loads(request.body) if request.body else {}
        lang = data.get('lang', 'en')
        
        # Prepare payload according to API specification
        payload = {
            'lang': lang,
            'project_id': str(project.uuid)
        }

        headers = {
            'Content-Type': 'application/json',
            'accept': 'application/json',
            'X-Service-Name': 'agent-service'
        }

        if DEBUG:
            print(f"=== GENERATE TEST CASES (ASYNC) ===")
            print(f"Endpoint: {GENERATE_TEST_ENTITIES_ENDPOINT}")
            print(f"Project UUID: {project_uuid}")
            print(f"Payload: {payload}")
            print(f"Selected FRs count: {selected_frs.count()}")
            print(f"===========================")

        # Call async API endpoint - it will return immediately with "Work in progress!"
        success, response_data, error_msg = call_api_with_retry(
            url=GENERATE_TEST_ENTITIES_ENDPOINT,
            method='POST',
            headers=headers,
            json_data=payload,
            max_retries=2,
            retry_delay=2
        )

        if DEBUG:
            print(f"=== GENERATE TEST CASES RESPONSE ===")
            print(f"Success: {success}")
            if success:
                print(f"Response Data: {response_data}")
            else:
                print(f"Error: {error_msg}")
            print(f"================================")
        
        if success:
            # Set session start time for status tracking
            import time as time_module
            cache_key = f'test_case_gen_start_{project_uuid}'
            request.session[cache_key] = time_module.time()
            request.session.save()
            
            # Check response - should have "Work in progress!" message
            if response_data and response_data.get('result', {}).get('description') == 'Work in progress!':
                return JsonResponse({
                    'success': True,
                    'message': 'Đang xử lý tạo test cases bất đồng bộ. Vui lòng đợi...',
                    'selected_frs_count': selected_frs.count()
                })
            else:
                return JsonResponse({
                    'success': True,
                    'message': 'Test case generation đã được khởi động',
                    'selected_frs_count': selected_frs.count()
                })
        else:
            return JsonResponse({
                'success': False,
                'message': f'Không thể khởi động tạo test cases: {error_msg}'
            }, status=500)
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Invalid JSON data in request'
        }, status=400)
    except Exception as e:
        if DEBUG:
            print(f"=== GENERATE TEST CASES ERROR ===")
            print(f"Error: {str(e)}")
            print(f"Error type: {type(e)}")
            print(f"================================")
        return JsonResponse({
            'success': False,
            'message': f'Unexpected error: {str(e)}'
        }, status=500)


def fetch_and_save_test_cases_from_api(project):
    """Fetch test suites and test cases from API and save to database"""
    try:
        # First, get test suites for this project
        headers = {
            'Content-Type': 'application/json',
            'accept': 'application/json',
            'X-Service-Name': 'agent-service',
            'Authorization': 'Basic YWRtaW46YWRtaW4='
        }
        
        test_suites_url = f"{GET_TEST_SUITES_ENDPOINT}/{str(project.uuid)}"
        
        if DEBUG:
            print(f"=== FETCHING TEST SUITES ===")
            print(f"URL: {test_suites_url}")
            print(f"============================")
        
        response = requests.get(test_suites_url, headers=headers, timeout=30, verify=False)
        
        if response.status_code != 200:
            if DEBUG:
                print(f"Failed to fetch test suites: {response.status_code} - {response.text}")
            return False, f"Failed to fetch test suites: {response.status_code}"
        
        response_data = response.json()
        
        if DEBUG:
            print(f"=== TEST SUITES RESPONSE ===")
            print(f"Response: {response_data}")
            print(f"============================")
        
        # Check if response is successful
        result = response_data.get('result', {})
        if result.get('code', []) != ['0000']:
            return False, f"API returned error: {result.get('description', 'Unknown error')}"
        
        # Get test suites
        data = response_data.get('data', {})
        test_suites = data.get('test_suites', [])
        
        if not test_suites:
            # No test suites yet
            return False, None
        
        # Delete existing test cases for this project (if regenerating)
        GeneratedTestCase.objects.filter(project=project).delete()
        
        saved_count = 0
        
        # Fetch test cases for each test suite
        for test_suite in test_suites:
            test_suite_id = test_suite.get('test_suite_id')
            if not test_suite_id:
                continue
            
            # Get or create ProjectTestSuite and save test_suite_id from API
            test_suite_name = test_suite.get('test_suite_name', f'Test Suite {test_suite_id}')
            test_suite_obj, created = ProjectTestSuite.objects.get_or_create(
                project=project,
                api_test_suite_id=test_suite_id,
                defaults={
                    'test_suite_name': test_suite_name,
                    'description': test_suite.get('description', '')
                }
            )
            
            # Update api_test_suite_id if it wasn't set
            if not test_suite_obj.api_test_suite_id:
                test_suite_obj.api_test_suite_id = test_suite_id
                test_suite_obj.save()
            
            if DEBUG:
                print(f"=== TEST SUITE OBJECT ===")
                print(f"Test Suite ID (API): {test_suite_id}")
                print(f"Test Suite UUID (DB): {test_suite_obj.uuid}")
                print(f"Created: {created}")
                print(f"=========================")
            
            test_cases_url = f"{GET_TEST_CASES_ENDPOINT}/{test_suite_id}"
            
            if DEBUG:
                print(f"=== FETCHING TEST CASES FOR SUITE ===")
                print(f"Test Suite ID: {test_suite_id}")
                print(f"URL: {test_cases_url}")
                print(f"=====================================")
            
            test_cases_response = requests.get(test_cases_url, headers=headers, timeout=30, verify=False)
            
            if test_cases_response.status_code != 200:
                if DEBUG:
                    print(f"Failed to fetch test cases for suite {test_suite_id}: {test_cases_response.status_code}")
                continue
            
            test_cases_data = test_cases_response.json()
            
            # Check if response is successful
            test_cases_result = test_cases_data.get('result', {})
            if test_cases_result.get('code', []) != ['0000']:
                if DEBUG:
                    print(f"API returned error for test cases: {test_cases_result.get('description', 'Unknown error')}")
                continue
            
            # Get test cases
            test_cases_info = test_cases_data.get('data', {})
            test_cases_list = test_cases_info.get('test_cases', [])
            
            # Save test cases to database
            for test_case in test_cases_list:
                api_info = test_case.get('api_info', {})
                request_body = test_case.get('request_body', {})
                expected_output = test_case.get('expected_output', {})
                test_case_type = test_case.get('test_case_type', 'basic_validation')
                
                # Determine HTTP method from api_info
                http_method = api_info.get('method', 'GET')
                
                # Get URL from api_info
                request_url = api_info.get('url', '')
                
                # Get headers from api_info
                request_headers = api_info.get('headers', {})
                
                # Get test case ID and name
                test_case_id = test_case.get('test_case_id', '')
                test_case_name = test_case.get('test_case', '')
                
                # Create test case object
                test_case_obj = GeneratedTestCase(
                    project=project,
                    api_name=request_url,  # Use URL as API name for now
                    http_method=http_method,
                    request_url=request_url,
                    request_headers=request_headers,
                    test_case_id=test_case_id,
                    test_case_name=test_case_name,
                    test_category=test_case_type,
                    request_body_template=request_body,
                    request_mapping={},  # Empty mapping as request_body is already the final body
                    expected_output=expected_output,
                    test_case_data=test_case
                )
                test_case_obj.save()
                saved_count += 1
        
        if DEBUG:
            print(f"=== SAVED TEST CASES ===")
            print(f"Total saved: {saved_count}")
            print(f"=========================")
        
        return True, saved_count
        
    except Exception as e:
        if DEBUG:
            print(f"=== FETCH AND SAVE TEST CASES ERROR ===")
            print(f"Error: {str(e)}")
            import traceback
            print(traceback.format_exc())
            print(f"======================================")
        return False, str(e)


@login_required
@require_http_methods(["GET"])
def check_test_case_status(request, project_uuid):
    """Check the status of test case generation with async polling logic"""
    project = get_object_or_404(UserProject, uuid=project_uuid, user=request.user)
    
    try:
        # Check if test cases exist in database
        test_cases_count = GeneratedTestCase.objects.filter(project=project).count()
        
        if DEBUG:
            print(f"=== CHECK TEST CASE STATUS ===")
            print(f"Project UUID: {project_uuid}")
            print(f"Test cases count: {test_cases_count}")
            print(f"=============================")
        
        if test_cases_count > 0:
            # Test cases have been generated and saved
            return JsonResponse({
                'status': 'completed',
                'message': f'Test case generation completed successfully ({test_cases_count} test cases)',
                'test_cases_count': test_cases_count,
                'test_cases': None  # Will be fetched separately
            })
        
        # Still processing - check if generation was started
        import time as time_module
        cache_key = f'test_case_gen_start_{project_uuid}'
        start_time = request.session.get(cache_key)
        
        if not start_time:
            # Generation hasn't started yet
            return JsonResponse({
                'status': 'processing',
                'message': 'Đang khởi tạo quá trình tạo test cases...',
                'progress': 5
            })
        
        elapsed = time_module.time() - start_time
        
        # Wait 1 minute (60 seconds) before starting to poll
        if elapsed < 60:
            return JsonResponse({
                'status': 'processing',
                'message': f'Đang xử lý... ({int(elapsed)}s / 60s)',
                'progress': min(int((elapsed / 60) * 50), 50)
            })
        
        # After 1 minute, start polling test-suites endpoint every 5 seconds
        # Track last fetch time to only fetch every 5 seconds
        last_fetch_key = f'test_case_last_fetch_{project_uuid}'
        last_fetch_time = request.session.get(last_fetch_key, 0)
        
        # Only fetch if 5 seconds have passed since last fetch
        if time_module.time() - last_fetch_time < 5:
            # Still processing, but don't fetch yet
            polling_elapsed = elapsed - 60  # Time spent polling
            return JsonResponse({
                'status': 'processing',
                'message': f'Đang chờ test suites hoàn thành... ({int(polling_elapsed)}s polling)',
                'progress': min(50 + int((polling_elapsed / 120) * 45), 95)  # 50-95% range
            })
        
        # Update last fetch time
        request.session[last_fetch_key] = time_module.time()
        request.session.save()
        
        # Try to fetch test suites and test cases
        success, result = fetch_and_save_test_cases_from_api(project)
        
        if success:
            # Successfully fetched and saved test cases
            # Clear session keys
            if cache_key in request.session:
                del request.session[cache_key]
            if last_fetch_key in request.session:
                del request.session[last_fetch_key]
            request.session.save()
            
            test_cases_count = GeneratedTestCase.objects.filter(project=project).count()
            return JsonResponse({
                'status': 'completed',
                'message': f'Test case generation completed successfully ({test_cases_count} test cases)',
                'test_cases_count': test_cases_count,
                'test_cases': None
            })
        elif result is None:
            # No test suites yet - still processing, continue polling
            # The frontend will call this again in 5 seconds
            polling_elapsed = elapsed - 60  # Time spent polling
            return JsonResponse({
                'status': 'processing',
                'message': f'Đang chờ test suites hoàn thành... ({int(polling_elapsed)}s polling)',
                'progress': min(50 + int((polling_elapsed / 120) * 45), 95)  # 50-95% range
            })
        else:
            # Error occurred
            if DEBUG:
                print(f"Error fetching test cases: {result}")
            # Don't clear session keys yet, allow retry
            return JsonResponse({
                'status': 'processing',
                'message': f'Đang thử lại... ({result})',
                'progress': 90
            })
            
    except Exception as e:
        if DEBUG:
            print(f"=== CHECK TEST CASE STATUS ERROR ===")
            print(f"Error: {str(e)}")
            import traceback
            print(traceback.format_exc())
            print(f"===================================")
        return JsonResponse({
            'status': 'error',
            'message': f'Unexpected error: {str(e)}'
        }, status=500)


@login_required
@require_http_methods(["GET"])
def get_test_cases(request, project_uuid):
    """Get test cases from API by test suite ID"""
    project = get_object_or_404(UserProject, uuid=project_uuid, user=request.user)
    
    try:
        # Get the latest test suite for this project
        latest_test_suite = ProjectTestSuite.objects.filter(project=project).order_by('-created_at').first()
        
        if not latest_test_suite or not latest_test_suite.api_test_suite_id:
            return JsonResponse({
                'success': False,
                'message': 'Không tìm thấy test suite cho project này.'
            }, status=404)
        
        test_suite_id = latest_test_suite.api_test_suite_id
        
        if DEBUG:
            print(f"\n=== GET TEST CASES FROM API ===")
            print(f"Project UUID: {project_uuid}")
            print(f"Test Suite ID: {test_suite_id}")
        
        # Prepare headers according to API specification
        headers = {
            'accept': 'application/json',
            'X-Service-Name': 'agent-service',
            'Authorization': 'Basic YWRtaW46YWRtaW4='
        }
        
        # Build API URL
        test_cases_url = f"{GET_TEST_CASES_ENDPOINT}/{test_suite_id}"
        
        if DEBUG:
            print(f"API URL: {test_cases_url}")
            print(f"Headers: {headers}")
        
        # Call API
        response = requests.get(test_cases_url, headers=headers, timeout=30, verify=False)
        
        if DEBUG:
            print(f"Response Status: {response.status_code}")
        
        if response.status_code != 200:
            return JsonResponse({
                'success': False,
                'message': f'Lỗi khi gọi API: HTTP {response.status_code}'
            }, status=response.status_code)
        
        # Parse response
        response_data = response.json()
        
        if DEBUG:
            print(f"Response Data: {json.dumps(response_data, indent=2, ensure_ascii=False)}")
        
        # Check result code
        result = response_data.get('result', {})
        code = result.get('code', [])
        
        if code != ['0000']:
            description = result.get('description', 'Unknown error')
            return JsonResponse({
                'success': False,
                'message': f'API trả về lỗi: {description}'
            }, status=400)
        
        # Extract test cases from response
        data = response_data.get('data', {})
        test_cases = data.get('test_cases', [])
        
        if DEBUG:
            print(f"Found {len(test_cases)} test cases in API response")
        
        # Format test cases for frontend
        formatted_test_cases = []
        
        for tc in test_cases:
            # Extract data from API response
            test_case_id = tc.get('test_case_id', 'N/A')
            test_case_name = tc.get('test_case', 'N/A')
            test_case_type = tc.get('test_case_type', 'basic_validation')
            request_body = tc.get('request_body', {})
            execute = tc.get('execute', False)
            tc_id = tc.get('id', '')
            api_info = tc.get('api_info', {})
            expected_output = tc.get('expected_output', {})
            
            # Extract API info
            api_url = api_info.get('url', 'N/A')
            api_method = api_info.get('method', 'N/A')
            api_headers = api_info.get('headers', {})
            
            # Extract expected output
            expected_statuscode = expected_output.get('statuscode', 'N/A')
            expected_response = expected_output.get('response_mapping', {})
            
            # Format category name
            category_display = 'Basic Validation' if test_case_type == 'basic_validation' else 'Business Logic'
            
            # Format test case ID
            formatted_test_case_id = f"TC-{test_case_id}" if test_case_id != 'N/A' else 'N/A'
            
            formatted_test_cases.append({
                'test_case_id': formatted_test_case_id,
                'endpoint': api_url,
                'header': api_headers,
                'test_case_name': test_case_name,
                'test_category': category_display,
                'request_body': json.dumps(request_body, indent=2, ensure_ascii=False),
                'expected_statuscode': expected_statuscode,
                'expected_response': json.dumps(expected_response, indent=2, ensure_ascii=False) if expected_response else 'N/A',
                'api_name': api_url.split('/')[-1] if api_url != 'N/A' else 'N/A',  # Extract API name from URL
                'http_method': api_method,
                'uuid': tc_id,
                'full_test_case_data': tc,  # Include full test case data from API
                'is_selected': execute,  # Use execute field as selection state
                'execute': execute
            })
        
        if DEBUG:
            print(f"Formatted {len(formatted_test_cases)} test cases")
            print(f"===========================================\n")
        
        # Return as dataframe-like structure
        return JsonResponse({
            'success': True,
            'data': {
                'columns': ['test_case_id', 'endpoint', 'header', 'test_case_name', 'test_category', 
                           'request_body', 'expected_statuscode', 'expected_response'],
                'rows': formatted_test_cases,
                'count': len(formatted_test_cases)
            }
        })
        
    except requests.exceptions.RequestException as e:
        if DEBUG:
            print(f"=== GET TEST CASES API ERROR ===")
            print(f"Request Error: {str(e)}")
            import traceback
            print(traceback.format_exc())
            print(f"===================================")
        return JsonResponse({
            'success': False,
            'message': f'Lỗi kết nối API: {str(e)}'
        }, status=500)
    except Exception as e:
        if DEBUG:
            print(f"=== GET TEST CASES ERROR ===")
            print(f"Error: {str(e)}")
            import traceback
            print(traceback.format_exc())
            print(f"===========================")
        return JsonResponse({
            'success': False,
            'message': f'Unexpected error: {str(e)}'
        }, status=500)


@login_required
@require_http_methods(["POST"])
def select_test_cases(request, project_uuid):
    """Select test cases for execution via API"""
    project = get_object_or_404(UserProject, uuid=project_uuid, user=request.user)
    
    try:
        # Parse request body
        if DEBUG:
            print(f"\n{'='*60}")
            print(f"=== SELECT TEST CASES - START ===")
            print(f"{'='*60}")
            print(f"Request Body (raw): {request.body}")
        
        data = json.loads(request.body) if request.body else {}
        test_case_ids = data.get('test_case_ids', [])
        execute = data.get('execute', True)
        
        if DEBUG:
            print(f"\n--- Request Parsed ---")
            print(f"Project UUID: {project_uuid}")
            print(f"User: {request.user}")
            print(f"Test Case IDs: {test_case_ids}")
            print(f"Test Case IDs Count: {len(test_case_ids)}")
            print(f"Execute Flag: {execute}")
            print(f"Full Request Data: {json.dumps(data, indent=2, ensure_ascii=False)}")
        
        if not test_case_ids:
            if DEBUG:
                print(f"\n--- ERROR: No test case IDs provided ---")
            return JsonResponse({
                'success': False,
                'message': 'Vui lòng chọn ít nhất một test case.'
            }, status=400)
        
        # Warn if execute is False - this might be the issue
        if not execute:
            if DEBUG:
                print(f"\n⚠ WARNING: execute=False was sent!")
                print(f"  If you want to SELECT test cases for execution, execute should be True")
                print(f"  execute=False might mean 'deselect' or 'unselect' test cases")
                print(f"  This might explain why execute field is not being set to True on the server")
        
        # Validate and prepare test_case_ids
        if not isinstance(test_case_ids, list):
            return JsonResponse({
                'success': False,
                'message': 'test_case_ids phải là một array.'
            }, status=400)
        
        # Ensure all test_case_ids are strings (UUIDs)
        test_case_ids = [str(tc_id) for tc_id in test_case_ids]
        
        # Prepare payload according to API specification
        payload = {
            'test_case_ids': test_case_ids,
            'execute': bool(execute)  # Ensure boolean
        }
        
        # Prepare headers according to API specification
        headers = {
            'accept': 'application/json',
            'Content-Type': 'application/json',
            'X-Service-Name': 'agent-service',
            'Authorization': 'Basic YWRtaW46YWRtaW4='
        }
        
        if DEBUG:
            print(f"\n--- API Call Preparation ---")
            print(f"Endpoint: {SELECT_TEST_CASES_ENDPOINT}")
            print(f"Payload: {json.dumps(payload, indent=2, ensure_ascii=False)}")
            print(f"Payload Type Check:")
            print(f"  - test_case_ids type: {type(payload['test_case_ids'])}")
            print(f"  - test_case_ids length: {len(payload['test_case_ids'])}")
            print(f"  - execute type: {type(payload['execute'])}")
            print(f"  - execute value: {payload['execute']}")
            print(f"Headers: {json.dumps(headers, indent=2, ensure_ascii=False)}")
        
        # Call API endpoint
        response = requests.post(
            SELECT_TEST_CASES_ENDPOINT,
            headers=headers,
            json=payload,
            timeout=30,
            verify=False
        )
        
        if DEBUG:
            print(f"\n--- API Response ---")
            print(f"Status Code: {response.status_code}")
        
        if response.status_code != 200:
            if DEBUG:
                print(f"Response Text: {response.text}")
                print(f"Response Headers: {dict(response.headers)}")
            return JsonResponse({
                'success': False,
                'message': f'Lỗi khi gọi API: HTTP {response.status_code}'
            }, status=response.status_code)
        
        # Parse response
        try:
            response_data = response.json()
        except json.JSONDecodeError:
            if DEBUG:
                print(f"ERROR: Response is not valid JSON")
                print(f"Response Text: {response.text}")
                print(f"Response Headers: {dict(response.headers)}")
            return JsonResponse({
                'success': False,
                'message': f'API trả về response không hợp lệ: {response.text[:200]}'
            }, status=500)
        
        if DEBUG:
            print(f"Response Data: {json.dumps(response_data, indent=2, ensure_ascii=False)}")
            print(f"Response Headers: {dict(response.headers)}")
            print(f"Full Response Object: Status={response.status_code}, URL={response.url}")
        
        # Check result code
        result = response_data.get('result', {})
        code = result.get('code', [])
        
        if DEBUG:
            print(f"\n--- Response Processing ---")
            print(f"Result: {result}")
            print(f"Code: {code}")
            print(f"Code == ['0000']: {code == ['0000']}")
        
        if code != ['0000']:
            description = result.get('description', 'Unknown error')
            if DEBUG:
                print(f"\n--- API Returned Error Code ---")
                print(f"Code: {code}")
                print(f"Description: {description}")
                print(f"Full Result: {result}")
                print(f"\n{'='*60}")
                print(f"=== SELECT TEST CASES - END (ERROR CODE) ===")
                print(f"{'='*60}\n")
            return JsonResponse({
                'success': False,
                'message': f'API trả về lỗi: {description}'
            }, status=400)
        
        # Extract selected test cases from response
        data_response = response_data.get('data', {})
        selected_test_cases = data_response.get('test_cases', [])
        
        if DEBUG:
            print(f"\n--- Success ---")
            print(f"Selected Test Cases: {selected_test_cases}")
            print(f"Selected Count: {len(selected_test_cases)}")
        
        # Verify: Call get_test_cases API to check if execute was actually set
        if DEBUG:
            print(f"\n--- Verifying Execute Status ---")
        
        try:
            # Get test suite ID for verification
            latest_test_suite = ProjectTestSuite.objects.filter(project=project).order_by('-created_at').first()
            if latest_test_suite and latest_test_suite.api_test_suite_id:
                verify_headers = {
                    'accept': 'application/json',
                    'X-Service-Name': 'agent-service',
                    'Authorization': 'Basic YWRtaW46YWRtaW4='
                }
                verify_url = f"{GET_TEST_CASES_ENDPOINT}/{latest_test_suite.api_test_suite_id}"
                
                if DEBUG:
                    print(f"Verification URL: {verify_url}")
                
                # Wait and retry verification (backend might need time to process async update)
                import time
                execute_status_map = {}
                max_retries = 5  # Try up to 5 times
                initial_delay = 1.0  # Start with 1 second
                max_delay = 3.0  # Max 3 seconds between retries
                
                for retry in range(max_retries):
                    if retry > 0:
                        # Exponential backoff: 1s, 2s, 3s, 3s, 3s
                        delay = min(initial_delay * retry, max_delay)
                        if DEBUG:
                            print(f"  Retry {retry}/{max_retries-1}: Waiting {delay}s before checking...")
                        time.sleep(delay)
                    
                    verify_response = requests.get(verify_url, headers=verify_headers, timeout=30, verify=False)
                    
                    if verify_response.status_code == 200:
                        verify_data = verify_response.json()
                        verify_result = verify_data.get('result', {})
                        if verify_result.get('code', []) == ['0000']:
                            verify_test_cases = verify_data.get('data', {}).get('test_cases', [])
                            
                            # Check execute status for selected test cases
                            execute_status_map = {}
                            for tc in verify_test_cases:
                                tc_id = tc.get('id')
                                tc_execute = tc.get('execute', False)
                                if tc_id in selected_test_cases:
                                    execute_status_map[tc_id] = tc_execute
                            
                            # Check if all selected test cases have execute=True
                            all_execute_true = all(execute_status_map.values()) if execute_status_map else False
                            
                            if DEBUG:
                                true_count = sum(1 for v in execute_status_map.values() if v is True)
                                false_count = sum(1 for v in execute_status_map.values() if v is False)
                                print(f"  Attempt {retry + 1}: Execute=True: {true_count}, Execute=False: {false_count}")
                            
                            # If all are True, we're done
                            if all_execute_true:
                                if DEBUG:
                                    print(f"  ✓ All test cases have execute=True!")
                                break
                        else:
                            if DEBUG:
                                print(f"  Attempt {retry + 1}: API returned error code")
                    else:
                        if DEBUG:
                            print(f"  Attempt {retry + 1}: HTTP {verify_response.status_code}")
                
                if DEBUG:
                    print(f"\nVerification Results (after {max_retries} attempts):")
                    print(f"  Total test cases checked: {len(execute_status_map)}")
                    true_count = sum(1 for v in execute_status_map.values() if v is True)
                    false_count = sum(1 for v in execute_status_map.values() if v is False)
                    print(f"  Execute=True: {true_count}")
                    print(f"  Execute=False: {false_count}")
                    
                    if false_count > 0:
                        print(f"  ⚠ WARNING: {false_count} test case(s) still have execute=False!")
                        print(f"  This might indicate:")
                        print(f"    1. Backend API needs more time to process (async)")
                        print(f"    2. Backend API has a bug")
                        print(f"    3. Payload format might be incorrect")
                        for tc_id, exec_status in execute_status_map.items():
                            if not exec_status:
                                print(f"    - {tc_id}: execute={exec_status}")
                
                # Prepare verification info for response
                if execute_status_map:
                    verification_info = {
                        'verified': True,
                        'execute_true_count': sum(1 for v in execute_status_map.values() if v is True),
                        'execute_false_count': sum(1 for v in execute_status_map.values() if v is False),
                        'execute_status': execute_status_map,
                        'all_execute_true': all(execute_status_map.values())
                    }
                else:
                    verification_info = {
                        'verified': False,
                        'error': 'Failed to verify: Could not retrieve test cases'
                    }
                    if DEBUG:
                        print(f"Verification failed: Could not retrieve test cases")
            else:
                verification_info = {
                    'verified': False,
                    'error': 'No test suite found for verification'
                }
                if DEBUG:
                    print(f"Verification skipped: No test suite found")
        except Exception as verify_error:
            verification_info = {
                'verified': False,
                'error': f'Verification error: {str(verify_error)}'
            }
            if DEBUG:
                print(f"Verification error: {verify_error}")
                import traceback
                print(traceback.format_exc())
        
        if DEBUG:
            print(f"\n{'='*60}")
            print(f"=== SELECT TEST CASES - END (SUCCESS) ===")
            print(f"{'='*60}\n")
        
        # Return success response with verification info
        return JsonResponse({
            'success': True,
            'message': f'Đã chọn {len(selected_test_cases)} test case(s) thành công.',
            'selected_count': len(selected_test_cases),
            'selected_test_cases': selected_test_cases,
            'verification': verification_info if 'verification_info' in locals() else {'verified': False, 'error': 'Verification not performed'},
            'response': response_data
        })
        
    except json.JSONDecodeError as e:
        if DEBUG:
            print(f"\n--- JSON Decode Error ---")
            print(f"Error: {str(e)}")
            print(f"Request Body: {request.body}")
            print(f"\n{'='*60}")
            print(f"=== SELECT TEST CASES - END (JSON ERROR) ===")
            print(f"{'='*60}\n")
        return JsonResponse({
            'success': False,
            'message': 'Invalid JSON data in request'
        }, status=400)
    except requests.exceptions.RequestException as e:
        if DEBUG:
            print(f"\n--- API Request Error ---")
            print(f"Error: {str(e)}")
            print(f"\n{'='*60}")
            print(f"=== SELECT TEST CASES - END (API ERROR) ===")
            print(f"{'='*60}\n")
        return JsonResponse({
            'success': False,
            'message': f'Lỗi kết nối API: {str(e)}'
        }, status=500)
    except Exception as e:
        if DEBUG:
            print(f"\n{'='*60}")
            print(f"=== SELECT TEST CASES - EXCEPTION ===")
            print(f"Error Type: {type(e).__name__}")
            print(f"Error Message: {str(e)}")
            import traceback
            print(f"\nFull Traceback:")
            print(traceback.format_exc())
            print(f"{'='*60}")
            print(f"=== SELECT TEST CASES - END (EXCEPTION) ===")
            print(f"{'='*60}\n")
        return JsonResponse({
            'success': False,
            'message': f'Unexpected error: {str(e)}'
        }, status=500)


@login_required
@require_http_methods(["GET"])
def get_test_suite_id(request, project_uuid):
    """Get test suite ID from database for the project"""
    project = get_object_or_404(UserProject, uuid=project_uuid, user=request.user)
    
    try:
        if DEBUG:
            print(f"\n{'='*60}")
            print(f"=== GET TEST SUITE ID - START ===")
            print(f"{'='*60}")
            print(f"Project UUID: {project_uuid}")
            print(f"User: {request.user}")
        
        # Get the most recent test suite for this project
        latest_test_suite = ProjectTestSuite.objects.filter(project=project).order_by('-created_at').first()
        
        if latest_test_suite:
            # Ưu tiên dùng api_test_suite_id nếu có, nếu không thì dùng uuid
            test_suite_id = latest_test_suite.api_test_suite_id or str(latest_test_suite.uuid)
            if DEBUG:
                print(f"\n--- Test Suite Found ---")
                print(f"Test Suite UUID (DB): {latest_test_suite.uuid}")
                print(f"API Test Suite ID: {latest_test_suite.api_test_suite_id}")
                print(f"Final Test Suite ID (used): {test_suite_id}")
                print(f"Test Suite Name: {latest_test_suite.test_suite_name}")
                print(f"Created At: {latest_test_suite.created_at}")
                print(f"\n{'='*60}")
                print(f"=== GET TEST SUITE ID - END (SUCCESS) ===")
                print(f"{'='*60}\n")
            return JsonResponse({
                'success': True,
                'test_suite_id': test_suite_id,
                'test_suite_name': latest_test_suite.test_suite_name,
                'message': 'Đã lấy test_suite_id từ database thành công.'
            })
        else:
            if DEBUG:
                print(f"\n--- No Test Suite Found ---")
                print(f"Project has {ProjectTestSuite.objects.filter(project=project).count()} test suites")
                print(f"\n{'='*60}")
                print(f"=== GET TEST SUITE ID - END (NOT FOUND) ===")
                print(f"{'='*60}\n")
            return JsonResponse({
                'success': False,
                'message': 'Không tìm thấy test suite trong database. Vui lòng đảm bảo test cases đã được generate.'
            }, status=404)
        
    except Exception as e:
        if DEBUG:
            print(f"\n{'='*60}")
            print(f"=== GET TEST SUITE ID - EXCEPTION ===")
            print(f"Error Type: {type(e).__name__}")
            print(f"Error Message: {str(e)}")
            import traceback
            print(f"\nFull Traceback:")
            print(traceback.format_exc())
            print(f"{'='*60}")
            print(f"=== GET TEST SUITE ID - END (EXCEPTION) ===")
            print(f"{'='*60}\n")
        return JsonResponse({
            'success': False,
            'message': f'Unexpected error: {str(e)}'
        }, status=500)


@login_required
@require_http_methods(["POST"])
def execute_test_suite(request, project_uuid):
    """Execute test suite and return test_suite_report_id"""
    project = get_object_or_404(UserProject, uuid=project_uuid, user=request.user)
    
    try:
        # Parse request body
        if DEBUG:
            print(f"\n{'='*60}")
            print(f"=== EXECUTE TEST SUITE - START ===")
            print(f"{'='*60}")
            print(f"Request Body (raw): {request.body}")
        
        data = json.loads(request.body) if request.body else {}
        test_suite_id = data.get('test_suite_id')
        
        if DEBUG:
            print(f"\n--- Request Parsed ---")
            print(f"Project UUID: {project_uuid}")
            print(f"User: {request.user}")
            print(f"Test Suite ID: {test_suite_id}")
            print(f"Full Request Data: {json.dumps(data, indent=2, ensure_ascii=False)}")
        
        if not test_suite_id:
            if DEBUG:
                print(f"\n--- ERROR: No test_suite_id provided ---")
                print(f"\n{'='*60}")
                print(f"=== EXECUTE TEST SUITE - END (MISSING ID) ===")
                print(f"{'='*60}\n")
            return JsonResponse({
                'success': False,
                'message': 'test_suite_id là bắt buộc.'
            }, status=400)
        
        # Prepare payload according to API specification
        payload = {
            'test_suite_id': test_suite_id
        }
        
        headers = {
            'Content-Type': 'application/json',
            'accept': 'application/json',
            'X-Service-Name': 'agent-service',
            'Authorization': 'Basic YWRtaW46YWRtaW4='
        }
        
        if DEBUG:
            print(f"\n--- API Call Preparation ---")
            print(f"Endpoint: {EXECUTE_TEST_SUITE_ENDPOINT}")
            print(f"Payload: {json.dumps(payload, indent=2, ensure_ascii=False)}")
            print(f"Headers: {json.dumps({k: v for k, v in headers.items() if k != 'Authorization'}, indent=2, ensure_ascii=False)}")
            print(f"Authorization: {'present' if 'Authorization' in headers else 'not present'}")
        
        # Call API endpoint
        success, response_data, error_msg = call_api_with_retry(
            url=EXECUTE_TEST_SUITE_ENDPOINT,
            method='POST',
            headers=headers,
            json_data=payload,
            max_retries=2,
            retry_delay=2
        )
        
        if DEBUG:
            print(f"\n--- API Response ---")
            print(f"Success: {success}")
            if success:
                print(f"Response Data Type: {type(response_data)}")
                print(f"Response Data: {json.dumps(response_data, indent=2, ensure_ascii=False)}")
            else:
                print(f"Error Message: {error_msg}")
            print(f"{'='*60}\n")
        
        if success:
            # Extract test_suite_report_id from response
            # Response format: {"result": {...}, "data": {"test_suite_report_id": "..."}}
            test_suite_report_id = None
            data_response = response_data.get('data', {})
            
            if DEBUG:
                print(f"\n--- Extracting test_suite_report_id ---")
                print(f"Response Data: {response_data}")
                print(f"Data Response: {data_response}")
                print(f"Data Response Type: {type(data_response)}")
                print(f"Full Response Keys: {list(response_data.keys()) if isinstance(response_data, dict) else 'N/A'}")
            
            # Check various possible locations for test_suite_report_id
            if isinstance(data_response, dict):
                test_suite_report_id = data_response.get('test_suite_report_id')
                if DEBUG:
                    print(f"From data_response dict:")
                    print(f"  - test_suite_report_id: {data_response.get('test_suite_report_id')}")
                    print(f"  - All keys: {list(data_response.keys()) if isinstance(data_response, dict) else 'N/A'}")
            elif isinstance(data_response, str):
                # Sometimes data might be a string ID
                test_suite_report_id = data_response
                if DEBUG:
                    print(f"From data_response string: {test_suite_report_id}")
            
            # Also check at root level
            if not test_suite_report_id:
                test_suite_report_id = response_data.get('test_suite_report_id')
                if DEBUG:
                    print(f"From root level:")
                    print(f"  - test_suite_report_id: {response_data.get('test_suite_report_id')}")
            
            if DEBUG:
                print(f"\n--- Final test_suite_report_id ---")
                print(f"Extracted test_suite_report_id: {test_suite_report_id}")
            
            if test_suite_report_id:
                # Save report to database
                try:
                    # Try to find test_suite by api_test_suite_id
                    test_suite = None
                    if test_suite_id:
                        test_suite = ProjectTestSuite.objects.filter(
                            project=project,
                            api_test_suite_id=test_suite_id
                        ).first()
                    
                    # Create TestSuiteReport record
                    TestSuiteReport.objects.create(
                        project=project,
                        test_suite=test_suite,
                        test_suite_report_id=test_suite_report_id,
                        api_test_suite_id=test_suite_id or '',
                        status='running'
                    )
                    if DEBUG:
                        print(f"\n--- Saved TestSuiteReport to database ---")
                        print(f"Report ID: {test_suite_report_id}")
                        print(f"Project: {project.project_name}")
                        print(f"Test Suite: {test_suite.test_suite_name if test_suite else 'None'}")
                except Exception as e:
                    if DEBUG:
                        print(f"\n--- Error saving TestSuiteReport ---")
                        print(f"Error: {str(e)}")
                    # Don't fail the request if saving report fails
                    pass
                
                response_json = {
                    'success': True,
                    'message': 'Đã khởi động chạy test suite thành công.',
                    'test_suite_report_id': test_suite_report_id,
                    'response': response_data
                }
                if DEBUG:
                    print(f"\n--- Response JSON with test_suite_report_id ---")
                    print(f"Response JSON: {json.dumps(response_json, indent=2, ensure_ascii=False)}")
                    print(f"\n{'='*60}")
                    print(f"=== EXECUTE TEST SUITE - END (SUCCESS) ===")
                    print(f"{'='*60}\n")
                return JsonResponse(response_json)
            else:
                # Try to find test_suite_report_id in other possible locations
                if 'test_suite_report_id' in response_data:
                    test_suite_report_id = response_data.get('test_suite_report_id')
                    if DEBUG:
                        print(f"\n--- Found test_suite_report_id at root level ---")
                        print(f"test_suite_report_id: {test_suite_report_id}")
                    
                    # Save report to database
                    try:
                        # Try to find test_suite by api_test_suite_id
                        test_suite = None
                        if test_suite_id:
                            test_suite = ProjectTestSuite.objects.filter(
                                project=project,
                                api_test_suite_id=test_suite_id
                            ).first()
                        
                        # Create TestSuiteReport record
                        TestSuiteReport.objects.create(
                            project=project,
                            test_suite=test_suite,
                            test_suite_report_id=test_suite_report_id,
                            api_test_suite_id=test_suite_id or '',
                            status='running'
                        )
                        if DEBUG:
                            print(f"\n--- Saved TestSuiteReport to database (root level) ---")
                            print(f"Report ID: {test_suite_report_id}")
                    except Exception as e:
                        if DEBUG:
                            print(f"\n--- Error saving TestSuiteReport (root level) ---")
                            print(f"Error: {str(e)}")
                        # Don't fail the request if saving report fails
                        pass
                    
                    response_json = {
                        'success': True,
                        'message': 'Đã khởi động chạy test suite thành công.',
                        'test_suite_report_id': test_suite_report_id,
                        'response': response_data
                    }
                    if DEBUG:
                        print(f"\n--- Response JSON with test_suite_report_id (root level) ---")
                        print(f"Response JSON: {json.dumps(response_json, indent=2, ensure_ascii=False)}")
                        print(f"\n{'='*60}")
                        print(f"=== EXECUTE TEST SUITE - END (SUCCESS - ROOT LEVEL) ===")
                        print(f"{'='*60}\n")
                    return JsonResponse(response_json)
                else:
                    if DEBUG:
                        print(f"\n--- WARNING: No test_suite_report_id found ---")
                        print(f"Response structure:")
                        print(f"  - result: {response_data.get('result', 'N/A')}")
                        print(f"  - data: {response_data.get('data', 'N/A')}")
                        print(f"  - All keys: {list(response_data.keys()) if isinstance(response_data, dict) else 'N/A'}")
                        print(f"\n{'='*60}")
                        print(f"=== EXECUTE TEST SUITE - END (NO REPORT ID) ===")
                        print(f"{'='*60}\n")
                    return JsonResponse({
                        'success': False,
                        'message': 'Không tìm thấy test_suite_report_id trong response.',
                        'response': response_data
                    }, status=400)
        else:
            if DEBUG:
                print(f"\n--- API Call Failed ---")
                print(f"Error Message: {error_msg}")
                print(f"\n{'='*60}")
                print(f"=== EXECUTE TEST SUITE - END (API FAILED) ===")
                print(f"{'='*60}\n")
            return JsonResponse({
                'success': False,
                'message': f'Không thể chạy test suite: {error_msg}'
            }, status=500)
        
    except json.JSONDecodeError as e:
        if DEBUG:
            print(f"\n--- JSON Decode Error ---")
            print(f"Error: {str(e)}")
            print(f"Request Body: {request.body}")
            print(f"\n{'='*60}")
            print(f"=== EXECUTE TEST SUITE - END (JSON ERROR) ===")
            print(f"{'='*60}\n")
        return JsonResponse({
            'success': False,
            'message': 'Invalid JSON data in request'
        }, status=400)
    except Exception as e:
        if DEBUG:
            print(f"\n{'='*60}")
            print(f"=== EXECUTE TEST SUITE - EXCEPTION ===")
            print(f"Error Type: {type(e).__name__}")
            print(f"Error Message: {str(e)}")
            import traceback
            print(f"\nFull Traceback:")
            print(traceback.format_exc())
            print(f"{'='*60}")
            print(f"=== EXECUTE TEST SUITE - END (EXCEPTION) ===")
            print(f"{'='*60}\n")
        return JsonResponse({
            'success': False,
            'message': f'Unexpected error: {str(e)}'
        }, status=500)


@login_required
@require_http_methods(["GET"])
def get_test_report(request, project_uuid, test_suite_report_id):
    """Get test suite report by test_suite_report_id"""
    project = get_object_or_404(UserProject, uuid=project_uuid, user=request.user)
    
    try:
        if DEBUG:
            print(f"=== GET TEST REPORT ===")
            print(f"Project UUID: {project_uuid}")
            print(f"Test Suite Report ID: {test_suite_report_id}")
            print(f"========================")
        
        headers = {
            'Content-Type': 'application/json',
            'accept': 'application/json',
            'X-Service-Name': 'agent-service',
            'Authorization': 'Basic YWRtaW46YWRtaW4='
        }
        
        # Call API endpoint
        url = f"{GET_TEST_REPORT_ENDPOINT}/{test_suite_report_id}"
        success, response_data, error_msg = call_api_with_retry(
            url=url,
            method='GET',
            headers=headers,
            max_retries=2,
            retry_delay=2
        )
        
        if DEBUG:
            print(f"=== GET TEST REPORT RESPONSE ===")
            print(f"Success: {success}")
            if success:
                print(f"Response Data: {response_data}")
            else:
                print(f"Error: {error_msg}")
            print(f"================================")
        
        if success:
            return JsonResponse({
                'success': True,
                'message': 'Đã lấy report thành công.',
                'data': response_data.get('data', {}),
                'result': response_data.get('result', {}),
                'response': response_data
            })
        else:
            return JsonResponse({
                'success': False,
                'message': f'Không thể lấy report: {error_msg}'
            }, status=500)
        
    except Exception as e:
        if DEBUG:
            print(f"=== GET TEST REPORT ERROR ===")
            print(f"Error: {str(e)}")
            import traceback
            print(traceback.format_exc())
            print(f"============================")
        return JsonResponse({
            'success': False,
            'message': f'Unexpected error: {str(e)}'
        }, status=500)

