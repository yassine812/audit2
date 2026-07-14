from django.db.models.signals import post_migrate, pre_save
from django.dispatch import receiver
from django_celery_beat.models import PeriodicTask, IntervalSchedule
from django.utils import timezone
from .models import Enquete, Entreprise
from .utils.client_utils import get_base_url
from django.conf import settings
import requests
from django.db import transaction
import logging

logger = logging.getLogger(__name__)

@receiver(post_migrate)
def setup_periodic_tasks(sender, **kwargs):
    # Crée un intervalle de 5 minutes
    schedule, created = IntervalSchedule.objects.get_or_create(
        every=5,
        period=IntervalSchedule.MINUTES,
    )
    
    # Crée ou met à jour la tâche périodique
    PeriodicTask.objects.update_or_create(
        name='Vérifier les rappels des actions',
        defaults={
            'interval': schedule,
            'task': 'sales.tasks.check_actions_for_reminders',
            'enabled': True,
            'last_run_at': timezone.now(),
        }
    )

@receiver(pre_save, sender=Enquete)
def create_client_from_enquete(sender, instance, **kwargs):
    """
    Si l'enquête référence un 'client' (externe) par NumeroTiers et qu'il n'existe pas
    dans Entreprise (is_CLT=True), on le crée à partir de l'API.
    """
    # Aucun client défini → on sort
    if not getattr(instance, "client_id", None):
        return

    # client = instance.client doit exposer num_compte (NumeroTiers)
    client = getattr(instance, "client", None)
    if not client or not getattr(client, "num_compte", None):
        return

    numero = client.num_compte

    # Déjà présent localement ?
    if Entreprise.objects.filter(num_compte=numero, is_CLT=True).exists():
        return

    # Déterminer la société pour l'appel API
    societe = None
    if getattr(instance, "created_by", None) and hasattr(instance.created_by, "societe"):
        societe = instance.created_by.societe

    if not societe:
        logger.warning("Aucune société trouvée pour create_client_from_enquete (enquete %s)", instance.pk)
        return

    payload = None
    try:
        from .views import _fetch_client_from_api
        payload = _fetch_client_from_api(numero, societe)
    except Exception as e:
        logger.error("Erreur d'appel _fetch_client_from_api: %s", str(e), exc_info=True)
    if not payload:
        logger.error("Impossible de récupérer les données API pour le client %s (enquete %s)", numero, instance.pk)
        return

    try:
        with transaction.atomic():
            # Ne PAS imposer 'id' pour éviter les conflits avec l'AUTO INCREMENT.
            Entreprise.objects.create(**payload)
            logger.info("Client (num_compte=%s) créé pour l'enquête %s", numero, instance.pk)
    except Exception as e:
        logger.error("Erreur create_client_from_enquete: %s", str(e), exc_info=True)