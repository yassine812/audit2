from django import template
import json
import ast

register = template.Library()

def _render_lines(data) -> list[str]:
    lines: list[str] = []
    if isinstance(data, dict):
        for k, v in data.items():
            if isinstance(v, (dict, list)):
                lines.append(f"- {k}:")
                for sub in _render_lines(v):
                    lines.append(f"  {sub}")
            else:
                lines.append(f"- {k}: {v}")
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, (dict, list)):
                lines.append(f"-")
                for sub in _render_lines(item):
                    lines.append(f"  {sub}")
            else:
                lines.append(f"- {item}")
    return lines


@register.filter
def pretty_note(value: str) -> str:
    """
    Render a note string. If it's JSON or Python literal-like, pretty-print as bullet lines.
    Otherwise, return the original string.
    """
    if not isinstance(value, str):
        return str(value)
    s = value.strip()
    if not s:
        return ''
    # First try strict JSON
    try:
        data = json.loads(s)
        return "\n".join(_render_lines(data)) if isinstance(data, (dict, list)) else s
    except Exception:
        pass
    # Fallback: Python literal (e.g., single quotes)
    try:
        data = ast.literal_eval(s)
        return "\n".join(_render_lines(data)) if isinstance(data, (dict, list)) else s
    except Exception:
        return s

@register.filter
def nl2br(value: str) -> str:
    """Convert newlines to <br> for HTML display."""
    if not isinstance(value, str):
        return value
    return value.replace('\n', '<br>')


@register.filter
def confidence_label(value: str) -> str:
    """
    Retourne un label lisible pour le niveau de confiance de la recherche AI.
    """
    labels = {
        'high': '✓ Fiabilité élevée',
        'medium': '⚠ Fiabilité moyenne',
        'low': '⚠ Fiabilité faible',
        'none': '✗ Échec'
    }
    return labels.get(value, '⚠ Fiabilité moyenne')


@register.filter
def confidence_badge(value: str) -> str:
    """
    Retourne la classe CSS Bootstrap pour le badge de confiance.
    """
    badges = {
        'high': 'success',
        'medium': 'warning',
        'low': 'warning',
        'none': 'danger'
    }
    return badges.get(value, 'secondary')
