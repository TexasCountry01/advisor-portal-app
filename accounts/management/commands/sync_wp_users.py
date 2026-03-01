"""
Django management command: sync_wp_users

One-time (or periodic) population of portal User records from the
WP/CRM system.  Fetches all users with portal-access tags and creates
or updates matching Django User rows keyed on `contact_id`.

Usage:
    python manage.py sync_wp_users                 # live run
    python manage.py sync_wp_users --dry-run       # preview only
    python manage.py sync_wp_users --tag "Portal access: Member"   # one tag
    python manage.py sync_wp_users --verbose       # extra output

BLOCKED:
    The API endpoint URL and field mapping in `_extract_user_data()` (accounts/sso.py)
    need to be confirmed by the WP developer before this command can make real calls.
    Until then, the command structure, arg handling, and dry-run logic are ready.
"""

import logging
from django.core.management.base import BaseCommand
from django.conf import settings
from django.contrib.auth import get_user_model

from accounts.sso import (
    _extract_user_data,
    determine_role_from_tags,
    DELEGATE_TAGS,
    TAG_ROLE_MAP,
)
from core.models import AuditLog

logger = logging.getLogger(__name__)
User = get_user_model()

# Portal-access tags we want to pull from the CRM
SYNC_TAGS = list(TAG_ROLE_MAP.keys())


