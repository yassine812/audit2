import os, sys, django
from datetime import date

sys.path.insert(0, '.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')
django.setup()

from accounts.models import Societe, Section, Site, User
from reclamation_client.models import (
    ReclamationClient, Participant8D, DescriptionQQOQCCP,
    MesureConservatoireD3, AnalyseCausesDoubleAxeD4, ActionTestD5,
    ActionPermanenteD6, CapitalisationSMQSD7, ClotureRecevabiliteD8
)

# 1. Societe, Section & Site
societe = Societe.objects.first() or Societe.objects.create(nom="Société Test1")
section = Section.objects.first() or Section.objects.create(nom="Section Test", societe=societe)
site = Site.objects.first() or Site.objects.create(nom="Site Production Tunis", section=section)

# 2. Reclamation Client
rec, created = ReclamationClient.objects.get_or_create(
    reference="REC20260085",
    defaults={
        "type_signalement": ReclamationClient.TYPE_RECLAMATION,
        "mode_traitement": ReclamationClient.MODE_8D,
        "statut": ReclamationClient.STATUT_CLOTURE,
        "societe": societe,
        "section": section,
        "site": site,
        "client_nom": "ABC Automotive Tunisia",
        "contact_client": "Jean Dupont",
        "date_alerte_client": date(2026, 8, 25),
        "date_ouverture": date(2026, 8, 25),
        "description_piece": "Support métallique de fixation — défaut de montage",
        "reference_piece": "PIECE-001",
        "quantite_impactee": 12,
        "est_probleme_repetitif": False,
        "accuse_reception_envoye": True,
        "date_accuse_reception": date(2026, 8, 25),
        "numero_reclamation_client": "CL-2026-0085",
    }
)
if not created:
    rec.type_signalement = ReclamationClient.TYPE_RECLAMATION
    rec.mode_traitement = ReclamationClient.MODE_8D
    rec.statut = ReclamationClient.STATUT_CLOTURE
    rec.societe = societe
    rec.section = section
    rec.site = site
    rec.client_nom = "ABC Automotive Tunisia"
    rec.contact_client = "Jean Dupont"
    rec.date_alerte_client = date(2026, 8, 25)
    rec.date_ouverture = date(2026, 8, 25)
    rec.description_piece = "Support métallique de fixation — défaut de montage"
    rec.reference_piece = "PIECE-001"
    rec.quantite_impactee = 12
    rec.est_probleme_repetitif = False
    rec.accuse_reception_envoye = True
    rec.date_accuse_reception = date(2026, 8, 25)
    rec.numero_reclamation_client = "CL-2026-0085"
    rec.save()

print(f"Reclamation reference: {rec.reference} (id={rec.pk})")

# 3. Participants D1
rec.participants.all().delete()
Participant8D.objects.create(reclamation=rec, nom_externe="Ahmed Ben Ali", fonction="Responsable Qualité", est_pilote=True)
Participant8D.objects.create(reclamation=rec, nom_externe="Yassine Martin", fonction="Responsable Production", est_pilote=False)
Participant8D.objects.create(reclamation=rec, nom_externe="Sarah Dupont", fonction="Méthodes", est_pilote=False)
Participant8D.objects.create(reclamation=rec, nom_externe="Karim Trabelsi", fonction="Maintenance", est_pilote=False)

