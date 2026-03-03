"""
WP Fusion SSO Integration — OAuth2 + Login-Time Sync

OAuth2 Authorization Code Grant flow via miniOrange OAuth Server.
Handles:
  1. Redirecting to WP for authorization
  2. Exchanging auth code for access token
  3. Fetching user profile from resource endpoint
  4. Parsing tags → role mapping
  5. Auto-provisioning new users on first SSO login
  6. Login-time sync (update portal DB if WP data changed)

FIELD MAPPING NOTE:
  The exact JSON field names from the resource endpoint are TBD.
  All field extraction is centralized in `_extract_user_data()` so
  it can be updated in one place once the payload is confirmed.
"""

import logging
import secrets
import requests
from django.conf import settings
from django.contrib.auth import get_user_model, login
from core.models import AuditLog

logger = logging.getLogger(__name__)
User = get_user_model()

# Roles assigned inside the portal that SSO should NEVER overwrite.
# Users with these roles also bypass the WP tag check on SSO login.
PORTAL_MANAGED_ROLES = {'technician', 'manager', 'administrator'}


# ============================================================================
# TAG → ROLE MAPPING
# ============================================================================
# Authentication is handled by GHL (GoHighLevel).
# Only TWO authorization tags are passed in the SSO call.
# Technician/Manager/Admin roles are managed inside the portal admin panel.
# ============================================================================

TAG_ROLE_MAP = {
    'portal access: member': 'member',
    'portal access: delegate': 'member',   # delegates use member role but are pure delegates
}

# Tags that indicate a pure delegate (admin assistant, no own cases)
# NOTE: All tag comparisons are CASE-INSENSITIVE (lowered before matching)
DELEGATE_TAGS = {'portal access: delegate'}

# Tags that indicate a member (advisor with own cases)
MEMBER_TAGS = {'portal access: member'}


def generate_state_token():
    """Generate a random state token for CSRF protection in OAuth2 flow."""
    return secrets.token_urlsafe(32)


def get_authorization_url(state):
    """
    Build the WP authorization URL to redirect the user to.
    
    Returns the full URL with query parameters.
    """
    params = {
        'client_id': settings.WP_OAUTH_CLIENT_ID,
        'redirect_uri': settings.WP_OAUTH_REDIRECT_URI,
        'response_type': 'code',
        'scope': 'openid profile email',
        'state': state,
        'prompt': 'login',  # Force WP to show login form (don't reuse existing session)
    }
    query_string = '&'.join(f'{k}={requests.utils.quote(str(v))}' for k, v in params.items())
    return f'{settings.WP_OAUTH_AUTHORIZE_URL}?{query_string}'


def exchange_code_for_token(code):
    """
    Exchange authorization code for access token (Step 5 of OAuth flow).
    
    Returns dict with access_token, or raises an exception.
    """
    data = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': settings.WP_OAUTH_REDIRECT_URI,
        'client_id': settings.WP_OAUTH_CLIENT_ID,
        'client_secret': settings.WP_OAUTH_CLIENT_SECRET,
    }
    
    response = requests.post(
        settings.WP_OAUTH_TOKEN_URL,
        data=data,
        timeout=15,
    )
    
    if response.status_code != 200:
        logger.error(f'Token exchange failed: {response.status_code} — {response.text}')
        raise SSOError(f'Token exchange failed (HTTP {response.status_code})')
    
    token_data = response.json()
    
    if 'access_token' not in token_data:
        logger.error(f'No access_token in response: {token_data}')
        raise SSOError('No access_token in token response')
    
    return token_data


def fetch_user_profile(access_token):
    """
    Fetch user profile from the WP resource endpoint (Step 6 of OAuth flow).
    
    Returns the raw JSON dict from the resource endpoint.
    """
    response = requests.get(
        settings.WP_OAUTH_RESOURCE_URL,
        headers={'Authorization': f'Bearer {access_token}'},
        timeout=15,
    )
    
    if response.status_code != 200:
        logger.error(f'Resource fetch failed: {response.status_code} — {response.text}')
        raise SSOError(f'Resource fetch failed (HTTP {response.status_code})')
    
    return response.json()


