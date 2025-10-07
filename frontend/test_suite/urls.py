from django.urls import path, include
from . import views

urlpatterns = [
    path('add/<uuid:project_uuid>/', views.test_suite_add, name='test_suite_add'),
    # path('edit/<uuid:test_suite_uuid>/', views.test_suite_edit, name='test_suite_edit'),
    # path('delete/<uuid:test_suite_uuid>/', views.test_suite_delete, name='test_suite_delete'),
    path('<uuid:test_suite_uuid>/', views.test_suite_detail, name='test_suite_detail'),
]