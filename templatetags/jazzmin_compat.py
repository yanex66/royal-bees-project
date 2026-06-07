from django import template
from django.utils.html import format_html
from jazzmin.templatetags import jazzmin as original_jazzmin

register = template.Library()

@register.simple_tag
def jazzmin_paginator_number(cl, i):
    """
    Overriding the broken Jazzmin tag to fix "args or kwargs must be provided"
    """
    inline_safe = original_jazzmin.jazzmin_paginator_number(cl, i)
    # We strip the original formatting and return a safe string
    return format_html("{}", inline_safe)