from django.urls import path
from . import views

urlpatterns = [
    # Member views
    path('member/dashboard/', views.member_dashboard, name='member_dashboard'),
    path('member/submit/', views.case_submit, name='case_submit'),
    
    # Technician views
    path('technician/workbench/', views.technician_workbench, name='technician_workbench'),
    
    # Shared views
    path('list/', views.case_list, name='case_list'),
    path('<int:pk>/', views.case_detail, name='case_detail'),
]
