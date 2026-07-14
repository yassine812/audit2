"""Modèles de gestion documentaire (PROC-PM02-001 v5 indice 1)."""

import os

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.text import get_valid_filename


class ProcessusService(models.Model):
    """Référentiel des processus/services (PM02, PS01, PR04...)."""

    code = models.CharField(max_length=10, unique=True, verbose_name="Code")
    libelle = models.CharField(max_length=255, verbose_name="Libellé")
    description = models.TextField(blank=True, verbose_name="Description")
    actif = models.BooleanField(default=True, verbose_name="Actif")
    date_creation = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")
    date_modification = models.DateTimeField(auto_now=True, verbose_name="Date de modification")

    class Meta:
        ordering = ["code"]
        verbose_name = "Processus / Service"
        verbose_name_plural = "Processus / Services"

    def __str__(self) -> str:
        return f"{self.code} - {self.libelle}"


class DossierDocumentaire(models.Model):
    """Dossier hiérarchique de classement de la bibliothèque documentaire."""

    nom = models.CharField(max_length=120, verbose_name="Nom")
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        related_name="sous_dossiers",
        null=True,
        blank=True,
        verbose_name="Dossier parent",
    )
    description = models.CharField(max_length=255, blank=True, verbose_name="Description")
    couleur = models.CharField(
        max_length=7,
        default="#E4A11B",
        validators=[RegexValidator(r"^#[0-9A-Fa-f]{6}$", "Couleur hexadécimale invalide.")],
        verbose_name="Couleur",
    )
    acces_restreint = models.BooleanField(default=False, verbose_name="Limiter l'accès")
    roles_autorises = models.JSONField(default=list, blank=True, verbose_name="Rôles autorisés")
    actions_autorisees = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Actions autorisées",
    )
    societes_autorisees = models.ManyToManyField(
        "accounts.Societe", blank=True, related_name="dossiers_documentaires_autorises"
    )
    sections_autorisees = models.ManyToManyField(
        "accounts.Section", blank=True, related_name="dossiers_documentaires_autorises"
    )
    utilisateurs_autorises = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True, related_name="dossiers_documentaires_autorises"
    )
    cree_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="dossiers_documentaires_crees",
        null=True,
        blank=True,
        verbose_name="Créé par",
    )
    date_creation = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")
    date_modification = models.DateTimeField(auto_now=True, verbose_name="Date de modification")

    class Meta:
        ordering = ["nom"]
        verbose_name = "Dossier documentaire"
        verbose_name_plural = "Dossiers documentaires"
        constraints = [
            models.UniqueConstraint(
                fields=["parent", "nom"],
                name="gd_unique_dossier_nom_par_parent",
            ),
            models.UniqueConstraint(
                fields=["nom"],
                condition=Q(parent__isnull=True),
                name="gd_unique_dossier_nom_racine",
            ),
        ]

    def __str__(self) -> str:
        return self.nom

    def clean(self):
        super().clean()
        parent = self.parent
        visited = {self.pk} if self.pk else set()
        while parent:
            if parent.pk in visited:
                raise ValidationError({"parent": "Un dossier ne peut pas être son propre descendant."})
            visited.add(parent.pk)
            parent = parent.parent

    def get_ancestors(self):
        ancestors = []
        current = self.parent
        visited = set()
        while current and current.pk not in visited:
            visited.add(current.pk)
            ancestors.append(current)
            current = current.parent
        return list(reversed(ancestors))

    def chemin_stockage(self):
        """Chemin relatif reproduisant l'arborescence visible dans MEDIA_ROOT."""
        folders = self.get_ancestors() + [self]
        return "/".join(get_valid_filename(folder.nom) for folder in folders)

    def utilisateur_autorise(self, user, action="lire"):
        if not getattr(user, "is_authenticated", False):
            return False
        if getattr(user, "is_superuser", False):
            return True
        chain = self.get_ancestors() + [self]
        for folder in chain:
            if not folder.acces_restreint:
                continue
            regles = [
                regle for regle in folder.regles_acces.all()
                if action in regle.actions_autorisees
            ]
            if not regles:
                return False
            autorise = False
            for regle in regles:
                role_match = any(getattr(user, role, False) for role in regle.roles_autorises)
                user_match = regle.utilisateurs_autorises.filter(pk=user.pk).exists()
                societe_ids = set(regle.societes_autorisees.values_list("pk", flat=True))
                user_societe_ids = set(user.societes.values_list("pk", flat=True))
                if user.societe_id:
                    user_societe_ids.add(user.societe_id)
                societe_match = bool(societe_ids & user_societe_ids)
                section_match = bool(
                    user.section_id
                    and regle.sections_autorisees.filter(pk=user.section_id).exists()
                )
                if role_match or user_match or societe_match or section_match:
                    autorise = True
                    break
            if not autorise:
                return False
        return True


