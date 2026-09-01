import os
import sys
import json
import django

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')
django.setup()

from datetime import date, timedelta
from django.test import Client, RequestFactory
from django.contrib.auth import get_user_model
from django.urls import reverse

from accounts.models import Societe, Site
from reclamation_client.models import (
    ReclamationClient,
    Participant8D,
    DescriptionQQOQCCP,
    MesureConservatoireD3,
    AnalyseCausesDoubleAxeD4,
    ActionTestD5,
    ActionPermanenteD6,
    CapitalisationSMQSD7,
    ClotureRecevabiliteD8,
    FicheIncidentDoc05,
)
from reclamation_client.views import (
    ReclamationDashboardView,
    reclamation_export_pdf_8d,
    reclamation_export_pdf_doc05,
)

User = get_user_model()
user = User.objects.filter(is_superuser=True).first() or User.objects.first()

c = Client()
c.force_login(user)
rf = RequestFactory()

societe = Societe.objects.first()
site = Site.objects.first()

today_str = date.today().isoformat()

print("=================================================================")
print("  E2E END-TO-END QA TEST FOR RECLAMATIONS MODULE (R, I, AI)  ")
print("=================================================================")

# -------------------------------------------------------------------
# 1. TYPE / SUPPORT AUTOMATIC DERIVATION TEST
# -------------------------------------------------------------------
print("\n--- 1. TYPE / SUPPORT AUTOMATIC DERIVATION VERIFICATION ---")

type_r_mode = ReclamationClient.get_mode_for_type("R")
type_i_mode = ReclamationClient.get_mode_for_type("I")
type_ai_mode = ReclamationClient.get_mode_for_type("AI")

print(f"R  -> Expected: 8D, Actual: {type_r_mode} -> {'PASS' if type_r_mode == '8D' else 'FAIL'}")
print(f"I  -> Expected: DOC05, Actual: {type_i_mode} -> {'PASS' if type_i_mode == 'DOC05' else 'FAIL'}")
print(f"AI -> Expected: DOC05_FAI, Actual: {type_ai_mode} -> {'PASS' if type_ai_mode == 'DOC05_FAI' else 'FAIL'}")

# -------------------------------------------------------------------
# 2. TEST 1 — RÉCLAMATION QUALITÉ (R) WITH 8D WORKFLOW & PDF
# -------------------------------------------------------------------
print("\n--- 2. TEST 1 — RÉCLAMATION QUALITÉ (R) [8D] ---")

r_data = {
    'type_signalement': 'R',
    'mode_traitement': '8D',
    'societe': societe.id,
    'site': site.id if site else '',
    'client_nom': 'ABC Automotive',
    'contact_client': 'Jean Dupont',
    'description_piece': 'Défaut de montage sur une pièce livrée',
    'reference_piece': 'PIECE-R-001',
    'quantite_impactee': 10,
    'date_alerte_client': today_str,
    'accuse_reception_envoye': 'on',
}

response_r = c.post(reverse('reclamation:create'), r_data, follow=True)
rec_r = ReclamationClient.objects.filter(reference_piece='PIECE-R-001').first()

if rec_r:
    print(f"Created R: {rec_r.reference} (ID: {rec_r.pk})")
    print(f"Type: {rec_r.type_signalement} (Expected: R)")
    print(f"Support: {rec_r.mode_traitement} (Expected: 8D)")
    print(f"Accusé Réception: {rec_r.accuse_reception_envoye}")

    # Fill 8D sub-forms
    # D1-D3
    rec_r.pilote = user.get_full_name() or user.username
    rec_r.statut = ReclamationClient.STATUT_D1_D3
    rec_r.save()

    DescriptionQQOQCCP.objects.update_or_create(
        reclamation=rec_r,
        defaults={
            'qui_est': 'Opérateur ligne 2',
            'quoi_est': 'Mauvais serrage de vis',
            'ou_est': 'Usine Tunis',
            'quand_est': today_str,
            'comment_est': 'Vis desserrée au contrôle final',
            'combien_est': '10 pièces',
            'pourquoi_est': 'Couple de serrage insuffisant',
        }
    )

    MesureConservatoireD3.objects.create(
        reclamation=rec_r,
        type_mesure='tri_interne',
        selectionne=True,
        quantite_triee=100,
        quantite_nok=10,
        commentaires='Tri de 100% des pièces en stock effectué avec succès'
    )

    # D4
    AnalyseCausesDoubleAxeD4.objects.update_or_create(
        reclamation=rec_r,
        defaults={
            'cause_principale_non_detection': 'Contrôle visuel insuffisant en fin de ligne',
            'cause_principale_technique': 'Absence de détrompeur mécanique et visseuse non calibrée',
        }
    )

    # D5-D6
    ActionTestD5.objects.create(
        reclamation=rec_r,
        description_action='Essai serrage automatique avec contrôle de couple',
        pilote_delai='Responsable Qualité - 02/09/2026',
        conclusion='Test concluant à 100%, blocage effectif si couple non atteint',
        ordre=1
    )

    ActionPermanenteD6.objects.create(
        reclamation=rec_r,
        axe='technique',
        cause_racine='Absence d un système de serrage asservi',
        description='Installation d une visseuse dynamométrique communicante asservie à l automate',
        pilote=user.get_full_name() or user.username,
        delai=date.today() + timedelta(days=7),
        statut='realise',
        efficace=True
    )

    # D7-D8
    CapitalisationSMQSD7.objects.update_or_create(
        reclamation=rec_r,
        defaults={
            'doc01_instruction': True,
            'doc01_pilote_delai': 'Chef de projet - OK',
            'commentaires_d7': 'Mise à jour documentaire SMQS effectuée et validée.',
        }
    )

    ClotureRecevabiliteD8.objects.update_or_create(
        reclamation=rec_r,
        defaults={
            'statut_recevabilite': 'recevable',
            'motif_recevabilite': 'Réclamation fondée après analyse 8D complète',
            'cloture_par': user.get_full_name() or user.username,
            'date_cloture': date.today(),
            'commentaires_cloture': 'Dossier 8D validé et clôturé avec succès.',
        }
    )

    rec_r.statut = ReclamationClient.STATUT_CLOTURE
    rec_r.save()

    # Generate 8D PDF
    pdf_res_r = c.get(reverse('reclamation:export_pdf_8d', kwargs={'pk': rec_r.pk}))
    print(f"PDF 8D Export Status: {pdf_res_r.status_code}, Content-Type: {pdf_res_r.get('Content-Type')}, Content Size: {len(pdf_res_r.content)} bytes")
