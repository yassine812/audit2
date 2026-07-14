import logging
from datetime import date
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models import Max
from django.utils import timezone

logger = logging.getLogger(__name__)


class AuditType(models.TextChoices):
    """Types d'audit autorisés."""

    INTERNE = "INTERNE", "Audit interne"
    SITE = "SITE", "Audit site"
    POSTE = "POSTE", "Audit de poste"
    EQUIPEMENT = "EQUIPEMENT", "Audit équipement"


class AuditStatut(models.TextChoices):
    """Statuts du cycle de vie d'un audit."""

    BROUILLON = "BROUILLON", "Brouillon"
    PLANIFIER = "PLANIFIER", "Planifié"
    EN_COURS = "EN_COURS", "En cours"
    TERMINE = "TERMINE", "Terminé"



class NormeDocument(models.Model):
    """Document normatif (ISO, OHSAS, etc.)."""

    nom = models.CharField(max_length=255, unique=True)
    actif = models.BooleanField(default=True)
    fichier = models.FileField(upload_to="normes/", null=True, blank=True)

    class Meta:
        ordering = ("nom",)
        verbose_name = "Norme documentaire"
        verbose_name_plural = "Normes documentaires"

    def __str__(self) -> str:
        return self.nom


class ChapitreNorme(models.Model):
    """Chapitre de norme rattaché à un document."""

    norme = models.ForeignKey(
        NormeDocument,
        on_delete=models.PROTECT,
        related_name="chapitres",
    )
    reference = models.CharField(max_length=100)
    intitule = models.CharField(max_length=255)
    num_page = models.PositiveSmallIntegerField(null=True, blank=True)
    actif = models.BooleanField(default=True)

    class Meta:
        ordering = ("norme__nom", "reference")
        unique_together = ("norme", "reference")
        verbose_name = "Chapitre de norme"
        verbose_name_plural = "Chapitres de norme"

    def __str__(self) -> str:
        return f"{self.norme} - {self.reference}"


class Theme(models.Model):
    """Thème de référentiel audit."""

    texte = models.CharField(max_length=255)
    actif = models.BooleanField(default=True)

    class Meta:
        ordering = ("texte",)
        verbose_name = "Thème"
        verbose_name_plural = "Thèmes"

    def __str__(self) -> str:
        # show the text; chapters can be listed where appropriate in templates
        return self.texte


class CritereEvaluation(models.Model):
    """Critère à évaluer pendant l'audit."""

    theme = models.ForeignKey(
        Theme,
        on_delete=models.PROTECT,
        related_name="criteres",
        null=True,
    )
    texte = models.TextField()
    actif = models.BooleanField(default=True)
    chapitre_norme = models.ManyToManyField(
        ChapitreNorme,
        related_name="criteres",
        blank=True,
    )
    preuves_attendues = models.ManyToManyField(
        "PreuveAttendue",
        related_name="criteres_preuves",
        blank=True,
    )

    class Meta:
        ordering = ("theme", "id")
        verbose_name = "Critère d'évaluation"
        verbose_name_plural = "Critères d'évaluation"

    def __str__(self) -> str:
        return f"{self.theme} - {self.id}"


class BaremeCotation(models.Model):
    """Barème de cotation (C/PC/NC)."""

    code = models.CharField(max_length=10, unique=True)
    note = models.DecimalField(max_digits=5, decimal_places=2)
    description = models.CharField(max_length=255)
    actif = models.BooleanField(default=True)

    class Meta:
        ordering = ("-note", "code")
        verbose_name = "Barème de cotation"
        verbose_name_plural = "Barèmes de cotation"

    def __str__(self) -> str:
        return f"{self.code} ({self.note})"


class PreuveAttendue(models.Model):
    libelle = models.TextField()
    code = models.CharField(max_length=10, blank=True)
    actif = models.BooleanField(default=True)

    # optional relation to a type/category of preuve
    type_preuve = models.ForeignKey(
        'PreuveAttendueType',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='preuves',
    )

    def __str__(self) -> str:
        return self.libelle


class PreuveAttendueType(models.Model):
    """Type ou catégorie d'une preuve attendue (ex: Photo, Document, Déclaration)."""

    nom = models.CharField(max_length=150, unique=True)
    actif = models.BooleanField(default=True)

    class Meta:
        ordering = ('nom',)
        verbose_name = 'Type de preuve attendue'
        verbose_name_plural = 'Types de preuves attendues'

    def __str__(self) -> str:
        return self.nom