class RegleAccesDossier(models.Model):
    class Action(models.TextChoices):
        LIRE = "lire", "Lire"
        MODIFIER = "modifier", "Modifier"
        TELECHARGER = "telecharger", "Télécharger"

    dossier = models.ForeignKey(
        DossierDocumentaire,
        on_delete=models.CASCADE,
        related_name="regles_acces",
    )
    actions_autorisees = models.JSONField(default=list, blank=True)
    roles_autorises = models.JSONField(default=list, blank=True)
    societes_autorisees = models.ManyToManyField(
        "accounts.Societe", blank=True, related_name="regles_dossiers_autorisees"
    )
    sections_autorisees = models.ManyToManyField(
        "accounts.Section", blank=True, related_name="regles_dossiers_autorisees"
    )
    utilisateurs_autorises = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True, related_name="regles_dossiers_autorisees"
    )

    class Meta:
        ordering = ["pk"]

    def __str__(self):
        return f"{self.dossier} - {', '.join(self.actions_autorisees)}"


def fichier_bibliotheque_upload_to(instance, filename):
    filename = get_valid_filename(os.path.basename(filename))
    chemin = instance.dossier.chemin_stockage() if instance.dossier else ""
    return f"gestion_documentaire/bibliotheque/{chemin}/{filename}".replace("//", "/")


class FichierBibliotheque(models.Model):
    """Fichier simple rangé dans l'explorateur documentaire."""

    dossier = models.ForeignKey(
        DossierDocumentaire, on_delete=models.CASCADE, related_name="fichiers",
        null=True, blank=True, verbose_name="Dossier"
    )
    fichier = models.FileField(upload_to=fichier_bibliotheque_upload_to, max_length=500)
    nom = models.CharField(max_length=255, verbose_name="Nom")
    taille = models.PositiveBigIntegerField(default=0, verbose_name="Taille")
    type_mime = models.CharField(max_length=120, blank=True)
    ajoute_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="fichiers_documentaires_ajoutes",
    )
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["nom"]
        constraints = [
            models.UniqueConstraint(fields=["dossier", "nom"], name="gd_unique_fichier_nom_par_dossier"),
            models.UniqueConstraint(
                fields=["nom"], condition=Q(dossier__isnull=True),
                name="gd_unique_fichier_nom_racine",
            ),
        ]

    def __str__(self):
        return self.nom

    @property
    def extension(self):
        return os.path.splitext(self.nom)[1].lower()

    def delete(self, *args, **kwargs):
        storage, name = self.fichier.storage, self.fichier.name
        result = super().delete(*args, **kwargs)
        if name:
            storage.delete(name)
        return result


