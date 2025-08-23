from django.urls import path
from . import views

urlpatterns = [
    path('', views.testcase_history, name='testcase_history'),
    # path('add/', views.TestCaseHistoryView.as_view(), name='add_testcase_history'),
]

