from django.urls import path
from . import views

urlpatterns = [
    # Member views
    path('member/dashboard/', views.member_dashboard, name='member_dashboard'),
    path('member/submit/', views.case_submit, name='case_submit'),
    
    # DEV ONLY - Form preview without authentication
    path('dev/form-preview/', views.form_preview, name='form_preview'),
    
    # Technician views
    path('technician/workbench/', views.technician_workbench, name='technician_workbench'),
    
    # Shared views
    path('list/', views.case_list, name='case_list'),
    path('<int:pk>/', views.case_detail, name='case_detail'),
    
    # File upload views
    path('<int:case_id>/upload-document/', views.upload_document, name='upload_document'),
    path('<int:case_id>/upload-report/', views.upload_report, name='upload_report'),
    path('<int:case_id>/add-note/', views.add_note, name='add_note'),
    
    # PDF viewing
    path('<int:case_id>/fact-finder-pdf/', views.view_fact_finder_pdf, name='view_fact_finder_pdf'),
]
