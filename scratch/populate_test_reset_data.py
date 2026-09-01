import os
import sys
import django
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
django.setup()

from django.contrib.auth import get_user_model
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
from accounts.models import Societe, Site

User = get_user_model()
user = User.objects.first()
societe = Societe.objects.first()
site = Site.objects.first()

print("--- CREATING 3 COMPLETE TEST RECLAMATIONS ---")

# ─────────────────────────────────────────────────────────────────────────────
# 1. RECORD R — Réclamation Qualité (Formelle)
# ─────────────────────────────────────────────────────────────────────────────
rec_r = ReclamationClient.objects.create(
    type_signalement=ReclamationClient.TYPE_RECLAMATION,
    mode_traitement=ReclamationClient.MODE_8D,
    client_nom="ABC Automotive Tunisia",
    contact_client="Jean Dupont (Responsable Qualité Client)",
    description_piece="Faisceau de câblage moteur principal V6",
    reference_piece="REF-7701-AB88",
    quantite_impactee=450,
    date_alerte_client=date(2026, 8, 25),
    accuse_reception_envoye=True,
    numero_reclamation_client="REC-ABC-2026-089",
    est_probleme_repetitif=False,
    statut=ReclamationClient.STATUT_D7_D8,
    societe=societe,
    site=site,
    created_by=user,
    updated_by=user,
)

# Related 8D Objects
Participant8D.objects.create(reclamation=rec_r, user=user, fonction="Pilote Qualité", est_pilote=True)
Participant8D.objects.create(reclamation=rec_r, nom_externe="Marc Antoine", fonction="Responsable Production", est_pilote=False)
Participant8D.objects.create(reclamation=rec_r, nom_externe="Sarah Ben Ali", fonction="Ingénieur Méthodes", est_pilote=False)

DescriptionQQOQCCP.objects.create(
    reclamation=rec_r,
    description_client="Déconnexion intempestive du connecteur principal sous vibrations moteur.",
    quoi_est="Faisceau moteur V6 - Connecteur 24 broches non verrouillé.",
    quoi_nest_pas="Faisceaux habitacle ou éclairage.",
    qui_est="Ligne d'assemblage final chez ABC Automotive.",
    qui_nest_pas="Zone sous-traitance câblage.",
    ou_est="Poste de montage M04 Usine Sousse.",
    ou_nest_pas="Postes d'essais banc statique.",
    quand_est="Détecté le 25/08/2026 au contrôle final.",
    quand_nest_pas="Contrôle réception composants.",
    comment_est="Clip de retenue plastique cassé sur 12% des faisceaux.",
    comment_nest_pas="Broches pliées ou fils dénudés.",
    combien_est="450 pièces sur le lot L-9920.",
    combien_nest_pas="Totalité du lot (1200 pièces).",
    pourquoi_est="Risque d'arrêt de chaîne chez le constructeur.",
    pourquoi_nest_pas="Défaut purement esthétique.",
)

MesureConservatoireD3.objects.create(reclamation=rec_r, type_mesure="tri_interne", selectionne=True, quantite_triee=1200, quantite_nok=54, commentaires="1200 pièces triées en stock usine. 54 NOK isolées.")
MesureConservatoireD3.objects.create(reclamation=rec_r, type_mesure="tri_externe", selectionne=True, quantite_triee=450, quantite_nok=18, commentaires="450 pièces triées chez le client ABC Automotive.")
MesureConservatoireD3.objects.create(reclamation=rec_r, type_mesure="repere_unitaire", selectionne=True, quantite_triee=1650, quantite_nok=0, commentaires="Marquage point vert sur connecteurs 100% conformes.")
MesureConservatoireD3.objects.create(reclamation=rec_r, type_mesure="autre", selectionne=True, quantite_triee=1, quantite_nok=0, commentaires="Remplacement immédiat de la pince d'insertion mécanique sur ligne.")

AnalyseCausesDoubleAxeD4.objects.create(
    reclamation=rec_r,
    cause_principale_non_detection="Absence de test de traction axiale post-clipsage au banc d'essai final.",
    cause_principale_technique="Usure prématurée de l'ergot de guidage sur le moule d'injection plastique #3.",
    pourquoi_non_detection=[
        {"etape": 1, "pourquoi": "Le banc de test ne détectait pas le mauvais verrouillage", "statut": "avere", "justification": "Banc d'essai électrique uniquement sans test mécanique"},
        {"etape": 2, "pourquoi": "Procédure d'essai non mise à jour", "statut": "avere", "justification": "Gamme de contrôle 2024 inchangée"}
    ],
    pourquoi_technique=[
        {"etape": 1, "pourquoi": "Le clip de retenue se cassait à l'insertion", "statut": "avere", "justification": "Force d'insertion trop élevée (>35N)"},
        {"etape": 2, "pourquoi": "Ergot de guidage moule déformé", "statut": "avere", "justification": "Moule #3 en fin de vie après 500k cycles"}
    ],
)