class Command(BaseCommand):
    help = (
        'Sync portal users from WP/CRM.  Creates or updates User records '
        'for everyone with a portal-access tag.'
    )

    # ------------------------------------------------------------------
    # Arguments
    # ------------------------------------------------------------------
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview what would change without writing to the database.',
        )
        parser.add_argument(
            '--tag',
            type=str,
            default=None,
            help='Sync only users with this specific tag (e.g. "Portal access: Member").',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Print extra detail for every user processed.',
        )

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------
    def handle(self, *args, **options):
        dry_run = options['dry_run']
        single_tag = options.get('tag')
        verbose = options['verbose']

        tags_to_sync = [single_tag] if single_tag else SYNC_TAGS
        self.stdout.write(
            self.style.HTTP_INFO(
                f'Syncing users for tag(s): {", ".join(tags_to_sync)}'
            )
        )
        if dry_run:
            self.stdout.write(self.style.WARNING('** DRY RUN — no database writes **'))

        # ----- Fetch contacts from CRM / WP API -----
        contacts = self._fetch_contacts(tags_to_sync)

        if contacts is None:
            self.stdout.write(
                self.style.ERROR(
                    'API call not yet implemented — need endpoint URL + sample JSON '
                    'from WP developer. See accounts/sso.py _extract_user_data().'
                )
            )
            return

        if not contacts:
            self.stdout.write(self.style.SUCCESS('No contacts returned from API.'))
            return

        # ----- Process each contact -----
        created = 0
        updated = 0
        skipped = 0
        errors = 0

        for raw in contacts:
            try:
                data = _extract_user_data(raw)

                if not data.get('contact_id'):
                    self.stdout.write(
                        self.style.WARNING(f'  SKIP (no contact_id): {raw}')
                    )
                    skipped += 1
                    continue

                if not data.get('email'):
                    self.stdout.write(
                        self.style.WARNING(
                            f'  SKIP (no email): contact_id={data["contact_id"]}'
                        )
                    )
                    skipped += 1
                    continue

                role = determine_role_from_tags(data['tags'])
                is_delegate = any(t in DELEGATE_TAGS for t in data['tags'])

                # Try to match existing user by contact_id, then by email
                user = (
                    User.objects.filter(contact_id=data['contact_id']).first()
                    or User.objects.filter(email__iexact=data['email']).first()
                )

                if user:
                    changes = self._compute_changes(user, data, role)
                    if changes:
                        if dry_run:
                            self.stdout.write(
                                f'  UPDATE {data["email"]} (id={user.id}): {changes}'
                            )
                        else:
                            self._apply_changes(user, data, role)
                        updated += 1
                    else:
                        if verbose:
                            self.stdout.write(f'  NO CHANGE {data["email"]}')
                        skipped += 1
                else:
                    if dry_run:
                        self.stdout.write(
                            f'  CREATE {data["email"]} role={role} '
                            f'ws={data["workshop_code"]} delegate={is_delegate}'
                        )
                    else:
                        self._create_user(data, role)
                    created += 1

            except Exception as exc:
                errors += 1
                self.stdout.write(
                    self.style.ERROR(f'  ERROR processing contact: {exc}')
                )
                logger.exception('sync_wp_users: error processing contact')

        # ----- Summary -----
        self.stdout.write('')
        style = self.style.SUCCESS if not errors else self.style.WARNING
        self.stdout.write(
            style(
                f'Done.  Created: {created}  Updated: {updated}  '
                f'Skipped: {skipped}  Errors: {errors}'
            )
        )

        if not dry_run and (created or updated):
            AuditLog.objects.create(
                action_type='wp_user_sync',
                description=(
                    f'WP user sync completed: {created} created, {updated} updated, '
                    f'{skipped} skipped, {errors} errors'
                ),
                changes={
                    'created': created,
                    'updated': updated,
                    'skipped': skipped,
                    'errors': errors,
                    'tags_synced': tags_to_sync,
                },
            )

    # ------------------------------------------------------------------
    # API call — STUB until WP dev confirms endpoint
    # ------------------------------------------------------------------
    def _fetch_contacts(self, tags):
        """
        Fetch all CRM contacts that have any of the given tags.

        TODO: Implement once the WP developer confirms:
          1. The API endpoint URL (WP REST? CRM API? WP Fusion REST?)
          2. How to filter by tag (query param? separate call per tag?)
          3. Authentication method (API key? OAuth token?)
          4. Pagination approach

        Returns:
            list[dict] — raw contact dicts from the API, or
            None       — if the call is not yet implemented.
        """
        # ---------------------------------------------------------------
        # PLACEHOLDER — return None to signal "not implemented yet"
        # ---------------------------------------------------------------
        # Example of what the real implementation might look like:
        #
        # import requests
        # base_url = settings.WP_OAUTH_BASE_URL
        # api_url = f'{base_url}/wp-json/wp/v2/users'  # or CRM endpoint
        # headers = {'Authorization': f'Bearer {api_key}'}
        # all_contacts = []
        # for tag in tags:
        #     resp = requests.get(api_url, params={'tag': tag}, headers=headers)
        #     resp.raise_for_status()
        #     all_contacts.extend(resp.json())
        # return all_contacts
        # ---------------------------------------------------------------
        return None

    # ------------------------------------------------------------------
    # Diff helper
    # ------------------------------------------------------------------
    def _compute_changes(self, user, data, role):
        """Return a dict of {field: (old, new)} for fields that differ."""
        changes = {}
        field_map = {
            'contact_id': data['contact_id'],
            'email': data['email'],
            'first_name': data['first_name'],
            'last_name': data['last_name'],
            'workshop_code': data['workshop_code'],
            'phone': data['phone'],
            'role': role,
        }
        for field, new_val in field_map.items():
            if not new_val:
                continue  # don't overwrite with blanks
            old_val = getattr(user, field, None)
            if old_val is None:
                old_val = ''
            if str(old_val).strip().lower() != str(new_val).strip().lower():
                changes[field] = (old_val, new_val)
        return changes

    # ------------------------------------------------------------------
    # Write helpers
    # ------------------------------------------------------------------
    def _apply_changes(self, user, data, role):
        """Apply data changes to an existing user and save."""
        if data['contact_id'] and not user.contact_id:
            user.contact_id = data['contact_id']
        if data['email']:
            user.email = data['email']
        if data['first_name']:
            user.first_name = data['first_name']
        if data['last_name']:
            user.last_name = data['last_name']
        if data['workshop_code']:
            user.workshop_code = data['workshop_code']
        if data['phone']:
            user.phone = data['phone']
        if role:
            user.role = role
        user.save()
        logger.info(f'sync_wp_users: updated user {user.email} (id={user.id})')

    def _create_user(self, data, role):
        """Create a new User record from CRM data."""
        user = User(
            username=data['username'] or data['email'].split('@')[0],
            email=data['email'],
            first_name=data['first_name'],
            last_name=data['last_name'],
            role=role,
            contact_id=data['contact_id'],
            workshop_code=data['workshop_code'],
            phone=data['phone'],
            is_active=True,
        )
        # SSO users don't need a usable password — they authenticate via OAuth
        user.set_unusable_password()
        user.save()
        logger.info(f'sync_wp_users: created user {user.email} (id={user.id})')
        return user
