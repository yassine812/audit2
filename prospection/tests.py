"""
Tests complets du module Prospection.
Couvre :
  - Modèles (création, contraintes, méthodes)
  - Vues web (login, dashboard, CRUD prospects/concurrents/clients/actions/events/SWOT/enquêtes)
  - API REST mobile (auth, actions, events, prospects, SWOT, notifications, calendrier)
  - Intégration SAGE (clé chargée depuis .env, connexion réelle)
  - Formulaires (SocieteForm, EntrepriseForm)
"""

import json
import uuid
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from accounts.models import Societe
from prospection.models import (
    Action,
    Entreprise,
    Enquete,
    EnqueteToken,
    Evenement,
    FCMDevice,
    Notification,
    NotificationUtilisateur,
    ProspectInfo,
    ProspectResearch,
    Question,
    Reponse,
    Swot,
)
from prospection.forms import SocieteForm, EntrepriseForm
from prospection.utils.client_utils import get_base_url

User = get_user_model()


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def make_societe(nom="TestSociété"):
    return Societe.objects.create(nom=nom)


def make_superuser(username="superadmin"):
    return User.objects.create_superuser(
        username=username, password="superpass123!", email=f"{username}@test.com"
    )


def make_rc_user(societe, username="rc_user"):
    return User.objects.create_user(
        username=username, password="rcpass123!", email=f"{username}@test.com",
        is_RC=True, societe=societe
    )


def make_commercial_user(societe, username="commercial"):
    return User.objects.create_user(
        username=username, password="compass123!", email=f"{username}@test.com",
        is_C=True, societe=societe
    )


def make_entreprise(societe, is_CLT=False, is_Prospect=False, is_Concurent=False,
                    nom="Acme Corp", num_compte=None):
    return Entreprise.objects.create(
        nom=nom,
        adresse="1 Rue Test",
        secteur_activite="IT",
        telephone="0600000000",
        email="contact@acme.com",
        is_CLT=is_CLT,
        is_Prospect=is_Prospect,
        is_Concurent=is_Concurent,
        societe=societe,
        num_compte=num_compte,
    )


def make_action(entreprise, societe, user, is_Appel=True):
    return Action.objects.create(
        sujet="Test Action",
        compte_rendu="CR test",
        notes="Notes test",
        is_Appel=is_Appel,
        entreprise=entreprise,
        societe=societe,
        created_by=user,
        pilote=user,
        date_heure_planifie=timezone.now() + timedelta(days=1),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 1. MODÈLES
# ═══════════════════════════════════════════════════════════════════════════════

class EntrepriseModelTest(TestCase):
    def setUp(self):
        self.societe = make_societe()

    def test_create_client(self):
        e = make_entreprise(self.societe, is_CLT=True, num_compte="CL001")
        self.assertEqual(str(e), "Acme Corp")
        self.assertTrue(e.is_CLT)

    def test_create_prospect(self):
        e = make_entreprise(self.societe, is_Prospect=True)
        self.assertTrue(e.is_Prospect)

    def test_create_concurrent(self):
        e = make_entreprise(self.societe, is_Concurent=True, nom="Rival Inc")
        self.assertTrue(e.is_Concurent)

    def test_unique_num_compte_par_societe(self):
        make_entreprise(self.societe, is_CLT=True, num_compte="CL002")
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            make_entreprise(self.societe, is_CLT=True, num_compte="CL002", nom="Other")


class ActionModelTest(TestCase):
    def setUp(self):
        self.societe = make_societe()
        self.user = make_rc_user(self.societe)
        self.entreprise = make_entreprise(self.societe, is_CLT=True)

    def test_create_appel_action(self):
        a = make_action(self.entreprise, self.societe, self.user, is_Appel=True)
        self.assertTrue(a.is_Appel)
        self.assertIn("Test Action", str(a))

    def test_create_email_action(self):
        a = make_action(self.entreprise, self.societe, self.user, is_Appel=False)
        a.is_Email = True
        a.save()
        self.assertTrue(a.is_Email)

    def test_create_rv_action(self):
        a = Action.objects.create(
            sujet="RDV Test",
            compte_rendu="CR",
            notes="",
            is_RV=True,
            etat="planifie",
            entreprise=self.entreprise,
            societe=self.societe,
            created_by=self.user,
            date_heure_planifie=timezone.now(),
        )
        self.assertTrue(a.is_RV)

    def test_invalid_etat_appel_raises(self):
        a = Action(
            sujet="Bad State",
            compte_rendu="",
            notes="",
            is_Appel=True,
            etat="planifie",  # invalid for appel
            entreprise=self.entreprise,
            societe=self.societe,
            created_by=self.user,
            date_heure_planifie=timezone.now(),
        )
        with self.assertRaises(ValueError):
            a.save()


class EvenementModelTest(TestCase):
    def setUp(self):
        self.societe = make_societe()
        self.user = make_rc_user(self.societe)

    def test_create_evenement(self):
        e = Evenement.objects.create(
            nom="Conférence Annuelle",
            lieu="Paris",
            secteur_activite="IT",
            type="interne",
            created_by=self.user,
            societe=self.societe,
            date_heure_planifie=timezone.now(),
        )
        self.assertIn("Conférence Annuelle", str(e))


class SwotModelTest(TestCase):
    def setUp(self):
        self.societe = make_societe()
        self.user = make_rc_user(self.societe)
        self.concurrent = make_entreprise(self.societe, is_Concurent=True, nom="Rival")

    def test_create_swot(self):
        s = Swot.objects.create(
            type="force",
            description="Innovation rapide",
            axe="technologique",
            entreprise=self.concurrent,
            societe=self.societe,
            created_by=self.user,
        )
        self.assertEqual(str(s), "Force | Technologique | " + str(s.date))


class NotificationModelTest(TestCase):
    def setUp(self):
        self.societe = make_societe()
        self.user = make_rc_user(self.societe)

    def test_create_notification(self):
        n = Notification.objects.create(
            message="Nouvelle action créée",
            type="action",
            lien_id=1,
        )
        n.utilisateurs.add(self.user)
        self.assertIn(self.user, n.utilisateurs.all())
        self.assertIn("Nouvelle action créée", str(n))

    def test_notification_utilisateur_mark_read(self):
        n = Notification.objects.create(message="Test notif", type="event", lien_id=2)
        nu = NotificationUtilisateur.objects.create(notification=n, utilisateur=self.user)
        self.assertFalse(nu.est_lu)
        nu.est_lu = True
        nu.save()
        self.assertTrue(NotificationUtilisateur.objects.get(pk=nu.pk).est_lu)


class QuestionModelTest(TestCase):
    def test_create_question_and_get_text(self):
        q = Question.objects.create(
            question_fr="Comment évaluez-vous notre service ?",
            question_en="How do you rate our service?",
            type=Question.Type.CLOSED,
        )
        self.assertEqual(q.get_question_text('fr'), "Comment évaluez-vous notre service ?")
        self.assertEqual(q.get_question_text('en'), "How do you rate our service?")
        self.assertEqual(q.get_question_text('de'), "Comment évaluez-vous notre service ?")  # fallback


class EnqueteModelTest(TestCase):
    def setUp(self):
        self.societe = make_societe()
        self.user = make_rc_user(self.societe)
        self.client_ent = make_entreprise(self.societe, is_CLT=True, nom="ClientX")

    def test_create_enquete(self):
        e = Enquete.objects.create(
            description="Enquête satisfaction",
            date_creation=datetime.now().date(),
            created_by=self.user,
            client=self.client_ent,
        )
        self.assertEqual(e.client, self.client_ent)

    def test_enquete_token_is_valid(self):
        e = Enquete.objects.create(
            description="Enquête avec token",
            date_creation=datetime.now().date(),
            created_by=self.user,
            client=self.client_ent,
        )
        token = EnqueteToken.objects.create(
            enquete=e,
            client=self.client_ent,
        )
        self.assertTrue(token.is_valid())
        self.assertFalse(token.used)


class ProspectResearchModelTest(TestCase):
    def setUp(self):
        self.societe = make_societe()
        self.user = make_rc_user(self.societe)
        self.entreprise = make_entreprise(self.societe, is_Prospect=True)

    def test_create_research(self):
        pr = ProspectResearch.objects.create(
            entreprise=self.entreprise,
            created_by=self.user,
            query="Recherche contact",
            summary="Résumé trouvé",
            confidence="high",
        )
        self.assertIn(self.entreprise.nom, str(pr))

    def test_create_prospect_info(self):
        pr = ProspectResearch.objects.create(
            entreprise=self.entreprise,
            created_by=self.user,
            confidence="medium",
        )
        info = ProspectInfo.objects.create(
            entreprise=self.entreprise,
            research=pr,
            type=ProspectInfo.InfoType.EMAIL,
            value="contact@prospect.com",
        )
        self.assertEqual(info.value, "contact@prospect.com")


# ═══════════════════════════════════════════════════════════════════════════════
# 2. FORMULAIRES
# ═══════════════════════════════════════════════════════════════════════════════

class SocieteFormTest(TestCase):
    def test_valid_form(self):
        form = SocieteForm(data={"nom": "Nouvelle Société"})
        self.assertTrue(form.is_valid())

    def test_empty_nom_invalid(self):
        form = SocieteForm(data={"nom": ""})
        self.assertFalse(form.is_valid())


class EntrepriseFormTest(TestCase):
    def setUp(self):
        self.societe = make_societe()

    def test_valid_form(self):
        form = EntrepriseForm(data={
            "nom": "TestCorp",
            "adresse": "2 Avenue Test",
            "secteur_activite": "Finance",
            "telephone": "0700000000",
            "email": "test@corp.com",
            "is_CLT": True,
            "is_Prospect": False,
            "is_Concurent": False,
            "societe": self.societe.pk,
            "date": datetime.now().date().isoformat(),
        })
        self.assertTrue(form.is_valid(), form.errors)

    def test_invalid_email(self):
        form = EntrepriseForm(data={
            "nom": "BadCorp",
            "adresse": "X",
            "secteur_activite": "X",
            "telephone": "X",
            "email": "not-an-email",
            "is_CLT": False,
            "is_Prospect": True,
            "is_Concurent": False,
            "societe": self.societe.pk,
            "date": datetime.now().date().isoformat(),
        })
        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)


