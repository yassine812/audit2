"""Services métier du module Achats."""

from decimal import Decimal

from django.core.mail import send_mail
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from .models import (
    ConfigurationValidationSection,
    DemandeAchat,
    Dysfonctionnement,
    EtapeValidation,
    EvaluationFournisseur,
    Fournisseur,
    ReceptionMarchandise,
)


def user_can_validate_etape(user, etape):
    """Indique si l'utilisateur courant peut traiter une étape selon son rôle."""
    if user is None or not getattr(user, "is_authenticated", False):
        return False

    if etape.statut != EtapeValidation.STATUT_EN_ATTENTE:
        return False

    if etape.validateur_id:
        return etape.validateur_id == user.pk

    if etape.niveau == EtapeValidation.NIVEAU_DIRECTEUR_POLE:
        return user.is_RO

    if etape.niveau == EtapeValidation.NIVEAU_DIRECTEUR_GENERAL:
        return user.is_superuser

    return False


def _users_for_validation_level(niveau):
    """Retourne les utilisateurs à notifier pour un niveau de validation donné."""
    from accounts.models import User

    queryset = User.objects.filter(is_active=True).exclude(email="")
    if niveau == EtapeValidation.NIVEAU_DIRECTEUR_POLE:
        return queryset.filter(is_RO=True)
    if niveau == EtapeValidation.NIVEAU_DIRECTEUR_GENERAL:
        return queryset.filter(is_superuser=True)
    return queryset.none()


def _resolve_validateurs_for_demande(demande):
    """Retourne les validateurs configurés pour la section d'une demande."""
    config = (
        ConfigurationValidationSection.objects.select_related("validateur_n1", "validateur_n2")
        .filter(section=demande.section_analytique)
        .first()
    )
    if not config:
        return None, None
    return config.validateur_n1, config.validateur_n2


def _send_notification_email(subject, message, recipients):
    """Envoie un email simple sans bloquer le workflow si aucun destinataire n'existe."""
    recipient_list = sorted({email for email in recipients if email})
    if not recipient_list:
        return 0

    return send_mail(
        subject=subject,
        message=message,
        from_email=None,
        recipient_list=recipient_list,
        fail_silently=True,
    )


def _notify_validation_required(demande, niveau, validateur=None):
    """Notifie les utilisateurs concernés lorsqu'une validation est attendue."""
    if validateur is not None:
        recipients = [validateur.email]
    else:
        recipients = _users_for_validation_level(niveau).values_list("email", flat=True)
    niveau_label = "N1" if niveau == EtapeValidation.NIVEAU_DIRECTEUR_POLE else "N2"
    subject = f"[Achats] Validation {niveau_label} requise pour {demande.numero}"
    message = (
        f"Une demande d'achat nécessite votre validation.\n\n"
        f"Demande : {demande.numero}\n"
        f"Demandeur : {demande.demandeur}\n"
        f"Section : {demande.section_analytique}\n"
        f"Statut : {demande.get_statut_display()}\n"
        f"Montant HT : {demande.total_commande_ht or 0}\n"
    )
    return _send_notification_email(subject, message, recipients)


def _notify_demande_status(demande, decision, acteur, commentaire=""):
    """Notifie le demandeur après une décision de validation ou de retour."""
    if not demande.demandeur.email:
        return 0

    decision_map = {
        EtapeValidation.STATUT_APPROUVE: "validée",
        EtapeValidation.STATUT_REFUSE: "refusée",
        EtapeValidation.STATUT_MODIFICATION_DEMANDEE: "retournée pour modification",
    }
    subject = f"[Achats] Mise à jour de votre demande {demande.numero}"
    message = (
        f"Votre demande d'achat {demande.numero} a été {decision_map.get(decision, 'mise à jour')}.\n\n"
        f"Traité par : {acteur}\n"
        f"Nouveau statut : {demande.get_statut_display()}\n"
    )
    if commentaire:
        message += f"Commentaire : {commentaire}\n"

    return _send_notification_email(subject, message, [demande.demandeur.email])


