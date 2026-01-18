"""
Case-related audit logging service.
Provides centralized functions for logging case operations with audit trails.
"""
from django.utils import timezone
from django.db import transaction
from core.models import AuditLog
from ..models import Case
import logging

logger = logging.getLogger(__name__)


def hold_case(case, user, reason='', hold_duration_days=None):
    """
    Place a case on hold and log the action.
    
    Args:
        case: Case instance to hold
        user: User performing the action
        reason: Reason for hold (optional)
        hold_duration_days: Expected duration (optional)
    
    Returns:
        Boolean indicating success
    """
    from django.utils import timezone
    from datetime import timedelta
    
    try:
        old_status = case.status
        case.status = 'hold'
        case.hold_reason = reason or 'Case placed on hold'
        case.hold_start_date = timezone.now()
        case.hold_duration_days = hold_duration_days
        
        # Calculate hold_end_date if duration is specified
        if hold_duration_days:
            case.hold_end_date = case.hold_start_date + timedelta(days=float(hold_duration_days))
        else:
            case.hold_end_date = None
        
        case._audit_user = user
        case._hold_reason = reason or 'Case placed on hold'
        case._hold_duration_days = hold_duration_days
        case.save()
        
        # Explicit audit log
        AuditLog.log_activity(
            user=user,
            action_type='case_held',
            description=f'Case #{case.external_case_id} placed on hold',
            case=case,
            changes={'status': {'from': old_status, 'to': 'hold'}},
            metadata={
                'reason': reason or 'No reason provided',
                'held_at': timezone.now().isoformat(),
                'duration_days': hold_duration_days,
                'hold_end_date': case.hold_end_date.isoformat() if case.hold_end_date else None
            }
        )
        logger.info(f'Case {case.id} held by {user.username}. Reason: {reason}')
        return True
    except Exception as e:
        logger.error(f'Error holding case {case.id}: {str(e)}')
        return False


def resume_case(case, user, reason='', previous_status='accepted'):
    """
    Resume a case from hold and log the action.
    
    Args:
        case: Case instance to resume
        user: User performing the action
        reason: Reason for resuming (optional)
        previous_status: Status to return to (default: 'accepted')
    
    Returns:
        Boolean indicating success
    """
    try:
        old_status = case.status
        case.status = previous_status
        case._audit_user = user
        case._resume_reason = reason or 'Case resumed'
        case._hold_duration = calculate_hold_duration(case)
        case.save()
        
        # Explicit audit log
        AuditLog.log_activity(
            user=user,
            action_type='case_resumed',
            description=f'Case #{case.external_case_id} resumed from hold',
            case=case,
            changes={'status': {'from': old_status, 'to': previous_status}},
            metadata={
                'reason': reason or 'No reason provided',
                'resumed_at': timezone.now().isoformat(),
                'hold_duration': calculate_hold_duration(case)
            }
        )
        logger.info(f'Case {case.id} resumed by {user.username}. Reason: {reason}')
        return True
    except Exception as e:
        logger.error(f'Error resuming case {case.id}: {str(e)}')
        return False


def change_case_tier(case, user, new_tier, reason=''):
    """
    Change a case tier and log the action.
    
    Args:
        case: Case instance
        user: User performing the action
        new_tier: New tier value (1, 2, or 3)
        reason: Reason for tier change
    
    Returns:
        Boolean indicating success
    """
    try:
        old_tier = case.tier
        case.tier = new_tier
        case._audit_user = user
        case._tier_change_reason = reason or 'Tier adjustment'
        case.save()
        
        # Explicit audit log
        AuditLog.log_activity(
            user=user,
            action_type='case_tier_changed',
            description=f'Case #{case.external_case_id} tier changed from {old_tier} to {new_tier}',
            case=case,
            changes={'tier': {'from': old_tier, 'to': new_tier}},
            metadata={
                'reason': reason or 'Complexity reassessment',
                'changed_at': timezone.now().isoformat()
            }
        )
        logger.info(f'Case {case.id} tier changed from {old_tier} to {new_tier} by {user.username}')
        return True
    except Exception as e:
        logger.error(f'Error changing case tier: {str(e)}')
        return False


def calculate_hold_duration(case):
    """Calculate how long a case was on hold"""
    try:
        if case.status == 'hold' and hasattr(case, '_held_since'):
            duration = timezone.now() - case._held_since
            return str(duration)
        return 'N/A'
    except:
        return 'Unknown'


def log_email_notification(case, member_email, send_date, delivery_status='sent'):
    """
    Log when an email notification is sent to a member.
    
    Args:
        case: Case instance
        member_email: Email address notification sent to
        send_date: Date/time of send
        delivery_status: 'sent', 'failed', 'pending', etc.
    """
    try:
        AuditLog.log_activity(
            user=None,  # System action
            action_type='email_notification_sent',
            description=f'Email notification sent to {member_email} for case #{case.external_case_id}',
            case=case,
            metadata={
                'recipient': member_email,
                'send_date': send_date.isoformat() if send_date else None,
                'delivery_status': delivery_status,
                'notification_type': 'case_release'
            }
        )
        logger.info(f'Logged email notification for case {case.id} to {member_email}')
    except Exception as e:
        logger.error(f'Error logging email notification: {str(e)}')


