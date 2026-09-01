import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
django.setup()

from django.test import RequestFactory
from django.contrib.auth import get_user_model
from django.db import transaction
from reclamation_client.models import ReclamationClient, FicheIncidentDoc05
from reclamation_client.views import (
    reclamation_export_pdf_8d,
    reclamation_export_pdf_doc05,
    reclamation_update_8d,
    reclamation_update_doc05,
)
from reclamation_client.forms import ReclamationQuickCreateForm
from accounts.models import Societe
from django.contrib.messages.storage.fallback import FallbackStorage

User = get_user_model()
user = User.objects.first()
societe, _ = Societe.objects.get_or_create(nom="AB Serve Test")
factory = RequestFactory()

# Wrap execution so test records are created temporarily and deleted immediately afterwards
created_test_ids = []

try:
    # Form Validation Test: Browser submits WITHOUT mode_traitement because disabled select is omitted
    form_data = {
        "type_signalement": "I",
        "societe": societe.pk,
        "client_nom": "Form Test Client",
        "quantite_impactee": 1,
        "date_alerte_client": "2026-09-01",
    }
    form = ReclamationQuickCreateForm(data=form_data)
    is_valid = form.is_valid()
    print(f"[TEST FORM] Form valid without mode_traitement in POST: {is_valid}")
    assert is_valid
    assert form.cleaned_data["mode_traitement"] == "DOC05"

    # Test 1: Create R (Réclamation Qualité)
    rec_r = ReclamationClient.objects.create(
        type_signalement=ReclamationClient.TYPE_RECLAMATION,
        mode_traitement="INVALID_MODE",
        client_nom="TEMP_TEST_R",
        societe=societe,
        created_by=user,
    )
    created_test_ids.append(rec_r.pk)
    print(f"[TEST 1] Type R -> mode_traitement: {rec_r.mode_traitement} (Expected: 8D)")
    assert rec_r.mode_traitement == ReclamationClient.MODE_8D

    # Test 2: Create I (Incident Client)
    rec_i = ReclamationClient.objects.create(
        type_signalement=ReclamationClient.TYPE_INCIDENT,
        mode_traitement="8D",
        client_nom="TEMP_TEST_I",
        societe=societe,
        created_by=user,
    )
    created_test_ids.append(rec_i.pk)
    fiche_i, _ = FicheIncidentDoc05.objects.get_or_create(reclamation=rec_i)
    print(f"[TEST 2] Type I -> mode_traitement: {rec_i.mode_traitement} (Expected: DOC05)")
    assert rec_i.mode_traitement == ReclamationClient.MODE_DOC05
    assert fiche_i is not None

    # Test 3: Create AI (Amélioration Interne)
    rec_ai = ReclamationClient.objects.create(
        type_signalement=ReclamationClient.TYPE_AMELIORATION,
        mode_traitement="8D",
        client_nom="TEMP_TEST_AI",
        societe=societe,
        created_by=user,
    )
    created_test_ids.append(rec_ai.pk)
    fiche_ai, _ = FicheIncidentDoc05.objects.get_or_create(reclamation=rec_ai)
    print(f"[TEST 3] Type AI -> mode_traitement: {rec_ai.mode_traitement} (Expected: DOC05_FAI)")
    assert rec_ai.mode_traitement == ReclamationClient.MODE_DOC05_FAI
    assert fiche_ai is not None

    # Test 4: PDF Exports
    req = factory.get(f"/reclamations/{rec_r.pk}/export-pdf-8d/")
    req.user = user
    resp_pdf_r = reclamation_export_pdf_8d(req, rec_r.pk)
    print(f"[TEST 4] PDF 8D Export Status: {resp_pdf_r.status_code}, Content-Type: {resp_pdf_r.get('Content-Type')}")
    assert resp_pdf_r.status_code == 200
    assert "application/pdf" in resp_pdf_r.get("Content-Type")

    req = factory.get(f"/reclamations/{rec_i.pk}/export-pdf-doc05/")
    req.user = user
    resp_pdf_i = reclamation_export_pdf_doc05(req, rec_i.pk)
    print(f"[TEST 5] PDF Doc05 (Incident) Export Status: {resp_pdf_i.status_code}, Content-Type: {resp_pdf_i.get('Content-Type')}")
    assert resp_pdf_i.status_code == 200
    assert "application/pdf" in resp_pdf_i.get("Content-Type")

    req = factory.get(f"/reclamations/{rec_ai.pk}/export-pdf-doc05/")
    req.user = user
    resp_pdf_ai = reclamation_export_pdf_doc05(req, rec_ai.pk)
    print(f"[TEST 6] PDF Doc05 (FAI) Export Status: {resp_pdf_ai.status_code}, Content-Type: {resp_pdf_ai.get('Content-Type')}")
    assert resp_pdf_ai.status_code == 200
    assert "application/pdf" in resp_pdf_ai.get("Content-Type")

    # Test 5: Route Enforcement Redirects
    req = factory.get(f"/reclamations/{rec_i.pk}/editer-8d/")
    req.user = user
    req.session = {}
    setattr(req, '_messages', FallbackStorage(req))
    resp_redirect = reclamation_update_8d(req, rec_i.pk)
    print(f"[TEST 7] Accessing 8D Editor for Incident record -> Redirect Status: {resp_redirect.status_code}, Target: {resp_redirect.url}")
    assert resp_redirect.status_code == 302

    print("--- ALL WORKFLOW TESTS PASSED PERFECTLY! ---")

finally:
    if created_test_ids:
        ReclamationClient.objects.filter(pk__in=created_test_ids).delete()
        print(f"[CLEANUP] Deleted temporary test records: {created_test_ids}")
