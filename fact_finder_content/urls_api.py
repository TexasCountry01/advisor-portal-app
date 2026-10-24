from django.urls import path

from . import views_api

urlpatterns = [
    path('resolve-content/', views_api.resolve_content, name='fact_finder_resolve_content'),
    path('resolve-content/v2/', views_api.resolve_content_v2, name='fact_finder_resolve_content_v2'),
]
