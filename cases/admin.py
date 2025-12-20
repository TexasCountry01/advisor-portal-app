from django.contrib import admin
from .models import Case, CaseDocument, CaseReport, CaseNote


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
        'assigned_to',
        'date_submitted',
        'date_completed'
    ]
    
    list_filter = [
        'status', 
        'urgency', 
        'tier',
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
    
    readonly_fields = ['external_case_id', 'date_submitted', 'created_at', 'updated_at']
    
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

