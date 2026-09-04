"""Suite de tests unitaires et d'intégration pour le module Plan de Prévention (PDP)."""

from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse

from accounts.models import Customer, Section, Site, Societe
from gestion_documentaire.models import Processus
from .models import PlanPrevention, PlanPreventionRisque, RisquePDP
from .constants import DEFAULT_PREDEFINED_RISKS

User = get_user_model()


class RisquePDPModelTestCase(TestCase):
    """Tests unitaires du nouveau modèle RisquePDP (catalogue dédié PDP)."""

    def test_risquepdp_creation_and_attributes(self):
        r = RisquePDP.objects.create(
            code="test_circulation",
            titre="Circulation piétonne dans l'atelier",
            description="Risque de heurt ou chute",
            categorie="Circulation",
            mesures_prevention_recommandees="Balisage et gilet haute visibilité",
            ordre=1,
            est_actif=True,
        )
        self.assertEqual(r.code, "test_circulation")
        self.assertEqual(r.titre, "Circulation piétonne dans l'atelier")
        self.assertEqual(str(r), "test_circulation - Circulation piétonne dans l'atelier")
        # Vérifier qu'il n'a aucun attribut processus
        self.assertFalse(hasattr(r, "processus_id"))
        self.assertFalse(hasattr(r, "probabilite"))
        self.assertFalse(hasattr(r, "gravite"))

    def test_risquepdp_ordering(self):
        r2 = RisquePDP.objects.create(code="code_b", titre="Risque B", ordre=2)
        r1 = RisquePDP.objects.create(code="code_a", titre="Risque A", ordre=1)
        qs = list(RisquePDP.objects.filter(code__in=["code_a", "code_b"]))
        self.assertEqual(qs[0], r1)
        self.assertEqual(qs[1], r2)


class PlanPreventionModelTestCase(TestCase):
    """Tests unitaires des modèles PlanPrevention et PlanPreventionRisque."""

    def setUp(self):
        self.societe1 = Societe.objects.create(nom="AB Serve France")
        self.societe2 = Societe.objects.create(nom="Societe Tierce")
        self.section = Section.objects.create(Nom="Section Nord", societe=self.societe1)
        self.site = Site.objects.create(nom="Site Renault Douai", section=self.section)
        self.customer = Customer.objects.create(
            intitule="Renault SAS",
            adresse="Usine de Douai",
            telephone="0327000000",
            societe=self.societe1,
        )
        self.user = User.objects.create_user(
            username="testuser_rs",
            password="Password123!",
            is_RS=True,
            societe=self.societe1,
            section=self.section,
        )

    def test_pdp_creation_and_reference_generation(self):
        pdp = PlanPrevention.objects.create(
            societe=self.societe1,
            section=self.section,
            site=self.site,
            customer=self.customer,
            eu_nom="Renault SAS",
            ee_nom="AB Serve France",
            nature_operation="Retouche techniques sur Longerons",
            created_by=self.user,
        )
        self.assertTrue(pdp.reference.startswith("PDP"))
        self.assertEqual(str(pdp), f"{pdp.reference} - Renault SAS / Retouche techniques sur Longerons")
        # Nouveau PDP débute avec 0 risque
        self.assertEqual(pdp.pdp_risques.count(), 0)

    def test_explicit_risk_association(self):
        pdp = PlanPrevention.objects.create(
            societe=self.societe1,
            eu_nom="Renault SAS",
            created_by=self.user,
        )
        r_pdp, _ = RisquePDP.objects.get_or_create(
            code="test_assoc_risk",
            defaults={"titre": "Risque test association", "ordre": 1}
        )
        assoc = PlanPreventionRisque.objects.create(
            pdp=pdp,
            risque=r_pdp,
            concerne_eu=True,
            concerne_ee=False,
            mesures_prevention="Port de chaussures de sécurité",
            mise_en_oeuvre_eu=True,
            ordre=1,
        )
        self.assertEqual(pdp.pdp_risques.count(), 1)
        self.assertEqual(pdp.risques.first().risque, r_pdp)
        self.assertEqual(assoc.mesures_prevention, "Port de chaussures de sécurité")


