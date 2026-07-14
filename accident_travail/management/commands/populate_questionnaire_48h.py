"""
Commande de management : populate_questionnaire_48h

Peuple le modèle QuestionnaireTemplate avec toutes les questions
du questionnaire d'analyse 48h extrait du formulaire Excel officiel.

Usage :
    python manage.py populate_questionnaire_48h
    python manage.py populate_questionnaire_48h --flush  # efface avant de recharger
"""

from django.core.management.base import BaseCommand

from accident_travail.models import QuestionnaireTemplate

QUESTIONS = [
    # ─── Section 1 : L'organisation du travail ────────────────────────────
    ("1.1",  "1 — L'organisation du travail", "L'activité réalisée a-t-elle été préparée ?", False, "", ""),
    ("1.2",  "1 — L'organisation du travail", "La victime gérait-elle un événement inhabituel ?", False, "", ""),
    ("1.3",  "1 — L'organisation du travail", "Le temps alloué à la tâche était-il suffisant ?", False, "", ""),
    ("1.4",  "1 — L'organisation du travail", "La procédure / mode opératoire existait-il ?", False, "", ""),
    ("1.4b", "1 — L'organisation du travail", "Si oui, était-il adapté à la situation ?", True, "1.4", "O"),
    ("1.5",  "1 — L'organisation du travail", "La procédure / mode opératoire était-il connu de la victime ?", False, "", ""),
    ("1.6",  "1 — L'organisation du travail", "La procédure / mode opératoire était-il respecté ?", False, "", ""),
    ("1.7",  "1 — L'organisation du travail", "Des consignes de sécurité existaient-elles pour cette activité ?", False, "", ""),
    ("1.7b", "1 — L'organisation du travail", "Si oui, étaient-elles connues de la victime ?", True, "1.7", "O"),
    ("1.8",  "1 — L'organisation du travail", "Le poste de travail faisait-il l'objet d'une évaluation des risques ?", False, "", ""),
    ("1.9",  "1 — L'organisation du travail", "Le risque à l'origine de l'accident était-il identifié dans le DUER ?", False, "", ""),
    ("1.10", "1 — L'organisation du travail", "Des mesures de prévention étaient-elles prévues ?", False, "", ""),
    ("1.11", "1 — L'organisation du travail", "Ces mesures de prévention étaient-elles mises en œuvre ?", False, "", ""),
    ("1.12", "1 — L'organisation du travail", "Existait-il un plan de prévention ou un protocole de sécurité ?", False, "", ""),

    # ─── Section 2 : La victime ────────────────────────────────────────────
    ("2.1",  "2 — La victime", "La victime avait-elle reçu une formation à la sécurité lors de son embauche ?", False, "", ""),
    ("2.2",  "2 — La victime", "La victime avait-elle reçu une formation spécifique au poste ?", False, "", ""),
    ("2.3",  "2 — La victime", "La victime avait-elle suivi les formations réglementaires obligatoires (habilitations, CACES…) ?", False, "", ""),
    ("2.4",  "2 — La victime", "La visite médicale de la victime était-elle à jour ?", False, "", ""),
    ("2.5",  "2 — La victime", "La victime présentait-elle des restrictions d'aptitude médicale ?", False, "", ""),
    ("2.5b", "2 — La victime", "Si oui, le poste respectait-il ces restrictions ?", True, "2.5", "O"),

    # ─── Section 3 : La tâche demandée / l'activité réalisée ──────────────
    ("3.1",  "3 — La tâche demandée / l'activité réalisée", "La tâche demandée était-elle dans les attributions habituelles de la victime ?", False, "", ""),
    ("3.2",  "3 — La tâche demandée / l'activité réalisée", "La tâche demandée était-elle conforme à la fiche de poste ?", False, "", ""),
    ("3.3",  "3 — La tâche demandée / l'activité réalisée", "La charge de travail était-elle normale ?", False, "", ""),
    ("3.4",  "3 — La tâche demandée / l'activité réalisée", "La victime travaillait-elle seule au moment de l'accident ?", False, "", ""),
    ("3.5",  "3 — La tâche demandée / l'activité réalisée", "La communication entre les intervenants était-elle adaptée ?", False, "", ""),
    ("3.6",  "3 — La tâche demandée / l'activité réalisée", "Un permis de travail était-il requis ?", False, "", ""),
    ("3.6b", "3 — La tâche demandée / l'activité réalisée", "Si oui, avait-il été délivré ?", True, "3.6", "O"),
    ("3.7",  "3 — La tâche demandée / l'activité réalisée", "La victime avait-elle été informée des risques spécifiques à cette tâche ?", False, "", ""),
    ("3.8",  "3 — La tâche demandée / l'activité réalisée", "Une co-activité était-elle à l'origine de l'accident ?", False, "", ""),
    ("3.9",  "3 — La tâche demandée / l'activité réalisée", "La victime était-elle sous pression temporelle ?", False, "", ""),
    ("3.10", "3 — La tâche demandée / l'activité réalisée", "La victime était-elle exposée à des facteurs de pénibilité ?", False, "", ""),

    # ─── Section 4 : Le milieu ─────────────────────────────────────────────
    ("4.1",  "4 — Le milieu", "L'emplacement était-il dégagé et propre ?", False, "", ""),
    ("4.1b", "4 — Le milieu", "Si non, cela a-t-il contribué à l'accident ?", True, "4.1", "N"),
    ("4.2",  "4 — Le milieu", "L'éclairage était-il suffisant ?", False, "", ""),
    ("4.3",  "4 — Le milieu", "Les conditions météorologiques ont-elles joué un rôle ?", False, "", ""),
    ("4.4",  "4 — Le milieu", "Le bruit ambiant pouvait-il gêner la communication ?", False, "", ""),
    ("4.5",  "4 — Le milieu", "Les voies de circulation étaient-elles adaptées et balisées ?", False, "", ""),
    ("4.6",  "4 — Le milieu", "Le sol était-il en bon état (pas glissant, pas dégradé) ?", False, "", ""),
    ("4.7",  "4 — Le milieu", "L'espace de travail était-il suffisant pour réaliser l'activité en sécurité ?", False, "", ""),
    ("4.8",  "4 — Le milieu", "La signalisation de sécurité était-elle présente et visible ?", False, "", ""),
    ("4.9",  "4 — Le milieu", "L'environnement thermique était-il adapté ?", False, "", ""),
    ("4.10", "4 — Le milieu", "Des nuisances chimiques, biologiques ou radiologiques étaient-elles présentes ?", False, "", ""),

    # ─── Section 5 : Les produits, équipements utilisés ───────────────────
    ("5.1",  "5 — Les produits, équipements utilisés", "L'équipement utilisé était-il adapté à la tâche ?", False, "", ""),
    ("5.2",  "5 — Les produits, équipements utilisés", "L'équipement était-il en bon état de fonctionnement ?", False, "", ""),
    ("5.3",  "5 — Les produits, équipements utilisés", "L'équipement faisait-il l'objet d'une vérification périodique ?", False, "", ""),
    ("5.3b", "5 — Les produits, équipements utilisés", "Si oui, la dernière vérification était-elle à jour ?", True, "5.3", "O"),
    ("5.4",  "5 — Les produits, équipements utilisés", "L'équipement était-il conforme aux normes en vigueur ?", False, "", ""),
    ("5.5",  "5 — Les produits, équipements utilisés", "L'équipement disposait-il d'un marquage CE ?", False, "", ""),
    ("5.6",  "5 — Les produits, équipements utilisés", "Une notice d'utilisation était-elle disponible ?", False, "", ""),
    ("5.7",  "5 — Les produits, équipements utilisés", "La victime avait-elle reçu une formation à l'utilisation de cet équipement ?", False, "", ""),
    ("5.8",  "5 — Les produits, équipements utilisés", "Les dispositifs de protection de l'équipement étaient-ils en place ?", False, "", ""),
    ("5.8b", "5 — Les produits, équipements utilisés", "Si non, avaient-ils été délibérément retirés ?", True, "5.8", "N"),
    ("5.9",  "5 — Les produits, équipements utilisés", "L'équipement présentait-il un défaut connu avant l'accident ?", False, "", ""),
    ("5.10", "5 — Les produits, équipements utilisés", "Des EPI étaient-ils requis pour cette activité ?", False, "", ""),
    ("5.10b","5 — Les produits, équipements utilisés", "Si oui, étaient-ils disponibles ?", True, "5.10", "O"),
    ("5.10c","5 — Les produits, équipements utilisés", "Si disponibles, étaient-ils portés par la victime ?", True, "5.10b", "O"),
    ("5.11", "5 — Les produits, équipements utilisés", "Les EPI étaient-ils adaptés au risque ?", False, "", ""),
    ("5.12", "5 — Les produits, équipements utilisés", "Les EPI étaient-ils en bon état ?", False, "", ""),
    ("5.13", "5 — Les produits, équipements utilisés", "La victime avait-elle reçu une formation sur le port des EPI ?", False, "", ""),
    ("5.14", "5 — Les produits, équipements utilisés", "Un produit chimique était-il impliqué dans l'accident ?", False, "", ""),
    ("5.14b","5 — Les produits, équipements utilisés", "Si oui, une fiche de données de sécurité (FDS) était-elle disponible ?", True, "5.14", "O"),
    ("5.15", "5 — Les produits, équipements utilisés", "Le stockage des produits était-il conforme ?", False, "", ""),
    ("5.16", "5 — Les produits, équipements utilisés", "Un appareil de levage était-il impliqué ?", False, "", ""),
    ("5.16b","5 — Les produits, équipements utilisés", "Si oui, faisait-il l'objet d'un contrôle réglementaire à jour ?", True, "5.16", "O"),
    ("5.17", "5 — Les produits, équipements utilisés", "Les accessoires de levage (élingues, crochets…) étaient-ils vérifiés ?", False, "", ""),
    ("5.18", "5 — Les produits, équipements utilisés", "Un équipement de travail en hauteur était-il impliqué ?", False, "", ""),
    ("5.18b","5 — Les produits, équipements utilisés", "Si oui, était-il conforme et vérifié ?", True, "5.18", "O"),
    ("5.19", "5 — Les produits, équipements utilisés", "Une installation électrique était-elle en cause ?", False, "", ""),
    ("5.19b","5 — Les produits, équipements utilisés", "Si oui, était-elle conforme et vérifiée périodiquement ?", True, "5.19", "O"),
    ("5.20", "5 — Les produits, équipements utilisés", "Un véhicule ou engin de chantier était-il impliqué ?", False, "", ""),
    ("5.20b","5 — Les produits, équipements utilisés", "Si oui, le conducteur possédait-il les autorisations requises (permis, CACES…) ?", True, "5.20", "O"),
    ("5.21", "5 — Les produits, équipements utilisés", "La maintenance de l'équipement était-elle à jour ?", False, "", ""),
    ("5.22", "5 — Les produits, équipements utilisés", "Un dysfonctionnement de l'équipement avait-il été signalé avant l'accident ?", False, "", ""),
    ("5.23", "5 — Les produits, équipements utilisés", "L'outillage à main utilisé était-il adapté et en bon état ?", False, "", ""),
    ("5.24", "5 — Les produits, équipements utilisés", "Le matériel de premiers secours était-il accessible et opérationnel ?", False, "", ""),
    ("5.25", "5 — Les produits, équipements utilisés", "Les consignations / déconsignations nécessaires avaient-elles été effectuées ?", False, "", ""),
    ("5.26", "5 — Les produits, équipements utilisés", "Des dispositifs anti-erreur (poka-yoke) auraient-ils pu éviter l'accident ?", False, "", ""),
]


class Command(BaseCommand):
    help = "Peuple le référentiel des questions du questionnaire d'analyse 48h."

    def add_arguments(self, parser):
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Supprime toutes les questions existantes avant de recharger.",
        )

    def handle(self, *args, **options):
        if options["flush"]:
            deleted, _ = QuestionnaireTemplate.objects.all().delete()
            self.stdout.write(self.style.WARNING(f"{deleted} questions supprimées."))

        created_count = 0
        updated_count = 0

        for ordre, (code, section, question, est_sous_question, parent_code, condition) in enumerate(QUESTIONS, start=1):
            obj, created = QuestionnaireTemplate.objects.update_or_create(
                code=code,
                defaults={
                    "section": section,
                    "question": question,
                    "est_sous_question": est_sous_question,
                    "parent_code": parent_code,
                    "condition_affichage": condition,
                    "ordre": ordre,
                },
            )
            if created:
                created_count += 1
            else:
                updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Questionnaire 48h : {created_count} questions créées, {updated_count} mises à jour."
            )
        )
