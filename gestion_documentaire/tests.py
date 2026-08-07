from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.db import transaction
from django.test import TestCase
from django.urls import reverse

from .forms import VersionDocumentForm
from .models import (
    Document,
    DossierDocumentaire,
    FichierBibliotheque,
    Indicateur,
    MesureIndicateur,
    ObjectifIndicateur,
    Processus,
    ProcessusService,
    RegleAccesDossier,
)
from .permissions import ROLE_DIRECTION, ROLE_PILOTE_PROCESSUS, ROLE_QSE, ROLE_UTILISATEUR


User = get_user_model()


class DocumentTransitionTests(TestCase):
    def setUp(self):
        self.processus = ProcessusService.objects.create(code="PM02", libelle="Processus documentaire")
        self.user = User.objects.create_user(username="redacteur", password="testpass123")
        self.document = Document.objects.create(
            type_document=Document.TypeDocument.PROCEDURE,
            processus_service=self.processus,
            numero_ordre=1,
            titre="Gestion documentaire",
            statut=Document.Statut.BROUILLON,
            cree_par=self.user,
        )

    def test_transition_directe_brouillon_vers_applicable_interdite(self):
        with self.assertRaises(ValidationError):
            self.document.transitionner_statut(Document.Statut.APPLICABLE, utilisateur=self.user)

    def test_transition_sequence_complete_autorisee(self):
        self.document.transitionner_statut(Document.Statut.EN_VERIFICATION, utilisateur=self.user)
        self.document.refresh_from_db()
        self.assertEqual(self.document.statut, Document.Statut.EN_VERIFICATION)

        self.document.transitionner_statut(Document.Statut.EN_APPROBATION, utilisateur=self.user)
        self.document.refresh_from_db()
        self.assertEqual(self.document.statut, Document.Statut.EN_APPROBATION)

        self.document.transitionner_statut(Document.Statut.APPLICABLE, utilisateur=self.user)
        self.document.refresh_from_db()
        self.assertEqual(self.document.statut, Document.Statut.APPLICABLE)
        self.assertIsNotNone(self.document.date_application)


class UniqueApplicableConstraintTests(TestCase):
    def setUp(self):
        self.processus = ProcessusService.objects.create(code="PM02", libelle="Processus documentaire")
        self.user = User.objects.create_user(username="qse_user", password="testpass123")

    def test_un_seul_document_applicable_par_code_documentaire(self):
        doc1 = Document.objects.create(
            type_document=Document.TypeDocument.PROCEDURE,
            processus_service=self.processus,
            numero_ordre=1,
            titre="Doc v1",
            statut=Document.Statut.APPLICABLE,
            cree_par=self.user,
        )

        doc2 = Document.objects.create(
            type_document=Document.TypeDocument.PROCEDURE,
            processus_service=self.processus,
            numero_ordre=1,
            titre="Doc v2",
            statut=Document.Statut.BROUILLON,
            cree_par=self.user,
        )

        doc2.statut = Document.Statut.APPLICABLE
        with self.assertRaises(ValidationError):
            with transaction.atomic():
                doc2.save()

        doc1.refresh_from_db()
        doc2.refresh_from_db()
        self.assertEqual(doc1.statut, Document.Statut.APPLICABLE)
        self.assertEqual(doc2.statut, Document.Statut.BROUILLON)


