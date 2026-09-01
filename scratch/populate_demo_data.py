import os
import sys
import django
from datetime import date, timedelta

sys.path.insert(0, '.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')
django.setup()

from accounts.models import User, Societe
from accident_travail.models import ActionCorrective
from reclamation_client.models import (
    ReclamationClient, DescriptionQQOQCCP, MesureConservatoireD3,
    AnalyseCausesDoubleAxeD4, ActionTestD5, CapitalisationSMQSD7,
    ClotureRecevabiliteD8, Participant8D
)

user = User.objects.filter(is_superuser=True).first() or User.objects.first()
societe = Societe.objects.first()

print(f"Utilisateur pour création : {user} | Société : {societe}")

# Supprimer les données de test précédentes avec préfixe [TEST DEMO]
ReclamationClient.objects.filter(client_nom__icontains="[TEST DEMO]").delete()

today = date.today()

# ==============================================================================
# SCÉNARIO 1 : Réclamation Qualité (R) — ABC Automotive
# ==============================================================================
rec1 = ReclamationClient.objects.create(
    type_signalement="R",
    mode_traitement="8D",
    societe=societe,
    site=None,
    client_nom="[TEST DEMO] ABC Automotive",
    contact_client="Jean Dupont (Resp. Qualité Client)",
    description_piece="Support Moteur ALU V6",
    reference_piece="PIECE-001",
    quantite_impactee=100,
    date_alerte_client=today - timedelta(days=10),
    date_ouverture=today - timedelta(days=9),
    date_incident=today - timedelta(days=12),
    statut=ReclamationClient.STATUT_D4_D6,
    accuse_reception_envoye=True,
    date_accuse_reception=today - timedelta(days=9),
    created_by=user,
)

# D1 Participants
Participant8D.objects.create(reclamation=rec1, user=user, fonction="Pilote Qualité 8D", est_pilote=True)
Participant8D.objects.create(reclamation=rec1, nom_externe="Marc Lemoine", fonction="Expert Procédé Assemblage")

# D2 QQOQCCP
DescriptionQQOQCCP.objects.create(
    reclamation=rec1,
    description_client="Défaut de montage constaté lors du contrôle à la réception client sur lot PIECE-001.",
    quoi_est="Bavure de bavure non ébavurée sur le trou de fixation A3.",
    quoi_nest_pas="Trou de fixation B1 ou B2 intacts.",
    qui_est="Ligne de montage 2 - Opérateur A",
    qui_nest_pas="Ligne de montage 1",
    ou_est="Poste d'ébavurage final",
    ou_nest_pas="Poste de moulage",
    quand_est="Post-assemblage du 15 du mois",
    quand_nest_pas="Lors du pré-assemblage",
    comment_est="Ecartement au calibre > 0.05mm",
    comment_nest_pas="Jeu normal d'assemblage",
    combien_est="12 pièces NOK sur 100 inspectées",
    combien_nest_pas="88 pièces conformes",
    pourquoi_est="Risque d'usure prématurée du silentbloc",
    pourquoi_nest_pas="Pas de rupture structurelle immédiate",
)

# D3 Mesures Conservatoires
MesureConservatoireD3.objects.update_or_create(
    reclamation=rec1, type_mesure="tri_interne",
    defaults={"selectionne": True, "quantite_triee": 250, "quantite_nok": 5, "commentaires": "Tri en magasin interne"}
)
MesureConservatoireD3.objects.update_or_create(
    reclamation=rec1, type_mesure="tri_externe",
    defaults={"selectionne": True, "quantite_triee": 100, "quantite_nok": 12, "commentaires": "Tri effectué sur le site client ABC Automotive"}
)

# D4 Double Axe 5 Pourquoi
p_nd_1 = [
    "Le défaut n'a pas été détecté au contrôle final.",
    "Le contrôle n'a pas été réalisé correctement.",
    "L'instruction de contrôle était imprécise.",
    "L'instruction n'avait pas été mise à jour.",
    "Instruction de contrôle non mise à jour."
]

p_tech_1 = [
    "Le défaut est apparu après un mauvais réglage du poste.",
    "Le réglage était incorrect.",
    "Le paramètre n'était pas correctement défini.",
    "Le standard de réglage était incomplet.",
    "Standard de réglage incomplet."
]

AnalyseCausesDoubleAxeD4.objects.create(
    reclamation=rec1,
    cause_principale_non_detection=p_nd_1[4],
    cause_principale_technique=p_tech_1[4],
    pourquoi_non_detection=p_nd_1,
    pourquoi_technique=p_tech_1,
)

