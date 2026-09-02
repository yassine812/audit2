"""Test POSTing the 8D form for Reclamation 115 to find validation failures."""

import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
django.setup()

from reclamation_client.models import (
    ReclamationClient,
    DescriptionQQOQCCP,
    AnalyseCausesDoubleAxeD4,
    CapitalisationSMQSD7,
    ClotureRecevabiliteD8,
    MesureConservatoireD3,
)
from reclamation_client.forms import (
    ReclamationHeaderForm,
    DescriptionQQOQCCPForm,
    AnalyseCausesDoubleAxeForm,
    CapitalisationSMQSD7Form,
    ClotureRecevabiliteD8Form,
    Participant8DFormSet,
    MesureConservatoireD3FormSet,
    ActionTestD5FormSet,
    ActionPermanenteD6FormSet,
)

def test_post():
    rec = ReclamationClient.objects.get(pk=115)
    
    # Ensure D3 records exist
    for t in ["tri_interne", "tri_externe", "repere_unitaire", "autre"]:
        MesureConservatoireD3.objects.get_or_create(reclamation=rec, type_mesure=t)

    # Simulate user post data with 1 row in D1, D5, D6, plus extra blank rows
    post_data = {
        # Header
        "numero_reclamation_client": rec.numero_reclamation_client or "REC2609037",
        "type_signalement": rec.type_signalement or "R",
        "statut": "brouillon",
        "societe": str(rec.societe_id),
        "client_nom": rec.client_nom or "Client QA Live Formset Test",
        "quantite_impactee": "10",
        "date_alerte_client": "2026-09-01",
        "date_ouverture": "2026-09-01",

        # D1 Formset (1 row filled, 1 empty)
        "participants-TOTAL_FORMS": "2",
        "participants-INITIAL_FORMS": "0",
        "participants-0-user": "",
        "participants-0-nom_externe": "",
        "participants-0-fonction": "qqq",
        "participants-0-est_pilote": "on",
        "participants-1-user": "",
        "participants-1-nom_externe": "",
        "participants-1-fonction": "",

        # D3 Formset
        "mesures_d3-TOTAL_FORMS": "4",
        "mesures_d3-INITIAL_FORMS": "4",

        # D5 Formset (1 row filled, 1 empty)
        "actions_tests-TOTAL_FORMS": "2",
        "actions_tests-INITIAL_FORMS": "0",
        "actions_tests-0-description_action": "jjjj",
        "actions_tests-0-pilote_delai": "jjjj",
        "actions_tests-0-conclusion": "jjj",
        "actions_tests-1-description_action": "",
        "actions_tests-1-pilote_delai": "",
        "actions_tests-1-conclusion": "",

        # D6 Formset (1 row filled, 2 empty)
        "actions_perm-TOTAL_FORMS": "3",
        "actions_perm-INITIAL_FORMS": "0",
        "actions_perm-0-axe": "technique",
        "actions_perm-0-description": "jjj",
        "actions_perm-0-pilote": "jjjj",
        "actions_perm-0-delai": "2026-09-01",
        "actions_perm-0-date_realisation": "2026-09-02",
        "actions_perm-0-statut": "en_cours",
        "actions_perm-0-efficace": "True",
        "actions_perm-0-audit_poste_doc37": "on",

        "actions_perm-1-axe": "technique",
        "actions_perm-1-description": "",
        "actions_perm-1-pilote": "",
        "actions_perm-1-statut": "non_demarre",

        "actions_perm-2-axe": "technique",
        "actions_perm-2-description": "",
        "actions_perm-2-pilote": "",
        "actions_perm-2-statut": "non_demarre",

        # D8
        "statut_recevabilite": "recevable",
    }

    mesures_d3_list = list(rec.mesures_conservatoires.all().order_by("pk"))
    for idx, m in enumerate(mesures_d3_list):
        post_data[f"mesures_d3-{idx}-id"] = str(m.pk)
        post_data[f"mesures_d3-{idx}-type_mesure"] = m.type_mesure

    analyse_d4, _ = AnalyseCausesDoubleAxeD4.objects.get_or_create(reclamation=rec)
    capitalisation_d7, _ = CapitalisationSMQSD7.objects.get_or_create(reclamation=rec)
    cloture_d8, _ = ClotureRecevabiliteD8.objects.get_or_create(reclamation=rec)
    qqoqccp, _ = DescriptionQQOQCCP.objects.get_or_create(reclamation=rec)

    header_form = ReclamationHeaderForm(post_data, instance=rec, is_admin=True)
    qqoqccp_form = DescriptionQQOQCCPForm(post_data, instance=qqoqccp)
    analyse_d4_form = AnalyseCausesDoubleAxeForm(post_data, instance=analyse_d4)
    capitalisation_d7_form = CapitalisationSMQSD7Form(post_data, instance=capitalisation_d7)
    cloture_d8_form = ClotureRecevabiliteD8Form(post_data, instance=cloture_d8)

    participants_formset = Participant8DFormSet(post_data, instance=rec, prefix="participants")
    mesures_d3_formset = MesureConservatoireD3FormSet(post_data, instance=rec, prefix="mesures_d3")
    actions_tests_formset = ActionTestD5FormSet(post_data, instance=rec, prefix="actions_tests")
    actions_permanentes_formset = ActionPermanenteD6FormSet(post_data, instance=rec, prefix="actions_perm")

    print(f"header_form valid: {header_form.is_valid()} -> {header_form.errors}")
    print(f"qqoqccp_form valid: {qqoqccp_form.is_valid()} -> {qqoqccp_form.errors}")
    print(f"analyse_d4_form valid: {analyse_d4_form.is_valid()} -> {analyse_d4_form.errors}")
    print(f"capitalisation_d7_form valid: {capitalisation_d7_form.is_valid()} -> {capitalisation_d7_form.errors}")
    print(f"cloture_d8_form valid: {cloture_d8_form.is_valid()} -> {cloture_d8_form.errors}")
    print(f"participants_formset valid: {participants_formset.is_valid()} -> errors: {participants_formset.errors}")
    print(f"mesures_d3_formset valid: {mesures_d3_formset.is_valid()} -> errors: {mesures_d3_formset.errors}")
    print(f"actions_tests_formset valid: {actions_tests_formset.is_valid()} -> errors: {actions_tests_formset.errors}")
    print(f"actions_permanentes_formset valid: {actions_permanentes_formset.is_valid()} -> errors: {actions_permanentes_formset.errors}")

    all_valid = (
        header_form.is_valid() and qqoqccp_form.is_valid() and
        analyse_d4_form.is_valid() and capitalisation_d7_form.is_valid() and
        cloture_d8_form.is_valid() and participants_formset.is_valid() and
        mesures_d3_formset.is_valid() and actions_tests_formset.is_valid() and
        actions_permanentes_formset.is_valid()
    )
    print(f"\nOVERALL POST VALIDATION PASSED: {all_valid}")

    if all_valid:
        header_form.save()
        qqoqccp_form.save()
        analyse_d4_form.save()
        capitalisation_d7_form.save()
        cloture_d8_form.save()
        participants_formset.save()
        mesures_d3_formset.save()
        actions_tests_formset.save()
        actions_permanentes_formset.save()
        print("SAVED SUCCESSFULLY!")

if __name__ == "__main__":
    test_post()
