"""
Fix historical credit values for cases accepted before commit 40840bb was deployed.
Before that fix, the acceptance form stored the selected credit in audit metadata
but never called set_case_credit() to persist it to case.credit_value.

This script updates case.credit_value from the acceptance metadata for affected cases,
UNLESS a manual adjustment was made after acceptance (those should be preserved).
"""
import os, django
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
django.setup()

from decimal import Decimal
from core.models import AuditLog
from cases.models import CreditAuditLog, Case

fixed = 0
skipped = 0

for log in AuditLog.objects.filter(action_type='case_accepted').order_by('-timestamp'):
    case = log.case
    if not case or not log.metadata:
        continue
    
    meta_credit = log.metadata.get('credit_value', '')
    if not meta_credit:
        continue
    
    # Check if acceptance credit was already saved (has CreditAuditLog 'acceptance' entry)
    has_acceptance_log = CreditAuditLog.objects.filter(
        case=case, adjustment_context='acceptance'
    ).exists()
    if has_acceptance_log:
        # Already fixed — skip
        continue
    
    # Check if there was a MANUAL adjustment after acceptance that should be preserved
    manual_adjustment = CreditAuditLog.objects.filter(
        case=case, 
        adjustment_context='update',
        adjusted_at__gt=log.timestamp
    ).order_by('-adjusted_at').first()
    
    if manual_adjustment:
        print(f'SKIP {case.external_case_id}: manual adjustment to {manual_adjustment.credit_value_after} after acceptance (keeping manual value)')
        skipped += 1
        continue
    
    # Fix: update case.credit_value to what was selected during acceptance
    try:
        new_credit = Decimal(str(meta_credit))
        old_credit = case.credit_value
        
        if old_credit == new_credit:
            continue  # Already correct
        
        # Create a CreditAuditLog entry for the fix
        CreditAuditLog.objects.create(
            case=case,
            credit_value_before=old_credit,
            credit_value_after=new_credit,
            adjusted_by=log.user,  # Use the original acceptor
            adjustment_context='acceptance',
            adjustment_reason=f'Retroactive fix: acceptance selected {meta_credit} but was not persisted due to deployment timing',
        )
        
        case.credit_value = new_credit
        case._skip_audit_signal = True
        case.save(update_fields=['credit_value'])
        
        print(f'FIXED {case.external_case_id}: {old_credit} -> {new_credit} (accepted by {log.user})')
        fixed += 1
        
    except (ValueError, TypeError) as e:
        print(f'ERROR {case.external_case_id}: {e}')

print(f'\nDone: {fixed} fixed, {skipped} skipped (had manual adjustments)')
