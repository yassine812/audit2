from django.conf import settings
from .models import NotificationUtilisateur
from django.contrib.auth import get_user_model

def notifications(request):
    if request.user.is_authenticated:
        User = get_user_model()
        user = request.user
        unread_notifications = NotificationUtilisateur.objects.filter(
            utilisateur=user,
            est_lu=False
        ).select_related('notification').order_by('-notification__date_heure').count()
        
        all_notifications = NotificationUtilisateur.objects.filter(
            utilisateur=user,
        ).select_related('notification').order_by('-notification__date_heure')
        
        return {
            'unread_notifications': all_notifications,
            'unread_notifications_count': unread_notifications
        }
    return {'all_notifications': [], 'unread_notifications': 0}

def firebase_config(request):
    return {
        'FCM_API_KEY': settings.FCM_APIKEY,
        'FCM_AUTH_DOMAIN': settings.FCM_AUTH_DOMAIN,
        'FCM_PROJECT_ID': settings.FCM_PROJECT_ID,
        'FCM_STORAGE_BUCKET': settings.FCM_STORAGE_BUCKET,
        'FCM_SENDER_ID': settings.FCM_SENDER_ID,
        'FCM_APP_ID': settings.FCM_APP_ID,
        'FCM_VAPID_KEY': settings.FCM_VAPID_KEY
    }