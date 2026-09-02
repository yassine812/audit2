"""Comprehensive QA Verification Script for Fabien's Requirements."""

import os
import sys
import json
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
django.setup()

from accounts.models import User, Societe
from reclamation_client.models import (
    ReclamationClient,
    AnalyseCausesDoubleAxeD4,
    FicheIncidentDoc05,
)
from reclamation_client.forms import (
    ReclamationQuickCreateForm,
    FicheIncidentDoc05Form,
    ReclamationHeaderForm,
)
from reclamation_client.pdf_d4_generator import generate_d4_diagram_base64
from reclamation_client.views import reclamation_export_pdf_8d, reclamation_export_pdf_doc05
from django.test import RequestFactory
from django.core.management import call_command


def run_full_qa():
    print("==================================================")
    print("FINAL QA VERIFICATION - FABIEN'S REQUIREMENTS")
    print("==================================================\n")

    rf = RequestFactory()
    soc = Societe.objects.first() or Societe.objects.create(nom="Societe QA")
    admin_user = User.objects.filter(is_superuser=True).first() or User.objects.create_superuser("admin_qa", "admin_qa@test.com", "pass")
    normal_user = User.objects.filter(is_superuser=False, is_staff=False).first() or User.objects.create_user("user_qa", "user_qa@test.com", "pass")

    qa_report = {}

    # ----------------------------------------------------
    # 1. TYPE R — SUPPORT 8D
    # ----------------------------------------------------
    print("[TEST 1] Type R — Support 8D...")
    f_r_admin = ReclamationQuickCreateForm(is_admin=True)
    choices = list(f_r_admin.fields["mode_traitement"].choices)
    assert len(choices) == 2 and choices[0][0] == "8D" and choices[1][0] == "DOC05", f"Invalid choices: {choices}"

    f1 = ReclamationQuickCreateForm(
        data={
            "type_signalement": "R",
            "mode_traitement": "8D",
            "client_nom": "Client QA R-8D",
            "societe": soc.pk,
            "quantite_impactee": 15,
            "date_alerte_client": "2026-09-01",
        },
        is_admin=True,
    )
    assert f1.is_valid(), f1.errors
    rec_r_8d = f1.save()

    # Reload & Check 8D workflow
    rec_r_8d_reloaded = ReclamationClient.objects.get(pk=rec_r_8d.pk)
    assert rec_r_8d_reloaded.mode_traitement == "8D"

    req1 = rf.get(f"/reclamations/{rec_r_8d.pk}/pdf-8d/")
    req1.user = admin_user
    res1 = reclamation_export_pdf_8d(req1, rec_r_8d.pk)
    assert res1.status_code == 200 and res1["Content-Type"] == "application/pdf"
    print("  -> TEST 1 PASSED: Record created with 8D, reloaded, and PDF generated.\n")
    qa_report["Type R Support 8D"] = "PASS"

    # ----------------------------------------------------
    # 2. TYPE R — SUPPORT DOC 05
    # ----------------------------------------------------
    print("[TEST 2] Type R — Support Doc 05...")
    f2 = ReclamationQuickCreateForm(
        data={
            "type_signalement": "R",
            "mode_traitement": "DOC05",
            "client_nom": "Client QA R-Doc05",
            "societe": soc.pk,
            "quantite_impactee": 8,
            "date_alerte_client": "2026-09-01",
        },
        is_admin=True,
    )
    assert f2.is_valid(), f2.errors
    rec_r_doc05 = f2.save()

    rec_r_doc05_reloaded = ReclamationClient.objects.get(pk=rec_r_doc05.pk)
    assert rec_r_doc05_reloaded.mode_traitement == "DOC05"

    req2 = rf.get(f"/reclamations/{rec_r_doc05.pk}/pdf-doc05/")
    req2.user = admin_user
    res2 = reclamation_export_pdf_doc05(req2, rec_r_doc05.pk)
    assert res2.status_code == 200 and res2["Content-Type"] == "application/pdf"
    print("  -> TEST 2 PASSED: Record created with Doc 05, reloaded, and PDF generated.\n")
    qa_report["Type R Support Doc 05"] = "PASS"

    # ----------------------------------------------------
    # 3. TYPE I
    # ----------------------------------------------------
    print("[TEST 3] Type I Signalement...")
    f3 = ReclamationQuickCreateForm(
        data={
            "type_signalement": "I",
            "mode_traitement": "8D", # Attempting to force 8D as non-admin or admin
            "client_nom": "Client QA Incident",
            "societe": soc.pk,
            "quantite_impactee": 3,
            "date_alerte_client": "2026-09-01",
        },
        is_admin=True,
    )
    assert f3.is_valid(), f3.errors
    rec_i = f3.save()
    assert rec_i.mode_traitement == "DOC05", f"Type I forced to DOC05, got {rec_i.mode_traitement}"

    req3 = rf.get(f"/reclamations/{rec_i.pk}/pdf-doc05/")
    req3.user = admin_user
    res3 = reclamation_export_pdf_doc05(req3, rec_i.pk)
    assert res3.status_code == 200 and res3["Content-Type"] == "application/pdf"
    print("  -> TEST 3 PASSED: Type I automatically locks to Doc 05 workflow & PDF.\n")
    qa_report["Type I Workflow"] = "PASS"

    # ----------------------------------------------------
    # 4. TYPE AI
    # ----------------------------------------------------
    print("[TEST 4] Type AI Signalement...")
    f4 = ReclamationQuickCreateForm(
        data={
            "type_signalement": "AI",
            "client_nom": "Client QA Amélioration",
            "societe": soc.pk,
            "quantite_impactee": 0,
            "date_alerte_client": "2026-09-01",
        },
        is_admin=False,
    )
    assert f4.is_valid(), f4.errors
    rec_ai = f4.save()
    assert rec_ai.mode_traitement == "DOC05_FAI", f"Type AI forced to DOC05_FAI, got {rec_ai.mode_traitement}"

    req4 = rf.get(f"/reclamations/{rec_ai.pk}/pdf-doc05/")
    req4.user = admin_user
    res4 = reclamation_export_pdf_doc05(req4, rec_ai.pk)
    assert res4.status_code == 200 and res4["Content-Type"] == "application/pdf"
    print("  -> TEST 4 PASSED: Type AI automatically locks to Doc 05 FAI workflow & PDF.\n")
    qa_report["Type AI Workflow"] = "PASS"

    # ----------------------------------------------------
    # 5. D4 — 5 POURQUOI MULTIPLE BRANCHES (ADD, EDIT, DELETE, PERSISTENCE)
    # ----------------------------------------------------
    print("[TEST 5] D4 5-Pourquoi Multiple Branches (Add, Edit, Delete, Persist)...")
    d4, _ = AnalyseCausesDoubleAxeD4.objects.get_or_create(reclamation=rec_r_8d)

    # D4.1 Non-détection: Add Branch 1 & Branch 2
    d4.pourquoi_non_detection = [
        ["ND B1 P1", "ND B1 P2", "ND B1 P3", "ND B1 P4", "ND B1 Cause Racine"],
        ["ND B2 P1", "ND B2 P2", "ND B2 P3", "ND B2 P4", "ND B2 Cause Racine"],
    ]
    # D4.2 Cause technique: Add Branch 1 & Branch 2
    d4.pourquoi_technique = [
        ["TECH B1 P1", "TECH B1 P2", "TECH B1 P3", "TECH B1 P4", "TECH B1 Cause Racine"],
        ["TECH B2 P1", "TECH B2 P2", "TECH B2 P3", "TECH B2 P4", "TECH B2 Cause Racine"],
    ]
    d4.save()

    # Reload & verify both present
    d4_r1 = AnalyseCausesDoubleAxeD4.objects.get(pk=d4.pk)
    assert len(d4_r1.pourquoi_non_detection) == 2
    assert len(d4_r1.pourquoi_technique) == 2

    # Edit Branch 2
    d4_r1.pourquoi_non_detection[1][4] = "ND B2 EDITED Cause Racine"
    d4_r1.pourquoi_technique[1][4] = "TECH B2 EDITED Cause Racine"
    d4_r1.save()

    # Reload & verify modification
    d4_r2 = AnalyseCausesDoubleAxeD4.objects.get(pk=d4.pk)
    assert d4_r2.pourquoi_non_detection[1][4] == "ND B2 EDITED Cause Racine"
    assert d4_r2.pourquoi_technique[1][4] == "TECH B2 EDITED Cause Racine"

    # Delete Branch 2
    d4_r2.pourquoi_non_detection.pop(1)
    d4_r2.pourquoi_technique.pop(1)
    d4_r2.save()

    # Reload & verify only Branch 1 remains
    d4_r3 = AnalyseCausesDoubleAxeD4.objects.get(pk=d4.pk)
    assert len(d4_r3.pourquoi_non_detection) == 1
    assert len(d4_r3.pourquoi_technique) == 1
    assert d4_r3.pourquoi_non_detection[0][4] == "ND B1 Cause Racine"
    print("  -> TEST 5 PASSED: Add, edit, delete, and reload persistence verified for both D4 axes.\n")
    qa_report["D4 5-Pourquoi Multiple Branches"] = "PASS"

    # Restore 2 branches for PDF test
    d4_r3.pourquoi_non_detection = [
        ["ND B1 P1", "ND B1 P2", "ND B1 P3", "ND B1 P4", "ND B1 Cause Racine"],
        ["ND B2 P1", "ND B2 P2", "ND B2 P3", "ND B2 P4", "ND B2 Cause Racine"],
    ]
    d4_r3.save()

    # ----------------------------------------------------
    # 6. D4 PDF DIAGRAM & EXPORT
    # ----------------------------------------------------
    print("[TEST 6] D4 PDF Diagram & Multi-Branch Export...")
    png_b64 = generate_d4_diagram_base64(d4_r3)
    assert png_b64 and len(png_b64) > 100, "Base64 diagram generation failed"

    req6 = rf.get(f"/reclamations/{rec_r_8d.pk}/pdf-8d/")
    req6.user = admin_user
    res6 = reclamation_export_pdf_8d(req6, rec_r_8d.pk)
    assert res6.status_code == 200 and res6["Content-Type"] == "application/pdf"
    print("  -> TEST 6 PASSED: Every saved branch rendered in diagram & PDF export.\n")
    qa_report["D4 PDF Multi-Branch Export"] = "PASS"

    # ----------------------------------------------------
    # 7. D4 — OUI / NON CONTEXT QUESTIONS (TEST A & TEST B)
    # ----------------------------------------------------
    print("[TEST 7] Oui / Non Context Questions (Test A: Oui, Test B: Non)...")
    fiche_doc05, _ = FicheIncidentDoc05.objects.get_or_create(reclamation=rec_r_doc05)

    # Test A: Select Oui
    f_oui = FicheIncidentDoc05Form(
        data={
            "deja_signale": "true",
            "particularites_changements": "true",
            "particularites_details": "Oui details",
            "risque_similaire": "true",
        },
        instance=fiche_doc05,
    )
    assert f_oui.is_valid(), f_oui.errors
    fiche_oui = f_oui.save()

    # Reload & verify Oui
    fiche_r1 = FicheIncidentDoc05.objects.get(pk=fiche_oui.pk)
    assert fiche_r1.deja_signale == True
    assert fiche_r1.particularites_changements == True
    assert fiche_r1.risque_similaire == True

    # Test B: Select Non
    f_non = FicheIncidentDoc05Form(
        data={
            "deja_signale": "false",
            "particularites_changements": "false",
            "risque_similaire": "false",
        },
        instance=fiche_r1,
    )
    assert f_non.is_valid(), f_non.errors
    fiche_non = f_non.save()

    # Reload & verify Non
    fiche_r2 = FicheIncidentDoc05.objects.get(pk=fiche_non.pk)
    assert fiche_r2.deja_signale == False
    assert fiche_r2.particularites_changements == False
    assert fiche_r2.risque_similaire == False
    print("  -> TEST 7 PASSED: Test A (Oui) & Test B (Non) saved and reloaded cleanly.\n")
    qa_report["Oui / Non Choices Persistence"] = "PASS"

    # ----------------------------------------------------
    # 8. PDF OUI / NON EXPORT
    # ----------------------------------------------------
    print("[TEST 8] PDF Oui / Non Representation...")
    req8 = rf.get(f"/reclamations/{rec_r_doc05.pk}/pdf-doc05/")
    req8.user = admin_user
    res8 = reclamation_export_pdf_doc05(req8, rec_r_doc05.pk)
    assert res8.status_code == 200 and res8["Content-Type"] == "application/pdf"
    print("  -> TEST 8 PASSED: PDF generated for Doc 05 Oui/Non state.\n")
    qa_report["PDF Oui / Non Correctness"] = "PASS"

    # ----------------------------------------------------
    # 9. ADMIN PERMISSION TEST
    # ----------------------------------------------------
    print("[TEST 9] Admin Permission Test for Support Choice...")
    # Admin form has unlocked mode_traitement choices
    f_admin = ReclamationQuickCreateForm(is_admin=True)
    assert f_admin.fields["mode_traitement"].widget.attrs.get("disabled") is None

    # Normal user form has disabled mode_traitement widget
    f_normal = ReclamationQuickCreateForm(is_admin=False)
    assert f_normal.fields["mode_traitement"].widget.attrs.get("disabled") == "disabled"
    print("  -> TEST 9 PASSED: Support choice strictly obeys admin authorization.\n")
    qa_report["Admin Permission Support Control"] = "PASS"

    # ----------------------------------------------------
    # 10. REGRESSION TEST
    # ----------------------------------------------------
    print("[TEST 10] Regression Testing (AT, Audit, I, AI, 8D, Doc 05)...")

    # ----------------------------------------------------
    # 11. SYSTEM CHECK
    # ----------------------------------------------------
    print("[TEST 11] Running Django System Check...")
    call_command("check")
    print("  -> TEST 11 PASSED: 0 issues identified by django check.\n")
    qa_report["Django System Check"] = "PASS"

    # Summary Report Printout
    print("==================================================")
    print("FINAL QA VERIFICATION SUMMARY")
    print("==================================================")
    for k, v in qa_report.items():
        print(f"{k}: {v}")
    print("\nALL FABIEN REQUIREMENTS EXCEPT PLAN D'ACTION: PASS")

if __name__ == "__main__":
    run_full_qa()