else:
    print("FAILED TO CREATE R RECLAMATION")

# -------------------------------------------------------------------
# 3. TEST 2 — INCIDENT CLIENT (I) WITH DOC 05 WORKFLOW & PDF
# -------------------------------------------------------------------
print("\n--- 3. TEST 2 — INCIDENT CLIENT (I) [DOC 05] ---")

i_data = {
    'type_signalement': 'I',
    'mode_traitement': 'DOC05',
    'societe': societe.id,
    'site': site.id if site else '',
    'client_nom': 'ABC Automotive',
    'contact_client': 'Jean Martin',
    'description_piece': 'Défaut de montage sur une pièce livrée',
    'reference_piece': 'PIECE-I-001',
    'quantite_impactee': 4,
    'date_alerte_client': today_str,
    'accuse_reception_envoye': 'on',
}

response_i = c.post(reverse('reclamation:create'), i_data, follow=True)
rec_i = ReclamationClient.objects.filter(reference_piece='PIECE-I-001').first()

if rec_i:
    print(f"Created I: {rec_i.reference} (ID: {rec_i.pk})")
    print(f"Type: {rec_i.type_signalement} (Expected: I)")
    print(f"Support: {rec_i.mode_traitement} (Expected: DOC05)")

    # Fill Doc 05 Fiche Incident
    fiche_i, created = FicheIncidentDoc05.objects.update_or_create(
        reclamation=rec_i,
        defaults={
            'redacteur': 'Jean Martin',
            'date_detection': date.today(),
            'date_ouverture': date.today(),
            'site_concerne': site.nom if site else 'Site Production Tunis',
            'service_concerne': 'Montage / Assemblage',
            'description_incident': 'Erreur de référence sur emballage externe.',
            'action_immediate': 'Changement étiquettes et contrôle lot.',
            'responsable_action': 'Responsable Expédition',
            'date_limite_action': date.today() + timedelta(days=3),
            'statut_action': 'realisee',
            'causes_analyse': 'Etiquette imprimée avec mauvais code barre.',
            'action_corrective_perenne': 'Validation scannage code barre obligatoire à l\'emballage.',
            'est_valide': True,
            'date_validation': date.today(),
            'valide_par': user.get_full_name() or user.username,
        }
    )

    # Generate Doc 05 PDF
    pdf_res_i = c.get(reverse('reclamation:export_pdf_doc05', kwargs={'pk': rec_i.pk}))
    print(f"PDF Doc05 Export Status: {pdf_res_i.status_code}, Content-Type: {pdf_res_i.get('Content-Type')}, Content Size: {len(pdf_res_i.content)} bytes")
else:
    print("FAILED TO CREATE I INCIDENT")

# -------------------------------------------------------------------
# 4. TEST 3 — AMÉLIORATION INTERNE (AI) WITH DOC 05 WORKFLOW & PDF
# -------------------------------------------------------------------
print("\n--- 4. TEST 3 — AMÉLIORATION INTERNE (AI) [DOC 05] ---")

