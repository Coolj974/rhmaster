from django import template

register = template.Library()

@register.filter
def in_group(user, group_name):
    """Vérifie si l'utilisateur appartient à un groupe spécifique"""
    return user.groups.filter(name=group_name).exists()

@register.filter
def split(value, sep):
    """Split a string into a list on sep."""
    if value:
        return value.split(sep)
    return []

@register.filter
def in_list(value, list_string):
    """Check if the value is in a comma-separated list."""
    if list_string:
        items = list_string.split(',')
        return value in items
    return False

@register.filter
def multiply(value, arg):
    """Multiplie la valeur par l'argument"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def intdiv(value, arg):
    """Division entière sécurisée"""
    try:
        arg = int(arg)
        if arg == 0:
            return 0
        return int(value) // arg
    except (ValueError, TypeError):
        return 0

@register.filter
def divide(value, arg):
    """Division décimale sécurisée"""
    try:
        arg = float(arg)
        if arg == 0:
            return 0
        return float(value) / arg
    except (ValueError, TypeError):
        return 0