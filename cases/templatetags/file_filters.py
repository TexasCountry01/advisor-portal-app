import os

from django import template

register = template.Library()


@register.filter
def filename(value):
    """Extract just the filename from a file path."""
    if not value:
        return ''
    return os.path.basename(str(value))
