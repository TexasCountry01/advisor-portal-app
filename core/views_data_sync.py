"""
Data Sync Panel — Pull users/cases from PROD to TEST/LOCAL.

Hidden admin tool accessible at /data-sync/ with access code validation.
Uses SSH to call `python manage.py export_data` on PROD, then imports locally.
"""
import json
import logging
import os
import re
import shutil
import subprocess
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from accounts.models import MemberCreditAllowance, MemberDelegate, User
from core.models import AuditLog, SystemSettings

logger = logging.getLogger(__name__)

# Safe patterns for inputs passed to SSH commands
_EMAIL_RE = re.compile(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$')
_CASE_ID_RE = re.compile(r'^[A-Za-z0-9\-]+$')

# ---------------------------------------------------------------------------
# SSH helpers
# ---------------------------------------------------------------------------

def _get_ssh_config():
    """Return (user, host, app_path) for PROD SSH."""
    return (
        getattr(settings, 'PROD_SSH_USER', 'dev'),
        getattr(settings, 'PROD_SSH_HOST', '104.248.126.74'),
        getattr(settings, 'PROD_SSH_APP_PATH', '/var/www/advisor-portal'),
    )


def _ssh_export(args_str, timeout=45):
    """
    SSH into PROD and run `python manage.py export_data <args_str>`.
    Returns parsed JSON or raises RuntimeError.
    args_str must already be sanitized by callers.
    """
    user, host, path = _get_ssh_config()
    cmd = (
        f'cd {path} && source venv/bin/activate && '
        f'python manage.py export_data {args_str}'
    )
    ssh_bin = shutil.which('ssh') or '/usr/bin/ssh'
    result = subprocess.run(
        [ssh_bin, '-o', 'StrictHostKeyChecking=accept-new',
         '-o', 'ConnectTimeout=10', f'{user}@{host}', cmd],
        capture_output=True, text=True, timeout=timeout,
    )
    if result.returncode != 0:
        raise RuntimeError(f'SSH command failed: {result.stderr.strip()}')
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as e:
        raise RuntimeError(f'Invalid JSON from PROD: {e}\nOutput: {result.stdout[:500]}')


def _scp_file(remote_path, local_path, timeout=60):
    """SCP a single file from PROD media/ to local media/."""
    user, host, app_path = _get_ssh_config()
    remote_full = f'{user}@{host}:{app_path}/media/{remote_path}'
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    scp_bin = shutil.which('scp') or '/usr/bin/scp'
    result = subprocess.run(
        [scp_bin, '-o', 'StrictHostKeyChecking=accept-new',
         '-o', 'ConnectTimeout=10', remote_full, local_path],
        capture_output=True, text=True, timeout=timeout,
    )
    if result.returncode != 0:
        raise RuntimeError(f'SCP failed for {remote_path}: {result.stderr.strip()}')


# ---------------------------------------------------------------------------
# Access validation
# ---------------------------------------------------------------------------

def _validate_access(request):
    """
    Check session for valid access code. Returns (is_valid, access_level).
    access_level: 'dev' or 'admin'
    """
    return request.session.get('data_sync_access', None)


def _check_access_code(code):
    """
    Validate an access code against SystemSettings.
    Returns 'dev', 'admin', or None.
    """
    s = SystemSettings.get_settings()
    if s.dev_sync_code and code == s.dev_sync_code:
        return 'dev'
    if s.admin_sync_code and code == s.admin_sync_code:
        return 'admin'
    return None


# ---------------------------------------------------------------------------
# User import helpers
# ---------------------------------------------------------------------------

def _resolve_user_by_email(email):
    """Find a local user by email (case-insensitive). Returns User or None."""
    if not email:
        return None
    try:
        return User.objects.get(email__iexact=email.strip())
    except User.DoesNotExist:
        return None


def _import_user(user_data, request_user=None):
    """
    Create or update a local user from exported user_data dict.
    Returns (user, created, changes_summary).
    """
    email = user_data['email'].strip().lower()
    changes = []

    try:
        user = User.objects.get(email__iexact=email)
        created = False
        # Update fields that differ
        sync_fields = [
            'first_name', 'last_name', 'role', 'contact_id', 'user_level',
            'workshop_code', 'is_pure_delegate', 'notification_email',
            'phone', 'is_active', 'is_test_account',
        ]
        for field in sync_fields:
            new_val = user_data.get(field, '')
            old_val = getattr(user, field) or ''
            # Normalize booleans
            if isinstance(new_val, bool):
                old_val = bool(old_val)
            if str(new_val) != str(old_val):
                changes.append(f'{field}: {old_val!r} → {new_val!r}')
                setattr(user, field, new_val)
        if changes:
            user.save()
    except User.DoesNotExist:
        # Create new user with SSO-compatible username
        username = email.split('@')[0]
        # Ensure unique username
        base_username = username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f'{base_username}{counter}'
            counter += 1
        user = User.objects.create(
            email=email,
            username=username,
            first_name=user_data.get('first_name', ''),
            last_name=user_data.get('last_name', ''),
            role=user_data.get('role', 'member'),
            contact_id=user_data.get('contact_id', '') or None,
            user_level=user_data.get('user_level', '') or None,
            workshop_code=user_data.get('workshop_code', ''),
            is_pure_delegate=user_data.get('is_pure_delegate', False),
            notification_email=user_data.get('notification_email', ''),
            phone=user_data.get('phone', ''),
            font_size=user_data.get('font_size', '100'),
            is_active=user_data.get('is_active', True),
            is_test_account=user_data.get('is_test_account', False),
        )
        # Set unusable password — SSO handles auth
        user.set_unusable_password()
        user.save()
        created = True
        changes.append('created new user')

    return user, created, changes


def _import_delegates(member, delegates_data, request_user=None):
    """
    Replace all delegates for a member with PROD data.
    Deletes existing, creates fresh from export.
    Returns summary list.
    """
    summary = []
    existing = list(MemberDelegate.objects.filter(member=member).values_list(
        'delegate__email', flat=True
    ))
    MemberDelegate.objects.filter(member=member).delete()
    if existing:
        summary.append(f'Cleared {len(existing)} existing delegate(s)')

    for d in delegates_data:
        delegate_user, d_created, _ = _import_user(d['delegate_user'])
        assigned_by = _resolve_user_by_email(d.get('assigned_by_email', ''))
        MemberDelegate.objects.create(
            member=member,
            delegate=delegate_user,
            assigned_by=assigned_by,
        )
        action = 'created+assigned' if d_created else 'assigned'
        summary.append(f'{action} delegate: {delegate_user.email}')

    return summary


def _import_credits(member, credits_data, request_user=None):
    """Import credit allowances for a member (upsert by fiscal_year+quarter)."""
    summary = []
    for c in credits_data:
        configured_by = _resolve_user_by_email(c.get('configured_by_email', ''))
        ca, created = MemberCreditAllowance.objects.update_or_create(
            member=member,
            fiscal_year=c['fiscal_year'],
            quarter=c['quarter'],
            defaults={
                'allowed_credits': c['allowed_credits'],
                'configured_by': configured_by,
                'notes': c.get('notes', ''),
            },
        )
        action = 'created' if created else 'updated'
        summary.append(f'{action} FY{c["fiscal_year"]} Q{c["quarter"]}: {c["allowed_credits"]} credits')
    return summary


# ---------------------------------------------------------------------------
# Case import helpers
# ---------------------------------------------------------------------------

def _parse_datetime(val):
    """Parse an ISO datetime string, return datetime or None."""
    if not val:
        return None
    if isinstance(val, datetime):
        return val
    try:
        return datetime.fromisoformat(val)
    except (ValueError, TypeError):
        return None


def _parse_date(val):
    """Parse an ISO date string, return date or None."""
    if not val:
        return None
    if isinstance(val, date) and not isinstance(val, datetime):
        return val
    try:
        if isinstance(val, str) and 'T' in val:
            return datetime.fromisoformat(val).date()
        return date.fromisoformat(val)
    except (ValueError, TypeError):
        return None


def _parse_decimal(val):
    """Parse a decimal value, return Decimal or None."""
    if val is None or val == '':
        return None
    try:
        return Decimal(str(val))
    except (InvalidOperation, ValueError):
        return None


def _import_case_data(case_export, request_user=None):
    """
    Import a full case export (from --case output).
    Auto-imports member if needed.
    Returns (case, summary_log).
    """
    from cases.models import (
        Case, CaseChangeRequest, CaseDocument, CaseMessage,
        CaseNote, CaseNotification, CaseReport, CaseReviewHistory,
        CreditAuditLog,
    )
    from cases.models_fact_finder import FederalFactFinder

    summary = []
    cd = case_export['case']

    # --- Auto-import member if needed ---
    member_data = case_export.get('member_data')
    if member_data:
        member, m_created, m_changes = _import_user(member_data['user'])
        if m_created:
            summary.append(f'Auto-created member: {member.email}')
        elif m_changes:
            summary.append(f'Updated member: {member.email} ({", ".join(m_changes)})')
        # Import delegates for this member
        delegate_summary = _import_delegates(member, member_data.get('delegates', []))
        summary.extend(delegate_summary)
    else:
        member = _resolve_user_by_email(cd['member_email'])

    # --- Resolve user FKs ---
    created_by = _resolve_user_by_email(cd.get('created_by_email', ''))
    assigned_to = _resolve_user_by_email(cd.get('assigned_to_email', ''))
    reviewed_by = _resolve_user_by_email(cd.get('reviewed_by_email', ''))
    accepted_by = _resolve_user_by_email(cd.get('accepted_by_email', ''))
    rejected_by = _resolve_user_by_email(cd.get('rejected_by_email', ''))
    original_case = None
    if cd.get('original_case_id'):
        try:
            original_case = Case.objects.get(external_case_id=cd['original_case_id'])
        except Case.DoesNotExist:
            pass

    # --- Create or update the case ---
    case_fields = {
        'workshop_code': cd.get('workshop_code', ''),
        'member': member,
        'created_by': created_by,
        'assigned_to': assigned_to,
        'reviewed_by': reviewed_by,
        'accepted_by': accepted_by,
        'rejected_by': rejected_by,
        'original_case': original_case,
        'employee_first_name': cd.get('employee_first_name', ''),
        'employee_last_name': cd.get('employee_last_name', ''),
        'client_email': cd.get('client_email', ''),
        'num_reports_requested': cd.get('num_reports_requested', 1),
        'urgency': cd.get('urgency', 'normal'),
        'status': cd.get('status', 'submitted'),
        'hold_reason': cd.get('hold_reason', ''),
        'hold_start_date': _parse_datetime(cd.get('hold_start_date')),
        'hold_end_date': _parse_datetime(cd.get('hold_end_date')),
        'hold_duration_days': _parse_decimal(cd.get('hold_duration_days')),
        'status_before_hold': cd.get('status_before_hold', ''),
        'reviewed_at': _parse_datetime(cd.get('reviewed_at')),
        'review_notes': cd.get('review_notes', ''),
        'review_status': cd.get('review_status') or None,
        'tier': cd.get('tier', ''),
        'date_accepted': _parse_datetime(cd.get('date_accepted')),
        'date_due': _parse_date(cd.get('date_due')),
        'date_scheduled': _parse_date(cd.get('date_scheduled')),
        'date_completed': _parse_datetime(cd.get('date_completed')),
        'scheduled_release_date': _parse_datetime(cd.get('scheduled_release_date')),
        'actual_release_date': _parse_datetime(cd.get('actual_release_date')),
        'scheduled_email_date': _parse_datetime(cd.get('scheduled_email_date')),
        'actual_email_sent_date': _parse_datetime(cd.get('actual_email_sent_date')),
        'rejection_reason': cd.get('rejection_reason') or None,
        'rejection_notes': cd.get('rejection_notes', ''),
        'date_rejected': _parse_datetime(cd.get('date_rejected')),
        'reassignment_history': cd.get('reassignment_history', []),
        'report_notes_to_member': cd.get('report_notes_to_member', ''),
        'report_notes': cd.get('report_notes', []),
        'fact_finder_data': cd.get('fact_finder_data', {}),
        'fact_finder_pdf_status': cd.get('fact_finder_pdf_status', 'pending'),
        'fact_finder_pdf_generated_at': _parse_datetime(cd.get('fact_finder_pdf_generated_at')),
        'special_notes': cd.get('special_notes', ''),
        'retirement_date_preference': _parse_date(cd.get('retirement_date_preference')),
        'api_sync_status': cd.get('api_sync_status', 'pending'),
        'api_synced_at': _parse_datetime(cd.get('api_synced_at')),
        'credit_value': _parse_decimal(cd.get('credit_value')),
        'credit_adjustment_reason': cd.get('credit_adjustment_reason', ''),
        'is_resubmitted': cd.get('is_resubmitted', False),
        'resubmission_count': cd.get('resubmission_count', 0),
        'previous_status': cd.get('previous_status', ''),
        'resubmission_date': _parse_datetime(cd.get('resubmission_date')),
        'resubmission_notes': cd.get('resubmission_notes', ''),
        'has_member_updates': cd.get('has_member_updates', False),
        'member_last_update_date': _parse_datetime(cd.get('member_last_update_date')),
        'has_member_change_request': cd.get('has_member_change_request', False),
        'has_member_new_info': cd.get('has_member_new_info', False),
        'has_profeds_error': cd.get('has_profeds_error', False),
        'error_modification_count': cd.get('error_modification_count', 0),
        'notes': cd.get('notes', ''),
    }

    try:
        case = Case.objects.get(external_case_id=cd['external_case_id'])
        for k, v in case_fields.items():
            setattr(case, k, v)
        case.save()
        case_created = False
        summary.append(f'Updated existing case: {cd["external_case_id"]}')
    except Case.DoesNotExist:
        case = Case(**case_fields, external_case_id=cd['external_case_id'])
        case.save()
        case_created = True
        summary.append(f'Created case: {cd["external_case_id"]}')

    # --- Documents (create only if not already exists by filename+case) ---
    for doc in case_export.get('documents', []):
        existing = CaseDocument.objects.filter(
            case=case, original_filename=doc['original_filename']
        ).exists()
        if existing:
            summary.append(f'Skipped existing doc: {doc["original_filename"]}')
            continue
        uploaded_by = _resolve_user_by_email(doc.get('uploaded_by_email', ''))
        new_doc = CaseDocument(
            case=case,
            document_type=doc.get('document_type', 'other'),
            original_filename=doc.get('original_filename', ''),
            file_size=doc.get('file_size', 0),
            uploaded_by=uploaded_by,
            notes=doc.get('notes', ''),
        )
        # Handle file transfer via SCP
        if doc.get('file_path'):
            media_root = str(settings.MEDIA_ROOT)
            local_path = os.path.join(media_root, doc['file_path'])
            try:
                _scp_file(doc['file_path'], local_path)
                new_doc.file.name = doc['file_path']
                summary.append(f'Transferred doc: {doc["original_filename"]}')
            except RuntimeError as e:
                summary.append(f'SCP failed for {doc["original_filename"]}: {e}')
                continue
        new_doc.save()

    # --- Reports ---
    for r in case_export.get('reports', []):
        existing = CaseReport.objects.filter(
            case=case, report_number=r['report_number']
        ).exists()
        if existing:
            continue
        new_report = CaseReport(
            case=case,
            report_number=r['report_number'],
            status=r.get('status', 'pending'),
            assigned_to=_resolve_user_by_email(r.get('assigned_to_email', '')),
            reviewed_by=_resolve_user_by_email(r.get('reviewed_by_email', '')),
            notes=r.get('notes', ''),
            started_at=_parse_datetime(r.get('started_at')),
            completed_at=_parse_datetime(r.get('completed_at')),
        )
        if r.get('report_file_path'):
            media_root = str(settings.MEDIA_ROOT)
            local_path = os.path.join(media_root, r['report_file_path'])
            try:
                _scp_file(r['report_file_path'], local_path)
                new_report.report_file.name = r['report_file_path']
                summary.append(f'Transferred report #{r["report_number"]}')
            except RuntimeError as e:
                summary.append(f'SCP failed for report #{r["report_number"]}: {e}')
        new_report.save()

    # --- Notes ---
    if case_created:
        for n in case_export.get('notes', []):
            CaseNote.objects.create(
                case=case,
                author=_resolve_user_by_email(n.get('author_email', '')),
                note=n.get('note', ''),
                is_internal=n.get('is_internal', True),
            )
        if case_export.get('notes'):
            summary.append(f'Imported {len(case_export["notes"])} note(s)')

    # --- Messages ---
    if case_created:
        for m in case_export.get('messages', []):
            CaseMessage.objects.create(
                case=case,
                author=_resolve_user_by_email(m.get('author_email', '')),
                message=m.get('message', ''),
            )
        if case_export.get('messages'):
            summary.append(f'Imported {len(case_export["messages"])} message(s)')

    # --- Review History ---
    if case_created:
        for rh in case_export.get('review_history', []):
            CaseReviewHistory.objects.create(
                case=case,
                reviewed_by=_resolve_user_by_email(rh.get('reviewed_by_email', '')),
                original_technician=_resolve_user_by_email(rh.get('original_technician_email', '')),
                review_action=rh.get('review_action', 'approved'),
                review_notes=rh.get('review_notes', ''),
            )
        if case_export.get('review_history'):
            summary.append(f'Imported {len(case_export["review_history"])} review history record(s)')

    # --- Change Requests ---
    if case_created:
        for cr in case_export.get('change_requests', []):
            CaseChangeRequest.objects.create(
                case=case,
                member=_resolve_user_by_email(cr.get('member_email', '')) or member,
                request_type=cr.get('request_type', 'additional_info'),
                requested_due_date=_parse_date(cr.get('requested_due_date')),
                cancellation_reason=cr.get('cancellation_reason', ''),
                member_notes=cr.get('member_notes', ''),
                status=cr.get('status', 'pending'),
                technician_response_notes=cr.get('technician_response_notes', ''),
                reviewed_by=_resolve_user_by_email(cr.get('reviewed_by_email', '')),
                reviewed_at=_parse_datetime(cr.get('reviewed_at')),
            )
        if case_export.get('change_requests'):
            summary.append(f'Imported {len(case_export["change_requests"])} change request(s)')

    # --- Notifications ---
    if case_created:
        for n in case_export.get('notifications', []):
            CaseNotification.objects.create(
                case=case,
                member=_resolve_user_by_email(n.get('member_email', '')) or member,
                notification_type=n.get('notification_type', 'case_released'),
                title=n.get('title', ''),
                message=n.get('message', ''),
                hold_reason=n.get('hold_reason', ''),
                is_read=n.get('is_read', False),
            )

    # --- Credit Audit Logs ---
    if case_created:
        for cal in case_export.get('credit_audit_logs', []):
            CreditAuditLog.objects.create(
                case=case,
                adjusted_by=_resolve_user_by_email(cal.get('adjusted_by_email', '')),
                credit_value_before=_parse_decimal(cal.get('credit_value_before')),
                credit_value_after=_parse_decimal(cal.get('credit_value_after', '0')),
                adjustment_reason=cal.get('adjustment_reason', ''),
                adjustment_context=cal.get('adjustment_context', 'update'),
            )

    # --- Fact Finder ---
    fff_data = case_export.get('fact_finder')
    if fff_data:
        try:
            fff = FederalFactFinder.objects.get(case=case)
            # Update existing
            for field_name, val in fff_data.items():
                if field_name in ('case', 'created_at', 'updated_at', 'case_id'):
                    continue
                field = FederalFactFinder._meta.get_field(field_name)
                if hasattr(field, 'get_internal_type'):
                    ft = field.get_internal_type()
                    if ft in ('DateField',):
                        val = _parse_date(val)
                    elif ft in ('DateTimeField',):
                        val = _parse_datetime(val)
                    elif ft in ('DecimalField',):
                        val = _parse_decimal(val)
                setattr(fff, field_name, val)
            fff.save()
            summary.append('Updated fact finder')
        except FederalFactFinder.DoesNotExist:
            fff = FederalFactFinder(case=case)
            for field_name, val in fff_data.items():
                if field_name in ('case', 'created_at', 'updated_at', 'case_id'):
                    continue
                field = FederalFactFinder._meta.get_field(field_name)
                if hasattr(field, 'get_internal_type'):
                    ft = field.get_internal_type()
                    if ft in ('DateField',):
                        val = _parse_date(val)
                    elif ft in ('DateTimeField',):
                        val = _parse_datetime(val)
                    elif ft in ('DecimalField',):
                        val = _parse_decimal(val)
                setattr(fff, field_name, val)
            fff.save()
            summary.append('Created fact finder')

    return case, summary


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------

@login_required
def data_sync_panel(request):
    """Main data sync panel — requires access code in session."""
    access = _validate_access(request)
    return render(request, 'core/data_sync.html', {
        'access_level': access,
    })


@require_POST
@login_required
def data_sync_authenticate(request):
    """Validate access code and store in session."""
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid request'}, status=400)

    code = body.get('code', '').strip()
    if not code:
        return JsonResponse({'error': 'Access code required'}, status=400)

    level = _check_access_code(code)
    if not level:
        return JsonResponse({'error': 'Invalid access code'}, status=403)

    request.session['data_sync_access'] = level
    return JsonResponse({'access_level': level})


@require_GET
@login_required
def data_sync_list_members(request):
    """AJAX: List PROD members for dropdown."""
    access = _validate_access(request)
    if not access:
        return JsonResponse({'error': 'Not authenticated'}, status=403)
    try:
        data = _ssh_export('--list-members')
        return JsonResponse({'members': data})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_GET
@login_required
def data_sync_list_staff(request):
    """AJAX: List PROD staff for dropdown."""
    access = _validate_access(request)
    if not access:
        return JsonResponse({'error': 'Not authenticated'}, status=403)
    try:
        data = _ssh_export('--list-staff')
        return JsonResponse({'staff': data})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_GET
@login_required
def data_sync_list_cases(request):
    """AJAX: List PROD cases for dropdown."""
    access = _validate_access(request)
    if not access:
        return JsonResponse({'error': 'Not authenticated'}, status=403)
    try:
        data = _ssh_export('--list-cases', timeout=45)
        return JsonResponse({'cases': data})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# Safe pattern for search queries passed to SSH
_SEARCH_QUERY_RE = re.compile(r'^[a-zA-Z0-9 \.\'\-]+$')


@require_GET
@login_required
def data_sync_search_cases(request):
    """AJAX: Search PROD cases by employee/member name."""
    access = _validate_access(request)
    if not access:
        return JsonResponse({'error': 'Not authenticated'}, status=403)
    query = request.GET.get('q', '').strip()
    if not query or len(query) < 2:
        return JsonResponse({'error': 'Search query must be at least 2 characters'}, status=400)
    if len(query) > 100:
        return JsonResponse({'error': 'Search query too long'}, status=400)
    if not _SEARCH_QUERY_RE.match(query):
        return JsonResponse({'error': 'Invalid characters in search query'}, status=400)
    try:
        data = _ssh_export(f'--search-cases "{query}"', timeout=45)
        return JsonResponse({'cases': data})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_POST
@login_required
def data_sync_pull_member(request):
    """Pull a member (user + delegates + credits) from PROD."""
    access = _validate_access(request)
    if not access:
        return JsonResponse({'error': 'Not authenticated'}, status=403)
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid request'}, status=400)

    email = body.get('email', '').strip()
    if not email:
        return JsonResponse({'error': 'Member email required'}, status=400)
    if not _EMAIL_RE.match(email):
        return JsonResponse({'error': 'Invalid email format'}, status=400)

    try:
        data = _ssh_export(f'--member {email}')
        if 'error' in data:
            return JsonResponse({'error': data['error']}, status=404)

        # Import user
        user, created, changes = _import_user(data['user'])
        summary = []
        if created:
            summary.append(f'Created member: {user.email}')
        elif changes:
            summary.append(f'Updated member: {user.email} ({", ".join(changes)})')
        else:
            summary.append(f'Member unchanged: {user.email}')

        # Import delegates
        delegate_summary = _import_delegates(user, data.get('delegates', []))
        summary.extend(delegate_summary)

        # Import credits
        credit_summary = _import_credits(user, data.get('credit_allowances', []))
        summary.extend(credit_summary)

        # Audit log
        AuditLog.log_activity(
            user=request.user,
            action_type='data_sync',
            description=f'Pulled member from PROD: {email}',
            related_user=user,
            metadata={'summary': summary, 'access_level': access},
            ip_address=request.META.get('REMOTE_ADDR'),
        )

        return JsonResponse({'success': True, 'summary': summary})
    except Exception as e:
        logger.exception(f'data_sync_pull_member failed for {email}')
        return JsonResponse({'error': str(e)}, status=500)


@require_POST
@login_required
def data_sync_pull_staff(request):
    """Pull a staff user from PROD."""
    access = _validate_access(request)
    if not access:
        return JsonResponse({'error': 'Not authenticated'}, status=403)
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid request'}, status=400)

    email = body.get('email', '').strip()
    if not email:
        return JsonResponse({'error': 'Staff email required'}, status=400)
    if not _EMAIL_RE.match(email):
        return JsonResponse({'error': 'Invalid email format'}, status=400)

    try:
        data = _ssh_export(f'--staff {email}')
        if 'error' in data:
            return JsonResponse({'error': data['error']}, status=404)

        user, created, changes = _import_user(data['user'])
        summary = []
        if created:
            summary.append(f'Created staff user: {user.email}')
        elif changes:
            summary.append(f'Updated staff: {user.email} ({", ".join(changes)})')
        else:
            summary.append(f'Staff unchanged: {user.email}')

        AuditLog.log_activity(
            user=request.user,
            action_type='data_sync',
            description=f'Pulled staff from PROD: {email}',
            related_user=user,
            metadata={'summary': summary, 'access_level': access},
            ip_address=request.META.get('REMOTE_ADDR'),
        )

        return JsonResponse({'success': True, 'summary': summary})
    except Exception as e:
        logger.exception(f'data_sync_pull_staff failed for {email}')
        return JsonResponse({'error': str(e)}, status=500)


@require_POST
@login_required
def data_sync_pull_case(request):
    """Pull a case (+ member + all related data + files) from PROD."""
    access = _validate_access(request)
    if not access:
        return JsonResponse({'error': 'Not authenticated'}, status=403)
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid request'}, status=400)

    case_id = body.get('case_id', '').strip()
    if not case_id:
        return JsonResponse({'error': 'Case ID required'}, status=400)
    if not _CASE_ID_RE.match(case_id):
        return JsonResponse({'error': 'Invalid case ID format'}, status=400)

    try:
        data = _ssh_export(f'--case {case_id}', timeout=60)
        if 'error' in data:
            return JsonResponse({'error': data['error']}, status=404)

        case, summary = _import_case_data(data, request_user=request.user)

        AuditLog.log_activity(
            user=request.user,
            action_type='data_sync',
            description=f'Pulled case from PROD: {case_id}',
            case=case,
            metadata={'summary': summary, 'access_level': access},
            ip_address=request.META.get('REMOTE_ADDR'),
        )

        return JsonResponse({'success': True, 'summary': summary})
    except Exception as e:
        logger.exception(f'data_sync_pull_case failed for {case_id}')
        return JsonResponse({'error': str(e)}, status=500)
