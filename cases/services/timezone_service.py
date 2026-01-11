"""
Service for timezone handling, specifically for Central Standard Time (CST).
All release calculations should use this service to ensure consistency.
"""

from django.utils import timezone
from datetime import datetime, timedelta
import pytz

# Central Standard Time timezone
CST = pytz.timezone('America/Chicago')


def get_cst_now():
    """Get current datetime in Central Standard Time"""
    return timezone.now().astimezone(CST)


def calculate_release_time_cst(hours_delay: int) -> datetime:
    """
    Calculate scheduled release time in CST.
    
    Args:
        hours_delay: Number of hours to delay (0-5)
        
    Returns:
        datetime object in CST representing when case should be released
    """
    if not isinstance(hours_delay, int) or hours_delay < 0 or hours_delay > 5:
        raise ValueError("hours_delay must be between 0 and 5")
    
    # Get current time in CST
    cst_now = get_cst_now()
    
    # Add delay
    release_time_cst = cst_now + timedelta(hours=hours_delay)
    
    return release_time_cst


def get_delay_label(hours: int) -> str:
    """Get human-readable label for delay"""
    delay_labels = {
        0: 'Immediately',
        1: '1 Hour',
        2: '2 Hours',
        3: '3 Hours',
        4: '4 Hours',
        5: '5 Hours',
    }
    return delay_labels.get(hours, 'Unknown')


def should_release_case(case) -> bool:
    """
    Check if a case should be released based on its scheduled_release_date.
    Compares scheduled date against today's date in CST.
    
    Args:
        case: Case object with scheduled_release_date
        
    Returns:
        True if case should be released, False otherwise
    """
    if not case.scheduled_release_date or case.actual_release_date:
        return False
    
    # Get today's date in CST
    cst_today = get_cst_now().date()
    
    # Compare dates
    return case.scheduled_release_date <= cst_today


def convert_to_scheduled_date_cst(release_datetime: datetime) -> 'date':
    """
    Convert a release datetime to a scheduled_release_date (just the date part, in CST).
    Used when setting scheduled_release_date from a calculated release time.
    
    Args:
        release_datetime: datetime object (should be in CST)
        
    Returns:
        date object representing the scheduled release date
    """
    if isinstance(release_datetime, datetime):
        # If it has timezone info, convert to CST first
        if release_datetime.tzinfo:
            release_datetime = release_datetime.astimezone(CST)
        return release_datetime.date()
    
    return release_datetime
