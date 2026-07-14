"""Modèles du module Achats."""

from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q, Sum
from django.utils import timezone

from accounts.models import Section


class Fournisseur(models.Model):
    """Fournisseur potentiel ou validé pour les achats."""

    STATUT_CHOICES = [
        ("A", "A"),
        ("B", "B"),
        ("C", "C"),
        ("D", "D"),
    ]

    nom = models.CharField(max_length=255, verbose_name="Nom")
    adresse = models.CharField(max_length=500, verbose_name="Adresse")
    reference_fournisseur = models.CharField(max_length=100, blank=True, verbose_name="Référence fournisseur")
    contact_nom = models.CharField(max_length=255, blank=True, verbose_name="Nom du contact")
    contact_mail = models.EmailField(blank=True, verbose_name="E-mail du contact")
    contact_tel = models.CharField(max_length=30, blank=True, verbose_name="Téléphone du contact")
    statut_evaluation = models.CharField(
        max_length=1,
        choices=STATUT_CHOICES,
        null=True,
        blank=True,
        verbose_name="Statut d'évaluation",
    )
    pris_en_compte = models.BooleanField(default=True, verbose_name="Pris en compte")
    date_creation = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")

    class Meta:
        ordering = ["nom"]
        verbose_name = "Fournisseur"
        verbose_name_plural = "Fournisseurs"

    def __str__(self) -> str:
        return self.nom


class ArticleCatalogue(models.Model):
    """Article référencé dans le catalogue achats."""

    TYPE_CHOICES = [
        ("materiel", "Matériel"),
        ("immateriel", "Immatériel"),
    ]
    CATEGORIE_CHOICES = [
        ("fourniture_bureau", "Fourniture bureau"),
        ("outillage", "Outillage"),
        ("epi", "EPI"),
        ("autre", "Autre"),
    ]

    reference = models.CharField(max_length=100, unique=True, verbose_name="Référence")
    designation = models.CharField(max_length=255, verbose_name="Désignation")
    description = models.TextField(blank=True, verbose_name="Description")
    stock_disponible = models.PositiveIntegerField(default=0, verbose_name="Stock disponible")
    prix_reference_ht = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Prix de reference HT",
    )
    photo = models.ImageField(upload_to="catalogue/", blank=True, null=True, verbose_name="Photo")
    type_article = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        verbose_name="Type d'article",
    )
    categorie = models.CharField(
        max_length=30,
        choices=CATEGORIE_CHOICES,
        verbose_name="Catégorie",
    )
    actif = models.BooleanField(default=True, verbose_name="Actif")
    date_creation = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")
    cree_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="articles_catalogue",
        verbose_name="Créé par",
    )

    class Meta:
        ordering = ["designation"]
        verbose_name = "Article du catalogue"
        verbose_name_plural = "Articles du catalogue"

    def __str__(self) -> str:
        return f"{self.reference} - {self.designation}"


class OffreFournisseur(models.Model):
    """Offre tarifaire d'un fournisseur pour un article."""

    article = models.ForeignKey(
        ArticleCatalogue,
        on_delete=models.CASCADE,
        related_name="offres",
        verbose_name="Article",
    )
    fournisseur = models.ForeignKey(
        Fournisseur,
        on_delete=models.CASCADE,
        related_name="offres",
        verbose_name="Fournisseur",
    )
    tarif_propose = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Tarif proposé",
    )
    reference_chez_fournisseur = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Référence chez le fournisseur",
    )
    date_maj = models.DateTimeField(auto_now=True, verbose_name="Date de mise à jour")

    class Meta:
        unique_together = ("article", "fournisseur")
        verbose_name = "Offre fournisseur"
        verbose_name_plural = "Offres fournisseurs"

    def __str__(self) -> str:
        return f"{self.article.designation} / {self.fournisseur.nom}"


