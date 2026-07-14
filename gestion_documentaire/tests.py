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