# ============================================================================
# FIELD EXTRACTION — Update this when payload is confirmed
# ============================================================================

def _extract_user_data(profile_data):
    """
    Extract normalized user data from the WP resource endpoint response.
    
    This is the SINGLE PLACE to update when the actual JSON field names
    are confirmed from the resource endpoint.
    
    Confirmed field mapping (from WP developer, 2026-03-01):
        contact_id  → GHL contact ID string (e.g. "Kzqrc450LtP3s461wVAz")
        email       → user email
        first_name  → first name
        last_name   → last name
        username    → WP username
        member_code → workshop/member code (e.g. "ABC")
        wpf_tags    → list of tag strings from WP Fusion
    
    Returns a dict with normalized keys:
        contact_id, email, first_name, last_name, username,
        workshop_code, phone, tags (list of tag names)
    """
    # Contact ID — GHL contact ID (string, NOT integer)
    contact_id = profile_data.get('contact_id', '') or ''
    
    # Basic identity
    email = profile_data.get('email', '')
    first_name = profile_data.get('first_name', '')
    last_name = profile_data.get('last_name', '')
    username = profile_data.get('username', '') or (email.split('@')[0] if email else '')
    
    # Member/workshop code
    workshop_code = profile_data.get('member_code', '')
    
    # Phone (not in current payload, but may be added later)
    phone = profile_data.get('phone', '')
    
    # WP Fusion tags — confirmed as list of strings in "wpf_tags" field
    raw_tags = profile_data.get('wpf_tags', [])
    
    # Normalize tags to a list of strings
    tags = _normalize_tags(raw_tags)
    
    # Only title-case names that are all lowercase (e.g. 'dale' -> 'Dale')
    # Preserve intentional mixed case like McGregor, McDonald, DeLuca
    def _smart_case(name):
        s = name.strip()
        return s.title() if s == s.lower() else s

    return {
        'contact_id': str(contact_id).strip() if contact_id else '',
        'email': email.strip().lower() if email else '',
        'first_name': _smart_case(first_name) if first_name else '',
        'last_name': _smart_case(last_name) if last_name else '',
        'username': username.strip().lower() if username else '',
        'workshop_code': workshop_code.strip().upper() if workshop_code else '',
        'phone': phone.strip() if phone else '',
        'tags': tags,
    }


def _normalize_tags(raw_tags):
    """
    Normalize tags from various formats into a flat list of strings.
    
    Handles:
    - List of strings: ['Portal: Member', 'Portal: Delegate']
    - List of dicts: [{'name': 'Portal: Member'}, ...]
    - Comma-separated string: 'Portal: Member, Portal: Delegate'
    - Nested under a key: {'tags': [...]} 
    """
    if isinstance(raw_tags, str):
        return [t.strip() for t in raw_tags.split(',') if t.strip()]
    
    if isinstance(raw_tags, list):
        result = []
        for tag in raw_tags:
            if isinstance(tag, str):
                result.append(tag.strip())
            elif isinstance(tag, dict):
                # Try common keys
                name = tag.get('name') or tag.get('tag_name') or tag.get('label') or ''
                if name:
                    result.append(name.strip())
        return result
    
    return []


# ============================================================================
# ROLE DETERMINATION FROM TAGS
# ============================================================================

