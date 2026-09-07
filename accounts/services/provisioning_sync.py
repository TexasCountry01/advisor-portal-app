"""
Provisioning Sync — shared detection logic for GHL <-> portal drift.

Used by BOTH:
  - The manual "Sync from GHL" admin page (accounts/views.py sync_ghl_contacts)
  - The daily provisioning alert cron job (Phase 3)

This is the single place that knows how to fetch GHL contacts, filter to
portal-relevant ones, and match them against portal User records — so that
logic is never duplicated between the manual page and the automated job.

See docs/PROVISIONING_SYNC_CRON_ACTION_PLAN_2026-09-06.md for the full design.
"""
import logging

from django.contrib.auth import get_user_model
from django.utils import timezone

from ..ghl_client import fetch_ghl_contacts
from ..sso import determine_role_from_tags
from ..models import ProvisioningAlert

logger = logging.getLogger(__name__)
User = get_user_model()


def _fetch_and_index_contacts(limit=100, max_total=1000):
    """Fetch all GHL contacts once and build lookup indexes for reuse.

    Indexes are built from the FULL contact list (not just tag-relevant
    contacts), since detecting a *removed* tag requires being able to find
    a contact that no longer has one.
    """
    contacts = fetch_ghl_contacts(limit=limit, max_total=max_total)
    by_contact_id = {}
    by_email = {}
    for contact in contacts:
        contact_id = contact.get('contact_id')
        email = (contact.get('email') or '').strip().lower()
        if contact_id:
            by_contact_id[contact_id] = contact
        if email and email not in by_email:
            by_email[email] = contact
    return contacts, by_contact_id, by_email


def check_ghl_status_for_email(email):
    """Look up a single email among ALL GHL contacts (not just tag-filtered)
    to determine provisioning status — used to enrich the delegate-request
    staff email with a specific, actionable GHL status instead of a generic
    "process in GHL" instruction.

    Returns a dict:
        {'found': bool, 'contact_id': str|None, 'has_access': bool, 'role': str|None}
    """
    if not email:
        return {'found': False, 'contact_id': None, 'has_access': False, 'role': None}

    _, _, by_email = _fetch_and_index_contacts()
    contact = by_email.get(email.strip().lower())
    if not contact:
        return {'found': False, 'contact_id': None, 'has_access': False, 'role': None}

    role, is_pure_delegate, has_access = determine_role_from_tags(contact.get('tags', []))
    return {
        'found': True,
        'contact_id': contact.get('contact_id'),
        'has_access': has_access,
        'role': role,
    }


def get_relevant_contacts(contacts=None):
    """All GHL contacts with a portal-access tag, annotated with the
    determined role/delegate flag and the matching portal User (if any,
    matched by contact_id then email fallback — same order as SSO login).

    This is the single shared computation behind both the manual GHL Sync
    Review page and category 1 (new_ghl_contact) of the daily alert job.
    """
    if contacts is None:
        contacts, _, _ = _fetch_and_index_contacts()

    relevant = []
    for contact in contacts:
        role, is_pure_delegate, has_access = determine_role_from_tags(contact.get('tags', []))
        if not has_access:
            continue

        contact_id = contact.get('contact_id')
        email = contact.get('email')
        portal_user = None
        if contact_id:
            portal_user = User.objects.filter(contact_id=contact_id).first()
        if not portal_user and email:
            portal_user = User.objects.filter(email__iexact=email).first()

        relevant.append({
            'contact_id': contact_id,
            'email': email,
            'first_name': contact.get('first_name', ''),
            'last_name': contact.get('last_name', ''),
            'workshop_code': contact.get('workshop_code', ''),
            'tags': contact.get('tags', []),
            'ghl_role': role,
            'is_pure_delegate': is_pure_delegate,
            'portal_user': portal_user,
        })
    return relevant


