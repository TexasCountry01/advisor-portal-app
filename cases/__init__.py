"""
Cases app - Case management and workflow system.

This app handles:
- Case submission and workflow (member -> technician -> admin -> completion)
- PDF form management (Federal Fact Finder form with 209 fields)
- Multi-role dashboards (member, technician, administrator, manager)
- Document management and attachments
- Case status tracking and analytics
"""
from .constants import *  # noqa: F401,F403

__all__ = [
    # Constants exported for convenience
    'ROLE_MEMBER',
    'ROLE_TECHNICIAN', 
    'ROLE_ADMINISTRATOR',
    'ROLE_MANAGER',
    'CASE_STATUS_DRAFT',
    'CASE_STATUS_SUBMITTED',
    'CASE_STATUS_ACCEPTED',
    'CASE_STATUS_PENDING_REVIEW',
    'CASE_STATUS_HOLD',
    'CASE_STATUS_COMPLETED',
]
