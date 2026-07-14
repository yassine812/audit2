"""Routes du module Accidents de Travail."""

from django.urls import path

from . import views
from .mixins import at_roles_required

app_name = "at"

urlpatterns = [
    # Dashboard
    path("", at_roles_required(views.dashboard), name="at_dashboard"),

    # Liste et détail
    path("liste/", at_roles_required(views.AccidentListView.as_view()), name="at_liste"),
    path("<int:pk>/", at_roles_required(views.AccidentDetailView.as_view()), name="at_detail"),

    # Création et modification — 3 étapes
    path("nouveau/", at_roles_required(views.AccidentCreate24hView.as_view()), name="at_create_24h"),
    path("nouveau/rapide/", at_roles_required(views.at_create_quick), name="at_create_quick"),
    path("<int:pk>/modifier-24h/", at_roles_required(views.AccidentUpdate24hView.as_view()), name="at_update_24h"),
    path("<int:pk>/analyse-48h/", at_roles_required(views.Analyse48hView.as_view()), name="at_analyse_48h"),
    path("<int:pk>/lap-8j/", at_roles_required(views.LAP8JView.as_view()), name="at_lap_8j"),

    # Rapport complet (impression / PDF)
    path("<int:pk>/rapport/", at_roles_required(views.accident_rapport), name="at_rapport"),

    # Export Excel
    path("<int:pk>/export-excel/", at_roles_required(views.accident_export_excel), name="at_export_excel"),

    # Statistiques globales des causes
    path("causes/", at_roles_required(views.global_causes_view), name="at_causes_globales"),

    # Autocomplete causes racines (AJAX)
    path("api/causes/autocomplete/", at_roles_required(views.causes_autocomplete), name="at_causes_autocomplete"),

    # Auto-save brouillon
    path("<int:pk>/auto-save/", at_roles_required(views.auto_save_draft), name="at_auto_save"),

    # Auto-save questionnaire 48h (AJAX partiel)
    path("<int:pk>/questionnaire-autosave/", at_roles_required(views.questionnaire_autosave), name="at_questionnaire_autosave"),

    # Auto-save complet formulaire 48h et LAP 8j (AJAX)
    path("<int:pk>/autosave-48h/", at_roles_required(views.autosave_analyse_48h), name="at_autosave_48h"),
    path("<int:pk>/autosave-8j/", at_roles_required(views.autosave_lap_8j), name="at_autosave_8j"),

    # API filtrage dynamique
    path("api/sections/<int:societe_id>/", at_roles_required(views.api_sections_by_societe), name="at_api_sections"),
    path("api/sites/<int:section_id>/", at_roles_required(views.api_sites_by_section), name="at_api_sites"),

    # ── Référentiel questionnaire 48h (CRUD) ────────────────────────────────
    path("questionnaire/", at_roles_required(views.questionnaire_list), name="questionnaire_list"),
    path("questionnaire/nouveau/", at_roles_required(views.questionnaire_create), name="questionnaire_create"),
    path("questionnaire/<int:pk>/modifier/", at_roles_required(views.questionnaire_update), name="questionnaire_update"),
    path("questionnaire/<int:pk>/supprimer/", at_roles_required(views.questionnaire_delete), name="questionnaire_delete"),

    # ── Arbre des causes ──────────────────────────────────────────────────────
    path("<int:pk>/arbre-causes/", at_roles_required(views.arbre_causes_view), name="at_arbre_causes"),
    path("<int:pk>/arbre-causes/api/", at_roles_required(views.arbre_causes_api), name="at_arbre_causes_api"),
] 
