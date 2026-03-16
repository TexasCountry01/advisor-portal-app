from django.contrib import admin
from .models import Conversation, Message, MessageReadStatus


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ('author', 'body', 'created_at')


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ['subject', 'started_by', 'is_urgent', 'status', 'assigned_to', 'created_at', 'updated_at']
    list_filter = ['status', 'is_urgent', 'created_at']
    search_fields = ['subject', 'started_by__username', 'started_by__first_name', 'started_by__last_name']
    raw_id_fields = ['started_by', 'assigned_to', 'closed_by']
    inlines = [MessageInline]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['conversation', 'author', 'created_at']
    list_filter = ['created_at']
    raw_id_fields = ['conversation', 'author']


@admin.register(MessageReadStatus)
class MessageReadStatusAdmin(admin.ModelAdmin):
    list_display = ['user', 'conversation', 'message', 'created_at']
    list_filter = ['created_at']
    raw_id_fields = ['message', 'user', 'conversation']