class DemandeAchat(models.Model):
    """Demande d'achat saisie par un utilisateur métier."""

    STATUT_BROUILLON = "brouillon"
    STATUT_SOUMISE = "soumise"
    STATUT_EN_COURS_DEVIS = "en_cours_devis"
    STATUT_VALIDATION_N1 = "en_validation_n1"
    STATUT_VALIDATION_N2 = "en_validation_n2"
    STATUT_VALIDEE = "validee"
    STATUT_REFUSEE = "refusee"
    STATUT_COMMANDEE = "commandee"
    STATUT_RECEPTIONNEE = "receptionnee"
    STATUT_CLOTUREE = "cloturee"

    STATUT_CHOICES = [
        (STATUT_BROUILLON, "Brouillon"),
        (STATUT_SOUMISE, "Soumise"),
        (STATUT_EN_COURS_DEVIS, "En cours de devis"),
        (STATUT_VALIDATION_N1, "Validation N1"),
        (STATUT_VALIDATION_N2, "Validation N2"),
        (STATUT_VALIDEE, "Validée"),
        (STATUT_REFUSEE, "Refusée"),
        (STATUT_COMMANDEE, "Commandée"),
        (STATUT_RECEPTIONNEE, "Réceptionnée"),
        (STATUT_CLOTUREE, "Clôturée"),
    ]

    demandeur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="demandes_achat",
        verbose_name="Demandeur",
    )
    date_emission = models.DateTimeField(auto_now_add=True, verbose_name="Date d'émission")
    delai_souhaite = models.DateField(null=True, blank=True, verbose_name="Délai souhaité")
    adresse_livraison = models.CharField(max_length=255, verbose_name="Adresse de livraison")
    section_analytique = models.ForeignKey(
        Section,
        on_delete=models.PROTECT,
        related_name="demandes_achat",
        verbose_name="Section analytique",
    )
    categorie = models.CharField(
        max_length=30,
        choices=ArticleCatalogue.CATEGORIE_CHOICES,
        verbose_name="Catégorie",
    )
    est_demande_de_prix = models.BooleanField(
        default=False,
        help_text="Demande de prix uniquement, pour étude/devis/consultation",
        verbose_name="Demande de prix uniquement",
    )
    statut = models.CharField(
        max_length=30,
        choices=STATUT_CHOICES,
        default=STATUT_BROUILLON,
        verbose_name="Statut",
    )
    total_commande_ht = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Total commande HT",
    )
    date_creation = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")
    date_modification = models.DateTimeField(auto_now=True, verbose_name="Date de modification")
    numero = models.CharField(max_length=20, unique=True, blank=True, verbose_name="Numéro")

    class Meta:
        ordering = ["-date_creation"]
        verbose_name = "Demande d'achat"
        verbose_name_plural = "Demandes d'achat"

    def __str__(self) -> str:
        return self.numero or f"Demande d'achat #{self.pk}"

    def save(self, *args, **kwargs):
        """Génère automatiquement le numéro de demande au premier enregistrement."""
        if not self.numero:
            year = timezone.now().year
            prefix = f"DA-{year}-"
            last_request = (
                DemandeAchat.objects.filter(numero__startswith=prefix)
                .order_by("-numero")
                .first()
            )
            last_index = 0
            if last_request and last_request.numero:
                try:
                    last_index = int(last_request.numero.split("-")[-1])
                except (TypeError, ValueError):
                    last_index = 0
            self.numero = f"{prefix}{last_index + 1:04d}"

        super().save(*args, **kwargs)

    def recalculer_total(self):
        """Recalcule le total HT à partir des lignes."""
        total = self.lignes.aggregate(
            montant=Sum("prix_total", default=Decimal("0.00")),
        )["montant"]
        self.total_commande_ht = total or Decimal("0.00")
        self.save(update_fields=["total_commande_ht", "date_modification"])

    def lancer_circuit_validation(self):
        """Délègue le lancement du circuit de validation au service métier."""
        from .services import lancer_circuit_validation

        return lancer_circuit_validation(self)

    def traiter_validation(self, etape, decision, commentaire, user):
        """Délègue le traitement d'une décision de validation au service métier."""
        from .services import traiter_validation_demande

        return traiter_validation_demande(
            demande=self,
            etape=etape,
            decision=decision,
            commentaire=commentaire,
            user=user,
        )

    @classmethod
    def mes_demandes_a_valider(cls, user):
        """Retourne les demandes ayant une étape de validation en attente pour l'utilisateur."""
        from .services import mes_demandes_a_valider

        return mes_demandes_a_valider(user)

    @property
    def is_conforme(self):
        """Retourne la conformité de la réception si elle existe."""
        try:
            return self.reception.conforme_quantite_etat
        except ReceptionMarchandise.DoesNotExist:
            return None


