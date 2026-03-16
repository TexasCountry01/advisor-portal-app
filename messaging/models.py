from django.db import models
from django.conf import settings


class Conversation(models.Model):
    """
    A general-question thread between a member and staff.
    Completely separate from cases — lives in the Messages area.
    """
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('closed', 'Closed'),
    ]

    subject = models.CharField(max_length=255)
    started_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='started_conversations',
    )
    is_urgent = models.BooleanField(default=False)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='open')
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_conversations',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='closed_conversations',
    )

    class Meta:
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['started_by', '-updated_at']),
            models.Index(fields=['status', '-updated_at']),
            models.Index(fields=['assigned_to', 'status']),
        ]

    def __str__(self):
        return f"{self.subject} (by {self.started_by})"


class Message(models.Model):
    """An individual message within a conversation."""
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='messages',
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='general_messages',
    )
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['conversation', 'created_at']),
        ]

    def __str__(self):
        return f"Message by {self.author} on {self.conversation.subject}"


class MessageReadStatus(models.Model):
    """
    Tracks which users have NOT yet read a message.
    Record exists = unread.  Deleted when the user views the conversation.
    Same pattern as cases.UnreadMessage.
    """
    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name='unread_by',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='unread_general_messages',
    )
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='unread_statuses',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [['message', 'user']]
        indexes = [
            models.Index(fields=['user', 'conversation']),
            models.Index(fields=['user', '-created_at']),
        ]

    def __str__(self):
        return f"Unread: {self.user} on {self.conversation.subject}"