class PDPViewsAndPermissionsTestCase(TestCase):
    """Tests d'intégration des vues, autorisations et isolation multi-tenant."""

    def setUp(self):
        self.client = Client()

        # Société 1 & Utilisateurs (RO)
        self.soc1 = Societe.objects.create(nom="AB Serve Est")
        self.user_soc1 = User.objects.create_user(
            username="user_soc1",
            password="Password123!",
            is_RO=True,
            societe=self.soc1,
        )

        # Utilisateurs par profil pour tests des permissions
        self.user_ro = self.user_soc1  # is_RO=True

        self.user_auditeur = User.objects.create_user(
            username="user_auditeur",
            password="Password123!",
            is_auditeur=True,
            societe=self.soc1,
        )

        self.user_admin = User.objects.create_user(
            username="user_admin_staff",
            password="Password123!",
            is_staff=True,
            is_superuser=False,
            societe=self.soc1,
        )

        self.user_superuser = User.objects.create_user(
            username="user_superuser",
            password="Password123!",
            is_superuser=True,
            is_staff=True,
            societe=self.soc1,
        )

        # Normal User (Pas d'Admin, pas de RO, pas d'Auditeur, pas de superuser)
        self.user_normal = User.objects.create_user(
            username="user_normal",
            password="Password123!",
            is_OP=True,
            societe=self.soc1,
        )

        # Autres rôles non autorisés à ajouter un risque
        self.user_ce = User.objects.create_user(
            username="user_ce",
            password="Password123!",
            is_CE=True,
            societe=self.soc1,
        )

        self.user_rs = User.objects.create_user(
            username="user_rs",
            password="Password123!",
            is_RS=True,
            societe=self.soc1,
        )

        # Société 2 & Utilisateurs (Autre Tenant)
        self.soc2 = Societe.objects.create(nom="Concurrent S.A.")
        self.user_soc2 = User.objects.create_user(
            username="user_soc2",
            password="Password123!",
            is_RO=True,
            societe=self.soc2,
        )

        # PDP créé sous Société 1
        self.pdp_soc1 = PlanPrevention.objects.create(
            societe=self.soc1,
            eu_nom="Client Renault",
            ee_nom="AB Serve Est",
            nature_operation="Ponçage Longerons",
            created_by=self.user_soc1,
        )

    def test_list_view_authenticated(self):
        self.client.login(username="user_soc1", password="Password123!")
        response = self.client.get(reverse("plan_prevention:liste"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.pdp_soc1.reference)

    def test_tenant_isolation_list_view(self):
        """Un utilisateur de la Société 2 ne doit pas voir le PDP de la Société 1."""
        self.client.login(username="user_soc2", password="Password123!")
        response = self.client.get(reverse("plan_prevention:liste"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, self.pdp_soc1.reference)

    def test_tenant_isolation_detail_view_forbidden(self):
        """Un utilisateur de la Société 2 ne peut pas consulter le PDP de la Société 1 (404)."""
        self.client.login(username="user_soc2", password="Password123!")
        response = self.client.get(reverse("plan_prevention:detail", kwargs={"pk": self.pdp_soc1.pk}))
        self.assertEqual(response.status_code, 404)

    def test_dashboard_view_authenticated(self):
        """Test de l'accès au tableau de bord pour un utilisateur authentifié."""
        self.client.login(username="user_soc1", password="Password123!")
        response = self.client.get(reverse("plan_prevention:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Tableau de bord — Plans de Prévention")
        self.assertContains(response, self.pdp_soc1.reference)

    def test_risque_catalogue_visibility_and_button_permissions(self):
        """Les risques prédéfinis sont visibles par TOUS les utilisateurs.
        Le bouton 'Ajouter un risque' n'est visible que pour Superuser, Admin, RO, Auditeur.
        """
        # S'assurer qu'au moins un risque existe
        r_predef, _ = RisquePDP.objects.get_or_create(
            code="test_catalogue_risk",
            defaults={"titre": "Risque prédéfini catalogue", "ordre": 1, "est_actif": True}
        )

        authorized_users = [
            ("user_soc1", "RO"),
            ("user_auditeur", "Auditeur"),
            ("user_admin_staff", "Administrateur"),
            ("user_superuser", "Superuser"),
        ]
        for username, role_name in authorized_users:
            self.client.login(username=username, password="Password123!")
            res = self.client.get(reverse("plan_prevention:risque_list"))
            self.assertEqual(res.status_code, 200, f"Échec GET risque_list pour {role_name}")
            self.assertContains(res, "Risque prédéfini catalogue", msg_prefix=f"{role_name} doit voir les risques")
            self.assertTrue(res.context["can_add_risk"], f"can_add_risk doit être True pour {role_name}")
            self.assertContains(res, "Ajouter un risque", msg_prefix=f"Bouton visible pour {role_name}")

        unauthorized_users = [
            ("user_normal", "Utilisateur normal"),
            ("user_ce", "CE"),
            ("user_rs", "RS"),
        ]
        for username, role_name in unauthorized_users:
            self.client.login(username=username, password="Password123!")
            res = self.client.get(reverse("plan_prevention:risque_list"))
            self.assertEqual(res.status_code, 200, f"Échec GET risque_list pour {role_name}")
            self.assertContains(res, "Risque prédéfini catalogue", msg_prefix=f"{role_name} doit voir les risques")
            self.assertFalse(res.context["can_add_risk"], f"can_add_risk doit être False pour {role_name}")
            self.assertNotContains(res, "Ajouter un risque", msg_prefix=f"Bouton masqué pour {role_name}")

    def test_risk_creation_permissions(self):
        """API création de risque :
        - Superuser, Admin, RO, Auditeur -> 200
        - Utilisateur normal, CE, RS -> 403
        """
        # 1. RO -> Autorisé (200)
        self.client.login(username="user_soc1", password="Password123!")
        res = self.client.post(reverse("plan_prevention:api_create_risque"), {
            "code": "risk_ro_ok",
            "titre": "Risque créé par RO",
            "categorie": "Général",
            "ordre": 10,
        })
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json()["success"])

        # 2. Auditeur -> Autorisé (200)
        self.client.login(username="user_auditeur", password="Password123!")
        res = self.client.post(reverse("plan_prevention:api_create_risque"), {
            "code": "risk_auditeur_ok",
            "titre": "Risque créé par Auditeur",
            "categorie": "Audit",
            "ordre": 11,
        })
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json()["success"])

        # 3. Administrateur -> Autorisé (200)
        self.client.login(username="user_admin_staff", password="Password123!")
        res = self.client.post(reverse("plan_prevention:api_create_risque"), {
            "code": "risk_admin_ok",
            "titre": "Risque créé par Admin",
            "categorie": "Admin",
            "ordre": 12,
        })
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json()["success"])

        # 4. Superuser -> Autorisé (200)
        self.client.login(username="user_superuser", password="Password123!")
        res = self.client.post(reverse("plan_prevention:api_create_risque"), {
            "code": "risk_superuser_ok",
            "titre": "Risque créé par Superuser",
            "categorie": "Super",
            "ordre": 13,
        })
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json()["success"])

        # 5. Utilisateur normal -> Refusé (403)
        self.client.login(username="user_normal", password="Password123!")
        res = self.client.post(reverse("plan_prevention:api_create_risque"), {
            "code": "risk_normal_fail",
            "titre": "Risque utilisateur normal",
        })
        self.assertEqual(res.status_code, 403)

        # 6. CE -> Refusé (403)
        self.client.login(username="user_ce", password="Password123!")
        res = self.client.post(reverse("plan_prevention:api_create_risque"), {
            "code": "risk_ce_fail",
            "titre": "Risque créé par CE",
        })
        self.assertEqual(res.status_code, 403)

        # 7. RS -> Refusé (403)
        self.client.login(username="user_rs", password="Password123!")
        res = self.client.post(reverse("plan_prevention:api_create_risque"), {
            "code": "risk_rs_fail",
            "titre": "Risque créé par RS",
        })
        self.assertEqual(res.status_code, 403)

    def test_pdp_pdf_export(self):
        """Test de la génération du PDF pour un utilisateur autorisé."""
        self.client.login(username="user_soc1", password="Password123!")
        response = self.client.get(reverse("plan_prevention:export_pdf", kwargs={"pk": self.pdp_soc1.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertTrue(len(response.content) > 0)

    def test_new_pdp_creation_selective_risks(self):
        """Test que la création d'un PDP n'associe que les risques explicitement cochés par l'utilisateur."""
        self.client.login(username="user_soc1", password="Password123!")
        r_first = RisquePDP.objects.first()
        if not r_first:
            r_first = RisquePDP.objects.create(code="test_r1", titre="Risque test", ordre=1)

        post_data = {
            "societe": self.soc1.pk,
            "eu_nom": "Client Test Selected",
            "ee_nom": "AB Serve Test",
            "nature_operation": "Opération spécifique",
            "statut": "brouillon",
            "type_operation": "ponctuelle",
            f"risk_selected_{r_first.id}": str(r_first.id),
            f"risk_mesures_{r_first.id}": "Port de gilet obligatoire",
            f"risk_me_eu_{r_first.id}": "on",
        }
        response = self.client.post(reverse("plan_prevention:create"), post_data)
        self.assertEqual(response.status_code, 302)

        new_pdp = PlanPrevention.objects.filter(eu_nom="Client Test Selected").first()
        self.assertIsNotNone(new_pdp)
        # Seul le risque coché doit être associé (count = 1)
        self.assertEqual(new_pdp.pdp_risques.count(), 1)
        assoc = new_pdp.pdp_risques.first()
        self.assertEqual(assoc.risque_id, r_first.id)
        self.assertEqual(assoc.mesures_prevention, "Port de gilet obligatoire")
        self.assertTrue(assoc.mise_en_oeuvre_eu)

    def test_new_pdp_creation_zero_risks_default(self):
        """Un nouveau PDP créé sans cocher de risque commence avec 0 risque."""
        self.client.login(username="user_soc1", password="Password123!")
        post_data = {
            "societe": self.soc1.pk,
            "eu_nom": "Client Zero Risk",
            "ee_nom": "AB Serve Test",
            "nature_operation": "Opération sans risques cochés",
            "statut": "brouillon",
            "type_operation": "ponctuelle",
        }
        response = self.client.post(reverse("plan_prevention:create"), post_data)
        self.assertEqual(response.status_code, 302)

        pdp_zero = PlanPrevention.objects.filter(eu_nom="Client Zero Risk").first()
        self.assertIsNotNone(pdp_zero)
        self.assertEqual(pdp_zero.pdp_risques.count(), 0)



