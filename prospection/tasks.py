from celery import shared_task
from celery.utils.log import get_task_logger
from django.utils import timezone
from django.contrib.auth import get_user_model
from .models import Action, Evenement
from .fcm_utils import create_and_send_notification
from datetime import timedelta
import pytz

logger = get_task_logger(__name__)

@shared_task(bind=True, name='sales.tasks.check_actions_for_reminders')
def check_actions_for_reminders(self):
    """
    Vérifie les actions qui ont besoin de rappels et envoie les notifications
    avec gestion correcte du fuseau horaire de Tunis (UTC+1)
    """
    try:
        # 1. Définir le fuseau horaire de Tunis
        tunis_tz = pytz.timezone('Africa/Tunis')
        now = timezone.now().astimezone(tunis_tz)
        
        notifications_sent = 0

        # 2. Rendez-vous: rappel 1 jour avant
        rv_1_day = now + timedelta(days=1)
        rendez_vous_day = Action.objects.filter(
            is_RV=True,
            date_heure_planifie__gt=now,
            date_heure_planifie__lte=rv_1_day,
            date_heure_realiser__isnull=True,
            reminder_sent_1day=False,
            reminder_sent_1hour=False
        ).exclude(
            # Exclure les RV qui ont moins de 24h avant
            date_heure_planifie__lte=now + timedelta(hours=1)
        )

        # 3. Tous les types: rappel 1 heure avant
        one_hour_later = now + timedelta(hours=1)
        actions_hour = Action.objects.filter(
            date_heure_planifie__gt=now,
            date_heure_planifie__lte=one_hour_later,
            date_heure_realiser__isnull=True,
            reminder_sent_1hour=False
        )
        
        # Événements dans 1 jour (rappels 24h avant)
        events_1day = Evenement.objects.filter(
            date_heure_planifie__gt=now,
            date_heure_planifie__lte=rv_1_day,
            date_heure_realiser__isnull=True,
            reminder_sent_1day=False,
            reminder_sent_1hour=False
        ).exclude(
            date_heure_planifie__lte=now + timedelta(hours=1)
        )
        
        # Événements dans 1 heure (rappels 1h avant)
        events_1hour = Evenement.objects.filter(
            date_heure_planifie__gt=now,
            date_heure_planifie__lte=one_hour_later,
            date_heure_realiser__isnull=True,
            reminder_sent_1hour=False
        )

        User = get_user_model()

        def send_reminder(action, is_day_reminder):
            try:
                action_date = action.date_heure_planifie.astimezone(tunis_tz)
                
                users_to_notify = set()
                if action.created_by and action.pilote != action.created_by:
                    users_to_notify.add(action.created_by)
                if action.pilote:
                    users_to_notify.add(action.pilote)
                admins = User.objects.filter(is_superuser=True).exclude(
                    id__in=[u.id for u in users_to_notify]
                )
                users_to_notify.update(admins)

                action_type = "Rendez-vous" if action.is_RV else "Appel" if action.is_Appel else "Email"
                time_left = "1 jour" if is_day_reminder else "1 heure"
                
                company_name = action.societe.nom if action.societe else "Filiale inconnue"
                
                message = (f"Rappel: un {action_type} intitulée '{action.sujet}' est prévue dans {time_left} "
                   f"({action_date.strftime('%d/%m/%Y at %H:%M')}). "
                   f"Cette action est gérée par {company_name}.")

                create_and_send_notification(
                    message=message,
                    users=users_to_notify,
                    type='action',
                    id=action.id
                )

                if is_day_reminder:
                    action.reminder_sent_1day = True
                else:
                    action.reminder_sent_1hour = True
                action.save()
                
                return True
                
            except Exception as e:
                logger.error(f"Erreur notification pour action {action.id}: {str(e)}")
                return False
            
        def send_event_reminder(event, is_day_reminder):
            """Envoie les notifications pour un événement"""
            try:
                event_date = event.date_heure_planifie.astimezone(tunis_tz)
                
                users_to_notify = set()
                if event.created_by and event.pilote != event.created_by:
                    users_to_notify.add(event.created_by)
                if event.pilote:
                    users_to_notify.add(event.pilote)
                admins = User.objects.filter(is_superuser=True).exclude(
                    id__in=[u.id for u in users_to_notify]
                )
                users_to_notify.update(admins)
                
                company_name = event.societe.nom if event.societe else "Unknown Company"
                
                if is_day_reminder:
                    message = (f"Rappel : L'événement '{event.nom}' a lieu demain "
                            f"à {event.date_heure_planifie.strftime('%H:%M')} "
                            f"à {event.lieu}"
                            f"({event_date.strftime('%d/%m/%Y at %H:%M')}). "
                            f"Cet événement est organisé par {company_name}.")
                else:  # 1hour
                    message = (f"Rappel : L'événement '{event.nom}' commence "
                            f"dans une heure à {event.lieu}"
                            f"({event_date.strftime('%d/%m/%Y at %H:%M')}). "
                            f"Cet événement est organisé par {company_name}.")
                
                create_and_send_notification(
                    message=message,
                    users=users_to_notify,
                    type='event',
                    id=event.id
                )
                
                if is_day_reminder:
                    event.reminder_sent_1day = True
                else:
                    event.reminder_sent_1hour = True
                event.save()
                
                return True
                
            except Evenement.DoesNotExist:
                logger.error(f"Événement {event.nom} introuvable pour le rappel")

        # Traitement des rappels
        for action in rendez_vous_day:
            if send_reminder(action, is_day_reminder=True):
                notifications_sent += 1

        for action in actions_hour:
            if send_reminder(action, is_day_reminder=False):
                notifications_sent += 1
                
        for event in events_1day:
            if send_event_reminder(event, is_day_reminder=True):
                notifications_sent += 1
        
        for event in events_1hour:
            if send_event_reminder(event, is_day_reminder=False):
                notifications_sent += 1

        return f"{notifications_sent} notifications envoyées (TZ: Africa/Tunis)"

    except Exception as e:
        logger.error(f"Erreur dans check_actions_for_reminders: {str(e)}")
        self.retry(exc=e, countdown=300)
        