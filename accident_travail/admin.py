"""Administration Django du module Accidents de Travail."""

import csv
from django.contrib import admin
from django.http import HttpResponse
from django.utils.html import format_html

from .models import (
    AccidentTravail,
    ActionCorrective,
    ActionCorrectiveImmédiate,
    Analyse48h,
    LAP8Jours,
    QuestionnaireItem,
    QuestionnaireTemplate,
)


def export_csv(modeladmin, request, queryset):
    """Action admin : exporter la sélection en CSV."""
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="accidents.csv"'
    response.write("\ufeff")  # BOM UTF-8 pour Excel
    writer = csv.writer(response, delimiter=";")
    writer.writerow([
        "Référence", "Type", "Statut", "Société", "Section", "Site",
        "Victime", "Date accident", "Conséquence", "Créé le",
    ])
    for a in queryset.select_related("societe", "section", "site"):
        writer.writerow([
            a.reference, a.get_type_accident_display(), a.get_statut_display(),
            a.societe, a.section or "", a.site or "",
            a.victime_nom_prenom, a.date_accident,
            a.get_consequence_display(), a.created_at.date(),
        ])
    return response


export_csv.short_description = "Exporter la sélection en CSV"


class Analyse48hInline(admin.StackedInline):
    model = Analyse48h
    extra = 0
    readonly_fields = ("created_at", "updated_at")
    can_delete = False
    show_change_link = True
    verbose_name = "Analyse 48h"


class LAP8JoursInline(admin.StackedInline):
    model = LAP8Jours
    extra = 0
    readonly_fields = ("created_at", "updated_at")
    can_delete = False
    show_change_link = True
    verbose_name = "LAP 8 jours"


class ActionCorrectiveImmediateInline(admin.TabularInline):
    model = ActionCorrectiveImmédiate
    extra = 0
    fields = ("description", "pilote", "delai", "statut")
    readonly_fields = ()


@admin.register(AccidentTravail)
class AccidentTravailAdmin(admin.ModelAdmin):
    list_display = (
        "reference", "victime_nom_prenom", "date_accident", "societe",
        "type_accident", "statut_badge", "consequence", "echeance_48h",
        "echeance_8j",
    )
    list_filter = ("statut", "type_accident", "consequence", "societe", "date_accident")
    search_fields = ("reference", "victime_nom_prenom", "circonstances_detaillees")
    readonly_fields = ("reference", "created_at", "updated_at", "echeance_48h", "echeance_8j")
    date_hierarchy = "date_accident"
    inlines = [ActionCorrectiveImmediateInline, Analyse48hInline, LAP8JoursInline]
    actions = [export_csv]

    def get_actions(self, request):
        actions = super().get_actions(request)
        # Désactiver la suppression
        if "delete_selected" in actions:
            del actions["delete_selected"]
        return actions

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(description="Statut")
    def statut_badge(self, obj):
        colors = {
            "24h": "#ffc107",
            "48h": "#17a2b8",
            "8j": "#007bff",
            "cloture": "#28a745",
        }
        color = colors.get(obj.statut, "#6c757d")
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:4px">{}</span>',
            color,
            obj.get_statut_display(),
        )


@admin.register(Analyse48h)
class Analyse48hAdmin(admin.ModelAdmin):
    list_display = ("accident", "date_analyse", "valide_par", "created_at")
    readonly_fields = ("created_at", "updated_at")
    search_fields = ("accident__reference", "accident__victime_nom_prenom")
    has_delete_permission = lambda self, request, obj=None: False


@admin.register(LAP8Jours)
class LAP8JoursAdmin(admin.ModelAdmin):
    list_display = ("accident", "communication_alerte_securite", "mise_a_jour_duer", "created_at")
    readonly_fields = ("created_at", "updated_at")
    search_fields = ("accident__reference",)
    has_delete_permission = lambda self, request, obj=None: False


@admin.register(QuestionnaireTemplate)
class QuestionnaireTemplateAdmin(admin.ModelAdmin):
    list_display = ("code", "section", "question_court", "est_sous_question", "ordre")
    list_filter = ("section", "est_sous_question")
    ordering = ("ordre", "code")

    @admin.display(description="Question")
    def question_court(self, obj):
        return obj.question[:80]


@admin.register(ActionCorrective)
class ActionCorrectiveAdmin(admin.ModelAdmin):
    list_display = ("lap", "cause_racine_court", "pilote", "delai", "statut", "efficace")
    list_filter = ("statut", "efficace")

    @admin.display(description="Cause racine")
    def cause_racine_court(self, obj):
        return obj.cause_racine[:60]