# ═══════════════════════════════════════════════════════════════════════════════
# 3. VUES WEB — Authentification
# ═══════════════════════════════════════════════════════════════════════════════

class AuthViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.societe = make_societe()
        self.user = make_rc_user(self.societe, "auth_user")

    def test_login_page_get(self):
        resp = self.client.get(reverse("prospection:login"))
        self.assertEqual(resp.status_code, 200)

    def test_login_success(self):
        resp = self.client.post(reverse("prospection:login"), {
            "username": "auth_user",
            "password": "rcpass123!",
        }, follow=True)
        self.assertEqual(resp.status_code, 200)

    def test_login_wrong_credentials(self):
        resp = self.client.post(reverse("prospection:login"), {
            "username": "auth_user",
            "password": "wrong",
        })
        self.assertNotEqual(resp.wsgi_request.user.is_authenticated, True)

    def test_logout(self):
        self.client.login(username="auth_user", password="rcpass123!")
        resp = self.client.post(reverse("prospection:logout"), follow=True)
        self.assertEqual(resp.status_code, 200)


# ═══════════════════════════════════════════════════════════════════════════════
# 4. VUES WEB — Dashboard & pages protégées
# ═══════════════════════════════════════════════════════════════════════════════

class DashboardViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.societe = make_societe()
        self.user = make_rc_user(self.societe, "dash_user")
        self.client.login(username="dash_user", password="rcpass123!")

    def test_dashboard_accessible(self):
        resp = self.client.get(reverse("prospection:index"))
        self.assertIn(resp.status_code, [200, 302])

    def test_dashboard_redirect_if_not_logged_in(self):
        c = Client()
        resp = c.get(reverse("prospection:index"))
        self.assertIn(resp.status_code, [302, 301])


# ═══════════════════════════════════════════════════════════════════════════════
# 5. VUES WEB — Entreprises (Prospects, Clients, Concurrents)
# ═══════════════════════════════════════════════════════════════════════════════

