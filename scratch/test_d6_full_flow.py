import os
import sys
import django

sys.path.insert(0, '.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')
django.setup()

import fitz # PyMuPDF
from django.test import RequestFactory
from accounts.models import User, Societe
from reclamation_client.models import ReclamationClient
from accident_travail.models import ActionCorrective
from reclamation_client.forms import ActionPermanenteD6FormSet
from reclamation_client.views import reclamation_export_pdf_8d, reclamation_update_8d, ReclamationDetailView

def test_full_d6_flow():
    print("==================================================")
    print("RUNNING D6 FULL FLOW PERSISTENCE & PDF VERIFICATION")
    print("==================================================\n")

    user = User.objects.filter(is_superuser=True).first() or User.objects.first()
    soc = Societe.objects.first() or Societe.objects.create(nom="Societe Test D6")

    ReclamationClient.objects.filter(reference="REC8D-D6-VERIF").delete()

    rec = ReclamationClient.objects.create(
        reference="REC8D-D6-VERIF",
        type_signalement="R",
        mode_traitement="8D",
        client_nom="Client D6 Test",
        societe=soc,
        quantite_impactee=10,
        date_alerte_client="2026-09-01",
        date_ouverture="2026-09-01",
    )

    factory = RequestFactory()

    # -----------------------------------------------------------------
    # Test 1: CREATE D6 Action
    # -----------------------------------------------------------------
    print("Test 1 — Create D6 action...")
    post_data_1 = {
        "numero_reclamation_client": "REC-D6-V",
        "type_signalement": "R",
        "statut": "d4_d6",
        "societe": str(soc.pk),
        "client_nom": "Client D6 Test",
        "quantite_impactee": "10",
        "date_alerte_client": "2026-09-01",
        "date_ouverture": "2026-09-01",
        "statut_recevabilite": "recevable",

        "actions_perm-TOTAL_FORMS": "1",
        "actions_perm-INITIAL_FORMS": "0",
        "actions_perm-0-axe": "technique",
        "actions_perm-0-description": "D6 UNIQUE ACTION TEST",
        "actions_perm-0-pilote": "D6 UNIQUE PILOTE",
        "actions_perm-0-delai": "2026-09-03",
        "actions_perm-0-date_realisation": "2026-09-04",
        "actions_perm-0-statut": "en_cours",
        "actions_perm-0-efficace": "True",
    }

    fs_1 = ActionPermanenteD6FormSet(post_data_1, instance=rec, prefix="actions_perm")
    assert fs_1.is_valid(), f"Formset create errors: {fs_1.errors}"
    fs_1.save()

    d6_actions = list(ActionCorrective.objects.filter(reclamation=rec))
    assert len(d6_actions) == 1, f"Expected 1 record in DB, found {len(d6_actions)}"
    action_1 = d6_actions[0]
    assert action_1.description == "D6 UNIQUE ACTION TEST"
    assert action_1.pilote == "D6 UNIQUE PILOTE"
    print(f" -> DB Record verified! desc: '{action_1.description}', pilote: '{action_1.pilote}', delai: '{action_1.delai}', date_real: '{action_1.date_realisation}'")

    # -----------------------------------------------------------------
    # Test 2: RELOAD 8D Editor
    # -----------------------------------------------------------------
    print("\nTest 2 — Reload 8D editor formset...")
    fs_reload = ActionPermanenteD6FormSet(instance=rec, prefix="actions_perm")
    assert len(fs_reload.forms) == 1
    reloaded_form = fs_reload.forms[0]
    assert reloaded_form.initial.get("description") == "D6 UNIQUE ACTION TEST"
    assert reloaded_form.initial.get("pilote") == "D6 UNIQUE PILOTE"
    assert str(reloaded_form.initial.get("delai")) == "2026-09-03"
    assert str(reloaded_form.initial.get("date_realisation")) == "2026-09-04"
    print(" -> Editor reloaded values verified successfully!")

    # -----------------------------------------------------------------
    # Test 3: PDF Generation
    # -----------------------------------------------------------------
    print("\nTest 3 — Generate PDF and verify D6 content...")
    req_pdf = factory.get(f"/reclamation/{rec.pk}/pdf-8d/")
    req_pdf.user = user
    resp_pdf = reclamation_export_pdf_8d(req_pdf, rec.pk)
    assert resp_pdf.status_code == 200, f"PDF generation returned status {resp_pdf.status_code}"
    
    doc = fitz.open(stream=resp_pdf.content, filetype="pdf")
    pdf_text = ""
    for page in doc:
        pdf_text += page.get_text()

    print("Checking text inside PDF...")
    d6_idx = pdf_text.find("D6 -")
    if d6_idx != -1:
        print("--- PDF D6 SNIPPET ---")
        print(pdf_text[d6_idx:d6_idx+600])
        print("----------------------")

    norm_text = " ".join(pdf_text.split())
    assert "D6 UNIQUE ACTION TEST" in norm_text, "ERROR: 'D6 UNIQUE ACTION TEST' missing from generated PDF!"
    assert "D6 UNIQUE PILOTE" in norm_text, "ERROR: 'D6 UNIQUE PILOTE' missing from generated PDF!"
    assert "03/09/2026" in norm_text, "ERROR: '03/09/2026' missing from generated PDF!"
    assert "04/09/2026" in norm_text, "ERROR: '04/09/2026' missing from generated PDF!"
    print(" -> PDF export verified successfully! Saved D6 data appears in PDF!")

    # -----------------------------------------------------------------
    # Test 4: UPDATE D6 Action
    # -----------------------------------------------------------------
    print("\nTest 4 — Update D6 action...")
    post_data_update = {
        "actions_perm-TOTAL_FORMS": "1",
        "actions_perm-INITIAL_FORMS": "1",
        "actions_perm-0-id": str(action_1.pk),
        "actions_perm-0-axe": "technique",
        "actions_perm-0-description": "D6 UPDATED ACTION TEST",
        "actions_perm-0-pilote": "D6 UPDATED PILOTE",
        "actions_perm-0-delai": "2026-09-10",
        "actions_perm-0-date_realisation": "2026-09-12",
        "actions_perm-0-statut": "realise",
    }
    fs_update = ActionPermanenteD6FormSet(post_data_update, instance=rec, prefix="actions_perm")
    assert fs_update.is_valid(), f"Formset update errors: {fs_update.errors}"
    fs_update.save()

    d6_actions_upd = list(ActionCorrective.objects.filter(reclamation=rec))
    assert len(d6_actions_upd) == 1, f"Expected 1 record after update, found {len(d6_actions_upd)}"
    assert d6_actions_upd[0].description == "D6 UPDATED ACTION TEST"

    resp_pdf_upd = reclamation_export_pdf_8d(req_pdf, rec.pk)
    doc_upd = fitz.open(stream=resp_pdf_upd.content, filetype="pdf")
    pdf_text_upd = "".join([p.get_text() for p in doc_upd])
    norm_text_upd = " ".join(pdf_text_upd.split())
    assert "D6 UPDATED ACTION TEST" in norm_text_upd
    assert "D6 UPDATED PILOTE" in norm_text_upd
    assert "10/09/2026" in norm_text_upd
    assert "12/09/2026" in norm_text_upd
    print(" -> Update verified! Database count remains 1 and PDF reflects updated values!")

    # -----------------------------------------------------------------
    # Test 5: DELETE D6 Action
    # -----------------------------------------------------------------
    print("\nTest 5 — Delete D6 action...")
    post_data_del = {
        "actions_perm-TOTAL_FORMS": "1",
        "actions_perm-INITIAL_FORMS": "1",
        "actions_perm-0-id": str(action_1.pk),
        "actions_perm-0-description": "D6 UPDATED ACTION TEST",
        "actions_perm-0-DELETE": "on",
    }
    fs_del = ActionPermanenteD6FormSet(post_data_del, instance=rec, prefix="actions_perm")
    assert fs_del.is_valid(), f"Formset delete errors: {fs_del.errors}"
    fs_del.save()

    assert ActionCorrective.objects.filter(reclamation=rec).count() == 0
    print(" -> Deletion verified! DB count is 0.")

    # -----------------------------------------------------------------
    # Test 6: Empty extra rows test
    # -----------------------------------------------------------------
    print("\nTest 6 — Empty extra rows test...")
    post_data_empty = {
        "actions_perm-TOTAL_FORMS": "2",
        "actions_perm-INITIAL_FORMS": "0",
        "actions_perm-0-axe": "technique",
        "actions_perm-0-description": "",
        "actions_perm-0-pilote": "",
        "actions_perm-1-axe": "technique",
        "actions_perm-1-description": "",
        "actions_perm-1-pilote": "",
    }
    fs_empty = ActionPermanenteD6FormSet(post_data_empty, instance=rec, prefix="actions_perm")
    assert fs_empty.is_valid(), f"Empty formset errors: {fs_empty.errors}"
    fs_empty.save()

    assert ActionCorrective.objects.filter(reclamation=rec).count() == 0
    print(" -> Empty rows ignored cleanly! No database records created.")

    print("\n==================================================")
    print("ALL D6 FULL FLOW TESTS PASSED SUCCESSFULLY!")
    print("==================================================\n")

if __name__ == "__main__":
    test_full_d6_flow()
