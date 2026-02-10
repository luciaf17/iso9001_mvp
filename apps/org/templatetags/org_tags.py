import re

from django import template


register = template.Library()


@register.filter
def extract_tag(value):
    if not value:
        return ""

    match = re.search(r"\((.*?)\)", str(value))
    if not match:
        return ""

    tag = match.group(1) or ""
    return tag.strip()
