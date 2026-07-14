from decimal import Decimal
from datetime import time
from io import BytesIO

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from openpyxl import load_workbook

from accounts.models import Section, Societe

from .models import (
	ArticleCatalogue,
	Devis,
	DemandeAchat,
	Dysfonctionnement,
	EtapeValidation,
	EvaluationFournisseur,
	Fournisseur,
	LigneDemandeAchat,
	OffreFournisseur,
	ReceptionMarchandise,
)
from .forms import DevisForm, LigneDemandeAchatForm
from .services import calculer_evaluation_fournisseur


User = get_user_model()


class ReceptionMarchandiseModelTests(TestCase):
	def setUp(self):
		self.societe = Societe.objects.create(nom="AB Serve Quality")
		self.demandeur = User.objects.create_user(
			username="demandeur_achat",
			password="testpass123",
		)
		self.section = Section.objects.create(
			Nom="Section Achats",
			societe=self.societe,
		)
		self.demandeur.section = self.section
		self.demandeur.societe = self.societe
		self.demandeur.save(update_fields=["section", "societe"])
		self.demande = DemandeAchat.objects.create(
			demandeur=self.demandeur,
			adresse_livraison="Dépôt central",
			section_analytique=self.section,
			categorie="autre",
			statut=DemandeAchat.STATUT_COMMANDEE,
		)

	def _build_reception(self, **overrides):
		payload = {
			"demande": self.demande,
			"receptionne_par": self.demandeur,
			"conforme_quantite_etat": True,
			"c1_reponse_demande_prix": 1,
			"c2_livraisons": 1,
			"c3_disponibilite": 1,
			"c4_qualite_utilisation": 1,
			"c5_qualite_reception": 1,
			"c6_information_produit": 1,
			"c7_reglement_litiges": 1,
			"c8_couts": 1,
			"c9_communication": 1,
		}
		payload.update(overrides)
		return ReceptionMarchandise(**payload)

	def test_calculer_score_arrondit_a_deux_decimales_pour_notes_minimales(self):
		reception = self._build_reception()

		self.assertEqual(reception.calculer_score(), Decimal("32.14"))
		self.assertEqual(reception.calculer_note(), ReceptionMarchandise.NOTE_D)

	def test_calculer_score_retourne_note_c_sur_un_profil_uniforme_a_2(self):
		reception = self._build_reception(
			c1_reponse_demande_prix=2,
			c2_livraisons=2,
			c3_disponibilite=2,
			c4_qualite_utilisation=2,
			c5_qualite_reception=2,
			c6_information_produit=2,
			c7_reglement_litiges=2,
			c8_couts=2,
			c9_communication=2,
		)

		self.assertEqual(reception.calculer_score(), Decimal("64.29"))
		self.assertEqual(reception.calculer_note(), ReceptionMarchandise.NOTE_C)

	def test_save_persiste_score_note_et_propriete_conformite(self):
		reception = self._build_reception(
			c1_reponse_demande_prix=2,
			c2_livraisons=2,
			c3_disponibilite=2,
			c4_qualite_utilisation=2,
			c5_qualite_reception=2,
			c6_information_produit=2,
			c7_reglement_litiges=2,
			c8_couts=4,
			c9_communication=4,
			conforme_quantite_etat=False,
		)
		reception.save()

		self.demande.refresh_from_db()
		reception.refresh_from_db()

		self.assertEqual(reception.score_calcule, Decimal("85.71"))
		self.assertEqual(reception.note_calculee, ReceptionMarchandise.NOTE_B)
		self.assertIs(self.demande.is_conforme, False)


