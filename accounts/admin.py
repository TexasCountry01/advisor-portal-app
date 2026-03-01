from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, UserPreference, AuditLog, MemberDelegate


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Custom user admin with role and level fields"""
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Role & Permissions', {
            'fields': ('role', 'user_level', 'workshop_code', 'phone')
        }),
    )
    
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Role & Permissions', {
            'fields': ('role', 'user_level', 'workshop_code', 'phone')
        }),
    )
    
    list_display = ['username', 'email', 'first_name', 'last_name', 'role', 'user_level', 'is_active']
    list_filter = ['role', 'user_level', 'is_active', 'is_staff']
    search_fields = ['username', 'email', 'first_name', 'last_name', 'workshop_code']


@admin.register(UserPreference)
class UserPreferenceAdmin(admin.ModelAdmin):
    list_display = ['user', 'preference_key', 'updated_at']
    list_filter = ['preference_key']
    search_fields = ['user__username', 'preference_key']


@admin.register(MemberDelegate)
class MemberDelegateAdmin(admin.ModelAdmin):
    list_display = ['delegate', 'member', 'assigned_by', 'created_at']
    list_filter = ['created_at']
    search_fields = ['delegate__username', 'delegate__first_name', 'delegate__last_name',
                     'member__username', 'member__first_name', 'member__last_name']
    raw_id_fields = ['member', 'delegate', 'assigned_by']
    readonly_fields = ['created_at']


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'action', 'resource_type', 'resource_id', 'created_at']
    list_filter = ['action', 'resource_type', 'created_at']
    search_fields = ['user__username', 'action', 'resource_type']
    readonly_fields = ['user', 'action', 'resource_type', 'resource_id', 'details', 'ip_address', 'user_agent', 'created_at']
    date_hierarchy = 'created_at'

