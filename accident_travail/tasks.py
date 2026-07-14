"""Tâches de notifications d'échéances des accidents de travail.

Sans Celery, utilisez la commande de gestion :
    python manage.py send_reminders
à planifier via cron toutes les heures :
    0 * * * * /chemin/.venv/bin/python /chemin/manage.py send_reminders
"""

import logging
from datetime import timedelta

from django.core.mail import send_mail
from django.db.models import Q
from django.template.loader import render_to_string
from django.utils import timezone

logger = logging.getLogger(__name__)

try:
    from celery import shared_task
except ImportError:
    # Celery non installé : décorateur no-op transparent
    def shared_task(func):
        return func


def envoyer_notification_echeance(accident, type_echeance):
    """Envoie un email de rappel d'échéance aux responsables de la section."""
    from accounts.models import User

    # Destinataires : utilisateurs actifs de la même société ayant un rôle RS, RO ou CE
    destinataires = list(
        User.objects.filter(
            section__societe=accident.societe,
            is_active=True,
        )
        .filter(Q(is_RS=True) | Q(is_RO=True) | Q(is_CE=True))
        .values_list("email", flat=True)
        .distinct()
    )

    # For brouillon reminders, also notify the creator
    if type_echeance == "brouillon" and accident.created_by and accident.created_by.email:
        if accident.created_by.email not in destinataires:
            destinataires.append(accident.created_by.email)

    if not destinataires:
        logger.warning(
            "Aucun destinataire pour la notification %s de l'accident %s",
            type_echeance, accident.reference,
        )
        return

    template_map = {
        "brouillon": "accident_travail/emails/rappel_brouillon.html",
        "48h": "accident_travail/emails/rappel_48h.html",
        "8j": "accident_travail/emails/rappel_8j.html",
    }
    subject_map = {
        "brouillon": f"⏰ Rappel — Brouillon à compléter : {accident.reference}",
        "48h": f"⚠️ Rappel — Analyse 48h requise : {accident.reference}",
        "8j": f"⚠️ Rappel — LAP 8 jours requise : {accident.reference}",
    }

    html_message = render_to_string(template_map[type_echeance], {"accident": accident})
    send_mail(
        subject=subject_map[type_echeance],
        message="",
        from_email=None,  # utilise DEFAULT_FROM_EMAIL
        recipient_list=destinataires,
        html_message=html_message,
        fail_silently=True,
    )
    logger.info(
        "Notification %s envoyée pour l'accident %s à %s",
        type_echeance, accident.reference, destinataires,
    )


@shared_task
def envoyer_rappels_echeances():
    """
    Lance toutes les heures via Celery Beat.
    Envoie des rappels pour les accidents dont l'échéance approche.
    """
    from .models import AccidentTravail

    now = timezone.now()

    # Rappel brouillon : créé il y a plus de 12h, pas encore notifié
    accidents_brouillon = AccidentTravail.objects.filter(
        statut=AccidentTravail.STATUT_BROUILLON,
        created_at__lte=now - timedelta(hours=12),
        notification_brouillon_envoyee=False,
    )
    for accident in accidents_brouillon:
        envoyer_notification_echeance(accident, "brouillon")
        accident.notification_brouillon_envoyee = True
        accident.save(update_fields=["notification_brouillon_envoyee"])

    # Rappel 48h : échéance dans moins de 6h, pas encore notifié
    accidents_48h = AccidentTravail.objects.filter(
        statut=AccidentTravail.STATUT_24H,
        echeance_48h__lte=now + timedelta(hours=6),
        notification_48h_envoyee=False,
    )
    for accident in accidents_48h:
        envoyer_notification_echeance(accident, "48h")
        accident.notification_48h_envoyee = True
        accident.save(update_fields=["notification_48h_envoyee"])

    # Rappel 8j : échéance dans moins de 24h, pas encore notifié
    accidents_8j = AccidentTravail.objects.filter(
        statut=AccidentTravail.STATUT_48H,
        echeance_8j__lte=now + timedelta(hours=24),
        notification_8j_envoyee=False,
    )
    for accident in accidents_8j:
        envoyer_notification_echeance(accident, "8j")
        accident.notification_8j_envoyee = True
        accident.save(update_fields=["notification_8j_envoyee"])

    logger.info(
        "Rappels envoyés : %d (brouillon), %d (48h), %d (8j)",
        accidents_brouillon.count(), accidents_48h.count(), accidents_8j.count(),
    )
    return {
        "rappels_brouillon": accidents_brouillon.count(),
        "rappels_48h": accidents_48h.count(),
        "rappels_8j": accidents_8j.count(),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Notifications d'événements (création / modification / soumission)
# ─────────────────────────────────────────────────────────────────────────────

SUJET_ALERTE = {
    "creation":        "🚨 Nouvel accident déclaré : {ref}",
    "modification_24h": "✏️ Déclaration 24h modifiée : {ref}",
    "soumission_24h":  "✅ Déclaration 24h soumise : {ref}",
    "modification_48h": "✏️ Analyse 48h mise à jour : {ref}",
    "soumission_48h":  "✅ Analyse 48h soumise : {ref}",
    "modification_8j": "✏️ LAP 8 jours mis à jour : {ref}",
    "cloture":         "🔒 Accident clôturé : {ref}",
}


def notifier_accident_alerte(accident, evenement, acteur=None):
    """Notifie par email la chaîne d'alerte lors d'un événement sur un accident.

    Destinataires :
    - RO, RS, CE dont la section = section de l'accident
    - Tous les CE de la même société (chef d'établissement, vision globale)
    - Tous les superadmin actifs avec une adresse email
    L'acteur déclenchant l'événement est exclu pour éviter l'auto-notification.
    """
    from django.db.models import Q as _Q
    from accounts.models import User

    section = accident.section
    societe = accident.societe

    # RS/RO/CE de la section concernée
    qs_section = User.objects.filter(
        section=section, is_active=True,
    ).filter(_Q(is_RS=True) | _Q(is_RO=True) | _Q(is_CE=True)) if section else User.objects.none()

    # CE de toute la société (peuvent être sur une autre section)
    qs_ce_societe = User.objects.filter(
        section__societe=societe, is_active=True, is_CE=True,
    ) if societe else User.objects.none()

    # Superadmins
    qs_superadmin = User.objects.filter(is_superuser=True, is_active=True)

    destinataires = set(
        list(qs_section.exclude(email="").values_list("email", flat=True))
        + list(qs_ce_societe.exclude(email="").values_list("email", flat=True))
        + list(qs_superadmin.exclude(email="").values_list("email", flat=True))
    )

    # Ne pas notifier l'acteur de l'événement
    if acteur and acteur.email:
        destinataires.discard(acteur.email)

    destinataires = list(destinataires)
    if not destinataires:
        logger.warning(
            "Aucun destinataire pour l'alerte '%s' de l'accident %s",
            evenement, accident.reference,
        )
        return

    sujet = SUJET_ALERTE.get(evenement, f"Accident {accident.reference} — {evenement}")
    sujet = sujet.format(ref=accident.reference)

    html_message = render_to_string(
        "accident_travail/emails/notification_alerte.html",
        {"accident": accident, "evenement": evenement, "acteur": acteur},
    )

    send_mail(
        subject=sujet,
        message="",
        from_email=None,
        recipient_list=destinataires,
        html_message=html_message,
        fail_silently=True,
    )
    logger.info(
        "Alerte '%s' envoyée pour l'accident %s à : %s",
        evenement, accident.reference, destinataires,
    )
