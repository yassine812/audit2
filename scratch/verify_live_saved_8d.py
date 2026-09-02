"""Script to verify live saved 8D dossiers in database."""

import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
django.setup()

from reclamation_client.models import (
    ReclamationClient, AnalyseCausesDoubleAxeD4, CapitalisationSMQSD7, ClotureRecevabiliteD8
)

def verify_saved_dossiers():
    recs = ReclamationClient.objects.filter(mode_traitement="8D").order_by("-pk")
    print(f"Total 8D dossiers in database: {recs.count()}\n")
    for r in recs[:5]:
        print(f"--- Dossier {r.reference} (PK: {r.pk}) ---")
        print(f"  Client: {r.client_nom}")
        print(f"  Societé: {r.societe}")
        print(f"  Quantité: {r.quantite_impactee}")
        print(f"  Date alerte: {r.date_alerte_client}")
        print(f"  Date ouverture: {r.date_ouverture}")
        
        d4 = getattr(r, "analyse_d4", None)
        if d4:
            print(f"  D4.1 Non-détection branches: {len(d4.pourquoi_non_detection)}")
            print(f"  D4.2 Cause technique branches: {len(d4.pourquoi_technique)}")
        
        d7 = getattr(r, "capitalisation_d7", None)
        if d7:
            print(f"  D7 Doc01 mis à jour: {d7.doc01_instruction}")
            print(f"  D7 Doc38 mis à jour: {d7.doc38_habilitation_poste}, Pilote-Délai: '{d7.doc38_pilote_delai}'")

        d8 = getattr(r, "cloture_d8", None)
        if d8:
            print(f"  D8 Recevabilité: {d8.statut_recevabilite}")
        print()

if __name__ == "__main__":
    verify_saved_dossiers()
