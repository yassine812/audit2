"""Test formset validation fixes."""

import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
django.setup()

from accounts.models import User, Societe
from reclamation_client.models import (
    ReclamationClient, DescriptionQQOQCCP, AnalyseCausesDoubleAxeD4,
    CapitalisationSMQSD7, ClotureRecevabiliteD8
)
from reclamation_client.forms import (
    ReclamationHeaderForm, DescriptionQQOQCCPForm, AnalyseCausesDoubleAxeForm,
    CapitalisationSMQSD7Form, ClotureRecevabiliteD8Form, Participant8DFormSet,
    MesureConservatoireD3FormSet, ActionTestD5FormSet, ActionPermanenteD6FormSet
)

def test_browser_post():
    soc = Societe.objects.first() or Societe.objects.create(nom="Test Soc")
    rec, _ = ReclamationClient.objects.get_or_create(
        reference="REC8D-BROWSER-TEST",
        defaults={
            "type_signalement": "R",
            "mode_traitement": "8D",
            "client_nom": "Client Test",
            "societe": soc,
            "quantite_impactee": 10,
            "date_alerte_client": "2026-09-01",
            "date_ouverture": "2026-09-01",
        }
    )

    qqoqccp, _ = DescriptionQQOQCCP.objects.get_or_create(reclamation=rec)
    analyse_d4, _ = AnalyseCausesDoubleAxeD4.objects.get_or_create(reclamation=rec)
    capitalisation_d7, _ = CapitalisationSMQSD7.objects.get_or_create(reclamation=rec)
    cloture_d8, _ = ClotureRecevabiliteD8.objects.get_or_create(reclamation=rec)

    # Browser POST data with empty extra formset rows
    browser_post = {
        "numero_reclamation_client": "REC-123",
        "numero_interne": "INT-123",
        "type_signalement": "R",
        "statut": "brouillon",
        "societe": str(soc.pk),
        "client_nom": "Client Test",
        "quantite_impactee": "10",
        "date_alerte_client": "2026-09-01",
        "date_ouverture": "2026-09-01",

        "statut_recevabilite": "recevable",

        # Participant formset with 1 empty extra row
        "participants-TOTAL_FORMS": "1",
        "participants-INITIAL_FORMS": "0",
        "participants-MIN_NUM_FORMS": "0",
        "participants-MAX_NUM_FORMS": "1000",
        "participants-0-user": "",
        "participants-0-nom_externe": "",
        "participants-0-fonction": "",

        # Mesures D3
        "mesures_d3-TOTAL_FORMS": "0",
        "mesures_d3-INITIAL_FORMS": "0",

        # Action Test D5 formset with 1 empty extra row
        "actions_tests-TOTAL_FORMS": "1",
        "actions_tests-INITIAL_FORMS": "0",
        "actions_tests-MIN_NUM_FORMS": "0",
        "actions_tests-MAX_NUM_FORMS": "1000",
        "actions_tests-0-description_action": "",
        "actions_tests-0-pilote_delai": "",
        "actions_tests-0-conclusion": "",

        # Action Permanente D6 formset with 1 empty extra row (posted with default select options)
        "actions_perm-TOTAL_FORMS": "1",
        "actions_perm-INITIAL_FORMS": "0",
        "actions_perm-MIN_NUM_FORMS": "0",
        "actions_perm-MAX_NUM_FORMS": "1000",
        "actions_perm-0-axe": "technique",
        "actions_perm-0-description": "",
        "actions_perm-0-statut": "non_demarre",
    }

    f_head = ReclamationHeaderForm(browser_post, instance=rec, is_admin=True)
    f_qq = DescriptionQQOQCCPForm(browser_post, instance=qqoqccp)
    f_d4 = AnalyseCausesDoubleAxeForm(browser_post, instance=analyse_d4)
    f_d7 = CapitalisationSMQSD7Form(browser_post, instance=capitalisation_d7)
    f_d8 = ClotureRecevabiliteD8Form(browser_post, instance=cloture_d8)
    fs_part = Participant8DFormSet(browser_post, instance=rec, prefix="participants")
    fs_d3 = MesureConservatoireD3FormSet(browser_post, instance=rec, prefix="mesures_d3")
    fs_test = ActionTestD5FormSet(browser_post, instance=rec, prefix="actions_tests")
    fs_perm = ActionPermanenteD6FormSet(browser_post, instance=rec, prefix="actions_perm")

    print("ReclamationHeaderForm valid:", f_head.is_valid(), f_head.errors)
    print("DescriptionQQOQCCPForm valid:", f_qq.is_valid(), f_qq.errors)
    print("AnalyseCausesDoubleAxeForm valid:", f_d4.is_valid(), f_d4.errors)
    print("CapitalisationSMQSD7Form valid:", f_d7.is_valid(), f_d7.errors)
    print("ClotureRecevabiliteD8Form valid:", f_d8.is_valid(), f_d8.errors)
    print("Participant8DFormSet valid:", fs_part.is_valid(), fs_part.errors)
    print("MesureConservatoireD3FormSet valid:", fs_d3.is_valid(), fs_d3.errors)
    print("ActionTestD5FormSet valid:", fs_test.is_valid(), fs_test.errors)
    print("ActionPermanenteD6FormSet valid:", fs_perm.is_valid(), fs_perm.errors)

if __name__ == "__main__":
    test_browser_post()
