"""
Signal handlers for automatic audit logging.
Logs all significant user actions automatically.
"""
from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.utils import timezone
from cases.models import Case, CaseDocument, CaseNote, CaseReport
from accounts.models import User
from core.models import AuditLog, SystemSettings


# ============================================================================
# Authentication Signals
# ============================================================================

@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    """Log when a user logs in"""
    ip_address = get_client_ip(request)
    AuditLog.log_activity(
        user=user,
        action_type='login',
        description=f'{user.username} logged in',
        ip_address=ip_address,
        metadata={'user_agent': request.META.get('HTTP_USER_AGENT', '')}
    )


@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    """Log when a user logs out"""
    ip_address = get_client_ip(request)
    AuditLog.log_activity(
        user=user,
        action_type='logout',
        description=f'{user.username} logged out',
        ip_address=ip_address
    )


# ============================================================================
# Case Signals
# ============================================================================

@receiver(pre_save, sender=Case)
def track_case_changes(sender, instance, **kwargs):
    """Track changes to a case before saving"""
    if instance.pk:
        try:
            old_instance = Case.objects.get(pk=instance.pk)
            instance._old_values = {
                'status': old_instance.status,
                'assigned_to': old_instance.assigned_to_id,
                'urgency': old_instance.urgency,
            }
        except Case.DoesNotExist:
            instance._old_values = {}
    else:
        instance._old_values = {}


@receiver(post_save, sender=Case)
def log_case_activity(sender, instance, created, **kwargs):
    """Log case creation or significant changes"""
    # Skip if this was just created by import or during migration
    if not hasattr(instance, '_state'):
        return
    
    # Get the user from request context (set by views)
    user = getattr(instance, '_audit_user', None)
    if not user:
        return
    
    changes = {}
    
    if created:
        AuditLog.log_activity(
            user=user,
            action_type='case_created',
            description=f'Case {instance.id} created',
            case=instance,
            changes={'created': True}
        )
    else:
        # Check for status changes
        old_status = getattr(instance, '_old_values', {}).get('status')
        if old_status and old_status != instance.status:
            AuditLog.log_activity(
                user=user,
                action_type='case_status_changed',
                description=f'Case {instance.id} status changed from {old_status} to {instance.status}',
                case=instance,
                changes={'status': {'from': old_status, 'to': instance.status}}
            )
        
        # Check for assignment changes
        old_assigned = getattr(instance, '_old_values', {}).get('assigned_to')
        if old_assigned != instance.assigned_to_id:
            if old_assigned is None:
                action = 'case_assigned'
                desc = f'Case {instance.id} assigned to {instance.assigned_to}'
            else:
                action = 'case_reassigned'
                old_user = User.objects.filter(id=old_assigned).first()
                desc = f'Case {instance.id} reassigned from {old_user} to {instance.assigned_to}'
            
            AuditLog.log_activity(
                user=user,
                action_type=action,
                description=desc,
                case=instance,
                related_user=instance.assigned_to,
                changes={'assigned_to': {'from': old_assigned, 'to': instance.assigned_to_id}}
            )
        
        # Check for urgency changes
        old_urgency = getattr(instance, '_old_values', {}).get('urgency')
        if old_urgency and old_urgency != instance.urgency:
            AuditLog.log_activity(
                user=user,
                action_type='case_updated',
                description=f'Case {instance.id} urgency changed from {old_urgency} to {instance.urgency}',
                case=instance,
                changes={'urgency': {'from': old_urgency, 'to': instance.urgency}}
            )


# ============================================================================
# Document Signals
# ============================================================================

@receiver(post_save, sender=CaseDocument)
def log_document_upload(sender, instance, created, **kwargs):
    """Log when a document is uploaded"""
    if created:
        user = getattr(instance, '_audit_user', None)
        if not user:
            return
        
        AuditLog.log_activity(
            user=user,
            action_type='document_uploaded',
            description=f'Document "{instance.filename}" uploaded to case {instance.case_id}',
            case=instance.case,
            document=instance,
            metadata={'filename': instance.filename, 'file_size': instance.file_size}
        )


@receiver(post_delete, sender=CaseDocument)
def log_document_delete(sender, instance, **kwargs):
    """Log when a document is deleted"""
    user = getattr(instance, '_audit_user', None)
    if not user:
        return
    
    AuditLog.log_activity(
        user=user,
        action_type='document_deleted',
        description=f'Document "{instance.filename}" deleted from case {instance.case_id}',
        case=instance.case,
        metadata={'filename': instance.filename}
    )


# ============================================================================
# Case Note Signals
# ============================================================================

