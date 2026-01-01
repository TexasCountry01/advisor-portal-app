from django.urls import path
from . import views
from . import views_pdf_template
from . import views_quick_submit
from . import views_submit_case

urlpatterns = [
    # Member views
    path('member/dashboard/', views.member_dashboard, name='member_dashboard'),
    path('member/submit/', views_submit_case.submit_case, name='case_submit'),  # Enhanced case submission
    path('api/calculate-rushed-fee/', views_submit_case.api_calculate_rushed_fee, name='api_calculate_rushed_fee'),
    
    # DEV ONLY - Form preview without authentication
    path('dev/form-preview/', views.form_preview, name='form_preview'),
    
    # Technician views
    path('technician/dashboard/', views.technician_dashboard, name='technician_dashboard'),
    
    # Admin views
    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    
    # Manager views
    path('manager/dashboard/', views.manager_dashboard, name='manager_dashboard'),
    
    # Shared views
    path('list/', views.case_list, name='case_list'),
    path('<int:pk>/', views.case_detail, name='case_detail'),
    path('<int:pk>/delete/', views.delete_case, name='delete_case'),
    path('<int:case_id>/reassign/', views.reassign_case, name='reassign_case'),
    path('<int:case_id>/take-ownership/', views.take_case_ownership, name='take_case_ownership'),
    path('<int:case_id>/submit-final/', views.submit_case_final, name='submit_case_final'),
    path('<int:case_id>/add-note/', views.add_case_note, name='add_case_note'),
    path('<int:case_id>/upload-report/', views.upload_case_report, name='upload_case_report'),
    
    # Reference PDF template with document upload
    path('<int:case_id>/fact-finder-template/', views_pdf_template.fact_finder_template, name='case_fact_finder'),
    path('<int:case_id>/view-fact-finder-pdf/', views_pdf_template.view_fact_finder_pdf, name='view_fact_finder_pdf'),
    path('document/<int:doc_id>/download/', views_pdf_template.download_document, name='download_document'),
    path('document/<int:doc_id>/delete/', views_pdf_template.delete_document, name='delete_document'),
    path('template/download/', views_pdf_template.download_template, name='download_template'),
    path('<int:case_id>/submit/', views_pdf_template.submit_case, name='submit_case'),
    path('<int:case_id>/save-draft/', views_pdf_template.save_case_draft, name='save_case_draft'),
    path('<int:case_id>/extract-pdf-fields/', views_pdf_template.extract_pdf_fields, name='extract_pdf_fields'),
]
