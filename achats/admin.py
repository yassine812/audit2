"""Administration du module Achats."""

from django.contrib import admin

from .models import (
    ArticleCatalogue,
    ConfigurationValidationSection,
    Devis,
    DemandeAchat,
    Dysfonctionnement,
    EvaluationFournisseur,
    Fournisseur,
    LigneDemandeAchat,
    OffreFournisseur,
    ReceptionMarchandise,
)


class OffreFournisseurInline(admin.TabularInline):
    """Inline pour gérer les offres fournisseurs depuis l'article."""

    model = OffreFournisseur
    extra = 1


class LigneDemandeAchatInline(admin.TabularInline):
    """Inline des lignes de demande d'achat."""

    model = LigneDemandeAchat
    extra = 1


class DevisInline(admin.TabularInline):
    """Inline pour les devis saisis sur une ligne de demande."""

    model = Devis
    extra = 0


@admin.register(Fournisseur)
class FournisseurAdmin(admin.ModelAdmin):
    list_display = ("nom", "reference_fournisseur", "contact_nom", "contact_mail", "statut_evaluation", "pris_en_compte")
    list_filter = ("statut_evaluation", "pris_en_compte")
    search_fields = ("nom", "reference_fournisseur", "contact_nom", "contact_mail")


@admin.register(ArticleCatalogue)
class ArticleCatalogueAdmin(admin.ModelAdmin):
    list_display = ("reference", "designation", "stock_disponible", "prix_reference_ht", "categorie", "type_article", "actif", "cree_par")
    list_filter = ("categorie", "type_article", "actif")
    search_fields = ("reference", "designation", "description")
    inlines = [OffreFournisseurInline]


@admin.register(OffreFournisseur)
class OffreFournisseurAdmin(admin.ModelAdmin):
    list_display = ("article", "fournisseur", "tarif_propose", "reference_chez_fournisseur")
    list_filter = ("article", "fournisseur")
    search_fields = ("article__designation", "fournisseur__nom")


@admin.register(DemandeAchat)
class DemandeAchatAdmin(admin.ModelAdmin):
    list_display = (
        "numero",
        "demandeur",
        "section_analytique",
        "categorie",
        "statut",
        "total_commande_ht",
        "date_creation",
    )
    list_filter = ("statut", "categorie", "section_analytique")
    search_fields = ("numero", "demandeur__username", "demandeur__first_name", "demandeur__last_name")
    inlines = [LigneDemandeAchatInline]


@admin.register(Devis)
class DevisAdmin(admin.ModelAdmin):
    list_display = ("ligne", "fournisseur", "prix_propose", "est_choisi", "saisi_par", "date_saisie")
    list_filter = ("est_choisi", "fournisseur")
    search_fields = ("ligne__demande__numero", "fournisseur__nom", "reference_fournisseur")


@admin.register(ReceptionMarchandise)
class ReceptionMarchandiseAdmin(admin.ModelAdmin):
    list_display = ("demande", "date_reception", "receptionne_par", "conforme_quantite_etat", "score_calcule", "note_calculee")
    list_filter = ("conforme_quantite_etat", "note_calculee")
    search_fields = ("demande__numero", "receptionne_par__username")


@admin.register(Dysfonctionnement)
class DysfonctionnementAdmin(admin.ModelAdmin):
    list_display = ("id", "demande", "reception", "statut", "signale_par", "date_signalement")
    list_filter = ("statut", "date_signalement")
    search_fields = ("demande__numero", "description", "signale_par__username")


@admin.register(EvaluationFournisseur)
class EvaluationFournisseurAdmin(admin.ModelAdmin):
    list_display = ("fournisseur", "annee", "pris_en_compte", "nb_receptions_evaluees", "score_moyen", "note", "nb_dysfonctionnements")
    list_filter = ("annee", "pris_en_compte", "note")
    search_fields = ("fournisseur__nom",)


@admin.register(ConfigurationValidationSection)
class ConfigurationValidationSectionAdmin(admin.ModelAdmin):
    list_display = ("section", "validateur_n1", "validateur_n2", "date_modification")
    search_fields = (
        "section__Nom",
        "validateur_n1__username",
        "validateur_n1__first_name",
        "validateur_n1__last_name",
        "validateur_n2__username",
        "validateur_n2__first_name",
        "validateur_n2__last_name",
    )