@receiver(post_save, sender=CaseNote)
def log_note_activity(sender, instance, created, **kwargs):
    """Log when a note is added or updated"""
    user = getattr(instance, '_audit_user', None)
    if not user:
        return
    
    if created:
        AuditLog.log_activity(
            user=user,
            action_type='note_added',
            description=f'Note added to case {instance.case_id}',
            case=instance.case,
            metadata={'note_type': instance.note_type or 'general'}
        )


@receiver(post_delete, sender=CaseNote)
def log_note_delete(sender, instance, **kwargs):
    """Log when a note is deleted"""
    user = getattr(instance, '_audit_user', None)
    if not user:
        return
    
    AuditLog.log_activity(
        user=user,
        action_type='note_deleted',
        description=f'Note deleted from case {instance.case_id}',
        case=instance.case,
        metadata={'note_type': instance.note_type or 'general'}
    )


# ============================================================================
# Quality Review Signals
# ============================================================================

@receiver(post_save, sender=CaseReport)
def log_review_activity(sender, instance, created, **kwargs):
    """Log when a quality review is submitted or updated"""
    user = getattr(instance, '_audit_user', None)
    if not user:
        return
    
    if created:
        AuditLog.log_activity(
            user=user,
            action_type='review_submitted',
            description=f'Quality review submitted for case {instance.case_id}',
            case=instance.case,
            metadata={'review_status': instance.report_status}
        )
    else:
        AuditLog.log_activity(
            user=user,
            action_type='review_updated',
            description=f'Quality review updated for case {instance.case_id}',
            case=instance.case,
            metadata={'review_status': instance.report_status}
        )


# ============================================================================
# User Management Signals
# ============================================================================

@receiver(pre_save, sender=User)
def track_user_changes(sender, instance, **kwargs):
    """Track changes to a user"""
    if instance.pk:
        try:
            old_instance = User.objects.get(pk=instance.pk)
            instance._old_user_values = {
                'role': old_instance.role,
                'user_level': old_instance.user_level,
                'is_active': old_instance.is_active,
            }
        except User.DoesNotExist:
            instance._old_user_values = {}
    else:
        instance._old_user_values = {}


@receiver(post_save, sender=User)
def log_user_activity(sender, instance, created, **kwargs):
    """Log user creation or changes"""
    # Skip if not an admin action
    admin_user = getattr(instance, '_admin_user', None)
    if not admin_user:
        return
    
    if created:
        AuditLog.log_activity(
            user=admin_user,
            action_type='user_created',
            description=f'User {instance.username} created with role {instance.get_role_display()}',
            related_user=instance,
            metadata={'role': instance.role, 'email': instance.email}
        )
    else:
        old_values = getattr(instance, '_old_user_values', {})
        changes = {}
        
        if old_values.get('role') != instance.role:
            changes['role'] = {
                'from': old_values.get('role'),
                'to': instance.role
            }
        
        if old_values.get('is_active') != instance.is_active:
            changes['is_active'] = {
                'from': old_values.get('is_active'),
                'to': instance.is_active
            }
        
        if changes:
            AuditLog.log_activity(
                user=admin_user,
                action_type='user_updated',
                description=f'User {instance.username} updated: {", ".join(changes.keys())}',
                related_user=instance,
                changes=changes
            )


@receiver(post_delete, sender=User)
def log_user_delete(sender, instance, **kwargs):
    """Log when a user is deleted"""
    admin_user = getattr(instance, '_admin_user', None)
    if not admin_user:
        return
    
    AuditLog.log_activity(
        user=admin_user,
        action_type='user_deleted',
        description=f'User {instance.username} deleted',
        related_user=instance,
        metadata={'role': instance.role, 'email': instance.email}
    )


# ============================================================================
# Settings Signals
# ============================================================================

@receiver(post_save, sender=SystemSettings)
def log_settings_update(sender, instance, created, **kwargs):
    """Log when system settings are updated"""
    user = getattr(instance, '_audit_user', None)
    if not user:
        return
    
    if not created:
        AuditLog.log_activity(
            user=user,
            action_type='settings_updated',
            description='System settings updated',
            changes={'settings': 'System configuration changed'}
        )


# ============================================================================
# Member Profile Update Signals
# ============================================================================

@receiver(post_save, sender=User)
def log_user_profile_changes(sender, instance, created, **kwargs):
    """Log when a user updates their profile (NEW)"""
    if created:
        return  # Skip new user creation, handled separately
    
    # Get audit user from context
    user = getattr(instance, '_audit_user', None)
    if not user:
        return
    
    # Check if this is a member profile edit
    if instance.role == 'member':
        old_values = getattr(instance, '_old_profile_values', {})
        if old_values:
            changed_fields = [
                field for field in ['first_name', 'last_name', 'email', 'phone_number']
                if old_values.get(field) != getattr(instance, field, None)
            ]
            
            if changed_fields:
                AuditLog.log_activity(
                    user=user if user.id != instance.id else instance,
                    action_type='member_profile_updated',
                    description=f'Profile updated: {", ".join(changed_fields)}',
                    related_user=instance,
                    changes={
                        field: {
                            'from': old_values.get(field),
                            'to': getattr(instance, field, None)
                        }
                        for field in changed_fields
                    },
                    metadata={'edited_by': user.username if user else 'self'}
                )


