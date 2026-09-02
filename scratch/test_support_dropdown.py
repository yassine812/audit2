"""Unit test verifying Type R Support dropdown options and persistence."""

import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
django.setup()

from accounts.models import Societe
from reclamation_client.models import ReclamationClient
from reclamation_client.forms import ReclamationQuickCreateForm, ReclamationHeaderForm
from django.core.management import call_command


def run_tests():
    print("==================================================")
    print("VERIFYING TYPE R SUPPORT DROPDOWN & PERSISTENCE")
    print("==================================================\n")

    soc = Societe.objects.first() or Societe.objects.create(nom="Societe Test Dropdown")

    # Step 1: Open creation form as Administrator
    form_admin = ReclamationQuickCreateForm(is_admin=True)
    choices = list(form_admin.fields["mode_traitement"].choices)

    print("Step 1 & 2: Form choices for Admin user:")
    for val, label in choices:
        print(f"  - {val}: {label}")

    assert len(choices) == 2, f"Expected exactly 2 choices, got {len(choices)}: {choices}"
    assert choices[0] == (ReclamationClient.MODE_8D, "Rapport 8D"), f"Unexpected choice 0: {choices[0]}"
    assert choices[1] == (ReclamationClient.MODE_DOC05, "Fiche d'incident (Doc 05)"), f"Unexpected choice 1: {choices[1]}"
    print("PASS: Exactly TWO options displayed for Type R (Rapport 8D and Fiche d'incident (Doc 05)).\n")

    # Step 3: Test selecting Rapport 8D
    form_8d = ReclamationQuickCreateForm(
        data={
            "type_signalement": "R",
            "mode_traitement": "8D",
            "client_nom": "Client Test 8D",
            "societe": soc.pk,
            "quantite_impactee": 10,
            "date_alerte_client": "2026-09-01",
        },
        is_admin=True,
    )
    assert form_8d.is_valid(), form_8d.errors
    rec_8d = form_8d.save()
    print(f"Step 3: Created Type R with 8D -> Reference: {rec_8d.reference}")

    # Step 4: Test selecting Fiche d'incident (Doc 05)
    form_doc05 = ReclamationQuickCreateForm(
        data={
            "type_signalement": "R",
            "mode_traitement": "DOC05",
            "client_nom": "Client Test Doc05",
            "societe": soc.pk,
            "quantite_impactee": 5,
            "date_alerte_client": "2026-09-01",
        },
        is_admin=True,
    )
    assert form_doc05.is_valid(), form_doc05.errors
    rec_doc05 = form_doc05.save()
    print(f"Step 4: Created Type R with Doc 05 -> Reference: {rec_doc05.reference}")

    # Step 5: Reload from DB and verify persistence
    rec_8d_reloaded = ReclamationClient.objects.get(pk=rec_8d.pk)
    rec_doc05_reloaded = ReclamationClient.objects.get(pk=rec_doc05.pk)

    assert rec_8d_reloaded.mode_traitement == "8D", f"Expected 8D, got {rec_8d_reloaded.mode_traitement}"
    assert rec_doc05_reloaded.mode_traitement == "DOC05", f"Expected DOC05, got {rec_doc05_reloaded.mode_traitement}"

    print(f"Step 5: Persisted values after reload:")
    print(f"  - {rec_8d_reloaded.reference}: mode_traitement = {rec_8d_reloaded.mode_traitement} (8D)")
    print(f"  - {rec_doc05_reloaded.reference}: mode_traitement = {rec_doc05_reloaded.mode_traitement} (DOC05)")
    print("PASS: Both selections saved and persisted correctly upon reload.\n")

    # Step 6: Run Django System Check
    print("Step 6: Running manage.py check...")
    call_command("check")
    print("PASS: System check identified 0 issues.\n")

    print("ALL TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    run_tests()