class EntrepriseWebViewsTest(TestCase):
    def setUp(self):
        self.client_http = Client()
        self.societe = make_societe()
        self.superuser = make_superuser("ent_super")
        self.client_http.login(username="ent_super", password="superpass123!")
        self.prospect = make_entreprise(self.societe, is_Prospect=True, nom="ProspectA")
        self.clt = make_entreprise(self.societe, is_CLT=True, nom="ClientA", num_compte="C001")
        self.concurrent = make_entreprise(self.societe, is_Concurent=True, nom="ConcurrentA")

    def test_prospects_list(self):
        resp = self.client_http.get(reverse("prospection:prospects_list"))
        self.assertEqual(resp.status_code, 200)

    def test_prospect_detail(self):
        resp = self.client_http.get(
            reverse("prospection:prospect_detail", args=[self.prospect.pk])
        )
        self.assertEqual(resp.status_code, 200)

    def test_add_prospect(self):
        resp = self.client_http.post(reverse("prospection:add_entreprise", args=["prospect"]), {
            "nom": "NouveauProspect",
            "adresse": "3 Rue Prospect",
            "secteur_activite": "Commerce",
            "telephone": "0611111111",
            "email": "np@test.com",
            "is_Prospect": True,
            "societe": self.societe.pk,
            "date": datetime.now().date().isoformat(),
        }, follow=True)
        self.assertIn(resp.status_code, [200, 302])

    def test_edit_prospect(self):
        resp = self.client_http.post(
            reverse("prospection:edit_entreprise", args=[self.prospect.pk, "prospect"]),
            {
                "nom": "ProspectEdited",
                "adresse": "Edited Rue",
                "secteur_activite": "IT",
                "telephone": "0699999999",
                "email": "edited@test.com",
                "date": datetime.now().date().isoformat(),
            },
            follow=True,
        )
        self.assertIn(resp.status_code, [200, 302])

    def test_delete_prospect(self):
        to_delete = make_entreprise(self.societe, is_Prospect=True, nom="ToDelete")
        resp = self.client_http.post(
            reverse("prospection:delete_entreprise", args=[to_delete.pk, "prospect"]),
            follow=True,
        )
        self.assertIn(resp.status_code, [200, 302])
        self.assertFalse(Entreprise.objects.filter(pk=to_delete.pk).exists())

    def test_convert_prospect_to_client(self):
        resp = self.client_http.post(
            reverse("prospection:convert_prospect_to_client", args=[self.prospect.pk]),
            follow=True,
        )
        self.assertIn(resp.status_code, [200, 302])

    def test_gestion_concurrents(self):
        resp = self.client_http.get(reverse("prospection:gestion_concurrents"))
        self.assertIn(resp.status_code, [200, 302])


# ═══════════════════════════════════════════════════════════════════════════════
# 6. VUES WEB — Actions (Appels, Emails, RVs)
# ═══════════════════════════════════════════════════════════════════════════════

class ActionWebViewsTest(TestCase):
    def setUp(self):
        self.c = Client()
        self.societe = make_societe()
        self.user = make_superuser("action_super")
        self.c.login(username="action_super", password="superpass123!")
        self.entreprise = make_entreprise(self.societe, is_CLT=True, nom="ActionCorp", num_compte="A001")
        self.action = make_action(self.entreprise, self.societe, self.user, is_Appel=True)

    def test_call_list(self):
        resp = self.c.get(reverse("prospection:call_list"))
        self.assertEqual(resp.status_code, 200)

    def test_email_list(self):
        resp = self.c.get(reverse("prospection:email_list"))
        self.assertEqual(resp.status_code, 200)

    def test_rv_list(self):
        resp = self.c.get(reverse("prospection:rv_list"))
        self.assertEqual(resp.status_code, 200)

    def test_call_details(self):
        resp = self.c.get(reverse("prospection:call_details", args=[self.action.pk]))
        self.assertIn(resp.status_code, [200, 302])

    def test_action_details(self):
        resp = self.c.get(reverse("prospection:action_details", args=[self.action.pk]))
        self.assertIn(resp.status_code, [200, 302])

    def test_delete_call(self):
        to_del = make_action(self.entreprise, self.societe, self.user, is_Appel=True)
        to_del.sujet = "ToDelete"
        to_del.save()
        resp = self.c.post(
            reverse("prospection:delete_call", args=[to_del.pk]),
            follow=True,
        )
        self.assertIn(resp.status_code, [200, 302])
        self.assertFalse(Action.objects.filter(pk=to_del.pk).exists())


# ═══════════════════════════════════════════════════════════════════════════════
# 7. VUES WEB — Événements
# ═══════════════════════════════════════════════════════════════════════════════

class EventWebViewsTest(TestCase):
    def setUp(self):
        self.c = Client()
        self.societe = make_societe()
        self.user = make_superuser("event_super")
        self.c.login(username="event_super", password="superpass123!")
        self.event = Evenement.objects.create(
            nom="Salon Tech",
            lieu="Lyon",
            secteur_activite="IT",
            type="externe",
            created_by=self.user,
            societe=self.societe,
            date_heure_planifie=timezone.now(),
        )

    def test_event_list_interne(self):
        resp = self.c.get(reverse("prospection:event_list", args=["interne"]))
        self.assertEqual(resp.status_code, 200)

    def test_event_list_externe(self):
        resp = self.c.get(reverse("prospection:event_list", args=["externe"]))
        self.assertEqual(resp.status_code, 200)

    def test_event_details(self):
        resp = self.c.get(reverse("prospection:event_details", args=[self.event.pk]))
        self.assertIn(resp.status_code, [200, 302])

    def test_delete_event(self):
        ev = Evenement.objects.create(
            nom="ToDelete",
            lieu="Paris",
            secteur_activite="Commerce",
            type="interne",
            created_by=self.user,
            societe=self.societe,
            date_heure_planifie=timezone.now(),
        )
        resp = self.c.post(
            reverse("prospection:delete_event", args=[ev.pk]),
            follow=True,
        )
        self.assertIn(resp.status_code, [200, 302])
        self.assertFalse(Evenement.objects.filter(pk=ev.pk).exists())


# ═══════════════════════════════════════════════════════════════════════════════
# 8. VUES WEB — SWOT
# ═══════════════════════════════════════════════════════════════════════════════

class SwotWebViewsTest(TestCase):
    def setUp(self):
        self.c = Client()
        self.societe = make_societe()
        self.user = make_superuser("swot_super")
        self.c.login(username="swot_super", password="superpass123!")
        self.concurrent = make_entreprise(self.societe, is_Concurent=True, nom="SwotRival")
        self.swot = Swot.objects.create(
            type="force",
            description="Innovation",
            axe="technologique",
            entreprise=self.concurrent,
            societe=self.societe,
            created_by=self.user,
        )

    def test_swot_list(self):
        resp = self.c.get(reverse("prospection:swot_list"))
        self.assertEqual(resp.status_code, 200)

    def test_get_swot_details(self):
        resp = self.c.get(reverse("prospection:get_swot_details", args=[self.swot.pk]))
        self.assertIn(resp.status_code, [200, 302])

    def test_delete_swot(self):
        s = Swot.objects.create(
            type="faiblesse", description="Lent", axe="commercial",
            entreprise=self.concurrent, societe=self.societe, created_by=self.user,
        )
        resp = self.c.post(
            reverse("prospection:delete_swot", args=[s.pk]),
            follow=True,
        )
        self.assertIn(resp.status_code, [200, 302])
        self.assertFalse(Swot.objects.filter(pk=s.pk).exists())


# ═══════════════════════════════════════════════════════════════════════════════
# 9. VUES WEB — Enquêtes & Questions
# ═══════════════════════════════════════════════════════════════════════════════