class NiveauxAttendus(models.Model):
    """Niveaux attendus pour un type d'audit (ex: seuil en pourcentage)."""

    actif = models.BooleanField(default=True)
    valeur = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="Pourcentage (0-100)",
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    description = models.TextField(blank=True)
    type_audit = models.CharField(max_length=20, choices=AuditType.choices, null=True, blank=True)

    class Meta:
        verbose_name = "Niveau attendu"
        verbose_name_plural = "Niveaux attendus"

    def __str__(self) -> str:
        return f"{self.valeur}% - {self.get_type_audit_display()}"


class FormulaireAudit(models.Model):
    """En-tête du formulaire d'audit."""

    titre = models.CharField(max_length=255)
    type_audit = models.CharField(max_length=20, choices=AuditType.choices)
    section = models.ForeignKey(
        "accounts.Section",
        on_delete=models.PROTECT,
        related_name="formulaires_audit",
        null=True,
        blank=True,
    )
    actif = models.BooleanField(default=True)
    cree_le = models.DateTimeField(auto_now_add=True)

    # Types autorisant plusieurs formulaires par section
    MULTI_FORMULAIRE_TYPES = {AuditType.EQUIPEMENT, AuditType.POSTE}

    class Meta:
        ordering = ("section", "type_audit", "titre")
        verbose_name = "Formulaire d'audit"
        verbose_name_plural = "Formulaires d'audit"

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.section and self.type_audit and self.type_audit not in self.MULTI_FORMULAIRE_TYPES:
            qs = FormulaireAudit.objects.filter(section=self.section, type_audit=self.type_audit)
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            if qs.exists():
                raise ValidationError(
                    "Un formulaire existe déjà pour cette section et ce type d'audit. "
                    "Seuls les types Équipement et Poste autorisent plusieurs formulaires par section."
                )

    def __str__(self) -> str:
        return f"{self.titre} - {self.get_type_audit_display()}"


class LigneFormulaire(models.Model):
    """Ligne détaillée d'un formulaire d'audit."""

    formulaire = models.ForeignKey(
        FormulaireAudit,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lignes",
    )
    critere = models.ForeignKey(
        CritereEvaluation,
        on_delete=models.PROTECT,
        related_name="lignes_formulaire",
    )
    ordre = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("ordre", "id")
        unique_together = ("formulaire", "critere")
        verbose_name = "Ligne de formulaire"
        verbose_name_plural = "Lignes de formulaire"

    def save(self, *args, **kwargs):
        if not self.pk and self.ordre == 0:
            last = LigneFormulaire.objects.filter(formulaire=self.formulaire).aggregate(
                max_ordre=models.Max('ordre')
            )['max_ordre']
            self.ordre = (last or 0) + 1
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.formulaire} - Ligne {self.ordre}"


class Audit(models.Model):
    """Audit planifié/exécuté."""

    numero = models.CharField(max_length=30, unique=True, blank=True)
    formulaire = models.ForeignKey(
        FormulaireAudit,
        on_delete=models.PROTECT,
        related_name="audits",
    )
    statut = models.CharField(
        max_length=20,
        choices=AuditStatut.choices,
        default=AuditStatut.BROUILLON,
    )
    date_audit = models.DateField(default=date.today)
    commentaire = models.TextField(blank=True)
    cree_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="audits_crees",
    )
    cree_le = models.DateTimeField(auto_now_add=True)
    responsable_audit = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="audits_responsable",
        null=True,
        blank=True,
    )
    actif = models.BooleanField(default=True)

    class Meta:
        ordering = ("-date_audit", "-id")
        verbose_name = "Audit"
        verbose_name_plural = "Audits"

    def __str__(self) -> str:
        return f"{self.numero}"

    def save(self, *args, **kwargs):
        """Génère automatiquement le numéro d'audit au premier enregistrement."""
        if not self.numero:
            self.numero = self.generate_numero()
        super().save(*args, **kwargs)

    @classmethod
    def generate_numero(cls) -> str:
        """Construit un numéro format AUD-YYYYMMDD-XXXX."""
        today = timezone.localdate()
        prefix = f"AUD-{today.strftime('%Y%m%d')}-"
        last = cls.objects.filter(numero__startswith=prefix).aggregate(max_num=Max("numero"))["max_num"]
        if last:
            try:
                sequence = int(last.split("-")[-1]) + 1
            except (ValueError, IndexError):
                sequence = 1
        else:
            sequence = 1
        return f"{prefix}{sequence:04d}"


