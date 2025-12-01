from django.contrib import admin
from .models import TestSuiteReport

# Register your models here.
@admin.register(TestSuiteReport)
class TestSuiteReportAdmin(admin.ModelAdmin):
    list_display = ('test_suite_report_id', 'project', 'test_suite', 'status', 'executed_at', 'created_at')
    list_filter = ('status', 'executed_at', 'project')
    search_fields = ('test_suite_report_id', 'project__project_name', 'test_suite__test_suite_name')
    readonly_fields = ('uuid', 'created_at', 'executed_at')
    date_hierarchy = 'executed_at'
    
    fieldsets = (
        ('Thông tin cơ bản', {
            'fields': ('uuid', 'project', 'test_suite', 'test_suite_report_id', 'api_test_suite_id')
        }),
        ('Trạng thái', {
            'fields': ('status', 'executed_at', 'created_at')
        }),
    )
