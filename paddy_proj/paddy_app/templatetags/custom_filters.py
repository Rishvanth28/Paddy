from django import template

register = template.Library()

@register.filter
def sub(value, arg):
    """Subtract the arg from the value."""
    try:
        if value is None:
            value = 0
        if arg is None:
            arg = 0
        return float(value) - float(arg)
    except (ValueError, TypeError):
        return value
