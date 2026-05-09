from django.contrib import admin
from .models import ReferenceClause


@admin.register(ReferenceClause)
class ReferenceClauseAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'subcategory', 'sort_order', 'is_active', 'updated_at')
    list_filter = ('is_active', 'category')
    search_fields = ('title', 'category', 'subcategory', 'body')
    list_editable = ('sort_order', 'is_active')
    ordering = ('sort_order', 'category', 'subcategory', 'title')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('category', 'subcategory', 'title', 'body')
        }),
        ('Options', {
            'fields': ('sort_order', 'is_active', 'created_at', 'updated_at')
        }),
    )
