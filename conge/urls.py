"""Routes du module Gestion des Congés."""

from django.urls import path
from . import views
from . import configuration_views

app_name = "conge"

urlpatterns = [
    # Tableau de bord
    path("dashboard/", views.dashboard_conge, name="dashboard"),

    # Liste principale
    path("", views.liste_conges, name="liste"),

    # Nouvelle demande
    path("nouvelle/", views.nouvelle_demande, name="nouvelle_demande"),

    # Détail
    path("<int:pk>/", views.detail_conge, name="detail"),

    # Validation / refus (RO/RS uniquement)
    path("<int:pk>/valider/", views.valider_conge, name="valider"),

    # Téléchargement PDF
    path("<int:pk>/pdf/<str:exemplaire>/", views.telecharger_pdf, name="pdf"),

    # Configuration de la chaîne de validation (admin)
    path("admin/configuration/", configuration_views.configuration_list, name="config_list"),
    path("admin/configuration/<int:section_id>/", configuration_views.configuration_detail, name="config_detail"),

    # Actions AJAX pour la configuration
    path("admin/configuration/<int:section_id>/add-ro/", configuration_views.add_validateur_ro, name="add_ro"),
    path("admin/configuration/<int:section_id>/remove-ro/", configuration_views.remove_validateur_ro, name="remove_ro"),
    path("admin/configuration/<int:section_id>/add-rs/", configuration_views.add_validateur_rs, name="add_rs"),
    path("admin/configuration/<int:section_id>/remove-rs/", configuration_views.remove_validateur_rs, name="remove_rs"),
    path("admin/configuration/<int:section_id>/add-ce/", configuration_views.add_gestionnaire_ce, name="add_ce"),
    path("admin/configuration/<int:section_id>/remove-ce/", configuration_views.remove_gestionnaire_ce, name="remove_ce"),
]
