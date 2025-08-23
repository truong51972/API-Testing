from django.urls import path
from . import views

urlpatterns = [
    path('', views.project_list, name='project_list'),
    path('add/', views.project_add, name='project_add'),
    path('edit/<uuid:project_uuid>/', views.project_edit, name='project_edit'),
    path('delete/<uuid:project_uuid>/', views.project_delete, name='project_delete'),
    path('<uuid:project_uuid>/', views.project_detail_by_uuid, name='project_detail_by_uuid'),
]
