"""Verify submission and saving of Doc 05 record."""

import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
django.setup()

from accounts.models import User, Societe
from reclamation_client.models import ReclamationClient, FicheIncidentDoc05
from reclamation_client.views import reclamation_update_doc05
from django.test import RequestFactory
from django.core.management import call_command


def run_verification():
    print("==================================================")
    print("TESTING DOC 05 SUBMISSION AND SAVE FIX")
    print("==================================================\n")

    rf = RequestFactory()
    soc = Societe.objects.first() or Societe.objects.create(nom="Societe Fix")
    admin_user = User.objects.filter(is_superuser=True).first() or User.objects.create_superuser("admin_fix", "admin_fix@test.com", "pass")

    rec, _ = ReclamationClient.objects.get_or_create(
        reference="REC2609030",
        defaults={
            "type_signalement": "R",
            "mode_traitement": "DOC05",
            "client_nom": "ABC Automotive3",
            "societe": soc,
        }
    )

    # Submit POST with exact dates from user test (02/09/2026 and 03/09/2026)
    post_data = {
        "redacteur": "admin",
        "date_detection": "2026-09-02",
        "date_ouverture": "2026-09-03",
        "site_concerne": "Site Production Tunis",
        "evenement_qualite": "on",
        "quoi_reponse": "Bavures plastiques",
        "qui_reponse": "Opérateur assemblage",
        "ou_reponse": "Poste T3",
        "quand_reponse": "Poste du matin",
        "comment_reponse": "Défaut d'emboitement",
        "combien_reponse": "45 pièces",
        "autre_reponse": "Ref. CP-20",
        "deja_signale": "false",
        "particularites_changements": "true",
        "particularites_details": "Nouveau lot PP",
        "risque_similaire": "false",
    }

    req = rf.post(f"/reclamations/{rec.pk}/doc05/", data=post_data)
    req.user = admin_user

    # Add message storage fallback
    from django.contrib.messages.storage.fallback import FallbackStorage
    setattr(req, 'session', 'session')
    messages = FallbackStorage(req)
    setattr(req, '_messages', messages)

    res = reclamation_update_doc05(req, rec.pk)

    print("Response HTTP Status Code:", res.status_code)
    assert res.status_code in [200, 302], f"Unexpected status code {res.status_code}"

    # Reload from DB and verify saved values
    fiche = FicheIncidentDoc05.objects.get(reclamation=rec)
    print("\nSaved FicheIncidentDoc05 Attributes:")
    print("  - redacteur:", fiche.redacteur)
    print("  - date_detection:", fiche.date_detection)
    print("  - date_ouverture:", fiche.date_ouverture)
    print("  - site_concerne:", fiche.site_concerne)
    print("  - evenement_qualite:", fiche.evenement_qualite)
    print("  - deja_signale:", fiche.deja_signale)
    print("  - particularites_changements:", fiche.particularites_changements)

    assert fiche.redacteur == "admin"
    assert str(fiche.date_detection) == "2026-09-02"
    assert str(fiche.date_ouverture) == "2026-09-03"
    assert fiche.site_concerne == "Site Production Tunis"
    assert fiche.evenement_qualite == True
    assert fiche.deja_signale == False
    assert fiche.particularites_changements == True

    print("\nPASS: Doc 05 record saved and persisted successfully!")

    print("\nRunning django system check...")
    call_command("check")
    print("PASS: System check identified 0 issues.")

if __name__ == "__main__":
    run_verification()
