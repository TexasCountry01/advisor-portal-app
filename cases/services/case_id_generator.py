"""
Case ID Generator Service

Generates meaningful case IDs in format: WS###-YYYY-MM-#### 
Example: WS001-2026-01-0042

Format breakdown:
- WS = Workshop prefix (constant)
- ### = Workshop code (first 3 digits)
- YYYY-MM = Year and month of case creation
- #### = Sequential counter for that workshop/month (zero-padded)
"""

from django.db.models import Max
from django.utils import timezone
from cases.models import Case
import re


def generate_case_id(workshop_code):
    """
    Generate a meaningful case ID based on workshop code, current date, and sequence.
    
    Args:
        workshop_code (str): The workshop code (e.g., 'WS001', '001', 'WS-001')
    
    Returns:
        str: Generated case ID in format WS###-YYYY-MM-####
        
    Example:
        generate_case_id('WS001') -> 'WS001-2026-01-0001'
        generate_case_id('001') -> 'WS001-2026-01-0001'
    """
    # Extract numeric part from workshop code (handle various formats: 'WS001', '001', 'WS-001', etc.)
    workshop_match = re.search(r'(\d{3})', workshop_code)
    workshop_num = workshop_match.group(1) if workshop_match else '000'
    
    # Get current date
    now = timezone.now()
    year = now.year
    month = now.month
    
    # Format: WS###-YYYY-MM
    date_prefix = f"WS{workshop_num}-{year}-{month:02d}"
    
    # Find the highest sequence number for this workshop/month combination
    # Query cases with IDs matching this prefix
    existing_cases = Case.objects.filter(
        external_case_id__startswith=date_prefix
    ).values_list('external_case_id', flat=True)
    
    # Extract sequence numbers from existing IDs
    max_sequence = 0
    for case_id in existing_cases:
        # Extract the last 4-digit sequence: WS001-2026-01-0042 -> 42
        seq_match = re.search(r'-(\d{4})$', case_id)
        if seq_match:
            seq_num = int(seq_match.group(1))
            max_sequence = max(max_sequence, seq_num)
    
    # Increment and format with zero-padding
    next_sequence = max_sequence + 1
    if next_sequence > 9999:
        # Fallback if we somehow exceed 4 digits (unlikely in practice)
        next_sequence = 9999
    
    return f"{date_prefix}-{next_sequence:04d}"
