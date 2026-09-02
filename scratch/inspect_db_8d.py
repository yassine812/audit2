"""Inspect actual database records for 8D ReclamationClient (especially PK 115 REC2609037)."""

import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
django.setup()

from reclamation_client.models import ReclamationClient, Participant8D, ActionTestD5
from accident_travail.models import ActionCorrective

def inspect_db():
    print("==================================================")
    print("DATABASE INSPECTION FOR RECLAMATION 8D")
    print("==================================================\n")

    recs = ReclamationClient.objects.all().order_by("-pk")[:5]
    for r in recs:
        print(f"--- Reclamation PK: {r.pk} | Reference: '{r.reference}' | Client: '{r.client_nom}' ---")
        
        participants = Participant8D.objects.filter(reclamation=r).order_by("pk")
        print(f"  D1 Participants (DB count: {participants.count()}):")
        for p in participants:
            user_str = p.user.username if p.user else "None"
            print(f"    - PK: {p.pk} | User: '{user_str}' | Nom Externe: '{p.nom_externe}' | Fonction: '{p.fonction}' | Pilote: {p.est_pilote}")

        tests = ActionTestD5.objects.filter(reclamation=r).order_by("pk")
        print(f"  D5 Actions Tests (DB count: {tests.count()}):")
        for t in tests:
            print(f"    - PK: {t.pk} | Action: '{t.description_action}' | Pilote/Delai: '{t.pilote_delai}' | Conclusion: '{t.conclusion}' | Ordre: {getattr(t, 'ordre', 'N/A')}")

        perms = ActionCorrective.objects.filter(reclamation=r).order_by("pk")
        print(f"  D6 Actions Permanentes (DB count: {perms.count()}):")
        for a in perms:
            print(f"    - PK: {a.pk} | Axe: '{a.axe}' | Description: '{a.description}' | Pilote: '{a.pilote}' | Statut: '{a.statut}' | Ordre: {getattr(a, 'ordre', 'N/A')}")
        print()

if __name__ == "__main__":
    inspect_db()