ActionTestD5.objects.create(reclamation=rec_r, description_action="Test de remplacement de l'empreinte du moule #3 par un insert en acier trempé.", pilote_delai="Marc Antoine - 01/09/2026", conclusion="Test concluant : 0 casse sur 500 cycles.", ordre=1)

ActionPermanenteD6.objects.create(reclamation=rec_r, axe="technique", cause_racine="Usure moule #3", description="Remplacement de l'empreinte de moule #3 et ajout d'un capteur de force pneumatique.", pilote="Marc Antoine", delai=date(2026, 9, 15), date_realisation=date(2026, 9, 10), statut="realise", efficace=True, ordre=1)
ActionPermanenteD6.objects.create(reclamation=rec_r, axe="non_detection", cause_racine="Absence test mécanique EOL", description="Intégration d'un test de traction automatique 15N sur le banc d'essai EOL.", pilote="Sarah Ben Ali", delai=date(2026, 9, 20), statut="en_cours", ordre=2)

CapitalisationSMQSD7.objects.create(
    reclamation=rec_r,
    doc01_instruction=True, doc01_pilote_delai="Sarah Ben Ali - 05/09/2026",
    doc12_gammes=True, doc12_pilote_delai="Marc Antoine - 10/09/2026", precisez_gammes="Gamme d'assemblage G-402 Rev C",
    doc50_ok_demarrage=True, doc50_pilote_delai="Chef d'équipe M04"
)

ClotureRecevabiliteD8.objects.create(
    reclamation=rec_r,
    statut_recevabilite="recevable",
    motif_decision_factuel="La défaillance de l'ergot de guidage du moule #3 est avérée et imputable à AB Serve.",
    feliciter_equipe=True,
    date_envoi_8d_final=date(2026, 9, 1),
)

FicheIncidentDoc05.objects.create(reclamation=rec_r, redacteur="Yassine Slimani", site_concerne=site.nom if site else "Usine Sousse")

print(f"Created Record 1: {rec_r.reference} ({rec_r.get_type_signalement_display()} -> {rec_r.get_mode_traitement_display()})")

# ─────────────────────────────────────────────────────────────────────────────
# 2. RECORD I — Incident Client (Informel)
# ─────────────────────────────────────────────────────────────────────────────
rec_i = ReclamationClient.objects.create(
    type_signalement=ReclamationClient.TYPE_INCIDENT,
    mode_traitement=ReclamationClient.MODE_DOC05,
    client_nom="Sovab Logistics",
    contact_client="Alain Leroy (Logistique & Transport)",
    description_piece="Carton d'emballage renforcé 400x300x200",
    reference_piece="EMB-BOX-40",
    quantite_impactee=25,
    date_alerte_client=date(2026, 8, 28),
    accuse_reception_envoye=True,
    statut=ReclamationClient.STATUT_D4_D6,
    societe=societe,
    site=site,
    created_by=user,
    updated_by=user,
)