class LigneDemandeAchat(models.Model):
    """Ligne d'article ou de besoin d'une demande d'achat."""

    demande = models.ForeignKey(
        DemandeAchat,
        on_delete=models.CASCADE,
        related_name="lignes",
        verbose_name="Demande",
    )
    article_catalogue = models.ForeignKey(
        ArticleCatalogue,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lignes_demande",
        verbose_name="Article du catalogue",
    )
    hors_catalogue = models.BooleanField(default=False, verbose_name="Hors catalogue")
    nouvelle_designation = models.CharField(max_length=255, blank=True, verbose_name="Nouvelle désignation")
    nouvelle_description = models.TextField(blank=True, verbose_name="Nouvelle description")
    nouvelle_photo = models.ImageField(
        upload_to="nouveaux_articles/",
        blank=True,
        null=True,
        verbose_name="Photo du nouvel article",
    )
    quantite = models.PositiveIntegerField(verbose_name="Quantité")
    qte_stock = models.PositiveIntegerField(default=0, verbose_name="Qté stock")
    prix_unitaire = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Renseigné par le service achat",
        verbose_name="Prix unitaire",
    )
    prix_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Prix total",
    )
    reference_fournisseur = models.CharField(max_length=100, blank=True, verbose_name="Référence fournisseur")
    fournisseur_retenu = models.ForeignKey(
        Fournisseur,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lignes_retenues",
        verbose_name="Fournisseur retenu",
    )
    commentaire = models.TextField(blank=True, verbose_name="Commentaire")
    engin_concerne = models.CharField(max_length=255, blank=True, verbose_name="Engin (si concerné)")

    class Meta:
        verbose_name = "Ligne de demande d'achat"
        verbose_name_plural = "Lignes de demande d'achat"

    def __str__(self) -> str:
        if self.article_catalogue:
            return f"{self.article_catalogue.designation} x {self.quantite}"
        return f"{self.nouvelle_designation or 'Article hors catalogue'} x {self.quantite}"

    def clean(self):
        """Vérifie que la ligne vise soit le catalogue, soit un nouvel article."""
        super().clean()

        has_catalogue = bool(self.article_catalogue)
        has_new_article = bool(self.hors_catalogue and self.nouvelle_designation.strip())

        if has_catalogue and self.hors_catalogue:
            raise ValidationError(
                "Sélectionnez un article du catalogue ou renseignez un article hors catalogue, pas les deux."
            )

        if not has_catalogue and not has_new_article:
            raise ValidationError(
                "Vous devez choisir un article du catalogue ou renseigner une désignation hors catalogue."
            )

        if has_catalogue and self.nouvelle_designation.strip():
            raise ValidationError(
                "La désignation hors catalogue doit rester vide lorsqu'un article catalogue est choisi."
            )

    def save(self, *args, **kwargs):
        """Calcule le prix total si le prix unitaire est renseigné."""
        if self.prix_unitaire is not None:
            self.prix_total = Decimal(self.quantite) * self.prix_unitaire
        else:
            self.prix_total = None
        super().save(*args, **kwargs)


