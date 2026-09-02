"""Test script reproducing the exact Doc 05 validation bug."""

import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
django.setup()

from accounts.models import Societe
from reclamation_client.models import ReclamationClient, FicheIncidentDoc05
from reclamation_client.forms import ReclamationHeaderForm, FicheIncidentDoc05Form

def test_doc05_validation():
    soc = Societe.objects.first() or Societe.objects.create(nom="Test Soc")
    rec, _ = ReclamationClient.objects.get_or_create(
        reference="REC2609030",
        defaults={
            "type_signalement": "R",
            "mode_traitement": "DOC05",
            "client_nom": "ABC Automotive3",
            "societe": soc,
        }
    )
    fiche, _ = FicheIncidentDoc05.objects.get_or_create(reclamation=rec)

    # Simulated POST data sent by form_doc05.html when clicking "Enregistrer la Fiche"
    post_data = {
        "redacteur": "admin",
        "date_detection": "2026-09-02",
        "date_ouverture": "2026-09-03",
        "site_concerne": "Site Production Tunis",
        "evenement_qualite": "on",
    }

    header_form = ReclamationHeaderForm(post_data, instance=rec)
    doc05_form = FicheIncidentDoc05Form(post_data, instance=fiche)

    print("--- VALIDATION RESULTS ---")
    print("doc05_form.is_valid():", doc05_form.is_valid())
    print("doc05_form.errors:", doc05_form.errors)

    print("\nheader_form.is_valid():", header_form.is_valid())
    print("header_form.errors:", header_form.errors)

if __name__ == "__main__":
    test_doc05_validation()