def determine_role_from_tags(tags):
    """
    Determine the Django role based on authorization tags.
    
    Only TWO tags are used for SSO authorization:
    1. 'Portal access: Member' → role='member' (advisors)
    2. 'Portal access: Delegate' → role='member' (pure delegates / admin assistants)
    
    Technician, Manager, and Administrator roles are created
    directly in the portal admin panel — NOT via SSO tags.
    
    Tag matching is CASE-INSENSITIVE.
    
    Returns (role, is_pure_delegate, has_access)
    """
    # Lowercase all tags for case-insensitive matching
    tag_set = {t.lower().strip() for t in tags if isinstance(t, str)}
    
    logger.info(f'SSO tag check — received tags (lowered): {tag_set}')
    logger.info(f'SSO tag check — looking for member={MEMBER_TAGS}, delegate={DELEGATE_TAGS}')
    
    has_member = bool(tag_set & MEMBER_TAGS)
    has_delegate = bool(tag_set & DELEGATE_TAGS)
    
    if has_member:
        # Member (advisor) — may also be a delegate, but role is 'member'
        return 'member', False, True
    
    if has_delegate:
        # Pure delegate (admin assistant) — uses 'member' role but no own cases
        return 'member', True, True
    
    # No portal tags — no access
    return None, False, False


# ============================================================================
# USER PROVISIONING + LOGIN-TIME SYNC
# ============================================================================

def get_or_create_user_from_sso(profile_data, request=None):
    """
    Match or create a Django user from SSO resource endpoint data.
    
    Matching order:
    1. By contact_id (immutable CRM link)
    2. By email (fallback for first-time SSO before contact_id is set)
    
    On every login:
    - Sync name, email, workshop_code, phone from WP
    - Update role if tags changed
    - Log all changes to AuditLog
    
    Returns (user, created, changes_dict) or raises SSOError.
    """
    data = _extract_user_data(profile_data)
    
    contact_id = data['contact_id']
    email = data['email']
    tags = data['tags']
    
    if not contact_id and not email:
        raise SSOError('No contact_id or email in resource response — cannot identify user')
    
    # Determine role from tags
    role, is_pure_delegate, has_access = determine_role_from_tags(tags)
    
    # Bypass tag check for existing users with portal-managed roles.
    # Admins, technicians, and managers can always SSO in — their roles are
    # assigned inside the portal, not controlled by WP tags.
    if not has_access:
        existing_user = None
        if contact_id:
            existing_user = User.objects.filter(contact_id=contact_id).first()
        if not existing_user and email:
            existing_user = User.objects.filter(email__iexact=email).first()
        
        if existing_user and existing_user.role in PORTAL_MANAGED_ROLES:
            logger.info(f'SSO tag bypass — {email} has portal-managed role '
                        f"'{existing_user.role}', skipping tag requirement")
            role = existing_user.role  # Keep their current role
            has_access = True
        else:
            raise SSOAccessDenied('No portal access tag found. Contact your administrator.')
    
    # Check email allowlist (TEST server gate)
    # Sources: DB model (SSOAllowedEmail) + env var (SSO_ALLOWED_EMAILS)
    # If EITHER has entries, only listed emails can SSO in.
    # If BOTH are empty, all tagged users can SSO in (production behavior).
    from .models import SSOAllowedEmail
    db_emails = set(SSOAllowedEmail.objects.values_list('email', flat=True))
    env_emails = set(getattr(settings, 'SSO_ALLOWED_EMAILS', []))
    allowed_emails = db_emails | env_emails
    
    if allowed_emails and email.lower() not in allowed_emails:
        logger.warning(f'SSO blocked by allowlist: {email} not in allowed emails')
        raise SSOAccessDenied('Access to this portal instance is restricted. Contact your administrator.')
    
    # Try to find existing user
    user = None
    created = False
    
    if contact_id:
        try:
            user = User.objects.get(contact_id=contact_id)
        except User.DoesNotExist:
            pass
    
    if not user and email:
        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            pass
        except User.MultipleObjectsReturned:
            user = User.objects.filter(email__iexact=email).first()
    
    changes = {}
    
    if user:
        # ---- EXISTING USER: login-time sync ----
        changes = _sync_user_fields(user, data, role)
        
        if changes:
            user.save()
            logger.info(f'SSO sync updated user {user.username}: {changes}')
            
            # Log changes to AuditLog
            if request:
                AuditLog.objects.create(
                    user=user,
                    action_type='sso_sync',
                    description=f'SSO login-time sync updated {user.get_full_name()} ({user.email})',
                    related_user=user,
                    changes=changes,
                    metadata={
                        'contact_id': contact_id,
                        'tags': tags,
                    },
                    ip_address=_get_client_ip(request),
                )
    else:
        # ---- NEW USER: auto-provision ----
        username = _generate_unique_username(data['username'] or data['email'].split('@')[0])
        
        user = User.objects.create(
            username=username,
            email=data['email'],
            first_name=data['first_name'],
            last_name=data['last_name'],
            contact_id=contact_id,
            role=role,
            workshop_code=data['workshop_code'],
            phone=data['phone'],
            is_active=True,
        )
        # SSO users don't use Django passwords
        user.set_unusable_password()
        user.save()
        created = True
        
        logger.info(f'SSO auto-provisioned new user: {user.username} (contact_id={contact_id}, role={role})')
        
        if request:
            AuditLog.objects.create(
                user=user,
                action_type='sso_auto_provision',
                description=f'SSO auto-provisioned new user: {user.get_full_name()} ({user.email}, role={role})',
                related_user=user,
                metadata={
                    'contact_id': contact_id,
                    'role': role,
                    'is_pure_delegate': is_pure_delegate,
                    'tags': tags,
                    'email': data['email'],
                },
                ip_address=_get_client_ip(request),
            )
    
    # Ensure user is active
    if not user.is_active:
        raise SSOAccessDenied('Your portal account has been deactivated. Contact your administrator.')
    
    return user, created, changes


