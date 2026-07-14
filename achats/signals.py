"""Signaux du module Achats."""

from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from .models import Devis, LigneDemandeAchat


@receiver(post_save, sender=LigneDemandeAchat)
def recalculer_total_demande_apres_sauvegarde(sender, instance, **kwargs):
    """Recalcule le total HT de la demande après chaque modification de ligne."""
    instance.demande.recalculer_total()


@receiver(post_delete, sender=LigneDemandeAchat)
def recalculer_total_demande_apres_suppression(sender, instance, **kwargs):
    """Recalcule aussi le total HT lorsqu'une ligne est supprimée."""
    instance.demande.recalculer_total()


@receiver(pre_save, sender=Devis)
def conserver_un_seul_devis_choisi(sender, instance, **kwargs):
    """Désactive les autres devis retenus d'une même ligne avant sauvegarde."""
    if not instance.est_choisi or not instance.ligne_id:
        return

    Devis.objects.filter(ligne_id=instance.ligne_id, est_choisi=True).exclude(
        pk=instance.pk,
    ).update(est_choisi=False)
