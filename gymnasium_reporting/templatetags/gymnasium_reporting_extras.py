from django import template
from django.conf import settings
import os

register = template.Library()

@register.filter(name='basename')
def basename(value):
    """Extracts the basename of a file path."""
    return os.path.basename(value)

@register.simple_tag
def get_setting(name):
    """gets a django.conf setting"""
    return getattr(settings, name, "")