class EvaluationFournisseurServiceTests(TestCase):
	def setUp(self):
		self.societe = Societe.objects.create(nom="AB Serve Quality")
		self.section = Section.objects.create(Nom="Section Opérations", societe=self.societe)
		self.demandeur = User.objects.create_user(
			username="demandeur_eval",
			password="testpass123",
			section=self.section,
			societe=self.societe,
		)
		self.fournisseur = Fournisseur.objects.create(
			nom="Fournisseur Alpha",
			adresse="Zone industrielle",
			pris_en_compte=True,
		)

	def _creer_reception_avec_score(self, suffixe, score):
		demande = DemandeAchat.objects.create(
			demandeur=self.demandeur,
			adresse_livraison=f"Site {suffixe}",
			section_analytique=self.section,
			categorie="autre",
			statut=DemandeAchat.STATUT_RECEPTIONNEE,
		)
		LigneDemandeAchat.objects.create(
			demande=demande,
			hors_catalogue=True,
			nouvelle_designation=f"Besoin {suffixe}",
			quantite=1,
			fournisseur_retenu=self.fournisseur,
		)
		reception = ReceptionMarchandise.objects.create(
			demande=demande,
			receptionne_par=self.demandeur,
			conforme_quantite_etat=True,
			c1_reponse_demande_prix=4,
			c2_livraisons=4,
			c3_disponibilite=4,
			c4_qualite_utilisation=4,
			c5_qualite_reception=4,
			c6_information_produit=4,
			c7_reglement_litiges=4,
			c8_couts=4,
			c9_communication=4,
		)
		ReceptionMarchandise.objects.filter(pk=reception.pk).update(score_calcule=score)
		reception.refresh_from_db()
		return demande, reception

	def test_calculer_evaluation_fournisseur_agrege_moyenne_note_et_dysfonctionnements(self):
		annee = timezone.now().year
		demande_1, reception_1 = self._creer_reception_avec_score("A", Decimal("95.00"))
		demande_2, reception_2 = self._creer_reception_avec_score("B", Decimal("80.00"))
		demande_3, reception_3 = self._creer_reception_avec_score("C", Decimal("70.00"))

		Dysfonctionnement.objects.create(
			reception=reception_1,
			heure_signalement=time(9, 15),
			description="Colis abîmé",
			signale_par=self.demandeur,
		)
		Dysfonctionnement.objects.create(
			demande=demande_2,
			heure_signalement=time(11, 0),
			description="Erreur de préparation",
			signale_par=self.demandeur,
		)

		evaluation = calculer_evaluation_fournisseur(self.fournisseur, annee)

		self.fournisseur.refresh_from_db()
		self.assertIsNotNone(evaluation)
		self.assertEqual(evaluation.nb_receptions_evaluees, 3)
		self.assertEqual(evaluation.score_moyen, Decimal("81.67"))
		self.assertEqual(evaluation.note, ReceptionMarchandise.NOTE_B)
		self.assertEqual(evaluation.nb_dysfonctionnements, 2)
		self.assertEqual(evaluation.pris_en_compte, True)
		self.assertEqual(self.fournisseur.statut_evaluation, ReceptionMarchandise.NOTE_B)
		self.assertTrue(
			EvaluationFournisseur.objects.filter(
				fournisseur=self.fournisseur,
				annee=annee,
			).exists()
		)


