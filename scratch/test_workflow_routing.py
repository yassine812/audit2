import os, sys
import django

sys.path.insert(0, r"c:\Users\Yassine\audit2-main")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from reclamation_client.models import ReclamationClient
from accident_travail.models import Societe, Site

User = get_user_model()
user = User.objects.filter(is_superuser=True).first() or User.objects.first()

societe = Societe.objects.first()
site = Site.objects.first()

c = Client()
c.force_login(user)

print("--- TEST A: R + 8D ---")
resp_a = c.post("/reclamations/nouveau/", {
    "type_signalement": "R",
    "mode_traitement": "8D",
    "societe": societe.id,
    "site": site.id if site else "",
    "client_nom": "Test Client 8D",
    "contact_client": "Contact 8D",
    "description_piece": "Pièce 8D",
    "reference_piece": "REF-8D",
    "quantite_impactee": 10,
    "date_alerte_client": "2026-08-31",
}, follow=False)

print(f"Status: {resp_a.status_code}, Redirect URL: {resp_a.url}")
assert "/editer-8d/" in resp_a.url, "R + 8D must redirect to editer-8d!"
print("TEST A PASSED: Redirected to 8D editor as expected.")

print("\n--- TEST B: I + Fiche Incident (DOC05) ---")
resp_b = c.post("/reclamations/nouveau/", {
    "type_signalement": "I",
    "mode_traitement": "DOC05",
    "societe": societe.id,
    "site": site.id if site else "",
    "client_nom": "Test Client Incident",
    "contact_client": "Contact Incident",
    "description_piece": "Pièce Incident",
    "reference_piece": "REF-INC",
    "quantite_impactee": 5,
    "date_alerte_client": "2026-08-31",
}, follow=False)

print(f"Status: {resp_b.status_code}, Redirect URL: {resp_b.url}")
assert "/editer-8d/" not in resp_b.url, "I + DOC05 must NOT redirect to editer-8d!"
assert resp_b.url.endswith("/"), f"Expected redirect to detail URL, got {resp_b.url}"
print("TEST B PASSED: Redirected to detail synthesis page instead of 8D editor.")

print("\n--- TEST C: AI + Amélioration (DOC05) ---")
resp_c = c.post("/reclamations/nouveau/", {
    "type_signalement": "AI",
    "mode_traitement": "DOC05",
    "societe": societe.id,
    "site": site.id if site else "",
    "client_nom": "Test Client AI",
    "contact_client": "Contact AI",
    "description_piece": "Pièce AI",
    "reference_piece": "REF-AI",
    "quantite_impactee": 2,
    "date_alerte_client": "2026-08-31",
}, follow=False)

print(f"Status: {resp_c.status_code}, Redirect URL: {resp_c.url}")
assert "/editer-8d/" not in resp_c.url, "AI + DOC05 must NOT redirect to editer-8d!"
print("TEST C PASSED: Redirected to detail synthesis page.")

print("\nALL WORKFLOW ROUTING TESTS PASSED PERFECTLY!")
