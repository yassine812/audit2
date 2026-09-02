"""Stateless regression test script for 8D formset persistence (D1, D5, D6)."""

import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
django.setup()

from accounts.models import User, Societe
from reclamation_client.models import (
    ReclamationClient, Participant8D, ActionTestD5, DescriptionQQOQCCP,
    AnalyseCausesDoubleAxeD4, CapitalisationSMQSD7, ClotureRecevabiliteD8
)
from accident_travail.models import ActionCorrective
from reclamation_client.forms import (
    ReclamationHeaderForm, DescriptionQQOQCCPForm, AnalyseCausesDoubleAxeForm,
    CapitalisationSMQSD7Form, ClotureRecevabiliteD8Form, Participant8DFormSet,
    MesureConservatoireD3FormSet, ActionTestD5FormSet, ActionPermanenteD6FormSet
)

def run_test():
    print("==================================================")
    print("TESTING 8D FORMSET PERSISTENCE (D1, D5, D6)")
    print("==================================================\n")

    # Clean up existing test records for stateless execution
    ReclamationClient.objects.filter(reference="REC8D-FORMSET-TEST-001").delete()

    soc = Societe.objects.first() or Societe.objects.create(nom="Societe Formset Test")
    user1 = User.objects.filter(username="user1").first() or User.objects.create_user("user1", "u1@test.com", "pass")
    user2 = User.objects.filter(username="user2").first() or User.objects.create_user("user2", "u2@test.com", "pass")

    rec = ReclamationClient.objects.create(
        reference="REC8D-FORMSET-TEST-001",
        type_signalement="R",
        mode_traitement="8D",
        client_nom="Client Formset Test",
        societe=soc,
        quantite_impactee=10,
        date_alerte_client="2026-09-01",
        date_ouverture="2026-09-01",
    )

    # 1. TEST D1 PARTICIPANTS PERSISTENCE (3 ROWS)
    print("--- 1. Testing D1 Participants (3 rows) ---")
    post_d1 = {
        "numero_reclamation_client": "REC-123",
        "type_signalement": "R",
        "statut": "brouillon",
        "societe": str(soc.pk),
        "client_nom": "Client Formset Test",
        "quantite_impactee": "10",
        "date_alerte_client": "2026-09-01",
        "date_ouverture": "2026-09-01",
        "statut_recevabilite": "recevable",

        "participants-TOTAL_FORMS": "3",
        "participants-INITIAL_FORMS": "0",
        "participants-MIN_NUM_FORMS": "0",
        "participants-MAX_NUM_FORMS": "1000",

        "participants-0-user": str(user1.pk),
        "participants-0-nom_externe": "",
        "participants-0-fonction": "Chef de Projet",
        "participants-0-est_pilote": "on",

        "participants-1-user": str(user2.pk),
        "participants-1-nom_externe": "",
        "participants-1-fonction": "Ingénieur Qualité",

        "participants-2-user": "",
        "participants-2-nom_externe": "Expert Externe (Tiers)",
        "participants-2-fonction": "Consultant Externe",

        "mesures_d3-TOTAL_FORMS": "0",
        "mesures_d3-INITIAL_FORMS": "0",
        "actions_tests-TOTAL_FORMS": "0",
        "actions_tests-INITIAL_FORMS": "0",
        "actions_perm-TOTAL_FORMS": "0",
        "actions_perm-INITIAL_FORMS": "0",
    }

    fs_part = Participant8DFormSet(post_d1, instance=rec, prefix="participants")
    assert fs_part.is_valid(), f"Participant formset invalid: {fs_part.errors}"
    fs_part.save()

    parts = list(Participant8D.objects.filter(reclamation=rec).order_by("pk"))
    print(f"Saved D1 participants count: {len(parts)}")
    for p in parts:
        print(f"  - Participant PK {p.pk}: user={p.user}, nom_externe='{p.nom_externe}', fonction='{p.fonction}', pilote={p.est_pilote}")
    assert len(parts) == 3, f"Expected 3 participants, got {len(parts)}"

    # 2. TEST D5 ACTIONSTESTS PERSISTENCE (3 ROWS)
    print("\n--- 2. Testing D5 Actions Tests (3 rows) ---")
    post_d5 = {
        "numero_reclamation_client": "REC-123",
        "type_signalement": "R",
        "statut": "brouillon",
        "societe": str(soc.pk),
        "client_nom": "Client Formset Test",
        "quantite_impactee": "10",
        "date_alerte_client": "2026-09-01",
        "date_ouverture": "2026-09-01",
        "statut_recevabilite": "recevable",

        "participants-TOTAL_FORMS": "3",
        "participants-INITIAL_FORMS": "3",
        "participants-0-id": str(parts[0].pk),
        "participants-0-user": str(user1.pk),
        "participants-0-fonction": "Chef de Projet",
        "participants-1-id": str(parts[1].pk),
        "participants-1-user": str(user2.pk),
        "participants-1-fonction": "Ingénieur Qualité",
        "participants-2-id": str(parts[2].pk),
        "participants-2-nom_externe": "Expert Externe (Tiers)",
        "participants-2-fonction": "Consultant Externe",

        "mesures_d3-TOTAL_FORMS": "0",
        "mesures_d3-INITIAL_FORMS": "0",

        "actions_tests-TOTAL_FORMS": "3",
        "actions_tests-INITIAL_FORMS": "0",
        "actions_tests-0-description_action": "TEST A - Test d'étanchéité",
        "actions_tests-0-pilote_delai": "Jean - 05/09/2026",
        "actions_tests-0-conclusion": "OK - Conforme",

        "actions_tests-1-description_action": "TEST B - Test de résistance",
        "actions_tests-1-pilote_delai": "Ahmed - 06/09/2026",
        "actions_tests-1-conclusion": "NOK - Déformation",

        "actions_tests-2-description_action": "TEST C - Contrôle visuel 100%",
        "actions_tests-2-pilote_delai": "Yassine - 07/09/2026",
        "actions_tests-2-conclusion": "OK - Validé",

        "actions_perm-TOTAL_FORMS": "0",
        "actions_perm-INITIAL_FORMS": "0",
    }

    fs_test = ActionTestD5FormSet(post_d5, instance=rec, prefix="actions_tests")
    assert fs_test.is_valid(), f"ActionTest formset invalid: {fs_test.errors}"
    fs_test.save()

    tests_d5 = list(ActionTestD5.objects.filter(reclamation=rec).order_by("pk"))
    print(f"Saved D5 actions tests count: {len(tests_d5)}")
    for t in tests_d5:
        print(f"  - ActionTest PK {t.pk}: desc='{t.description_action}', pilote='{t.pilote_delai}', conclusion='{t.conclusion}'")
    assert len(tests_d5) == 3, f"Expected 3 D5 actions, got {len(tests_d5)}"

    # 3. TEST D6 ACTIONSPERMANENTES PERSISTENCE (3 ROWS)
    print("\n--- 3. Testing D6 Actions Permanentes (3 rows) ---")
    post_d6 = {
        "numero_reclamation_client": "REC-123",
        "type_signalement": "R",
        "statut": "brouillon",
        "societe": str(soc.pk),
        "client_nom": "Client Formset Test",
        "quantite_impactee": "10",
        "date_alerte_client": "2026-09-01",
        "date_ouverture": "2026-09-01",
        "statut_recevabilite": "recevable",

        "participants-TOTAL_FORMS": "3",
        "participants-INITIAL_FORMS": "3",
        "participants-0-id": str(parts[0].pk),
        "participants-0-user": str(user1.pk),
        "participants-0-fonction": "Chef de Projet",
        "participants-1-id": str(parts[1].pk),
        "participants-1-user": str(user2.pk),
        "participants-1-fonction": "Ingénieur Qualité",
        "participants-2-id": str(parts[2].pk),
        "participants-2-nom_externe": "Expert Externe (Tiers)",
        "participants-2-fonction": "Consultant Externe",

        "mesures_d3-TOTAL_FORMS": "0",
        "mesures_d3-INITIAL_FORMS": "0",

        "actions_tests-TOTAL_FORMS": "3",
        "actions_tests-INITIAL_FORMS": "3",
        "actions_tests-0-id": str(tests_d5[0].pk),
        "actions_tests-0-description_action": "TEST A - Test d'étanchéité",
        "actions_tests-1-id": str(tests_d5[1].pk),
        "actions_tests-1-description_action": "TEST B - Test de résistance",
        "actions_tests-2-id": str(tests_d5[2].pk),
        "actions_tests-2-description_action": "TEST C - Contrôle visuel 100%",

        "actions_perm-TOTAL_FORMS": "3",
        "actions_perm-INITIAL_FORMS": "0",

        "actions_perm-0-axe": "technique",
        "actions_perm-0-description": "ACTION A - Modification outillage",
        "actions_perm-0-pilote": "Jean",
        "actions_perm-0-statut": "en_cours",

        "actions_perm-1-axe": "non_detection",
        "actions_perm-1-description": "ACTION B - Mise à jour gamme de contrôle",
        "actions_perm-1-pilote": "Ahmed",
        "actions_perm-1-statut": "non_demarre",

        "actions_perm-2-axe": "technique",
        "actions_perm-2-description": "ACTION C - Formation des opérateurs",
        "actions_perm-2-pilote": "Yassine",
        "actions_perm-2-statut": "realise",
    }

    fs_perm = ActionPermanenteD6FormSet(post_d6, instance=rec, prefix="actions_perm")
    assert fs_perm.is_valid(), f"ActionPermanente formset invalid: {fs_perm.errors}"
    fs_perm.save()

    perms_d6 = list(ActionCorrective.objects.filter(reclamation=rec).order_by("pk"))
    print(f"Saved D6 actions permanentes count: {len(perms_d6)}")
    for a in perms_d6:
        print(f"  - ActionCorrective PK {a.pk}: axe='{a.axe}', desc='{a.description}', pilote='{a.pilote}', statut='{a.statut}'")
    assert len(perms_d6) == 3, f"Expected 3 D6 actions, got {len(perms_d6)}"

    # 4. TEST UPDATE EXISTING ROW (MODIFICATION WITHOUT DUPLICATION)
    print("\n--- 4. Testing Row Update (Modify Row 2) ---")
    post_update = {
        "numero_reclamation_client": "REC-123",
        "type_signalement": "R",
        "statut": "brouillon",
        "societe": str(soc.pk),
        "client_nom": "Client Formset Test",
        "quantite_impactee": "10",
        "date_alerte_client": "2026-09-01",
        "date_ouverture": "2026-09-01",
        "statut_recevabilite": "recevable",

        "participants-TOTAL_FORMS": "3",
        "participants-INITIAL_FORMS": "3",
        "participants-0-id": str(parts[0].pk),
        "participants-0-user": str(user1.pk),
        "participants-0-fonction": "Chef de Projet",
        "participants-1-id": str(parts[1].pk),
        "participants-1-user": str(user2.pk),
        "participants-1-fonction": "Ingénieur Qualité Principal (MODIFIED)",
        "participants-2-id": str(parts[2].pk),
        "participants-2-nom_externe": "Expert Externe (Tiers)",
        "participants-2-fonction": "Consultant Externe",

        "mesures_d3-TOTAL_FORMS": "0",
        "mesures_d3-INITIAL_FORMS": "0",
        "actions_tests-TOTAL_FORMS": "3",
        "actions_tests-INITIAL_FORMS": "3",
        "actions_tests-0-id": str(tests_d5[0].pk),
        "actions_tests-0-description_action": "TEST A - Test d'étanchéité",
        "actions_tests-1-id": str(tests_d5[1].pk),
        "actions_tests-1-description_action": "TEST B - Test de résistance (MODIFIED)",
        "actions_tests-2-id": str(tests_d5[2].pk),
        "actions_tests-2-description_action": "TEST C - Contrôle visuel 100%",

        "actions_perm-TOTAL_FORMS": "3",
        "actions_perm-INITIAL_FORMS": "3",
        "actions_perm-0-id": str(perms_d6[0].pk),
        "actions_perm-0-axe": "technique",
        "actions_perm-0-description": "ACTION A - Modification outillage",
        "actions_perm-0-statut": "en_cours",
        "actions_perm-1-id": str(perms_d6[1].pk),
        "actions_perm-1-axe": "non_detection",
        "actions_perm-1-description": "ACTION B - Gamme de contrôle (MODIFIED)",
        "actions_perm-1-statut": "non_demarre",
        "actions_perm-2-id": str(perms_d6[2].pk),
        "actions_perm-2-axe": "technique",
        "actions_perm-2-description": "ACTION C - Formation des opérateurs",
        "actions_perm-2-statut": "realise",
    }

    fs_p_up = Participant8DFormSet(post_update, instance=rec, prefix="participants")
    fs_t_up = ActionTestD5FormSet(post_update, instance=rec, prefix="actions_tests")
    fs_a_up = ActionPermanenteD6FormSet(post_update, instance=rec, prefix="actions_perm")

    print("fs_p_up errors:", fs_p_up.errors)
    print("fs_t_up errors:", fs_t_up.errors)
    print("fs_a_up errors:", fs_a_up.errors)

    assert fs_p_up.is_valid() and fs_t_up.is_valid() and fs_a_up.is_valid()
    fs_p_up.save()
    fs_t_up.save()
    fs_a_up.save()

    parts_up = Participant8D.objects.filter(reclamation=rec)
    tests_up = ActionTestD5.objects.filter(reclamation=rec)
    perms_up = ActionCorrective.objects.filter(reclamation=rec)

    assert parts_up.count() == 3 and parts_up.get(pk=parts[1].pk).fonction == "Ingénieur Qualité Principal (MODIFIED)"
    assert tests_up.count() == 3 and tests_up.get(pk=tests_d5[1].pk).description_action == "TEST B - Test de résistance (MODIFIED)"
    assert perms_up.count() == 3 and perms_up.get(pk=perms_d6[1].pk).description == "ACTION B - Gamme de contrôle (MODIFIED)"
    print("  -> UPDATE PASSED: Row 2 modified in D1, D5, D6 without creating any duplicate records!")

    # 5. TEST ROW DELETION
    print("\n--- 5. Testing Row Deletion (Delete Row 2) ---")
    post_delete = {
        "numero_reclamation_client": "REC-123",
        "type_signalement": "R",
        "statut": "brouillon",
        "societe": str(soc.pk),
        "client_nom": "Client Formset Test",
        "quantite_impactee": "10",
        "date_alerte_client": "2026-09-01",
        "date_ouverture": "2026-09-01",
        "statut_recevabilite": "recevable",

        "participants-TOTAL_FORMS": "3",
        "participants-INITIAL_FORMS": "3",
        "participants-0-id": str(parts[0].pk),
        "participants-0-user": str(user1.pk),
        "participants-0-fonction": "Chef de Projet",
        "participants-1-id": str(parts[1].pk),
        "participants-1-user": str(user2.pk),
        "participants-1-fonction": "Ingénieur Qualité Principal (MODIFIED)",
        "participants-1-DELETE": "on",
        "participants-2-id": str(parts[2].pk),
        "participants-2-nom_externe": "Expert Externe (Tiers)",
        "participants-2-fonction": "Consultant Externe",

        "mesures_d3-TOTAL_FORMS": "0",
        "mesures_d3-INITIAL_FORMS": "0",

        "actions_tests-TOTAL_FORMS": "3",
        "actions_tests-INITIAL_FORMS": "3",
        "actions_tests-0-id": str(tests_d5[0].pk),
        "actions_tests-0-description_action": "TEST A - Test d'étanchéité",
        "actions_tests-1-id": str(tests_d5[1].pk),
        "actions_tests-1-description_action": "TEST B - Test de résistance (MODIFIED)",
        "actions_tests-1-DELETE": "on",
        "actions_tests-2-id": str(tests_d5[2].pk),
        "actions_tests-2-description_action": "TEST C - Contrôle visuel 100%",

        "actions_perm-TOTAL_FORMS": "3",
        "actions_perm-INITIAL_FORMS": "3",
        "actions_perm-0-id": str(perms_d6[0].pk),
        "actions_perm-0-axe": "technique",
        "actions_perm-0-description": "ACTION A - Modification outillage",
        "actions_perm-0-statut": "en_cours",
        "actions_perm-1-id": str(perms_d6[1].pk),
        "actions_perm-1-axe": "non_detection",
        "actions_perm-1-description": "ACTION B - Gamme de contrôle (MODIFIED)",
        "actions_perm-1-statut": "non_demarre",
        "actions_perm-1-DELETE": "on",
        "actions_perm-2-id": str(perms_d6[2].pk),
        "actions_perm-2-axe": "technique",
        "actions_perm-2-description": "ACTION C - Formation des opérateurs",
        "actions_perm-2-statut": "realise",
    }

    fs_p_del = Participant8DFormSet(post_delete, instance=rec, prefix="participants")
    fs_t_del = ActionTestD5FormSet(post_delete, instance=rec, prefix="actions_tests")
    fs_a_del = ActionPermanenteD6FormSet(post_delete, instance=rec, prefix="actions_perm")

    assert fs_p_del.is_valid() and fs_t_del.is_valid() and fs_a_del.is_valid()
    fs_p_del.save()
    fs_t_del.save()
    fs_a_del.save()

    parts_del = Participant8D.objects.filter(reclamation=rec)
    tests_del = ActionTestD5.objects.filter(reclamation=rec)
    perms_del = ActionCorrective.objects.filter(reclamation=rec)

    assert parts_del.count() == 2 and not parts_del.filter(pk=parts[1].pk).exists()
    assert tests_del.count() == 2 and not tests_del.filter(pk=tests_d5[1].pk).exists()
    assert perms_del.count() == 2 and not perms_del.filter(pk=perms_d6[1].pk).exists()
    print("  -> DELETE PASSED: Row 2 deleted in D1, D5, D6!")

    # 6. TEST EMPTY EXTRA ROW (SHOULD BE IGNORED, NOT PERSISTED)
    print("\n--- 6. Testing Empty Extra Form (Ignore Fake/Duplicate) ---")
    post_empty_extra = {
        "numero_reclamation_client": "REC-123",
        "type_signalement": "R",
        "statut": "brouillon",
        "societe": str(soc.pk),
        "client_nom": "Client Formset Test",
        "quantite_impactee": "10",
        "date_alerte_client": "2026-09-01",
        "date_ouverture": "2026-09-01",
        "statut_recevabilite": "recevable",

        # 2 initial forms + 1 empty extra form
        "participants-TOTAL_FORMS": "3",
        "participants-INITIAL_FORMS": "2",
        "participants-0-id": str(parts_del[0].pk),
        "participants-0-user": str(user1.pk),
        "participants-0-fonction": "Chef de Projet",
        "participants-1-id": str(parts_del[1].pk),
        "participants-1-nom_externe": "Expert Externe (Tiers)",
        "participants-1-fonction": "Consultant Externe",
        "participants-2-user": "",
        "participants-2-nom_externe": "",
        "participants-2-fonction": "",

        "mesures_d3-TOTAL_FORMS": "0",
        "mesures_d3-INITIAL_FORMS": "0",

        "actions_tests-TOTAL_FORMS": "3",
        "actions_tests-INITIAL_FORMS": "2",
        "actions_tests-0-id": str(tests_del[0].pk),
        "actions_tests-0-description_action": "TEST A - Test d'étanchéité",
        "actions_tests-1-id": str(tests_del[1].pk),
        "actions_tests-1-description_action": "TEST C - Contrôle visuel 100%",
        "actions_tests-2-description_action": "",
        "actions_tests-2-pilote_delai": "",
        "actions_tests-2-conclusion": "",

        "actions_perm-TOTAL_FORMS": "3",
        "actions_perm-INITIAL_FORMS": "2",
        "actions_perm-0-id": str(perms_del[0].pk),
        "actions_perm-0-axe": "technique",
        "actions_perm-0-description": "ACTION A - Modification outillage",
        "actions_perm-0-statut": "en_cours",
        "actions_perm-1-id": str(perms_del[1].pk),
        "actions_perm-1-axe": "technique",
        "actions_perm-1-description": "ACTION C - Formation des opérateurs",
        "actions_perm-1-statut": "realise",
        "actions_perm-2-axe": "technique",
        "actions_perm-2-description": "",
        "actions_perm-2-statut": "non_demarre",
    }

    fs_p_emp = Participant8DFormSet(post_empty_extra, instance=rec, prefix="participants")
    fs_t_emp = ActionTestD5FormSet(post_empty_extra, instance=rec, prefix="actions_tests")
    fs_a_emp = ActionPermanenteD6FormSet(post_empty_extra, instance=rec, prefix="actions_perm")

    print("fs_p_emp errors:", fs_p_emp.errors)
    print("fs_t_emp errors:", fs_t_emp.errors)
    print("fs_a_emp errors:", fs_a_emp.errors)

    assert fs_p_emp.is_valid() and fs_t_emp.is_valid() and fs_a_emp.is_valid()
    fs_p_emp.save()
    fs_t_emp.save()
    fs_a_emp.save()

    parts_final = Participant8D.objects.filter(reclamation=rec)
    tests_final = ActionTestD5.objects.filter(reclamation=rec)
    perms_final = ActionCorrective.objects.filter(reclamation=rec)

    for t in tests_final:
        print(f"  - Final ActionTest PK {t.pk}: desc='{t.description_action}', pilote='{t.pilote_delai}', conclusion='{t.conclusion}'")

    assert parts_final.count() == 2, f"Expected 2 participants, got {parts_final.count()}"
    assert tests_final.count() == 2, f"Expected 2 D5 tests, got {tests_final.count()}"
    assert perms_final.count() == 2, f"Expected 2 D6 perms, got {perms_final.count()}"
    print("  -> EMPTY EXTRA ROW PASSED: Empty extra form ignored, 0 fake records created!")

    print("\nALL 8D FORMSET PERSISTENCE TESTS PASSED CLEANLY!\n")

if __name__ == "__main__":
    run_test()
