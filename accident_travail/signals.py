"""Signals pour l'historique automatique des accidents de travail via LogEntry."""

import json
from django.contrib.admin.models import LogEntry, ADDITION, CHANGE
from django.contrib.contenttypes.models import ContentType
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone


def _log(user, obj, action_flag, message):
    """Crée une entrée dans le journal Django admin LogEntry."""
    if user is None or not hasattr(user, 'pk') or not user.pk:
        return
    LogEntry.objects.log_action(
        user_id=user.pk,
        content_type_id=ContentType.objects.get_for_model(obj).pk,
        object_id=obj.pk,
        object_repr=str(obj)[:200],
        action_flag=action_flag,
        change_message=message,
    )


def log_accident_history(user, accident, message, action_flag=CHANGE):
    """Enregistre une entrée d'historique sur l'accident."""
    _log(user, accident, action_flag, message)


def log_analyse_history(user, analyse, message, action_flag=CHANGE):
    """Enregistre une entrée d'historique sur l'analyse 48h."""
    _log(user, analyse, action_flag, message)
    # Aussi sur l'accident parent
    _log(user, analyse.accident, action_flag, f"[Analyse 48h] {message}")


def log_lap_history(user, lap, message, action_flag=CHANGE):
    """Enregistre une entrée d'historique sur le LAP 8j."""
    _log(user, lap, action_flag, message)
    _log(user, lap.accident, action_flag, f"[LAP 8j] {message}")
