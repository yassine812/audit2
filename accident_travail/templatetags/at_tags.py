"""Template tags pour le module Accidents de Travail."""

from django import template
from django.utils.html import format_html

register = template.Library()


@register.inclusion_tag("accident_travail/partials/_statut_badge.html")
def statut_badge(accident):
    """Affiche un badge coloré selon le statut de l'accident."""
    return {"accident": accident}


@register.simple_tag
def statut_color(statut):
    """Retourne la classe Bootstrap correspondant au statut."""
    colors = {
        "brouillon": "secondary",
        "24h": "warning",
        "48h": "info",
        "8j": "primary",
        "cloture": "success",
    }
    return colors.get(statut, "secondary")


@register.simple_tag
def progression_pct(statut):
    """Retourne le pourcentage de progression (pour une barre de progression)."""
    pct = {"brouillon": 5, "24h": 25, "48h": 50, "8j": 75, "cloture": 100}
    return pct.get(statut, 0)


@register.filter
def get_item(dictionary, key):
    """Filtre pour accéder à un élément d'un dict dans un template."""
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    return None


@register.filter
def is_in_list(value, lst):
    """Retourne True si value est dans lst (JSONField list)."""
    if isinstance(lst, list):
        return value in lst
    return False


@register.filter
def split(value, sep=","):
    """Divise une chaîne par séparateur."""
    return value.split(sep)


@register.filter
def getfield(form, field_name):
    """Retourne le BoundField d'un formulaire par nom."""
    return form[field_name]


@register.inclusion_tag("accident_travail/partials/_progression_steps.html")
def progression_steps(accident):
    """Affiche les étapes de progression de l'accident."""
    return {"accident": accident}
