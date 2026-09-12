from django.contrib import admin

from .models import ContentBlockGroup, ContentBlock, ContentBlockVersion


@admin.register(ContentBlockGroup)
class ContentBlockGroupAdmin(admin.ModelAdmin):
    list_display = ('label', 'key', 'display_order')
    ordering = ('display_order',)


@admin.register(ContentBlock)
class ContentBlockAdmin(admin.ModelAdmin):
    list_display = ('label', 'key', 'group', 'is_active', 'updated_at')
    list_filter = ('group', 'is_active')
    search_fields = ('key', 'label')


@admin.register(ContentBlockVersion)
class ContentBlockVersionAdmin(admin.ModelAdmin):
    list_display = ('block', 'plan_year', 'status', 'created_by', 'published_at', 'updated_at')
    list_filter = ('status', 'plan_year', 'block__group')
    search_fields = ('block__key', 'block__label')
    readonly_fields = ('published_at', 'created_at', 'updated_at')
