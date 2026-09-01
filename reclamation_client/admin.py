"""Administration Django du module Réclamation Client."""

from django.contrib import admin

from .models import (
    ActionPermanenteD6,
    ActionTestD5,
    AnalyseCausesDoubleAxeD4,
    CapitalisationSMQSD7,
    ClotureRecevabiliteD8,
    DescriptionQQOQCCP,
    MesureConservatoireD3,
    Participant8D,
    ReclamationClient,
)


class Participant8DInline(admin.TabularInline):
    model = Participant8D
    extra = 1


class MesureConservatoireD3Inline(admin.TabularInline):
    model = MesureConservatoireD3
    extra = 0


class ActionTestD5Inline(admin.TabularInline):
    model = ActionTestD5
    extra = 0


class ActionPermanenteD6Inline(admin.TabularInline):
    model = ActionPermanenteD6
    extra = 0


@admin.register(ReclamationClient)
class ReclamationClientAdmin(admin.ModelAdmin):
    list_display = (
        "reference", "client_nom", "type_signalement", "mode_traitement",
        "statut", "date_alerte_client", "accuse_reception_envoye",
    )
    list_filter = ("type_signalement", "mode_traitement", "statut", "societe", "site")
    search_fields = ("reference", "client_nom", "numero_reclamation_client", "description_piece")
    inlines = [Participant8DInline, MesureConservatoireD3Inline, ActionTestD5Inline, ActionPermanenteD6Inline]


admin.site.register(DescriptionQQOQCCP)
admin.site.register(AnalyseCausesDoubleAxeD4)
admin.site.register(CapitalisationSMQSD7)
admin.site.register(ClotureRecevabiliteD8)