class AchatsRequiredFieldsTests(TestCase):
	def setUp(self):
		self.societe = Societe.objects.create(nom="AB Serve Quality")
		self.section = Section.objects.create(Nom="Section Achat", societe=self.societe)
		self.user = User.objects.create_user(
			username="acheteur_ui",
			password="testpass123",
			section=self.section,
			societe=self.societe,
		)
		self.client.force_login(self.user)
		self.fournisseur = Fournisseur.objects.create(
			nom="Fournisseur Test",
			adresse="Zone 1",
			reference_fournisseur="FOUR-TEST-01",
		)

	def test_fournisseur_form_affiche_les_marqueurs_obligatoires(self):
		response = self.client.get(reverse("achats:fournisseur_create"))

		self.assertContains(response, 'class="form-label fw-semibold required-label"')
		self.assertContains(response, "Les champs marqués d'un astérisque sont obligatoires.")
		self.assertContains(response, "Réf. fournisseur")

	def test_creation_fournisseur_refusee_si_champs_requis_absents(self):
		response = self.client.post(
			reverse("achats:fournisseur_create"),
			{
				"nom": "",
				"adresse": "",
				"contact_nom": "",
				"contact_mail": "",
				"contact_tel": "",
			},
		)

		self.assertEqual(response.status_code, 200)
		self.assertEqual(Fournisseur.objects.filter(nom="").count(), 0)
		self.assertFormError(response.context["form"], "nom", "Ce champ est obligatoire.")
		self.assertFormError(response.context["form"], "adresse", "Ce champ est obligatoire.")

	def test_creation_article_refusee_si_offre_commencee_sans_tarif(self):
		response = self.client.post(
			reverse("achats:catalogue_create"),
			{
				"reference": "ART-001",
				"designation": "Article test",
				"description": "Description test",
				"type_article": "materiel",
				"categorie": "autre",
				"offres-TOTAL_FORMS": "1",
				"offres-INITIAL_FORMS": "0",
				"offres-MIN_NUM_FORMS": "0",
				"offres-MAX_NUM_FORMS": "1000",
				"offres-0-fournisseur": str(self.fournisseur.pk),
				"offres-0-tarif_propose": "",
				"offres-0-reference_chez_fournisseur": "REF-FOUR-1",
			},
		)

		self.assertEqual(response.status_code, 200)
		self.assertFalse(ArticleCatalogue.objects.filter(reference="ART-001").exists())
		self.assertEqual(OffreFournisseur.objects.count(), 0)
		self.assertContains(response, "Ce champ est obligatoire.")

	def test_creation_demande_refusee_si_champs_requis_absents(self):
		response = self.client.post(
			reverse("achats:demande_create"),
			{
				"delai_souhaite": "",
				"adresse_livraison": "",
				"section_analytique": "",
				"categorie": "",
				"action": "brouillon",
				"lignes-TOTAL_FORMS": "1",
				"lignes-INITIAL_FORMS": "0",
				"lignes-MIN_NUM_FORMS": "0",
				"lignes-MAX_NUM_FORMS": "1000",
				"lignes-0-hors_catalogue": "on",
				"lignes-0-nouvelle_designation": "",
				"lignes-0-quantite": "",
				"lignes-0-qte_stock": "",
			},
		)

		self.assertEqual(response.status_code, 200)
		self.assertEqual(DemandeAchat.objects.count(), 0)
		self.assertFormError(response.context["form"], "adresse_livraison", "Ce champ est obligatoire.")
		self.assertFormError(response.context["form"], "section_analytique", "Ce champ est obligatoire.")
		self.assertFormError(response.context["form"], "categorie", "Ce champ est obligatoire.")
		self.assertContains(response, "Vous devez choisir un article du catalogue ou renseigner une désignation hors catalogue.")


