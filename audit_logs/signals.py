"""Signaux d'audit automatiques pour enregistrer les actions dans LogEntry."""

import logging
from django.contrib.admin.models import LogEntry, ADDITION, CHANGE, DELETION
from django.contrib.contenttypes.models import ContentType
from django.db.models.signals import post_save, post_delete

from .middleware import get_current_user

logger = logging.getLogger(__name__)


def register_audit_signal(model_class):
    """Enregistre les signaux post_save et post_delete pour un modèle donné."""

    def _post_save_handler(sender, instance, created, **kwargs):
        try:
            user = get_current_user()
            if not user or not getattr(user, "is_authenticated", False):
                # Tente de trouver un attribut utilisateur sur le modèle
                for attr in ("user", "demandeur", "cree_par", "utilisateur", "acheteur", "victime"):
                    possible_user = getattr(instance, attr, None)
                    if possible_user and getattr(possible_user, "pk", None):
                        user = possible_user
                        break

            if not user or not getattr(user, "pk", None):
                return

            action_flag = ADDITION if created else CHANGE
            action_name = "Création" if created else "Modification"
            verbose_name = sender._meta.verbose_name.capitalize()

            LogEntry.objects.log_action(
                user_id=user.pk,
                content_type_id=ContentType.objects.get_for_model(instance).pk,
                object_id=instance.pk,
                object_repr=str(instance)[:200],
                action_flag=action_flag,
                change_message=f"{action_name} de {verbose_name}: {instance}",
            )
        except Exception as e:
            logger.exception("Erreur lors de l'enregistrement du log d'audit pour %s: %s", instance, e)

    def _post_delete_handler(sender, instance, **kwargs):
        try:
            user = get_current_user()
            if not user or not getattr(user, "is_authenticated", False):
                for attr in ("user", "demandeur", "cree_par", "utilisateur", "acheteur", "victime"):
                    possible_user = getattr(instance, attr, None)
                    if possible_user and getattr(possible_user, "pk", None):
                        user = possible_user
                        break

            if not user or not getattr(user, "pk", None):
                return

            verbose_name = sender._meta.verbose_name.capitalize()

            LogEntry.objects.log_action(
                user_id=user.pk,
                content_type_id=ContentType.objects.get_for_model(instance).pk,
                object_id=instance.pk,
                object_repr=str(instance)[:200],
                action_flag=DELETION,
                change_message=f"Suppression de {verbose_name}: {instance}",
            )
        except Exception as e:
            logger.exception("Erreur lors de l'enregistrement de la suppression d'audit pour %s: %s", instance, e)

    post_save.connect(
        _post_save_handler,
        sender=model_class,
        weak=False,
        dispatch_uid=f"audit_post_save_{model_class._meta.app_label}_{model_class._meta.model_name}",
    )
    post_delete.connect(
        _post_delete_handler,
        sender=model_class,
        weak=False,
        dispatch_uid=f"audit_post_delete_{model_class._meta.app_label}_{model_class._meta.model_name}",
    )


def setup_audit_signals():
    """Connecte automatiquement les signaux d'audit pour tous les modèles métier de tous les modules."""
    from django.apps import apps

    EXCLUDED_APPS = {"contenttypes", "sessions", "admin", "auth", "django_celery_beat", "authtoken"}
    EXCLUDED_MODELS = {"logentry", "session", "permission", "contenttype", "token"}

    try:
        for model in apps.get_models():
            app_label = model._meta.app_label
            model_name = model._meta.model_name

            if app_label in EXCLUDED_APPS or model_name in EXCLUDED_MODELS:
                continue

            register_audit_signal(model)
    except Exception as e:
        logger.exception("Erreur lors de l'initialisation des signaux d'audit globaux: %s", e)
