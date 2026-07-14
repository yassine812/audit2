"""
Modèles de l'application Prospection Commerciale.

Les modèles Societe et Utilisateur sont importés depuis l'app accounts
afin d'utiliser les modèles partagés du projet audit2.
"""
from datetime import datetime, timezone
import uuid

from django.db import models
from django.contrib.auth import get_user_model
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _

# ─── Imports depuis accounts pour compatibilité descendante ──────────────────
# Ainsi, `from .models import *` dans views/admin continue de fonctionner.
from accounts.models import Societe, User as Utilisateur  # noqa: F401


class Notification(models.Model):
    TYPE_CHOICES = [
        ('action', 'Action'),
        ('event', 'Événement'),
        ('enquete', 'Enquête'),
    ]

    message = models.TextField(verbose_name="Message")
    date_heure = models.DateTimeField(auto_now_add=True, verbose_name="Date et Heure")
    type = models.CharField(
        max_length=10,
        choices=TYPE_CHOICES,
        verbose_name="Type de notification"
    )
    lien_id = models.PositiveIntegerField(
        verbose_name="ID de l'action ou de l'événement lié"
    )
    utilisateurs = models.ManyToManyField(
        get_user_model(),
        through='NotificationUtilisateur',
        related_name='prospection_notifications',
        verbose_name="Utilisateurs"
    )

    def __str__(self):
        return f"{self.message[:30]}"


class NotificationUtilisateur(models.Model):
    notification = models.ForeignKey(Notification, on_delete=models.CASCADE)
    utilisateur = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    est_lu = models.BooleanField(default=False, verbose_name="Lu")

    class Meta:
        unique_together = ('notification', 'utilisateur')

    def __str__(self):
        lu_status = "✔️ Lu" if self.est_lu else "❌ Non lu"
        return f"{self.notification} - {self.utilisateur} - {lu_status}"


class Entreprise(models.Model):
    nom = models.CharField(max_length=100, verbose_name="Nom")
    adresse = models.CharField(max_length=200, verbose_name="Adresse")
    secteur_activite = models.CharField(max_length=100, verbose_name="Secteur d'Activité")
    telephone = models.CharField(max_length=20, verbose_name="Téléphone")
    email = models.EmailField(verbose_name="Email", db_index=True)
    date = models.DateField(default=now, verbose_name="Date")
    date_conversion = models.DateTimeField(null=True, blank=True, verbose_name="Date Conversion")
    is_CLT = models.BooleanField(default=False, verbose_name="Est Client")
    is_Prospect = models.BooleanField(default=False, verbose_name="Est Prospect")
    is_Concurent = models.BooleanField(default=False, verbose_name="Est Concurrent")
    societe = models.ForeignKey(
        'accounts.Societe', on_delete=models.SET_NULL,
        null=True, blank=True, verbose_name="Société"
    )
    num_compte = models.CharField(max_length=50, null=True, blank=True, verbose_name="Numéro de compte")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['societe', 'num_compte'],
                name='unique_num_compte_par_societe',
                condition=~models.Q(num_compte__isnull=True)
            )
        ]

    def __str__(self):
        return f"{self.nom}"


class Evenement(models.Model):
    TYPE_CHOICES = [
        ('interne', 'Interne'),
        ('externe', 'Externe'),
    ]

    ETAT_CHOICES_EVENT = [
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('', '-'),
    ]

    CATEGORIE_CHOICES = [
        ('foire', 'Foire'),
        ('salon', 'Salon'),
        ('conference', 'Conference'),
        ('seminaire', 'Seminaire'),
    ]

    nom = models.CharField(max_length=100, verbose_name="Nom")
    date = models.DateTimeField(auto_now_add=True, verbose_name="Date")
    date_heure_planifie = models.DateTimeField(default=now, verbose_name="Date et Heure Planifiés")
    date_heure_realiser = models.DateTimeField(null=True, blank=True, verbose_name="Date et Heure Réalisés")
    lieu = models.CharField(max_length=200, verbose_name="Lieu")
    secteur_activite = models.CharField(max_length=100, verbose_name="Secteur Activité")
    etat = models.CharField(max_length=50, choices=ETAT_CHOICES_EVENT, default='', verbose_name="État", blank=True)
    notes = models.TextField(verbose_name="Notes", blank=True, null=True)
    societe = models.ForeignKey(
        'accounts.Societe', on_delete=models.SET_NULL,
        null=True, blank=True, verbose_name="Société"
    )
    entreprise = models.ForeignKey('Entreprise', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Entreprise")
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, default='interne', verbose_name="Type")
    created_by = models.ForeignKey(
        get_user_model(), on_delete=models.SET_NULL, null=True,
        verbose_name="Créé par", related_name="evenements_crees"
    )
    pilote = models.ForeignKey(
        get_user_model(), on_delete=models.SET_NULL, null=True,
        verbose_name="Pilote", related_name="evenements_pilotes"
    )
    categorie = models.CharField(
        max_length=20,
        choices=CATEGORIE_CHOICES,
        verbose_name="Catégorie",
        blank=True
    )
    reminder_sent_1day = models.BooleanField(default=False, verbose_name="Rappel 1 jour envoyé")
    reminder_sent_1hour = models.BooleanField(default=False, verbose_name="Rappel 1 heure envoyé")

    class Meta:
        indexes = [
            models.Index(fields=['reminder_sent_1day']),
            models.Index(fields=['reminder_sent_1hour']),
            models.Index(fields=['categorie']),
            models.Index(fields=['type']),
        ]

    def __str__(self):
        return f"Événement: {self.nom} | Type: {self.get_type_display()} | Date: {self.date}"