class AchatsWorkflowViewsTests(TestCase):
	def setUp(self):
		self.societe = Societe.objects.create(nom="AB Serve Quality")
		self.section = Section.objects.create(Nom="Section Workflow", societe=self.societe)
		self.demandeur = User.objects.create_user(
			username="demandeur_flow",
			password="testpass123",
			email="demandeur_flow@example.com",
			section=self.section,
			societe=self.societe,
		)
		self.ro_user = User.objects.create_user(
			username="ro_flow",
			password="testpass123",
			email="ro_flow@example.com",
			section=self.section,
			societe=self.societe,
			is_RO=True,
		)
		self.superadmin_user = User.objects.create_user(
			username="dg_flow",
			password="testpass123",
			email="dg_flow@example.com",
			section=self.section,
			societe=self.societe,
			is_superuser=True,
		)
		self.achat_user = User.objects.create_user(
			username="achat_flow",
			password="testpass123",
			section=self.section,
			societe=self.societe,
			is_staff=True,
		)
		self.fournisseur = Fournisseur.objects.create(nom="Fournisseur Flow", adresse="Zone 2")
		self.demande = DemandeAchat.objects.create(
			demandeur=self.demandeur,
			adresse_livraison="Dépôt 1",
			section_analytique=self.section,
			categorie="autre",
			statut=DemandeAchat.STATUT_SOUMISE,
		)
		self.ligne = LigneDemandeAchat.objects.create(
			demande=self.demande,
			hors_catalogue=True,
			nouvelle_designation="Article Flow",
			quantite=2,
			qte_stock=0,
		)

	def test_retenir_devis_met_a_jour_ligne_et_statut_demande(self):
		self.client.force_login(self.achat_user)
		devis = Devis.objects.create(
			ligne=self.ligne,
			fournisseur=self.fournisseur,
			prix_propose=Decimal("25.00"),
			reference_fournisseur="DEV-001",
			saisi_par=self.achat_user,
		)

		response = self.client.post(reverse("achats:devis_choose", args=[devis.pk]))

		self.assertEqual(response.status_code, 302)
		devis.refresh_from_db()
		self.ligne.refresh_from_db()
		self.demande.refresh_from_db()
		self.assertTrue(devis.est_choisi)
		self.assertEqual(self.ligne.fournisseur_retenu, self.fournisseur)
		self.assertEqual(self.ligne.prix_unitaire, Decimal("25.00"))
		self.assertEqual(self.ligne.prix_total, Decimal("50.00"))
		self.assertEqual(self.demande.statut, DemandeAchat.STATUT_EN_COURS_DEVIS)

	def test_lancer_validation_et_traiter_etapes_selon_roles_ro_et_superadmin(self):
		self.client.force_login(self.achat_user)
		self.demande.statut = DemandeAchat.STATUT_EN_COURS_DEVIS
		self.demande.save(update_fields=["statut"])
		self.ligne.fournisseur_retenu = self.fournisseur
		self.ligne.prix_unitaire = Decimal("25.00")
		self.ligne.save()

		response = self.client.post(reverse("achats:demande_launch_validation", args=[self.demande.pk]))

		self.assertEqual(response.status_code, 302)
		self.demande.refresh_from_db()
		etape_n1 = EtapeValidation.objects.get(demande=self.demande, niveau=EtapeValidation.NIVEAU_DIRECTEUR_POLE)
		self.assertEqual(self.demande.statut, DemandeAchat.STATUT_VALIDATION_N1)
		self.assertIsNone(etape_n1.validateur)
		self.assertEqual(len(mail.outbox), 1)
		self.assertIn(self.ro_user.email, mail.outbox[0].to)
		self.assertIn(self.demande.numero, mail.outbox[0].subject)

		self.client.force_login(self.ro_user)
		response = self.client.post(
			reverse("achats:demande_validation_action", args=[self.demande.pk, etape_n1.pk]),
			{"decision": EtapeValidation.STATUT_APPROUVE, "commentaire": "OK RO"},
		)

		self.assertEqual(response.status_code, 302)
		self.demande.refresh_from_db()
		etape_n1.refresh_from_db()
		self.assertEqual(etape_n1.validateur, self.ro_user)
		self.assertEqual(self.demande.statut, DemandeAchat.STATUT_VALIDATION_N2)
		etape_n2 = EtapeValidation.objects.get(demande=self.demande, niveau=EtapeValidation.NIVEAU_DIRECTEUR_GENERAL)
		self.assertEqual(len(mail.outbox), 2)
		self.assertIn(self.superadmin_user.email, mail.outbox[1].to)

		self.client.force_login(self.superadmin_user)
		response = self.client.post(
			reverse("achats:demande_validation_action", args=[self.demande.pk, etape_n2.pk]),
			{"decision": EtapeValidation.STATUT_APPROUVE, "commentaire": "OK DG"},
		)

		self.assertEqual(response.status_code, 302)
		self.demande.refresh_from_db()
		etape_n2.refresh_from_db()
		self.assertEqual(etape_n2.validateur, self.superadmin_user)
		self.assertEqual(self.demande.statut, DemandeAchat.STATUT_VALIDEE)
		self.assertEqual(len(mail.outbox), 3)
		self.assertIn(self.demandeur.email, mail.outbox[2].to)
		self.assertIn("Mise à jour", mail.outbox[2].subject)

	def test_enregistrer_reception_passe_la_demande_en_receptionnee(self):
		self.client.force_login(self.achat_user)
		self.demande.statut = DemandeAchat.STATUT_VALIDEE
		self.demande.save(update_fields=["statut"])

		response = self.client.post(
			reverse("achats:reception_edit", args=[self.demande.pk]),
			{
				"conforme_quantite_etat": "on",
				"c1_reponse_demande_prix": "4",
				"c2_livraisons": "4",
				"c3_disponibilite": "4",
				"c4_qualite_utilisation": "4",
				"c5_qualite_reception": "4",
				"c6_information_produit": "4",
				"c7_reglement_litiges": "4",
				"c8_couts": "4",
				"c9_communication": "4",
			},
		)

		self.assertEqual(response.status_code, 302)
		self.demande.refresh_from_db()
		reception = ReceptionMarchandise.objects.get(demande=self.demande)
		self.assertEqual(self.demande.statut, DemandeAchat.STATUT_RECEPTIONNEE)
		self.assertEqual(reception.note_calculee, ReceptionMarchandise.NOTE_A)

	def test_recalcul_evaluation_depuis_vue_cree_l_evaluation(self):
		self.client.force_login(self.achat_user)
		self.demande.statut = DemandeAchat.STATUT_RECEPTIONNEE
		self.demande.save(update_fields=["statut"])
		self.ligne.fournisseur_retenu = self.fournisseur
		self.ligne.prix_unitaire = Decimal("10.00")
		self.ligne.save()
		ReceptionMarchandise.objects.create(
			demande=self.demande,
			receptionne_par=self.achat_user,
			conforme_quantite_etat=True,
			c1_reponse_demande_prix=4,
			c2_livraisons=4,
			c3_disponibilite=4,
			c4_qualite_utilisation=4,
			c5_qualite_reception=4,
			c6_information_produit=4,
			c7_reglement_litiges=4,
			c8_couts=4,
			c9_communication=4,
		)

		response = self.client.post(
			reverse("achats:evaluation_list"),
			{
				"annee": timezone.now().year,
				"fournisseur": str(self.fournisseur.pk),
				"action": "calculer_fournisseur",
			},
		)

		self.assertEqual(response.status_code, 302)
		self.assertTrue(
			EvaluationFournisseur.objects.filter(
				fournisseur=self.fournisseur,
				annee=timezone.now().year,
			).exists()
		)