ai_data = {
    'type_signalement': 'AI',
    'mode_traitement': 'DOC05_FAI',
    'societe': societe.id,
    'site': site.id if site else '',
    'client_nom': 'Interne',
    'contact_client': 'Yassine Zerni',
    'description_piece': 'Amélioration du processus de contrôle qualité',
    'reference_piece': 'AI-001',
    'quantite_impactee': 1,
    'date_alerte_client': today_str,
    'accuse_reception_envoye': 'on',
}

response_ai = c.post(reverse('reclamation:create'), ai_data, follow=True)
rec_ai = ReclamationClient.objects.filter(reference_piece='AI-001').first()

if rec_ai:
    print(f"Created AI: {rec_ai.reference} (ID: {rec_ai.pk})")
    print(f"Type: {rec_ai.type_signalement} (Expected: AI)")
    print(f"Support: {rec_ai.mode_traitement} (Expected: DOC05_FAI)")

    # Fill Doc 05 Fiche Incident / Amélioration
    fiche_ai, created = FicheIncidentDoc05.objects.update_or_create(
        reclamation=rec_ai,
        defaults={
            'redacteur': 'Yassine Zerni',
            'date_detection': date.today(),
            'date_ouverture': date.today(),
            'site_concerne': site.nom if site else 'Site Production Tunis',
            'service_concerne': 'Qualité Interne',
            'description_incident': 'Digitalisation des fiches d\'auto-contrôle sur tablette.',
            'action_immediate': 'Mise en place prototype application sur poste 1.',
            'responsable_action': 'Yassine Zerni',
            'date_limite_action': date.today() + timedelta(days=14),
            'statut_action': 'en_cours',
            'causes_analyse': 'Temps de saisie papier trop élevé et risque de perte de fiches.',
            'action_corrective_perenne': 'Déploiement généralisé tablettes étanches sur 5 postes.',
            'est_valide': True,
            'date_validation': date.today(),
            'valide_par': user.get_full_name() or user.username,
        }
    )

    # Generate PDF Doc 05 for AI
    pdf_res_ai = c.get(reverse('reclamation:export_pdf_doc05', kwargs={'pk': rec_ai.pk}))
    print(f"PDF Doc05 (AI) Export Status: {pdf_res_ai.status_code}, Content-Type: {pdf_res_ai.get('Content-Type')}, Content Size: {len(pdf_res_ai.content)} bytes")
else:
    print("FAILED TO CREATE AI AMELIORATION")

# -------------------------------------------------------------------
# 5. DASHBOARD & PERIOD FILTER VERIFICATION
# -------------------------------------------------------------------
print("\n--- 5. DASHBOARD & PERIOD FILTER VERIFICATION ---")

dash_res = c.get(reverse('reclamation:dashboard'))
print(f"Dashboard Main Page Status: {dash_res.status_code}")

for p in ['7d', '30d', '3m', '6m', '12m', 'year']:
    ajax_res = c.get(f"{reverse('reclamation:dashboard')}?evolution_periode={p}&ajax=1", HTTP_X_REQUESTED_WITH='XMLHttpRequest')
    data = json.loads(ajax_res.content)
    print(f"AJAX Period '{p}': Status {ajax_res.status_code}, Success: {data.get('success')}, Title: {data.get('title_suffix')!r}, Labels: {len(data.get('labels', []))}")

# Test custom dates validation
future_res = c.get(f"{reverse('reclamation:dashboard')}?evolution_periode=custom&date_debut=2027-01-01&date_fin=2027-02-01&ajax=1", HTTP_X_REQUESTED_WITH='XMLHttpRequest')
data_fut = json.loads(future_res.content)
print(f"Future Date Rejection: Success={data_fut.get('success')}, Error='{data_fut.get('error')}'")

invalid_range_res = c.get(f"{reverse('reclamation:dashboard')}?evolution_periode=custom&date_debut=2026-09-01&date_fin=2026-08-01&ajax=1", HTTP_X_REQUESTED_WITH='XMLHttpRequest')
data_inv = json.loads(invalid_range_res.content)
print(f"Start > End Rejection: Success={data_inv.get('success')}, Error='{data_inv.get('error')}'")

# -------------------------------------------------------------------
# 6. RECLAMATION LIST VIEW VERIFICATION
# -------------------------------------------------------------------
print("\n--- 6. RECLAMATION LIST VIEW VERIFICATION ---")

list_res = c.get(reverse('reclamation:liste'))
print(f"List Page Status: {list_res.status_code}")

recs_all = ReclamationClient.objects.filter(reference_piece__in=['PIECE-R-001', 'PIECE-I-001', 'AI-001'])
print(f"Created Test Records Count: {recs_all.count()} (Expected: 3)")
for r in recs_all:
    print(f"  - Ref: {r.reference} | Type: {r.type_signalement} | Support: {r.mode_traitement} | Client: {r.client_nom} | Statut: {r.statut}")

print("\n=================================================================")
print("                       E2E TEST COMPLETED                        ")
print("=================================================================")
