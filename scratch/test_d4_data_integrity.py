"""Test D4 data integrity on brand-new and saved ReclamationClient objects."""

import os
import sys
import json
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
django.setup()

from accounts.models import Societe
from reclamation_client.models import ReclamationClient, AnalyseCausesDoubleAxeD4
from reclamation_client.pdf_d4_generator import generate_d4_diagram_base64

def test_d4_integrity():
    print("==================================================")
    print("TESTING D4 DATA INTEGRITY (NO SAMPLE ANSWERS)")
    print("==================================================\n")

    soc = Societe.objects.first() or Societe.objects.create(nom="Societe D4 Test")

    # 1. Test Brand-New Reclamation
    rec_new = ReclamationClient.objects.create(
        reference="REC8D-D4-NEW",
        type_signalement="R",
        mode_traitement="8D",
        client_nom="Client D4 Test",
        societe=soc,
        quantite_impactee=5,
    )
    d4_new, _ = AnalyseCausesDoubleAxeD4.objects.get_or_create(reclamation=rec_new)

    print(f"Brand-New Reclamation D4.1 ND: {d4_new.pourquoi_non_detection}")
    print(f"Brand-New Reclamation D4.2 Tech: {d4_new.pourquoi_technique}")
    print(f"Brand-New Reclamation D4.1 Synth: '{d4_new.cause_principale_non_detection}'")
    print(f"Brand-New Reclamation D4.2 Synth: '{d4_new.cause_principale_technique}'")

    assert d4_new.pourquoi_non_detection == [], "Brand new D4.1 must be empty list"
    assert d4_new.pourquoi_technique == [], "Brand new D4.2 must be empty list"
    assert d4_new.cause_principale_non_detection == "", "Brand new D4.1 synth must be empty"
    assert d4_new.cause_principale_technique == "", "Brand new D4.2 synth must be empty"

    # 2. Test User Input Saving & Persistence
    user_nd = [["P1 custom ND", "P2 custom ND", "", "", "Root cause P5 ND"]]
    user_tech = [
        ["P1 custom Tech A", "P2 custom Tech A", "P3 Tech A", "", "Root cause P5 Tech A"],
        ["P1 custom Tech B", "", "", "", "Root cause P5 Tech B"],
    ]

    d4_new.pourquoi_non_detection = user_nd
    d4_new.pourquoi_technique = user_tech
    d4_new.cause_principale_non_detection = "Root cause P5 ND"
    d4_new.cause_principale_technique = "Root cause P5 Tech A"
    d4_new.save()

    # 3. Reload from DB
    d4_reloaded = AnalyseCausesDoubleAxeD4.objects.get(reclamation=rec_new)
    print("\n--- Reloaded Saved Reclamation ---")
    print(f"Reloaded D4.1 ND: {d4_reloaded.pourquoi_non_detection}")
    print(f"Reloaded D4.2 Tech: {d4_reloaded.pourquoi_technique}")

    assert d4_reloaded.pourquoi_non_detection == user_nd, "Saved D4.1 must match exact user input"
    assert d4_reloaded.pourquoi_technique == user_tech, "Saved D4.2 must match exact user input"
    assert d4_reloaded.cause_principale_non_detection == "Root cause P5 ND"
    assert d4_reloaded.cause_principale_technique == "Root cause P5 Tech A"

    # 4. Diagram Generator Check
    diag_b64 = generate_d4_diagram_base64(d4_reloaded)
    assert diag_b64.startswith("data:image/png;base64,"), "Diagram generation failed"

    print("\nALL D4 DATA INTEGRITY TESTS PASSED 100%!\n")

if __name__ == "__main__":
    test_d4_integrity()
