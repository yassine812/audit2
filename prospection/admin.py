from django.contrib import admin
from .models import (
    Notification, Evenement, Entreprise, Swot, Action,
    FCMDevice, NotificationUtilisateur, Question, Enquete,
    Reponse, EnqueteToken, ProspectResearch, ProspectInfo,
)

admin.site.register(Notification)
admin.site.register(Entreprise)
admin.site.register(Evenement)
admin.site.register(Swot)
admin.site.register(Action)
admin.site.register(FCMDevice)
admin.site.register(NotificationUtilisateur)
admin.site.register(Question)
admin.site.register(Enquete)
admin.site.register(Reponse)
admin.site.register(EnqueteToken)
admin.site.register(ProspectResearch)
admin.site.register(ProspectInfo)