FicheIncidentDoc05.objects.create(
    reclamation=rec_i,
    redacteur="Yassine Slimani",
    date_detection=date(2026, 8, 28),
    date_ouverture=date(2026, 8, 28),
    site_concerne=site.nom if site else "Usine Sousse",
    evenement_qualite=True,
    evenement_securite=False,
    evenement_environnement=False,
    quoi_reponse="Déchirure du rabat inférieur lors de la manutention palettisée.",
    qui_reponse="Opérateur logistique quai d'expédition Sovab.",
    ou_reponse="Plateforme de distribution Sovab Lyon.",
    quand_reponse="Lors du déchargement camion du 28/08/2026.",
    comment_reponse="Ruban adhésif insuffisamment appliqué sur la sous-face des palettes.",
    combien_reponse="25 cartons détériorés sur un total de 500.",
    autre_reponse="Produits internes intacts, seul le conditionnement extérieur est impacté.",
    motif_non_conformite="Tension de la bande adhésive automatique trop faible sur la filmeuse #2.",
    pourquoi_chains=[
        {"p1": "Rabats de carton ouverts", "p2": "Adhésif décollé", "p3": "Pression du rouleau adhésif insuffisante", "p4": "Ressort de rappel usé", "p5": "Absence de maintenance préventive mensuelle", "conclusion": "Changer le ressort et intégrer la filmeuse au plan de maintenance préventive"}
    ],
    deja_signale=False,
    particularites_changements=True,
    particularites_details="Changement de fournisseur de ruban adhésif (passage à du polypropylène 32µm).",
    risque_similaire=False,
    mesures_immediates=[
        {"description": "Sur-scotchage manuel des 25 cartons impactés", "pilote": "Alain Leroy", "delai": "2026-08-28", "realise_le": "2026-08-28"}
    ],
    actions_correctives=[
        {"description": "Remplacement du ressort de tension filmeuse #2", "pilote": "Equipe Maintenance", "delai": "2026-09-02", "realise_le": "2026-08-30", "efficacite": "Oui, 500 cartons expédiés sans défaut"}
    ],
    date_cloture=date(2026, 8, 31),
)

print(f"Created Record 2: {rec_i.reference} ({rec_i.get_type_signalement_display()} -> {rec_i.get_mode_traitement_display()})")

# ─────────────────────────────────────────────────────────────────────────────
# 3. RECORD AI — Amélioration Interne
# ─────────────────────────────────────────────────────────────────────────────
rec_ai = ReclamationClient.objects.create(
    type_signalement=ReclamationClient.TYPE_AMELIORATION,
    mode_traitement=ReclamationClient.MODE_DOC05_FAI,
    client_nom="Service Assemblage Interne",
    contact_client="Karim Najar (Chef d'Atelier)",
    description_piece="Plaquette de frein arrière Série B",
    reference_piece="PLQ-BRK-B9",
    quantite_impactee=10,
    date_alerte_client=date(2026, 8, 30),
    accuse_reception_envoye=True,
    statut=ReclamationClient.STATUT_D1_D3,
    societe=societe,
    site=site,
    created_by=user,
    updated_by=user,
)

FicheIncidentDoc05.objects.create(
    reclamation=rec_ai,
    redacteur="Karim Najar",
    date_detection=date(2026, 8, 30),
    date_ouverture=date(2026, 8, 30),
    site_concerne="Atelier UAP2",
    evenement_qualite=True,
    evenement_securite=True,
    evenement_environnement=False,
    quoi_reponse="Présence de bavures métalliques sur l'encoche de fixation.",
    qui_reponse="Opérateur d'assemblage poste 3.",
    ou_reponse="Poste d'ébavurage manuel UAP2.",
    quand_reponse="En début d'équipe du matin (06h00).",
    comment_reponse="Gêne lors de l'insertion dans l'étrier de frein.",
    combien_reponse="10 pièces sur 200 inspectées.",
    autre_reponse="Proposition d'ajout d'une meuleuse d'ébavurage automatique.",
    motif_non_conformite="Lime manuelle usée provoquant des bavures irrégulières.",
    pourquoi_chains=[
        {"p1": "Gêne à l'assemblage", "p2": "Bavures métalliques", "p3": "Ebavurage manuel irrégulier", "p4": "Outil manuel en fin de vie", "p5": "Absence de fréquence de remplacement des limes", "conclusion": "Définir une durée de vie limite pour les limes d'ébavurage (2000 pièces max)"}
    ],
    deja_signale=True,
    deja_signale_details="Signalé verbalement le mois dernier.",
    particularites_changements=False,
    risque_similaire=True,
    risque_similaire_details="Ligne d'assemblage Série A (plaquettes avant).",
    mesures_immediates=[
        {"description": "Remplacement immédiat de la lime du poste 3 par une lime neuve", "pilote": "Karim Najar", "delai": "2026-08-30", "realise_le": "2026-08-30"}
    ],
    actions_correctives=[
        {"description": "Mise en place d'un bac de détrompage et étalonnage des outils d'ébavurage", "pilote": "Services Méthodes", "delai": "2026-09-10", "realise_le": "", "efficacite": "En cours"}
    ],
)

print(f"Created Record 3: {rec_ai.reference} ({rec_ai.get_type_signalement_display()} -> {rec_ai.get_mode_traitement_display()})")
print(f"--- TOTAL RECLAMATIONS IN DATABASE: {ReclamationClient.objects.count()} ---")
