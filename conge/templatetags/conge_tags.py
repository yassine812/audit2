"""Template tags pour le module congé."""

from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """
    Filtre Django pour accéder à un item d'un dictionnaire.
    
    Usage dans un template:
      {{ my_dict|get_item:key_variable }}
    """
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    return None
