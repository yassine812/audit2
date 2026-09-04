"""Modèles de l'application Plan de Prévention Simplifié (PDP)."""

import logging
from django.conf import settings
from django.db import models
from django.utils import timezone
from django.urls import reverse

from .constants import DEFAULT_PREDEFINED_RISKS

logger = logging.getLogger(__name__)


class PlanPrevention(models.Model):
    """Fiche principale du Plan de Prévention Simplifié (PDP)."""

    TYPE_PONCTUELLE = "ponctuelle"
    TYPE_ANNUELLE = "annuelle"
    TYPE_CHOICES = [
        (TYPE_PONCTUELLE, "Ponctuelle"),
        (TYPE_ANNUELLE, "Annuelle"),
    ]

    STATUT_BROUILLON = "brouillon"
    STATUT_VALIDE = "valide"
    STATUT_CLOTURE = "cloture"
    STATUT_CHOICES = [
        (STATUT_BROUILLON, "Brouillon"),
        (STATUT_VALIDE, "Validé / En cours"),
        (STATUT_CLOTURE, "Clôturé / Archivé"),
    ]

    # ── Identifiant & Organisation ───────────────────────────────────────────
    reference = models.CharField(
        max_length=30,
        unique=True,
        blank=True,
        verbose_name="Référence PDP",
        help_text="Généré automatiquement : PDP + AAMMM + séquence (ex : PDP2609001)",
    )
    societe = models.ForeignKey(
        "accounts.Societe",
        on_delete=models.PROTECT,
        related_name="plans_prevention",
        verbose_name="Société (E.E.)",
    )
    section = models.ForeignKey(
        "accounts.Section",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="plans_prevention",
        verbose_name="Section",
    )
    site = models.ForeignKey(
        "accounts.Site",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="plans_prevention",
        verbose_name="Site concerné",
    )
    customer = models.ForeignKey(
        "accounts.Customer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="plans_prevention",
        verbose_name="Client E.U. (Sage)",
    )

    # ── Header / Opération ───────────────────────────────────────────────────
    type_operation = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default=TYPE_PONCTUELLE,
        verbose_name="Nature de l'opération (Type)",
    )
    nature_operation = models.CharField(
        max_length=255,

        blank=True,
        default="",
        verbose_name="Intitulé de l'opération",
    )

    # ── Entreprise Utilisatrice (E.U.) ────────────────────────────────────────
    eu_nom = models.CharField(max_length=200, blank=True, default="", verbose_name="E.U. - Nom")
    eu_adresse = models.TextField(blank=True, verbose_name="E.U. - Adresse")
    eu_telephone = models.CharField(max_length=50, blank=True, verbose_name="E.U. - Téléphone")
    eu_representant_nom = models.CharField(max_length=150, blank=True, verbose_name="E.U. - Représentant (M.)")
    eu_representant_fonction = models.CharField(max_length=150, blank=True, verbose_name="E.U. - Fonction")
    eu_representant_telephone = models.CharField(max_length=50, blank=True, verbose_name="E.U. - Représentant Tél.")

    # ── Entreprise Extérieure (E.E.) ──────────────────────────────────────────
    ee_nom = models.CharField(max_length=200, blank=True, default="", verbose_name="E.E. - Nom")
    ee_adresse = models.TextField(blank=True, verbose_name="E.E. - Adresse")
    ee_telephone = models.CharField(max_length=50, blank=True, verbose_name="E.E. - Téléphone")
    ee_representant_nom = models.CharField(max_length=150, blank=True, verbose_name="E.E. - Représentant (M.)")
    ee_representant_fonction = models.CharField(max_length=150, blank=True, verbose_name="E.E. - Fonction")
    ee_representant_telephone = models.CharField(max_length=50, blank=True, verbose_name="E.E. - Représentant Tél.")

    # ── Intervention ─────────────────────────────────────────────────────────
    lieu_intervention = models.CharField(max_length=255, blank=True, verbose_name="Lieu de l'intervention")
    date_debut = models.DateField(null=True, blank=True, verbose_name="Date prévue de début")
    date_fin = models.DateField(null=True, blank=True, verbose_name="Date prévue de fin")
    horaire_travail = models.CharField(max_length=150, blank=True, verbose_name="Horaire de travail prévu")
    effectif_prevu = models.CharField(max_length=100, blank=True, verbose_name="Effectif E.E. prévu sur le site")
    duree_approximative = models.CharField(max_length=100, blank=True, verbose_name="Durée approximative de l'opération")
    sous_traitants = models.TextField(blank=True, verbose_name="Sous-traitants éventuels")

    # ── Consignes particulières / Visite préalable ────────────────────────────
    date_visite_prealable = models.DateField(null=True, blank=True, verbose_name="Date de la visite préalable")
    secteur_intervention = models.CharField(max_length=255, blank=True, verbose_name="Secteur d'intervention")
    itineraire = models.TextField(
        blank=True,
        default="",
        verbose_name="Itinéraire à suivre",
    )
    zone_danger_particulier = models.TextField(blank=True, verbose_name="Zone présentant un danger particulier")
    locaux_mis_disposition = models.TextField(
        blank=True,
        verbose_name="Locaux (bureaux, vestiaires, sanitaires, réfectoires) mis à disposition de l'E.E.",
    )
    appareils_mis_disposition = models.TextField(
        blank=True,
        default="",
        verbose_name="Appareils mis à disposition par l'E.U. à l'E.E.",
    )

    # ── Organisation des secours ──────────────────────────────────────────────
    numeros_urgence = models.TextField(
        blank=True,
        default="",
        verbose_name="Numéros d'urgence du site",
    )
    infirmerie_trousse_sst_location = models.TextField(
        blank=True,
        verbose_name="Emplacement de l'infirmerie, trousse de secours, liste des SST",
    )
    consigne_evacuation = models.TextField(
        blank=True,
        verbose_name="Consigne en cas d'évacuation générale",
    )

    # ── Suivi Médical Renforcé (SIR) ──────────────────────────────────────────
    suivi_medical_renforce = models.BooleanField(
        default=False,
        verbose_name="Postes relevant d'un Suivi Individuel Renforcé (SIR) ?",
    )
    postes_concernes = models.TextField(
        blank=True,
        verbose_name="Postes concernés (+ copie Médecine du Travail)",
    )

    # ── Remarques CSSCT & Signatures ──────────────────────────────────────────
    remarques_cssct = models.TextField(
        blank=True,
        verbose_name="Remarques et avis du CSSCT de l'E.E. si nécessaire",
    )
    date_signature_eu = models.DateField(null=True, blank=True, verbose_name="Date signature E.U.")
    signature_eu_nom = models.CharField(max_length=150, blank=True, verbose_name="Nom signataire E.U.")
    signature_eu_image = models.TextField(blank=True, verbose_name="Signature E.U. (Base64)")

    date_signature_ee = models.DateField(null=True, blank=True, verbose_name="Date signature E.E.")
    signature_ee_nom = models.CharField(max_length=150, blank=True, verbose_name="Nom signataire E.E.")
    signature_ee_image = models.TextField(blank=True, verbose_name="Signature E.E. (Base64)")

    # ── Statut & Métadonnées ──────────────────────────────────────────────────
    statut = models.CharField(
        max_length=20,
        choices=STATUT_CHOICES,
        default=STATUT_BROUILLON,
        verbose_name="Statut du document",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="plans_prevention_crees",
        verbose_name="Créateur",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Dernière modification")

    class Meta:
        verbose_name = "Plan de Prévention Simplifié"
        verbose_name_plural = "Plans de Prévention Simplifiés"
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"{self.reference or f'PDP #{self.pk}'} - {self.eu_nom} / {self.nature_operation}"

    def get_absolute_url(self):
        return reverse("plan_prevention:detail", kwargs={"pk": self.pk})

    def generate_reference(self):
        """Génère la référence unique du PDP : PDP + YYMM + Séquence sur 3 chiffres."""
        now = timezone.now()
        prefix = f"PDP{now.strftime('%y%m')}"
        last_pdp = (
            PlanPrevention.objects.filter(reference__startswith=prefix)
            .order_by("-reference")
            .first()
        )
        if last_pdp and len(last_pdp.reference) >= 9:
            try:
                seq = int(last_pdp.reference[7:]) + 1
            except ValueError:
                seq = 1
        else:
            seq = 1
        return f"{prefix}{seq:03d}"

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = self.generate_reference()
        super().save(*args, **kwargs)

    @property
    def risques(self):
        """Retourne les risques associés au PDP via la table de jonction PlanPreventionRisque."""
        return self.pdp_risques.select_related("risque").all()

    def populate_default_risks(self):
        """Obsolète: un nouveau PDP ne doit plus avoir de risques automatiquement pré-associés."""
        pass


# ──────────────────────────────────────────────────────────────────────────────
# RisquePDP — Catalogue dédié au Plan de Prévention (Indépendant de Processus)
# ──────────────────────────────────────────────────────────────────────────────
class RisquePDP(models.Model):
    """Catalogue des risques propres au Plan de Prévention (PDP).
    
    Totalement indépendant de Processus et du DUERP.
    """

    code = models.CharField(max_length=50, unique=True, verbose_name="Code")
    titre = models.CharField(max_length=255, verbose_name="Titre / Risque")
    description = models.TextField(blank=True, verbose_name="Description détaillée")
    categorie = models.CharField(max_length=100, blank=True, verbose_name="Catégorie")
    mesures_prevention_recommandees = models.TextField(
        blank=True, verbose_name="Mesures de prévention recommandées"
    )
    est_actif = models.BooleanField(default=True, verbose_name="Actif")
    ordre = models.PositiveIntegerField(default=0, verbose_name="Ordre d'affichage")
    cree_le = models.DateTimeField(auto_now_add=True, verbose_name="Créé le")
    mis_a_jour_le = models.DateTimeField(auto_now=True, verbose_name="Mis à jour le")

    class Meta:
        verbose_name = "Risque PDP"
        verbose_name_plural = "Catalogue des Risques PDP"
        ordering = ("ordre", "code")

    def __str__(self) -> str:
        return f"{self.code} - {self.titre}" if self.code else self.titre


class PlanPreventionRisque(models.Model):
    """Table d'association PDP <-> RisquePDP, contenant les données spécifiques au PDP."""

    pdp = models.ForeignKey(
        PlanPrevention,
        on_delete=models.CASCADE,
        related_name="pdp_risques",
        verbose_name="Plan de prévention",
    )
    risque = models.ForeignKey(
        RisquePDP,
        on_delete=models.CASCADE,
        related_name="pdp_associations",
        verbose_name="Risque PDP",
    )
    concerne_eu = models.BooleanField(default=False, verbose_name="Risque / Interférence E.U.")
    concerne_ee = models.BooleanField(default=False, verbose_name="Risque E.E.")
    mesures_prevention = models.TextField(blank=True, verbose_name="Mesures de prévention retenues")
    mise_en_oeuvre_eu = models.BooleanField(default=False, verbose_name="Mise en œuvre E.U.")
    mise_en_oeuvre_ee = models.BooleanField(default=False, verbose_name="Mise en œuvre E.E.")
    ordre = models.IntegerField(default=0, verbose_name="Ordre d'affichage")

    class Meta:
        verbose_name = "Risque PDP"
        verbose_name_plural = "Risques PDP"
        ordering = ("ordre", "pk")

    def __str__(self) -> str:
        return f"Risque PDP #{self.ordre} ({self.pdp.reference})"

