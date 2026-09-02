"""Test script for D6 ModelFormSet persistence and deletion behavior."""

import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
django.setup()

from accounts.models import User, Societe
from reclamation_client.models import ReclamationClient
from accident_travail.models import ActionCorrective
from reclamation_client.forms import ActionPermanenteD6FormSet

def test_d6_persistence():
    print("==================================================")
    print("TESTING D6 MODELFORMSET PERSISTENCE & DELETION")
    print("==================================================\n")

    ReclamationClient.objects.filter(reference="REC8D-D6-TEST").delete()

    soc = Societe.objects.first() or Societe.objects.create(nom="Societe D6 Test")
    rec = ReclamationClient.objects.create(
        reference="REC8D-D6-TEST",
        type_signalement="R",
        mode_traitement="8D",
        client_nom="Client D6 Test",
        societe=soc,
        quantite_impactee=5,
        date_alerte_client="2026-09-01",
        date_ouverture="2026-09-01",
    )

    # Step 1: Create 1 Action in D6
    print("Step 1: Save 1 action in D6...")
    post_1 = {
        "numero_reclamation_client": "REC-D6",
        "type_signalement": "R",
        "statut": "brouillon",
        "societe": str(soc.pk),
        "client_nom": "Client D6 Test",
        "quantite_impactee": "5",
        "date_alerte_client": "2026-09-01",
        "date_ouverture": "2026-09-01",
        "statut_recevabilite": "recevable",

        "actions_perm-TOTAL_FORMS": "1",
        "actions_perm-INITIAL_FORMS": "0",
        "actions_perm-0-axe": "technique",
        "actions_perm-0-description": "ACTION 1 - Correction outillage",
        "actions_perm-0-pilote": "Jean",
        "actions_perm-0-statut": "en_cours",
    }

    fs_1 = ActionPermanenteD6FormSet(post_1, instance=rec, prefix="actions_perm")
    assert fs_1.is_valid(), f"D6 formset 1 invalid: {fs_1.errors}"
    fs_1.save()

    actions_1 = list(ActionCorrective.objects.filter(reclamation=rec).order_by("pk"))
    print(f"Saved D6 actions count: {len(actions_1)}")
    assert len(actions_1) == 1
    action_1_pk = actions_1[0].pk
    print(f"  -> Action PK: {action_1_pk}, Desc: '{actions_1[0].description}'")

    # Step 2: Edit Action 1 & Add Action 2
    print("\nStep 2: Edit Action 1 & Add Action 2...")
    post_2 = {
        "numero_reclamation_client": "REC-D6",
        "type_signalement": "R",
        "statut": "brouillon",
        "societe": str(soc.pk),
        "client_nom": "Client D6 Test",
        "quantite_impactee": "5",
        "date_alerte_client": "2026-09-01",
        "date_ouverture": "2026-09-01",
        "statut_recevabilite": "recevable",

        "actions_perm-TOTAL_FORMS": "2",
        "actions_perm-INITIAL_FORMS": "1",
        "actions_perm-0-id": str(action_1_pk),
        "actions_perm-0-axe": "technique",
        "actions_perm-0-description": "ACTION 1 - Correction outillage (MODIFIED)",
        "actions_perm-0-pilote": "Jean Marc",
        "actions_perm-0-statut": "realise",

        "actions_perm-1-axe": "non_detection",
        "actions_perm-1-description": "ACTION 2 - Mise à jour procédure",
        "actions_perm-1-pilote": "Ahmed",
        "actions_perm-1-statut": "en_cours",
    }

    fs_2 = ActionPermanenteD6FormSet(post_2, instance=rec, prefix="actions_perm")
    assert fs_2.is_valid(), f"D6 formset 2 invalid: {fs_2.errors}"
    fs_2.save()

    actions_2 = list(ActionCorrective.objects.filter(reclamation=rec).order_by("pk"))
    print(f"Saved D6 actions count: {len(actions_2)}")
    assert len(actions_2) == 2
    assert actions_2[0].pk == action_1_pk
    assert actions_2[0].description == "ACTION 1 - Correction outillage (MODIFIED)"
    print(f"  -> Action 1 updated cleanly without duplication! Action 2 added (PK {actions_2[1].pk})")

    # Step 3: Mark Action 1 for DELETE
    print("\nStep 3: Delete Action 1...")
    post_3 = {
        "numero_reclamation_client": "REC-D6",
        "type_signalement": "R",
        "statut": "brouillon",
        "societe": str(soc.pk),
        "client_nom": "Client D6 Test",
        "quantite_impactee": "5",
        "date_alerte_client": "2026-09-01",
        "date_ouverture": "2026-09-01",
        "statut_recevabilite": "recevable",

        "actions_perm-TOTAL_FORMS": "2",
        "actions_perm-INITIAL_FORMS": "2",
        "actions_perm-0-id": str(action_1_pk),
        "actions_perm-0-axe": "technique",
        "actions_perm-0-description": "ACTION 1 - Correction outillage (MODIFIED)",
        "actions_perm-0-statut": "realise",
        "actions_perm-0-DELETE": "on",

        "actions_perm-1-id": str(actions_2[1].pk),
        "actions_perm-1-axe": "non_detection",
        "actions_perm-1-description": "ACTION 2 - Mise à jour procédure",
        "actions_perm-1-statut": "en_cours",
    }

    fs_3 = ActionPermanenteD6FormSet(post_3, instance=rec, prefix="actions_perm")
    assert fs_3.is_valid(), f"D6 formset 3 invalid: {fs_3.errors}"
    fs_3.save()

    actions_3 = list(ActionCorrective.objects.filter(reclamation=rec).order_by("pk"))
    print(f"Saved D6 actions count after deletion: {len(actions_3)}")
    assert len(actions_3) == 1
    assert actions_3[0].pk == actions_2[1].pk
    print("  -> Action 1 DELETED successfully from DB! Action 2 remains.")

    print("\nD6 MODELFORMSET PERSISTENCE TESTS PASSED 100%!\n")

if __name__ == "__main__":
    test_d6_persistence()
