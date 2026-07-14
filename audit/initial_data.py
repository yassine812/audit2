"""Données initiales du module audit."""

from decimal import Decimal

from .models import AuditType, BaremeCotation


BAREME_FIXTURES = [
    {"code": "C", "note": Decimal("2.00"), "description": "Conforme", "actif": True},
    {"code": "PC", "note": Decimal("1.00"), "description": "Partiellement conforme", "actif": True},
    {"code": "NC", "note": Decimal("-1.00"), "description": "Non conforme", "actif": True},
]

AUDIT_TYPE_FIXTURES = [
    {"code": AuditType.INTERNE, "label": "Audit interne"},
    {"code": AuditType.SITE, "label": "Audit site"},
    {"code": AuditType.POSTE, "label": "Audit de poste"},
    {"code": AuditType.EQUIPEMENT, "label": "Audit équipement"},
]


def load_initial_data() -> None:
    """Insère les fixtures minimales (idempotent)."""
    for item in BAREME_FIXTURES:
        BaremeCotation.objects.update_or_create(code=item["code"], defaults=item)
