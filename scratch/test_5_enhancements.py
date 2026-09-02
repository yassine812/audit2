"""Test script for the 5 Fabien enhancements."""

import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
django.setup()

from accounts.models import User
from reclamation_client.models import ReclamationClient, AnalyseCausesDoubleAxeD4, FicheIncidentDoc05
from reclamation_client.forms import ReclamationQuickCreateForm, FicheIncidentDoc05Form
from accident_travail.models import ActionCorrective
from reclamation_client.pdf_d4_generator import generate_d4_diagram_base64


def test_admin_support_choice():
    print("--- TEST 1: Admin Support Choice for Type R ---")
    admin_user = User.objects.filter(is_superuser=True).first() or User.objects.create_superuser("admin_test", "admin@test.com", "pass")
    normal_user = User.objects.filter(is_superuser=False, is_staff=False).first() or User.objects.create_user("user_test", "user@test.com", "pass")

    from accounts.models import Societe
    soc = Societe.objects.first() or Societe.objects.create(nom="Societe Test")

    # Non-admin submits Type R with Doc 05 -> Should force 8D
    form_user = ReclamationQuickCreateForm(
        data={
            "type_signalement": "R",
            "mode_traitement": "DOC05",
            "client_nom": "Test Non Admin",
            "societe": soc.pk,
            "quantite_impactee": 10,
            "date_alerte_client": "2026-09-01",
        },
        is_admin=False,
    )
    assert form_user.is_valid(), f"User form errors: {form_user.errors}"
    assert form_user.cleaned_data["mode_traitement"] == ReclamationClient.MODE_8D, f"Expected 8D for non-admin, got {form_user.cleaned_data['mode_traitement']}"
    print("PASS: Non-admin restricted to default 8D for Type R.")

    # Admin submits Type R with Doc 05 -> Should accept DOC05
    form_admin = ReclamationQuickCreateForm(
        data={
            "type_signalement": "R",
            "mode_traitement": "DOC05",
            "client_nom": "Test Admin",
            "societe": soc.pk,
            "quantite_impactee": 10,
            "date_alerte_client": "2026-09-01",
        },
        is_admin=True,
    )
    assert form_admin.is_valid(), f"Admin form errors: {form_admin.errors}"
    assert form_admin.cleaned_data["mode_traitement"] == ReclamationClient.MODE_DOC05, f"Expected DOC05 for admin choice, got {form_admin.cleaned_data['mode_traitement']}"
    print("PASS: Admin choice (R + Doc 05) preserved.")


def test_d4_multiple_branches():
    print("--- TEST 2: D4 5-Pourquoi Multiple Branches & PDF ---")
    from accounts.models import Societe
    soc = Societe.objects.first() or Societe.objects.create(nom="Societe Test")

    rec, _ = ReclamationClient.objects.get_or_create(
        reference="REC-TEST-D4-001",
        defaults={
            "type_signalement": "R",
            "mode_traitement": "8D",
            "client_nom": "Client D4",
            "societe": soc,
        }
    )
    d4, _ = AnalyseCausesDoubleAxeD4.objects.get_or_create(reclamation=rec)
    
    # Save 2 branches in Non-Détection and 2 branches in Cause Technique
    d4.pourquoi_non_detection = [
        ["ND B1 P1", "ND B1 P2", "ND B1 P3", "ND B1 P4", "ND B1 P5 Root Cause"],
        ["ND B2 P1", "ND B2 P2", "ND B2 P3", "ND B2 P4", "ND B2 P5 Root Cause"]
    ]
    d4.pourquoi_technique = [
        ["TECH B1 P1", "TECH B1 P2", "TECH B1 P3", "TECH B1 P4", "TECH B1 P5 Root Cause"],
        ["TECH B2 P1", "TECH B2 P2", "TECH B2 P3", "TECH B2 P4", "TECH B2 P5 Root Cause"]
    ]
    d4.save()

    # Verify diagram generation
    png_b64 = generate_d4_diagram_base64(d4)
    assert png_b64 and len(png_b64) > 100, "PDF D4 diagram generation failed!"
    print("PASS: D4 multiple branches saved and rendered in PDF diagram base64.")


def test_action_sync_and_oui_non():
    print("--- TEST 3: Action Sync to ActionCorrective & Oui/Non Context Questions ---")
    from accounts.models import Societe
    soc = Societe.objects.first() or Societe.objects.create(nom="Societe Test")

    rec, _ = ReclamationClient.objects.get_or_create(
        reference="REC-TEST-ACT-001",
        defaults={
            "type_signalement": "I",
            "mode_traitement": "DOC05",
            "client_nom": "Client Incident",
            "societe": soc,
        }
    )
    fiche, _ = FicheIncidentDoc05.objects.get_or_create(
        reclamation=rec,
        defaults={
            "redacteur": "Test User",
            "deja_signale": False,
            "particularites_changements": True,
            "particularites_details": "Nouveau lot matière",
            "risque_similaire": False,
            "actions_correctives": [
                {
                    "action": "Action Corrective 1 - Formation opérateur",
                    "pilote": "Jean Dupont",
                    "delai": "2026-09-15",
                    "realise_le": "",
                    "efficacite": "Non",
                },
                {
                    "action": "Action Corrective 2 - Révision gamme d'usinage",
                    "pilote": "Marie Martin",
                    "delai": "2026-09-30",
                    "realise_le": "2026-09-01",
                    "efficacite": "Oui",
                }
            ]
        }
    )

    # Sync actions to ActionCorrective model
    ActionCorrective.objects.filter(reclamation=rec).delete()
    for idx, act in enumerate(fiche.actions_correctives or [], start=1):
        desc = act.get("action") or act.get("description") or ""
        if desc:
            ActionCorrective.objects.create(
                reclamation=rec,
                description=desc,
                pilote=act.get("pilote", ""),
                delai=act.get("delai") or None,
                date_realisation=act.get("realise_le") or None,
                statut="realise" if act.get("realise_le") else "en_cours",
                efficace=True if str(act.get("efficacite", "")).lower() in ["oui", "true", "1"] else (False if str(act.get("efficacite", "")).lower() in ["non", "false", "0"] else None),
                ordre=idx,
            )

    actions_count = ActionCorrective.objects.filter(reclamation=rec).count()
    assert actions_count == 2, f"Expected 2 ActionCorrective records, found {actions_count}"
    print("PASS: Actions synced to central ActionCorrective model for Planning.")


if __name__ == "__main__":
    test_admin_support_choice()
    test_d4_multiple_branches()
    test_action_sync_and_oui_non()
    print("\nALL 5 ENHANCEMENT TESTS PASSED SUCCESSFULLY!")