# 4. Description D2 (QQOQCCP)
DescriptionQQOQCCP.objects.update_or_create(
    reclamation=rec,
    defaults={
        "description_client": "Le client a constaté un défaut de montage sur plusieurs supports métalliques livrés le 24/08/2026. La pièce présente un mauvais positionnement de la fixation, empêchant son montage correct sur l'ensemble final.",
        "quoi_est": "Support métallique présentant un défaut de positionnement de la fixation.",
        "quoi_nest_pas": "Le défaut ne concerne pas la matière première ni les dimensions générales du support.",
        "qui_est": "Le défaut concerne les pièces assemblées sur la ligne de montage client.",
        "qui_nest_pas": "Les autres références produites sur la même ligne ne présentent pas ce défaut.",
        "ou_est": "Le défaut a été détecté sur le site client ABC Automotive Tunisia.",
        "ou_nest_pas": "Le défaut n'a pas été identifié sur les autres sites clients.",
        "quand_est": "Le défaut a été détecté le 25/08/2026 lors du montage des pièces.",
        "quand_nest_pas": "Le défaut n'était pas identifié lors du contrôle final avant expédition.",
        "comment_est": "La fixation est positionnée de manière incorrecte et empêche l'assemblage.",
        "comment_nest_pas": "La fixation n'est pas cassée et la pièce reste visuellement conforme sur plusieurs contrôles.",
        "combien_est": "12 pièces non conformes ont été identifiées sur un lot de 120 pièces.",
        "combien_nest_pas": "Les 108 autres pièces du lot ont été contrôlées conformes.",
        "pourquoi_est": "Le défaut peut provoquer un arrêt du montage chez le client.",
        "pourquoi_nest_pas": "Le défaut ne présente pas de risque de sécurité pour l'utilisateur final.",
    }
)

# 5. Mesures Conservatoires D3
rec.mesures_conservatoires.all().delete()
MesureConservatoireD3.objects.create(
    reclamation=rec, type_mesure="tri_interne", selectionne=True, quantite_triee=120, quantite_nok=12, commentaires="Tri complet du stock disponible avant expédition."
)
MesureConservatoireD3.objects.create(
    reclamation=rec, type_mesure="tri_externe", selectionne=True, quantite_triee=80, quantite_nok=8, commentaires="Tri réalisé chez le client sur le stock disponible."
)
MesureConservatoireD3.objects.create(
    reclamation=rec, type_mesure="repere_unitaire", selectionne=True, quantite_triee=200, quantite_nok=20, commentaires="Les pièces contrôlées ont été identifiées individuellement."
)
MesureConservatoireD3.objects.create(
    reclamation=rec, type_mesure="autre", selectionne=True, quantite_triee=200, quantite_nok=20, commentaires="Blocage temporaire du lot concerné et information immédiate du service qualité."
)

# 6. Analyse des Causes D4 (5 Pourquoi)
non_detection_5w = [
    {"etape": 1, "pourquoi": "Le défaut n'a pas été détecté lors du contrôle final.", "statut": "avere", "justification": ""},
    {"etape": 2, "pourquoi": "L'opérateur n'a pas effectué le contrôle sur deux pièces simultanément.", "statut": "avere", "justification": ""},
    {"etape": 3, "pourquoi": "Cette méthode de contrôle n'était pas explicitement demandée dans la gamme.", "statut": "avere", "justification": ""},
    {"etape": 4, "pourquoi": "La gamme de contrôle ne précisait pas le nombre de pièces à contrôler simultanément.", "statut": "avere", "justification": ""},
    {"etape": 5, "pourquoi": "Le standard de contrôle n'avait pas été mis à jour après modification du processus.", "statut": "avere", "justification": ""},
]

technique_5w = [
    {"etape": 1, "pourquoi": "Le support présente un mauvais positionnement de la fixation.", "statut": "avere", "justification": ""},
    {"etape": 2, "pourquoi": "L'outillage d'assemblage présente un positionnement insuffisamment précis.", "statut": "avere", "justification": ""},
    {"etape": 3, "pourquoi": "Le contrôle périodique de l'outillage n'a pas été réalisé dans le délai prévu.", "statut": "avere", "justification": ""},
    {"etape": 4, "pourquoi": "Le planning de maintenance préventive n'a pas été correctement suivi.", "statut": "avere", "justification": ""},
    {"etape": 5, "pourquoi": "Le système de suivi du planning de maintenance ne déclenchait pas d'alerte automatique.", "statut": "avere", "justification": ""},
]

AnalyseCausesDoubleAxeD4.objects.update_or_create(
    reclamation=rec,
    defaults={
        "cause_principale_non_detection": "AVÉRÉ : la gamme de contrôle doit être mise à jour afin de préciser la méthode de contrôle.",
        "cause_principale_technique": "AVÉRÉ : le suivi du planning de maintenance doit être renforcé et l'outillage doit être contrôlé.",
        "pourquoi_non_detection": non_detection_5w,
        "pourquoi_technique": technique_5w,
    }
)

