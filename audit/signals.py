import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Audit, AuditStatut, ResultatAudit

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Audit)
def create_resultat_when_audit_termine(sender, instance: Audit, **kwargs):
    """Crée le résultat automatiquement quand l'audit est terminé."""
    if instance.statut == AuditStatut.TERMINE:
        resultat, created = ResultatAudit.objects.get_or_create(audit=instance)
        if created:
            logger.info("Résultat créé automatiquement pour l'audit %s", instance.numero)
        else:
            logger.debug("Résultat déjà existant pour l'audit %s", instance.numero)
