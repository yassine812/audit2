"""URLs du module gestion documentaire."""

from django.urls import path

from .views import (
    CreerNouvelleVersionView,
    DashboardQSEView,
    DocumentCreateView,
    DocumentDetailView,
    DocumentListView,
    DocumentUpdateView,
    DossierCreateView,
    approuver_document,
    archiver_document,
    exporter_document_pdf,
    fichier_version,
    modifier_dossier,
    renommer_fichier,
    supprimer_dossier,
    supprimer_fichier,
    telecharger_fichier_bibliotheque,
    uploader_fichiers,
    visualiser_fichier_bibliotheque,
    soumettre_verification,
)

app_name = "gestion_documentaire"

urlpatterns = [
    path("documents/", DocumentListView.as_view(), name="document_list"),
    path("documents/racine/", DocumentListView.as_view(), {"racine": True}, name="bibliotheque_racine"),
    path("documents/dossier/<int:dossier_id>/", DocumentListView.as_view(), name="dossier_detail"),
    path("documents/dossiers/nouveau/", DossierCreateView.as_view(), name="dossier_create"),
    path("documents/dossier/<int:dossier_id>/nouveau/", DossierCreateView.as_view(), name="sous_dossier_create"),
    path("documents/dossier/<int:dossier_id>/upload/", uploader_fichiers, name="uploader_fichiers"),
    path("documents/racine/upload/", uploader_fichiers, name="uploader_fichiers_racine"),
    path("documents/dossiers/<int:pk>/modifier/", modifier_dossier, name="modifier_dossier"),
    path("documents/dossiers/<int:pk>/supprimer/", supprimer_dossier, name="supprimer_dossier"),
    path("documents/fichiers/<int:pk>/renommer/", renommer_fichier, name="renommer_fichier"),
    path("documents/fichiers/<int:pk>/supprimer/", supprimer_fichier, name="supprimer_fichier"),
    path("documents/fichiers/<int:pk>/telecharger/", telecharger_fichier_bibliotheque, name="telecharger_fichier_bibliotheque"),
    path("documents/fichiers/<int:pk>/visualiser/", visualiser_fichier_bibliotheque, name="visualiser_fichier_bibliotheque"),
    path("documents/nouveau/", DocumentCreateView.as_view(), name="document_create"),
    path("documents/<int:pk>/", DocumentDetailView.as_view(), name="document_detail"),
    path("documents/<int:pk>/modifier/", DocumentUpdateView.as_view(), name="document_update"),
    path("documents/<int:pk>/soumettre-verification/", soumettre_verification, name="soumettre_verification"),
    path("documents/<int:pk>/approuver/", approuver_document, name="approuver_document"),
    path("documents/<int:pk>/archiver/", archiver_document, name="archiver_document"),
    path("documents/<int:pk>/nouvelle-version/", CreerNouvelleVersionView.as_view(), name="creer_nouvelle_version"),
    path("documents/<int:pk>/export-pdf/", exporter_document_pdf, name="exporter_document_pdf"),
    path("versions/<int:pk>/fichier/<str:nature>/", fichier_version, name="fichier_version"),
    path("dashboard/", DashboardQSEView.as_view(), name="dashboard_qse"),
]
