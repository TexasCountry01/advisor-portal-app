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

The same detection/email logic is also available as an on-demand "Run Now"
action in System Settings -> Provisioning Alerts (see accounts/views.py
run_provisioning_alerts_now). Both call
accounts.services.provisioning_sync.run_provisioning_alert_cycle() so there
is exactly one implementation of the actual sync + send logic.
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
        if options.get('dry_run', False):
            self._handle_dry_run()
            return

        from accounts.services.provisioning_sync import run_provisioning_alert_cycle

        result = run_provisioning_alert_cycle(triggered_by=None, force=False)

        if result.get('skipped_disabled'):
            self.stdout.write(self.style.WARNING(
                'Provisioning alerts are disabled in System Settings. Skipping.'
            ))
            return

        if not result['success']:
            self.stdout.write(self.style.ERROR(f"GHL sync failed: {result['error']}"))
            return

        if result['total_open'] == 0:
            self.stdout.write(self.style.SUCCESS('No open provisioning alerts. Nothing to report.'))
        else:
            suffix = f" ({result['email_skip_reason']})" if not result['email_sent'] and result['email_skip_reason'] else ''
            self.stdout.write(self.style.SUCCESS(
                f"{result['open_new_count']} new-contact alert(s), {result['open_missing_count']} missing-tag "
                f"alert(s) open. Email sent: {result['email_sent']}{suffix}"
            ))

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