def _sync_user_fields(user, data, new_role):
    """
    Compare WP data against stored portal data and update if changed.
    
    Returns a dict of {field: {'old': ..., 'new': ...}} for all changed fields.
    """
    changes = {}
    
    # contact_id — set if not already stored
    if data['contact_id'] and not user.contact_id:
        changes['contact_id'] = {'old': None, 'new': data['contact_id']}
        user.contact_id = data['contact_id']
    
    # email
    if data['email'] and data['email'] != user.email.lower():
        changes['email'] = {'old': user.email, 'new': data['email']}
        user.email = data['email']
    
    # first_name
    if data['first_name'] and data['first_name'] != user.first_name:
        changes['first_name'] = {'old': user.first_name, 'new': data['first_name']}
        user.first_name = data['first_name']
    
    # last_name
    if data['last_name'] and data['last_name'] != user.last_name:
        changes['last_name'] = {'old': user.last_name, 'new': data['last_name']}
        user.last_name = data['last_name']
    
    # workshop_code
    if data['workshop_code'] and data['workshop_code'] != user.workshop_code:
        changes['workshop_code'] = {'old': user.workshop_code, 'new': data['workshop_code']}
        user.workshop_code = data['workshop_code']
    
    # phone
    if data['phone'] and data['phone'] != user.phone:
        changes['phone'] = {'old': user.phone, 'new': data['phone']}
        user.phone = data['phone']
    
    # role — only update for member/delegate roles (SSO-managed).
    # NEVER overwrite portal-assigned roles (technician, manager, administrator).
    # Those are set manually in /admin/ and must be preserved.
    if new_role and new_role != user.role and user.role not in PORTAL_MANAGED_ROLES:
        changes['role'] = {'old': user.role, 'new': new_role}
        user.role = new_role
    
    return changes


def _generate_unique_username(base_username):
    """Generate a unique username, appending numbers if necessary."""
    username = base_username[:30]  # Django max 150, but keep it short
    if not User.objects.filter(username=username).exists():
        return username
    
    for i in range(1, 1000):
        candidate = f'{username}{i}'
        if not User.objects.filter(username=candidate).exists():
            return candidate
    
    # Fallback
    return f'{username}_{secrets.token_hex(4)}'


def _get_client_ip(request):
    """Get client IP from request, handling proxied requests."""
    x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded:
        return x_forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


# ============================================================================
# EXCEPTIONS
# ============================================================================

class SSOError(Exception):
    """General SSO error."""
    pass


class SSOAccessDenied(SSOError):
    """User does not have portal access tags."""
    pass
