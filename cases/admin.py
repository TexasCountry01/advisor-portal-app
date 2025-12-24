from django.contrib import admin
from django.utils.html import format_html
from .models import Case, CaseDocument, CaseReport, CaseNote, APICallLog, FederalFactFinder
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


@admin.register(FederalFactFinder)
class FederalFactFinderAdmin(admin.ModelAdmin):
    """Admin interface for Federal Fact Finder data"""
    
    list_display = [
        'case_id',
        'employee_name',
        'retirement_system',
        'employee_type',
        'created_at',
        'updated_at'
    ]
    
    list_filter = [
        'retirement_system',
        'employee_type',
        'retirement_type',
        'created_at',
    ]
    
    search_fields = [
        'employee_name',
        'case__external_case_id',
        'case__employee_first_name',
        'case__employee_last_name'
    ]
    
    readonly_fields = ['created_at', 'updated_at', 'total_tsp_balance', 'total_fegli_premium']
    
    fieldsets = (
        ('Case Information', {
            'fields': ('case', 'created_at', 'updated_at')
        }),
        ('Basic Information', {
            'fields': (
                'employee_name', 'employee_dob',
                'spouse_name', 'spouse_dob',
                'address', 'city', 'state', 'zip_code'
            )
        }),
        ('Retirement System & Employee Type', {
            'fields': (
                'retirement_system', 'csrs_offset_date', 'fers_transfer_date',
                'employee_type', 'leo_start_date', 'cbpo_on_date_7_6_2008',
                'firefighter_start_date', 'atc_start_date', 'foreign_service_start_date',
                'retirement_type', 'optional_offer_date'
            )
        }),
        ('Retirement Pay & Leave', {
            'fields': (
                'leave_scd', 'retirement_scd',
                'retirement_timing', 'retirement_age', 'retirement_date',
                'reduce_spousal_pension_protection', 'spousal_pension_reduction_reason',
                'has_court_order_dividing_benefits', 'court_order_details',
                'current_annual_salary', 'expects_highest_three_at_end', 'highest_salary_history',
                'sick_leave_hours', 'annual_leave_hours',
                'ss_benefit_at_62', 'ss_desired_start_age', 'ss_benefit_at_desired_age',
                'page1_notes'
            )
        }),
        ('Military Service - Active Duty', {
            'fields': (
                'has_active_duty', 'active_duty_start_date', 'active_duty_end_date',
                'active_duty_deposit_made', 'active_duty_amount_owed',
                'active_duty_interrupted_service', 'active_duty_lwop_start', 'active_duty_lwop_end',
                'active_duty_lwop_deposit_made',
                'active_duty_retired', 'active_duty_pension_amount',
                'active_duty_overseas_time_added', 'active_duty_overseas_time_amount',
                'active_duty_notes'
            ),
            'classes': ('collapse',)
        }),
        ('Military Service - Reserves', {
            'fields': (
                'has_reserves', 'reserves_start_date', 'reserves_end_date',
                'reserves_creditable_time_years', 'reserves_creditable_time_months', 'reserves_creditable_time_days',
                'reserves_deposit_made', 'reserves_amount_owed',
                'reserves_interrupted_service', 'reserves_lwop_start', 'reserves_lwop_end',
                'reserves_lwop_deposit_made',
                'reserves_retired', 'reserves_pension_amount', 'reserves_pension_start_age',
                'reserves_notes'
            ),
            'classes': ('collapse',)
        }),
        ('Military Service - Academy', {
            'fields': (
                'has_academy', 'academy_start_date', 'academy_end_date',
                'academy_deposit_made', 'academy_amount_owed',
                'academy_appears_on_sf50',
                'academy_notes'
            ),
            'classes': ('collapse',)
        }),
        ('Special Federal Service', {
            'fields': (
                'has_non_deduction_service', 'non_deduction_start_date', 'non_deduction_end_date',
                'non_deduction_deposit_made', 'non_deduction_amount_owed', 'non_deduction_notes',
                'has_break_in_service', 'break_original_start_date', 'break_original_end_date',
                'break_period_start_date', 'break_period_end_date',
                'break_took_refund', 'break_made_redeposit', 'break_amount_owed', 'break_notes',
                'has_part_time_service', 'part_time_start_date', 'part_time_end_date',
                'part_time_hours_per_week', 'part_time_contributed_to_retirement', 'part_time_notes',
                'other_service_history_notes', 'no_special_service'
            ),
            'classes': ('collapse',)
        }),
        ('FEGLI', {
            'fields': (
                'fegli_premium_line1', 'fegli_premium_line2', 'fegli_premium_line3', 'fegli_premium_line4',
                'total_fegli_premium',
                'fegli_five_year_requirement_met', 'fegli_keep_in_retirement',
                'fegli_sole_source', 'fegli_purpose',
                'fegli_dependent_children_ages',
                'fegli_notes'
            ),
            'classes': ('collapse',)
        }),
        ('FEHB', {
            'fields': (
                'fehb_health_premium', 'fehb_dental_premium', 'fehb_vision_premium', 'fehb_dental_vision_premium',
                'fehb_coverage_type',
                'fehb_five_year_requirement_met', 'fehb_keep_in_retirement',
                'fehb_spouse_reliant',
                'fehb_has_tricare', 'fehb_has_va', 'fehb_has_spouse_plan', 'fehb_has_private_plan',
                'fehb_notes'
            ),
            'classes': ('collapse',)
        }),
        ('FLTCIP', {
            'fields': (
                'fltcip_employee_premium', 'fltcip_spouse_premium', 'fltcip_other_premium',
                'fltcip_daily_benefit', 'fltcip_benefit_period', 'fltcip_inflation_protection',
                'fltcip_want_to_discuss',
                'fltcip_notes'
            ),
            'classes': ('collapse',)
        }),
        ('TSP - Planning', {
            'fields': (
                'tsp_use_for_income', 'tsp_use_for_fun_money', 'tsp_use_for_legacy', 'tsp_use_for_other',
                'tsp_retirement_goal_amount', 'tsp_amount_needed', 'tsp_need_asap', 'tsp_need_at_age',
                'tsp_sole_source_investing', 'tsp_sole_source_explanation',
                'tsp_retirement_plan',
                'tsp_took_in_service_withdrawal', 'tsp_withdrawal_financial_hardship', 'tsp_withdrawal_age_based'
            ),
            'classes': ('collapse',)
        }),
        ('TSP - Contributions & Loans', {
            'fields': (
                'tsp_traditional_contribution', 'tsp_roth_contribution',
                'tsp_general_loan_date', 'tsp_general_loan_balance', 'tsp_general_loan_repayment', 'tsp_general_loan_payoff_date',
                'tsp_residential_loan_date', 'tsp_residential_loan_balance', 'tsp_residential_loan_repayment', 'tsp_residential_loan_payoff_date'
            ),
            'classes': ('collapse',)
        }),
        ('TSP - Fund Balances', {
            'fields': (
                'total_tsp_balance',
                'tsp_g_fund_balance', 'tsp_f_fund_balance', 'tsp_c_fund_balance', 'tsp_s_fund_balance', 'tsp_i_fund_balance',
                'tsp_l_income_balance', 'tsp_l_2025_balance', 'tsp_l_2030_balance', 'tsp_l_2035_balance',
                'tsp_l_2040_balance', 'tsp_l_2045_balance', 'tsp_l_2050_balance', 'tsp_l_2055_balance',
                'tsp_l_2060_balance', 'tsp_l_2065_balance'
            ),
            'classes': ('collapse',)
        }),
        ('TSP - Fund Allocations', {
            'fields': (
                'tsp_g_fund_allocation', 'tsp_f_fund_allocation', 'tsp_c_fund_allocation', 'tsp_s_fund_allocation', 'tsp_i_fund_allocation',
                'tsp_l_income_allocation', 'tsp_l_2025_allocation', 'tsp_l_2030_allocation', 'tsp_l_2035_allocation',
                'tsp_l_2040_allocation', 'tsp_l_2045_allocation', 'tsp_l_2050_allocation', 'tsp_l_2055_allocation',
                'tsp_l_2060_allocation', 'tsp_l_2065_allocation'
            ),
            'classes': ('collapse',)
        }),
        ('TSP - Risk & Outcomes', {
            'fields': (
                'tsp_employee_risk_tolerance', 'tsp_spouse_risk_tolerance',
                'tsp_best_outcome', 'tsp_worst_outcome',
                'tsp_comments'
            ),
            'classes': ('collapse',)
        }),
        ('Additional Notes', {
            'fields': ('additional_notes',)
        }),
    )
    
    def case_id(self, obj):
        return obj.case.external_case_id
    case_id.short_description = 'Case ID'


