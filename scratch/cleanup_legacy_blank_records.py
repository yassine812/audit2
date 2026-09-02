"""Clean up existing legacy blank records in D1, D5, D6 across all ReclamationClient instances."""

import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
django.setup()

from reclamation_client.models import Participant8D, ActionTestD5
from accident_travail.models import ActionCorrective

def cleanup():
    print("Cleaning up legacy blank records in DB...")
    
    # 1. D1 Participants with empty user, nom_externe, and fonction
    blank_d1 = Participant8D.objects.filter(user__isnull=True, nom_externe="", fonction="")
    count_d1 = blank_d1.count()
    blank_d1.delete()
    print(f"Deleted {count_d1} blank D1 participant records.")

    # 2. D5 Actions Tests with empty description_action
    blank_d5 = ActionTestD5.objects.filter(description_action="", pilote_delai="", conclusion="")
    count_d5 = blank_d5.count()
    blank_d5.delete()
    print(f"Deleted {count_d5} blank D5 action test records.")

    # 3. D6 Actions Permanentes with empty description
    blank_d6 = ActionCorrective.objects.filter(reclamation__isnull=False, description="", pilote="")
    count_d6 = blank_d6.count()
    blank_d6.delete()
    print(f"Deleted {count_d6} blank D6 action corrective records.")

if __name__ == "__main__":
    cleanup()
