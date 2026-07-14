"""Commande de gestion pour envoyer les rappels d'échéances des accidents de travail.

À planifier via cron (toutes les heures) :
    0 * * * * cd /home/bouthaina/Desktop/Travail/audit2 && .venv/bin/python manage.py send_reminders >> /var/log/at_reminders.log 2>&1

Ou via cron sur le venv directement :
    0 * * * * /home/bouthaina/Desktop/Travail/audit2/.venv/bin/python /home/bouthaina/Desktop/Travail/audit2/manage.py send_reminders
"""

from django.core.management.base import BaseCommand
from django.utils import timezone

from accident_travail.tasks import envoyer_rappels_echeances


class Command(BaseCommand):
    help = "Envoie les rappels d'échéances (brouillon 12h, analyse 48h, LAP 8 jours)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simule l'envoi sans envoyer d'emails ni mettre à jour la base.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        self.stdout.write(
            f"[{timezone.now():%Y-%m-%d %H:%M:%S}] Vérification des échéances..."
        )

        if dry_run:
            self._dry_run()
        else:
            result = envoyer_rappels_echeances()
            self.stdout.write(
                self.style.SUCCESS(
                    f"  ✓ Rappels envoyés — brouillon: {result['rappels_brouillon']}, "
                    f"48h: {result['rappels_48h']}, 8j: {result['rappels_8j']}"
                )
            )

    def _dry_run(self):
        """Affiche les accidents qui recevraient un rappel, sans rien envoyer."""
        from datetime import timedelta
        from accident_travail.models import AccidentTravail

        now = timezone.now()

        brouillons = AccidentTravail.objects.filter(
            statut=AccidentTravail.STATUT_BROUILLON,
            created_at__lte=now - timedelta(hours=12),
            notification_brouillon_envoyee=False,
        )
        at_48h = AccidentTravail.objects.filter(
            statut=AccidentTravail.STATUT_24H,
            echeance_48h__lte=now + timedelta(hours=6),
            notification_48h_envoyee=False,
        )
        at_8j = AccidentTravail.objects.filter(
            statut=AccidentTravail.STATUT_48H,
            echeance_8j__lte=now + timedelta(hours=24),
            notification_8j_envoyee=False,
        )

        self.stdout.write(self.style.WARNING("  [DRY-RUN] Aucun email envoyé."))
        self.stdout.write(f"  Brouillons > 12h sans rappel : {brouillons.count()}")
        for a in brouillons:
            self.stdout.write(f"    - {a.reference} ({a.created_at:%Y-%m-%d %H:%M})")

        self.stdout.write(f"  Accidents 24h avec échéance 48h dans <6h : {at_48h.count()}")
        for a in at_48h:
            self.stdout.write(f"    - {a.reference} (échéance: {a.echeance_48h:%Y-%m-%d %H:%M})")

        self.stdout.write(f"  Accidents 48h avec échéance 8j dans <24h : {at_8j.count()}")
        for a in at_8j:
            self.stdout.write(f"    - {a.reference} (échéance: {a.echeance_8j:%Y-%m-%d %H:%M})")
