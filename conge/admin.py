"""Administration du module Gestion des Congés."""

from django.contrib import admin
from .models import DemandeConge, ValidationChainConfiguration


@admin.register(DemandeConge)
class DemandeCongeAdmin(admin.ModelAdmin):
    list_display  = (
        "id", "nom", "prenom", "section", "date_debut", "date_fin",
        "nombre_jours", "type_conge", "statut", "date_demande",
        "date_validation", "validateur",
    )
    list_filter   = ("statut", "type_conge", "section", "date_demande")
    search_fields = ("nom", "prenom", "demandeur__username", "demandeur__email")
    readonly_fields = (
        "date_demande", "created_at", "updated_at",
        "signature_demandeur", "signature_responsable",
    )
    list_per_page = 25
    date_hierarchy = "date_demande"

    fieldsets = (
        ("Demandeur", {
            "fields": ("demandeur", "nom", "prenom", "section"),
        }),
        ("Période", {
            "fields": ("date_debut", "date_fin", "date_reprise", "nombre_jours"),
        }),
        ("Imputation", {
            "fields": ("type_conge", "evenement_familial_precision"),
        }),
        ("Workflow", {
            "fields": ("statut", "date_demande", "date_validation", "validateur", "commentaire_refus"),
        }),
        ("Signatures", {
            "fields": ("signature_demandeur", "signature_responsable"),
            "classes": ("collapse",),
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )


@admin.register(ValidationChainConfiguration)
class ValidationChainConfigurationAdmin(admin.ModelAdmin):
    list_display = (
        "section", "get_ro_count", "get_rs_count",
        "get_ce_count", "date_modification", "modifie_par"
    )
    list_filter = ("section", "date_modification")
    search_fields = ("section__Nom",)
    filter_horizontal = (
        "validateurs_ro", "validateurs_rs",
        "gestionnaires_ce"
    )
    readonly_fields = ("date_modification",)

    def get_ro_count(self, obj):
        return obj.validateurs_ro.count()
    get_ro_count.short_description = "Validateurs RO"

    def get_rs_count(self, obj):
        return obj.validateurs_rs.count()
    get_rs_count.short_description = "Validateurs RS"

    def get_ce_count(self, obj):
        return obj.gestionnaires_ce.count()
    get_ce_count.short_description = "Gestionnaires CE"
