from django.urls import path

from . import views

app_name = 'fact_finder_content'

urlpatterns = [
    path('', views.content_list, name='content_list'),
    path('<int:block_id>/', views.content_block_detail, name='content_block_detail'),
]