def log_cron_job_execution(job_name, records_processed, status='success', error_msg=''):
    """
    Log when a cron job executes.
    
    Args:
        job_name: Name of the cron job
        records_processed: Number of records processed
        status: 'success' or 'error'
        error_msg: Error message if failed
    """
    try:
        AuditLog.log_activity(
            user=None,  # System action
            action_type='cron_job_executed',
            description=f'Cron job "{job_name}" executed ({records_processed} records processed)',
            metadata={
                'job_name': job_name,
                'records_processed': records_processed,
                'status': status,
                'error_message': error_msg or '',
                'executed_at': timezone.now().isoformat()
            }
        )
        logger.info(f'Logged cron job execution: {job_name} ({records_processed} records)')
    except Exception as e:
        logger.error(f'Error logging cron job: {str(e)}')


def log_quarterly_credit_reset(member_user, old_allowance, new_allowance):
    """
    Log quarterly credit allowance reset for a member.
    
    Args:
        member_user: User instance (member)
        old_allowance: Previous credit allowance
        new_allowance: New credit allowance
    """
    try:
        AuditLog.log_activity(
            user=None,  # System action
            action_type='quarterly_credit_reset',
            description=f'Quarterly credit reset for {member_user.username}',
            related_user=member_user,
            changes={
                'credit_allowance': {'from': old_allowance, 'to': new_allowance}
            },
            metadata={
                'member': member_user.username,
                'reset_date': timezone.now().isoformat(),
                'reset_type': 'automatic_quarterly'
            }
        )
    except Exception as e:
        logger.error(f'Error logging credit reset: {str(e)}')


def log_bulk_credit_reset(member_count, new_allowance):
    """
    Log bulk quarterly credit reset operation.
    
    Args:
        member_count: Number of members reset
        new_allowance: Credit allowance value used
    """
    try:
        AuditLog.log_activity(
            user=None,  # System action
            action_type='bulk_credit_reset',
            description=f'Bulk quarterly credit reset for {member_count} members',
            metadata={
                'member_count': member_count,
                'new_allowance': new_allowance,
                'reset_date': timezone.now().isoformat(),
                'reset_type': 'batch_automatic'
            }
        )
        logger.info(f'Logged bulk credit reset: {member_count} members')
    except Exception as e:
        logger.error(f'Error logging bulk credit reset: {str(e)}')


def log_audit_log_access(user, view_type, filters_applied=None):
    """
    Log when a user accesses the audit log dashboard.
    
    Args:
        user: User accessing audit logs
        view_type: 'main_dashboard', 'detail_view', 'case_trail', 'export'
        filters_applied: Dictionary of filters used
    """
    try:
        AuditLog.log_activity(
            user=user,
            action_type='audit_log_accessed',
            description=f'{user.username} accessed audit log ({view_type})',
            metadata={
                'view_type': view_type,
                'filters': filters_applied or {},
                'accessed_at': timezone.now().isoformat()
            }
        )
    except Exception as e:
        logger.error(f'Error logging audit access: {str(e)}')


def log_bulk_export(user, export_type, record_count, filters_applied=None):
    """
    Log when bulk data is exported.
    
    Args:
        user: User performing export
        export_type: Type of export (cases, documents, audit_log, etc.)
        record_count: Number of records exported
        filters_applied: Dictionary of filters used
    """
    try:
        AuditLog.log_activity(
            user=user,
            action_type='bulk_export',
            description=f'Bulk export: {export_type} ({record_count} records)',
            changes={'export_type': export_type, 'record_count': record_count},
            metadata={
                'export_type': export_type,
                'record_count': record_count,
                'filters': filters_applied or {},
                'exported_at': timezone.now().isoformat()
            }
        )
        logger.info(f'Logged bulk export by {user.username}: {export_type} ({record_count} records)')
    except Exception as e:
        logger.error(f'Error logging bulk export: {str(e)}')


def log_report_generation(user, report_type, parameters=None):
    """
    Log when a report is generated.
    
    Args:
        user: User generating report
        report_type: Type of report (audit_trail, credit_trail, quality_review, etc.)
        parameters: Dictionary of report parameters
    """
    try:
        AuditLog.log_activity(
            user=user,
            action_type='report_generated',
            description=f'Report generated: {report_type}',
            metadata={
                'report_type': report_type,
                'parameters': parameters or {},
                'generated_at': timezone.now().isoformat()
            }
        )
        logger.info(f'Logged report generation by {user.username}: {report_type}')
    except Exception as e:
        logger.error(f'Error logging report generation: {str(e)}')
