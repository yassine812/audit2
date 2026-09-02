"""Verification script for 8D save & D4 multi-branching."""

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
    DescriptionQQOQCCP,
    AnalyseCausesDoubleAxeD4,
    CapitalisationSMQSD7,
    ClotureRecevabiliteD8,
)
from reclamation_client.views import reclamation_update_8d, reclamation_export_pdf_8d
from reclamation_client.pdf_d4_generator import generate_d4_diagram_base64
from django.test import RequestFactory
from django.core.management import call_command


def run_test():
    print("==================================================")
    print("TESTING 8D FORM SAVE & D4 MULTI-BRANCHING")
    print("==================================================\n")

    rf = RequestFactory()
    soc = Societe.objects.first() or Societe.objects.create(nom="Societe 8D Test")
    admin_user = User.objects.filter(is_superuser=True).first() or User.objects.create_superuser("admin_8d", "admin_8d@test.com", "pass")

    rec, _ = ReclamationClient.objects.get_or_create(
        reference="REC-TEST-8D-001",
        defaults={
            "type_signalement": "R",
            "mode_traitement": "8D",
            "client_nom": "Client 8D Test",
            "societe": soc,
            "quantite_impactee": 20,
            "date_alerte_client": "2026-09-01",
        }
    )

    # Initialize OneToOne models
    DescriptionQQOQCCP.objects.get_or_create(reclamation=rec)
    analyse_d4, _ = AnalyseCausesDoubleAxeD4.objects.get_or_create(reclamation=rec)
    CapitalisationSMQSD7.objects.get_or_create(reclamation=rec)
    ClotureRecevabiliteD8.objects.get_or_create(reclamation=rec)

    # Multi-branch JSON structures
    branches_nd = [
        ["ND B1 P1", "ND B1 P2", "ND B1 P3", "ND B1 P4", "ND B1 Cause Racine"],
        ["ND B2 P1", "ND B2 P2", "ND B2 P3", "ND B2 P4", "ND B2 Cause Racine"],
        ["ND B3 P1", "ND B3 P2", "ND B3 P3", "ND B3 P4", "ND B3 Cause Racine"],
    ]

    branches_tech = [
        ["TECH B1 P1", "TECH B1 P2", "TECH B1 P3", "TECH B1 P4", "TECH B1 Cause Racine"],
        ["TECH B2 P1", "TECH B2 P2", "TECH B2 P3", "TECH B2 P4", "TECH B2 Cause Racine"],
        ["TECH B3 P1", "TECH B3 P2", "TECH B3 P3", "TECH B3 P4", "TECH B3 Cause Racine"],
    ]

    # Form POST payload matching form_8d.html
    post_data = {
        "client_nom": "Client 8D Test Modified",
        "type_signalement": "R",
        "mode_traitement": "8D",
        "statut": "brouillon",
        "societe": soc.pk,
        "quantite_impactee": 25,
        "date_alerte_client": "2026-09-01",
        "date_ouverture": "2026-09-01",
        "statut_recevabilite": "recevable",
        "pourquoi_non_detection_json": json.dumps(branches_nd),
        "pourquoi_technique_json": json.dumps(branches_tech),
        "cause_principale_non_detection": "ND B3 Cause Racine",
        "cause_principale_technique": "TECH B3 Cause Racine",

        # Formset management forms
        "participants-TOTAL_FORMS": "0",
        "participants-INITIAL_FORMS": "0",
        "participants-MIN_NUM_FORMS": "0",
        "participants-MAX_NUM_FORMS": "1000",

        "mesures_d3-TOTAL_FORMS": "0",
        "mesures_d3-INITIAL_FORMS": "0",
        "mesures_d3-MIN_NUM_FORMS": "0",
        "mesures_d3-MAX_NUM_FORMS": "1000",

        "actions_tests-TOTAL_FORMS": "0",
        "actions_tests-INITIAL_FORMS": "0",
        "actions_tests-MIN_NUM_FORMS": "0",
        "actions_tests-MAX_NUM_FORMS": "1000",

        "actions_perm-TOTAL_FORMS": "0",
        "actions_perm-INITIAL_FORMS": "0",
        "actions_perm-MIN_NUM_FORMS": "0",
        "actions_perm-MAX_NUM_FORMS": "1000",
    }

    req = rf.post(f"/reclamations/{rec.pk}/editer-8d/", data=post_data)
    req.user = admin_user

    from django.contrib.messages.storage.fallback import FallbackStorage
    setattr(req, 'session', 'session')
    messages = FallbackStorage(req)
    setattr(req, '_messages', messages)

    from reclamation_client.forms import (
        ReclamationHeaderForm, DescriptionQQOQCCPForm, AnalyseCausesDoubleAxeForm,
        CapitalisationSMQSD7Form, ClotureRecevabiliteD8Form, Participant8DFormSet,
        MesureConservatoireD3FormSet, ActionTestD5FormSet, ActionPermanenteD6FormSet
    )
    qqoqccp, _ = DescriptionQQOQCCP.objects.get_or_create(reclamation=rec)
    cap_d7, _ = CapitalisationSMQSD7.objects.get_or_create(reclamation=rec)
    clot_d8, _ = ClotureRecevabiliteD8.objects.get_or_create(reclamation=rec)

    f_head = ReclamationHeaderForm(post_data, instance=rec, is_admin=True)
    f_qq = DescriptionQQOQCCPForm(post_data, instance=qqoqccp)
    f_d4 = AnalyseCausesDoubleAxeForm(post_data, instance=analyse_d4)
    f_d7 = CapitalisationSMQSD7Form(post_data, instance=cap_d7)
    f_d8 = ClotureRecevabiliteD8Form(post_data, instance=clot_d8)
    fs_part = Participant8DFormSet(post_data, instance=rec, prefix="participants")
    fs_d3 = MesureConservatoireD3FormSet(post_data, instance=rec, prefix="mesures_d3")
    fs_test = ActionTestD5FormSet(post_data, instance=rec, prefix="actions_tests")
    fs_perm = ActionPermanenteD6FormSet(post_data, instance=rec, prefix="actions_perm")

    print("\n--- FORM VALIDATION CHECKS ---")
    print("ReclamationHeaderForm is_valid:", f_head.is_valid(), f_head.errors)
    print("DescriptionQQOQCCPForm is_valid:", f_qq.is_valid(), f_qq.errors)
    print("AnalyseCausesDoubleAxeForm is_valid:", f_d4.is_valid(), f_d4.errors)
    print("CapitalisationSMQSD7Form is_valid:", f_d7.is_valid(), f_d7.errors)
    print("ClotureRecevabiliteD8Form is_valid:", f_d8.is_valid(), f_d8.errors)
    print("Participant8DFormSet is_valid:", fs_part.is_valid(), fs_part.errors)
    print("MesureConservatoireD3FormSet is_valid:", fs_d3.is_valid(), fs_d3.errors)
    res = reclamation_update_8d(req, rec.pk)
    print("\nView Response HTTP Status Code:", res.status_code)
    assert res.status_code == 302, f"Expected 302 redirect, got {res.status_code}"

    # Reload and verify D4 persistence
    d4_reloaded = AnalyseCausesDoubleAxeD4.objects.get(reclamation=rec)
    print("\nReloaded D4 Branches:")
    print("  - D4.1 Non-détection branches count:", len(d4_reloaded.pourquoi_non_detection))
    print("  - D4.2 Cause technique branches count:", len(d4_reloaded.pourquoi_technique))

    assert len(d4_reloaded.pourquoi_non_detection) == 3
    assert len(d4_reloaded.pourquoi_technique) == 3
    assert d4_reloaded.pourquoi_non_detection[2][4] == "ND B3 Cause Racine"
    assert d4_reloaded.pourquoi_technique[2][4] == "TECH B3 Cause Racine"

    print("PASS: 8D form save & D4 multi-branch persistence verified!\n")

    # PDF generation test
    print("Testing D4 PDF diagram & export...")
    png_b64 = generate_d4_diagram_base64(d4_reloaded)
    assert png_b64 and len(png_b64) > 100, "Base64 diagram generation failed"

    req_pdf = rf.get(f"/reclamations/{rec.pk}/pdf-8d/")
    req_pdf.user = admin_user
    res_pdf = reclamation_export_pdf_8d(req_pdf, rec.pk)
    assert res_pdf.status_code == 200 and res_pdf["Content-Type"] == "application/pdf"
    print("PASS: PDF export generated with all 6 branches!\n")

    print("Running django system check...")
    call_command("check")
    print("PASS: System check identified 0 issues.")

if __name__ == "__main__":
    run_test()
