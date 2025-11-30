from django.urls import path
from . import views

urlpatterns = [
    path('', views.project_list, name='project_list'),
    path('add/', views.project_add, name='project_add'),
    path('edit/<uuid:project_uuid>/', views.project_edit, name='project_edit'),
    path('delete/<uuid:project_uuid>/', views.project_delete, name='project_delete'),
    path('<uuid:project_uuid>/', views.project_detail_by_uuid, name='project_detail_by_uuid'),
    path('document/<int:doc_id>/delete/', views.delete_document, name="delete_document"),
    
    # AI Processing URLs
    path('<uuid:project_uuid>/ai/start/', views.start_ai_processing, name='start_ai_processing'),
    path('<uuid:project_uuid>/ai/status/', views.check_ai_processing_status, name='check_ai_processing_status'),
    path('<uuid:project_uuid>/ai/test/', views.test_api_integration, name='test_api_integration'),
    path('<uuid:project_uuid>/sections/', views.section_selection_view, name='section_selection'),
    path('<uuid:project_uuid>/sections/json/', views.get_sections_json, name='get_sections_json'),
    path('<uuid:project_uuid>/sections/update/', views.update_section_selection, name='update_section_selection'),
    path('<uuid:project_uuid>/preprocessed-document/<str:doc_id>/delete/', views.delete_preprocessed_document, name='delete_preprocessed_document'),
    path('<uuid:project_uuid>/test-suite/create/', views.create_test_suite_from_sections, name='create_test_suite_from_sections'),
    path('<uuid:project_uuid>/annotate-fr/', views.get_fr_infors, name='annotate_fr_api'),
    path('<uuid:project_uuid>/select-fr/', views.select_fr_info, name='select_fr_info'),
    
    # Test Case Generation URLs
    path('<uuid:project_uuid>/test-cases/check/', views.check_test_suite_exists, name='check_test_suite_exists'),
    path('<uuid:project_uuid>/test-cases/generate/', views.generate_test_cases, name='generate_test_cases'),
    path('<uuid:project_uuid>/test-cases/status/', views.check_test_case_status, name='check_test_case_status'),
    path('<uuid:project_uuid>/test-cases/', views.get_test_cases, name='get_test_cases'),
    path('<uuid:project_uuid>/test-cases/select/', views.select_test_cases, name='select_test_cases'),
    path('<uuid:project_uuid>/test-suite/get-id/', views.get_test_suite_id, name='get_test_suite_id'),
    path('<uuid:project_uuid>/test-suite/execute/', views.execute_test_suite, name='execute_test_suite'),
    path('<uuid:project_uuid>/test-report/<str:test_suite_report_id>/', views.get_test_report, name='get_test_report'),

    # API Integration URLs
    path('api/create/', views.api_create_project, name='api_create_project'),
    path('api/all/', views.api_get_all_projects, name='api_get_all_projects'),
    path('api/delete/<str:project_id>/', views.api_delete_project, name='api_delete_project'),

    # API Status URLs
    path('api/status/', views.api_status_view, name='api_status'),
    path('api/common/health', views.api_health_check, name='api_health_check'),
    path('api/server-status/', views.api_server_status, name='api_server_status'),

]