class Devis(models.Model):
    """Devis saisi par l'équipe achat pour une ligne de demande."""

    ligne = models.ForeignKey(
        LigneDemandeAchat,
        on_delete=models.CASCADE,
        related_name="devis",
        verbose_name="Ligne",
    )
    fournisseur = models.ForeignKey(
        Fournisseur,
        on_delete=models.PROTECT,
        related_name="devis_achats",
        verbose_name="Fournisseur",
    )
    prix_propose = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Prix proposé",
    )
    reference_fournisseur = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Référence fournisseur",
    )
    document = models.FileField(
        upload_to="devis/",
        blank=True,
        null=True,
        verbose_name="Document",
    )
    delai_livraison_propose = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Délai de livraison proposé",
    )
    est_choisi = models.BooleanField(default=False, verbose_name="Devis retenu")
    saisi_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="devis_saisis",
        verbose_name="Saisi par",
    )
    date_saisie = models.DateTimeField(auto_now_add=True, verbose_name="Date de saisie")

    class Meta:
        ordering = ["ligne_id", "date_saisie", "pk"]
        verbose_name = "Devis"
        verbose_name_plural = "Devis"
        constraints = [
            models.UniqueConstraint(
                fields=["ligne"],
                condition=Q(est_choisi=True),
                name="unique_devis_choisi_par_ligne",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.fournisseur} - {self.prix_propose}"

    def clean(self):
        """Vérifie qu'un seul devis est retenu par ligne."""
        super().clean()

        if not self.est_choisi or not self.ligne_id:
            return

        deja_choisi = Devis.objects.filter(ligne_id=self.ligne_id, est_choisi=True)
        if self.pk:
            deja_choisi = deja_choisi.exclude(pk=self.pk)

        if deja_choisi.exists():
            raise ValidationError("Un seul devis peut être retenu par ligne de demande.")


class EtapeValidation(models.Model):
    """Étape de validation hiérarchique d'une demande d'achat."""

    NIVEAU_DEMANDEUR = 1
    NIVEAU_DIRECTEUR_POLE = 2
    NIVEAU_DIRECTEUR_GENERAL = 3

    STATUT_EN_ATTENTE = "en_attente"
    STATUT_APPROUVE = "approuve"
    STATUT_REFUSE = "refuse"
    STATUT_MODIFICATION_DEMANDEE = "modification_demandee"

    NIVEAU_CHOICES = [
        (NIVEAU_DEMANDEUR, "Demandeur"),
        (NIVEAU_DIRECTEUR_POLE, "Directeur de Pôle"),
        (NIVEAU_DIRECTEUR_GENERAL, "Directeur Général"),
    ]
    STATUT_CHOICES = [
        (STATUT_EN_ATTENTE, "En attente"),
        (STATUT_APPROUVE, "Approuvé"),
        (STATUT_REFUSE, "Refusé"),
        (STATUT_MODIFICATION_DEMANDEE, "Modification demandée"),
    ]

    demande = models.ForeignKey(
        DemandeAchat,
        on_delete=models.CASCADE,
        related_name="etapes",
        verbose_name="Demande",
    )
    niveau = models.PositiveSmallIntegerField(choices=NIVEAU_CHOICES, verbose_name="Niveau")
    validateur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="etapes_validation_achat",
        verbose_name="Validateur",
    )
    statut = models.CharField(
        max_length=30,
        choices=STATUT_CHOICES,
        default=STATUT_EN_ATTENTE,
        verbose_name="Statut",
    )
    commentaire = models.TextField(blank=True, verbose_name="Commentaire")
    date_creation = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")
    date_action = models.DateTimeField(null=True, blank=True, verbose_name="Date d'action")

    class Meta:
        ordering = ["demande", "niveau"]
        verbose_name = "Étape de validation"
        verbose_name_plural = "Étapes de validation"

    def __str__(self) -> str:
        return f"{self.demande} - N{self.niveau}"


class ConfigurationValidationSection(models.Model):
    """Paramétrage de la chaîne de validation achats par section."""

    section = models.OneToOneField(
        Section,
        on_delete=models.CASCADE,
        related_name="configuration_validation_achat",
        verbose_name="Section",
    )
    validateur_n1 = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="validations_achat_n1_configurees",
        verbose_name="Validateur N1",
    )
    validateur_n2 = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="validations_achat_n2_configurees",
        verbose_name="Validateur N2",
    )
    date_creation = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")
    date_modification = models.DateTimeField(auto_now=True, verbose_name="Date de modification")

    class Meta:
        ordering = ["section__Nom"]
        verbose_name = "Configuration validation section"
        verbose_name_plural = "Configurations validation sections"

    def __str__(self) -> str:
        return f"{self.section} - N1/N2"

    def clean(self):
        super().clean()
        if self.validateur_n1_id and self.validateur_n1_id == self.validateur_n2_id:
            raise ValidationError("Les validateurs N1 et N2 doivent être différents.")


