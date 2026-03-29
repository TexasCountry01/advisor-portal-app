import logging
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from .models import Conversation, Message, MessageReadStatus

logger = logging.getLogger(__name__)

STAFF_ROLES = ('technician', 'administrator', 'manager')
BROADCAST_ROLES = ('administrator', 'manager')


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
        # Members see their own conversations + broadcast messages
        conversations = Conversation.objects.filter(
            Q(started_by=user) | Q(is_broadcast=True)
        ).select_related('assigned_to', 'started_by').distinct().order_by('-updated_at')
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
        'can_broadcast': _can_broadcast(user),
    }
    return render(request, 'messaging/inbox.html', context)


@login_required
def conversation_detail(request, pk):
    """View and reply to a conversation."""
    user = request.user
    is_staff = user.role in STAFF_ROLES
    conversation = get_object_or_404(Conversation, pk=pk)

    # Permission: member can only see own conversations or broadcasts
    if not is_staff and conversation.started_by != user and not conversation.is_broadcast:
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
        # Send email notification to the member (non-broadcast conversations only)
        if not conversation.is_broadcast:
            try:
                from cases.services.email_service import send_email_notification, _get_notification_email, should_send_emails
                member_email = _get_notification_email(conversation.started_by)
                if member_email and should_send_emails():
                    send_email_notification(
                        subject=f'Re: {conversation.subject} - ProFeds Benefits Team',
                        template_name='message_reply_notification.html',
                        context={
                            'member_first_name': conversation.started_by.first_name or conversation.started_by.username,
                            'subject': conversation.subject,
                            'reply_preview': body[:300],
                            'staff_name': user.get_full_name() or 'Benefits Team',
                            'conversation_url': f"{getattr(__import__('django.conf', fromlist=['settings']).settings, 'SITE_URL', 'https://reports.profeds.com')}/messages/{conversation.pk}/",
                        },
                        recipient_email=member_email,
                        user=user,
                        action_type='email_notification_sent',
                    )
            except Exception as e:
                logger.error(f'Error sending reply email for conversation {conversation.pk}: {e}')
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


def _can_broadcast(user):
    """Check if user has broadcast permission: admin, manager, or level-3 tech."""
    if user.role in BROADCAST_ROLES:
        return True
    if user.role == 'technician' and getattr(user, 'user_level', '') == 'level_3':
        return True
    return False


@login_required
@require_http_methods(["GET", "POST"])
def broadcast_message(request):
    """Admin/Manager/Level-3 Tech sends a broadcast to all active members+delegates with cases."""
    user = request.user
    if not _can_broadcast(user):
        return redirect('messaging:inbox')

    from accounts.models import User as UserModel, MemberDelegate

    # Get target audience: active members/delegates who have cases
    target_users = UserModel.objects.filter(
        is_active=True
    ).filter(
        Q(submitted_cases__isnull=False) |
        Q(delegated_members__isnull=False)
    ).exclude(
        role__in=STAFF_ROLES
    ).distinct()

    if request.method == 'POST':
        subject = request.POST.get('subject', '').strip()
        body = request.POST.get('body', '').strip()
        send_email = request.POST.get('send_email') == '1'

        if not subject or not body:
            return render(request, 'messaging/broadcast.html', {
                'error': 'Subject and message are required.',
                'subject': subject,
                'body': body,
                'send_email': send_email,
                'target_count': target_users.count(),
            })

        # Create the broadcast conversation
        conversation = Conversation.objects.create(
            subject=subject,
            started_by=user,
            is_broadcast=True,
            broadcast_email_sent=send_email,
            status='closed',  # Broadcasts are informational, start closed
        )
        msg = Message.objects.create(
            conversation=conversation,
            author=user,
            body=body,
        )

        # Create unread records for all target users
        read_statuses = [
            MessageReadStatus(message=msg, user=target, conversation=conversation)
            for target in target_users
        ]
        MessageReadStatus.objects.bulk_create(read_statuses, ignore_conflicts=True)

        recipients_count = len(read_statuses)
        emails_sent = 0

        # Send emails if requested
        if send_email:
            from cases.services.email_service import send_email_notification, _get_notification_email, should_send_emails
            from django.conf import settings as django_settings
            if should_send_emails():
                site_url = getattr(django_settings, 'SITE_URL', 'https://reports.profeds.com')
                for target in target_users:
                    target_email = _get_notification_email(target)
                    if target_email:
                        try:
                            send_email_notification(
                                subject=f'{subject} - ProFeds Benefits Team',
                                template_name='broadcast_notification.html',
                                context={
                                    'member_first_name': target.first_name or target.username,
                                    'subject': subject,
                                    'body': body,
                                    'sender_name': user.get_full_name() or 'Benefits Team',
                                    'portal_url': f"{site_url}/messages/{conversation.pk}/",
                                },
                                recipient_email=target_email,
                                user=user,
                                action_type='email_notification_sent',
                            )
                            emails_sent += 1
                        except Exception as e:
                            logger.error(f'Error sending broadcast email to {target_email}: {e}')

        logger.info(
            f'Broadcast "{subject}" by {user.username}: '
            f'{recipients_count} recipients, {emails_sent} emails sent'
        )

        from django.contrib import messages
        email_note = f', {emails_sent} emails sent' if send_email else ''
        messages.success(request, f'Broadcast sent to {recipients_count} users{email_note}.')
        return redirect('messaging:conversation_detail', pk=conversation.pk)

    context = {
        'target_count': target_users.count(),
    }
    return render(request, 'messaging/broadcast.html', context)
