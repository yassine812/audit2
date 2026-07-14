"""Configuration admin pour l'app accounts."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Customer, Section, Site, Societe, User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = (
        "username", "email", "first_name", "last_name",
        "section", "societe", "role_display",
        "is_RS", "is_RO", "is_CE", "is_OP", "is_auditeur",
        "is_C", "is_RC", "is_CLT",
        "is_staff", "is_active",
    )
    list_filter = (
        "section", "societe",
        "is_auditeur", "is_RS", "is_RO", "is_CE", "is_OP",
        "is_C", "is_RC", "is_CLT",
        "is_resp", "is_divers", "is_assistante", "is_sais", "is_interime",
        "is_staff", "is_active",
    )
    search_fields = ("username", "first_name", "last_name", "email", "telephone")
    fieldsets = UserAdmin.fieldsets + (
        (
            "Organisation",
            {"fields": ("section", "societe", "societes", "customer")},
        ),
        (
            "Coordonnées",
            {"fields": ("telephone", "pays", "adresse", "vat_code")},
        ),
        (
            "Rôles ERP / Opérations",
            {
                "fields": (
                    "is_RS", "is_RO", "is_CE", "is_OP",
                    "is_resp", "is_divers", "is_assistante", "is_sais", "is_interime",
                )
            },
        ),
        (
            "Rôles Audit & Commercial",
            {"fields": ("is_auditeur", "is_C", "is_RC", "is_CLT")},
        ),
        (
            "Métadonnées",
            {
                "fields": (
                    "admin_created", "rs_created", "ce_created",
                    "cout_horaire", "failed_attempts", "timezone",
                )
            },
        ),
    )


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display  = ("intitule", "compte", "type", "societe", "email", "telephone", "is_draft")
    list_filter   = ("societe", "is_draft", "type")
    search_fields = ("intitule", "compte", "email", "siret")


@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display  = ("Nom", "societe", "pays", "gouvernorat")
    list_filter   = ("societe", "pays")
    search_fields = ("Nom", "gouvernorat")


@admin.register(Societe)
class SocieteAdmin(admin.ModelAdmin):
    list_display  = ("nom",)
    search_fields = ("nom",)


@admin.register(Site)
class SiteAdmin(admin.ModelAdmin):
    list_display  = ("nom", "section")
    list_filter   = ("section",)
    search_fields = ("nom",)