def compute_new_ghl_contacts(contacts=None):
    """Category 1 — GHL contacts with a portal access tag but no matching
    portal User record yet (needs Provision)."""
    return [r for r in get_relevant_contacts(contacts=contacts) if r['portal_user'] is None]


def compute_missing_tag_users(by_contact_id=None, by_email=None):
    """Category 2 — active, role='member' portal Users whose GHL record no
    longer carries a portal access tag (or has no matching GHL contact at
    all). Needs Deactivate.

    Scoped to role='member' only — technician/manager/administrator accounts
    are intentionally never GHL-tag-driven (see accounts/sso.py
    PORTAL_MANAGED_ROLES), so checking them would produce a false alert on
    every staff account, every single run.
    """
    if by_contact_id is None or by_email is None:
        _, by_contact_id, by_email = _fetch_and_index_contacts()

    results = []
    members = User.objects.filter(role='member', is_active=True)
    for user in members:
        contact = None
        if user.contact_id:
            contact = by_contact_id.get(user.contact_id)
        if not contact and user.email:
            contact = by_email.get(user.email.strip().lower())

        has_access = False
        if contact:
            _, _, has_access = determine_role_from_tags(contact.get('tags', []))

        if has_access:
            continue

        results.append({
            'user_id': user.id,
            'username': user.username,
            'email': user.email,
            'name': user.get_full_name() or user.username,
            'contact_id': user.contact_id or '',
        })
    return results


def sync_provisioning_alerts():
    """Run both detections and upsert ProvisioningAlert rows.

    Any previously-open alert that isn't found again this run is marked
    resolved automatically (provisioned, tag restored, or user deactivated).

    Returns a dict: {
        'new_contacts': [...], 'missing_tag_users': [...],
        'new_alerts': [ProvisioningAlert, ...], 'still_open_alerts': [...],
    }
    """
    contacts, by_contact_id, by_email = _fetch_and_index_contacts()

    new_contacts = compute_new_ghl_contacts(contacts=contacts)
    missing_tag_users = compute_missing_tag_users(by_contact_id=by_contact_id, by_email=by_email)

    now = timezone.now()
    seen_alert_ids = []
    new_alerts = []
    still_open_alerts = []

    for item in new_contacts:
        try:
            alert = ProvisioningAlert.objects.get(
                alert_type='new_ghl_contact',
                contact_id=item['contact_id'],
                resolved_at__isnull=True,
            )
            alert.details = item
            alert.email = item.get('email') or alert.email
            alert.save()  # auto_now bumps last_seen_at
            still_open_alerts.append(alert)
        except ProvisioningAlert.DoesNotExist:
            alert = ProvisioningAlert.objects.create(
                alert_type='new_ghl_contact',
                contact_id=item['contact_id'],
                email=item.get('email') or '',
                details=item,
            )
            new_alerts.append(alert)
        seen_alert_ids.append(alert.id)

    for item in missing_tag_users:
        try:
            alert = ProvisioningAlert.objects.get(
                alert_type='missing_ghl_tag',
                user_id=item['user_id'],
                resolved_at__isnull=True,
            )
            alert.details = item
            alert.contact_id = item.get('contact_id') or alert.contact_id
            alert.email = item.get('email') or alert.email
            alert.save()
            still_open_alerts.append(alert)
        except ProvisioningAlert.DoesNotExist:
            alert = ProvisioningAlert.objects.create(
                alert_type='missing_ghl_tag',
                user_id=item['user_id'],
                contact_id=item.get('contact_id') or '',
                email=item.get('email') or '',
                details=item,
            )
            new_alerts.append(alert)
        seen_alert_ids.append(alert.id)

    # Self-heal: anything previously open but not found again this run is resolved.
    resolved_count = ProvisioningAlert.objects.filter(
        resolved_at__isnull=True
    ).exclude(id__in=seen_alert_ids).update(resolved_at=now)

    if resolved_count:
        logger.info(f'Provisioning sync: auto-resolved {resolved_count} alert(s) no longer detected.')

    return {
        'new_contacts': new_contacts,
        'missing_tag_users': missing_tag_users,
        'new_alerts': new_alerts,
        'still_open_alerts': still_open_alerts,
        'resolved_count': resolved_count,
    }


