from django import template
import os

register = template.Library()

@register.filter(name='basename')
def basename(value):
    """Extracts the basename of a file path."""
    return os.path.basename(value)
