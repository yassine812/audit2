"""Modèles de l'application Gestion des Accidents de Travail."""

import logging
from datetime import timedelta

from django.db import models
from django.utils import timezone

logger = logging.getLogger(__name__)


class AccidentTravail(models.Model):
    """Modèle principal — tronc commun de la déclaration d'accident."""

    TYPE_TRAVAIL = "travail"
    TYPE_TRAJET = "trajet"
    TYPE_CHOICES = [
        (TYPE_TRAVAIL, "Accident de travail"),
        (TYPE_TRAJET, "Accident de trajet"),
    ]

    STATUT_BROUILLON = "brouillon"
    STATUT_24H = "24h"
    STATUT_48H = "48h"
    STATUT_8J = "8j"
    STATUT_CLOTURE = "cloture"
    STATUT_CHOICES = [
        (STATUT_BROUILLON, "Brouillon (à compléter)"),
        (STATUT_24H, "Déclaration 24h en cours"),
        (STATUT_48H, "Analyse 48h en cours"),
        (STATUT_8J, "LAP 8 jours en cours"),
        (STATUT_CLOTURE, "Clôturé"),
    ]

    CONTRAT_CHOICES = [
        ("CDI", "CDI"),
        ("CDD", "CDD"),
        ("apprenti", "Apprenti/Élève"),
        ("interimaire", "Intérimaire"),
    ]

    LIEU_TYPE_CHOICES = [
        ("habituel", "Lieu de travail habituel"),
        ("occasionnel", "Lieu de travail occasionnel"),
        ("repas", "Lieu de repas"),
        ("trajet_domicile", "Trajet domicile/travail"),
        ("trajet_repas", "Trajet travail/repas"),
        ("deplacement", "Déplacement pour l'employeur"),
    ]

    CONSEQUENCE_SANS_ARRET = "sans_arret"
    CONSEQUENCE_AVEC_ARRET = "avec_arret"
    CONSEQUENCE_DECES = "deces"
    CONSEQUENCE_CHOICES = [
        (CONSEQUENCE_SANS_ARRET, "Sans arrêt de travail"),
        (CONSEQUENCE_AVEC_ARRET, "Avec arrêt de travail"),
        (CONSEQUENCE_DECES, "Décès"),
    ]

    # ── Identifiant ──────────────────────────────────────────────────────────
    reference = models.CharField(
        max_length=30, unique=True, blank=True,
        verbose_name="Référence",
        help_text="Généré automatiquement : AT + AAMMM + séquence (ex : AT2511001)",
    )
    type_accident = models.CharField(
        max_length=10, choices=TYPE_CHOICES, default=TYPE_TRAVAIL,
        verbose_name="Type d'accident",
    )
    statut = models.CharField(
        max_length=10, choices=STATUT_CHOICES, default=STATUT_24H,
        verbose_name="Statut",
    )

    # ── Rattachement organisationnel ─────────────────────────────────────────
    societe = models.ForeignKey(
        "accounts.Societe", on_delete=models.PROTECT, related_name="accidents",
        verbose_name="Société",
    )
    section = models.ForeignKey(
        "accounts.Section", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="accidents", verbose_name="Section",
    )
    site = models.ForeignKey(
        "accounts.Site", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="accidents", verbose_name="Site",
    )

    # ── Victime ──────────────────────────────────────────────────────────────
    victime_nom_prenom = models.CharField(max_length=200, verbose_name="Nom et prénom")

    # ── Informations accident ────────────────────────────────────────────────
    date_accident = models.DateField(verbose_name="Date de l'accident")
    heure_accident = models.TimeField(
        null=True, blank=True, verbose_name="Heure de l'accident",
    )
    lieu_accident = models.CharField(
        max_length=300, blank=True, verbose_name="Lieu de l'accident",
    )
    lieu_precisions = models.TextField(blank=True, verbose_name="Précisions sur le lieu")
    lieu_type = models.CharField(
        max_length=50, choices=LIEU_TYPE_CHOICES, blank=True,
        verbose_name="Type de lieu",
    )
    activite_victime = models.TextField(
        blank=True, verbose_name="Activité de la victime au moment de l'accident",
    )
    nature_accident = models.TextField(blank=True, verbose_name="Nature de l'accident")
    objet_contact = models.TextField(blank=True, verbose_name="Objet ou substance ayant causé la lésion")
    reserves = models.TextField(blank=True, verbose_name="Réserves")

    # ── Éléments matériels & lésions (JSONField) ─────────────────────────────
    elements_materiels = models.JSONField(
        default=list, blank=True, verbose_name="Éléments matériels",
        help_text="Liste des éléments matériels impliqués",
    )
    nature_lesions = models.JSONField(
        default=list, blank=True, verbose_name="Nature des lésions",
    )
    siege_lesions = models.JSONField(
        default=list, blank=True, verbose_name="Siège des lésions",
    )
    siege_lesions_schema = models.TextField(
        blank=True, verbose_name="Schéma siège des lésions",
        help_text="Image annotée (base64) du schéma corporel",
    )
    siege_lesions_arrows_data = models.JSONField(
        default=list, blank=True, verbose_name="Données des flèches du schéma",
        help_text="Coordonnées et types des flèches annotées sur le schéma corporel",
    )

    # ── EPI ──────────────────────────────────────────────────────────────────
    epi_endommage = models.BooleanField(null=True, verbose_name="EPI endommagé")
    epi_precisions = models.TextField(blank=True, verbose_name="Précisions EPI")

    # ── Soins ─────────────────────────────────────────────────────────────────
    premiers_soins = models.BooleanField(null=True, verbose_name="Premiers soins dispensés")
    premiers_soins_par = models.CharField(
        max_length=200, blank=True, verbose_name="Premiers soins par",
    )
    premiers_soins_lesquels = models.TextField(
        blank=True, verbose_name="Nature des premiers soins",
    )
    consultation_medecin = models.BooleanField(
        null=True, verbose_name="Consultation médecin",
    )
    consultation_medecin_info = models.TextField(
        blank=True, verbose_name="Informations consultation médecin",
    )
    transport_hopital = models.BooleanField(
        null=True, verbose_name="Transport hôpital",
    )
    transport_hopital_nom = models.CharField(
        max_length=300, blank=True, verbose_name="Nom de l'hôpital",
    )

    # ── Conséquences ─────────────────────────────────────────────────────────
    consequence = models.CharField(
        max_length=20, choices=CONSEQUENCE_CHOICES, blank=True,
        verbose_name="Conséquence",
    )
    rapport_police = models.BooleanField(null=True, verbose_name="Rapport de police établi")
    rapport_police_par = models.CharField(
        max_length=200, blank=True, verbose_name="Rapport de police par",
    )
    registre_benins_date = models.DateField(
        null=True, blank=True, verbose_name="Date d'inscription registre des accidents bénins",
        db_column="registre_benins_date",
    )
    registre_benins_numero = models.CharField(
        max_length=50, blank=True, verbose_name="N° registre accidents bénins",
        db_column="registre_benins_numero",
    )
    autres_victimes = models.BooleanField(
        null=True, verbose_name="Autres victimes",
    )

    # ── Horaires ─────────────────────────────────────────────────────────────
    horaire_debut1 = models.TimeField(null=True, blank=True, verbose_name="Début vacation 1")
    horaire_fin1 = models.TimeField(null=True, blank=True, verbose_name="Fin vacation 1")
    horaire_debut2 = models.TimeField(null=True, blank=True, verbose_name="Début vacation 2")
    horaire_fin2 = models.TimeField(null=True, blank=True, verbose_name="Fin vacation 2")

    # ── Constatation ─────────────────────────────────────────────────────────
    accident_constate_le = models.DateField(
        null=True, blank=True, verbose_name="Accident constaté le",
    )
    accident_constate_heure = models.TimeField(
        null=True, blank=True, verbose_name="Heure de constatation",
    )
    accident_constate_par = models.CharField(
        max_length=20,
        choices=[("employeur", "Par l'employeur"), ("preposes", "Par ses préposés"), ("victime", "Décrit par la victime")],
        blank=True, verbose_name="Constaté par",
    )
    accident_connu_le = models.DateField(
        null=True, blank=True, verbose_name="Accident connu le",
    )

    # ── Tiers ─────────────────────────────────────────────────────────────────
    tiers_implique = models.BooleanField(null=True, verbose_name="Tiers impliqué")
    tiers_nom_adresse = models.TextField(blank=True, verbose_name="Nom et adresse du tiers")
    tiers_assurance = models.CharField(
        max_length=200, blank=True, verbose_name="Assurance du tiers",
    )

    # ── Témoin / 1ère personne avisée ────────────────────────────────────────
    temoin_ou_premiere_personne = models.CharField(
        max_length=20,
        choices=[("temoin", "Témoin"), ("premiere_personne", "1ère personne avisée")],
        blank=True, verbose_name="Type de déclarant secondaire",
    )
    temoin_nom_prenom = models.CharField(
        max_length=200, blank=True, verbose_name="Nom et prénom témoin",
    )
    temoin_adresse = models.TextField(blank=True, verbose_name="Adresse témoin")

    # ── QR HSE ────────────────────────────────────────────────────────────────
    qr_hse = models.CharField(max_length=50, blank=True, verbose_name="QR HSE")

    # ── Circonstances détaillées ─────────────────────────────────────────────
    circonstances_detaillees = models.TextField(
        blank=True, verbose_name="Circonstances détaillées",
    )

    # ── Métadonnées ──────────────────────────────────────────────────────────
    created_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="accidents_crees", verbose_name="Créé par",
    )
    updated_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="accidents_modifies", verbose_name="Modifié par",
    )
    soumis_le = models.DateTimeField(
        null=True, blank=True, verbose_name="Formulaire 24h soumis le",
        help_text="Date/heure de soumission définitive de la déclaration 24h",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Créé le")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Modifié le")

    # ── Échéances calculées ───────────────────────────────────────────────────
    echeance_48h = models.DateTimeField(
        null=True, blank=True, verbose_name="Échéance analyse 48h",
    )
    echeance_8j = models.DateTimeField(
        null=True, blank=True, verbose_name="Échéance LAP 8 jours",
    )
    notification_brouillon_envoyee = models.BooleanField(
        default=False, verbose_name="Notification brouillon envoyée",
    )
    notification_48h_envoyee = models.BooleanField(
        default=False, verbose_name="Notification 48h envoyée",
    )
    notification_8j_envoyee = models.BooleanField(
        default=False, verbose_name="Notification 8 jours envoyée",
    )

    class Meta:
        verbose_name = "Accident de travail"
        verbose_name_plural = "Accidents de travail"
        ordering = ["-date_accident"]
        permissions = [
            ("can_view_all_societes", "Peut voir tous les accidents toutes sociétés"),
            ("can_export_accidents", "Peut exporter les données accidents"),
        ]

    def save(self, *args, **kwargs):
        # Auto-référence : AT + AAMMM + séquence (ex : AT2511001)
        if not self.reference:
            prefix = (
                self.date_accident.strftime("AT%y%m")
                if self.date_accident
                else timezone.now().strftime("AT%y%m")
            )
            last = (
                AccidentTravail.objects.filter(reference__startswith=prefix)
                .order_by("-reference")
                .values_list("reference", flat=True)
                .first()
            )
            next_num = int(last[-3:]) + 1 if last else 1
            self.reference = f"{prefix}{next_num:03d}"
            logger.info("Référence accident générée : %s", self.reference)

        # Calcul des échéances
        if self.date_accident and not self.echeance_48h:
            t = self.heure_accident or timezone.datetime.min.time()
            dt = timezone.datetime.combine(self.date_accident, t)
            self.echeance_48h = timezone.make_aware(dt) + timedelta(hours=48)
            self.echeance_8j = timezone.make_aware(dt) + timedelta(days=8)

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.reference} - {self.victime_nom_prenom} ({self.date_accident})"

    @property
    def statut_color(self):
        """Retourne la couleur Bootstrap associée au statut."""
        return {
            self.STATUT_BROUILLON: "secondary",
            self.STATUT_24H: "warning",
            self.STATUT_48H: "info",
            self.STATUT_8J: "primary",
            self.STATUT_CLOTURE: "success",
        }.get(self.statut, "secondary")

    @property
    def est_en_retard(self):
        """True si l'échéance courante est dépassée et l'accident non clôturé."""
        now = timezone.now()
        if self.statut == self.STATUT_24H and self.echeance_48h:
            return now > self.echeance_48h
        if self.statut == self.STATUT_48H and self.echeance_8j:
            return now > self.echeance_8j
        return False

    # Note: victime_age_calcule supprimé car victime_date_naissance a été retiré du modèle


