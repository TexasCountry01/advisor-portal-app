import logging
from typing import Any, Dict, List

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def get_ghl_headers() -> Dict[str, str]:
    token = (getattr(settings, 'GHL_PRIVATE_TOKEN', '') or '').strip()
    if not token:
        raise ValueError('GHL_PRIVATE_TOKEN is not configured.')
    return {
        'Authorization': f'Bearer {token}',
        'Version': '2021-07-28',
        'Accept': 'application/json',
    }


def normalize_tags(raw_tags: Any) -> List[str]:
    if raw_tags is None:
        return []
    if isinstance(raw_tags, str):
        return [tag.strip() for tag in raw_tags.split(',') if tag.strip()]
    if isinstance(raw_tags, list):
        tags: List[str] = []
        for item in raw_tags:
            if isinstance(item, str):
                tag = item.strip()
                if tag:
                    tags.append(tag)
            elif isinstance(item, dict):
                for key in ('name', 'tag_name', 'label', 'value'):
                    val = item.get(key)
                    if isinstance(val, str) and val.strip():
                        tags.append(val.strip())
                        break
        return tags
    if isinstance(raw_tags, dict):
        items = raw_tags.get('tags') or raw_tags.get('items') or []
        return normalize_tags(items)
    return []


def normalize_contact(raw_contact: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(raw_contact, dict):
        return {}

    contact_id = raw_contact.get('id') or raw_contact.get('contactId') or raw_contact.get('contact_id') or ''
    email = (raw_contact.get('email') or '').strip().lower()
    first_name = (raw_contact.get('firstName') or raw_contact.get('first_name') or '').strip()
    last_name = (raw_contact.get('lastName') or raw_contact.get('last_name') or '').strip()

    custom_fields = raw_contact.get('customFields') or raw_contact.get('custom_fields') or {}
    workshop_code = ''
    if isinstance(custom_fields, dict):
        workshop_code = (
            custom_fields.get('workshop_code')
            or custom_fields.get('member_code')
            or custom_fields.get('workshopCode')
            or custom_fields.get('company')
            or ''
        )
    if not workshop_code:
        workshop_code = (raw_contact.get('workshop_code') or raw_contact.get('member_code') or '').strip().upper()

    tags = normalize_tags(raw_contact.get('tags'))

    return {
        'contact_id': str(contact_id).strip(),
        'email': email,
        'first_name': first_name,
        'last_name': last_name,
        'workshop_code': str(workshop_code).strip().upper(),
        'tags': tags,
    }


def fetch_ghl_contacts(limit: int = 100, max_total: int = 1000) -> List[Dict[str, Any]]:
    location_id = (getattr(settings, 'GHL_LOCATION_ID', '') or '').strip()
    if not location_id:
        raise ValueError('GHL_LOCATION_ID is not configured.')

    headers = get_ghl_headers()
    base_url = (getattr(settings, 'GHL_API_BASE_URL', 'https://services.leadconnectorhq.com') or '').rstrip('/')

    # GHL caps `limit` at 100 per page — paginate with startAfterId/startAfter
    # to fetch everything up to max_total instead of silently truncating results.
    page_limit = min(limit, 100)
    all_contacts: List[Dict[str, Any]] = []
    seen_ids: set = set()
    start_after_id = None
    start_after = None

    while len(all_contacts) < max_total:
        url = f'{base_url}/contacts/?locationId={location_id}&limit={page_limit}'
        if start_after_id:
            url += f'&startAfterId={start_after_id}'
        if start_after:
            url += f'&startAfter={start_after}'

        response = requests.get(url, headers=headers, timeout=20)
        if response.status_code != 200:
            logger.error('GHL contacts request failed: %s %s', response.status_code, response.text)
            raise ValueError(f'GHL sync failed with HTTP {response.status_code}.')

        data = response.json()
        if isinstance(data, dict):
            page_contacts = data.get('contacts') or data.get('data') or data.get('results') or []
        elif isinstance(data, list):
            page_contacts = data
        else:
            page_contacts = []

        if not page_contacts:
            break

        # Only keep contacts we haven't already seen. If the API ignores our
        # pagination cursor and returns the same page again, this stops the
        # loop instead of duplicating every contact up to max_total.
        new_contacts = []
        for item in page_contacts:
            if not isinstance(item, dict):
                continue
            item_id = item.get('id') or item.get('contactId')
            if item_id and item_id in seen_ids:
                continue
            if item_id:
                seen_ids.add(item_id)
            new_contacts.append(item)

        if not new_contacts:
            # Entire page was already seen — pagination cursor isn't advancing.
            break

        all_contacts.extend(new_contacts)

        if len(page_contacts) < page_limit:
            # Last page — fewer results than requested means no more remain.
            break

        last_contact = page_contacts[-1]
        start_after_id = last_contact.get('id') or last_contact.get('contactId')
        start_after = last_contact.get('dateAdded') or last_contact.get('dateUpdated')
        if not start_after_id:
            break

    return [normalize_contact(item) for item in all_contacts[:max_total] if isinstance(item, dict)]