# Actions Correctives (ActionCorrective)
ActionCorrective.objects.create(
    reclamation=rec1,
    axe="non_detection",
    cause_racine=p_nd_1[4],
    description="Mettre à jour l'instruction de contrôle final au poste ébavurage",
    pilote="Resp. Qualité Produit",
    delai=today - timedelta(days=2),
    date_realisation=today - timedelta(days=2),
    statut="realise",
    efficace=None,
    ordre=1,
)

ActionCorrective.objects.create(
    reclamation=rec1,
    axe="technique",
    cause_racine=p_tech_1[4],
    description="Mettre à jour le standard de réglage de la broche d'ébarbage",
    pilote="Méthodes / Process",
    delai=today + timedelta(days=5),
    statut="en_cours",
    efficace=None,
    audit_poste_doc37=True,
    ordre=2,
)

ActionCorrective.objects.create(
    reclamation=rec1,
    axe="non_detection",
    cause_racine=p_nd_1[4],
    description="Vérifier l'efficacité du contrôle sur le poste d'ébavurage (Audit de poste Doc 37)",
    pilote="Superviseur Qualité",
    delai=today + timedelta(days=12),
    statut="non_demarre",
    efficace=None,
    ordre=3,
)

print(f"[OK] Scénario 1 créé : {rec1.reference} — {rec1.client_nom}")


# ==============================================================================
# SCÉNARIO 2 : Réclamation Qualité (R) — XYZ Industries (Clôturé & Recevable)
# ==============================================================================
rec2 = ReclamationClient.objects.create(
    type_signalement="R",
    mode_traitement="8D",
    societe=societe,
    site=None,
    client_nom="[TEST DEMO] XYZ Industries",
    contact_client="Sophie Martin (Achats)",
    description_piece="Carter d'Embrayage renforcé",
    reference_piece="PIECE-099",
    quantite_impactee=40,
    date_alerte_client=today - timedelta(days=30),
    date_ouverture=today - timedelta(days=29),
    date_incident=today - timedelta(days=32),
    statut=ReclamationClient.STATUT_CLOTURE,
    accuse_reception_envoye=True,
    date_accuse_reception=today - timedelta(days=29),
    created_by=user,
)

AnalyseCausesDoubleAxeD4.objects.create(
    reclamation=rec2,
    cause_principale_non_detection="Manque de gabarit de contrôle à la livraison",
    cause_principale_technique="Usure prématurée de la fraise d'usinage",
    pourquoi_non_detection=["Non détecté", "Pas de contrôle intermédiaire", "Manque d'outil dédié", "Absence de procédure", "Manque de gabarit de contrôle à la livraison"],
    pourquoi_technique=["Défaut de cote", "Outil détérioré", "Fréquence de changement trop longue", "Absence de compteur de cycles", "Usure prématurée de la fraise d'usinage"],
)

ActionCorrective.objects.create(
    reclamation=rec2,
    axe="technique",
    cause_racine="Usure prématurée de la fraise d'usinage",
    description="Remplacement systématique des outils d'usinage toutes les 500 pièces",
    pilote="Resp. Maintenance",
    delai=today - timedelta(days=15),
    date_realisation=today - timedelta(days=16),
    date_verification=today - timedelta(days=5),
    statut="verifie",
    efficace=True,
    ordre=1,
)

ActionCorrective.objects.create(
    reclamation=rec2,
    axe="non_detection",
    cause_racine="Manque de gabarit de contrôle à la livraison",
    description="Acquisition et mise en service d'un gabarit de contrôle Go/No-Go",
    pilote="Resp. Qualité",
    delai=today - timedelta(days=10),
    date_realisation=today - timedelta(days=10),
    date_verification=today - timedelta(days=4),
    statut="verifie",
    efficace=True,
    ordre=2,
)

ClotureRecevabiliteD8.objects.create(
    reclamation=rec2,
    statut_recevabilite=ClotureRecevabiliteD8.RECEVABILITE_RECEVABLE,
    motif_decision_factuel="Réclamation recevable. L'analyse des pièces retournées confirme le non-respect des tolérances de la fiche technique.",
    feliciter_equipe=True,
    date_felicitations=today - timedelta(days=2),
    date_envoi_8d_final=today - timedelta(days=2),
)

print(f"[OK] Scénario 2 créé : {rec2.reference} — {rec2.client_nom}")


# ==============================================================================
# SCÉNARIO 3 : Incident Client (I) — Client Test 2 (En cours)
# ==============================================================================
rec3 = ReclamationClient.objects.create(
    type_signalement="I",
    mode_traitement="DOC05",
    societe=societe,
    site=None,
    client_nom="[TEST DEMO] Client Test 2",
    contact_client="Paul Valéry",
    description_piece="Lot d'emballages carton non conforme",
    reference_piece="EMB-2024",
    quantite_impactee=500,
    date_alerte_client=today - timedelta(days=4),
    date_ouverture=today - timedelta(days=3),
    statut=ReclamationClient.STATUT_D1_D3,
    accuse_reception_envoye=True,
    date_accuse_reception=today - timedelta(days=3),
    created_by=user,
)

