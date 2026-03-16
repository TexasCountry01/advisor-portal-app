import logging
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from .models import Conversation, Message, MessageReadStatus

logger = logging.getLogger(__name__)

STAFF_ROLES = ('technician', 'administrator', 'manager')


@login_required
def inbox(request):
    """
    Message inbox.
    Members see their own conversations.
    Staff see all open conversations (message queue).
    """
    user = request.user
    is_staff = user.role in STAFF_ROLES

    if is_staff:
        status_filter = request.GET.get('status', 'open')
        assigned_filter = request.GET.get('assigned')
        urgent_filter = request.GET.get('urgent')

        conversations = Conversation.objects.select_related(
            'started_by', 'assigned_to'
        ).order_by('-updated_at')

        if status_filter in ('open', 'closed'):
            conversations = conversations.filter(status=status_filter)

        if assigned_filter == 'mine':
            conversations = conversations.filter(assigned_to=user)
        elif assigned_filter == 'unassigned':
            conversations = conversations.filter(assigned_to__isnull=True)

        if urgent_filter == '1':
            conversations = conversations.filter(is_urgent=True)
    else:
        # Members see only their own conversations
        conversations = Conversation.objects.filter(
            started_by=user
        ).select_related('assigned_to').order_by('-updated_at')
        status_filter = request.GET.get('status', '')
        assigned_filter = None
        urgent_filter = None
        if status_filter in ('open', 'closed'):
            conversations = conversations.filter(status=status_filter)

    # Add unread count per conversation
    for convo in conversations:
        convo.unread_count = MessageReadStatus.objects.filter(
            conversation=convo, user=user
        ).count()
        # Attach latest message preview
        latest = convo.messages.order_by('-created_at').first()
        convo.latest_message = latest

    context = {
        'conversations': conversations,
        'is_staff': is_staff,
        'status_filter': status_filter,
        'assigned_filter': assigned_filter,
        'urgent_filter': urgent_filter,
    }
    return render(request, 'messaging/inbox.html', context)