@transaction.atomic
def lancer_circuit_validation(demande):
    """Lance le circuit hiérarchique après saisie et sélection des devis."""
    if demande.statut != DemandeAchat.STATUT_EN_COURS_DEVIS:
        raise ValidationError(
            "Le circuit de validation ne peut être lancé que pour une demande en cours de devis.",
        )

    if not demande.lignes.exists():
        raise ValidationError("La demande doit contenir au moins une ligne avant transmission.")

    validateur_n1, validateur_n2 = _resolve_validateurs_for_demande(demande)

    if validateur_n1 is None and not demandeur_ro_exists():
        raise ValidationError("Aucun utilisateur avec le rôle RO n'est configuré pour valider le niveau N1.")

    if validateur_n2 is None and not superadmin_exists():
        raise ValidationError("Aucun super administrateur n'est configuré pour valider le niveau N2.")

    demande.etapes.filter(statut=EtapeValidation.STATUT_EN_ATTENTE).delete()
    etape = EtapeValidation.objects.create(
        demande=demande,
        niveau=EtapeValidation.NIVEAU_DIRECTEUR_POLE,
        validateur=validateur_n1,
        statut=EtapeValidation.STATUT_EN_ATTENTE,
    )
    demande.statut = DemandeAchat.STATUT_VALIDATION_N1
    demande.save(update_fields=["statut", "date_modification"])
    _notify_validation_required(demande, EtapeValidation.NIVEAU_DIRECTEUR_POLE, validateur_n1)
    return etape


def demandeur_ro_exists():
    """Indique si au moins un utilisateur RO peut traiter le niveau N1."""
    from accounts.models import User

    return User.objects.filter(is_active=True, is_RO=True).exists()


def superadmin_exists():
    """Indique si au moins un super administrateur peut traiter le niveau N2."""
    from accounts.models import User

    return User.objects.filter(is_active=True, is_superuser=True).exists()


@transaction.atomic
def traiter_validation_demande(demande, etape, decision, commentaire, user):
    """Traite une décision de validation sur une demande d'achat."""
    if etape.demande_id != demande.pk:
        raise ValidationError("L'étape de validation ne correspond pas à cette demande.")

    if etape.statut != EtapeValidation.STATUT_EN_ATTENTE:
        raise ValidationError("Cette étape de validation a déjà été traitée.")

    if not user_can_validate_etape(user, etape):
        raise PermissionDenied("Vous n'êtes pas autorisé à traiter cette étape de validation.")

    commentaire = (commentaire or "").strip()
    if decision in {
        EtapeValidation.STATUT_REFUSE,
        EtapeValidation.STATUT_MODIFICATION_DEMANDEE,
    } and not commentaire:
        raise ValidationError(
            "Un commentaire est obligatoire pour un refus ou une demande de modification.",
        )

    etape.statut = decision
    etape.validateur = user
    etape.commentaire = commentaire
    etape.date_action = timezone.now()
    etape.save(update_fields=["statut", "validateur", "commentaire", "date_action"])

    demande.etapes.exclude(pk=etape.pk).filter(
        statut=EtapeValidation.STATUT_EN_ATTENTE,
    ).delete()

    if decision == EtapeValidation.STATUT_APPROUVE:
        if etape.niveau == EtapeValidation.NIVEAU_DIRECTEUR_POLE:
            _, validateur_n2 = _resolve_validateurs_for_demande(demande)
            EtapeValidation.objects.create(
                demande=demande,
                niveau=EtapeValidation.NIVEAU_DIRECTEUR_GENERAL,
                validateur=validateur_n2,
                statut=EtapeValidation.STATUT_EN_ATTENTE,
            )
            demande.statut = DemandeAchat.STATUT_VALIDATION_N2
        elif etape.niveau == EtapeValidation.NIVEAU_DIRECTEUR_GENERAL:
            demande.statut = DemandeAchat.STATUT_VALIDEE
        else:
            raise ValidationError("Le niveau d'étape de validation est invalide.")
    elif decision == EtapeValidation.STATUT_REFUSE:
        demande.statut = DemandeAchat.STATUT_REFUSEE
    elif decision == EtapeValidation.STATUT_MODIFICATION_DEMANDEE:
        demande.statut = DemandeAchat.STATUT_SOUMISE
    else:
        raise ValidationError("La décision de validation est invalide.")

    demande.save(update_fields=["statut", "date_modification"])
    if decision == EtapeValidation.STATUT_APPROUVE and etape.niveau == EtapeValidation.NIVEAU_DIRECTEUR_POLE:
        _, validateur_n2 = _resolve_validateurs_for_demande(demande)
        _notify_validation_required(demande, EtapeValidation.NIVEAU_DIRECTEUR_GENERAL, validateur_n2)
    else:
        _notify_demande_status(demande, decision, user, commentaire)
    return demande


