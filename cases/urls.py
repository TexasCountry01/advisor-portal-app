from django.urls import path
from . import views
from . import views_pdf_template
from . import views_quick_submit
from . import views_submit_case

app_name = 'cases'

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
    path('<int:pk>/edit/', views.edit_case, name='edit_case'),
    path('<int:pk>/delete/', views.delete_case, name='delete_case'),
    path('<int:pk>/review/', views.case_review_for_acceptance, name='case_review_for_acceptance'),
    path('<int:pk>/accept/', views.accept_case, name='accept_case'),
    path('<int:pk>/reject/', views.reject_case, name='reject_case'),
    path('<int:case_id>/reassign/', views.reassign_case, name='reassign_case'),
    path('<int:case_id>/admin-take-ownership/', views.admin_take_ownership, name='admin_take_ownership'),
    path('<int:case_id>/take-ownership/', views.take_case_ownership, name='take_case_ownership'),
    path('<int:case_id>/adjust-credit/', views.adjust_case_credit, name='adjust_case_credit'),
    path('<int:pk>/save-report-notes/', views.save_report_notes, name='save_report_notes'),
    path('<int:pk>/download-notes-pdf/', views.generate_report_notes_pdf, name='generate_report_notes_pdf'),
    path('<int:pk>/edit-details/', views.edit_case_details, name='edit_case_details'),
    path('upload-image/', views.upload_image_for_notes, name='upload_image_for_notes'),
    path('credit-audit-trail/', views.credit_audit_trail, name='credit_audit_trail_report'),
    path('<int:case_id>/credit-audit-trail/', views.credit_audit_trail, name='credit_audit_trail'),
    path('<int:case_id>/submit-final/', views.submit_case_final, name='submit_case_final'),
    path('<int:case_id>/add-note/', views.add_case_note, name='add_case_note'),
    path('<int:case_id>/delete-note/<int:note_id>/', views.delete_case_note, name='delete_case_note'),
    path('<int:case_id>/upload-report/', views.upload_case_report, name='upload_case_report'),
    path('<int:case_id>/upload-tech-document/', views.upload_technician_document, name='upload_technician_document'),
    path('<int:case_id>/upload-member-document/', views.upload_member_document_to_completed_case, name='upload_member_document_completed'),
    path('<int:case_id>/resubmit/', views.resubmit_case, name='resubmit_case'),
    path('<int:case_id>/validate-completion/', views.validate_case_completion, name='validate_case_completion'),
    path('<int:case_id>/mark-completed/', views.mark_case_completed, name='mark_case_completed'),
    path('<int:case_id>/mark-incomplete/', views.mark_case_incomplete, name='mark_case_incomplete'),
    path('<int:case_id>/release-immediately/', views.release_case_immediately, name='release_case_immediately'),
    
    # View preference API
    path('api/view-preference/save/<str:view_type>/', views.save_view_preference, name='save_view_preference'),
    path('api/view-preference/get/', views.get_view_preference, name='get_view_preference'),
    
    # Column visibility API
    path('api/column-preference/save/', views.save_column_preference, name='save_column_preference'),
    path('api/column-config/<str:dashboard_name>/', views.get_column_config, name='get_column_config'),
    
    # Quality Review System
    path('review/queue/', views.review_queue, name='review_queue'),
    path('<int:case_id>/review/', views.review_case_detail, name='review_case_detail'),
    path('<int:case_id>/review/approve/', views.approve_case_review, name='approve_case_review'),
    path('<int:case_id>/review/request-revisions/', views.request_case_revisions, name='request_case_revisions'),
    path('<int:case_id>/review/correct/', views.correct_case_review, name='correct_case_review'),
    
    # Audit trails
    path('audit/', views.audit_log_dashboard, name='audit_log_dashboard'),
    path('<int:case_id>/audit-history/', views.case_audit_history, name='case_audit_history'),
    
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
