from django.urls import path

from . import views

app_name = 'fact_finder_content'

urlpatterns = [
    # Canonical entry point (also reached via the Admin Dashboard's "Fact Finder
    # Content" button, which reverses this same name and is therefore unaffected
    # by this reassignment). Phase 2C-2: now serves the PDF-ordered preview
    # (views.pdf_order_preview) instead of the original alphabetical list —
    # reusing that view directly, not a duplicate copy of its rendering logic.
    path('', views.pdf_order_preview, name='content_list'),
    # Kept as a second name for the same view/path pattern, for backward
    # compatibility with links/bookmarks/tests from Phases 2B/2C-1 that
    # reference this name directly.
    path('pdf-order-preview/', views.pdf_order_preview, name='pdf_order_preview'),
    # Temporary legacy route for the original alphabetical-by-label list (the
    # same view/template that used to be canonical). Admin-only (same
    # `_require_admin` check as every other route here), not linked from the
    # Admin Dashboard or from the new interface's normal navigation — reachable
    # only by an administrator who knows this URL. Not deleted per this phase's
    # explicit instruction to preserve it as a temporary fallback.
    path('legacy-list/', views.content_list, name='legacy_content_list'),
    path('<int:block_id>/', views.content_block_detail, name='content_block_detail'),
]
