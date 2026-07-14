from django.apps import AppConfig


class AuditConfig(AppConfig):
    """Configuration de l'application audit."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "audit"
    verbose_name = "Audit interne"

    def ready(self) -> None:
        """Charge les signaux de l'application."""
        from . import signals  # noqa: F401
