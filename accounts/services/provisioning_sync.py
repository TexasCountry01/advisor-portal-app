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

from .ghl_client import fetch_ghl_contacts
from .sso import determine_role_from_tags
from .models import ProvisioningAlert

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
