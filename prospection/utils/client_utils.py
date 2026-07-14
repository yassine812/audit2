"""Résolution de la base Sage (WebServices100) pour une société donnée."""
import unicodedata


def _normalize(name: str) -> str:
    name = unicodedata.normalize("NFKD", name or "").encode("ascii", "ignore").decode()
    return name.upper().replace(" ", "").replace("-", "").replace("_", "")


def get_base_url(societe_id):
    """Get the base URL based on societe_id.

    Résolution :
    1. Mapping historique par ID (3/4/6) conservé pour compatibilité.
    2. Sinon, résolution par le nom de la société en base
       (ex.: "AB Serve Tunisie" → "ABSERVE_TUNISIE").
    """
    base_map = {
        3: "ABSERVE_TUNISIE",
        4: "ABSERVE",
        6: "QFZ",
    }
    if societe_id in base_map:
        return base_map[societe_id]

    if not societe_id:
        return None

    try:
        from accounts.models import Societe
        societe = Societe.objects.filter(id=societe_id).first()
    except Exception:
        return None
    if not societe:
        return None

    norm = _normalize(societe.nom)
    if "QFZ" in norm:
        return "QFZ"
    if "TUNISIE" in norm:
        return "ABSERVE_TUNISIE"
    if "ABSERVE" in norm:
        return "ABSERVE"
    return None
