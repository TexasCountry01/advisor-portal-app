"""
WP Webhook Endpoint — Receives real-time profile update notifications from WordPress.

This endpoint will be called by WP Fusion / WordPress when:
  - A user's profile is updated (name, email, workshop_code change)
  - A user's tags change (portal access granted or revoked)
  - A subscription status changes (active → inactive)

SECURITY:
  - Validates a shared webhook secret (WP_WEBHOOK_SECRET env var)
  - Rejects requests without valid secret
  - Logs all incoming webhook events

STATUS: Skeleton — ready for wiring once WP developer confirms payload format.
"""

import json
import logging
import hmac
import hashlib
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.conf import settings
from core.models import AuditLog

logger = logging.getLogger(__name__)


@csrf_exempt
@require_POST
def wp_webhook(request):
    """
    Receive and process webhook events from WordPress / WP Fusion.

    Expected headers:
        X-WP-Webhook-Secret: <shared secret>

    Expected JSON body (TBD — update when WP dev confirms):
    {
        "event": "profile_updated" | "tags_changed" | "user_deactivated",
        "contact_id": 12345,
        "data": {
            "email": "...",
            "first_name": "...",
            "last_name": "...",
            "tags": [...],
            ...
        }
    }
    """
    # ---- Verify webhook secret ----
    webhook_secret = getattr(settings, 'WP_WEBHOOK_SECRET', None)
    if not webhook_secret:
        logger.warning('wp_webhook: WP_WEBHOOK_SECRET not configured — rejecting')
        return JsonResponse(
            {'error': 'Webhook not configured'},
            status=503,
        )

    received_secret = request.headers.get('X-WP-Webhook-Secret', '')
    if not hmac.compare_digest(received_secret, webhook_secret):
        logger.warning('wp_webhook: invalid secret received')
        return JsonResponse({'error': 'Invalid webhook secret'}, status=403)

    # ---- Parse body ----
    try:
        payload = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        logger.warning('wp_webhook: malformed JSON body')
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    event = payload.get('event', 'unknown')
    contact_id = payload.get('contact_id')

    logger.info(f'wp_webhook: received event={event} contact_id={contact_id}')

    # ---- Log the raw event ----
    AuditLog.objects.create(
        action_type='other',
        description=f'WP webhook received: event={event}, contact_id={contact_id}',
        metadata={
            'event': event,
            'contact_id': contact_id,
            'payload_keys': list(payload.keys()),
        },
        ip_address=request.META.get('REMOTE_ADDR'),
    )

    # ---- Dispatch by event type ----
    # TODO: Implement actual handlers once payload format is confirmed.
    #
    # if event == 'profile_updated':
    #     _handle_profile_update(contact_id, payload.get('data', {}))
    # elif event == 'tags_changed':
    #     _handle_tags_changed(contact_id, payload.get('data', {}))
    # elif event == 'user_deactivated':
    #     _handle_user_deactivated(contact_id)
    # else:
    #     logger.info(f'wp_webhook: unrecognized event type: {event}')

    return JsonResponse({
        'status': 'received',
        'event': event,
        'message': 'Webhook endpoint is operational but handlers are not yet implemented.',
    })