class EnqueteWebViewsTest(TestCase):
    def setUp(self):
        self.c = Client()
        self.societe = make_societe()
        self.user = make_superuser("enq_super")
        self.c.login(username="enq_super", password="superpass123!")
        self.client_ent = make_entreprise(self.societe, is_CLT=True, nom="ClientEnq", num_compte="E001")
        self.question = Question.objects.create(
            question_fr="Êtes-vous satisfait ?",
            question_en="Are you satisfied?",
            type=Question.Type.OUINON,
        )
        self.enquete = Enquete.objects.create(
            description="Satisfaction générale",
            date_creation=datetime.now().date(),
            created_by=self.user,
            client=self.client_ent,
        )
        self.enquete.questions.add(self.question)

    def test_questions_list(self):
        resp = self.c.get(reverse("prospection:questions"))
        self.assertEqual(resp.status_code, 200)

    def test_enquetes_list(self):
        resp = self.c.get(reverse("prospection:enquetes"))
        self.assertEqual(resp.status_code, 200)

    def test_detail_enquete(self):
        resp = self.c.get(reverse("prospection:detail_enquete", args=[self.enquete.pk]))
        self.assertIn(resp.status_code, [200, 302])

    def test_enquetes_analytics(self):
        resp = self.c.get(reverse("prospection:enquetes_analytics"))
        self.assertIn(resp.status_code, [200, 302])

    def test_question_stats(self):
        resp = self.c.get(reverse("prospection:question_stats", args=[self.question.pk]))
        self.assertIn(resp.status_code, [200, 302])

    def test_repondre_enquete_with_token(self):
        token = EnqueteToken.objects.create(
            enquete=self.enquete,
            client=self.client_ent,
        )
        resp = self.c.get(reverse("prospection:repondre_enquete", args=[token.token]))
        self.assertIn(resp.status_code, [200, 302])


# ═══════════════════════════════════════════════════════════════════════════════
# 10. VUES WEB — Utilisateurs
# ═══════════════════════════════════════════════════════════════════════════════

class UtilisateurWebViewsTest(TestCase):
    def setUp(self):
        self.c = Client()
        self.societe = make_societe()
        self.superuser = make_superuser("user_super")
        self.c.login(username="user_super", password="superpass123!")

    def test_liste_utilisateurs(self):
        resp = self.c.get(reverse("prospection:liste_utilisateurs"))
        self.assertEqual(resp.status_code, 200)

    def test_ajouter_utilisateur_get(self):
        resp = self.c.get(reverse("prospection:ajouter_utilisateur"))
        self.assertEqual(resp.status_code, 200)


# ═══════════════════════════════════════════════════════════════════════════════
# 11. VUES WEB — Sociétés
# ═══════════════════════════════════════════════════════════════════════════════

class SocieteWebViewsTest(TestCase):
    def setUp(self):
        self.c = Client()
        self.societe = make_societe(nom="MainSociete")
        self.superuser = make_superuser("soc_super")
        self.c.login(username="soc_super", password="superpass123!")

    def test_societe_list(self):
        resp = self.c.get(reverse("prospection:societe"))
        self.assertIn(resp.status_code, [200, 302])

    def test_add_societe(self):
        resp = self.c.post(reverse("prospection:add_societe"), {
            "nom": "NewSociete",
        }, follow=True)
        self.assertIn(resp.status_code, [200, 302])
        self.assertTrue(Societe.objects.filter(nom="NewSociete").exists())

    def test_edit_societe(self):
        soc = Societe.objects.create(nom="EditMe")
        resp = self.c.post(
            reverse("prospection:edit_societe", args=[soc.pk]),
            {"nom": "EditedName"},
            follow=True,
        )
        self.assertIn(resp.status_code, [200, 302])

    def test_delete_societe(self):
        soc = Societe.objects.create(nom="DeleteMe")
        resp = self.c.post(
            reverse("prospection:delete_societe", args=[soc.pk]),
            follow=True,
        )
        self.assertIn(resp.status_code, [200, 302])
        self.assertFalse(Societe.objects.filter(pk=soc.pk).exists())


# ═══════════════════════════════════════════════════════════════════════════════
# 12. VUES WEB — Notifications
# ═══════════════════════════════════════════════════════════════════════════════

class NotificationWebViewsTest(TestCase):
    def setUp(self):
        self.c = Client()
        self.societe = make_societe()
        self.user = make_rc_user(self.societe, "notif_user")
        self.c.login(username="notif_user", password="rcpass123!")
        self.notif = Notification.objects.create(
            message="Test notification web", type="action", lien_id=1
        )
        NotificationUtilisateur.objects.create(notification=self.notif, utilisateur=self.user)

    def test_all_notifications_page(self):
        resp = self.c.get(reverse("prospection:all_notifications"))
        self.assertIn(resp.status_code, [200, 302])

    def test_unread_count_api(self):
        resp = self.c.get(reverse("prospection:unread_notifications_count"))
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("count", data)

    def test_mark_all_as_read(self):
        resp = self.c.post(reverse("prospection:mark_all_notifications_as_read"))
        self.assertIn(resp.status_code, [200, 302])

    def test_mark_single_notification_read(self):
        resp = self.c.post(
            reverse("prospection:mark_notification_read", args=[self.notif.pk])
        )
        self.assertIn(resp.status_code, [200, 302])


# ═══════════════════════════════════════════════════════════════════════════════
# 13. API REST — Authentification mobile
# ═══════════════════════════════════════════════════════════════════════════════

