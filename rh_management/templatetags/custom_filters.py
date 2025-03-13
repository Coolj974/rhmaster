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