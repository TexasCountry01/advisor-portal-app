"""
Credit value calculation and tracking service
"""
from decimal import Decimal
from django.utils import timezone
from cases.models import CreditAuditLog


def calculate_default_credit(num_reports):
    """
    Calculate default credit value based on number of reports requested.
    
    Formula: 1.0 + (0.5 * (num_reports - 1)), capped at 3.0
    
    Examples:
    - 1 report = 1.0 credit
    - 2 reports = 1.5 credits
    - 3 reports = 2.0 credits
    - 4 reports = 2.5 credits
    - 5+ reports = 3.0 credits (capped)
    """
    try:
        num_reports = int(num_reports)
        if num_reports < 1:
            num_reports = 1
    except (ValueError, TypeError):
        num_reports = 1
    
    # Calculate: 1.0 + (0.5 * (num_reports - 1))
    credit = Decimal('1.0') + (Decimal('0.5') * Decimal(num_reports - 1))
    
    # Cap at 3.0
    return min(credit, Decimal('3.0'))


def create_credit_audit_log(case, credit_value_after, adjusted_by, context, reason=''):
    """
    Create an audit log entry for credit value changes.
    
    Args:
        case: Case instance
        credit_value_after: New credit value
        adjusted_by: User making the adjustment
        context: One of 'submission', 'acceptance', 'update', 'completion'
        reason: Optional reason for adjustment
    
    Returns:
        CreditAuditLog instance
    """
    audit_log = CreditAuditLog.objects.create(
        case=case,
        credit_value_before=case.credit_value,
        credit_value_after=credit_value_after,
        adjusted_by=adjusted_by,
        adjustment_context=context,
        adjustment_reason=reason,
    )
    return audit_log


def set_case_credit(case, credit_value, adjusted_by, context, reason=''):
    """
    Set case credit value and create audit log entry.
    
    Args:
        case: Case instance
        credit_value: New credit value to set
        adjusted_by: User making the adjustment
        context: One of 'submission', 'acceptance', 'update', 'completion'
        reason: Optional reason for adjustment
    """
    # Create audit log
    create_credit_audit_log(case, credit_value, adjusted_by, context, reason)
    
    # Update case
    case.credit_value = credit_value
    if reason:
        case.credit_adjustment_reason = reason
    case.save()
