"""
Constants for the cases application.
Centralized location for magic strings and configuration values.
"""

# ============================================================================
# USER ROLE CONSTANTS
# ============================================================================
ROLE_MEMBER = 'member'
ROLE_TECHNICIAN = 'technician'
ROLE_ADMINISTRATOR = 'administrator'
ROLE_MANAGER = 'manager'

ROLE_CHOICES = [
    (ROLE_MEMBER, 'Member (Financial Advisor)'),
    (ROLE_TECHNICIAN, 'Benefits Technician'),
    (ROLE_ADMINISTRATOR, 'Administrator'),
    (ROLE_MANAGER, 'Manager (View-Only Admin)'),
]

# Roles that can view sensitive data
ADMIN_ROLES = [ROLE_ADMINISTRATOR, ROLE_MANAGER, ROLE_TECHNICIAN]
STAFF_ROLES = [ROLE_TECHNICIAN, ROLE_ADMINISTRATOR, ROLE_MANAGER]

# ============================================================================
# CASE STATUS CONSTANTS
# ============================================================================
CASE_STATUS_SUBMITTED = 'submitted'
CASE_STATUS_ACCEPTED = 'accepted'
CASE_STATUS_HOLD = 'hold'
CASE_STATUS_PENDING_REVIEW = 'pending_review'
CASE_STATUS_COMPLETED = 'completed'
CASE_STATUS_DRAFT = 'draft'

CASE_STATUS_CHOICES = [
    (CASE_STATUS_DRAFT, 'Draft'),
    (CASE_STATUS_SUBMITTED, 'Submitted'),
    (CASE_STATUS_ACCEPTED, 'Accepted'),
    (CASE_STATUS_HOLD, 'Hold'),
    (CASE_STATUS_PENDING_REVIEW, 'Pending Review'),
    (CASE_STATUS_COMPLETED, 'Completed'),
]

# Status workflow transitions
DRAFT_STATUSES = [CASE_STATUS_DRAFT]
PENDING_STATUSES = [CASE_STATUS_SUBMITTED, CASE_STATUS_PENDING_REVIEW]
IN_PROGRESS_STATUSES = [CASE_STATUS_ACCEPTED]
BLOCKED_STATUSES = [CASE_STATUS_HOLD]
FINAL_STATUSES = [CASE_STATUS_COMPLETED]

# ============================================================================
# URGENCY CONSTANTS
# ============================================================================
URGENCY_NORMAL = 'normal'
URGENCY_URGENT = 'urgent'

URGENCY_CHOICES = [
    (URGENCY_NORMAL, 'Normal'),
    (URGENCY_URGENT, 'Urgent'),
]

# ============================================================================
# TIER CONSTANTS (Case complexity/priority levels)
# ============================================================================
TIER_1 = 'tier_1'
TIER_2 = 'tier_2'
TIER_3 = 'tier_3'

TIER_CHOICES = [
    (TIER_1, 'Tier 1'),
    (TIER_2, 'Tier 2'),
    (TIER_3, 'Tier 3'),
]

# ============================================================================
# TECHNICIAN LEVEL CONSTANTS
# ============================================================================
USER_LEVEL_1 = 'level_1'
USER_LEVEL_2 = 'level_2'
USER_LEVEL_3 = 'level_3'

USER_LEVEL_CHOICES = [
    (USER_LEVEL_1, 'Level 1 - New Technician'),
    (USER_LEVEL_2, 'Level 2 - Technician'),
    (USER_LEVEL_3, 'Level 3 - Senior Technician'),
]

# ============================================================================
# PDF CONFIGURATION CONSTANTS
# ============================================================================
PDF_UPLOAD_LIMIT = 10 * 1024 * 1024  # 10MB in bytes
PDF_TEMP_DIR = 'cases/static/documents/temp/'
PDF_TEMPLATE_PATH = 'cases/static/documents/Federal-Fact-Finder-Template.pdf'
PDF_FORM_FIELD_COUNT = 209  # Number of fields in Federal Fact Finder

# ============================================================================
# PAGINATION CONSTANTS
# ============================================================================
CASES_PER_PAGE = 25
DASHBOARD_ITEMS_PER_PAGE = 50

# ============================================================================
# FIELD DISPLAY CONSTANTS
# ============================================================================
# Fields visible to all dashboard roles
COMMON_DASHBOARD_FIELDS = [
    'external_case_id',
    'workshop_code',
    'member',
    'employee_first_name',
    'employee_last_name',
    'client_email',
    'date_submitted',
    'status',
    'urgency',
]

# Additional fields visible to tech/admin/manager
STAFF_ONLY_FIELDS = [
    'date_scheduled',
    'assigned_to',
    'tier',
    'reviewed_by',
    'report_notes',
]

# ============================================================================
# MESSAGE/NOTIFICATION CONSTANTS
# ============================================================================
MSG_CASE_SUBMITTED = 'Case submitted successfully'
MSG_CASE_ACCEPTED = 'Case accepted'
MSG_CASE_COMPLETED = 'Case completed'
MSG_DRAFT_SAVED = 'Draft saved successfully'
MSG_PDF_EXTRACTED = 'PDF fields extracted successfully'

# ============================================================================
# VALIDATION CONSTANTS
# ============================================================================
MIN_REPORTS_REQUESTED = 1
MAX_REPORTS_REQUESTED = 10
MAX_CASE_ID_LENGTH = 50
MAX_WORKSHOP_CODE_LENGTH = 50
