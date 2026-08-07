"""Commande d'initialisation des données de démonstration SMQS pour le Tableau de Bord (idempotente)."""

from decimal import Decimal
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from accounts.models import Societe
from gestion_documentaire.models import (
    Processus,
    Indicateur,
    ObjectifIndicateur,
    MesureIndicateur,
)

User = get_user_model()


class Command(BaseCommand):
    help = "Alimente la base de données avec un jeu complet de données de démonstration SMQS pour le tableau de bord (idempotent)."

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("--- Début de l'alimentation des données SMQS ---"))

        # 1. Société Test1
        societe, created = Societe.objects.get_or_create(
            nom="Société Test1"
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"Société créée : {societe.nom}"))
        else:
            self.stdout.write(f"Société réutilisée : {societe.nom}")

        # Récupération de l'utilisateur admin pour les affectations RO/RS
        admin_user = User.objects.filter(username="admin").first()
        if not admin_user:
            admin_user = User.objects.filter(is_superuser=True).first()

        # 2. Processus
        processus_defs = [
            {
                "code": "PM01",
                "nom": "Pilotage et amélioration du SMQS",
                "description": "Pilotage global du système de management, suivi des objectifs et amélioration continue.",
                "role": "RO",
            },
            {
                "code": "PM02",
                "nom": "Gestion des ressources humaines",
                "description": "Gestion des compétences, formations, effectifs et conditions de travail.",
                "role": "RO",
            },
            {
                "code": "PR01",
                "nom": "Gestion commerciale et satisfaction client",
                "description": "Suivi des demandes clients, réclamations, satisfaction et performance commerciale.",
                "role": "RS",
            },
            {
                "code": "PR02",
                "nom": "Réalisation des prestations",
                "description": "Planification, exécution et suivi de la qualité des prestations réalisées.",
                "role": "RO",
            },
            {
                "code": "PS01",
                "nom": "Gestion des achats et fournisseurs",
                "description": "Sélection, suivi et évaluation des fournisseurs et des achats.",
                "role": "RS",
            },
            {
                "code": "PS02",
                "nom": "Maintenance des équipements",
                "description": "Maintenance préventive et corrective des équipements et suivi de leur disponibilité.",
                "role": "RO",
            },
            {
                "code": "PS03",
                "nom": "Gestion documentaire",
                "description": "Gestion et archivage documentaire.",
                "role": None,
            },
        ]

        processus_dict = {}
        for pdata in processus_defs:
            proc, _ = Processus.objects.update_or_create(
                code=pdata["code"],
                defaults={
                    "nom": pdata["nom"],
                    "description": pdata["description"],
                    "societe": societe,
                    "is_active": True,
                },
            )
            processus_dict[pdata["code"]] = proc
            self.stdout.write(f"Processus configuré : {proc.code} — {proc.nom}")

            # Affectations des utilisateurs si l'admin existe
            if admin_user:
                if pdata["role"] == "RO":
                    proc.RO.add(admin_user)
                elif pdata["role"] == "RS":
                    proc.RS.add(admin_user)

        # 3. Définition des indicateurs, objectifs 2026/2025 et mesures 2026
        # Sens de performance attendu (documenté en commentaires car non stocké dans le modèle) :
        # - Valeur élevée souhaitée : Taux de réalisation, Taux de clôture, Taux de couverture, Taux de satisfaction, Taux de conformité, Taux de disponibilité
        # - Valeur faible souhaitée : Taux d'absentéisme, Nombre d'accidents, Nombre de réclamations, Délai moyen, Nombre de non-conformités, Nombre de retards, Nombre de pannes

        indicateurs_defs = [
            # ── Processus PM01 ──
            {
                "processus_code": "PM01",
                "code": "PM01-01",
                "nom": "Taux de réalisation des objectifs SMQS",
                "periodicite": Indicateur.Periodicite.MENSUEL,
                "mode_agregation": Indicateur.ModeAgregation.MOYENNE,
                "objectif_2026": Decimal("90"),
                "objectif_2025": Decimal("85"),
                # Sens attendu : Valeur élevée souhaitée
                "mesures_2026": {1: 82, 2: 85, 3: 88, 4: 90, 5: 91, 6: 92, 7: 93, 8: 91, 9: 94, 10: 95, 11: 96, 12: 97},
            },
            {
                "processus_code": "PM01",
                "code": "PM01-02",
                "nom": "Taux de clôture des actions d’amélioration",
                "periodicite": Indicateur.Periodicite.MENSUEL,
                "mode_agregation": Indicateur.ModeAgregation.MOYENNE,
                "objectif_2026": Decimal("85"),
                "objectif_2025": Decimal("80"),
                # Sens attendu : Valeur élevée souhaitée
                "mesures_2026": {1: 70, 2: 74, 3: 78, 4: 80, 5: 82, 6: 84, 7: 86, 8: 88, 9: 90, 10: 91, 11: 92, 12: 93},
            },
            {
                "processus_code": "PM01",
                "code": "PM01-03",
                "nom": "Nombre de revues de direction réalisées",
                "periodicite": Indicateur.Periodicite.TRIMESTRIEL,
                "mode_agregation": Indicateur.ModeAgregation.SOMME,
                "objectif_2026": Decimal("4"),
                "objectif_2025": Decimal("4"),
                # Mesures trimestrielles : Mars, Juin, Septembre, Décembre
                "mesures_2026": {3: 1, 6: 1, 9: 1, 12: 1},
            },

            # ── Processus PM02 ──
            {
                "processus_code": "PM02",
                "code": "PM02-01",
                "nom": "Taux d’absentéisme",
                "periodicite": Indicateur.Periodicite.MENSUEL,
                "mode_agregation": Indicateur.ModeAgregation.MOYENNE,
                "objectif_2026": Decimal("5"),
                "objectif_2025": Decimal("6"),
                # Sens attendu : Valeur faible souhaitée
                "mesures_2026": {1: 4.1, 2: 4.5, 3: 4.0, 4: 3.8, 5: 4.2, 6: 4.4, 7: 4.8, 8: 5.1, 9: 4.2, 10: 4.0, 11: 3.9, 12: 3.7},
            },
            {
                "processus_code": "PM02",
                "code": "PM02-02",
                "nom": "Taux de réalisation du plan de formation",
                "periodicite": Indicateur.Periodicite.MENSUEL,
                "mode_agregation": Indicateur.ModeAgregation.MOYENNE,
                "objectif_2026": Decimal("90"),
                "objectif_2025": Decimal("85"),
                # Sens attendu : Valeur élevée souhaitée
                "mesures_2026": {1: 60, 2: 65, 3: 70, 4: 72, 5: 75, 6: 80, 7: 82, 8: 84, 9: 87, 10: 90, 11: 93, 12: 95},
            },
            {
                "processus_code": "PM02",
                "code": "PM02-03",
                "nom": "Taux de couverture des compétences",
                "periodicite": Indicateur.Periodicite.TRIMESTRIEL,
                "mode_agregation": Indicateur.ModeAgregation.MOYENNE,
                "objectif_2026": Decimal("85"),
                "objectif_2025": Decimal("80"),
                # Sens attendu : Valeur élevée souhaitée
                "mesures_2026": {3: 78, 6: 81, 9: 84, 12: 88},
            },
            {
                "processus_code": "PM02",
                "code": "PM02-04",
                "nom": "Nombre d’accidents avec arrêt",
                "periodicite": Indicateur.Periodicite.MENSUEL,
                "mode_agregation": Indicateur.ModeAgregation.SOMME,
                "objectif_2026": Decimal("0"),
                "objectif_2025": Decimal("0"),
                # Sens attendu : Valeur faible souhaitée (Objectif 0)
                "mesures_2026": {1: 0, 2: 0, 3: 1, 4: 0, 5: 0, 6: 0, 7: 0, 8: 0, 9: 1, 10: 0, 11: 0, 12: 0},
            },

            # ── Processus PR01 ──
            {
                "processus_code": "PR01",
                "code": "PR01-01",
                "nom": "Taux de satisfaction client",
                "periodicite": Indicateur.Periodicite.TRIMESTRIEL,
                "mode_agregation": Indicateur.ModeAgregation.MOYENNE,
                "objectif_2026": Decimal("90"),
                "objectif_2025": Decimal("88"),
                # Sens attendu : Valeur élevée souhaitée
                "mesures_2026": {3: 86, 6: 89, 9: 91, 12: 93},
            },
            {
                "processus_code": "PR01",
                "code": "PR01-02",
                "nom": "Nombre de réclamations clients",
                "periodicite": Indicateur.Periodicite.MENSUEL,
                "mode_agregation": Indicateur.ModeAgregation.SOMME,
                "objectif_2026": Decimal("12"),
                "objectif_2025": Decimal("15"),
                # Sens attendu : Valeur faible souhaitée
                "mesures_2026": {1: 2, 2: 1, 3: 1, 4: 0, 5: 2, 6: 1, 7: 0, 8: 1, 9: 1, 10: 0, 11: 1, 12: 0},
            },
            {
                "processus_code": "PR01",
                "code": "PR01-03",
                "nom": "Délai moyen de traitement des réclamations",
                "periodicite": Indicateur.Periodicite.MENSUEL,
                "mode_agregation": Indicateur.ModeAgregation.MOYENNE,
                "objectif_2026": Decimal("5"),
                "objectif_2025": Decimal("7"),
                # Sens attendu : Valeur faible souhaitée
                "mesures_2026": {1: 7, 2: 6, 3: 6, 4: 5, 5: 5, 6: 4, 7: 4, 8: 5, 9: 4, 10: 3, 11: 3, 12: 3},
            },

            # ── Processus PR02 ──
            {
                "processus_code": "PR02",
                "code": "PR02-01",
                "nom": "Taux de prestations réalisées dans les délais",
                "periodicite": Indicateur.Periodicite.MENSUEL,
                "mode_agregation": Indicateur.ModeAgregation.MOYENNE,
                "objectif_2026": Decimal("95"),
                "objectif_2025": Decimal("92"),
                # Sens attendu : Valeur élevée souhaitée
                "mesures_2026": {1: 88, 2: 90, 3: 92, 4: 93, 5: 95, 6: 94, 7: 96, 8: 97, 9: 95, 10: 96, 11: 97, 12: 98},
            },
            {
                "processus_code": "PR02",
                "code": "PR02-02",
                "nom": "Taux de conformité des prestations",
                "periodicite": Indicateur.Periodicite.MENSUEL,
                "mode_agregation": Indicateur.ModeAgregation.MOYENNE,
                "objectif_2026": Decimal("98"),
                "objectif_2025": Decimal("96"),
                # Sens attendu : Valeur élevée souhaitée
                "mesures_2026": {1: 96, 2: 97, 3: 98, 4: 97, 5: 98, 6: 99, 7: 98, 8: 99, 9: 99, 10: 98, 11: 99, 12: 99},
            },
            {
                "processus_code": "PR02",
                "code": "PR02-03",
                "nom": "Nombre de prestations non conformes",
                "periodicite": Indicateur.Periodicite.MENSUEL,
                "mode_agregation": Indicateur.ModeAgregation.SOMME,
                "objectif_2026": Decimal("5"),
                "objectif_2025": Decimal("8"),
                # Sens attendu : Valeur faible souhaitée
                "mesures_2026": {1: 1, 2: 0, 3: 1, 4: 0, 5: 1, 6: 0, 7: 0, 8: 1, 9: 0, 10: 0, 11: 0, 12: 0},
            },

            # ── Processus PS01 ──
            {
                "processus_code": "PS01",
                "code": "PS01-01",
                "nom": "Taux de fournisseurs évalués",
                "periodicite": Indicateur.Periodicite.TRIMESTRIEL,
                "mode_agregation": Indicateur.ModeAgregation.MOYENNE,
                "objectif_2026": Decimal("95"),
                "objectif_2025": Decimal("90"),
                # Sens attendu : Valeur élevée souhaitée
                "mesures_2026": {3: 80, 6: 88, 9: 93, 12: 97},
            },
            {
                "processus_code": "PS01",
                "code": "PS01-02",
                "nom": "Taux de fournisseurs conformes",
                "periodicite": Indicateur.Periodicite.TRIMESTRIEL,
                "mode_agregation": Indicateur.ModeAgregation.MOYENNE,
                "objectif_2026": Decimal("90"),
                "objectif_2025": Decimal("88"),
                # Sens attendu : Valeur élevée souhaitée
                "mesures_2026": {3: 84, 6: 87, 9: 89, 12: 92},
            },
            {
                "processus_code": "PS01",
                "code": "PS01-03",
                "nom": "Nombre de retards fournisseurs",
                "periodicite": Indicateur.Periodicite.MENSUEL,
                "mode_agregation": Indicateur.ModeAgregation.SOMME,
                "objectif_2026": Decimal("10"),
                "objectif_2025": Decimal("15"),
                # Sens attendu : Valeur faible souhaitée
                "mesures_2026": {1: 2, 2: 2, 3: 1, 4: 1, 5: 0, 6: 1, 7: 0, 8: 1, 9: 0, 10: 0, 11: 1, 12: 0},
            },

            # ── Processus PS02 ──
            {
                "processus_code": "PS02",
                "code": "PS02-01",
                "nom": "Taux de disponibilité des équipements",
                "periodicite": Indicateur.Periodicite.MENSUEL,
                "mode_agregation": Indicateur.ModeAgregation.MOYENNE,
                "objectif_2026": Decimal("95"),
                "objectif_2025": Decimal("92"),
                # Sens attendu : Valeur élevée souhaitée
                "mesures_2026": {1: 92, 2: 93, 3: 94, 4: 95, 5: 96, 6: 95, 7: 97, 8: 96, 9: 95, 10: 97, 11: 98, 12: 97},
            },
            {
                "processus_code": "PS02",
                "code": "PS02-02",
                "nom": "Taux de réalisation de la maintenance préventive",
                "periodicite": Indicateur.Periodicite.MENSUEL,
                "mode_agregation": Indicateur.ModeAgregation.MOYENNE,
                "objectif_2026": Decimal("90"),
                "objectif_2025": Decimal("85"),
                # Sens attendu : Valeur élevée souhaitée
                "mesures_2026": {1: 75, 2: 78, 3: 80, 4: 82, 5: 85, 6: 88, 7: 90, 8: 91, 9: 92, 10: 93, 11: 94, 12: 95},
            },
            {
                "processus_code": "PS02",
                "code": "PS02-03",
                "nom": "Nombre de pannes critiques",
                "periodicite": Indicateur.Periodicite.MENSUEL,
                "mode_agregation": Indicateur.ModeAgregation.SOMME,
                "objectif_2026": Decimal("3"),
                "objectif_2025": Decimal("5"),
                # Sens attendu : Valeur faible souhaitée
                "mesures_2026": {1: 1, 2: 0, 3: 1, 4: 0, 5: 0, 6: 1, 7: 0, 8: 0, 9: 0, 10: 0, 11: 0, 12: 0},
            },
        ]

        # Ingestion des indicateurs, objectifs et mesures
        count_ind = 0
        count_obj = 0
        count_mes = 0

        for idata in indicateurs_defs:
            proc = processus_dict[idata["processus_code"]]

            ind, _ = Indicateur.objects.update_or_create(
                processus=proc,
                code=idata["code"],
                defaults={
                    "nom": idata["nom"],
                    "periodicite": idata["periodicite"],
                    "mode_agregation": idata["mode_agregation"],
                    "formats_chart_disponibles": idata.get("formats_chart_disponibles", ["bar", "line", "pie", "doughnut", "radar"]),
                    "is_active": True,
                },
            )
            count_ind += 1

            # Objectif 2026
            if idata.get("objectif_2026") is not None:
                ObjectifIndicateur.objects.update_or_create(
                    indicateur=ind,
                    annee=2026,
                    defaults={"valeur_objectif": idata["objectif_2026"]},
                )
                count_obj += 1

            # Objectif 2025 (comparaison N-1)
            if idata.get("objectif_2025") is not None:
                ObjectifIndicateur.objects.update_or_create(
                    indicateur=ind,
                    annee=2025,
                    defaults={"valeur_objectif": idata["objectif_2025"]},
                )
                count_obj += 1

            # Mesures 2026
            for mois, val in idata.get("mesures_2026", {}).items():
                MesureIndicateur.objects.update_or_create(
                    indicateur=ind,
                    annee=2026,
                    mois=mois,
                    defaults={
                        "valeur": Decimal(str(val)),
                        "saisie_par": admin_user,
                    },
                )
                count_mes += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"--- Succès : {len(processus_defs)} processus, {count_ind} indicateurs, "
                f"{count_obj} objectifs et {count_mes} mesures configurés avec succès. ---"
            )
        )
