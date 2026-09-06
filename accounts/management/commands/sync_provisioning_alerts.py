"""
Django management command: daily GHL <-> portal provisioning drift alert.

Run via cron daily at 6:00 AM Central Time:
    0 6 * * * cd /path/to/app && python manage.py sync_provisioning_alerts

Detects two kinds of drift (see accounts/services/provisioning_sync.py):
  1. New GHL contacts with a portal access tag, not yet provisioned in advisor-portal
     (needs Provision).
  2. Active, role='member' portal users whose GHL record no longer carries a
     portal access tag (needs Deactivate).

Sends a single digest email (subject: "Portal Access Changes - Action Required")
to up to 3 configured recipients in System Settings, ONLY if something is open.
Always writes an AuditLog entry summarizing the run, even a no-op run.

NOTE: Email sending is implemented in Phase 4 once the digest templates exist.
This command already performs full detection + persistence + audit logging;
only the actual email dispatch is a placeholder until then.
"""
import logging

from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Detect GHL/portal provisioning drift and email staff if anything needs attention'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview detected drift without writing to the database or sending email',
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)

        from core.models import SystemSettings
        system_settings = SystemSettings.get_settings()

        if not system_settings.provisioning_alerts_enabled:
            self.stdout.write(self.style.WARNING(
                'Provisioning alerts are disabled in System Settings. Skipping.'
            ))
            return

        if dry_run:
            self._handle_dry_run()
            return

        self._handle_real_run(system_settings)

    def _handle_dry_run(self):
        from accounts.services.provisioning_sync import compute_new_ghl_contacts, compute_missing_tag_users

        try:
            new_contacts = compute_new_ghl_contacts()
            missing_tag_users = compute_missing_tag_users()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'GHL fetch failed: {e}'))
            return

        self.stdout.write(self.style.WARNING(
            f'DRY RUN: {len(new_contacts)} new GHL contact(s) needing provisioning, '
            f'{len(missing_tag_users)} active member(s) missing GHL tag.'
        ))

        for item in new_contacts:
            name = f"{item.get('first_name', '')} {item.get('last_name', '')}".strip() or 'Unknown'
            self.stdout.write(f"  [NEW CONTACT]  {name} <{item.get('email')}> ({item.get('contact_id')})")

        for item in missing_tag_users:
            self.stdout.write(f"  [MISSING TAG]  {item['name']} <{item['email']}> (user_id={item['user_id']})")

        self.stdout.write(self.style.WARNING('DRY RUN: no database changes made, no email sent.'))

    def _handle_real_run(self, system_settings):
        from accounts.services.provisioning_sync import sync_provisioning_alerts
        from accounts.models import ProvisioningAlert
        from core.models import AuditLog

        try:
            result = sync_provisioning_alerts()
        except Exception as e:
            logger.error(f'Provisioning alert sync failed: {e}')
            self.stdout.write(self.style.ERROR(f'GHL sync failed: {e}'))
            AuditLog.objects.create(
                user=None,
                action_type='provisioning_alert_run',
                description=f'Provisioning alert sync FAILED: {e}',
                metadata={'error': str(e)},
            )
            return

        open_new_contacts = ProvisioningAlert.objects.filter(
            alert_type='new_ghl_contact', resolved_at__isnull=True
        )
        open_missing_tag = ProvisioningAlert.objects.filter(
            alert_type='missing_ghl_tag', resolved_at__isnull=True
        )
        open_new_count = open_new_contacts.count()
        open_missing_count = open_missing_tag.count()
        total_open = open_new_count + open_missing_count

        email_sent = False
        if total_open > 0:
            email_sent = self._send_digest_email(system_settings, open_new_contacts, open_missing_tag)

        # Always write an audit log entry, even a no-op run.
        AuditLog.objects.create(
            user=None,
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
            },
        )

        if total_open == 0:
            self.stdout.write(self.style.SUCCESS('No open provisioning alerts. Nothing to report.'))
        else:
            self.stdout.write(self.style.SUCCESS(
                f'{open_new_count} new-contact alert(s), {open_missing_count} missing-tag alert(s) open. '
                f'Email sent: {email_sent}'
            ))

    def _send_digest_email(self, system_settings, open_new_contacts, open_missing_tag):
        """Send the "Portal Access Changes - Action Required" digest email.

        Placeholder until Phase 4 builds the email templates
        (accounts/templates/emails/provisioning_alert_digest.html/.txt).
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
            self.stdout.write(self.style.WARNING(
                'No provisioning alert recipient emails configured/enabled — skipping send.'
            ))
            return False

        self.stdout.write(self.style.WARNING(
            f'Email templates not yet implemented (Phase 4) — would send to {recipients}, skipping send for now.'
        ))
        return False
