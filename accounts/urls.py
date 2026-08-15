from django.urls import path
from . import views
from . import views_sso
from . import views_webhook

urlpatterns = [
    # ========================================================================
    # SSO (WP Fusion / miniOAuth OAuth2)
    # ========================================================================
    path('sso/login/', views_sso.sso_login, name='sso_login'),
    path('sso/callback/', views_sso.sso_callback, name='sso_callback'),

    # ========================================================================
    # WP Webhook (real-time profile sync from WordPress)
    # ========================================================================
    path('api/wp-webhook/', views_webhook.wp_webhook, name='wp_webhook'),

    path('manage-users/', views.manage_users, name='manage_users'),
    path('edit-user-role/<int:user_id>/', views.edit_user_role, name='edit_user_role'),
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
    
    # ----------------------------------------------------------------
    # DEPRECATED: Old DelegateAccess-based routes (replaced by MemberDelegate
    # model + delegate_management view). Routes commented out to prevent
    # accidental use. View functions and models kept for migration compat.
    # See: /accounts/delegate-management/ for current delegate management.
    # ----------------------------------------------------------------
    # path(
    #     'members/<int:member_id>/delegate/add/',
    #     views.member_delegate_add,
    #     name='member_delegate_add'
    # ),
    # path(
    #     'delegates/<int:delegate_id>/edit/',
    #     views.member_delegate_edit,
    #     name='member_delegate_edit'
    # ),
    # path(
    #     'delegates/<int:delegate_id>/revoke/',
    #     views.member_delegate_revoke,
    #     name='member_delegate_revoke'
    # ),
    
    # Credit allowance management
    path(
        'members/<int:member_id>/credits/<int:fiscal_year>/q<int:quarter>/edit/',
        views.member_credit_allowance_edit,
        name='member_credit_allowance_edit'
    ),
    
    # ========================================================================
    # DELEGATE MANAGEMENT (Member-to-Delegate assignments)
    # ========================================================================
    path(
        'delegate-management/',
        views.delegate_management,
        name='delegate_management'
    ),
    path(
        'delegate-management/toggle-email/<int:assignment_id>/',
        views.toggle_delegate_email,
        name='toggle_delegate_email'
    ),
    path(
        'delegate-requests/<int:request_id>/process/',
        views.process_delegate_request,
        name='process_delegate_request'
    ),
    
    # ========================================================================
    # DEPRECATED: WORKSHOP DELEGATE MANAGEMENT URLS
    # ========================================================================
    # Replaced by MemberDelegate model + delegate_management view.
    # Routes commented out. View functions and models kept for migration compat.
    # See: /accounts/delegate-management/ for current delegate management.
    # ========================================================================
    # path(
    #     'workshop-delegates/',
    #     views.workshop_delegate_list,
    #     name='workshop_delegate_list'
    # ),
    # path(
    #     'workshop-delegates/add/',
    #     views.workshop_delegate_add,
    #     name='workshop_delegate_add'
    # ),
    # path(
    #     'workshop-delegates/<int:delegate_id>/edit/',
    #     views.workshop_delegate_edit,
    #     name='workshop_delegate_edit'
    # ),
    # path(
    #     'workshop-delegates/<int:delegate_id>/revoke/',
    #     views.workshop_delegate_revoke,
    #     name='workshop_delegate_revoke'
    # ),
]
