"""Configuration Django admin du module audit."""

from django.contrib import admin

from .models import (
    Audit,
    BaremeCotation,
    ChapitreNorme,
    CritereEvaluation,
    FormulaireAudit,
    LigneFormulaire,
    NormeDocument,
    ParticipantAudit,
    ReponseAudit,
    ResultatAudit,
    Theme,
    PreuveAttendueType,
)

from .models import PreuveAttendue, ReponseImage
from .models import NiveauxAttendus


class LigneFormulaireInline(admin.TabularInline):
    """Inline des lignes pour le formulaire d'audit."""

    model = LigneFormulaire
    extra = 1


@admin.register(FormulaireAudit)
class FormulaireAuditAdmin(admin.ModelAdmin):
    """Admin du formulaire audit."""
    list_display = ("titre", "section", "type_audit", "actif")
    list_filter = ("type_audit", "section")
    search_fields = ("titre",)
    inlines = [LigneFormulaireInline]


@admin.register(Audit)
class AuditAdmin(admin.ModelAdmin):
    """Admin des audits."""
    list_display = ("numero", "statut", "date_audit", "cree_par", "responsable_audit")
    list_filter = ("statut",)
    search_fields = ("numero",)
    readonly_fields = ("numero", "cree_le")


admin.site.register(NormeDocument)
admin.site.register(ChapitreNorme)
admin.site.register(Theme)
admin.site.register(CritereEvaluation)
admin.site.register(BaremeCotation)
admin.site.register(LigneFormulaire)
admin.site.register(ParticipantAudit)
admin.site.register(ReponseAudit)
admin.site.register(ResultatAudit)
admin.site.register(PreuveAttendue)
admin.site.register(PreuveAttendueType)
admin.site.register(ReponseImage)
admin.site.register(NiveauxAttendus)
