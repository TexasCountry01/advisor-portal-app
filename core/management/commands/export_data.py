"""
Export data from this environment as JSON for the data sync tool.
Runs on PROD via SSH from TEST/LOCAL.

Usage:
  python manage.py export_data --list-members
  python manage.py export_data --list-staff
  python manage.py export_data --list-cases
  python manage.py export_data --member EMAIL
  python manage.py export_data --staff EMAIL
  python manage.py export_data --case EXTERNAL_CASE_ID
"""
import json
import sys
from datetime import date, datetime
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import User, MemberDelegate, MemberCreditAllowance


def json_serial(obj):
    """JSON serializer for objects not serializable by default."""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return str(obj)
    if isinstance(obj, timezone.timedelta):
        return str(obj)
    raise TypeError(f"Type {type(obj)} not serializable")


def user_to_dict(user):
    """Serialize a User to a portable dict (no PKs, uses email as identifier)."""
    return {
        'email': user.email,
        'username': user.username,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'role': user.role,
        'contact_id': user.contact_id or '',
        'user_level': user.user_level or '',
        'workshop_code': user.workshop_code or '',
        'is_pure_delegate': user.is_pure_delegate,
        'notification_email': user.notification_email or '',
        'phone': user.phone or '',
        'font_size': user.font_size,
        'is_active': user.is_active,
        'is_test_account': user.is_test_account,
    }


