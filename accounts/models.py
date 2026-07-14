"""Modèles de l'app accounts."""

import pytz
from django.contrib.auth.models import AbstractUser
from django.db import models

# ─────────────────────────────────────────────────────────────────────────────
# Societe
# ─────────────────────────────────────────────────────────────────────────────

class Societe(models.Model):
    nom = models.CharField(max_length=255, unique=True, verbose_name="Nom")

    class Meta:
        ordering = ("nom",)
        verbose_name = "Société"
        verbose_name_plural = "Sociétés"

    def __str__(self) -> str:
        return self.nom


# ─────────────────────────────────────────────────────────────────────────────
# Customer  (nouveau — clients/tiers issus de Sage)
# ─────────────────────────────────────────────────────────────────────────────

class Customer(models.Model):
    compte              = models.CharField(max_length=100, blank=True, null=True, verbose_name="Compte")
    type                = models.CharField(max_length=100, blank=True, null=True, verbose_name="Type")
    intitule            = models.CharField(max_length=100, blank=True, null=True, verbose_name="Intitulé")
    abrege              = models.CharField(max_length=100, blank=True, null=True, verbose_name="Abrégé")
    qualite             = models.CharField(max_length=100, blank=True, null=True, verbose_name="Qualité")
    compte_collectif    = models.CharField(max_length=100, blank=True, null=True, verbose_name="Compte Collectif")
    interlocuteur       = models.CharField(max_length=100, blank=True, null=True, verbose_name="Interlocuteur")
    commentaire         = models.CharField(max_length=100, blank=True, null=True, verbose_name="Commentaire")
    adresse             = models.CharField(max_length=100, blank=True, null=True, verbose_name="Adresse")
    complement          = models.CharField(max_length=800, blank=True, null=True, verbose_name="Complément")
    code_postal         = models.CharField(max_length=100, blank=True, null=True, verbose_name="Code Postal")
    ville               = models.CharField(max_length=100, blank=True, null=True, verbose_name="Ville")
    region              = models.CharField(max_length=100, blank=True, null=True, verbose_name="Région")
    pays                = models.CharField(max_length=100, blank=True, null=True, verbose_name="Pays")
    telephone           = models.CharField(max_length=100, blank=True, null=True, verbose_name="Téléphone")
    linkedin            = models.CharField(max_length=200, blank=True, null=True, verbose_name="LinkedIn")
    facebook            = models.CharField(max_length=200, blank=True, null=True, verbose_name="Facebook")
    email               = models.EmailField(max_length=100, blank=True, null=True, verbose_name="Email")
    site_web            = models.CharField(max_length=200, blank=True, null=True, verbose_name="Site Web")
    siret               = models.CharField(max_length=100, blank=True, null=True, verbose_name="SIRET")
    code_naf            = models.CharField(max_length=100, blank=True, null=True, verbose_name="Code NAF")
    code_vat            = models.CharField(max_length=100, blank=True, null=True, verbose_name="Code VAT")
    societe             = models.ForeignKey(
        Societe,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="customers",
        verbose_name="Société",
    )
    is_draft            = models.BooleanField(default=False, verbose_name="Brouillon")

    class Meta:
        verbose_name = "Customer"
        verbose_name_plural = "Customers"
        ordering = ("intitule",)

    def __str__(self) -> str:
        return self.intitule or self.compte or f"Customer #{self.pk}"


# ─────────────────────────────────────────────────────────────────────────────
# Section
# ─────────────────────────────────────────────────────────────────────────────

class Section(models.Model):
    Nom          = models.CharField(max_length=255, verbose_name="Code / Nom")
    pays         = models.CharField(max_length=100, blank=True, null=True, verbose_name="Pays")
    gouvernorat  = models.CharField(max_length=100, blank=True, null=True, verbose_name="Gouvernorat")
    societe      = models.ForeignKey(
        Societe,
        on_delete=models.CASCADE,
        related_name="sections",
        null=True,
        blank=True,
        verbose_name="Société",
    )
    latitude_max  = models.FloatField(blank=True, null=True, verbose_name="Latitude max")
    latitude_min  = models.FloatField(blank=True, null=True, verbose_name="Latitude min")
    longitude_max = models.FloatField(blank=True, null=True, verbose_name="Longitude max")
    longitude_min = models.FloatField(blank=True, null=True, verbose_name="Longitude min")

    class Meta:
        ordering = ("Nom",)
        verbose_name = "Section"
        verbose_name_plural = "Sections"

    def __str__(self) -> str:
        return self.Nom


# ─────────────────────────────────────────────────────────────────────────────
# Site
# ─────────────────────────────────────────────────────────────────────────────

class Site(models.Model):
    nom     = models.CharField(max_length=255)
    section = models.ForeignKey(
        Section,
        on_delete=models.CASCADE,
        related_name="sites",
    )

    class Meta:
        ordering = ("nom",)

    def __str__(self) -> str:
        return self.nom


# ─────────────────────────────────────────────────────────────────────────────
# User
# ─────────────────────────────────────────────────────────────────────────────

_TZ_CHOICES = [(tz, tz) for tz in pytz.all_timezones]


