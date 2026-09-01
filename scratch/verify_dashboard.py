import os
import sys
import django

sys.path.insert(0, '.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')
django.setup()

from django.core.management import call_command
from django.test import Client
from accounts.models import User
from accident_travail.models import ActionCorrective
from reclamation_client.models import ReclamationClient, ClotureRecevabiliteD8

print("=== 1. Django Check ===")
call_command('check')

print("\n=== 2. Statistics Summary ===")
qs = ReclamationClient.objects.all()
demo_qs = ReclamationClient.objects.filter(client_nom__icontains='[TEST DEMO]')

total_count = qs.count()
ouvertes_count = qs.exclude(statut=ReclamationClient.STATUT_CLOTURE).count()
cloturees_count = qs.filter(statut=ReclamationClient.STATUT_CLOTURE).count()

r_count = qs.filter(type_signalement='R').count()
i_count = qs.filter(type_signalement='I').count()
ai_count = qs.filter(type_signalement='AI').count()

clotures = ClotureRecevabiliteD8.objects.select_related('reclamation')
recevables = clotures.filter(statut_recevabilite=ClotureRecevabiliteD8.RECEVABILITE_RECEVABLE).count()
non_recevables = clotures.filter(statut_recevabilite=ClotureRecevabiliteD8.RECEVABILITE_NON_RECEVABLE).count()
partiels = clotures.filter(statut_recevabilite=ClotureRecevabiliteD8.RECEVABILITE_PARTIEL).count()

actions = ActionCorrective.objects.filter(reclamation__isnull=False)
act_non_demarre = actions.filter(statut='non_demarre').count()
act_en_cours = actions.filter(statut='en_cours').count()
act_realise = actions.filter(statut='realise').count()
act_verifie = actions.filter(statut='verifie').count()

print(f"Total Réclamations : {total_count} (dont {demo_qs.count()} de démonstration [TEST DEMO])")
print(f"  - Réclamations Ouvertes : {ouvertes_count}")
print(f"  - Réclamations Clôturées : {cloturees_count}")
print(f"  - Réclamations Qualité (R) : {r_count}")
print(f"  - Incidents Client (I) : {i_count}")
print(f"  - Améliorations Internes (AI) : {ai_count}")
print(f"Recevabilité P05 §5 :")
print(f"  - Recevables : {recevables}")
print(f"  - Non Recevables : {non_recevables}")
print(f"  - Partiels : {partiels}")
print(f"Actions Correctives (ActionCorrective) : {actions.count()} au total")
print(f"  - Non démarrées : {act_non_demarre}")
print(f"  - En cours : {act_en_cours}")
print(f"  - Réalisées : {act_realise}")
print(f"  - Vérifiées : {act_verifie}")

print("\n=== 3. Testing GET /reclamations/ Endpoint ===")
client = Client()
user = User.objects.filter(is_superuser=True).first() or User.objects.first()
client.force_login(user)

response = client.get('/reclamations/')
print(f"GET /reclamations/ -> HTTP {response.status_code}")
assert response.status_code == 200, f"Expected 200, got {response.status_code}"

content = response.content.decode('utf-8')
assert 'Suivi du Nombre de Réclamations' in content, "Dashboard title missing"
assert '(Fabien)' not in content, "Text '(Fabien)' still present"

print("[OK] Dashboard response verified successfully!")