class Document(models.Model):
    """Document principal de référence (code documentaire unique)."""

    class TypeDocument(models.TextChoices):
        PROCEDURE = "procedure", "Procédure"
        MODE_OPERATOIRE = "mode_operatoire", "Mode opératoire"
        FORMULAIRE = "formulaire", "Formulaire"
        ENREGISTREMENT = "enregistrement", "Enregistrement"
        ASSOCIE = "associe", "Document associé"

    class Statut(models.TextChoices):
        BROUILLON = "brouillon", "Brouillon"
        EN_VERIFICATION = "en_verification", "En vérification"
        EN_APPROBATION = "en_approbation", "En approbation"
        APPLICABLE = "applicable", "Applicable"
        ARCHIVE = "archive", "Archivé"
        SUPPRIME = "supprime", "Supprimé"

    type_document = models.CharField(
        max_length=20,
        choices=TypeDocument.choices,
        verbose_name="Type de document",
    )
    processus_service = models.ForeignKey(
        ProcessusService,
        on_delete=models.PROTECT,
        related_name="documents",
        null=True,
        blank=True,
        verbose_name="Processus / Service",
    )
    dossier = models.ForeignKey(
        DossierDocumentaire,
        on_delete=models.SET_NULL,
        related_name="documents",
        null=True,
        blank=True,
        verbose_name="Dossier",
    )
    numero_ordre = models.PositiveIntegerField(verbose_name="Numéro d'ordre")
    code_documentaire = models.CharField(
        max_length=40,
        db_index=True,
        editable=False,
        verbose_name="Code documentaire",
    )
    titre = models.CharField(max_length=255, verbose_name="Titre")
    statut = models.CharField(
        max_length=20,
        choices=Statut.choices,
        default=Statut.BROUILLON,
        verbose_name="Statut",
    )

    # Champs métier minimaux - procédure
    objet = models.TextField(blank=True, verbose_name="Objet")
    domaine_application = models.TextField(blank=True, verbose_name="Domaine d'application")
    definitions = models.TextField(blank=True, verbose_name="Définitions")
    responsabilites = models.TextField(blank=True, verbose_name="Responsabilités")
    regles_etapes = models.TextField(blank=True, verbose_name="Règles / étapes")
    modalites_diffusion = models.TextField(blank=True, verbose_name="Modalités de diffusion")
    modalites_modification = models.TextField(blank=True, verbose_name="Modalités de modification")
    modalites_archivage = models.TextField(blank=True, verbose_name="Modalités d'archivage")

    # Champs métier minimaux - mode opératoire
    poste_service_activite = models.TextField(blank=True, verbose_name="Poste / service / activité")
    prerequis = models.TextField(blank=True, verbose_name="Prérequis")
    equipements_outils_logiciels = models.TextField(blank=True, verbose_name="Équipements / outils / logiciels")
    etapes_detaillees = models.TextField(blank=True, verbose_name="Étapes détaillées")
    points_controle = models.TextField(blank=True, verbose_name="Points de contrôle")
    criteres_acceptation = models.TextField(blank=True, verbose_name="Critères d'acceptation")
    consignes_securite = models.TextField(blank=True, verbose_name="Consignes de sécurité")
    enregistrements_a_completer = models.TextField(blank=True, verbose_name="Enregistrements à compléter")
    anomalies_actions = models.TextField(blank=True, verbose_name="Anomalies / actions à mener")

    # Champs métier minimaux - formulaire / enregistrement
    reference_documentaire = models.CharField(max_length=120, blank=True, verbose_name="Référence documentaire")
    schema_collecte = models.JSONField(default=dict, blank=True, verbose_name="Schéma de collecte")
    service_concerne = models.CharField(max_length=255, blank=True, verbose_name="Personne / service concerné")
    visas_validations = models.TextField(blank=True, verbose_name="Visas / validations")

    # Référence complémentaire facultative
    lien_externe = models.URLField(blank=True, verbose_name="Lien externe")

    # Archivage / retrait
    date_application = models.DateField(null=True, blank=True, verbose_name="Date d'application")
    date_retrait = models.DateField(null=True, blank=True, verbose_name="Date de retrait")
    motif_remplacement = models.TextField(blank=True, verbose_name="Motif de remplacement")

    est_supprime = models.BooleanField(default=False, verbose_name="Suppression logique")
    date_suppression = models.DateTimeField(null=True, blank=True, verbose_name="Date de suppression")

    cree_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="documents_crees",
        null=True,
        blank=True,
        verbose_name="Créé par",
    )
    date_creation = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")
    date_modification = models.DateTimeField(auto_now=True, verbose_name="Date de modification")

    class Meta:
        ordering = ["code_documentaire", "-date_modification"]
        verbose_name = "Document"
        verbose_name_plural = "Documents"
        constraints = [
            models.CheckConstraint(
                check=Q(numero_ordre__gte=1),
                name="gd_document_numero_ordre_gte_1",
            ),
            models.UniqueConstraint(
                fields=["code_documentaire"],
                condition=Q(statut="applicable", est_supprime=False),
                name="gd_unique_document_applicable_par_code",
            ),
            models.UniqueConstraint(
                fields=["code_documentaire", "statut"],
                condition=Q(statut="applicable", est_supprime=False),
                name="gd_unique_codedoc_statut_applicable",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.code_documentaire} {self.titre}".strip()

    @property
    def code_prefixe(self) -> str:
        if self.type_document == self.TypeDocument.PROCEDURE:
            return "PROC"
        if self.type_document == self.TypeDocument.MODE_OPERATOIRE:
            return "MO"
        if self.type_document in {self.TypeDocument.FORMULAIRE, self.TypeDocument.ENREGISTREMENT}:
            return "DOC"
        return "ASSOC"

    @property
    def nom_complet(self) -> str:
        date_ref = self.date_modification.date() if self.date_modification else timezone.localdate()
        return f"{self.code_documentaire} {self.titre} {date_ref.isoformat()}".strip()

    def generer_code_documentaire(self) -> str:
        numero = f"{self.numero_ordre:03d}"
        if self.type_document in {self.TypeDocument.PROCEDURE, self.TypeDocument.MODE_OPERATOIRE}:
            if not self.processus_service_id:
                raise ValidationError("Le processus/service est obligatoire pour ce type de document.")
            return f"{self.code_prefixe}-{self.processus_service.code}-{numero}"
        if self.type_document in {self.TypeDocument.FORMULAIRE, self.TypeDocument.ENREGISTREMENT}:
            return f"DOC-{numero}"
        if self.processus_service_id:
            return f"ASSOC-{self.processus_service.code}-{numero}"
        return f"ASSOC-{numero}"

    def can_transition_to(self, nouveau_statut: str) -> bool:
        transitions = {
            self.Statut.BROUILLON: {self.Statut.EN_VERIFICATION},
            self.Statut.EN_VERIFICATION: {self.Statut.EN_APPROBATION},
            self.Statut.EN_APPROBATION: {self.Statut.APPLICABLE},
            self.Statut.APPLICABLE: {self.Statut.ARCHIVE, self.Statut.SUPPRIME},
            self.Statut.ARCHIVE: set(),
            self.Statut.SUPPRIME: set(),
        }
        return nouveau_statut in transitions.get(self.statut, set())

    def transitionner_statut(self, nouveau_statut: str, utilisateur=None, commentaire: str = ""):
        if not self.can_transition_to(nouveau_statut):
            raise ValidationError(
                f"Transition interdite: {self.statut} -> {nouveau_statut}."
            )

        ancien_statut = self.statut
        self.statut = nouveau_statut
        today = timezone.localdate()

        if nouveau_statut == self.Statut.APPLICABLE:
            self.date_application = today
            self.date_retrait = None
        elif nouveau_statut in {self.Statut.ARCHIVE, self.Statut.SUPPRIME}:
            self.date_retrait = today
            if nouveau_statut == self.Statut.SUPPRIME:
                self.est_supprime = True
                self.date_suppression = timezone.now()

        self.save(update_fields=[
            "statut",
            "date_application",
            "date_retrait",
            "est_supprime",
            "date_suppression",
            "date_modification",
        ])

        if utilisateur is not None:
            ValidationDocument.objects.create(
                document=self,
                type_action=ValidationDocument.TypeAction.TRANSITION_STATUT,
                utilisateur=utilisateur,
                commentaire=commentaire,
                ancien_statut=ancien_statut,
                nouveau_statut=nouveau_statut,
            )

    def clean(self):
        super().clean()

        if self.type_document in {self.TypeDocument.PROCEDURE, self.TypeDocument.MODE_OPERATOIRE}:
            if not self.processus_service_id:
                raise ValidationError({"processus_service": "Ce champ est obligatoire pour PROC/MO."})

        if self.type_document in {self.TypeDocument.FORMULAIRE, self.TypeDocument.ENREGISTREMENT} and self.processus_service_id:
            raise ValidationError({"processus_service": "Les DOC (Formulaire/Enregistrement) utilisent le format DOC-NNN."})

        if self.statut == self.Statut.SUPPRIME and not self.est_supprime:
            raise ValidationError({"est_supprime": "Le drapeau de suppression logique est obligatoire."})

    def save(self, *args, **kwargs):
        self.code_documentaire = self.generer_code_documentaire()
        self.full_clean()
        super().save(*args, **kwargs)


class VersionDocument(models.Model):
    """Version historisée d'un document (version majeure + indice mineur)."""

    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name="versions",
        verbose_name="Document",
    )
    version = models.PositiveIntegerField(default=1, verbose_name="Version")
    indice = models.PositiveIntegerField(default=0, verbose_name="Indice")
    statut = models.CharField(
        max_length=20,
        choices=Document.Statut.choices,
        default=Document.Statut.BROUILLON,
        verbose_name="Statut",
    )

    fichier_reference = models.FileField(
        upload_to="gestion_documentaire/references/",
        blank=True,
        null=True,
        verbose_name="Fichier de référence (PDF)",
    )
    fichier_editable = models.FileField(
        upload_to="gestion_documentaire/editables/",
        blank=True,
        null=True,
        verbose_name="Fichier modifiable",
    )
    redacteur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="versions_documents_redigees",
        verbose_name="Rédacteur",
    )
    resume_changements = models.TextField(blank=True, verbose_name="Résumé des changements")
    copie_non_maitrisee = models.BooleanField(default=True, verbose_name="Copie non maîtrisée")

    est_supprime = models.BooleanField(default=False, verbose_name="Suppression logique")
    date_creation = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")
    date_modification = models.DateTimeField(auto_now=True, verbose_name="Date de modification")
    date_application = models.DateField(null=True, blank=True, verbose_name="Date d'application")
    date_retrait = models.DateField(null=True, blank=True, verbose_name="Date de retrait")

    class Meta:
        ordering = ["document", "-version", "-indice"]
        verbose_name = "Version document"
        verbose_name_plural = "Versions documents"
        constraints = [
            models.CheckConstraint(
                check=Q(version__gte=1),
                name="gd_version_document_version_gte_1",
            ),
            models.CheckConstraint(
                check=Q(indice__gte=0),
                name="gd_version_document_indice_gte_0",
            ),
            models.UniqueConstraint(
                fields=["document", "version", "indice"],
                name="gd_unique_version_indice_par_document",
            ),
            models.UniqueConstraint(
                fields=["document"],
                condition=Q(statut="applicable", est_supprime=False),
                name="gd_unique_version_applicable_par_document",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.document.code_documentaire} v{self.version}.{self.indice}"

    @property
    def code_complet(self) -> str:
        return self.document.code_documentaire

    def can_transition_to(self, nouveau_statut: str) -> bool:
        transitions = {
            Document.Statut.BROUILLON: {Document.Statut.EN_VERIFICATION},
            Document.Statut.EN_VERIFICATION: {Document.Statut.EN_APPROBATION},
            Document.Statut.EN_APPROBATION: {Document.Statut.APPLICABLE},
            Document.Statut.APPLICABLE: {Document.Statut.ARCHIVE, Document.Statut.SUPPRIME},
            Document.Statut.ARCHIVE: set(),
            Document.Statut.SUPPRIME: set(),
        }
        return nouveau_statut in transitions.get(self.statut, set())

    def transitionner_statut(self, nouveau_statut: str, utilisateur=None, commentaire: str = ""):
        if not self.can_transition_to(nouveau_statut):
            raise ValidationError(f"Transition interdite: {self.statut} -> {nouveau_statut}.")

        ancien_statut = self.statut
        self.statut = nouveau_statut
        today = timezone.localdate()

        if nouveau_statut == Document.Statut.APPLICABLE:
            self.date_application = today
            self.date_retrait = None
            # Dès qu'une nouvelle version est applicable, les anciennes passent en archive.
            self.document.versions.exclude(pk=self.pk).filter(statut=Document.Statut.APPLICABLE).update(
                statut=Document.Statut.ARCHIVE,
                date_retrait=today,
            )
        elif nouveau_statut in {Document.Statut.ARCHIVE, Document.Statut.SUPPRIME}:
            self.date_retrait = today
            if nouveau_statut == Document.Statut.SUPPRIME:
                self.est_supprime = True

        self.save(update_fields=[
            "statut",
            "date_application",
            "date_retrait",
            "est_supprime",
            "date_modification",
        ])

        # Synchronisation statut document principal.
        self.document.statut = nouveau_statut
        if nouveau_statut == Document.Statut.APPLICABLE:
            self.document.date_application = today
            self.document.date_retrait = None
        elif nouveau_statut in {Document.Statut.ARCHIVE, Document.Statut.SUPPRIME}:
            self.document.date_retrait = today
            if nouveau_statut == Document.Statut.SUPPRIME:
                self.document.est_supprime = True
                self.document.date_suppression = timezone.now()
        self.document.save(update_fields=[
            "statut",
            "date_application",
            "date_retrait",
            "est_supprime",
            "date_suppression",
            "date_modification",
        ])

        if utilisateur is not None:
            ValidationDocument.objects.create(
                document=self.document,
                version_document=self,
                type_action=ValidationDocument.TypeAction.TRANSITION_STATUT,
                utilisateur=utilisateur,
                commentaire=commentaire,
                ancien_statut=ancien_statut,
                nouveau_statut=nouveau_statut,
            )


class ValidationDocument(models.Model):
    """Audit trail horodaté des actions de vérification/approbation/diffusion."""

    class TypeAction(models.TextChoices):
        IDENTIFICATION_BESOIN = "identification_besoin", "Identification du besoin"
        VERIFICATION_EQUIVALENCE = "verification_equivalence", "Vérification document équivalent"
        DETERMINATION_TYPE = "determination_type", "Détermination du type"
        REDACTION = "redaction", "Rédaction"
        VERIFICATION_CONTENU = "verification_contenu", "Vérification du contenu"
        APPROBATION = "approbation", "Approbation"
        CODIFICATION = "codification", "Codification"
        DIFFUSION = "diffusion", "Diffusion"
        ARCHIVAGE = "archivage", "Archivage"
        SUPPRESSION = "suppression", "Suppression"
        TRANSITION_STATUT = "transition_statut", "Transition de statut"

    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name="validations",
        verbose_name="Document",
    )
    version_document = models.ForeignKey(
        VersionDocument,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="validations",
        verbose_name="Version document",
    )
    type_action = models.CharField(
        max_length=40,
        choices=TypeAction.choices,
        verbose_name="Type d'action",
    )
    utilisateur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="actions_validation_document",
        verbose_name="Utilisateur",
    )
    commentaire = models.TextField(blank=True, verbose_name="Commentaire")
    ancien_statut = models.CharField(
        max_length=20,
        choices=Document.Statut.choices,
        blank=True,
        verbose_name="Ancien statut",
    )
    nouveau_statut = models.CharField(
        max_length=20,
        choices=Document.Statut.choices,
        blank=True,
        verbose_name="Nouveau statut",
    )
    donnees_action = models.JSONField(default=dict, blank=True, verbose_name="Données d'action")
    date_action = models.DateTimeField(auto_now_add=True, verbose_name="Date d'action")

    class Meta:
        ordering = ["-date_action"]
        verbose_name = "Validation document"
        verbose_name_plural = "Validations documents"

    def __str__(self) -> str:
        return f"{self.document.code_documentaire} - {self.get_type_action_display()} ({self.date_action:%Y-%m-%d %H:%M})"