class PermissionsByRoleTests(TestCase):
    def setUp(self):
        self.processus = ProcessusService.objects.create(code="PM02", libelle="Processus documentaire")

        for role in [ROLE_QSE, ROLE_PILOTE_PROCESSUS, ROLE_DIRECTION, ROLE_UTILISATEUR]:
            Group.objects.get_or_create(name=role)

        self.qse = User.objects.create_user(
            username="qse", password="testpass123", is_auditeur=True
        )
        self.pilote = User.objects.create_user(
            username="pilote", password="testpass123", is_RO=True, is_auditeur=True
        )
        self.direction = User.objects.create_user(username="direction", password="testpass123")
        self.standard = User.objects.create_user(username="standard", password="testpass123")

        self.qse.groups.add(Group.objects.get(name=ROLE_QSE))
        self.pilote.groups.add(Group.objects.get(name=ROLE_PILOTE_PROCESSUS))
        self.direction.groups.add(Group.objects.get(name=ROLE_DIRECTION))
        self.standard.groups.add(Group.objects.get(name=ROLE_UTILISATEUR))

        self.doc_applicable = Document.objects.create(
            type_document=Document.TypeDocument.PROCEDURE,
            processus_service=self.processus,
            numero_ordre=10,
            titre="Applicable",
            statut=Document.Statut.APPLICABLE,
            cree_par=self.qse,
        )
        self.doc_brouillon = Document.objects.create(
            type_document=Document.TypeDocument.MODE_OPERATOIRE,
            processus_service=self.processus,
            numero_ordre=11,
            titre="Brouillon",
            statut=Document.Statut.BROUILLON,
            cree_par=self.qse,
        )

    def test_utilisateur_sans_profil_autorise_est_refuse(self):
        self.client.force_login(self.standard)
        response = self.client.get(reverse("gestion_documentaire:document_list"))
        self.assertEqual(response.status_code, 403)

    def test_qse_peut_acceder_dashboard_qse(self):
        self.client.force_login(self.qse)
        response = self.client.get(reverse("gestion_documentaire:dashboard_qse"))
        self.assertEqual(response.status_code, 200)

    def test_utilisateur_standard_refuse_dashboard_qse(self):
        self.client.force_login(self.standard)
        response = self.client.get(reverse("gestion_documentaire:dashboard_qse"))
        self.assertEqual(response.status_code, 403)

    def test_pilote_peut_soumettre_en_verification(self):
        self.client.force_login(self.pilote)
        response = self.client.post(
            reverse("gestion_documentaire:soumettre_verification", kwargs={"pk": self.doc_brouillon.pk})
        )
        self.assertEqual(response.status_code, 302)
        self.doc_brouillon.refresh_from_db()
        self.assertEqual(self.doc_brouillon.statut, Document.Statut.EN_VERIFICATION)


class BibliothequeDocumentaireTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="bibliothecaire", password="testpass123", is_auditeur=True
        )
        self.user.groups.add(Group.objects.get_or_create(name=ROLE_QSE)[0])

    def test_navigation_dans_un_dossier(self):
        dossier = DossierDocumentaire.objects.create(nom="Procédures", cree_par=self.user)
        fichier = FichierBibliotheque.objects.create(
            dossier=dossier,
            fichier="gestion_documentaire/bibliotheque/Procedures/procedure.pdf",
            nom="procedure.pdf",
            taille=9,
            ajoute_par=self.user,
        )
        self.client.force_login(self.user)
        response = self.client.get(
            reverse("gestion_documentaire:dossier_detail", kwargs={"dossier_id": dossier.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, fichier.nom)

    def test_une_version_vide_est_refusee(self):
        form = VersionDocumentForm(data={"type_increment": "mineur", "resume_changements": ""})
        self.assertFalse(form.is_valid())
        self.assertIn("Ajoutez au moins un fichier", form.non_field_errors()[0])

    def test_les_acces_sont_distincts_pour_chaque_action(self):
        ajout_user = User.objects.create_user(
            username="ajout_seulement", password="testpass123",
            is_RO=True, is_auditeur=True,
        )
        modification_user = User.objects.create_user(
            username="modification_seulement", password="testpass123",
            is_RO=True, is_auditeur=True,
        )
        dossier = DossierDocumentaire.objects.create(
            nom="Dossier strict", acces_restreint=True
        )
        consultation = RegleAccesDossier.objects.create(
            dossier=dossier, actions_autorisees=["lire"]
        )
        consultation.utilisateurs_autorises.add(ajout_user, modification_user)
        ajout = RegleAccesDossier.objects.create(
            dossier=dossier, actions_autorisees=["modifier"]
        )
        ajout.utilisateurs_autorises.add(ajout_user)
        modification = RegleAccesDossier.objects.create(
            dossier=dossier, actions_autorisees=["telecharger"]
        )
        modification.utilisateurs_autorises.add(modification_user)

        self.assertTrue(dossier.utilisateur_autorise(ajout_user, "modifier"))
        self.assertFalse(dossier.utilisateur_autorise(ajout_user, "telecharger"))
        self.assertTrue(dossier.utilisateur_autorise(modification_user, "telecharger"))
        self.assertFalse(dossier.utilisateur_autorise(modification_user, "modifier"))


# ============================================================
# MODULE TABLEAU DE BORD SMQS
# Tests automatisés pour le Tableau de Bord des Indicateurs
# ============================================================

from decimal import Decimal
from accounts.models import Societe
from .models import Processus, Indicateur, ObjectifIndicateur, MesureIndicateur
from .views import (
    obtenir_mois_periode,
    calculer_agregation_indicateur,
    evaluer_statut_indicateur,
)


class TdbModuleTests(TestCase):
    def setUp(self):
        self.societe = Societe.objects.create(nom="Société Test TdB")
        self.superuser = User.objects.create_superuser(
            username="admin_tdb", email="admin@test.com", password="password123"
        )
        self.ro_user = User.objects.create_user(
            username="ro_user", password="password123", is_RO=True, societe=self.societe
        )
        self.rs_user = User.objects.create_user(
            username="rs_user", password="password123", is_RS=True, societe=self.societe
        )
        self.ce_user = User.objects.create_user(
            username="ce_user", password="password123", is_CE=True, societe=self.societe
        )
        self.autre_user = User.objects.create_user(
            username="autre_user", password="password123"
        )

        self.processus = Processus.objects.create(
            societe=self.societe,
            code="PM02",
            nom="Management SMQS",
            is_active=True,
        )
        self.processus.RO.add(self.ro_user)
        self.processus.RS.add(self.rs_user)
        self.processus.CE.add(self.ce_user)

        self.ind_somme = Indicateur.objects.create(
            processus=self.processus,
            code="IND01",
            nom="Nombre d'audits",
            periodicite=Indicateur.Periodicite.MENSUEL,
            mode_agregation=Indicateur.ModeAgregation.SOMME,
            formats_chart_disponibles=["bar", "line"],
            is_active=True,
        )
        self.ind_moyenne = Indicateur.objects.create(
            processus=self.processus,
            code="IND02",
            nom="Taux de conformité",
            periodicite=Indicateur.Periodicite.MENSUEL,
            mode_agregation=Indicateur.ModeAgregation.MOYENNE,
            formats_chart_disponibles=["line"],
            is_active=True,
        )

        ObjectifIndicateur.objects.create(
            indicateur=self.ind_somme,
            annee=2026,
            valeur_objectif=Decimal("10.0000"),
        )

    def test_permissions_access_control(self):
        url_direct = reverse("gestion_documentaire:tdb_dashboard")
        url_proc = reverse("gestion_documentaire:tdb_dashboard_processus", kwargs={"processus_id": self.processus.pk})

        # Superuser autorisé sur l'accès direct
        self.client.force_login(self.superuser)
        res = self.client.get(url_direct)
        self.assertEqual(res.status_code, 200)

        # RO affecté autorisé sur l'accès direct
        self.client.force_login(self.ro_user)
        res = self.client.get(url_direct)
        self.assertEqual(res.status_code, 200)

        # RS affecté autorisé sur l'accès direct et sur le processus
        self.client.force_login(self.rs_user)
        res = self.client.get(url_direct)
        self.assertEqual(res.status_code, 200)
        res = self.client.get(url_proc)
        self.assertEqual(res.status_code, 200)

        # CE affecté autorisé sur l'accès direct et sur le processus
        self.client.force_login(self.ce_user)
        res = self.client.get(url_direct)
        self.assertEqual(res.status_code, 200)
        res = self.client.get(url_proc)
        self.assertEqual(res.status_code, 200)

        # Utilisateur non affecté et sans rôle REFUSÉ (403)
        self.client.force_login(self.autre_user)
        res = self.client.get(url_direct)
        self.assertEqual(res.status_code, 403)

    def test_permissions_role_flag_sans_affectation(self):
        # Un utilisateur portant le rôle RS/RO/CE doit pouvoir ouvrir l'accès direct
        # même s'il n'est pas affecté à un processus (le périmètre visible restera vide).
        url_direct = reverse("gestion_documentaire:tdb_dashboard")

        for user in (self.ro_user, self.rs_user, self.ce_user):
            self.processus.RO.remove(user)
            self.processus.RS.remove(user)
            self.processus.CE.remove(user)
            self.client.force_login(user)
            res = self.client.get(url_direct)
            self.assertEqual(res.status_code, 200)

        # Sans rôle ni affectation, accès direct toujours refusé
        self.client.force_login(self.autre_user)
        res = self.client.get(url_direct)
        self.assertEqual(res.status_code, 403)

    def test_perimetre_processus_par_societe(self):
        from gestion_documentaire.views import obtenir_donnees_tableau_de_bord

        societe_b = Societe.objects.create(nom="Société B TdB")

        proc_a2 = Processus.objects.create(
            societe=self.societe, code="PA01", nom="Processus A2", is_active=True
        )
        proc_a_inactif = Processus.objects.create(
            societe=self.societe, code="PAIN", nom="Processus A inactif", is_active=False
        )
        proc_b = Processus.objects.create(
            societe=societe_b, code="PB01", nom="Processus B", is_active=True
        )

        # RS/RO/CE de la société A : voient uniquement les processus actifs de A,
        # indépendamment de toute affectation nominative M2M.
        for user in (self.ro_user, self.rs_user, self.ce_user):
            user.societe = self.societe
            user.save()
            user.processus_RO.clear()
            user.processus_RS.clear()
            user.processus_CE.clear()
            data = obtenir_donnees_tableau_de_bord(user, {})
            codes = {p.code for p in data["tous_processus"]}
            self.assertEqual(codes, {"PM02", "PA01"})

        # RS/RO/CE sans société principale : zéro processus
        user_sans_societe = User.objects.create_user(
            username="ro_sans_societe", password="password123", is_RO=True
        )
        data = obtenir_donnees_tableau_de_bord(user_sans_societe, {})
        self.assertEqual(data["tous_processus"], [])

        # Superuser : voit tous les processus actifs, inactifs exclus
        data = obtenir_donnees_tableau_de_bord(self.superuser, {})
        codes = {p.code for p in data["tous_processus"]}
        self.assertIn("PM02", codes)
        self.assertIn("PA01", codes)
        self.assertIn("PB01", codes)
        self.assertNotIn("PAIN", codes)

        # Utilisateur non RS/RO/CE : périmètre M2M inchangé
        self.autre_user.societe = self.societe
        self.autre_user.save()
        proc_b.RO.add(self.autre_user)
        data = obtenir_donnees_tableau_de_bord(self.autre_user, {})
        codes = {p.code for p in data["tous_processus"]}
        self.assertEqual(codes, {"PB01"})

    def test_perimetre_societe_via_vue_http(self):
        self.ro_user.societe = self.societe
        self.ro_user.save()
        self.ro_user.processus_RO.clear()
        self.ro_user.processus_RS.clear()
        self.ro_user.processus_CE.clear()

        Processus.objects.create(societe=self.societe, code="PA01", nom="Processus A2", is_active=True)
        societe_b = Societe.objects.create(nom="Société B TdB")
        Processus.objects.create(societe=societe_b, code="PB01", nom="Processus B", is_active=True)

        url = reverse("gestion_documentaire:tdb_dashboard")
        self.client.force_login(self.ro_user)
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        codes = {p.code for p in res.context["tous_processus"]}
        self.assertEqual(codes, {"PM02", "PA01"})

    def test_actions_completes_rs_ro_ce(self):
        societe_b = Societe.objects.create(nom="Société B TdB")
        proc_b = Processus.objects.create(
            societe=societe_b, code="PB01", nom="Processus B", is_active=True
        )

        url_dashboard = reverse("gestion_documentaire:tdb_dashboard")
        url_dashboard_proc = reverse(
            "gestion_documentaire:tdb_dashboard_processus",
            kwargs={"processus_id": self.processus.pk},
        )
        url_dashboard_proc_b = reverse(
            "gestion_documentaire:tdb_dashboard_processus",
            kwargs={"processus_id": proc_b.pk},
        )
        url_export = reverse("gestion_documentaire:tdb_export_excel")
        url_json_proc = reverse(
            "gestion_documentaire:tdb_processus_detail_json",
            kwargs={"processus_id": self.processus.pk},
        )
        url_saisie_ind = reverse(
            "gestion_documentaire:tdb_saisie_mesures_indicateur",
            kwargs={"indicateur_id": self.ind_somme.pk, "annee": 2026},
        )
        url_saisie_mois = reverse(
            "gestion_documentaire:tdb_saisie_mesures",
            kwargs={"processus_id": self.processus.pk, "annee": 2026, "mois": 1},
        )
        url_update_proc_b = reverse(
            "gestion_documentaire:tdb_processus_update",
            kwargs={"processus_id": proc_b.pk},
        )

        for user in (self.ro_user, self.rs_user, self.ce_user):
            user.societe = self.societe
            user.save()
            user.processus_RO.clear()
            user.processus_RS.clear()
            user.processus_CE.clear()

            self.client.force_login(user)

            # Accès direct au module
            self.assertEqual(self.client.get(url_dashboard).status_code, 200)
            # Processus de sa société (même sans affectation M2M)
            self.assertEqual(self.client.get(url_dashboard_proc).status_code, 200)
            # Processus d'une autre société -> 403 (périmètre)
            self.assertEqual(self.client.get(url_dashboard_proc_b).status_code, 403)

            # Export Excel (POST) -> 200, pas de 403
            self.assertEqual(self.client.post(url_export).status_code, 200)

            # Endpoints AJAX / JSON
            self.assertEqual(self.client.get(url_json_proc).status_code, 200)
            self.assertEqual(self.client.get(url_saisie_ind).status_code, 200)
            self.assertEqual(self.client.get(url_saisie_mois).status_code, 200)

            # Action d'écriture sur un processus hors périmètre -> 403
            self.assertEqual(self.client.post(url_update_proc_b, {"nom": "X"}).status_code, 403)

    def test_export_excel_sans_societe(self):
        url_export = reverse("gestion_documentaire:tdb_export_excel")
        user_sans_societe = User.objects.create_user(
            username="ro_sans_societe", password="password123", is_RO=True
        )
        self.client.force_login(user_sans_societe)
        res = self.client.post(url_export)
        self.assertEqual(res.status_code, 200)

        import io
        from openpyxl import load_workbook
        wb = load_workbook(io.BytesIO(res.content))
        self.assertEqual(len(wb.sheetnames), 4)

    def test_export_excel_non_autorise(self):
        url_export = reverse("gestion_documentaire:tdb_export_excel")
        self.client.force_login(self.autre_user)
        res = self.client.post(url_export)
        self.assertEqual(res.status_code, 403)

    def test_calcul_agregation_avec_mesure_annuelle_mois_none(self):
        # M1=2.0, M2=0.0 (vraie mesure zero!), et mesure annuelle mois=None=5.0
        m1 = MesureIndicateur.objects.create(
            indicateur=self.ind_somme, annee=2026, mois=1, valeur=Decimal("2.0000"), saisie_par=self.ro_user
        )
        m2 = MesureIndicateur.objects.create(
            indicateur=self.ind_somme, annee=2026, mois=2, valeur=Decimal("0.0000"), saisie_par=self.ro_user
        )
        m_annuelle = MesureIndicateur.objects.create(
            indicateur=self.ind_somme, annee=2026, mois=None, valeur=Decimal("5.0000"), saisie_par=self.ro_user
        )

        mesures = [m1, m2, m_annuelle]

        # En Année complète : les 3 sont sommées (2 + 0 + 5 = 7)
        somme_annee = calculer_agregation_indicateur(self.ind_somme, mesures, type_periode="annee_complete")
        self.assertEqual(somme_annee, Decimal("7.0000"))

        # En Trimestre T1 : la mesure annuelle mois=None est EXCLUE (2 + 0 = 2)
        somme_t1 = calculer_agregation_indicateur(self.ind_somme, mesures, type_periode="trimestre")
        self.assertEqual(somme_t1, Decimal("2.0000"))

    def test_saisie_mesures_conservation_champ_vide(self):
        url_saisie = reverse(
            "gestion_documentaire:tdb_saisie_mesures",
            kwargs={"processus_id": self.processus.pk, "annee": 2026, "mois": 1},
        )
        self.client.force_login(self.ro_user)

        # 1. Création initiale d'une mesure M1 = 15.5 pour IND01
        MesureIndicateur.objects.create(
            indicateur=self.ind_somme, annee=2026, mois=1, valeur=Decimal("15.5000"), saisie_par=self.ro_user
        )

        # 2. Soumission d'une chaîne vide sur IND01 => RÈGLE : CONSERVER la mesure existante (pas de delete)
        res = self.client.post(url_saisie, {
            f"valeur_{self.ind_somme.id}": "",
            f"valeur_{self.ind_moyenne.id}": "8",
        })
        self.assertEqual(res.status_code, 302)

        # Vérification que la mesure IND01 existe TOUJOURS
        m_somme = MesureIndicateur.objects.get(indicateur=self.ind_somme, annee=2026, mois=1)
        self.assertEqual(m_somme.valeur, Decimal("15.5000"))

    def test_suppression_explicite_mesure(self):
        m = MesureIndicateur.objects.create(
            indicateur=self.ind_somme, annee=2026, mois=1, valeur=Decimal("10.0000"), saisie_par=self.ro_user
        )
        url_supprimer = reverse(
            "gestion_documentaire:tdb_supprimer_mesure",
            kwargs={"processus_id": self.processus.pk, "mesure_id": m.pk},
        )
        self.client.force_login(self.ro_user)
        res = self.client.post(url_supprimer)
        self.assertEqual(res.status_code, 302)
        self.assertFalse(MesureIndicateur.objects.filter(pk=m.pk).exists())

    def test_onglet_audits_etat_vide_sans_mapping(self):
        url = reverse("gestion_documentaire:tdb_dashboard") + "?tab=audits"
        self.client.force_login(self.ro_user)
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Répartition Globale des Audits")


class TdbCrudAndCodeGenerationTests(TestCase):
    def setUp(self):
        from accounts.models import Societe
        self.admin_user = User.objects.create_superuser(
            username="admin_test", email="admin@test.com", password="adminpassword123"
        )
        self.societe = Societe.objects.create(nom="Société AB Serve")
        self.processus = Processus.objects.create(
            code="CE", nom="Contrôle outil", description="Processus de test", societe=self.societe
        )
        self.indicateur = Indicateur.objects.create(
            processus=self.processus,
            code="CE01",
            nom="Contrôle outil ind",
            periodicite="mensuel",
            mode_agregation="somme",
        )

    def test_generer_code_processus_depuis_nom(self):
        from .views import generer_code_processus_depuis_nom
        code_ce = generer_code_processus_depuis_nom("Contrôle outil")
        self.assertTrue(code_ce.startswith("CE"))

        code_pa = generer_code_processus_depuis_nom("Pilotage et amélioration")
        self.assertEqual(code_pa, "PA")

        code_mq = generer_code_processus_depuis_nom("Management de la qualité")
        self.assertEqual(code_mq, "MQ")

    def test_generer_code_indicateur_format(self):
        from .views import generer_code_indicateur
        proc = Processus.objects.create(code="TEST", nom="Processus test code", societe=self.societe)
        code1 = generer_code_indicateur(proc)
        self.assertEqual(code1, "TEST01")

        Indicateur.objects.create(processus=proc, code=code1, nom="Ind 1")
        code2 = generer_code_indicateur(proc)
        self.assertEqual(code2, "TEST02")

        code3 = generer_code_indicateur(proc, extra_offset=1)
        self.assertEqual(code3, "TEST03")

    def test_saisie_mesures_indicateur_get_json_strict(self):
        # Mois 1 = 1, Mois 2 = 0, Mois 3..12 non mesurés
        MesureIndicateur.objects.create(
            indicateur=self.indicateur, annee=2026, mois=1, valeur=Decimal("1.0000"), saisie_par=self.admin_user
        )
        MesureIndicateur.objects.create(
            indicateur=self.indicateur, annee=2026, mois=2, valeur=Decimal("0.0000"), saisie_par=self.admin_user
        )

        url = reverse(
            "gestion_documentaire:tdb_saisie_mesures_indicateur",
            kwargs={"indicateur_id": self.indicateur.pk, "annee": 2026},
        )
        self.client.force_login(self.admin_user)
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        data = res.json()

        # Seuls les mois 1 et 2 doivent figurer
        self.assertIn("mesures", data)
        self.assertEqual(data["mesures"], {"1": "1", "2": "0"})
        self.assertNotIn("3", data["mesures"])

    def test_processus_update_view(self):
        url = reverse(
            "gestion_documentaire:tdb_processus_update",
            kwargs={"processus_id": self.processus.pk},
        )
        self.client.force_login(self.admin_user)
        res = self.client.post(url, {
            "code": "CE",
            "nom": "Contrôle outil modifié",
            "description": "Nouvelle description",
            "societe": str(self.societe.pk),
            "is_active": "true",
        })
        self.assertEqual(res.status_code, 302)
        self.processus.refresh_from_db()
        self.assertEqual(self.processus.nom, "Contrôle outil modifié")
        self.assertEqual(self.processus.description, "Nouvelle description")

    def test_processus_delete_view(self):
        url = reverse(
            "gestion_documentaire:tdb_processus_delete",
            kwargs={"processus_id": self.processus.pk},
        )
        self.client.force_login(self.admin_user)
        res = self.client.post(url)
        self.assertEqual(res.status_code, 302)
        self.assertFalse(Processus.objects.filter(pk=self.processus.pk).exists())

    def test_indicateur_update_view(self):
        url = reverse(
            "gestion_documentaire:tdb_indicateur_update",
            kwargs={"indicateur_id": self.indicateur.pk},
        )
        self.client.force_login(self.admin_user)
        res = self.client.post(url, {
            "nom": "Contrôle outil ind maj",
            "periodicite": "trimestriel",
            "mode_agregation": "moyenne",
            "is_active": "true",
            "valeur_objectif": "95.5",
            "objectif_annee": "2026",
        })
        self.assertEqual(res.status_code, 302)
        self.indicateur.refresh_from_db()
        self.assertEqual(self.indicateur.nom, "Contrôle outil ind maj")
        self.assertEqual(self.indicateur.periodicite, "trimestriel")
        self.assertEqual(self.indicateur.mode_agregation, "moyenne")
        obj = ObjectifIndicateur.objects.get(indicateur=self.indicateur, annee=2026)
        self.assertEqual(obj.valeur_objectif, Decimal("95.5000"))

    def test_indicateur_agregation_modes(self):
        ind_min = Indicateur.objects.create(
            processus=self.processus,
            code="IND_MIN",
            nom="Min test",
            periodicite=Indicateur.Periodicite.MENSUEL,
            mode_agregation=Indicateur.ModeAgregation.MINIMUM,
        )
        ind_max = Indicateur.objects.create(
            processus=self.processus,
            code="IND_MAX",
            nom="Max test",
            periodicite=Indicateur.Periodicite.MENSUEL,
            mode_agregation=Indicateur.ModeAgregation.MAXIMUM,
        )
        ind_num = Indicateur.objects.create(
            processus=self.processus,
            code="IND_NUM",
            nom="Nombre test",
            periodicite=Indicateur.Periodicite.MENSUEL,
            mode_agregation=Indicateur.ModeAgregation.NOMBRE,
        )

        MesureIndicateur.objects.create(indicateur=ind_min, annee=2026, mois=1, valeur=Decimal("15.5"))
        MesureIndicateur.objects.create(indicateur=ind_min, annee=2026, mois=2, valeur=Decimal("5.0"))
        MesureIndicateur.objects.create(indicateur=ind_min, annee=2026, mois=3, valeur=Decimal("20.0"))

        MesureIndicateur.objects.create(indicateur=ind_max, annee=2026, mois=1, valeur=Decimal("15.5"))
        MesureIndicateur.objects.create(indicateur=ind_max, annee=2026, mois=2, valeur=Decimal("5.0"))
        MesureIndicateur.objects.create(indicateur=ind_max, annee=2026, mois=3, valeur=Decimal("20.0"))

        MesureIndicateur.objects.create(indicateur=ind_num, annee=2026, mois=1, valeur=Decimal("15.5"))
        MesureIndicateur.objects.create(indicateur=ind_num, annee=2026, mois=2, valeur=Decimal("5.0"))

        mesures_min = list(MesureIndicateur.objects.filter(indicateur=ind_min))
        mesures_max = list(MesureIndicateur.objects.filter(indicateur=ind_max))
        mesures_num = list(MesureIndicateur.objects.filter(indicateur=ind_num))

        self.assertEqual(calculer_agregation_indicateur(ind_min, mesures_min), Decimal("5.0000"))
        self.assertEqual(calculer_agregation_indicateur(ind_max, mesures_max), Decimal("20.0000"))
        self.assertEqual(calculer_agregation_indicateur(ind_num, mesures_num), Decimal("2.0000"))

    def test_processus_create_with_indicator_agregation(self):
        url = reverse("gestion_documentaire:tdb_processus_create")
        self.client.force_login(self.admin_user)
        res = self.client.post(url, {
            "code": "PR_TEST",
            "nom": "Processus avec Agrégation",
            "description": "Test agregation",
            "societe": self.processus.societe_id,
            "ind_nom_1": "Indicateur Minimum",
            "ind_periodicite_1": "mensuel",
            "ind_agregation_1": "minimum",
        })
        self.assertEqual(res.status_code, 302)
        proc = Processus.objects.get(code="PR_TEST")
        ind = proc.indicateurs.first()
        self.assertIsNotNone(ind)
    def test_indicateur_create_modal_without_code(self):
        url = reverse("gestion_documentaire:indicateur_create")
        self.client.force_login(self.admin_user)
        res = self.client.post(url, {
            "processus": self.processus.id,
            "nom": "Taux de satisfaction client",
            "periodicite": "mensuel",
            "mode_agregation": "somme",
            "is_active": "true",
            "next": "/gestion-documentaire/tableau-de-bord/",
        })
        self.assertEqual(res.status_code, 302)
        ind = Indicateur.objects.get(nom="Taux de satisfaction client")
        self.assertTrue(ind.code.startswith(self.processus.code))


class TdbExportExcelTest(TestCase):
    def setUp(self):
        from accounts.models import Societe
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.user = User.objects.create_superuser("excel_user", "excel@test.com", "pass123")
        self.societe = Societe.objects.create(nom="Société Test Excel")
        self.processus = Processus.objects.create(code="PM01", nom="Pilotage", societe=self.societe)
        self.processus.RO.add(self.user)

    def test_export_excel_endpoint(self):
        import io
        from openpyxl import load_workbook
        url = reverse("gestion_documentaire:tdb_export_excel")
        self.client.force_login(self.user)
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response["Content-Type"],
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        self.assertIn("attachment; filename=", response["Content-Disposition"])

        wb = load_workbook(io.BytesIO(response.content))
        sheet_names = wb.sheetnames

        self.assertEqual(len(sheet_names), 4)
        self.assertIn("Synthèse des indicateurs", sheet_names)
        self.assertIn("Vue graphique", sheet_names)
        self.assertIn("Objectifs annuels", sheet_names)
        self.assertIn("Audits et conformité", sheet_names)

    def test_export_excel_post_chart_types(self):
        import io
        from openpyxl import load_workbook
        url = reverse("gestion_documentaire:tdb_export_excel")
        self.client.force_login(self.user)
        payload = {
            "chart_types": {"PM01-01": "bar", "PM01-02": "area"}
        }
        response = self.client.post(url, data=payload, content_type="application/json")
        self.assertEqual(response.status_code, 200)
        wb = load_workbook(io.BytesIO(response.content))
        self.assertIn("Vue graphique", wb.sheetnames)