# ============================================================================
# Case Hold/Resume Signals
# ============================================================================

@receiver(pre_save, sender=Case)
def track_case_hold_status(sender, instance, **kwargs):
    """Track case hold/resume status changes"""
    if instance.pk:
        try:
            old_instance = Case.objects.get(pk=instance.pk)
            instance._old_hold_status = old_instance.status
        except Case.DoesNotExist:
            instance._old_hold_status = None


@receiver(post_save, sender=Case)
def log_case_hold_resume(sender, instance, created, **kwargs):
    """Log when a case is placed on hold or resumed (NEW)"""
    if created:
        return
    
    user = getattr(instance, '_audit_user', None)
    if not user:
        return
    
    old_status = getattr(instance, '_old_hold_status', None)
    
    # Log case hold
    if old_status != 'hold' and instance.status == 'hold':
        reason = getattr(instance, '_hold_reason', 'Case placed on hold')
        AuditLog.log_activity(
            user=user,
            action_type='case_held',
            description=f'Case #{instance.external_case_id} placed on hold',
            case=instance,
            metadata={'reason': reason, 'held_at': timezone.now().isoformat()}
        )
    
    # Log case resume
    elif old_status == 'hold' and instance.status != 'hold':
        reason = getattr(instance, '_resume_reason', 'Case resumed')
        AuditLog.log_activity(
            user=user,
            action_type='case_resumed',
            description=f'Case #{instance.external_case_id} resumed from hold',
            case=instance,
            metadata={
                'reason': reason,
                'resumed_at': timezone.now().isoformat(),
                'hold_duration': getattr(instance, '_hold_duration', 'unknown')
            }
        )


# ============================================================================
# Case Tier Change Signals
# ============================================================================

@receiver(pre_save, sender=Case)
def track_case_tier_changes(sender, instance, **kwargs):
    """Track case tier changes"""
    if instance.pk:
        try:
            old_instance = Case.objects.get(pk=instance.pk)
            instance._old_tier = old_instance.tier
        except Case.DoesNotExist:
            instance._old_tier = None


@receiver(post_save, sender=Case)
def log_case_tier_change(sender, instance, created, **kwargs):
    """Log when case tier is changed (NEW)"""
    if created:
        return
    
    user = getattr(instance, '_audit_user', None)
    if not user:
        return
    
    old_tier = getattr(instance, '_old_tier', None)
    
    if old_tier and old_tier != instance.tier:
        reason = getattr(instance, '_tier_change_reason', 'Complexity assessment')
        AuditLog.log_activity(
            user=user,
            action_type='case_tier_changed',
            description=f'Case tier adjusted: Tier {old_tier} → Tier {instance.tier}',
            case=instance,
            changes={'tier': {'from': old_tier, 'to': instance.tier}},
            metadata={'reason': reason}
        )


# ============================================================================
# Role Change Signals
# ============================================================================

@receiver(pre_save, sender=User)
def track_user_role_changes(sender, instance, **kwargs):
    """Track user role and level changes"""
    if instance.pk:
        try:
            old_instance = User.objects.get(pk=instance.pk)
            instance._old_role = old_instance.role
            instance._old_level = old_instance.user_level
        except User.DoesNotExist:
            instance._old_role = None
            instance._old_level = None


@receiver(post_save, sender=User)
def log_user_role_change(sender, instance, created, **kwargs):
    """Log when user role or level is changed (NEW)"""
    if created:
        return
    
    user = getattr(instance, '_audit_user', None)
    if not user:
        return
    
    old_role = getattr(instance, '_old_role', None)
    old_level = getattr(instance, '_old_level', None)
    
    role_changed = old_role and old_role != instance.role
    level_changed = old_level and old_level != instance.user_level
    
    if role_changed or level_changed:
        changes = {}
        description_parts = []
        
        if role_changed:
            changes['role'] = {'from': old_role, 'to': instance.role}
            description_parts.append(f'role {old_role} → {instance.role}')
        
        if level_changed:
            changes['user_level'] = {'from': old_level, 'to': instance.user_level}
            description_parts.append(f'level {old_level} → {instance.user_level}')
        
        AuditLog.log_activity(
            user=user,
            action_type='user_role_changed',
            description=f'User {instance.username} access changed: {", ".join(description_parts)}',
            related_user=instance,
            changes=changes,
            metadata={'changed_by': user.username}
        )


# ============================================================================