class Swot(models.Model):
    TYPE_CHOICES = [
        ('force', 'Force'),
        ('faiblesse', 'Faiblesse'),
        ('opportunite', 'Opportunité'),
        ('menace', 'Menace'),
    ]

    AXE_CHOICES = [
        ('commercial', 'Commercial'),
        ('financiere', 'Financier'),
        ('exploitation', 'Exploitation'),
        ('rh', 'Ressources humaines'),
        ('technologique', 'Technologique'),
        ('autre', 'Autre'),
    ]

    type = models.CharField(max_length=50, choices=TYPE_CHOICES, verbose_name="Type")
    date = models.DateField(auto_now_add=True, verbose_name="Date")
    description = models.CharField(max_length=200, verbose_name="Description")
    axe = models.CharField(max_length=50, choices=AXE_CHOICES, verbose_name="Axe")
    societe = models.ForeignKey(
        'accounts.Societe', on_delete=models.SET_NULL,
        null=True, blank=True, verbose_name="Société"
    )
    created_by = models.ForeignKey(
        get_user_model(), on_delete=models.SET_NULL, null=True,
        verbose_name="Créé par", related_name="swots_crees"
    )
    entreprise = models.ForeignKey(
        'Entreprise',
        on_delete=models.CASCADE,
        limit_choices_to={'is_Concurent': True},
        verbose_name="Entreprise Concurrente"
    )

    def __str__(self):
        return f"{self.get_type_display()} | {self.get_axe_display()} | {self.date}"


class Action(models.Model):
    ETAT_CHOICES_APPEL = [
        ('reussi', 'Reussi'),
        ('non_reussi', 'Non Reussi'),
        ('', '-'),
    ]

    ETAT_CHOICES_EMAIL = [
        ('lu', 'Lu'),
        ('non_lu', 'Non lu'),
        ('', '-'),
    ]

    ETAT_CHOICES_RENDEZ_VOUS = [
        ('planifie', 'Planifié'),
        ('termine', 'Fini'),
        ('annule', 'Annulé'),
        ('', '-'),
    ]

    date_heure = models.DateTimeField(auto_now_add=True, verbose_name="Date et Heure")
    date_heure_planifie = models.DateTimeField(default=now, verbose_name="Date et Heure Planifiés", null=True, blank=True)
    date_heure_realiser = models.DateTimeField(null=True, blank=True, verbose_name="Date et Heure Réalisés")
    compte_rendu = models.TextField(verbose_name="Compte Rendu")
    notes = models.TextField(verbose_name="Notes")
    sujet = models.CharField(max_length=200, verbose_name="Sujet")
    is_Appel = models.BooleanField(default=False, verbose_name="est appel")
    is_Email = models.BooleanField(default=False, verbose_name="est email")
    is_RV = models.BooleanField(default=False, verbose_name="est rendez-vous")
    etat = models.CharField(max_length=50, verbose_name="État", blank=True, null=True)
    societe = models.ForeignKey(
        'accounts.Societe', on_delete=models.SET_NULL,
        null=True, blank=True, verbose_name="Société"
    )
    entreprise = models.ForeignKey(
        'Entreprise', on_delete=models.SET_NULL,
        null=True, blank=True, verbose_name="Entreprise/Client", related_name='actions'
    )
    created_by = models.ForeignKey(
        get_user_model(), on_delete=models.SET_NULL, null=True,
        verbose_name="Créé par", related_name="actions_crees"
    )
    pilote = models.ForeignKey(
        get_user_model(), on_delete=models.SET_NULL, null=True,
        verbose_name="Pilote", related_name="actions_pilotees"
    )
    reminder_sent_1day = models.BooleanField(default=False, verbose_name="Rappel 1 jour envoyé")
    reminder_sent_1hour = models.BooleanField(default=False, verbose_name="Rappel 1 heure envoyé")

    class Meta:
        indexes = [
            models.Index(fields=['reminder_sent_1day']),
            models.Index(fields=['reminder_sent_1hour']),
        ]

    def save(self, *args, **kwargs):
        if self.etat:
            if self.is_Appel and self.etat not in dict(self.ETAT_CHOICES_APPEL):
                raise ValueError("L'état pour un appel doit être 'Réussi' ou 'Non Réussi'.")
            elif self.is_Email and self.etat not in dict(self.ETAT_CHOICES_EMAIL):
                raise ValueError("L'état pour un email doit être 'Lu' ou 'Non Lu'.")
            elif self.is_RV and self.etat not in dict(self.ETAT_CHOICES_RENDEZ_VOUS):
                raise ValueError("L'état pour un rendez-vous doit être 'Planifié', 'Terminé' ou 'Annulé'.")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Action - {self.sujet} - {self.date_heure.strftime('%Y-%m-%d %H:%M')}"


