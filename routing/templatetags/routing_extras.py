from django import template

register = template.Library()

@register.filter
def short_token(value):
    """
    Extracts the sequence number from token 'OFFICE-DATE-SEQ'.
    Example: '050317-20251213-023' -> '023'
    """
    if not value or '-' not in value:
        return value
    try:
        return value.split('-')[-1]
    except Exception:
        return value

@register.filter
def is_eq(value, arg):
    """
    Compares two values for equality (coercing to string).
    Usage: {% if value|is_eq:arg %}
    """
    return str(value) == str(arg)
