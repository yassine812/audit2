"""Mixin et décorateur de permissions pour le module Accidents de Travail."""

from functools import wraps

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied

from .models import AccidentTravail


def user_has_at_access(user):
    """Autorise uniquement superadmin, RS et RO sur le module AT."""
    return bool(
        user.is_authenticated
        and (
            user.is_superuser
            or getattr(user, "is_RS", False)
            or getattr(user, "is_RO", False)
        )
    )


def at_roles_required(view_func):
    """Décorateur FBV : accès réservé à superadmin, RS, RO."""

    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not user_has_at_access(request.user):
            raise PermissionDenied
        return view_func(request, *args, **kwargs)

    return _wrapped


class AccidentPermissionMixin(LoginRequiredMixin):
    """
    Contrôle d'accès pour les vues du module AT.

    Règles :
        - RO, RS et superadmin : accès autorisé.
    - Filtrage par société : un utilisateur voit uniquement les accidents de
            sa section.societe, sauf is_superuser qui voit tout.
    - Aucune suppression n'est exposée.
    """

    def get_queryset(self):
        qs = AccidentTravail.objects.select_related("societe", "section", "site")
        user = self.request.user
        if user.is_superuser:
            pass  # voit tous les accidents
        else:
            # RO et RS : voit uniquement les accidents de sa section
            if user.section:
                qs = qs.filter(section=user.section)
            else:
                qs = qs.none()
        return qs

    def can_edit(self, accident=None):
        user = self.request.user
        return user_has_at_access(user)

    def dispatch(self, request, *args, **kwargs):
        if not user_has_at_access(request.user):
            raise PermissionDenied
        response = super().dispatch(request, *args, **kwargs)
        # Pour les vues d'édition, vérifier les droits
        if request.method in ("POST", "PUT", "PATCH") and not self.can_edit():
            raise PermissionDenied
        return response