class FCMDevice(models.Model):
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, related_name='fcm_devices')
    registration_id = models.TextField(verbose_name="Registration token")
    active = models.BooleanField(default=True, verbose_name="Is active")
    date_created = models.DateTimeField(auto_now_add=True, verbose_name="Creation date")

    class Meta:
        verbose_name = "FCM Device"
        verbose_name_plural = "FCM Devices"

    def __str__(self):
        return f"{self.user.username} - {self.registration_id[:20]}..."


class Question(models.Model):
    class Type(models.TextChoices):
        CLOSED = 'closed', _('Échelle')
        OUINON = 'ouinon', _('Oui / Non / Peut-être')
        OPEN = 'open', _('Commentaire')
        NOTE = 'note', _('Note (1-10)')

    question_fr = models.TextField(verbose_name=_("Intitulé de la question (Français)"), default="")
    question_en = models.TextField(verbose_name=_("Intitulé de la question (Anglais)"), default="")
    question_de = models.TextField(verbose_name=_("Intitulé de la question (Allemand)"), default="", blank=True)
    type = models.CharField(max_length=20, choices=Type.choices, default=Type.CLOSED, verbose_name=_("Type de question"))
    obligatoire = models.BooleanField(default=False, verbose_name=_("Obligatoire"))

    class Meta:
        verbose_name = "Question"
        verbose_name_plural = "Questions"

    def get_question_text(self, language='fr'):
        language = language.lower()
        if language == 'en' and self.question_en:
            return self.question_en
        elif language == 'de' and self.question_de:
            return self.question_de
        return self.question_fr

    def __str__(self):
        return self.question_fr


class Enquete(models.Model):
    titre = models.CharField(max_length=255, blank=True, verbose_name="Titre")
    description = models.TextField(verbose_name="Description")
    date_creation = models.DateField(verbose_name="Date de creation")
    date_modification = models.DateField(null=True, blank=True, verbose_name="Date de modification")
    date_envoi = models.DateField(null=True, blank=True, verbose_name="Date d'envoi")
    date_rappel = models.DateField(null=True, blank=True, verbose_name="Date de rappel")
    date_reponse = models.DateField(null=True, blank=True, verbose_name="Date de reponse")
    created_by = models.ForeignKey(
        get_user_model(), on_delete=models.SET_NULL, null=True,
        verbose_name="Créé par", related_name="enquetes_crees"
    )
    client = models.ForeignKey(Entreprise, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Client")
    email = models.EmailField(null=True, blank=True, verbose_name="Email destinataire")
    questions = models.ManyToManyField(Question, related_name='enquetes_set')
    is_completed = models.BooleanField(default=False, verbose_name="Répondu complètement")

    class Meta:
        verbose_name = "Enquête"
        verbose_name_plural = "Enquêtes"

    def save(self, *args, **kwargs):
        if self.pk and hasattr(self, 'client'):
            try:
                old_instance = Enquete.objects.get(pk=self.pk)
                if old_instance.client != self.client:
                    self.titre = f"{self.date_creation}_{self.client.nom}"
            except Enquete.DoesNotExist:
                pass
        if not self.titre and self.client:
            self.titre = f"{self.date_creation}_{self.client.nom}"
        super().save(*args, **kwargs)

    def get_progress(self, client):
        total_questions = self.questions.count()
        answered_questions = self.reponses.filter(client=client).count()
        return (answered_questions / total_questions) * 100 if total_questions > 0 else 0

    def __str__(self):
        return self.titre


class Reponse(models.Model):
    reponse = models.CharField(max_length=500, verbose_name=_("Valeur de la réponse"), help_text=_("Texte, Oui/Non, note ou choix selon le type de la question"))
    commentaire = models.TextField(verbose_name=_("Commentaire"), blank=True, null=True)
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='reponses', verbose_name=_("Question"))
    client = models.ForeignKey(Entreprise, on_delete=models.CASCADE, blank=True, null=True, related_name='client_reponses', verbose_name=_("Client"))
    enquete = models.ForeignKey(Enquete, on_delete=models.CASCADE, related_name='reponses', verbose_name=_("Enquête"))

    class Meta:
        verbose_name = "Réponse"
        verbose_name_plural = "Réponses"

    def __str__(self):
        client_name = self.client.nom if self.client else "Anonyme"
        return f"{client_name} → {self.question.question_fr[:30]} : {self.reponse[:20]}"


