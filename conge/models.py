"""Modèles du module Gestion des Congés."""

import logging
from django.conf import settings
from django.db import models
from django.utils import timezone

logger = logging.getLogger(__name__)


class DemandeConge(models.Model):
    """Demande de congé soumise par un opérateur."""

    # ── Statuts ──────────────────────────────────────────────────────────────
    STATUT_EN_ATTENTE = "en_attente"
    STATUT_VALIDE     = "valide"
    STATUT_REFUSE     = "refuse"
    STATUT_CHOICES = [
        (STATUT_EN_ATTENTE, "En attente"),
        (STATUT_VALIDE,     "Validé"),
        (STATUT_REFUSE,     "Refusé"),
    ]

    # ── Types de congé (imputation) ───────────────────────────────────────────
    TYPE_CONGES_PAYES       = "conges_payes"
    TYPE_BANQUE_HEURES      = "banque_heures"
    TYPE_CONGES_ANCIENNETE  = "conges_anciennete"
    TYPE_EVENEMENT_FAMILIAL = "evenement_familial"
    TYPE_AUTRE               = "autre"
    TYPE_CONGES_SANS_SOLDE  = "conges_sans_solde"
    TYPE_CONGE_CHOICES = [
        (TYPE_CONGES_PAYES,       "Congés payés"),
        (TYPE_BANQUE_HEURES,      "Banque d'heures"),
        (TYPE_CONGES_ANCIENNETE,  "Congés ancienneté"),
        (TYPE_EVENEMENT_FAMILIAL, "Événement familial"),
        (TYPE_AUTRE,              "Autre (imputation manuelle)"),
        (TYPE_CONGES_SANS_SOLDE,  "Congés sans solde"),
    ]

    # ── Demandeur ─────────────────────────────────────────────────────────────
    demandeur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="demandes_conge",
        verbose_name="Demandeur",
    )
    nom    = models.CharField(max_length=100, verbose_name="Nom")
    prenom = models.CharField(max_length=100, verbose_name="Prénom")
    section = models.ForeignKey(
        "accounts.Section",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="demandes_conge",
        verbose_name="Section",
    )

    # ── Période d'absence ─────────────────────────────────────────────────────
    date_debut   = models.DateField(verbose_name="S'absentera du")
    date_fin     = models.DateField(verbose_name="Au")
    date_reprise = models.DateField(verbose_name="Date de la reprise")
    nombre_jours = models.PositiveSmallIntegerField(verbose_name="Nombre de jour(s)")

    # ── Type d'imputation ─────────────────────────────────────────────────────
    type_conge = models.CharField(
        max_length=30,
        choices=TYPE_CONGE_CHOICES,
        verbose_name="Imputation sur",
    )
    evenement_familial_precision = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Préciser lequel (événement familial)",
    )

    # ── Workflow ──────────────────────────────────────────────────────────────
    statut = models.CharField(
        max_length=20,
        choices=STATUT_CHOICES,
        default=STATUT_EN_ATTENTE,
        verbose_name="Statut",
    )
    date_demande   = models.DateField(auto_now_add=True, verbose_name="Date de la demande")
    date_validation = models.DateField(
        null=True, blank=True,
        verbose_name="Date de validation",
    )
    validateur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="conges_traites",
        verbose_name="Validateur",
    )
    commentaire_refus = models.TextField(blank=True, verbose_name="Commentaire de refus")

    # ── Validation en cascade (RS → RO) ───────────────────────────────────────
    validateur_rs = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="conges_valides_rs",
        verbose_name="Validateur (Responsable Site)",
    )
    date_validation_rs = models.DateField(
        null=True, blank=True,
        verbose_name="Date validation RS",
    )
    validateur_ro = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="conges_valides_ro",
        verbose_name="Validateur (Responsable Opérationnel)",
    )
    date_validation_ro = models.DateField(
        null=True, blank=True,
        verbose_name="Date validation RO",
    )

    # ── Signatures électroniques (data URL base64 PNG) ────────────────────────
    signature_demandeur  = models.TextField(blank=True, verbose_name="Signature du demandeur")
    signature_responsable = models.TextField(blank=True, verbose_name="Signature du responsable")

    # ── Timestamps ────────────────────────────────────────────────────────────
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date_demande", "-created_at"]
        verbose_name = "Demande de congé"
        verbose_name_plural = "Demandes de congé"

    def __str__(self) -> str:
        return (
            f"Congé {self.nom} {self.prenom} "
            f"du {self.date_debut} au {self.date_fin} "
            f"[{self.get_statut_display()}]"
        )

    # ── Propriétés pratiques ───────────────────────────────────────────────────
    @property
    def is_en_attente(self) -> bool:
        return self.statut == self.STATUT_EN_ATTENTE

    @property
    def is_valide(self) -> bool:
        return self.statut == self.STATUT_VALIDE

    @property
    def is_refuse(self) -> bool:
        return self.statut == self.STATUT_REFUSE


# ─────────────────────────────────────────────────────────────────────────────
# Configuration de la Chaîne de Validation
# ─────────────────────────────────────────────────────────────────────────────

class ValidationChainConfiguration(models.Model):
    """
    Configuration de la chaîne de validation (d'alerte) pour une section.
    
    Permet de définir pour chaque section:
    - Qui sont les validateurs RO (Responsables Opérationnels)
    - Qui sont les validateurs RS (Responsables Site)
    - Qui sont les gestionnaires CE (Chefs d'équipe)
    - Qui reçoit les notifications (emails)
    """

    # ── Identifiant ───────────────────────────────────────────────────────────
    section = models.OneToOneField(
        "accounts.Section",
        on_delete=models.CASCADE,
        related_name="validation_chain_config",
        verbose_name="Section",
    )

    # ── Validateurs RO (Responsables Opérationnels) ──────────────────────────
    validateurs_ro = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="validation_chain_ro",
        blank=True,
        verbose_name="Validateurs RO (Responsables Opérationnels)",
        help_text="Utilisateurs qui valident les demandes au niveau RO",
    )

    # ── Validateurs RS (Responsables Site) ─────────────────────────────────
    validateurs_rs = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="validation_chain_rs",
        blank=True,
        verbose_name="Validateurs RS (Responsables Site)",
        help_text="Utilisateurs qui valident les demandes au niveau RS",
    )

    # ── Gestionnaires CE (Chefs d'équipe) ──────────────────────────────────
    gestionnaires_ce = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="validation_chain_ce",
        blank=True,
        verbose_name="Gestionnaires CE (Chefs d'équipe)",
        help_text="Utilisateurs qui gèrent les demandes CE",
    )

    # ── Audit ───────────────────────────────────────────────────────────────
    date_modification = models.DateTimeField(auto_now=True)
    modifie_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="validation_chain_modifications",
        verbose_name="Modifié par",
    )

    class Meta:
        verbose_name = "Configuration de chaîne de validation"
        verbose_name_plural = "Configurations de chaînes de validation"
        ordering = ("section__Nom",)

    def __str__(self) -> str:
        return f"Chaîne de validation - {self.section}"