class ParticipantAudit(models.Model):
    """Participant interne/externe à un audit."""

    audit = models.ForeignKey(
        Audit,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="participants",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="participations_audit",
        null=True,
        blank=True,
    )
    nom_externe = models.CharField(max_length=255, blank=True, null=True)
    fonction = models.CharField(max_length=255)
    est_auditeur_externe = models.BooleanField(default=False)

    class Meta:
        ordering = ("audit", "id")
        verbose_name = "Participant audit"
        verbose_name_plural = "Participants audit"

    def __str__(self) -> str:
        return self.user.get_full_name() if self.user else self.nom_externe

    def clean(self):
        """Applique la règle XOR: user OU nom_externe, jamais les deux."""
        super().clean()
        has_user = bool(self.user_id)
        has_external = bool(self.nom_externe and self.nom_externe.strip())
        if has_user == has_external:
            raise ValidationError("Renseignez soit un utilisateur interne, soit un nom externe.")


class ReponseAudit(models.Model):
    """Réponse/cotation d'une ligne de formulaire pour un audit."""

    audit = models.ForeignKey(
        Audit,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reponses",
    )
    ligne = models.ForeignKey(
        LigneFormulaire,
        on_delete=models.PROTECT,
        related_name="reponses",
    )
    cotation = models.ForeignKey(
        BaremeCotation,
        on_delete=models.PROTECT,
        related_name="reponses",
        null=True,
        blank=True,
    )
    commentaire = models.TextField(blank=True)
    document = models.FileField(upload_to="audit/reponses/", null=True, blank=True)

    class Meta:
        ordering = ("id",)
        unique_together = ("audit", "ligne")
        verbose_name = "Réponse audit"
        verbose_name_plural = "Réponses audit"

    def __str__(self) -> str:
        return f"{self.audit} - {self.ligne}"


class ReponseImage(models.Model):
    reponse = models.ForeignKey(
        ReponseAudit,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="images",
    )
    image = models.ImageField(upload_to="audit/reponses/")

    def __str__(self):
        return f"Image pour {self.reponse}"


class ResultatAudit(models.Model):
    """Résultat agrégé d'un audit terminé."""

    audit = models.OneToOneField(
        Audit,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="resultat",
    )
    niveau_attendu = models.ForeignKey(
        "NiveauxAttendus",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="resultats",
    )
    points_forts = models.TextField(blank=True)
    risques = models.TextField(blank=True)
    opportunites = models.TextField(blank=True)
    points_sensibles = models.TextField(blank=True)
    cree_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Résultat d'audit"
        verbose_name_plural = "Résultats d'audit"

    def __str__(self) -> str:
        return f"Résultat - {self.audit.numero}"

    @property
    def nb_conformes(self) -> int:
        """Nombre de réponses conformes (code C)."""
        return self.audit.reponses.filter(cotation__code__iexact='C').count()

    @property
    def nb_partiels(self) -> int:
        """Nombre de réponses partiellement conformes (code PC)."""
        return self.audit.reponses.filter(cotation__code__iexact='PC').count()

    @property
    def nb_nc(self) -> int:
        """Nombre de réponses non conformes (code NC)."""
        return self.audit.reponses.filter(cotation__code__iexact='NC').count()

    @property
    def nb_na(self) -> int:
        """Nombre de réponses non applicables (code NA)."""
        return self.audit.reponses.filter(cotation__code__iexact='NA').count()

    @property
    def nb_total_repondus(self) -> int:
        """Nombre de réponses ayant une cotation."""
        return self.audit.reponses.filter(cotation__isnull=False).count()

    @property
    def niveau_prestation_pct(self) -> Decimal:
        """Somme des notes (hors NA) / nombre total de critères * 100."""
        total_criteria = self.audit.formulaire.lignes.count()
        if total_criteria == 0:
            return Decimal("0.00")
        reponses = self.audit.reponses.filter(
            cotation__isnull=False
        ).exclude(
            cotation__code__iexact='NA'
        ).select_related('cotation')
        total_note = sum(r.cotation.note for r in reponses)
        return (Decimal(str(total_note)) / Decimal(str(total_criteria)) * 100).quantize(Decimal("0.01"))