# 7. Actions Tests D5
rec.actions_tests.all().delete()
ActionTestD5.objects.create(reclamation=rec, description_action="Contrôler 100 pièces avec la nouvelle méthode de contrôle.", pilote_delai="Ahmed Ben Ali - 26/08/2026", conclusion="Test concluant : aucun défaut non détecté.", ordre=1)
ActionTestD5.objects.create(reclamation=rec, description_action="Contrôler le positionnement de l'outillage d'assemblage.", pilote_delai="Karim Trabelsi - 27/08/2026", conclusion="Jeu excessif identifié sur l'outillage.", ordre=2)
ActionTestD5.objects.create(reclamation=rec, description_action="Réaliser une production pilote après réglage de l'outillage.", pilote_delai="Yassine Martin - 28/08/2026", conclusion="Production pilote conforme.", ordre=3)
ActionTestD5.objects.create(reclamation=rec, description_action="Vérifier l'efficacité du nouveau contrôle final.", pilote_delai="Sarah Dupont - 29/08/2026", conclusion="Contrôle conforme sur l'ensemble des pièces testées.", ordre=4)

# 8. Actions Permanentes D6
rec.actions_permanentes.all().delete()
ActionPermanenteD6.objects.create(reclamation=rec, description="Réparer et recalibrer l'outillage d'assemblage.", pilote="Karim Trabelsi", delai=date(2026, 8, 27), date_realisation=date(2026, 8, 27), statut="verifie", efficace=True, ordre=1)
ActionPermanenteD6.objects.create(reclamation=rec, description="Mettre à jour la gamme de contrôle.", pilote="Sarah Dupont", delai=date(2026, 8, 28), date_realisation=date(2026, 8, 28), statut="verifie", efficace=True, ordre=2)
ActionPermanenteD6.objects.create(reclamation=rec, description="Former les opérateurs à la nouvelle méthode de contrôle.", pilote="Ahmed Ben Ali", delai=date(2026, 8, 29), date_realisation=date(2026, 8, 29), statut="verifie", efficace=True, ordre=3)
ActionPermanenteD6.objects.create(reclamation=rec, description="Mettre en place un contrôle périodique renforcé de l'outillage.", pilote="Karim Trabelsi", delai=date(2026, 8, 30), date_realisation=date(2026, 8, 30), statut="verifie", efficace=True, ordre=4)

# 9. Capitalisation D7
CapitalisationSMQSD7.objects.update_or_create(
    reclamation=rec,
    defaults={
        "doc01_instruction": True, "doc01_pilote_delai": "Sarah Dupont - 29/08/2026",
        "doc5_24_competences": True, "doc5_24_pilote_delai": "Ahmed Ben Ali - 29/08/2026",
        "doc21_formation": True, "doc21_pilote_delai": "Ahmed Ben Ali - 30/08/2026",
        "doc34_habilitation_indiv": True, "doc34_pilote_delai": "Ahmed Ben Ali - 30/08/2026",
        "doc38_habilitation_poste": True, "doc38_pilote_delai": "Ahmed Ben Ali - 30/08/2026",
        "doc12_gammes": True, "doc12_pilote_delai": "Sarah Dupont - 28/08/2026", "precisez_gammes": "Gamme de contrôle final et gamme d'assemblage du support PIECE-001.",
        "doc50_ok_demarrage": True, "doc50_pilote_delai": "Yassine Martin - 31/08/2026",
    }
)

# 10. Cloture & Recevabilite D8
ClotureRecevabiliteD8.objects.update_or_create(
    reclamation=rec,
    defaults={
        "statut_recevabilite": "recevable",
        "motif_decision_factuel": "La responsabilité AB Serve est engagée car le défaut provient du processus d'assemblage interne et n'a pas été détecté avant expédition.",
        "feliciter_equipe": True,
        "date_felicitations": date(2026, 8, 31),
        "date_envoi_8d_final": date(2026, 8, 31),
    }
)

print("SUCCESSFULLY CREATED COMPLETE 8D RECLAMATION!")
