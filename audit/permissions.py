"""Règles d'accès métier pour le module audit."""

from __future__ import annotations

from typing import Iterable

from django.http import HttpResponseForbidden
from django.shortcuts import render

from .models import AuditType

CREATE_RULES = {
    AuditType.INTERNE: ("is_superuser", "is_auditeur"),
    AuditType.SITE: ("is_superuser", "is_auditeur"),
    AuditType.POSTE: ("is_superuser", "is_auditeur", "is_RS", "is_RO"),
    AuditType.EQUIPEMENT: ("is_superuser", "is_auditeur", "is_RO"),
}

USE_RULES = {
    AuditType.INTERNE: ("is_superuser", "is_auditeur", "is_RO"),
    AuditType.SITE: ("is_superuser", "is_auditeur", "is_RO"),
    AuditType.POSTE: ("is_superuser", "is_auditeur", "is_RO", "is_RS", "is_CE"),
    AuditType.EQUIPEMENT: ("is_superuser", "is_auditeur", "is_RO", "is_RS", "is_OP"),
}


def _has_any_flag(user, flags: Iterable[str]) -> bool:
    """Vérifie qu'un utilisateur possède au moins un rôle autorisé."""
    return any(bool(getattr(user, flag, False)) for flag in flags)


def user_can_create_audit(user, audit_type: str) -> bool:
    """Retourne vrai si l'utilisateur peut créer/lancer ce type d'audit."""
    flags = CREATE_RULES.get(audit_type, ())
    return _has_any_flag(user, flags)


def user_can_use_audit(user, audit_type: str) -> bool:
    """Retourne vrai si l'utilisateur peut saisir/consulter ce type d'audit."""
    flags = USE_RULES.get(audit_type, ())
    return _has_any_flag(user, flags)


def filter_allowed_types_for_create(user) -> list[str]:
    """Liste des types d'audit que l'utilisateur peut créer."""
    return [audit_type for audit_type in CREATE_RULES if user_can_create_audit(user, audit_type)]


def filter_allowed_types_for_use(user) -> list[str]:
    """Liste des types d'audit que l'utilisateur peut consulter/utiliser."""
    return [audit_type for audit_type in USE_RULES if user_can_use_audit(user, audit_type)]


class PermissionDeniedTemplateMixin:
    """Rend une page 403 explicite au lieu d'une redirection implicite."""

    permission_message = "Vous n'êtes pas autorisé à accéder à cette ressource."

    def render_forbidden(self, request):
        """Retourne une réponse HTTP 403 avec template dédié."""
        return HttpResponseForbidden(
            render(
                request,
                "403.html",
                {"message": self.permission_message},
                status=403,
            ).content
        )


class CanCreateAuditMixin(PermissionDeniedTemplateMixin):
    """Autorise l'accès seulement si l'utilisateur peut créer ce type d'audit."""

    def get_audit_type_for_permission(self):
        return self.kwargs.get("type_audit") or self.request.POST.get("type_audit") or self.request.GET.get("type_audit")

    def dispatch(self, request, *args, **kwargs):
        audit_type = self.get_audit_type_for_permission()
        if audit_type and not user_can_create_audit(request.user, audit_type):
            return self.render_forbidden(request)
        return super().dispatch(request, *args, **kwargs)


class CanUseAuditMixin(PermissionDeniedTemplateMixin):
    """Autorise l'accès seulement si l'utilisateur peut utiliser ce type d'audit."""

    def get_audit_type_for_permission(self):
        return self.kwargs.get("type_audit") or self.request.POST.get("type_audit") or self.request.GET.get("type_audit")

    def dispatch(self, request, *args, **kwargs):
        audit_type = self.get_audit_type_for_permission()
        if audit_type and not user_can_use_audit(request.user, audit_type):
            return self.render_forbidden(request)
        return super().dispatch(request, *args, **kwargs)
