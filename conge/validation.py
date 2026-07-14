"""Logique de validation pour les congés.

Règles de la chaîne (une seule décision suffit) :
  - Demandeur OP / CE   → RS ou RO de sa section valident + reçoivent l'alerte
  - Demandeur RS        → RO de sa section valide + reçoit l'alerte
  - Demandeur RO        → is_assistante de la même société valide + reçoit l'alerte
  - Demandeur autre     → is_RO + is_assistante de la même société valident + reçoivent l'alerte
  - Superadmin          → reçoit TOUTES les alertes, peut tout valider/refuser
"""

from django.contrib.auth import get_user_model
from django.db.models import Q

User = get_user_model()


# ─────────────────────────────────────────────────────────────────────────────
# Helpers société
# ─────────────────────────────────────────────────────────────────────────────

def _get_societe(user):
    """Retourne la société de l'utilisateur (user.societe ou user.section.societe)."""
    if user.societe:
        return user.societe
    if user.section and user.section.societe:
        return user.section.societe
    return None


def _societe_q(societe):
    """Filtre Q : utilisateurs appartenant à une société donnée."""
    return Q(societe=societe) | Q(section__societe=societe) | Q(societes=societe)


# ─────────────────────────────────────────────────────────────────────────────
# Récupérateurs de validateurs
# ─────────────────────────────────────────────────────────────────────────────

def _get_section_rs_ro(user):
    """RS et RO actifs de la même section (pour demandeur OP/CE)."""
    if not user.section:
        return User.objects.filter(Q(is_RS=True) | Q(is_RO=True), is_active=True)
    return User.objects.filter(
        section=user.section, is_active=True,
    ).filter(Q(is_RS=True) | Q(is_RO=True))


def _get_section_ro(user):
    """RO actifs de la même section (pour demandeur RS)."""
    if not user.section:
        return User.objects.filter(is_RO=True, is_active=True)
    return User.objects.filter(section=user.section, is_RO=True, is_active=True)


def _get_societe_assistante(user):
    """is_assistante actifs de la même société (pour demandeur RO)."""
    societe = _get_societe(user)
    qs = User.objects.filter(is_assistante=True, is_active=True).exclude(pk=user.pk)
    if societe:
        qs = qs.filter(_societe_q(societe)).distinct()
    return qs


def _get_societe_ro_assistante(user):
    """is_RO + is_assistante actifs de la même société (pour demandeur autre)."""
    societe = _get_societe(user)
    qs = User.objects.filter(
        Q(is_RO=True) | Q(is_assistante=True), is_active=True,
    ).exclude(pk=user.pk)
    if societe:
        qs = qs.filter(_societe_q(societe)).distinct()
    return qs


# ─────────────────────────────────────────────────────────────────────────────
# Chaîne de validation
# ─────────────────────────────────────────────────────────────────────────────

def get_validation_chain_for_demande(demande):
    """
    Retourne la chaîne de validation applicable à la demande.
    UNE SEULE décision (validation ou refus) suffit.

    Returns : dict  { 'niveau', 'description', 'validateurs' }
    """
    demandeur = demande.demandeur

    if demandeur.is_OP or demandeur.is_CE:
        return {
            "niveau": "OP_CE",
            "description": "Validation par RS ou RO de la section",
            "validateurs": _get_section_rs_ro(demandeur),
        }

    if demandeur.is_RS:
        return {
            "niveau": "RS",
            "description": "Validation par RO de la section",
            "validateurs": _get_section_ro(demandeur),
        }

    if demandeur.is_RO:
        return {
            "niveau": "RO",
            "description": "Validation par Assistante (même société)",
            "validateurs": _get_societe_assistante(demandeur),
        }

    # Autres rôles (assistante, resp., divers, interimaire…)
    return {
        "niveau": "AUTRE",
        "description": "Validation par RO ou Assistante (même société)",
        "validateurs": _get_societe_ro_assistante(demandeur),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Droits de validation
# ─────────────────────────────────────────────────────────────────────────────

def peut_valider_conge(user, demande):
    """
    True si l'utilisateur peut valider ou refuser la demande.

    - Demande déjà traitée (validée/refusée) → False pour tous
    - Superadmin → True pour toute demande en attente (y compris la sienne)
    - Pas de validation de sa propre demande (règle pour les non-superadmin)
    - Sinon : l'utilisateur doit être dans la liste des validateurs de la chaîne
    """
    if not user.is_active:
        return False
    if demande.statut in [demande.STATUT_VALIDE, demande.STATUT_REFUSE]:
        return False
    if user.is_superuser:
        return True
    if user == demande.demandeur:
        return False
    chain = get_validation_chain_for_demande(demande)
    return user in chain["validateurs"]


# ─────────────────────────────────────────────────────────────────────────────
# Droits de consultation
# ─────────────────────────────────────────────────────────────────────────────

def peut_voir_conge(user, demande):
    """
    True si l'utilisateur peut consulter la demande.

    - Sa propre demande                                          → toujours
    - Superadmin                                                 → toutes
    - RS                  : demandes OP/CE de sa section
    - RO                  : demandes OP/CE/RS de sa section
                           + demandes RO/autres de même société
    - is_assistante        : demandes RO/autres (non-OP/CE/RS) de même société
    """
    if not user.is_active:
        return False
    if demande.demandeur == user:
        return True
    if user.is_superuser:
        return True

    demandeur = demande.demandeur

    # Demandeur OP ou CE : RS et RO de sa section peuvent consulter
    if demandeur.is_OP or demandeur.is_CE:
        if user.section and user.section == demandeur.section:
            if user.is_RS or user.is_RO:
                return True
        return False

    # Demandeur RS : RO de sa section peut consulter
    if demandeur.is_RS:
        if user.section and user.section == demandeur.section and user.is_RO:
            return True
        return False

    # Demandeur RO ou autre : is_RO et is_assistante de même société peuvent consulter
    societe_dem  = _get_societe(demandeur)
    societe_user = _get_societe(user)
    if societe_dem and societe_user and societe_dem == societe_user:
        if user.is_RO or user.is_assistante:
            return True

    return False


# ─────────────────────────────────────────────────────────────────────────────
# Utilitaires
# ─────────────────────────────────────────────────────────────────────────────

def get_prochains_validateurs(demande):
    """Validateurs potentiels pour une demande encore en attente."""
    chain = get_validation_chain_for_demande(demande)
    return chain["validateurs"].filter(is_active=True).exclude(pk=demande.demandeur.pk)


# ─────────────────────────────────────────────────────────────────────────────
# Actions
# ─────────────────────────────────────────────────────────────────────────────

def marquer_validation(demande, validateur, signature=""):
    """
    Valide la demande. Enregistre le validateur, la date, la signature et le statut.
    """
    from datetime import date
    demande.validateur            = validateur
    demande.date_validation       = date.today()
    demande.statut                = demande.STATUT_VALIDE
    demande.signature_responsable = signature
    if validateur.is_RS:
        demande.validateur_rs      = validateur
        demande.date_validation_rs = date.today()
    elif validateur.is_RO:
        demande.validateur_ro      = validateur
        demande.date_validation_ro = date.today()
    demande.save()


def refuser_conge(demande, validateur, motif):
    """Refuse la demande et enregistre le validateur et le motif."""
    from datetime import date
    demande.statut            = demande.STATUT_REFUSE
    demande.validateur        = validateur
    demande.date_validation   = date.today()
    demande.commentaire_refus = motif
    demande.save()