class Command(BaseCommand):
    help = 'Export data as JSON for the data sync tool'

    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument('--list-members', action='store_true',
                           help='List all members (summary)')
        group.add_argument('--list-staff', action='store_true',
                           help='List all staff (summary)')
        group.add_argument('--list-cases', action='store_true',
                           help='List all cases (summary)')
        group.add_argument('--member', type=str, metavar='EMAIL',
                           help='Export full member data by email')
        group.add_argument('--staff', type=str, metavar='EMAIL',
                           help='Export full staff user data by email')
        group.add_argument('--case', type=str, metavar='CASE_ID',
                           help='Export full case data by external_case_id')

    def handle(self, *args, **options):
        # All output goes to stdout as JSON; errors to stderr
        if options['list_members']:
            self._list_members()
        elif options['list_staff']:
            self._list_staff()
        elif options['list_cases']:
            self._list_cases()
        elif options['member']:
            self._export_member(options['member'])
        elif options['staff']:
            self._export_staff(options['staff'])
        elif options['case']:
            self._export_case(options['case'])

    def _output_json(self, data):
        """Write JSON to stdout (not self.stdout to avoid Django formatting)."""
        sys.stdout.write(json.dumps(data, default=json_serial))

    def _list_members(self):
        members = User.objects.filter(role='member', is_active=True).order_by(
            'last_name', 'first_name'
        )
        result = []
        for m in members:
            delegate_count = MemberDelegate.objects.filter(member=m).count()
            result.append({
                'email': m.email,
                'first_name': m.first_name,
                'last_name': m.last_name,
                'workshop_code': m.workshop_code or '',
                'is_pure_delegate': m.is_pure_delegate,
                'delegate_count': delegate_count,
                'is_test_account': m.is_test_account,
            })
        self._output_json(result)

    def _list_staff(self):
        staff = User.objects.filter(
            role__in=['technician', 'administrator', 'manager'],
            is_active=True
        ).order_by('role', 'last_name', 'first_name')
        result = []
        for s in staff:
            result.append({
                'email': s.email,
                'first_name': s.first_name,
                'last_name': s.last_name,
                'role': s.role,
                'user_level': s.user_level or '',
                'is_test_account': s.is_test_account,
            })
        self._output_json(result)

    def _list_cases(self):
        from cases.models import Case
        cases = Case.objects.select_related('member', 'assigned_to').order_by(
            '-date_submitted'
        )[:200]  # Limit to most recent 200
        result = []
        for c in cases:
            result.append({
                'external_case_id': c.external_case_id,
                'member_email': c.member.email if c.member else '',
                'member_name': c.member.get_full_name() if c.member else '',
                'employee_name': f"{c.employee_first_name} {c.employee_last_name}".strip(),
                'status': c.status,
                'date_submitted': c.date_submitted.isoformat() if c.date_submitted else '',
                'assigned_to': c.assigned_to.get_full_name() if c.assigned_to else 'Unassigned',
            })
        self._output_json(result)

    def _export_member(self, email):
        try:
            user = User.objects.get(email__iexact=email.strip())
        except User.DoesNotExist:
            self._output_json({'error': f'No user found with email: {email}'})
            return

        # Delegates
        delegates = []
        for md in MemberDelegate.objects.filter(member=user).select_related(
            'delegate', 'assigned_by'
        ):
            delegates.append({
                'delegate_user': user_to_dict(md.delegate),
                'assigned_by_email': md.assigned_by.email if md.assigned_by else '',
            })

        # Credit allowances
        credits = []
        for ca in MemberCreditAllowance.objects.filter(member=user):
            credits.append({
                'fiscal_year': ca.fiscal_year,
                'quarter': ca.quarter,
                'allowed_credits': ca.allowed_credits,
                'configured_by_email': ca.configured_by.email if ca.configured_by else '',
                'notes': ca.notes or '',
            })

        self._output_json({
            'user': user_to_dict(user),
            'delegates': delegates,
            'credit_allowances': credits,
        })

    def _export_staff(self, email):
        try:
            user = User.objects.get(email__iexact=email.strip())
        except User.DoesNotExist:
            self._output_json({'error': f'No user found with email: {email}'})
            return
        self._output_json({'user': user_to_dict(user)})

    def _export_case(self, external_case_id):
        from cases.models import (
            Case, CaseDocument, CaseReport, CaseNote, CaseMessage,
            CaseNotification, CaseChangeRequest, CaseReviewHistory,
            CreditAuditLog,
        )
        from cases.models_fact_finder import FederalFactFinder

        try:
            case = Case.objects.select_related(
                'member', 'created_by', 'assigned_to', 'reviewed_by',
                'accepted_by', 'rejected_by', 'original_case',
            ).get(external_case_id=external_case_id)
        except Case.DoesNotExist:
            self._output_json({'error': f'No case found: {external_case_id}'})
            return

        def user_email(u):
            return u.email if u else ''

        # Core case data (all fields, user FKs as emails)
        case_data = {
            'external_case_id': case.external_case_id,
            'workshop_code': case.workshop_code,
            'member_email': user_email(case.member),
            'created_by_email': user_email(case.created_by),
            'assigned_to_email': user_email(case.assigned_to),
            'reviewed_by_email': user_email(case.reviewed_by),
            'accepted_by_email': user_email(case.accepted_by),
            'rejected_by_email': user_email(case.rejected_by),
            'original_case_id': case.original_case.external_case_id if case.original_case else '',
            'employee_first_name': case.employee_first_name,
            'employee_last_name': case.employee_last_name,
            'client_email': case.client_email,
            'num_reports_requested': case.num_reports_requested,
            'urgency': case.urgency,
            'status': case.status,
            'hold_reason': case.hold_reason,
            'hold_start_date': case.hold_start_date,
            'hold_end_date': case.hold_end_date,
            'hold_duration_days': case.hold_duration_days,
            'status_before_hold': case.status_before_hold,
            'reviewed_at': case.reviewed_at,
            'review_notes': case.review_notes,
            'review_status': case.review_status,
            'tier': case.tier,
            'date_submitted': case.date_submitted,
            'date_accepted': case.date_accepted,
            'date_due': case.date_due,
            'date_scheduled': case.date_scheduled,
            'date_completed': case.date_completed,
            'scheduled_release_date': case.scheduled_release_date,
            'actual_release_date': case.actual_release_date,
            'scheduled_email_date': case.scheduled_email_date,
            'actual_email_sent_date': case.actual_email_sent_date,
            'rejection_reason': case.rejection_reason,
            'rejection_notes': case.rejection_notes,
            'date_rejected': case.date_rejected,
            'reassignment_history': case.reassignment_history,
            'report_notes_to_member': case.report_notes_to_member,
            'report_notes': case.report_notes,
            'fact_finder_data': case.fact_finder_data,
            'fact_finder_pdf_status': case.fact_finder_pdf_status,
            'fact_finder_pdf_generated_at': case.fact_finder_pdf_generated_at,
            'special_notes': case.special_notes,
            'retirement_date_preference': case.retirement_date_preference,
            'api_sync_status': case.api_sync_status,
            'api_synced_at': case.api_synced_at,
            'credit_value': case.credit_value,
            'credit_adjustment_reason': case.credit_adjustment_reason,
            'is_resubmitted': case.is_resubmitted,
            'resubmission_count': case.resubmission_count,
            'previous_status': case.previous_status,
            'resubmission_date': case.resubmission_date,
            'resubmission_notes': case.resubmission_notes,
            'has_member_updates': case.has_member_updates,
            'member_last_update_date': case.member_last_update_date,
            'has_member_change_request': case.has_member_change_request,
            'has_member_new_info': case.has_member_new_info,
            'has_profeds_error': case.has_profeds_error,
            'error_modification_count': case.error_modification_count,
            'notes': case.notes,
            'created_at': case.created_at,
            'updated_at': case.updated_at,
        }

        # Documents (with file paths for SCP)
        documents = []
        for doc in CaseDocument.objects.filter(case=case).select_related('uploaded_by'):
            documents.append({
                'document_type': doc.document_type,
                'original_filename': doc.original_filename,
                'file_path': doc.file.name if doc.file else '',
                'file_size': doc.file_size,
                'uploaded_by_email': user_email(doc.uploaded_by),
                'uploaded_at': doc.uploaded_at,
                'notes': doc.notes,
            })

        # Reports
        reports = []
        for r in CaseReport.objects.filter(case=case).select_related(
            'assigned_to', 'reviewed_by'
        ):
            reports.append({
                'report_number': r.report_number,
                'status': r.status,
                'assigned_to_email': user_email(r.assigned_to),
                'reviewed_by_email': user_email(r.reviewed_by),
                'report_file_path': r.report_file.name if r.report_file else '',
                'notes': r.notes,
                'started_at': r.started_at,
                'completed_at': r.completed_at,
                'created_at': r.created_at,
                'updated_at': r.updated_at,
            })

        # Notes
        notes = []
        for n in CaseNote.objects.filter(case=case).select_related('author'):
            notes.append({
                'author_email': user_email(n.author),
                'note': n.note,
                'is_internal': n.is_internal,
                'created_at': n.created_at,
            })

        # Messages
        messages = []
        for m in CaseMessage.objects.filter(case=case).select_related('author'):
            messages.append({
                'author_email': user_email(m.author),
                'message': m.message,
                'created_at': m.created_at,
            })

        # Notifications
        notifications = []
        for n in CaseNotification.objects.filter(case=case).select_related('member'):
            notifications.append({
                'member_email': user_email(n.member),
                'notification_type': n.notification_type,
                'title': n.title,
                'message': n.message,
                'hold_reason': n.hold_reason or '',
                'is_read': n.is_read,
                'created_at': n.created_at,
                'read_at': n.read_at,
            })

        # Change requests
        change_requests = []
        for cr in CaseChangeRequest.objects.filter(case=case).select_related(
            'member', 'reviewed_by'
        ):
            change_requests.append({
                'member_email': user_email(cr.member),
                'request_type': cr.request_type,
                'requested_due_date': cr.requested_due_date,
                'cancellation_reason': cr.cancellation_reason or '',
                'member_notes': cr.member_notes,
                'status': cr.status,
                'technician_response_notes': cr.technician_response_notes,
                'reviewed_by_email': user_email(cr.reviewed_by),
                'created_at': cr.created_at,
                'reviewed_at': cr.reviewed_at,
            })

        # Review history
        review_history = []
        for rh in CaseReviewHistory.objects.filter(case=case).select_related(
            'reviewed_by', 'original_technician'
        ):
            review_history.append({
                'reviewed_by_email': user_email(rh.reviewed_by),
                'original_technician_email': user_email(rh.original_technician),
                'review_action': rh.review_action,
                'review_notes': rh.review_notes,
                'reviewed_at': rh.reviewed_at,
            })

        # Credit audit logs
        credit_audit = []
        for cal in CreditAuditLog.objects.filter(case=case).select_related('adjusted_by'):
            credit_audit.append({
                'adjusted_by_email': user_email(cal.adjusted_by),
                'adjusted_at': cal.adjusted_at,
                'credit_value_before': cal.credit_value_before,
                'credit_value_after': cal.credit_value_after,
                'adjustment_reason': cal.adjustment_reason,
                'adjustment_context': cal.adjustment_context,
            })

        # Fact Finder
        fact_finder_data = None
        try:
            fff = case.fact_finder
            # Serialize all FFF fields except the case FK
            fact_finder_data = {}
            for field in FederalFactFinder._meta.get_fields():
                if field.name == 'case':
                    continue
                if hasattr(field, 'attname'):
                    val = getattr(fff, field.attname, None)
                    fact_finder_data[field.name] = val
        except FederalFactFinder.DoesNotExist:
            pass

        # Collect all file paths for SCP
        file_paths = []
        for doc in documents:
            if doc['file_path']:
                file_paths.append(doc['file_path'])
        for r in reports:
            if r['report_file_path']:
                file_paths.append(r['report_file_path'])

        self._output_json({
            'case': case_data,
            'member_data': self._get_member_data(case.member) if case.member else None,
            'documents': documents,
            'reports': reports,
            'notes': notes,
            'messages': messages,
            'notifications': notifications,
            'change_requests': change_requests,
            'review_history': review_history,
            'credit_audit_logs': credit_audit,
            'fact_finder': fact_finder_data,
            'file_paths': file_paths,
        })

    def _get_member_data(self, user):
        """Get minimal member data for auto-pull during case import."""
        delegates = []
        for md in MemberDelegate.objects.filter(member=user).select_related(
            'delegate', 'assigned_by'
        ):
            delegates.append({
                'delegate_user': user_to_dict(md.delegate),
                'assigned_by_email': md.assigned_by.email if md.assigned_by else '',
            })
        return {
            'user': user_to_dict(user),
            'delegates': delegates,
        }
