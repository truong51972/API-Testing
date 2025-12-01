from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('library/', views.library, name='library'),
    path('reports/', views.reports, name='reports'),
    path('set-language/', views.set_language, name='set_language'),
]