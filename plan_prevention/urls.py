"""URL configuration du module Plan de Prévention (PDP)."""

from django.urls import path
from . import views

app_name = "plan_prevention"

urlpatterns = [
    path("", views.PDPDashboardView.as_view(), name="dashboard"),
    path("dashboard/", views.PDPDashboardView.as_view(), name="pdp_dashboard"),
    path("liste/", views.PDPListView.as_view(), name="liste"),
    path("nouveau/", views.PDPCreateView.as_view(), name="create"),
    path("<int:pk>/", views.PDPDetailView.as_view(), name="detail"),
    path("<int:pk>/modifier/", views.PDPUpdateView.as_view(), name="update"),
    path("<int:pk>/supprimer/", views.PDPDeleteView.as_view(), name="delete"),
    path("<int:pk>/export-pdf/", views.export_pdp_pdf, name="export_pdf"),
    path("risques/", views.RisqueListView.as_view(), name="risque_list"),
    # API Ajax auto-complete customer & creation de risque
    path("api/customer/<int:pk>/", views.api_customer_details, name="api_customer_details"),
    path("api/risque/nouveau/", views.api_create_risque, name="api_create_risque"),
]

