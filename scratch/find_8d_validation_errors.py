"""Script to find every single form field validation failure in 8D form."""

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

def inspect_default_8d_validation():
    soc = Societe.objects.first() or Societe.objects.create(nom="Test Soc")
    rec, _ = ReclamationClient.objects.get_or_create(
        reference="REC8D-INSPECT",
        defaults={
            "type_signalement": "R",
            "mode_traitement": "8D",
            "client_nom": "Client Test 8D",
            "societe": soc,
        }
    )

    qqoqccp, _ = DescriptionQQOQCCP.objects.get_or_create(reclamation=rec)
    analyse_d4, _ = AnalyseCausesDoubleAxeD4.objects.get_or_create(reclamation=rec)
    capitalisation_d7, _ = CapitalisationSMQSD7.objects.get_or_create(reclamation=rec)
    cloture_d8, _ = ClotureRecevabiliteD8.objects.get_or_create(reclamation=rec)

    # Empty POST dictionary (simulating a form submission where some fields aren't filled)
    empty_post = {
        "participants-TOTAL_FORMS": "0",
        "participants-INITIAL_FORMS": "0",
        "mesures_d3-TOTAL_FORMS": "0",
        "mesures_d3-INITIAL_FORMS": "0",
        "actions_tests-TOTAL_FORMS": "0",
        "actions_tests-INITIAL_FORMS": "0",
        "actions_perm-TOTAL_FORMS": "0",
        "actions_perm-INITIAL_FORMS": "0",
    }

    f_head = ReclamationHeaderForm(empty_post, instance=rec, is_admin=True)
    f_qq = DescriptionQQOQCCPForm(empty_post, instance=qqoqccp)
    f_d4 = AnalyseCausesDoubleAxeForm(empty_post, instance=analyse_d4)
    f_d7 = CapitalisationSMQSD7Form(empty_post, instance=capitalisation_d7)
    f_d8 = ClotureRecevabiliteD8Form(empty_post, instance=cloture_d8)

    print("=== INSPECTING EMPTY POST VALIDATION ===")
    print("1. ReclamationHeaderForm errors:", f_head.errors)
    print("2. DescriptionQQOQCCPForm errors:", f_qq.errors)
    print("3. AnalyseCausesDoubleAxeForm errors:", f_d4.errors)
    print("4. CapitalisationSMQSD7Form errors:", f_d7.errors)
    print("5. ClotureRecevabiliteD8Form errors:", f_d8.errors)

if __name__ == "__main__":
    inspect_default_8d_validation()