def run_provisioning_alert_cycle(triggered_by=None, force=False):
    """Run one full detection + persist + conditional-email cycle.

    Used by BOTH the daily cron (force=False, respects
    SystemSettings.provisioning_alerts_enabled) and the manual "Run Now"
    admin action (force=True, always runs regardless of that toggle — the
    global email kill switch, should_send_emails(), is still respected
    either way, since that's the app-wide emergency stop, not something a
    single feature's manual trigger should bypass).

    Returns a summary dict:
        {'success': bool, 'error': str|None, 'skipped_disabled': bool,
         'open_new_count': int, 'open_missing_count': int, 'total_open': int,
         'new_count': int, 'still_open_count': int, 'resolved_count': int,
         'email_sent': bool, 'email_skip_reason': str|None}
    """
    from core.models import SystemSettings, AuditLog

    system_settings = SystemSettings.get_settings()

    empty_result = {
        'open_new_count': 0, 'open_missing_count': 0, 'total_open': 0,
        'new_count': 0, 'still_open_count': 0, 'resolved_count': 0,
        'email_sent': False, 'email_skip_reason': None,
    }

    if not force and not system_settings.provisioning_alerts_enabled:
        return {'success': True, 'skipped_disabled': True, 'error': None, **empty_result}

    try:
        result = sync_provisioning_alerts()
    except Exception as e:
        logger.error(f'Provisioning alert sync failed: {e}')
        AuditLog.objects.create(
            user=triggered_by,
            action_type='provisioning_alert_run',
            description=f'Provisioning alert sync FAILED: {e}',
            metadata={'error': str(e), 'manual': triggered_by is not None},
        )
        return {'success': False, 'skipped_disabled': False, 'error': str(e), **empty_result}

    open_new_contacts = ProvisioningAlert.objects.filter(alert_type='new_ghl_contact', resolved_at__isnull=True)
    open_missing_tag = ProvisioningAlert.objects.filter(alert_type='missing_ghl_tag', resolved_at__isnull=True)
    open_new_count = open_new_contacts.count()
    open_missing_count = open_missing_tag.count()
    total_open = open_new_count + open_missing_count

    email_sent = False
    email_skip_reason = None
    if total_open > 0:
        new_alert_ids = {a.id for a in result['new_alerts']}
        email_sent, email_skip_reason = _send_digest_email(
            system_settings, open_new_contacts, open_missing_tag, new_alert_ids, triggered_by=triggered_by
        )

    AuditLog.objects.create(
        user=triggered_by,
        action_type='provisioning_alert_run',
        description=(
            f'Provisioning alert sync run: {len(result["new_alerts"])} new, '
            f'{len(result["still_open_alerts"])} still open, '
            f'{result["resolved_count"]} resolved. Email sent: {email_sent}.'
        ),
        metadata={
            'new_alerts_count': len(result['new_alerts']),
            'still_open_count': len(result['still_open_alerts']),
            'resolved_count': result['resolved_count'],
            'open_new_contacts': open_new_count,
            'open_missing_tag_users': open_missing_count,
            'email_sent': email_sent,
            'manual': triggered_by is not None,
        },
    )

    return {
        'success': True,
        'skipped_disabled': False,
        'error': None,
        'open_new_count': open_new_count,
        'open_missing_count': open_missing_count,
        'total_open': total_open,
        'new_count': len(result['new_alerts']),
        'still_open_count': len(result['still_open_alerts']),
        'resolved_count': result['resolved_count'],
        'email_sent': email_sent,
        'email_skip_reason': email_skip_reason,
    }