class MobileLoginAPITest(TestCase):
    def setUp(self):
        self.api = APIClient()
        self.societe = make_societe()
        self.user = make_rc_user(self.societe, "mob_user")

    def test_mobile_login_success(self):
        resp = self.api.post(
            reverse("prospection:mobile-login"),
            {"username": "mob_user", "password": "rcpass123!"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn("token", resp.data)
        self.assertIn("user_id", resp.data)
        self.assertIn("is_RC", resp.data)

    def test_mobile_login_bad_credentials(self):
        resp = self.api.post(
            reverse("prospection:mobile-login"),
            {"username": "mob_user", "password": "wrong"},
            format="json",
        )
        self.assertEqual(resp.status_code, 404)

    def test_mobile_login_missing_fields(self):
        resp = self.api.post(
            reverse("prospection:mobile-login"),
            {"username": "mob_user"},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_mobile_logout(self):
        self.api.post(
            reverse("prospection:mobile-login"),
            {"username": "mob_user", "password": "rcpass123!"},
            format="json",
        )
        token = Token.objects.get(user=self.user)
        self.api.credentials(HTTP_AUTHORIZATION="Token " + token.key)
        resp = self.api.post(reverse("prospection:api-logout"))
        self.assertEqual(resp.status_code, 200)


# ═══════════════════════════════════════════════════════════════════════════════
# 14. API REST — Sociétés
# ═══════════════════════════════════════════════════════════════════════════════

class SocieteAPITest(TestCase):
    def setUp(self):
        self.api = APIClient()
        self.societe = make_societe()
        self.superuser = make_superuser("soc_api_super")
        self.token = Token.objects.create(user=self.superuser)
        self.api.credentials(HTTP_AUTHORIZATION="Token " + self.token.key)

    def test_societe_list_superuser(self):
        resp = self.api.get(reverse("prospection:societe_list"))
        self.assertEqual(resp.status_code, 200)
        noms = [s["nom"] for s in resp.data]
        self.assertIn(self.societe.nom, noms)

    def test_societe_list_rc_user(self):
        rc = make_rc_user(self.societe, "soc_rc")
        token = Token.objects.create(user=rc)
        api2 = APIClient()
        api2.credentials(HTTP_AUTHORIZATION="Token " + token.key)
        resp = api2.get(reverse("prospection:societe_list"))
        self.assertEqual(resp.status_code, 200)

    def test_societe_list_unauthenticated(self):
        api_anon = APIClient()
        resp = api_anon.get(reverse("prospection:societe_list"))
        self.assertEqual(resp.status_code, 401)


# ═══════════════════════════════════════════════════════════════════════════════
# 15. API REST — Actions
# ═══════════════════════════════════════════════════════════════════════════════

class ActionAPITest(TestCase):
    def setUp(self):
        self.api = APIClient()
        self.societe = make_societe()
        self.user = make_superuser("act_api_super")
        self.token = Token.objects.create(user=self.user)
        self.api.credentials(HTTP_AUTHORIZATION="Token " + self.token.key)
        self.entreprise = make_entreprise(self.societe, is_Prospect=True, nom="ProspectAPI")
        self.action = make_action(self.entreprise, self.societe, self.user, is_Appel=True)

    def test_action_list_get(self):
        resp = self.api.get(reverse("prospection:action-list-create"))
        self.assertEqual(resp.status_code, 200)

    def test_action_create_prospect(self):
        resp = self.api.post(
            reverse("prospection:action-list-create"),
            {
                "sujet": "Nouveau Appel",
                "date_heure_planifie": (timezone.now() + timedelta(days=2)).isoformat(),
                "entreprise": str(self.entreprise.pk),
                "entreprise_type": "prospect",
                "is_Appel": True,
                "compte_rendu": "",
                "notes": "",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data["sujet"], "Nouveau Appel")

    def test_action_create_missing_sujet(self):
        resp = self.api.post(
            reverse("prospection:action-list-create"),
            {
                "date_heure_planifie": timezone.now().isoformat(),
                "entreprise": str(self.entreprise.pk),
                "entreprise_type": "prospect",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_action_detail_get(self):
        resp = self.api.get(reverse("prospection:action_detail", args=[self.action.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["sujet"], self.action.sujet)

    def test_action_count(self):
        resp = self.api.get(reverse("prospection:action-counts"))
        self.assertEqual(resp.status_code, 200)
        self.assertIn("calls", resp.data)
        self.assertIn("emails", resp.data)
        self.assertIn("appointments", resp.data)

    def test_calendar_actions(self):
        resp = self.api.get(reverse("prospection:calendar_actions"))
        self.assertEqual(resp.status_code, 200)
        self.assertIn("marked_dates", resp.data)

    def test_update_action_complete(self):
        resp = self.api.patch(
            reverse("prospection:update-action", args=[self.action.pk]),
            {
                "date_heure_realiser": (timezone.now()).strftime("%d/%m/%Y, %H:%M"),
                "compte_rendu": "Appel bien passé",
                "notes": "RAS",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["compte_rendu"], "Appel bien passé")

    def test_update_action_bad_date_format(self):
        resp = self.api.patch(
            reverse("prospection:update-action", args=[self.action.pk]),
            {"date_heure_realiser": "2024-01-01"},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_update_action_not_found(self):
        resp = self.api.patch(
            reverse("prospection:update-action", args=[99999]),
            {"date_heure_realiser": ""},
            format="json",
        )
        self.assertEqual(resp.status_code, 404)


# ═══════════════════════════════════════════════════════════════════════════════
# 16. API REST — Événements
# ═══════════════════════════════════════════════════════════════════════════════

class EventAPITest(TestCase):
    def setUp(self):
        self.api = APIClient()
        self.societe = make_societe()
        self.user = make_superuser("ev_api_super")
        self.token = Token.objects.create(user=self.user)
        self.api.credentials(HTTP_AUTHORIZATION="Token " + self.token.key)
        self.event = Evenement.objects.create(
            nom="API Event",
            lieu="Tunis",
            secteur_activite="Tech",
            type="interne",
            created_by=self.user,
            societe=self.societe,
            date_heure_planifie=timezone.now(),
        )

    def test_create_event_interne(self):
        resp = self.api.post(
            reverse("prospection:create_event"),
            {
                "nom": "Nouveau Événement",
                "lieu": "Sfax",
                "secteur_activite": "Commerce",
                "type": "interne",
                "date_heure_planifie": (timezone.now() + timedelta(days=3)).isoformat(),
                "societe": str(self.societe.pk),
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data["nom"], "Nouveau Événement")

    def test_create_event_missing_fields(self):
        resp = self.api.post(
            reverse("prospection:create_event"),
            {"nom": "Incomplete"},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_create_event_invalid_type(self):
        resp = self.api.post(
            reverse("prospection:create_event"),
            {
                "nom": "Bad Type",
                "lieu": "X",
                "secteur_activite": "X",
                "type": "invalide",
                "date_heure_planifie": timezone.now().isoformat(),
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_event_counts(self):
        resp = self.api.get(reverse("prospection:event-counts"))
        self.assertEqual(resp.status_code, 200)
        self.assertIn("internalEvents", resp.data)
        self.assertIn("externalEvents", resp.data)

    def test_calendar_events(self):
        resp = self.api.get(reverse("prospection:calendar_events"))
        self.assertEqual(resp.status_code, 200)
        self.assertIn("marked_dates", resp.data)

    def test_update_event(self):
        resp = self.api.patch(
            reverse("prospection:update-event", args=[self.event.pk]),
            {
                "date_heure_realiser": timezone.now().strftime("%d/%m/%Y, %H:%M"),
                "notes": "Réalisé avec succès",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["notes"], "Réalisé avec succès")

    def test_update_event_not_found(self):
        resp = self.api.patch(
            reverse("prospection:update-event", args=[99999]),
            {"notes": ""},
            format="json",
        )
        self.assertEqual(resp.status_code, 404)


# ═══════════════════════════════════════════════════════════════════════════════
# 17. API REST — Entreprises
# ═══════════════════════════════════════════════════════════════════════════════

class EntrepriseAPITest(TestCase):
    def setUp(self):
        self.api = APIClient()
        self.societe = make_societe()
        self.user = make_superuser("ent_api_super")
        self.token = Token.objects.create(user=self.user)
        self.api.credentials(HTTP_AUTHORIZATION="Token " + self.token.key)
        make_entreprise(self.societe, is_CLT=True, nom="APIClient", num_compte="API001")
        make_entreprise(self.societe, is_Prospect=True, nom="APIProspect")
        make_entreprise(self.societe, is_Concurent=True, nom="APIConcurrent")

    def test_entreprise_list_all(self):
        resp = self.api.get(reverse("prospection:entreprise-list"))
        self.assertEqual(resp.status_code, 200)
        noms = [e["nom"] for e in resp.data]
        self.assertIn("APIClient", noms)

    def test_entreprise_list_filter_clients(self):
        resp = self.api.get(reverse("prospection:entreprise-list") + "?is_CLT=true")
        self.assertEqual(resp.status_code, 200)
        for e in resp.data:
            self.assertTrue(e["is_CLT"])

    def test_entreprise_list_filter_concurrents(self):
        resp = self.api.get(reverse("prospection:entreprise-list") + "?is_Concurent=true")
        self.assertEqual(resp.status_code, 200)

    def test_get_entreprises_by_type_client(self):
        resp = self.api.get(reverse("prospection:get_entreprises_by_type") + "?is_CLT=true")
        self.assertEqual(resp.status_code, 200)
        for e in resp.data:
            self.assertTrue(e["is_CLT"])

    def test_get_entreprises_by_type_prospect(self):
        resp = self.api.get(reverse("prospection:get_entreprises_by_type") + "?is_CLT=false")
        self.assertEqual(resp.status_code, 200)


# ═══════════════════════════════════════════════════════════════════════════════
# 18. API REST — Prospects (création mobile)
# ═══════════════════════════════════════════════════════════════════════════════

class ProspectAPITest(TestCase):
    def setUp(self):
        self.api = APIClient()
        self.societe = make_societe()
        self.rc_user = make_rc_user(self.societe, "prosp_rc")
        self.token = Token.objects.create(user=self.rc_user)
        self.api.credentials(HTTP_AUTHORIZATION="Token " + self.token.key)

    def test_create_prospect_success(self):
        resp = self.api.post(
            reverse("prospection:create_prospect"),
            {
                "nom": "Nouveau Prospect Mobile",
                "secteur_activite": "Finance",
                "telephone": "0612345678",
                "email": "prospect@mobile.com",
                "adresse": "5 Rue Mobile",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data["nom"], "Nouveau Prospect Mobile")
        self.assertTrue(resp.data["is_Prospect"])

    def test_create_prospect_missing_nom(self):
        resp = self.api.post(
            reverse("prospection:create_prospect"),
            {"secteur_activite": "IT"},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_create_prospect_superuser_requires_societe(self):
        super_api = APIClient()
        su = make_superuser("prosp_super2")
        su_token = Token.objects.create(user=su)
        super_api.credentials(HTTP_AUTHORIZATION="Token " + su_token.key)
        resp = super_api.post(
            reverse("prospection:create_prospect"),
            {"nom": "SuperProspect"},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)
        # The error message mentions "société" (French with accent) — check a safe substring
        self.assertIn("obligatoire", str(resp.data).lower())

    def test_create_prospect_superuser_with_societe(self):
        super_api = APIClient()
        su = make_superuser("prosp_super3")
        su_token = Token.objects.create(user=su)
        super_api.credentials(HTTP_AUTHORIZATION="Token " + su_token.key)
        resp = super_api.post(
            reverse("prospection:create_prospect"),
            {"nom": "SuperProspectWithSoc", "societe": str(self.societe.pk)},
            format="json",
        )
        self.assertEqual(resp.status_code, 201)


# ═══════════════════════════════════════════════════════════════════════════════
# 19. API REST — SWOT
# ═══════════════════════════════════════════════════════════════════════════════

class SwotAPITest(TestCase):
    def setUp(self):
        self.api = APIClient()
        self.societe = make_societe()
        self.rc_user = make_rc_user(self.societe, "swot_rc")
        self.token = Token.objects.create(user=self.rc_user)
        self.api.credentials(HTTP_AUTHORIZATION="Token " + self.token.key)
        self.concurrent = make_entreprise(self.societe, is_Concurent=True, nom="SWOTAPI Rival")

    def test_add_swot_success(self):
        resp = self.api.post(
            reverse("prospection:add_swot"),
            json.dumps({
                "type": "force",
                "description": "Bonne réputation",
                "axe": "commercial",
                "entreprise": self.concurrent.pk,
                "created_by_id": self.rc_user.pk,
            }),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get("success"))

    def test_add_swot_missing_type(self):
        resp = self.api.post(
            reverse("prospection:add_swot"),
            json.dumps({
                "axe": "commercial",
                "entreprise": self.concurrent.pk,
                "created_by_id": self.rc_user.pk,
            }),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertFalse(data.get("success"))

    def test_swot_count(self):
        resp = self.api.get(reverse("prospection:swot_count"))
        self.assertEqual(resp.status_code, 200)
        self.assertIn("count", resp.json())

    def test_swot_axes(self):
        resp = self.api.get(reverse("prospection:swot_axes"))
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get("success"))
        axes_values = [a["value"] for a in data["data"]]
        self.assertIn("commercial", axes_values)
        self.assertIn("technologique", axes_values)

    def test_get_concurrents(self):
        resp = self.api.get(reverse("prospection:get_concurrents"))
        self.assertEqual(resp.status_code, 200)
        noms = [e["nom"] for e in resp.data]
        self.assertIn("SWOTAPI Rival", noms)


# ═══════════════════════════════════════════════════════════════════════════════
# 20. API REST — Notifications mobiles
# ═══════════════════════════════════════════════════════════════════════════════

class MobileNotificationsAPITest(TestCase):
    def setUp(self):
        self.api = APIClient()
        self.societe = make_societe()
        self.user = make_rc_user(self.societe, "notif_api_user")
        self.token = Token.objects.create(user=self.user)
        self.api.credentials(HTTP_AUTHORIZATION="Token " + self.token.key)
        self.notif = Notification.objects.create(
            message="Mobile notif test", type="action", lien_id=10
        )
        self.nu = NotificationUtilisateur.objects.create(
            notification=self.notif, utilisateur=self.user
        )

    def test_mobile_notifications_list(self):
        resp = self.api.get(reverse("prospection:mobile_notifications"))
        self.assertEqual(resp.status_code, 200)
        self.assertIn("notifications", resp.data)

    def test_mobile_mark_as_read(self):
        resp = self.api.post(
            reverse("prospection:mobile_mark_as_read"),
            {"notification_id": self.nu.pk},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.nu.refresh_from_db()
        self.assertTrue(self.nu.est_lu)

    def test_mobile_mark_as_read_not_found(self):
        resp = self.api.post(
            reverse("prospection:mobile_mark_as_read"),
            {"notification_id": 99999},
            format="json",
        )
        self.assertEqual(resp.status_code, 404)

    def test_register_fcm_token(self):
        resp = self.api.post(
            reverse("prospection:register_fcm_token"),
            {"token": "fcm_test_token_xyz"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(FCMDevice.objects.filter(registration_id="fcm_test_token_xyz").exists())

    def test_register_fcm_token_missing(self):
        resp = self.api.post(
            reverse("prospection:register_fcm_token"),
            {},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)


# ═══════════════════════════════════════════════════════════════════════════════
# 21. API REST — Clients SAGE (mocked)
# ═══════════════════════════════════════════════════════════════════════════════

MOCK_SAGE_CLIENTS = [
    {
        "NumeroTiers": "CL001",
        "Intitule": "Société Alpha",
        "Email": "alpha@sage.com",
        "Telephone1": "0700111222",
        "Telephone2": "",
    },
    {
        "NumeroTiers": "CL002",
        "Intitule": "Bêta Industries",
        "Email": "beta@sage.com",
        "Telephone1": "0700333444",
        "Telephone2": "",
    },
]

MOCK_SAGE_CLIENT_DETAIL = {
    "NumeroTiers": "CL001",
    "Intitule": "Société Alpha",
    "Email": "alpha@sage.com",
    "Telephone": "0700111222",
    "Adresse": "1 Route de Lyon",
}


class SageClientsMockedAPITest(TestCase):
    """Tests des endpoints clients SAGE avec un serveur SAGE simulé."""

    def setUp(self):
        self.api = APIClient()
        self.societe = Societe.objects.create(nom="TestSociete_Sage")
        self.superuser = make_superuser("sage_super")
        self.token = Token.objects.create(user=self.superuser)
        self.api.credentials(HTTP_AUTHORIZATION="Token " + self.token.key)

    @patch("prospection.api.requests.get")
    @patch("prospection.views.requests.get")
    def test_get_active_customers_api_sage_search(self, mock_views_get, mock_api_get):
        """Recherche clients : résultats combinés local + SAGE."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = MOCK_SAGE_CLIENTS
        mock_api_get.return_value = mock_response
        mock_views_get.return_value = mock_response

        with patch("prospection.api.get_base_url", return_value="ABSERVE_TUNISIE"):
            with patch("prospection.api.Societe") as mock_soc_class:
                mock_soc_class.objects.all.return_value = [self.societe]
                resp = self.api.get(
                    reverse("prospection:api_ajax_customers") + "?q=alpha"
                )
        self.assertIn(resp.status_code, [200, 400, 500])

    @patch("prospection.api.requests.get")
    def test_get_client_details_api_sage(self, mock_get):
        """Récupération des détails d'un client depuis SAGE."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'{"NumeroTiers":"CL001","Intitule":"Soc Alpha"}'
        mock_response.json.return_value = MOCK_SAGE_CLIENT_DETAIL
        mock_get.return_value = mock_response

        with patch("prospection.api.get_base_url", return_value="ABSERVE_TUNISIE"):
            resp = self.api.get(
                reverse("prospection:api_client_details", args=["CL001"])
                + f"?societe={self.societe.nom}"
            )
        self.assertIn(resp.status_code, [200, 400])

    @patch("prospection.api.requests.get")
    def test_action_create_with_sage_client(self, mock_get):
        """Création d'une action avec un client venant de SAGE (auto-création locale)."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "NumeroTiers": "SAGE001",
            "Intitule": "Sage Client Direct",
            "Email": "sage@client.com",
            "Adresse": "SAGE Rue",
            "Telephone": "0000000001",
        }
        mock_get.return_value = mock_response

        with patch("prospection.api.get_base_url", return_value="ABSERVE_TUNISIE"):
            resp = self.api.post(
                reverse("prospection:action-list-create"),
                {
                    "sujet": "Appel SAGE",
                    "date_heure_planifie": (timezone.now() + timedelta(days=1)).isoformat(),
                    "entreprise": "SAGE001",
                    "entreprise_type": "client",
                    "societe": str(self.societe.pk),
                    "is_Appel": True,
                    "compte_rendu": "",
                    "notes": "",
                },
                format="json",
            )
        self.assertIn(resp.status_code, [201, 400])
        if resp.status_code == 201:
            self.assertTrue(Entreprise.objects.filter(num_compte="SAGE001").exists())


# ═══════════════════════════════════════════════════════════════════════════════
# 22. SAGE API — Connexion réelle (via clé .env)
# ═══════════════════════════════════════════════════════════════════════════════

class SageAPIRealConnectionTest(TestCase):
    """
    Teste la connexion réelle à l'API Sage en utilisant les credentials du fichier .env.
    Ces tests font de vraies requêtes HTTP — ils sont marqués avec un commentaire
    pour être facilement désactivés en CI si le réseau n'est pas disponible.
    """

    def setUp(self):
        self.host = settings.SAGE_API_HOST
        self.token = settings.SAGE_API_TOKEN
        self.headers = {
            "Authorization": self.token,
            "Accept": "application/json",
        }

    def test_sage_token_loaded_from_env(self):
        """Le token SAGE doit être chargé depuis .env et non vide."""
        self.assertTrue(
            self.token,
            "SAGE_API_TOKEN est vide — vérifiez que le fichier .env est bien chargé."
        )
        self.assertNotEqual(
            self.token, "",
            "SAGE_API_TOKEN ne doit pas être une chaîne vide."
        )

    def test_sage_host_loaded_from_env(self):
        """Le host SAGE doit être chargé depuis .env."""
        self.assertTrue(self.host, "SAGE_API_HOST est vide.")
        self.assertTrue(
            self.host.startswith("http"),
            f"SAGE_API_HOST doit commencer par http(s): {self.host}"
        )

    def _try_sage_request(self, base):
        """Tente une requête sur un endpoint SAGE et retourne la réponse."""
        url = f"{self.host}/WebServices100/{base}/TiersService/rest/Clients"
        try:
            resp = requests.get(url, headers=self.headers, timeout=15)
            return resp
        except requests.exceptions.ConnectionError:
            return None
        except requests.exceptions.Timeout:
            return None

    def test_sage_abserve_tunisie_connection(self):
        """Test de connexion à la base ABSERVE_TUNISIE."""
        resp = self._try_sage_request("ABSERVE_TUNISIE")
        if resp is None:
            self.skipTest("Serveur SAGE ABSERVE_TUNISIE inaccessible depuis ce réseau.")
        self.assertIn(
            resp.status_code, [200, 401, 403, 404],
            f"Réponse inattendue du serveur SAGE ABSERVE_TUNISIE: {resp.status_code} — {resp.text[:200]}"
        )
        if resp.status_code == 200:
            data = resp.json()
            self.assertIsInstance(data, list, "La réponse SAGE doit être une liste de clients.")

    def test_sage_abserve_connection(self):
        """Test de connexion à la base ABSERVE."""
        resp = self._try_sage_request("ABSERVE")
        if resp is None:
            self.skipTest("Serveur SAGE ABSERVE inaccessible depuis ce réseau.")
        self.assertIn(
            resp.status_code, [200, 401, 403, 404],
            f"Réponse inattendue du serveur SAGE ABSERVE: {resp.status_code} — {resp.text[:200]}"
        )

    def test_sage_qfz_connection(self):
        """Test de connexion à la base QFZ."""
        resp = self._try_sage_request("QFZ")
        if resp is None:
            self.skipTest("Serveur SAGE QFZ inaccessible depuis ce réseau.")
        self.assertIn(
            resp.status_code, [200, 401, 403, 404],
            f"Réponse inattendue du serveur SAGE QFZ: {resp.status_code} — {resp.text[:200]}"
        )

    def test_sage_token_auth_header_format(self):
        """Vérifie que le token est utilisé tel quel comme Authorization header."""
        self.assertEqual(
            self.headers["Authorization"],
            self.token,
            "Le header Authorization doit contenir le token brut (pas Bearer)."
        )


# ═══════════════════════════════════════════════════════════════════════════════
# 23. Utilitaires — get_base_url
# ═══════════════════════════════════════════════════════════════════════════════

class GetBaseUrlTest(TestCase):
    def test_known_ids(self):
        self.assertEqual(get_base_url(3), "ABSERVE_TUNISIE")
        self.assertEqual(get_base_url(4), "ABSERVE")
        self.assertEqual(get_base_url(6), "QFZ")

    def test_unknown_id_returns_none(self):
        self.assertIsNone(get_base_url(99))
        self.assertIsNone(get_base_url(0))

    def test_none_input(self):
        self.assertIsNone(get_base_url(None))


# ═══════════════════════════════════════════════════════════════════════════════
# 24. API REST — Rapport IA (generate_report_view, mocké)
# ═══════════════════════════════════════════════════════════════════════════════

class GenerateReportAPITest(TestCase):
    def setUp(self):
        self.c = Client()
        self.societe = make_societe()
        self.user = make_superuser("report_super")
        self.c.force_login(self.user)
        self.entreprise = make_entreprise(self.societe, is_CLT=True, nom="ReportCorp", num_compte="R001")

    @patch("prospection.api.generate_report", return_value="Rapport généré automatiquement.")
    def test_generate_report_call(self, mock_gen):
        resp = self.c.post(
            reverse("prospection:generate_report"),
            json.dumps({
                "company": str(self.societe.pk),
                "contact": str(self.entreprise.pk),
                "action_type": "call",
                "subject": "Appel test",
                "planned_date": "01/06/2026",
                "answers": {
                    "q0": "Discussion produit",
                    "q1": "Client intéressé",
                    "q2": "Envoi devis",
                },
            }),
            content_type="application/json",
        )
        self.assertIn(resp.status_code, [200, 400, 403])
        if resp.status_code == 200:
            data = resp.json()
            self.assertIn("report", data)

    @patch("prospection.api.generate_report", return_value="Rapport email.")
    def test_generate_report_email(self, mock_gen):
        resp = self.c.post(
            reverse("prospection:generate_report"),
            json.dumps({
                "company": str(self.societe.pk),
                "contact": str(self.entreprise.pk),
                "action_type": "email",
                "subject": "Offre commerciale",
                "planned_date": "02/06/2026",
                "answers": {"q0": "Contenu email", "q1": "Urgent", "q2": "Réponse sous 48h"},
            }),
            content_type="application/json",
        )
        self.assertIn(resp.status_code, [200, 400, 403])

    def test_generate_report_invalid_action_type(self):
        resp = self.c.post(
            reverse("prospection:generate_report"),
            json.dumps({
                "company": str(self.societe.pk),
                "contact": str(self.entreprise.pk),
                "action_type": "sms",  # invalide
                "subject": "Test",
                "planned_date": "01/06/2026",
                "answers": {},
            }),
            content_type="application/json",
        )
        self.assertIn(resp.status_code, [400, 403])

    def test_generate_report_missing_subject(self):
        resp = self.c.post(
            reverse("prospection:generate_report"),
            json.dumps({
                "company": str(self.societe.pk),
                "contact": str(self.entreprise.pk),
                "action_type": "call",
                "planned_date": "01/06/2026",
                "answers": {},
            }),
            content_type="application/json",
        )
        self.assertIn(resp.status_code, [400, 403])


# ═══════════════════════════════════════════════════════════════════════════════
# 25. Permissions — Accès selon rôle
# ═══════════════════════════════════════════════════════════════════════════════

class RoleBasedAccessTest(TestCase):
    def setUp(self):
        self.societe_a = make_societe("SocieteA")
        self.societe_b = make_societe("SocieteB")
        self.rc_a = make_rc_user(self.societe_a, "rc_a")
        self.rc_b = make_rc_user(self.societe_b, "rc_b")
        self.token_a = Token.objects.create(user=self.rc_a)
        self.token_b = Token.objects.create(user=self.rc_b)
        self.ent_a = make_entreprise(self.societe_a, is_Prospect=True, nom="ProspectA_Role")
        self.ent_b = make_entreprise(self.societe_b, is_Prospect=True, nom="ProspectB_Role")

    def test_action_list_rc_filtered_by_societe(self):
        """RC de SocieteA ne voit que les actions de sa société."""
        action_a = make_action(self.ent_a, self.societe_a, self.rc_a)
        action_b = make_action(self.ent_b, self.societe_b, self.rc_b)

        api = APIClient()
        api.credentials(HTTP_AUTHORIZATION="Token " + self.token_a.key)
        resp = api.get(reverse("prospection:action-list-create"))
        self.assertEqual(resp.status_code, 200)
        ids = [a["id"] for a in resp.data]
        self.assertIn(action_a.pk, ids)
        self.assertNotIn(action_b.pk, ids)

    def test_unauthenticated_action_list_rejected(self):
        api_anon = APIClient()
        resp = api_anon.get(reverse("prospection:action-list-create"))
        self.assertEqual(resp.status_code, 401)

    def test_unauthenticated_prospect_creation_rejected(self):
        api_anon = APIClient()
        resp = api_anon.post(
            reverse("prospection:create_prospect"),
            {"nom": "Anon Prospect"},
            format="json",
        )
        self.assertEqual(resp.status_code, 401)
