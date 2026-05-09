from django.urls import path
from . import views

app_name = 'references'

urlpatterns = [
    path('api/search/', views.search_clauses, name='search'),
    path('reimport/', views.reimport_view, name='reimport'),
]
