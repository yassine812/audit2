"""Inspect DB and formset HTML rendering for Reclamation 115 (REC2609037)."""

import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
django.setup()

from reclamation_client.models import ReclamationClient, Participant8D, ActionTestD5
from accident_travail.models import ActionCorrective
from reclamation_client.forms import (
    Participant8DFormSet,
    ActionTestD5FormSet,
    ActionPermanenteD6FormSet,
)

def inspect_115():
    try:
        r = ReclamationClient.objects.get(pk=115)
    except ReclamationClient.DoesNotExist:
        print("Reclamation 115 does not exist.")
        return

    print(f"=== RECLAMATION 115 ({r.reference}) ===")
    
    parts = list(Participant8D.objects.filter(reclamation=r).order_by("pk"))
    tests = list(ActionTestD5.objects.filter(reclamation=r).order_by("pk"))
    perms = list(ActionCorrective.objects.filter(reclamation=r).order_by("pk"))

    print(f"D1 DB Participants ({len(parts)}):")
    for p in parts:
        print(f"  - PK: {p.pk}, User: {p.user}, Nom: '{p.nom_externe}', Fonction: '{p.fonction}'")

    print(f"D5 DB Tests ({len(tests)}):")
    for t in tests:
        print(f"  - PK: {t.pk}, Action: '{t.description_action}', Pilote: '{t.pilote_delai}', Conclusion: '{t.conclusion}'")

    print(f"D6 DB Perms ({len(perms)}):")
    for a in perms:
        print(f"  - PK: {a.pk}, Axe: '{a.axe}', Desc: '{a.description}', Pilote: '{a.pilote}'")

    fs_p = Participant8DFormSet(instance=r, prefix="participants")
    fs_t = ActionTestD5FormSet(instance=r, prefix="actions_tests")
    fs_a = ActionPermanenteD6FormSet(instance=r, prefix="actions_perm")

    print(f"\nFormset forms count: D1={len(fs_p.forms)}, D5={len(fs_t.forms)}, D6={len(fs_a.forms)}")

if __name__ == "__main__":
    inspect_115()
