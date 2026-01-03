from django.urls import path
from . import views
from . import views_reports

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile, name='profile'),
    path('system-settings/', views.system_settings, name='system_settings'),
    path('reports/', views_reports.view_reports, name='view_reports'),
    path('reports/export-csv/', views_reports.export_reports_csv, name='export_reports_csv'),
]