ActionCorrective.objects.create(
    reclamation=rec3,
    axe="autre",
    cause_racine="Erreur d'étiquetage fournisseur emballage",
    description="Isoler le lot d'emballages défectueux et demander le remplacement au fournisseur",
    pilote="Responsable Logistique",
    delai=today + timedelta(days=3),
    statut="en_cours",
    efficace=None,
    ordre=1,
)

print(f"[OK] Scénario 3 créé : {rec3.reference} — {rec3.client_nom}")


# ==============================================================================
# SCÉNARIO 4 : Incident Client (I) — Client Test 3 (Clôturé & Non Recevable)
# ==============================================================================
rec4 = ReclamationClient.objects.create(
    type_signalement="I",
    mode_traitement="DOC05",
    societe=societe,
    site=None,
    client_nom="[TEST DEMO] Client Test 3",
    contact_client="Claire Thomas",
    description_piece="Axe de transmission A-10",
    reference_piece="TRANS-A10",
    quantite_impactee=5,
    date_alerte_client=today - timedelta(days=20),
    date_ouverture=today - timedelta(days=19),
    statut=ReclamationClient.STATUT_CLOTURE,
    accuse_reception_envoye=True,
    date_accuse_reception=today - timedelta(days=19),
    created_by=user,
)

ClotureRecevabiliteD8.objects.create(
    reclamation=rec4,
    statut_recevabilite=ClotureRecevabiliteD8.RECEVABILITE_NON_RECEVABLE,
    motif_decision_factuel="Réclamation NON RECEVABLE. L'expertise contradictoire démontre que les pièces ont été détériorées lors d'une mauvaise manutention sur le site du client (choc mécanique postérieur à la livraison). Le procès-verbal de livraison signé sans réserve fait foi.",
    feliciter_equipe=False,
    date_envoi_8d_final=today - timedelta(days=10),
)

print(f"[OK] Scénario 4 créé : {rec4.reference} — {rec4.client_nom}")


# ==============================================================================
# SCÉNARIO 5 : Amélioration Interne (AI) — Équipe Interne (En cours)
# ==============================================================================
rec5 = ReclamationClient.objects.create(
    type_signalement="AI",
    mode_traitement="8D",
    societe=societe,
    site=None,
    client_nom="[TEST DEMO] Équipe Interne QSE",
    contact_client="Animateur Qualité Interne",
    description_piece="Ligne de conditionnement automatique",
    reference_piece="LIGNE-COND-01",
    quantite_impactee=0,
    date_alerte_client=today - timedelta(days=7),
    date_ouverture=today - timedelta(days=6),
    statut=ReclamationClient.STATUT_D4_D6,
    accuse_reception_envoye=False,
    created_by=user,
)

AnalyseCausesDoubleAxeD4.objects.create(
    reclamation=rec5,
    cause_principale_non_detection="Vérification manuelle sujette à fatigue visuelle",
    cause_principale_technique="Absence de détrompeur optique à la fermeture des cartons",
    pourquoi_non_detection=["Détecté trop tard", "Contrôle manuel uniquement", "Attention fluctuante", "Pas de double contrôle", "Vérification manuelle sujette à fatigue visuelle"],
    pourquoi_technique=["Absence de détection auto", "Pas de capteur", "Équipement initial non pourvu", "Priorité non accordée lors de l'installation", "Absence de détrompeur optique à la fermeture des cartons"],
)

ActionCorrective.objects.create(
    reclamation=rec5,
    axe="technique",
    cause_racine="Absence de détrompeur optique",
    description="Installer une cellule optique de détection sur le convoyeur de fermeture",
    pilote="Service Technique",
    delai=today + timedelta(days=10),
    statut="en_cours",
    efficace=None,
    ordre=1,
)

ActionCorrective.objects.create(
    reclamation=rec5,
    axe="non_detection",
    cause_racine="Vérification manuelle",
    description="Rédiger un standard de contrôle visuel renforcé pendant la phase transitoire",
    pilote="Qualité Atelier",
    delai=today - timedelta(days=1),
    date_realisation=today - timedelta(days=1),
    statut="realise",
    efficace=None,
    ordre=2,
)

print(f"[OK] Scénario 5 créé : {rec5.reference} — {rec5.client_nom}")

print("\nToutes les 5 Réclamations de démonstration ont été créées avec succès !")
