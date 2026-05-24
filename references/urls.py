from django.urls import path
from . import views

app_name = 'references'

urlpatterns = [
    path('api/search/', views.search_clauses, name='search'),
    path('api/featured/', views.featured_clauses, name='featured'),
    path('api/categories/', views.categories_list, name='categories'),
    path('api/clauses/', views.clauses_by_category, name='clauses_by_category'),
    path('api/clause/<int:clause_id>/', views.clause_detail, name='clause_detail'),
    path('api/user-searches/', views.user_searches_get, name='user_searches_get'),
    path('api/user-searches/save/', views.user_searches_save, name='user_searches_save'),
    path('api/user-searches/clear/', views.user_searches_clear, name='user_searches_clear'),
    path('reimport/', views.reimport_view, name='reimport'),
]
