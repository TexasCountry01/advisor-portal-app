"""Custom template filters for timezone handling"""

from django import template
from django.utils import timezone
import pytz

register = template.Library()

CST = pytz.timezone('America/Chicago')


@register.filter
def to_cst(value):
    """Convert a datetime to CST and format it with timezone indicator"""
    if not value:
        return ''
    
    # Convert to CST
    if value.tzinfo is None:
        # Naive datetime - assume UTC
        value = timezone.make_aware(value, timezone.utc)
    
    cst_time = value.astimezone(CST)
    
    # Format: "M d, Y at g:i A CST" (without leading zeros for hour)
    formatted = cst_time.strftime('%b %d, %Y at %I:%M %p CST').lstrip('0')
    return formatted
