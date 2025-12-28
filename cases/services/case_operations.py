"""
Business logic and workflow operations for cases.
Separates business logic from views for better testability and reusability.
"""
from django.utils import timezone
from django.db import transaction, models
from cases.models import Case
from .constants import (
    CASE_STATUS_ACCEPTED,
    CASE_STATUS_COMPLETED,
    CASE_STATUS_DRAFT,
    CASE_STATUS_PENDING_REVIEW,
    CASE_STATUS_HOLD,
    CASE_STATUS_SUBMITTED,
)


class CaseService:
    """Service for case-related business operations"""
    
    @staticmethod
    @transaction.atomic
    def submit_case(case: Case, user) -> bool:
        """
        Submit a case from draft to submitted status.
        
        Args:
            case: Case instance to submit
            user: User performing the action (should be case owner)
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            ValueError: If case cannot be submitted
        """
        if case.status not in [CASE_STATUS_DRAFT, CASE_STATUS_SUBMITTED]:
            raise ValueError(f"Cannot submit case with status: {case.status}")
        
        case.status = CASE_STATUS_SUBMITTED
        case.save()
        return True
    
    @staticmethod
    @transaction.atomic
    def accept_case(case: Case, technician) -> bool:
        """
        Accept a case for processing.
        
        Args:
            case: Case instance to accept
            technician: Technician accepting the case
            
        Returns:
            True if successful
            
        Raises:
            ValueError: If case cannot be accepted
        """
        if case.status not in [CASE_STATUS_SUBMITTED, CASE_STATUS_PENDING_REVIEW]:
            raise ValueError(f"Cannot accept case with status: {case.status}")
        
        case.status = CASE_STATUS_ACCEPTED
        case.assigned_to = technician
        case.date_accepted = timezone.now()
        case.save()
        return True
    
    @staticmethod
    @transaction.atomic
    def hold_case(case: Case, reason: str = None) -> bool:
        """
        Put a case on hold.
        
        Args:
            case: Case instance to hold
            reason: Optional reason for hold
            
        Returns:
            True if successful
        """
        case.status = CASE_STATUS_HOLD
        case.save()
        return True
    
    @staticmethod
    @transaction.atomic
    def complete_case(case: Case, reviewer=None) -> bool:
        """
        Mark a case as completed.
        
        Args:
            case: Case instance to complete
            reviewer: Optional reviewer for the case
            
        Returns:
            True if successful
            
        Raises:
            ValueError: If case is in invalid status
        """
        if case.status == CASE_STATUS_COMPLETED:
            raise ValueError("Case is already completed")
        
        case.status = CASE_STATUS_COMPLETED
        case.date_completed = timezone.now()
        if reviewer:
            case.reviewed_by = reviewer
        case.save()
        return True
    
    @staticmethod
    def save_draft(case: Case, data: dict) -> bool:
        """
        Save case draft with fact-finder form data.
        
        Args:
            case: Case instance
            data: Dictionary of form field data
            
        Returns:
            True if successful
        """
        case.fact_finder_data = data
        case.status = CASE_STATUS_DRAFT
        case.save()
        return True
    
    @staticmethod
    def get_case_status_badge_class(status: str) -> str:
        """
        Get Bootstrap badge class for case status.
        
        Args:
            status: Case status string
            
        Returns:
            Bootstrap CSS class (e.g., 'bg-primary', 'bg-success')
        """
        status_classes = {
            CASE_STATUS_DRAFT: 'bg-secondary',
            CASE_STATUS_SUBMITTED: 'bg-primary',
            CASE_STATUS_ACCEPTED: 'bg-info',
            CASE_STATUS_PENDING_REVIEW: 'bg-warning text-dark',
            CASE_STATUS_HOLD: 'bg-danger',
            CASE_STATUS_COMPLETED: 'bg-success',
        }
        return status_classes.get(status, 'bg-secondary')
    
    @staticmethod
    def can_user_edit_case(case: Case, user) -> bool:
        """
        Check if user can edit this case.
        
        Args:
            case: Case instance
            user: User to check
            
        Returns:
            True if user can edit, False otherwise
        """
        # Member can only edit their own draft cases
        if user.role == 'member':
            return case.member == user and case.status == CASE_STATUS_DRAFT
        
        # Technicians and admins can edit non-completed cases
        if user.role in ['technician', 'administrator']:
            return case.status != CASE_STATUS_COMPLETED
        
        return False
    
    @staticmethod
    def can_user_view_case(case: Case, user) -> bool:
        """
        Check if user can view this case.
        
        Args:
            case: Case instance
            user: User to check
            
        Returns:
            True if user can view, False otherwise
        """
        # Member can only view their own cases
        if user.role == 'member':
            return case.member == user
        
        # Technicians can view assigned cases
        if user.role == 'technician':
            return case.assigned_to == user or case.reviewed_by == user
        
        # Admin and manager can view all cases
        if user.role in ['administrator', 'manager']:
            return True
        
        return False


class CaseQueryService:
    """Service for case queries and filtering"""
    
    @staticmethod
    def get_user_cases(user, include_draft: bool = True):
        """
        Get all cases visible to the user based on their role.
        
        Args:
            user: User instance
            include_draft: Whether to include draft cases
            
        Returns:
            QuerySet of Case instances
        """
        if user.role == 'member':
            qs = Case.objects.filter(member=user)
            if not include_draft:
                qs = qs.exclude(status='draft')
            return qs
        
        elif user.role == 'technician':
            qs = Case.objects.filter(
                models.Q(assigned_to=user) | models.Q(reviewed_by=user)
            )
            return qs
        
        elif user.role in ['administrator', 'manager']:
            return Case.objects.all()
        
        return Case.objects.none()
    
    @staticmethod
    def get_cases_by_status(status: str, user=None):
        """
        Get cases filtered by status.
        
        Args:
            status: Case status
            user: Optional user for role-based filtering
            
        Returns:
            QuerySet of Case instances
        """
        qs = Case.objects.filter(status=status)
        
        if user and user.role == 'member':
            qs = qs.filter(member=user)
        
        return qs
    
    @staticmethod
    def get_overdue_cases():
        """
        Get cases past their due date.
        
        Returns:
            QuerySet of overdue Case instances
        """
        from django.db.models import Q
        now = timezone.now()
        return Case.objects.filter(
            Q(date_due__lt=now),
            Q(status__in=[CASE_STATUS_SUBMITTED, CASE_STATUS_ACCEPTED])
        )
