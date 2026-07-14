from pyfcm import FCMNotification
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from .models import FCMDevice, Notification as NotificationModel, NotificationUtilisateur
from pyfcm.errors import FCMNotRegisteredError, InvalidDataError
import logging

logger = logging.getLogger(__name__)
_push_service = None


def _get_push_service():
    global _push_service
    if _push_service is None:
        api_key = getattr(settings, "FCM_APIKEY", "")
        if api_key:
            _push_service = FCMNotification(api_key)
    return _push_service

def send_notification_fcm(user, message, title="Nouvelle notification", data=None):
    """
    Version améliorée avec :
    - Gestion des tokens expirés
    - Nettoyage automatique
    - Meilleure journalisation
    """
    if data is None:
        data = {}

    # Récupérer seulement les devices actifs
    devices = FCMDevice.objects.filter(user=user, active=True)
    if not devices.exists():
        logger.warning(f"Aucun device actif pour l'utilisateur {user.id}")
        return False

    registration_ids = [d.registration_id for d in devices]
    logger.info(f"Envoi à {len(registration_ids)} devices pour {user.username}")

    try:
        svc = _get_push_service()
        if svc is None:
            logger.warning("FCM not configured (FCM_APIKEY missing), skipping push notification")
            return False
        result = svc.notify_multiple_devices(
            registration_ids=registration_ids,
            message_title=title,
            message_body=message,
            data_message=data,
            timeout=10  # Timeout plus court
        )

        # Analyser la réponse pour détecter les tokens invalides
        if result and 'results' in result:
            for i, device_result in enumerate(result['results']):
                if 'error' in device_result:
                    error = device_result['error']
                    if error in ['NotRegistered', 'InvalidRegistration']:
                        # Désactiver le token invalide
                        invalid_token = registration_ids[i]
                        FCMDevice.objects.filter(
                            registration_id=invalid_token
                        ).update(active=False)
                        logger.info(f"Token désactivé : {invalid_token[:10]}... (erreur: {error})")

        return True

    except FCMNotRegisteredError as e:
        logger.error(f"Erreur FCM - tokens non enregistrés : {str(e)}")
        # Désactiver tous les tokens pour cet utilisateur
        devices.update(active=False)
        return False
        
    except InvalidDataError as e:
        logger.error(f"Données FCM invalides : {str(e)}")
        return False
        
    except Exception as e:
        logger.error(f"Erreur inattendue FCM : {str(e)}", exc_info=True)
        return False
    
def create_and_send_notification(message, users, type, id):
    """
    Crée une notification dans la base de données et l'envoie via FCM
    """
    notification = NotificationModel.objects.create(
        message=message,
        type=type,
        lien_id=id
    )
    
    for user in users:
        NotificationUtilisateur.objects.create(
            notification=notification,
            utilisateur=user,
            est_lu=False
        )
        send_notification_fcm(
            user=user,
            message=message,
            title="Nouvelle notification",
            data={
                "id": str(notification.id),
            }
        )
        
        context = {
            'username': user.username,  
            'message': message,
            'notification_id': notification.id,
        }
        
        html_message = render_to_string('adminlte/emails/notification_email.html', context)
        plain_message = strip_tags(html_message) 
        from_email = settings.DEFAULT_FROM_EMAIL
        to_email = user.email  
        
        send_mail(
            "Nouvelle notification", 
            plain_message,
            from_email,
            [to_email],
            html_message=html_message,
            fail_silently=False,
        )
    
    return notification