class ReceptionMarchandise(models.Model):
    """Confirmation de réception et évaluation qualité selon la grille P03."""

    NOTE_1 = 1
    NOTE_2 = 2
    NOTE_3 = 3
    NOTE_4 = 4

    NOTE_A = "A"
    NOTE_B = "B"
    NOTE_C = "C"
    NOTE_D = "D"

    NOTE_CHOICES = [
        (NOTE_1, "1"),
        (NOTE_2, "2"),
        (NOTE_3, "3"),
        (NOTE_4, "4"),
    ]
    NOTE_FOURNISSEUR_CHOICES = [
        (NOTE_A, "A"),
        (NOTE_B, "B"),
        (NOTE_C, "C"),
        (NOTE_D, "D"),
    ]

    demande = models.OneToOneField(
        DemandeAchat,
        on_delete=models.CASCADE,
        related_name="reception",
        verbose_name="Demande",
    )
    date_reception = models.DateField(auto_now_add=True, verbose_name="Date de réception")
    receptionne_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="receptions_marchandise",
        verbose_name="Réceptionné par",
    )
    conforme_quantite_etat = models.BooleanField(
        default=True,
        verbose_name="Conforme en quantité et état",
    )
    c1_reponse_demande_prix = models.PositiveSmallIntegerField(
        choices=NOTE_CHOICES,
        verbose_name="C1 Réponse aux demandes de prix",
    )
    c2_livraisons = models.PositiveSmallIntegerField(
        choices=NOTE_CHOICES,
        verbose_name="C2 Livraisons",
    )
    c3_disponibilite = models.PositiveSmallIntegerField(
        choices=NOTE_CHOICES,
        verbose_name="C3 Disponibilité",
    )
    c4_qualite_utilisation = models.PositiveSmallIntegerField(
        choices=NOTE_CHOICES,
        verbose_name="C4 Qualité à l'utilisation",
    )
    c5_qualite_reception = models.PositiveSmallIntegerField(
        choices=NOTE_CHOICES,
        verbose_name="C5 Qualité à la réception",
    )
    c6_information_produit = models.PositiveSmallIntegerField(
        choices=NOTE_CHOICES,
        verbose_name="C6 Information sur le produit",
    )
    c7_reglement_litiges = models.PositiveSmallIntegerField(
        choices=NOTE_CHOICES,
        verbose_name="C7 Règlement des litiges",
    )
    c8_couts = models.PositiveSmallIntegerField(
        choices=NOTE_CHOICES,
        verbose_name="C8 Coûts",
    )
    c9_communication = models.PositiveSmallIntegerField(
        choices=NOTE_CHOICES,
        verbose_name="C9 Communication",
    )
    score_calcule = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        editable=False,
        verbose_name="Score calculé",
    )
    note_calculee = models.CharField(
        max_length=1,
        choices=NOTE_FOURNISSEUR_CHOICES,
        editable=False,
        verbose_name="Note calculée",
    )
    date_creation = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")

    class Meta:
        ordering = ["-date_creation"]
        verbose_name = "Réception marchandise"
        verbose_name_plural = "Réceptions marchandise"

    def __str__(self) -> str:
        return f"Réception {self.demande}"

    def calculer_score(self):
        """Calcule le score de conformité selon la formule stricte P03."""
        decimal_huit = Decimal("8")
        decimal_dix = Decimal("10")
        decimal_quatre = Decimal("4")
        decimal_deux = Decimal("2")
        decimal_sept = Decimal("7")
        decimal_cent = Decimal("100")

        bloc_delais = (
            (Decimal(self.c1_reponse_demande_prix + self.c2_livraisons) / decimal_huit)
            * decimal_deux
        )
        bloc_produit = (
            (
                Decimal(
                    self.c3_disponibilite
                    + self.c4_qualite_utilisation
                    + self.c5_qualite_reception
                    + self.c6_information_produit
                    + self.c7_reglement_litiges
                )
                / decimal_dix
            )
            * decimal_deux
        )
        bloc_couts = (Decimal(self.c8_couts) / decimal_quatre) * decimal_deux
        bloc_relations = Decimal(self.c9_communication) / decimal_quatre

        score = (
            ((bloc_delais + bloc_produit + bloc_couts + bloc_relations) / decimal_sept)
            * decimal_cent
        )
        return score.quantize(Decimal("0.01"))

    def calculer_note(self):
        """Retourne la note fournisseur à partir du score calculé."""
        score = self.calculer_score()
        if score < Decimal("60"):
            return self.NOTE_D
        if score < Decimal("75"):
            return self.NOTE_C
        if score < Decimal("90"):
            return self.NOTE_B
        return self.NOTE_A

    def save(self, *args, **kwargs):
        """Met à jour automatiquement le score et la note avant sauvegarde."""
        self.score_calcule = self.calculer_score()
        self.note_calculee = self.calculer_note()
        super().save(*args, **kwargs)


