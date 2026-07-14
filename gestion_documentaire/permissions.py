"""Permissions et rôles RBAC du module gestion_documentaire."""

from __future__ import annotations

from functools import wraps
from typing import Iterable

from django.contrib.auth.models import Group
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied


ROLE_QSE = "qse"
ROLE_PILOTE_PROCESSUS = "pilote_processus"
ROLE_DIRECTION = "direction"
ROLE_UTILISATEUR = "utilisateur"


def peut_consulter_module(user) -> bool:
    """Profils autorisés à voir le module, avec exclusion client/opérateur."""
    if not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False):
        return True
    if getattr(user, "is_CLT", False) or getattr(user, "is_OP", False):
        return False
    return any(
        getattr(user, flag, False)
        for flag in ("is_CE", "is_RS", "is_RO", "is_assistante", "is_auditeur")
    )


def peut_modifier_bibliotheque(user) -> bool:
    """Superadmin, ou profil cumulant RO et auditeur."""
    return bool(
        getattr(user, "is_authenticated", False)
        and (
            getattr(user, "is_superuser", False)
            or (getattr(user, "is_RO", False) and getattr(user, "is_auditeur", False))
        )
    )


class ModuleDocumentaireRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return peut_consulter_module(self.request.user)

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            raise PermissionDenied("Accès interdit au module de gestion documentaire.")
        return super().handle_no_permission()


class ModificationBibliothequeRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return peut_modifier_bibliotheque(self.request.user)

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            raise PermissionDenied("Modification réservée au superadmin ou au profil RO et auditeur.")
        return super().handle_no_permission()


def module_documentaire_required(view_func):
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        if not peut_consulter_module(request.user):
            raise PermissionDenied("Accès interdit au module de gestion documentaire.")
        return view_func(request, *args, **kwargs)
    return wrapped


def modification_bibliotheque_required(view_func):
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        if not peut_modifier_bibliotheque(request.user):
            raise PermissionDenied("Modification réservée au superadmin ou au profil RO et auditeur.")
        return view_func(request, *args, **kwargs)
    return wrapped

ALL_ROLES = (
    ROLE_QSE,
    ROLE_PILOTE_PROCESSUS,
    ROLE_DIRECTION,
    ROLE_UTILISATEUR,
)


def normalize_role_name(role_name: str) -> str:
    """Normalise une chaîne de rôle pour comparaison."""
    return (role_name or "").strip().lower()


def ensure_document_roles_exist() -> None:
    """Crée les groupes de rôles documentaires s'ils n'existent pas."""
    for role in ALL_ROLES:
        Group.objects.get_or_create(name=role)


def user_has_role(user, role_name: str) -> bool:
    """Retourne vrai si l'utilisateur possède le rôle (ou est superuser)."""
    if not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False):
        return True
    return user.groups.filter(name=normalize_role_name(role_name)).exists()


def user_has_any_role(user, role_names: Iterable[str]) -> bool:
    """Retourne vrai si l'utilisateur a au moins un rôle parmi la liste."""
    normalized = [normalize_role_name(role) for role in role_names]
    if not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False):
        return True
    return user.groups.filter(name__in=normalized).exists()


def is_qse(user) -> bool:
    """Vrai si utilisateur QSE."""
    return user_has_role(user, ROLE_QSE)


def is_pilote_ou_qse(user) -> bool:
    """Vrai si utilisateur pilote de processus ou QSE."""
    return user_has_any_role(user, (ROLE_QSE, ROLE_PILOTE_PROCESSUS))


def is_direction_ou_habilite(user) -> bool:
    """Vrai si utilisateur direction ou profil habilité (QSE/pilote)."""
    return user_has_any_role(user, (ROLE_QSE, ROLE_DIRECTION, ROLE_PILOTE_PROCESSUS))


def is_standard_user(user) -> bool:
    """Vrai si l'utilisateur n'est ni QSE, ni pilote, ni direction."""
    if not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False):
        return False
    return not user_has_any_role(user, (ROLE_QSE, ROLE_PILOTE_PROCESSUS, ROLE_DIRECTION))


def filter_documents_for_user(queryset, user):
    """Restreint la visibilité: standard => documents applicables uniquement."""
    if not getattr(user, "is_authenticated", False):
        return queryset.none()

    # QSE, Direction, Pilote et superuser voient tout sauf les suppressions logiques.
    if user_has_any_role(user, (ROLE_QSE, ROLE_PILOTE_PROCESSUS, ROLE_DIRECTION)):
        return queryset.filter(est_supprime=False)

    # Utilisateur standard: seulement les documents applicables.
    return queryset.filter(statut="applicable", est_supprime=False)


class BaseRoleRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Mixin parent pour contrôler l'accès par rôles."""

    allowed_roles: tuple[str, ...] = ()
    permission_denied_message = "Vous n'avez pas les permissions nécessaires."

    def test_func(self):
        return user_has_any_role(self.request.user, self.allowed_roles)

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            raise PermissionDenied(self.permission_denied_message)
        return super().handle_no_permission()


class QSERequiredMixin(BaseRoleRequiredMixin):
    """Accès réservé au rôle QSE."""

    allowed_roles = (ROLE_QSE,)


class PiloteOuQSERequiredMixin(BaseRoleRequiredMixin):
    """Accès réservé à Pilote de processus ou QSE."""

    allowed_roles = (ROLE_QSE, ROLE_PILOTE_PROCESSUS)


class DirectionOuHabiliteRequiredMixin(BaseRoleRequiredMixin):
    """Accès réservé à Direction ou profil habilité (QSE/Pilote)."""

    allowed_roles = (ROLE_QSE, ROLE_DIRECTION, ROLE_PILOTE_PROCESSUS)


class DocumentVisibilityQuerysetMixin(LoginRequiredMixin):
    """Applique les règles de visibilité documentaire par rôle utilisateur."""

    def get_queryset(self):
        base_queryset = super().get_queryset()
        return filter_documents_for_user(base_queryset, self.request.user)


def role_required(*role_names: str):
    """Décorateur générique d'autorisation par rôle."""

    def decorator(view_func):
        @wraps(view_func)
        @user_passes_test(lambda user: user_has_any_role(user, role_names), login_url="/login/")
        def _wrapped(request, *args, **kwargs):
            return view_func(request, *args, **kwargs)

        return _wrapped

    return decorator


qse_required = role_required(ROLE_QSE)
pilote_ou_qse_required = role_required(ROLE_QSE, ROLE_PILOTE_PROCESSUS)
direction_ou_habilite_required = role_required(ROLE_QSE, ROLE_DIRECTION, ROLE_PILOTE_PROCESSUS)