def _send_digest_email(system_settings, open_new_contacts, open_missing_tag, new_alert_ids, triggered_by=None):
    """Send the "Portal Access Changes - Action Required" digest email to up
    to 3 configured recipients.

    Returns (sent: bool, skip_reason: str|None).
    """
    recipients = []
    if system_settings.provisioning_alert_email_1_enabled and system_settings.provisioning_alert_email_1:
        recipients.append(system_settings.provisioning_alert_email_1)
    if system_settings.provisioning_alert_email_2_enabled and system_settings.provisioning_alert_email_2:
        recipients.append(system_settings.provisioning_alert_email_2)
    if system_settings.provisioning_alert_email_3_enabled and system_settings.provisioning_alert_email_3:
        recipients.append(system_settings.provisioning_alert_email_3)

    if not recipients:
        logger.warning('Provisioning alert: open items exist but no recipient emails are configured/enabled.')
        return False, 'no recipient emails configured/enabled'

    from cases.services.email_service import should_send_emails
    if not should_send_emails():
        return False, 'email notifications disabled globally in System Settings'

    from django.core.mail import send_mail
    from django.template.loader import render_to_string
    from django.conf import settings as django_settings
    from django.utils import timezone
    from core.models import AuditLog

    def _row_for_contact_alert(alert):
        d = alert.details or {}
        name = f"{d.get('first_name', '')} {d.get('last_name', '')}".strip() or 'Unknown'
        return {
            'name': name,
            'email': alert.email or d.get('email', ''),
            'workshop_code': d.get('workshop_code', ''),
            'ghl_role': d.get('ghl_role', ''),
            'first_detected_at': alert.first_detected_at,
            'is_new': alert.id in new_alert_ids,
        }

    def _row_for_missing_tag_alert(alert):
        d = alert.details or {}
        return {
            'name': d.get('name') or alert.email or 'Unknown',
            'username': d.get('username', ''),
            'email': alert.email or d.get('email', ''),
            'first_detected_at': alert.first_detected_at,
            'is_new': alert.id in new_alert_ids,
        }

    new_contact_rows = [_row_for_contact_alert(a) for a in open_new_contacts.order_by('-first_detected_at')]
    missing_tag_rows = [_row_for_missing_tag_alert(a) for a in open_missing_tag.order_by('-first_detected_at')]

    site_url = getattr(django_settings, 'SITE_URL', 'https://portal.profeds.com')
    context = {
        'run_date': timezone.now(),
        'new_contact_rows': new_contact_rows,
        'missing_tag_rows': missing_tag_rows,
        'new_contacts_count': len(new_contact_rows),
        'missing_tag_count': len(missing_tag_rows),
        'ghl_sync_url': f'{site_url}/accounts/ghl-sync/',
    }

    subject = 'Portal Access Changes - Action Required'
    text_message = render_to_string('emails/provisioning_alert_digest.txt', context)
    html_message = render_to_string('emails/provisioning_alert_digest.html', context)

    try:
        send_mail(
            subject=subject,
            message=text_message,
            from_email=django_settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipients,
            html_message=html_message,
            fail_silently=False,
        )
    except Exception as e:
        logger.error(f'Failed to send provisioning alert digest: {e}')
        AuditLog.objects.create(
            user=triggered_by,
            action_type='email_notification_failed',
            description=f'Provisioning alert digest email FAILED to {recipients}: {e}',
            metadata={'recipients': recipients, 'error': str(e)},
        )
        return False, f'send failed: {e}'

    AuditLog.objects.create(
        user=triggered_by,
        action_type='provisioning_alert_sent',
        description=(
            f'Provisioning alert digest sent to {recipients}: '
            f'{len(new_contact_rows)} new-contact, {len(missing_tag_rows)} missing-tag item(s).'
        ),
        metadata={
            'recipients': recipients,
            'subject': subject,
            'new_contacts_count': len(new_contact_rows),
            'missing_tag_count': len(missing_tag_rows),
            'manual': triggered_by is not None,
        },
    )
    return True, None
