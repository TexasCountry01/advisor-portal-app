from django.urls import path
from . import views

app_name = 'messaging'

urlpatterns = [
    path('', views.inbox, name='inbox'),
    path('new/', views.new_conversation, name='new_conversation'),
    path('broadcast/', views.broadcast_message, name='broadcast'),
    path('<int:pk>/', views.conversation_detail, name='conversation_detail'),
    path('<int:pk>/reply/', views.reply, name='reply'),
    path('<int:pk>/claim/', views.claim_conversation, name='claim'),
    path('<int:pk>/close/', views.close_conversation, name='close'),
    path('<int:pk>/reopen/', views.reopen_conversation, name='reopen'),
    path('unread-count/', views.unread_count, name='unread_count'),
]
