"""Règles d'accès et filtrage multi-tenant pour le module Plan de Prévention (PDP).

Réutilise STRICTEMENT les mécanismes d'autorisation et d'isolation par société
existants dans l'application accounts / conge / accident_travail.
"""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Q

from accounts.models import Societe


def get_user_societe(user):
    """Retourne la société principale de l'utilisateur."""
    if hasattr(user, "societe") and user.societe:
        return user.societe
    if hasattr(user, "section") and user.section and user.section.societe:
        return user.section.societe
    return None


def get_societe_q_filter(societe):
    """Filtre Q pour isoler les données appartenant à une société donnée."""
    if not societe:
        return Q(pk__in=[])
    return Q(societe=societe) | Q(section__societe=societe)


def user_can_create_pdp(user) -> bool:
    """True si l'utilisateur peut créer un nouveau PDP."""
    if not user.is_authenticated:
        return False
    return bool(
        user.is_superuser
        or user.is_RS
        or user.is_RO
        or user.is_assistante
        or getattr(user, "is_auditeur", False)
    )


def user_can_edit_pdp(user, pdp) -> bool:
    """True si l'utilisateur a le droit de modifier ce PDP."""
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    # Vérification du tenant
    user_soc = get_user_societe(user)
    if user_soc and pdp.societe != user_soc and not user.societes.filter(pk=pdp.societe.pk).exists():
        return False
    return bool(user.is_RS or user.is_RO or user.is_assistante or pdp.created_by_id == user.pk)


def user_can_delete_pdp(user, pdp) -> bool:
    """True si l'utilisateur a le droit de supprimer ce PDP."""
    if not user.is_authenticated:
        return False
    if user.is_superuser or user.is_RO:
        return True
    return False


def user_can_add_pdp_risk(user) -> bool:
    """True si l'utilisateur peut créer un nouveau Risque PDP.

    Autorisé uniquement pour :
    - Administrateur (is_staff / is_admin)
    - RO (Responsable Opérationnel : is_RO)
    - Auditeur (is_auditeur)
    - Superuser (is_superuser)
    """
    if not user or not user.is_authenticated:
        return False
    is_admin = bool(
        getattr(user, "is_superuser", False)
        or getattr(user, "is_staff", False)
        or getattr(user, "is_admin", False)
    )
    return bool(
        is_admin
        or getattr(user, "is_RO", False)
        or getattr(user, "is_auditeur", False)
    )



def user_can_view_pdp(user, pdp) -> bool:
    """True si l'utilisateur peut consulter ce PDP."""
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    user_soc = get_user_societe(user)
    if not user_soc:
        return True
    return bool(
        pdp.societe == user_soc
        or (pdp.section and pdp.section.societe == user_soc)
        or user.societes.filter(pk=pdp.societe.pk).exists()
    )


def filter_pdp_queryset_for_user(qs, user):
    """Filtre un QuerySet PDP selon les droits et la société de l'utilisateur."""
    if not user.is_authenticated:
        return qs.none()
    if user.is_superuser:
        return qs
    user_soc = get_user_societe(user)
    if not user_soc:
        return qs.filter(created_by=user)
    
    # Restreindre aux PDP de la société ou des sociétés associées
    user_societes_ids = list(user.societes.values_list("pk", flat=True))
    if user_soc.pk not in user_societes_ids:
        user_societes_ids.append(user_soc.pk)
        
    return qs.filter(
        Q(societe_id__in=user_societes_ids)
        | Q(section__societe_id__in=user_societes_ids)
        | Q(created_by=user)
    ).distinct()


class PDPTenantScopedQuerySetMixin(LoginRequiredMixin):
    """Mixin CBV assurant l'isolation multi-tenant automatique des QuerySets."""

    def get_queryset(self):
        qs = super().get_queryset()
        return filter_pdp_queryset_for_user(qs, self.request.user)


class PDPCreatePermissionMixin(LoginRequiredMixin):
    """Mixin interdisant la création si l'utilisateur n'a pas le rôle requis."""

    def dispatch(self, request, *args, **kwargs):
        if not user_can_create_pdp(request.user):
            raise PermissionDenied("Vous n'avez pas les droits nécessaires pour créer un Plan de Prévention.")
        return super().dispatch(request, *args, **kwargs)


class PDPEditPermissionMixin(LoginRequiredMixin):
    """Mixin interdisant la modification d'un PDP non autorisé."""

    def dispatch(self, request, *args, **kwargs):
        obj = self.get_object()
        if not user_can_edit_pdp(request.user, obj):
            raise PermissionDenied("Accès refusé : vous n'avez pas le droit de modifier ce Plan de Prévention.")
        return super().dispatch(request, *args, **kwargs)
