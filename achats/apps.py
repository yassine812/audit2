from django.apps import AppConfig


class AchatsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'achats'

    def ready(self):
        from . import signals  # noqa: F401
