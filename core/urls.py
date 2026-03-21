from django.conf import settings
from django.urls import path
from . import views
from . import views_reports
from . import views_audit

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile, name='profile'),
    path('update-font-size/', views.update_font_size, name='update_font_size'),
    path('system-settings/', views.system_settings, name='system_settings'),
    path('beta-feedback/', views.submit_beta_feedback, name='submit_beta_feedback'),
    path('reports/', views_reports.view_reports, name='view_reports'),
    path('reports/export-csv/', views_reports.export_reports_csv, name='export_reports_csv'),
    path('reports/profeds-errors/', views_reports.profeds_error_tracking_report, name='profeds_error_tracking_report'),
    path('reports/beta-feedback/', views_reports.beta_feedback_report, name='beta_feedback_report'),
    # Audit Log URLs
    path('audit-log/', views_audit.view_audit_log, name='view_audit_log'),
    path('audit-log/<int:log_id>/', views_audit.audit_log_detail, name='audit_log_detail'),
    path('audit-log/export-csv/', views_audit.export_audit_log_csv, name='export_audit_log_csv'),
    path('cases/<int:case_id>/audit-trail/', views_audit.case_audit_trail, name='case_audit_trail'),
    # NEW: Audit Report URLs
    path('reports/activity-summary/', views_audit.activity_summary_report, name='activity_summary_report'),
    path('reports/user-activity/', views_audit.user_activity_report, name='user_activity_report'),
    path('reports/case-changes/', views_audit.case_change_history_report, name='case_change_history_report'),
    path('reports/quality-review-audit/', views_audit.quality_review_audit_report, name='quality_review_audit_report'),
    path('reports/system-events/', views_audit.system_event_audit_report, name='system_event_audit_report'),
]

# Data Sync routes — only available when ENABLE_DATA_SYNC=True in .env
if settings.ENABLE_DATA_SYNC:
    from . import views_data_sync
    urlpatterns += [
        path('data-sync/', views_data_sync.data_sync_panel, name='data_sync'),
        path('data-sync/authenticate/', views_data_sync.data_sync_authenticate, name='data_sync_authenticate'),
        path('data-sync/list-members/', views_data_sync.data_sync_list_members, name='data_sync_list_members'),
        path('data-sync/list-staff/', views_data_sync.data_sync_list_staff, name='data_sync_list_staff'),
        path('data-sync/list-cases/', views_data_sync.data_sync_list_cases, name='data_sync_list_cases'),
        path('data-sync/pull-member/', views_data_sync.data_sync_pull_member, name='data_sync_pull_member'),
        path('data-sync/pull-staff/', views_data_sync.data_sync_pull_staff, name='data_sync_pull_staff'),
        path('data-sync/pull-case/', views_data_sync.data_sync_pull_case, name='data_sync_pull_case'),
    ]
