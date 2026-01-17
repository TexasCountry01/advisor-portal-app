from django.urls import path
from . import views

urlpatterns = [
    path('manage-users/', views.manage_users, name='manage_users'),
    path('deactivate-user/<int:user_id>/', views.deactivate_user, name='deactivate_user'),
    path('reactivate-user/<int:user_id>/', views.reactivate_user, name='reactivate_user'),
    
    # ========================================================================
    # MEMBER PROFILE MANAGEMENT URLS
    # ========================================================================
    # These URLs are for Benefits Technicians to edit member profiles.
    # 
    # Pattern: /accounts/members/{member_id}/...
    # ========================================================================
    
    # Main member profile edit view (edit info, manage delegates, view credits)
    path(
        'members/<int:member_id>/edit/',
        views.member_profile_edit,
        name='member_profile_edit'
    ),
    
    # Delegate management
    path(
        'members/<int:member_id>/delegate/add/',
        views.member_delegate_add,
        name='member_delegate_add'
    ),
    path(
        'delegates/<int:delegate_id>/edit/',
        views.member_delegate_edit,
        name='member_delegate_edit'
    ),
    path(
        'delegates/<int:delegate_id>/revoke/',
        views.member_delegate_revoke,
        name='member_delegate_revoke'
    ),
    
    # Credit allowance management
    path(
        'members/<int:member_id>/credits/<int:fiscal_year>/q<int:quarter>/edit/',
        views.member_credit_allowance_edit,
        name='member_credit_allowance_edit'
    ),
]
