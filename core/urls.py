from django.urls import path
from . import views
from . import views_reports
from . import views_audit

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile, name='profile'),
    path('system-settings/', views.system_settings, name='system_settings'),
    path('reports/', views_reports.view_reports, name='view_reports'),
    path('reports/export-csv/', views_reports.export_reports_csv, name='export_reports_csv'),
    # Audit Log URLs
    path('audit-log/', views_audit.view_audit_log, name='view_audit_log'),
    path('audit-log/<int:log_id>/', views_audit.audit_log_detail, name='audit_log_detail'),
    path('audit-log/export-csv/', views_audit.export_audit_log_csv, name='export_audit_log_csv'),
    path('cases/<int:case_id>/audit-trail/', views_audit.case_audit_trail, name='case_audit_trail'),
]