class CatalogueAutoFillTests(TestCase):
	def test_select_article_expose_stock_et_prix_pour_auto_remplissage(self):
		fournisseur = Fournisseur.objects.create(
			nom="Fournisseur Catalogue",
			adresse="Zone 9",
			reference_fournisseur="FOUR-CAT-01",
		)
		article = ArticleCatalogue.objects.create(
			reference="CAT-001",
			designation="Article catalogue",
			stock_disponible=14,
			prix_reference_ht=Decimal("18.50"),
			type_article="materiel",
			categorie="autre",
		)
		OffreFournisseur.objects.create(
			article=article,
			fournisseur=fournisseur,
			tarif_propose=Decimal("19.00"),
			reference_chez_fournisseur="REF-CAT-FOUR",
		)

		form = LigneDemandeAchatForm()
		html = str(form["article_catalogue"])
		supplier_html = str(form["fournisseur_retenu"])

		self.assertIn('data-stock="14"', html)
		self.assertIn('data-price="18.50"', html)
		self.assertIn(f'value="{article.pk}"', html)
		self.assertIn('name="reference_fournisseur"', str(form["reference_fournisseur"]))
		self.assertIn('disabled', str(form["reference_fournisseur"]))
		self.assertIn('data-reference-fournisseur="FOUR-CAT-01"', supplier_html)

	def test_formulaire_ligne_aligne_reference_fournisseur_sur_offre(self):
		societe = Societe.objects.create(nom="AB Serve Test")
		section = Section.objects.create(Nom="Section Achat", societe=societe)
		fournisseur = Fournisseur.objects.create(nom="Fournisseur Ligne", adresse="Zone 10")
		fournisseur.reference_fournisseur = "POMPE-FOUR-01"
		fournisseur.save(update_fields=["reference_fournisseur"])
		article = ArticleCatalogue.objects.create(
			reference="CAT-002",
			designation="Pompe",
			stock_disponible=3,
			prix_reference_ht=Decimal("120.00"),
			type_article="materiel",
			categorie="autre",
		)
		OffreFournisseur.objects.create(
			article=article,
			fournisseur=fournisseur,
			tarif_propose=Decimal("118.00"),
			reference_chez_fournisseur="ANCIENNE-REF-OFFRE",
		)
		demandeur = User.objects.create_user(
			username="ligne_auto",
			password="testpass123",
			section=section,
			societe=societe,
		)
		demande = DemandeAchat.objects.create(
			demandeur=demandeur,
			adresse_livraison="Atelier",
			section_analytique=section,
			categorie="autre",
		)

		form = LigneDemandeAchatForm(
			data={
				"article_catalogue": str(article.pk),
				"hors_catalogue": "",
				"nouvelle_designation": "",
				"nouvelle_description": "",
				"quantite": "2",
				"qte_stock": "3",
				"prix_unitaire": "120.00",
				"prix_total": "240.00",
				"reference_fournisseur": "",
				"fournisseur_retenu": str(fournisseur.pk),
				"commentaire": "",
				"engin_concerne": "",
			},
			instance=LigneDemandeAchat(demande=demande),
		)

		self.assertTrue(form.is_valid(), form.errors)
		ligne = form.save()

		self.assertEqual(ligne.reference_fournisseur, "POMPE-FOUR-01")

	def test_formulaire_devis_aligne_reference_fournisseur_sur_fournisseur(self):
		fournisseur = Fournisseur.objects.create(
			nom="Fournisseur Devis",
			adresse="Zone 11",
			reference_fournisseur="DEV-FOUR-01",
			pris_en_compte=True,
		)

		form = LigneDemandeAchatForm()
		devis_form = DevisForm(
			data={
				"fournisseur": str(fournisseur.pk),
				"prix_propose": "45.00",
				"reference_fournisseur": "",
				"delai_livraison_propose": "48h",
				"est_choisi": "",
			}
		)

		supplier_html = str(devis_form["fournisseur"])
		ref_html = str(devis_form["reference_fournisseur"])

		self.assertIn('data-reference-fournisseur="DEV-FOUR-01"', supplier_html)
		self.assertIn('disabled', ref_html)
		self.assertTrue(devis_form.is_valid(), devis_form.errors)
		devis = devis_form.save(commit=False)
		self.assertEqual(devis.reference_fournisseur, "DEV-FOUR-01")


