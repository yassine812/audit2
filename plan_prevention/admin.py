"""Administration Django pour le module Plan de Prévention (PDP)."""

from django.contrib import admin
from .models import PlanPrevention, PlanPreventionRisque, RisquePDP


@admin.register(RisquePDP)
class RisquePDPAdmin(admin.ModelAdmin):
    list_display = ("ordre", "code", "titre", "categorie", "est_actif", "cree_le")
    list_filter = ("est_actif", "categorie")
    search_fields = ("code", "titre", "description", "mesures_prevention_recommandees")
    ordering = ("ordre", "code")


class PlanPreventionRisqueInline(admin.TabularInline):
    model = PlanPreventionRisque
    extra = 0
    fields = (
        "ordre",
        "risque",
        "concerne_eu",
        "concerne_ee",
        "mesures_prevention",
        "mise_en_oeuvre_eu",
        "mise_en_oeuvre_ee",
    )
    raw_id_fields = ("risque",)
    ordering = ("ordre",)


@admin.register(PlanPrevention)
class PlanPreventionAdmin(admin.ModelAdmin):
    list_display = (
        "reference",
        "nature_operation",
        "type_operation",
        "eu_nom",
        "ee_nom",
        "date_debut",
        "statut",
        "created_at",
    )
    list_filter = ("statut", "type_operation", "societe", "suivi_medical_renforce")
    search_fields = ("reference", "nature_operation", "eu_nom", "ee_nom", "lieu_intervention")
    raw_id_fields = ("societe", "section", "site", "customer", "created_by")
    inlines = [PlanPreventionRisqueInline]
    date_hierarchy = "created_at"