# ─────────────────────────────────────────────────────────────────────────────
# Analyse 48h
# ─────────────────────────────────────────────────────────────────────────────

class Analyse48h(models.Model):
    """Feuille d'analyse approfondie réalisée dans les 48 heures."""

    accident = models.OneToOneField(
        AccidentTravail, on_delete=models.CASCADE, related_name="analyse_48h",
        verbose_name="Accident",
    )

    # ── Participants ─────────────────────────────────────────────────────────
    participants_exploitation = models.TextField(blank=True, verbose_name="Exploitation")
    participants_cssct = models.TextField(blank=True, verbose_name="CSSCT")
    participants_rh = models.TextField(blank=True, verbose_name="RH")
    participants_qse = models.TextField(blank=True, verbose_name="QSE")
    participants_direction = models.TextField(blank=True, verbose_name="Direction")
    participants_finance = models.TextField(blank=True, verbose_name="Finance")
    participants_achat = models.TextField(blank=True, verbose_name="Achat")
    participants_commercial = models.TextField(blank=True, verbose_name="Commercial")
    participants_autre = models.TextField(blank=True, verbose_name="Autre")
    participants_client = models.TextField(blank=True, verbose_name="Client")

    # ── Victime (compléments) ─────────────────────────────────────────────────
    victime_age = models.PositiveIntegerField(null=True, blank=True, verbose_name="Âge")
    victime_sexe = models.CharField(
        max_length=1,
        choices=[("M", "Masculin"), ("F", "Féminin")],
        blank=True, verbose_name="Sexe",
    )
    victime_date_visite_medicale = models.DateField(
        null=True, blank=True, verbose_name="Date de la dernière visite médicale",
    )
    victime_restriction_aptitude = models.BooleanField(
        null=True, verbose_name="Restriction d'aptitude",
    )
    victime_restriction_precisions = models.TextField(
        blank=True, verbose_name="Précisions restrictions",
    )
    victime_poste_occupe = models.CharField(
        max_length=200, blank=True, verbose_name="Poste occupé au moment de l'accident",
    )
    victime_anciennete_poste_analyse = models.CharField(
        max_length=100, blank=True, verbose_name="Ancienneté au poste",
    )
    victime_poste_conforme = models.BooleanField(
        null=True, verbose_name="Poste conforme à la fiche de poste",
    )
    
    # ── Horaires de travail ───────────────────────────────────────────────────
    horaire_travail = models.CharField(
        max_length=100, blank=True, verbose_name="Horaire de travail",
        help_text="Exemple: 08:00-12:00, 14:00-18:00",
    )

    # ── Formations (JSONField) ────────────────────────────────────────────────
    formations = models.JSONField(
        default=list, blank=True,
        verbose_name="Formations",
        help_text='[{"nom": str, "realise": "NA"|"O"|"N", "date": date, "commentaire": str}]',
    )

    # ── Milieu ────────────────────────────────────────────────────────────────
    emplacement_interieur_exterieur = models.CharField(
        max_length=10,
        choices=[("interieur", "Intérieur"), ("exterieur", "Extérieur")],
        blank=True, verbose_name="Intérieur / Extérieur",
    )
    poste_travail_habituel = models.BooleanField(
        null=True, verbose_name="Poste de travail habituel",
    )
    emplacement_connu_victime = models.BooleanField(
        null=True, verbose_name="Emplacement connu de la victime",
    )
    lieu_depart = models.CharField(
        max_length=300, blank=True, verbose_name="Lieu de départ",
    )
    lieu_arrivee = models.CharField(
        max_length=300, blank=True, verbose_name="Lieu d'arrivée",
    )
    motif_deplacement = models.CharField(
        max_length=300, blank=True, verbose_name="Motif du déplacement",
    )
    nuisances = models.JSONField(default=dict, blank=True, verbose_name="Nuisances")
    nuisances_precisions = models.TextField(blank=True, verbose_name="Précisions nuisances")

    # ── Description activité ──────────────────────────────────────────────────
    description_activite = models.TextField(
        blank=True, verbose_name="Description de l'activité",
    )

    # ── Arbre des causes ──────────────────────────────────────────────────────
    arbre_causes = models.JSONField(
        default=dict, blank=True, verbose_name="Arbre des causes",
        help_text='{"nodes": [...], "edges": [...]}',
    )

    # ── Données 5 Pourquoi ────────────────────────────────────────────────────
    pourquoi_data = models.JSONField(
        default=dict, blank=True, verbose_name="Données 5 Pourquoi",
        help_text='{"code": {"section":..., "question":..., "pourquoi":[p1,p2,p3,p4,p5]}}',
    )

    # ── Validation ────────────────────────────────────────────────────────────
    date_analyse = models.DateField(null=True, blank=True, verbose_name="Date de l'analyse")
    valide_par = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="analyses_validees", verbose_name="Validé par",
    )
    soumis_le = models.DateTimeField(
        null=True, blank=True, verbose_name="Soumis le",
        help_text="Date/heure de soumission définitive de l'analyse 48h",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Analyse 48h"
        verbose_name_plural = "Analyses 48h"

    def __str__(self):
        return f"Analyse 48h — {self.accident.reference}"

    @property
    def soumis_en_retard(self):
        """True si la soumission a eu lieu après l'échéance 48h."""
        if self.soumis_le and self.accident.echeance_48h:
            return self.soumis_le > self.accident.echeance_48h
        return False

    @property
    def delai_restant_heures(self):
        """Heures restantes avant l'échéance 48h (négatif si dépassé)."""
        from django.utils import timezone
        if self.accident.echeance_48h:
            delta = self.accident.echeance_48h - timezone.now()
            return round(delta.total_seconds() / 3600, 1)
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Causes racines (identifiées lors de l'analyse 48h — méthode 5 Pourquoi)
# ─────────────────────────────────────────────────────────────────────────────

class CauseRacine(models.Model):
    """Cause identifiée lors de l'analyse 48h (méthode des 5 Pourquoi).

    Chaque enregistrement représente une cause élémentaire saisie dans le
    formulaire 48h. Le libellé est réutilisable d'un accident à l'autre :
    la recherche d'autocomplète propose les libellés déjà saisis.
    """

    analyse = models.ForeignKey(
        Analyse48h, on_delete=models.CASCADE, related_name="causes_racines",
        verbose_name="Analyse 48h",
    )
    texte = models.CharField(max_length=500, verbose_name="Cause identifiée")
    ordre = models.PositiveIntegerField(default=0, verbose_name="Ordre d'affichage")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["ordre", "id"]
        verbose_name = "Cause racine"
        verbose_name_plural = "Causes racines"

    def __str__(self):
        return self.texte


class QuestionnaireTemplate(models.Model):
    """Référentiel des questions NA/O/N du questionnaire 48h."""

    code = models.CharField(max_length=10, unique=True, verbose_name="Code")
    section = models.CharField(max_length=100, verbose_name="Section")
    question = models.TextField(verbose_name="Question")
    est_sous_question = models.BooleanField(default=False, verbose_name="Sous-question")
    parent_code = models.CharField(max_length=10, blank=True, verbose_name="Code parent")
    condition_affichage = models.CharField(
        max_length=2, blank=True,
        verbose_name="Condition d'affichage",
        help_text="'O' ou 'N' : affiché si le parent vaut cette réponse",
    )
    ordre = models.PositiveIntegerField(default=0, verbose_name="Ordre")

    class Meta:
        ordering = ["ordre", "code"]
        verbose_name = "Question questionnaire 48h"
        verbose_name_plural = "Questions questionnaire 48h"

    def __str__(self):
        return f"{self.code} — {self.question[:60]}"


class QuestionnaireItem(models.Model):
    """Réponse à une question du questionnaire 48h pour une analyse donnée."""

    REPONSE_NA = "NA"
    REPONSE_OUI = "O"
    REPONSE_NON = "N"
    REPONSE_CHOICES = [
        (REPONSE_NA, "Non Applicable"),
        (REPONSE_OUI, "Oui"),
        (REPONSE_NON, "Non"),
    ]

    analyse = models.ForeignKey(
        Analyse48h, on_delete=models.CASCADE, related_name="questionnaire_items",
        verbose_name="Analyse",
    )
    code = models.CharField(max_length=10, verbose_name="Code")
    section = models.CharField(max_length=100, verbose_name="Section")
    question = models.TextField(verbose_name="Question")
    reponse = models.CharField(
        max_length=2, choices=REPONSE_CHOICES, blank=True, verbose_name="Réponse",
    )
    precisions = models.TextField(blank=True, verbose_name="Précisions")
    est_sous_question = models.BooleanField(default=False, verbose_name="Sous-question")
    parent_code = models.CharField(max_length=10, blank=True, verbose_name="Code parent")
    condition_affichage = models.CharField(max_length=2, blank=True)

    class Meta:
        ordering = ["code"]
        unique_together = [["analyse", "code"]]
        verbose_name = "Item questionnaire"
        verbose_name_plural = "Items questionnaire"

    def __str__(self):
        return f"{self.analyse} — {self.code}"


# ─────────────────────────────────────────────────────────────────────────────
# LAP 8 jours
# ─────────────────────────────────────────────────────────────────────────────

class LAP8Jours(models.Model):
    """Liste d'Actions de Progrès — à compléter dans les 8 jours suivant l'accident."""

    accident = models.OneToOneField(
        AccidentTravail, on_delete=models.CASCADE, related_name="lap_8j",
        verbose_name="Accident",
    )

    # ── Participants ─────────────────────────────────────────────────────────
    participants_exploitation = models.TextField(blank=True, verbose_name="Exploitation")
    participants_cssct = models.TextField(blank=True, verbose_name="CSSCT")
    participants_rh = models.TextField(blank=True, verbose_name="RH")
    participants_qse = models.TextField(blank=True, verbose_name="QSE")
    participants_direction = models.TextField(blank=True, verbose_name="Direction")
    participants_finance = models.TextField(blank=True, verbose_name="Finance")
    participants_achat = models.TextField(blank=True, verbose_name="Achat")
    participants_commercial = models.TextField(blank=True, verbose_name="Commercial")
    participants_autre = models.TextField(blank=True, verbose_name="Autre")
    participants_client = models.TextField(blank=True, verbose_name="Client")

    # ── Communication ─────────────────────────────────────────────────────────
    communication_alerte_securite = models.BooleanField(
        null=True, verbose_name="Alerte sécurité communiquée",
    )
    communication_date = models.DateField(
        null=True, blank=True, verbose_name="Date communication",
    )
    mise_a_jour_duer = models.BooleanField(null=True, verbose_name="DUER mis à jour")
    duer_date = models.DateField(null=True, blank=True, verbose_name="Date MàJ DUER")
    transversalisation_groupe = models.BooleanField(
        null=True, verbose_name="Transversalisé au groupe",
    )
    transversalisation_date = models.DateField(
        null=True, blank=True, verbose_name="Date transversalisation",
    )
    transversalisation_valide_par = models.CharField(
        max_length=200, blank=True, verbose_name="Transversalisation validée par",
    )

    soumis_le = models.DateTimeField(
        null=True, blank=True, verbose_name="Soumis le",
        help_text="Date/heure de soumission définitive du LAP 8 jours",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "LAP 8 jours"
        verbose_name_plural = "LAP 8 jours"

    def __str__(self):
        return f"LAP 8j — {self.accident.reference}"

    @property
    def soumis_en_retard(self):
        """True si la soumission a eu lieu après l'échéance 8 jours."""
        if self.soumis_le and self.accident.echeance_8j:
            return self.soumis_le > self.accident.echeance_8j
        return False

    @property
    def delai_restant_heures(self):
        """Heures restantes avant l'échéance 8 jours (négatif si dépassé)."""
        from django.utils import timezone
        if self.accident.echeance_8j:
            delta = self.accident.echeance_8j - timezone.now()
            return round(delta.total_seconds() / 3600, 1)
        return None


class ActionCorrective(models.Model):
    """Action corrective ou préventive liée à un LAP 8 jours."""

    STATUT_CHOICES = [
        ("non_demarre", "Non démarré"),
        ("en_cours", "En cours"),
        ("realise", "Réalisé"),
        ("verifie", "Vérifié"),
    ]

    lap = models.ForeignKey(
        LAP8Jours, on_delete=models.CASCADE, related_name="actions",
        verbose_name="LAP 8 jours",
    )
    cause_racine = models.TextField(verbose_name="Cause racine")
    description = models.TextField(verbose_name="Action corrective / préventive")
    pilote = models.CharField(max_length=200, blank=True, verbose_name="Pilote")
    delai = models.DateField(null=True, blank=True, verbose_name="Délai")
    date_realisation = models.DateField(
        null=True, blank=True, verbose_name="Date de réalisation",
    )
    date_verification = models.DateField(
        null=True, blank=True, verbose_name="Date de vérification",
    )
    statut = models.CharField(
        max_length=20, choices=STATUT_CHOICES, default="non_demarre",
        verbose_name="Statut",
    )
    efficace = models.BooleanField(null=True, verbose_name="Action efficace")
    ordre = models.PositiveIntegerField(default=1, verbose_name="Ordre")

    class Meta:
        ordering = ["ordre"]
        verbose_name = "Action corrective"
        verbose_name_plural = "Actions correctives"

    def __str__(self):
        return f"{self.lap} — {self.description[:60]}"


class ActionCorrectiveImmédiate(models.Model):
    """Action corrective immédiate (formulaire 24h)."""

    STATUT_CHOICES = [
        ("non_demarre", "Non démarré"),
        ("en_cours", "En cours"),
        ("realise", "Réalisé"),
    ]

    accident = models.ForeignKey(
        AccidentTravail, on_delete=models.CASCADE,
        related_name="actions_correctives_immediates",
        verbose_name="Accident",
    )
    description = models.TextField(verbose_name="Description de l'action")
    pilote = models.CharField(max_length=200, blank=True, verbose_name="Pilote")
    delai = models.DateField(null=True, blank=True, verbose_name="Délai")
    statut = models.CharField(
        max_length=20, choices=STATUT_CHOICES, default="non_demarre",
        verbose_name="Statut",
    )
    ordre = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["ordre"]
        verbose_name = "Action corrective immédiate"
        verbose_name_plural = "Actions correctives immédiates"

    def __str__(self):
        return f"{self.accident.reference} — {self.description[:60]}"