class DemandeExcelExportTests(TestCase):
	def setUp(self):
		self.societe = Societe.objects.create(nom="AB Serve Tunisie")
		self.section = Section.objects.create(Nom="Section Excel", societe=self.societe)
		self.user = User.objects.create_user(
			username="demandeur_excel",
			password="testpass123",
			first_name="Ali",
			last_name="Ben Salah",
			email="ali@example.com",
			telephone="22110099",
			section=self.section,
			societe=self.societe,
		)
		self.client.force_login(self.user)
		self.fournisseur = Fournisseur.objects.create(nom="Fournisseur Excel", adresse="Zone Excel")
		self.demande = DemandeAchat.objects.create(
			demandeur=self.user,
			adresse_livraison="Magasin central",
			section_analytique=self.section,
			categorie="autre",
		)
		LigneDemandeAchat.objects.create(
			demande=self.demande,
			hors_catalogue=True,
			nouvelle_designation="Gants de protection",
			quantite=5,
			qte_stock=2,
			prix_unitaire=Decimal("12.50"),
			fournisseur_retenu=self.fournisseur,
			reference_fournisseur="GANT-FOUR-01",
			commentaire="Urgent",
			engin_concerne="Chariot",
		)

	def test_export_excel_retourne_un_classeur_doc07_renseigne(self):
		response = self.client.get(reverse("achats:demande_excel", args=[self.demande.pk]))

		self.assertEqual(response.status_code, 200)
		self.assertEqual(
			response["Content-Type"],
			"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
		)
		self.assertIn("attachment; filename=", response["Content-Disposition"])

		workbook = load_workbook(BytesIO(response.content))
		worksheet = workbook.active

		self.assertIn("Ali Ben Salah", worksheet["A5"].value)
		self.assertIn("22110099", worksheet["D5"].value)
		self.assertIn("ali@example.com", worksheet["I5"].value)
		self.assertIn("Magasin central", worksheet["I6"].value)
		self.assertEqual(worksheet["A10"].value, "Section Excel")
		self.assertEqual(worksheet["B10"].value, "Gants de protection")
		self.assertEqual(worksheet["D10"].value, 5)
		self.assertEqual(worksheet["H10"].value, "GANT-FOUR-01")
		self.assertEqual(worksheet["I10"].value, "Fournisseur Excel")
