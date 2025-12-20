from django.contrib import admin
from django.utils.html import format_html
from .models import Case, CaseDocument, CaseReport, CaseNote, APICallLog
from .services import benefits_api


@admin.register(Case)
class CaseAdmin(admin.ModelAdmin):
    """Admin interface for Case management"""
    
    list_display = [
        'external_case_id', 
        'workshop_code',
        'member', 
        'employee_full_name',
        'status', 
        'urgency',
        'api_sync_status_display',
        'assigned_to',
        'date_submitted',
        'date_completed'
    ]
    
    list_filter = [
        'status', 
        'urgency', 
        'tier',
        'api_sync_status',
        'date_submitted',
        'assigned_to'
    ]
    
    search_fields = [
        'external_case_id',
        'workshop_code',
        'employee_first_name',
        'employee_last_name',
        'client_email',
        'member__username',
        'member__email'
    ]
    
    readonly_fields = ['external_case_id', 'date_submitted', 'api_sync_status', 'api_synced_at', 'created_at', 'updated_at']
    
    actions = ['retry_api_sync']
    
    def api_sync_status_display(self, obj):
        """Colored display of API sync status"""
        colors = {
            'synced': 'green',
            'pending': 'orange',
            'failed': 'red',
        }
        color = colors.get(obj.api_sync_status, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_api_sync_status_display()
        )
    api_sync_status_display.short_description = 'API Sync'
    
    def retry_api_sync(self, request, queryset):
        """Admin action to retry failed API syncs"""
        from .services import submit_case_to_benefits_software
        
        failed_cases = queryset.filter(api_sync_status='failed')
        success_count = 0
        
        for case in failed_cases:
            success, case_id, error = submit_case_to_benefits_software(case)
            if success:
                success_count += 1
        
        self.message_user(
            request,
            f'Retry complete: {success_count} of {failed_cases.count()} cases successfully synced.'
        )
    retry_api_sync.short_description = 'Retry API sync for selected failed cases'
    
    fieldsets = (
        ('Case Information', {
            'fields': ('external_case_id', 'workshop_code', 'member')
        }),
        ('Employee Details', {
            'fields': ('employee_first_name', 'employee_last_name', 'client_email')
        }),
        ('Case Details', {
            'fields': ('num_reports_requested', 'urgency', 'status', 'tier')
        }),
        ('API Sync Status', {
            'fields': ('api_sync_status', 'api_synced_at'),
            'classes': ('collapse',)
        }),
        ('Assignment', {
            'fields': ('assigned_to', 'reviewed_by')
        }),
        ('Dates', {
            'fields': ('date_submitted', 'date_accepted', 'date_due', 'date_scheduled', 'date_completed')
        }),
        ('Reports', {
            'fields': ('report_notes',),
            'classes': ('collapse',)
        }),
        ('Notes', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    date_hierarchy = 'date_submitted'


@admin.register(CaseDocument)
class CaseDocumentAdmin(admin.ModelAdmin):
    list_display = ['original_filename', 'case', 'document_type', 'uploaded_by', 'uploaded_at', 'file_size']
    list_filter = ['document_type', 'uploaded_at']
    search_fields = ['original_filename', 'case__external_case_id', 'uploaded_by__username']
    readonly_fields = ['uploaded_at', 'file_size']
    date_hierarchy = 'uploaded_at'


@admin.register(CaseReport)
class CaseReportAdmin(admin.ModelAdmin):
    list_display = ['case', 'report_number', 'status', 'assigned_to', 'reviewed_by', 'completed_at']
    list_filter = ['status', 'created_at', 'completed_at']
    search_fields = ['case__external_case_id', 'assigned_to__username']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'created_at'


@admin.register(CaseNote)
class CaseNoteAdmin(admin.ModelAdmin):
    list_display = ['case', 'author', 'is_internal', 'created_at']
    list_filter = ['is_internal', 'created_at']
    search_fields = ['case__external_case_id', 'author__username', 'note']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'created_at'


@admin.register(APICallLog)
class APICallLogAdmin(admin.ModelAdmin):
    """Admin interface for API call logging and monitoring"""
    
    list_display = [
        'id',
        'case',
        'endpoint_short',
        'success_display',
        'attempt_number',
        'response_status_code',
        'created_at',
        'duration'
    ]
    
    list_filter = [
        'success',
        'response_status_code',
        'created_at',
        'attempt_number'
    ]
    
    search_fields = [
        'case__external_case_id',
        'endpoint',
        'error_message'
    ]
    
    readonly_fields = [
        'case',
        'endpoint',
        'request_payload',
        'response_status_code',
        'response_data',
        'success',
        'error_message',
        'attempt_number',
        'created_at',
        'completed_at',
        'duration'
    ]
    
    date_hierarchy = 'created_at'
    
    actions = ['retry_failed_calls']
    
    def endpoint_short(self, obj):
        """Display shortened endpoint URL"""
        if len(obj.endpoint) > 50:
            return obj.endpoint[:47] + '...'
        return obj.endpoint
    endpoint_short.short_description = 'Endpoint'
    
    def success_display(self, obj):
        """Colored display of success status"""
        if obj.success:
            return format_html('<span style="color: green; font-weight: bold;">✓ Success</span>')
        return format_html('<span style="color: red; font-weight: bold;">✗ Failed</span>')
    success_display.short_description = 'Status'
    
    def duration(self, obj):
        """Calculate and display call duration"""
        if obj.completed_at and obj.created_at:
            delta = obj.completed_at - obj.created_at
            return f"{delta.total_seconds():.2f}s"
        return "In progress..."
    duration.short_description = 'Duration'
    
    def retry_failed_calls(self, request, queryset):
        """Admin action to retry selected failed API calls"""
        from .services import submit_case_to_benefits_software
        
        failed_logs = queryset.filter(success=False)
        success_count = 0
        
        # Group by case to avoid duplicate retries
        cases = set(log.case for log in failed_logs)
        
        for case in cases:
            success, case_id, error = submit_case_to_benefits_software(case)
            if success:
                success_count += 1
        
        self.message_user(
            request,
            f'Retry complete: {success_count} of {len(cases)} cases successfully synced.'
        )
    retry_failed_calls.short_description = 'Retry failed API calls'
    
    fieldsets = (
        ('API Call Information', {
            'fields': ('case', 'endpoint', 'attempt_number')
        }),
        ('Request', {
            'fields': ('request_payload',),
            'classes': ('collapse',)
        }),
        ('Response', {
            'fields': ('response_status_code', 'response_data', 'success', 'error_message')
        }),
        ('Timing', {
            'fields': ('created_at', 'completed_at', 'duration')
        }),
    )