class Dysfonctionnement(models.Model):
    """Signalement d'un dysfonctionnement lié à une demande ou une réception."""

    STATUT_OUVERT = "ouvert"
    STATUT_EN_COURS = "en_cours"
    STATUT_CLOS = "clos"

    STATUT_CHOICES = [
        (STATUT_OUVERT, "Ouvert"),
        (STATUT_EN_COURS, "En cours de traitement"),
        (STATUT_CLOS, "Clos"),
    ]

    reception = models.ForeignKey(
        ReceptionMarchandise,
        on_delete=models.CASCADE,
        related_name="dysfonctionnements",
        null=True,
        blank=True,
        verbose_name="Réception",
    )
    demande = models.ForeignKey(
        DemandeAchat,
        on_delete=models.CASCADE,
        related_name="dysfonctionnements",
        null=True,
        blank=True,
        verbose_name="Demande",
    )
    date_signalement = models.DateField(auto_now_add=True, verbose_name="Date de signalement")
    heure_signalement = models.TimeField(verbose_name="Heure de signalement")
    description = models.TextField(verbose_name="Description")
    photo = models.ImageField(
        upload_to="dysfonctionnements/",
        blank=True,
        null=True,
        verbose_name="Photo",
    )
    signale_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="dysfonctionnements_signales",
        verbose_name="Signalé par",
    )
    statut = models.CharField(
        max_length=20,
        choices=STATUT_CHOICES,
        default=STATUT_OUVERT,
        verbose_name="Statut",
    )
    plan_action = models.TextField(
        blank=True,
        help_text="Plan d'action du prestataire pour remédier au dysfonctionnement",
        verbose_name="Plan d'action",
    )
    date_cloture = models.DateField(null=True, blank=True, verbose_name="Date de clôture")

    class Meta:
        ordering = ["-date_signalement"]
        verbose_name = "Dysfonctionnement"
        verbose_name_plural = "Dysfonctionnements"

    def __str__(self) -> str:
        return f"Dysfonctionnement #{self.pk or 'N/A'}"

    def clean(self):
        """Vérifie qu'un contexte de rattachement est renseigné."""
        super().clean()
        if not self.reception_id and not self.demande_id:
            raise ValidationError(
                "Un dysfonctionnement doit être rattaché à une réception ou à une demande.",
            )


class EvaluationFournisseur(models.Model):
    """Évaluation annuelle agrégée d'un fournisseur selon la procédure P03."""

    fournisseur = models.ForeignKey(
        Fournisseur,
        on_delete=models.CASCADE,
        related_name="evaluations",
        verbose_name="Fournisseur",
    )
    annee = models.PositiveSmallIntegerField(verbose_name="Année")
    ca_annuel = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="CA réalisé avec ce fournisseur sur l'année",
        verbose_name="CA annuel",
    )
    pris_en_compte = models.BooleanField(
        default=True,
        help_text="Selon critères P03 chapitre 5 : exclut assurances, hôtels, refacturations clients",
        verbose_name="Pris en compte",
    )
    nb_receptions_evaluees = models.PositiveIntegerField(default=0, verbose_name="Nb réceptions évaluées")
    score_moyen = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Score moyen",
    )
    note = models.CharField(
        max_length=1,
        choices=ReceptionMarchandise.NOTE_FOURNISSEUR_CHOICES,
        null=True,
        blank=True,
        verbose_name="Note",
    )
    nb_dysfonctionnements = models.PositiveIntegerField(default=0, verbose_name="Nb dysfonctionnements")
    date_calcul = models.DateTimeField(auto_now=True, verbose_name="Date de calcul")

    class Meta:
        unique_together = ("fournisseur", "annee")
        ordering = ["-annee", "-score_moyen"]
        verbose_name = "Évaluation fournisseur"
        verbose_name_plural = "Évaluations fournisseurs"

    def __str__(self) -> str:
        return f"{self.fournisseur} - {self.annee}"
