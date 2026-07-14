"""URLs du module Administration."""

from django.urls import path

from . import views

app_name = "administration"

urlpatterns = [
    # Dashboard
    path("", views.dashboard_admin, name="dashboard"),

    # Utilisateurs
    path("utilisateurs/", views.liste_utilisateurs, name="utilisateurs"),
    path("utilisateurs/nouveau/", views.creer_utilisateur, name="creer_utilisateur"),
    path("utilisateurs/<int:pk>/modifier/", views.modifier_utilisateur, name="modifier_utilisateur"),
    path("utilisateurs/<int:pk>/supprimer/", views.supprimer_utilisateur, name="supprimer_utilisateur"),

    # Sociétés
    path("societes/", views.liste_societes, name="societes"),
    path("societes/nouvelle/", views.creer_societe, name="creer_societe"),
    path("societes/<int:pk>/modifier/", views.modifier_societe, name="modifier_societe"),
    path("societes/<int:pk>/supprimer/", views.supprimer_societe, name="supprimer_societe"),

    # Sections
    path("sections/", views.liste_sections, name="sections"),
    path("sections/nouvelle/", views.creer_section, name="creer_section"),
    path("sections/<int:pk>/modifier/", views.modifier_section, name="modifier_section"),
    path("sections/<int:pk>/supprimer/", views.supprimer_section, name="supprimer_section"),

    # Sites
    path("sites/", views.liste_sites, name="sites"),
    path("sites/nouveau/", views.creer_site, name="creer_site"),
    path("sites/<int:pk>/modifier/", views.modifier_site, name="modifier_site"),
    path("sites/<int:pk>/supprimer/", views.supprimer_site, name="supprimer_site"),

    # Customers
    path("customers/", views.liste_customers, name="customers"),
    path("customers/nouveau/", views.creer_customer, name="creer_customer"),
    path("customers/<int:pk>/modifier/", views.modifier_customer, name="modifier_customer"),
    path("customers/<int:pk>/supprimer/", views.supprimer_customer, name="supprimer_customer"),
]