@login_required
def conversation_detail(request, pk):
    """View and reply to a conversation."""
    user = request.user
    is_staff = user.role in STAFF_ROLES
    conversation = get_object_or_404(Conversation, pk=pk)

    # Permission: member can only see own conversations
    if not is_staff and conversation.started_by != user:
        return redirect('messaging:inbox')

    # Mark all messages in this conversation as read for the current user
    MessageReadStatus.objects.filter(conversation=conversation, user=user).delete()

    messages_list = conversation.messages.select_related('author').order_by('created_at')

    context = {
        'conversation': conversation,
        'messages': messages_list,
        'is_staff': is_staff,
    }
    return render(request, 'messaging/conversation_detail.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def new_conversation(request):
    """Member creates a new general question."""
    user = request.user

    if request.method == 'POST':
        subject = request.POST.get('subject', '').strip()
        body = request.POST.get('body', '').strip()
        is_urgent = request.POST.get('is_urgent') == '1'

        if not subject or not body:
            return render(request, 'messaging/new_conversation.html', {
                'error': 'Subject and message are required.',
                'subject': subject,
                'body': body,
                'is_urgent': is_urgent,
            })

        # Create conversation + first message
        conversation = Conversation.objects.create(
            subject=subject,
            started_by=user,
            is_urgent=is_urgent,
        )
        msg = Message.objects.create(
            conversation=conversation,
            author=user,
            body=body,
        )

        # Create unread records for all active staff
        from accounts.models import User as UserModel
        staff_users = UserModel.objects.filter(role__in=STAFF_ROLES, is_active=True)
        MessageReadStatus.objects.bulk_create([
            MessageReadStatus(message=msg, user=staff, conversation=conversation)
            for staff in staff_users
        ])

        logger.info(f'New conversation "{subject}" created by {user.username} (urgent={is_urgent})')
        return redirect('messaging:conversation_detail', pk=conversation.pk)

    return render(request, 'messaging/new_conversation.html')


@login_required
@require_http_methods(["POST"])
def reply(request, pk):
    """Add a reply to a conversation."""
    user = request.user
    is_staff = user.role in STAFF_ROLES
    conversation = get_object_or_404(Conversation, pk=pk)

    # Permission check
    if not is_staff and conversation.started_by != user:
        return JsonResponse({'error': 'Access denied'}, status=403)

    body = request.POST.get('body', '').strip()
    if not body:
        return JsonResponse({'error': 'Message cannot be empty'}, status=400)

    msg = Message.objects.create(
        conversation=conversation,
        author=user,
        body=body,
    )

    # Update conversation timestamp
    conversation.save()  # triggers auto_now on updated_at

    # If conversation was closed, reopen it
    if conversation.status == 'closed':
        conversation.status = 'open'
        conversation.closed_at = None
        conversation.closed_by = None
        conversation.save(update_fields=['status', 'closed_at', 'closed_by', 'updated_at'])

    # Create unread records for recipients
    if is_staff:
        # Staff replied — mark unread for the member who started it
        MessageReadStatus.objects.get_or_create(
            message=msg, user=conversation.started_by,
            defaults={'conversation': conversation}
        )
    else:
        # Member replied — mark unread for all active staff
        from accounts.models import User as UserModel
        staff_users = UserModel.objects.filter(role__in=STAFF_ROLES, is_active=True)
        MessageReadStatus.objects.bulk_create([
            MessageReadStatus(message=msg, user=staff, conversation=conversation)
            for staff in staff_users
        ], ignore_conflicts=True)

    logger.info(f'Reply on conversation {conversation.pk} by {user.username}')
    return redirect('messaging:conversation_detail', pk=conversation.pk)


@login_required
@require_http_methods(["POST"])
def claim_conversation(request, pk):
    """Staff claims/assigns a conversation to themselves."""
    user = request.user
    if user.role not in STAFF_ROLES:
        return JsonResponse({'error': 'Access denied'}, status=403)

    conversation = get_object_or_404(Conversation, pk=pk)
    conversation.assigned_to = user
    conversation.save(update_fields=['assigned_to', 'updated_at'])
    logger.info(f'Conversation {pk} claimed by {user.username}')
    return redirect('messaging:conversation_detail', pk=pk)


@login_required
@require_http_methods(["POST"])
def close_conversation(request, pk):
    """Staff closes a resolved conversation."""
    user = request.user
    if user.role not in STAFF_ROLES:
        return JsonResponse({'error': 'Access denied'}, status=403)

    conversation = get_object_or_404(Conversation, pk=pk)
    conversation.status = 'closed'
    conversation.closed_at = timezone.now()
    conversation.closed_by = user
    conversation.save(update_fields=['status', 'closed_at', 'closed_by', 'updated_at'])
    logger.info(f'Conversation {pk} closed by {user.username}')
    return redirect('messaging:conversation_detail', pk=pk)


@login_required
@require_http_methods(["POST"])
def reopen_conversation(request, pk):
    """Staff reopens a closed conversation."""
    user = request.user
    if user.role not in STAFF_ROLES:
        return JsonResponse({'error': 'Access denied'}, status=403)

    conversation = get_object_or_404(Conversation, pk=pk)
    conversation.status = 'open'
    conversation.closed_at = None
    conversation.closed_by = None
    conversation.save(update_fields=['status', 'closed_at', 'closed_by', 'updated_at'])
    logger.info(f'Conversation {pk} reopened by {user.username}')
    return redirect('messaging:conversation_detail', pk=pk)


@login_required
@require_http_methods(["GET"])
def unread_count(request):
    """API: return total unread message count for nav badge."""
    count = MessageReadStatus.objects.filter(user=request.user).values(
        'conversation'
    ).distinct().count()
    return JsonResponse({'count': count})