class User(AbstractUser):
    # ── Organisation ─────────────────────────────────────────────────────────
    section  = models.ForeignKey(
        Section,
        on_delete=models.PROTECT,
        related_name="utilisateurs",
        null=True,
        blank=True,
        verbose_name="Section principale",
    )
    societe  = models.ForeignKey(
        Societe,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="commerciaux",
        verbose_name="Société principale",
    )
    societes = models.ManyToManyField(
        Societe,
        blank=True,
        related_name="utilisateurs_admins",
        verbose_name="Sociétés (Admin multi-société)",
    )
    customer = models.ForeignKey(
        Customer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="utilisateurs",
        verbose_name="Customer associé",
    )

    # ── Coordonnées ──────────────────────────────────────────────────────────
    telephone  = models.CharField(max_length=20,  null=True, blank=True, verbose_name="Téléphone")
    pays       = models.CharField(max_length=100, null=True, blank=True, verbose_name="Pays")
    adresse    = models.CharField(max_length=300, null=True, blank=True, verbose_name="Adresse")
    vat_code   = models.CharField(max_length=100, null=True, blank=True, verbose_name="VATCode")

    # ── Métadonnées création ──────────────────────────────────────────────────
    admin_created = models.CharField(max_length=150, blank=True, null=True, verbose_name="Rattaché (admin)")
    rs_created    = models.CharField(max_length=150, blank=True, null=True, verbose_name="RS créateur")
    ce_created    = models.CharField(max_length=150, blank=True, null=True, verbose_name="CE créateur")

    # ── Coûts / sécurité ─────────────────────────────────────────────────────
    cout_horaire    = models.FloatField(blank=True, null=True, verbose_name="Coût horaire")
    failed_attempts = models.FloatField(blank=True, null=True, verbose_name="Tentatives échouées")

    # ── Localisation / fuseau ─────────────────────────────────────────────────
    timezone = models.CharField(
        max_length=50,
        choices=_TZ_CHOICES,
        default="Africa/Tunis",
        verbose_name="Fuseau horaire",
    )

    # ── Rôles principaux (ERP / Opérations) ──────────────────────────────────
    is_RS        = models.BooleanField(default=False, verbose_name="Responsable de site")
    is_RO        = models.BooleanField(default=False, verbose_name="Responsable opérationnel")
    is_CE        = models.BooleanField(default=False, verbose_name="Chef d'équipe")
    is_OP        = models.BooleanField(default=False, verbose_name="Opérateur")
    is_resp      = models.BooleanField(default=False, verbose_name="Responsable")
    is_divers    = models.BooleanField(default=False, verbose_name="Divers / site")
    is_assistante= models.BooleanField(default=False, verbose_name="Assistante")
    is_sais      = models.BooleanField(default=False, verbose_name="Saisie")
    is_interime  = models.BooleanField(default=False, verbose_name="Intérimaire")

    # ── Rôles audit ───────────────────────────────────────────────────────────
    is_auditeur  = models.BooleanField(default=False, verbose_name="Auditeur")

    # ── Rôles prospection commerciale ────────────────────────────────────────
    is_C  = models.BooleanField(default=False, verbose_name="Commercial")
    is_RC = models.BooleanField(default=False, verbose_name="Responsable commercial")
    is_CLT= models.BooleanField(default=False, verbose_name="Client")

    # ── Fix clash with auth.Group / auth.Permission ───────────────────────────
    groups = models.ManyToManyField(
        "auth.Group",
        blank=True,
        help_text="The groups this user belongs to.",
        related_name="accounts_user_set",
        related_query_name="accounts_user",
        verbose_name="groups",
    )
    user_permissions = models.ManyToManyField(
        "auth.Permission",
        blank=True,
        help_text="Specific permissions for this user.",
        related_name="accounts_user_set",
        related_query_name="accounts_user",
        verbose_name="user permissions",
    )

    class Meta(AbstractUser.Meta):
        verbose_name = "Utilisateur"
        verbose_name_plural = "Utilisateurs"

    def __str__(self) -> str:
        full_name = self.get_full_name().strip()
        return full_name or self.username

    # ── Helpers ───────────────────────────────────────────────────────────────
    @property
    def role_display(self) -> str:
        """Retourne le premier rôle significatif comme libellé lisible."""
        roles = []
        if self.is_superuser:   roles.append("Super Admin")
        if self.is_RS:          roles.append("RS")
        if self.is_RO:          roles.append("RO")
        if self.is_CE:          roles.append("Chef d'équipe")
        if self.is_OP:          roles.append("Opérateur")
        if self.is_auditeur:    roles.append("Auditeur")
        if self.is_RC:          roles.append("Resp. Commercial")
        if self.is_C:           roles.append("Commercial")
        if self.is_CLT:         roles.append("Client")
        if self.is_resp:        roles.append("Responsable")
        if self.is_assistante:  roles.append("Assistante")
        if self.is_sais:        roles.append("Saisie")
        if self.is_interime:    roles.append("Intérimaire")
        if self.is_divers:      roles.append("Divers")
        return ", ".join(roles) or "Aucun rôle"

