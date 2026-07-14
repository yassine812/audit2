from django.apps import AppConfig


class AccidentTravailConfig(AppConfig):
    """Configuration de l'application Gestion des Accidents de Travail."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "accident_travail"
    verbose_name = "Accidents de Travail"