class EnqueteToken(models.Model):
    LANGUAGE_CHOICES = [
        ('fr', 'Français'),
        ('en', 'English'),
        ('de', 'Deutsch'),
    ]

    enquete = models.OneToOneField(Enquete, on_delete=models.CASCADE, related_name='token')
    client = models.ForeignKey(Entreprise, on_delete=models.CASCADE)
    token = models.CharField(max_length=64, unique=True, default=uuid.uuid4)
    created_at = models.DateTimeField(auto_now_add=True)
    used = models.BooleanField(default=False)
    language = models.CharField(max_length=2, choices=LANGUAGE_CHOICES, default='fr', verbose_name='Language')

    def is_valid(self):
        return not self.used and (datetime.now(timezone.utc) - self.created_at).days < 15

    def __str__(self):
        return f"Token for {self.enquete} ({self.client})"


# ===================== Prospects AI Research =====================

class ProspectResearch(models.Model):
    """Historique d'une recherche AI pour un prospect (Entreprise)."""
    entreprise = models.ForeignKey(
        'Entreprise', on_delete=models.CASCADE,
        related_name='prospect_researches', verbose_name="Entreprise"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Date de recherche")
    created_by = models.ForeignKey(
        get_user_model(), on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='prospect_research_created', verbose_name="Créé par"
    )
    query = models.TextField(blank=True, null=True, verbose_name="Requête utilisée")
    summary = models.TextField(blank=True, null=True, verbose_name="Résumé des trouvailles")
    raw_result = models.TextField(blank=True, null=True, verbose_name="Résultat brut")
    confidence = models.CharField(
        max_length=10,
        choices=[
            ('high', 'Fiabilité élevée'),
            ('medium', 'Fiabilité moyenne'),
            ('low', 'Fiabilité faible'),
            ('none', 'Échec'),
        ],
        default='medium',
        verbose_name="Niveau de confiance",
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Research {self.id} - {self.entreprise.nom} @ {self.created_at:%Y-%m-%d %H:%M}"


class ProspectInfo(models.Model):
    """Information structurée trouvée pour un prospect."""
    class InfoType(models.TextChoices):
        EMAIL = 'email', _('Email')
        PHONE = 'phone', _('Téléphone')
        WEBSITE = 'website', _('Site web')
        SOCIAL = 'social', _('Réseau social')
        ADDRESS = 'address', _('Adresse')
        NOTE = 'note', _('Note')

    entreprise = models.ForeignKey('Entreprise', on_delete=models.CASCADE, related_name='prospect_infos', verbose_name="Entreprise")
    research = models.ForeignKey(ProspectResearch, on_delete=models.CASCADE, related_name='infos', verbose_name="Recherche")
    type = models.CharField(max_length=20, choices=InfoType.choices, verbose_name="Type")
    value = models.CharField(max_length=500, verbose_name="Valeur")
    label = models.CharField(max_length=100, blank=True, null=True, verbose_name="Libellé")
    source_url = models.URLField(blank=True, null=True, verbose_name="Source")
    extra = models.JSONField(blank=True, null=True, verbose_name="Données supplémentaires")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Date d'enregistrement")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['entreprise', 'type', 'value'], name='unique_info_per_entreprise')
        ]
        indexes = [
            models.Index(fields=['type']),
        ]

    def __str__(self):
        return f"{self.get_type_display()} | {self.value}"
