from django.contrib import admin
from .models import ReferenceClause


@admin.register(ReferenceClause)
class ReferenceClauseAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'subcategory', 'sort_order', 'is_active', 'is_featured', 'updated_at')
    list_filter = ('is_active', 'is_featured', 'category')
    search_fields = ('title', 'category', 'subcategory', 'body')
    list_editable = ('sort_order', 'is_active', 'is_featured')
    ordering = ('sort_order', 'category', 'subcategory', 'title')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('category', 'subcategory', 'title', 'body')
        }),
        ('Options', {
            'fields': ('sort_order', 'is_active', 'is_featured', 'created_at', 'updated_at')
        }),
    )