def mes_demandes_a_valider(user):
    """Retourne les demandes ayant une étape en attente pour l'utilisateur."""
    filters = Q(etapes__statut=EtapeValidation.STATUT_EN_ATTENTE, etapes__validateur=user)
    if user.is_RO:
        filters |= Q(
            etapes__statut=EtapeValidation.STATUT_EN_ATTENTE,
            etapes__niveau=EtapeValidation.NIVEAU_DIRECTEUR_POLE,
            etapes__validateur__isnull=True,
        )
    if user.is_superuser:
        filters |= Q(
            etapes__statut=EtapeValidation.STATUT_EN_ATTENTE,
            etapes__niveau=EtapeValidation.NIVEAU_DIRECTEUR_GENERAL,
            etapes__validateur__isnull=True,
        )

    return (
        DemandeAchat.objects.filter(
            filters,
        )
        .select_related("demandeur", "section_analytique")
        .prefetch_related("lignes", "etapes")
        .distinct()
    )


def _calculer_note_depuis_score(score):
    """Détermine la note fournisseur à partir d'un score."""
    if score < Decimal("60"):
        return ReceptionMarchandise.NOTE_D
    if score < Decimal("75"):
        return ReceptionMarchandise.NOTE_C
    if score < Decimal("90"):
        return ReceptionMarchandise.NOTE_B
    return ReceptionMarchandise.NOTE_A


@transaction.atomic
def calculer_evaluation_fournisseur(fournisseur, annee):
    """Calcule l'évaluation annuelle d'un fournisseur à partir des réceptions liées."""
    receptions = list(
        ReceptionMarchandise.objects.filter(
            date_reception__year=annee,
            demande__lignes__fournisseur_retenu=fournisseur,
        )
        .select_related("demande")
        .distinct()
    )

    if not receptions:
        return None

    scores = [reception.score_calcule for reception in receptions if reception.score_calcule is not None]
    total_scores = sum(scores, Decimal("0.00"))
    score_moyen = (total_scores / Decimal(len(scores))).quantize(Decimal("0.01"))
    note = _calculer_note_depuis_score(score_moyen)

    nb_dysfonctionnements = (
        Dysfonctionnement.objects.filter(
            Q(
                reception__date_reception__year=annee,
                reception__demande__lignes__fournisseur_retenu=fournisseur,
            )
            | Q(
                date_signalement__year=annee,
                demande__lignes__fournisseur_retenu=fournisseur,
            )
        )
        .distinct()
        .count()
    )

    evaluation, _ = EvaluationFournisseur.objects.get_or_create(
        fournisseur=fournisseur,
        annee=annee,
        defaults={"pris_en_compte": fournisseur.pris_en_compte},
    )
    evaluation.pris_en_compte = fournisseur.pris_en_compte
    evaluation.nb_receptions_evaluees = len(receptions)
    evaluation.score_moyen = score_moyen
    evaluation.note = note
    evaluation.nb_dysfonctionnements = nb_dysfonctionnements
    evaluation.save()

    fournisseur.statut_evaluation = note
    fournisseur.save(update_fields=["statut_evaluation"])
    return evaluation


def calculer_toutes_evaluations(annee):
    """Calcule les évaluations annuelles pour tous les fournisseurs pris en compte."""
    evaluations = []
    for fournisseur in Fournisseur.objects.filter(pris_en_compte=True):
        evaluation = calculer_evaluation_fournisseur(fournisseur, annee)
        if evaluation is not None:
            evaluations.append(evaluation)
    return evaluations
