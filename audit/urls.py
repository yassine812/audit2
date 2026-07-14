"""Routes du module audit."""

from django.urls import path

from . import views

app_name = "audit"

urlpatterns = [
    # Tableau de bord
    path("dashboard/", views.DashboardView.as_view(), name="dashboard"),
    # Liste audits
    path("", views.AuditListView.as_view(), name="list"),
    path("create/", views.AuditCreateView.as_view(), name="create"),
    path("<int:pk>/edit/", views.AuditUpdateView.as_view(), name="audit-edit"),
    path("<int:pk>/delete/", views.AuditDeleteView.as_view(), name="audit-delete"),
    path("<int:pk>/evaluation/", views.AuditEvaluationView.as_view(), name="audit-evaluation"),
    path("<int:audit_pk>/ajax/save-reponse/", views.ajax_save_reponse, name="ajax-save-reponse"),
    path("ajax/copy-formulaire/", views.ajax_copy_formulaire, name="ajax-copy-formulaire"),
    path("<int:pk>/", views.AuditDetailView.as_view(), name="detail"),
    path("<int:pk>/lancer/", views.AuditLancerView.as_view(), name="lancer"),
    path("<int:pk>/terminer/", views.AuditTerminerView.as_view(), name="terminer"),


    # Réponses
    path("reponse/<int:pk>/edit/", views.ReponseAuditUpdateView.as_view(), name="reponse-edit"),
    path("<int:pk>/reponses/", views.ReponseAuditMassUpdateView.as_view(), name="reponses-masse"),

    # Résultats
    path("resultat/<int:pk>/", views.ResultatAuditDetailView.as_view(), name="resultat-detail"),
    path("resultat/<int:pk>/edit/", views.ResultatAuditUpdateView.as_view(), name="resultat-edit"),
    path("<int:pk>/rapport/", views.AuditRapportView.as_view(), name="audit-rapport"),
    path("<int:pk>/rapport/pdf/", views.audit_pdf, name="audit-pdf"),
    path("<int:pk>/ajax/save-swot/", views.ajax_save_swot, name="ajax-save-swot"),


    # Référentiel
    path("referentiel/normes/", views.NormeDocumentListView.as_view(), name="norme-list"),
    path("referentiel/normes/create/", views.NormeDocumentCreateView.as_view(), name="norme-create"),
    path("referentiel/normes/<int:pk>/edit/", views.NormeDocumentUpdateView.as_view(), name="norme-edit"),
    path("referentiel/normes/<int:pk>/delete/", views.NormeDocumentDeleteView.as_view(), name="norme-delete"),

    path("referentiel/chapitres/", views.ChapitreNormeListView.as_view(), name="chapitre-list"),
    path("referentiel/chapitres/create/", views.ChapitreNormeCreateView.as_view(), name="chapitre-create"),
    path("referentiel/chapitres/ajax/create/", views.ajax_create_chapitre, name="chapitre-ajax-create"),
    path("referentiel/themes/ajax/create/", views.ajax_create_theme, name="theme-ajax-create"),
    path("referentiel/themes/ajax/criteres/add/", views.ajax_add_criteres, name="theme-ajax-add-criteres"),
    path("referentiel/chapitres/<int:pk>/edit/", views.ChapitreNormeUpdateView.as_view(), name="chapitre-edit"),
    path("referentiel/chapitres/<int:pk>/delete/", views.ChapitreNormeDeleteView.as_view(), name="chapitre-delete"),
    path("referentiel/chapitres/<int:pk>/", views.ChapitreNormeDetailView.as_view(), name="chapitre-detail"),
    path("referentiel/normes/<int:pk>/pdf/", views.norme_pdf_view, name="norme-pdf"),
    path("referentiel/normes/<int:pk>/pdf/", views.norme_pdf_view, name="norme-pdf"),

    path("referentiel/themes/", views.ThemeListView.as_view(), name="theme-list"),
    path("referentiel/themes/create/", views.ThemeCreateView.as_view(), name="theme-create"),
    path("referentiel/themes/<int:pk>/", views.ThemeDetailView.as_view(), name="theme-detail"),
    path("referentiel/themes/<int:pk>/edit/", views.ThemeUpdateView.as_view(), name="theme-edit"),
    path("referentiel/themes/<int:pk>/delete/", views.ThemeDeleteView.as_view(), name="theme-delete"),

    path("referentiel/criteres/", views.CritereEvaluationListView.as_view(), name="critere-list"),
    path("referentiel/criteres/create/", views.CritereEvaluationCreateView.as_view(), name="critere-create"),
    path("referentiel/criteres/<int:pk>/edit/", views.CritereEvaluationUpdateView.as_view(), name="critere-edit"),
    path("referentiel/criteres/<int:pk>/delete/", views.CritereEvaluationDeleteView.as_view(), name="critere-delete"),

    path("referentiel/baremes/", views.BaremeCotationListView.as_view(), name="bareme-list"),
    path("referentiel/baremes/create/", views.BaremeCotationCreateView.as_view(), name="bareme-create"),
    path("referentiel/baremes/<int:pk>/edit/", views.BaremeCotationUpdateView.as_view(), name="bareme-edit"),
    path("referentiel/baremes/<int:pk>/delete/", views.BaremeCotationDeleteView.as_view(), name="bareme-delete"),
    
    path("referentiel/niveaux/", views.NiveauxAttendusListView.as_view(), name="niveaux-list"),
    path("referentiel/niveaux/create/", views.NiveauxAttendusCreateView.as_view(), name="niveaux-create"),
    path("referentiel/niveaux/<int:pk>/edit/", views.NiveauxAttendusUpdateView.as_view(), name="niveaux-edit"),
    path("referentiel/niveaux/<int:pk>/delete/", views.NiveauxAttendusDeleteView.as_view(), name="niveaux-delete"),

    # Preuves attendues
    path("referentiel/preuves/", views.PreuveAttendueListView.as_view(), name="preuve-list"),
    path("referentiel/preuves/create/", views.PreuveAttendueCreateView.as_view(), name="preuve-create"),
    path("referentiel/preuves/<int:pk>/edit/", views.PreuveAttendueUpdateView.as_view(), name="preuve-edit"),
    path("referentiel/preuves/<int:pk>/delete/", views.PreuveAttendueDeleteView.as_view(), name="preuve-delete"),

    # Types de preuves
    path("referentiel/preuves/types/", views.PreuveAttendueTypeListView.as_view(), name="preuve-type-list"),
    path("referentiel/preuves/types/create/", views.PreuveAttendueTypeCreateView.as_view(), name="preuve-type-create"),
    path("referentiel/preuves/types/<int:pk>/edit/", views.PreuveAttendueTypeUpdateView.as_view(), name="preuve-type-edit"),
    path("referentiel/preuves/types/<int:pk>/delete/", views.PreuveAttendueTypeDeleteView.as_view(), name="preuve-type-delete"),

    # Formulaires
    path("formulaires/", views.FormulaireAuditListView.as_view(), name="formulaire-list"),
    path("formulaires/ajax/theme-data/", views.ajax_formulaire_theme_data, name="formulaire-ajax-theme-data"),
    path("formulaires/create/", views.FormulaireAuditCreateView.as_view(), name="formulaire-create"),
    path("formulaires/<int:pk>/", views.FormulaireAuditDetailView.as_view(), name="formulaire-detail"),
    path("formulaires/<int:pk>/edit/", views.FormulaireAuditUpdateView.as_view(), name="formulaire-edit"),
    path("formulaires/<int:pk>/delete/", views.FormulaireAuditDeleteView.as_view(), name="formulaire-delete"),
    path("formulaires/<int:formulaire_pk>/lignes/create/", views.LigneFormulaireCreateView.as_view(), name="ligne-create"),
    path("lignes/<int:pk>/edit/", views.LigneFormulaireUpdateView.as_view(), name="ligne-edit"),
    path("lignes/<int:pk>/delete/", views.LigneFormulaireDeleteView.as_view(), name="ligne-delete"),
    path("lignes/reorder/", views.ajax_reorder_lignes, name="ligne-reorder"),
]
