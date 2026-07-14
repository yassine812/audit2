"""Alias de mixins/permissions pour compatibilité de structure."""

from .permissions import (  # noqa: F401
    DirectionOuHabiliteRequiredMixin,
    DocumentVisibilityQuerysetMixin,
    PiloteOuQSERequiredMixin,
    QSERequiredMixin,
)
