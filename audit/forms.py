"""Formulaires du module audit (Bootstrap/AdminLTE)."""

from django import forms
from django.core.exceptions import ValidationError
from django.forms.models import BaseInlineFormSet, inlineformset_factory

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
    NiveauxAttendus,
)


class BootstrapModelForm(forms.ModelForm):
    """Ajoute les classes CSS Bootstrap 4/AdminLTE à tous les champs."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            widget = field.widget
            label = field.label or field_name.replace("_", " ").capitalize()
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs.setdefault("class", "form-check-input")
            elif isinstance(widget, (forms.DateInput, forms.DateTimeInput)):
                widget.attrs["class"] = "form-control datepicker"
                widget.attrs.setdefault("type", "date")
                widget.attrs.setdefault("placeholder", label)
            elif isinstance(widget, forms.SelectMultiple):
                widget.attrs["class"] = "form-control"
                widget.attrs.setdefault("data-placeholder", label)
            elif isinstance(widget, forms.Select):
                widget.attrs["class"] = "form-control select2"
                widget.attrs.setdefault("data-placeholder", label)
            else:
                widget.attrs["class"] = "form-control"
                widget.attrs.setdefault("placeholder", label)
            widget.attrs.setdefault("id", f"id_{field_name}")


class NormeDocumentForm(BootstrapModelForm):
    class Meta:
        model = NormeDocument
        exclude = ("actif",)


class ChapitreNormeForm(BootstrapModelForm):
    class Meta:
        model = ChapitreNorme
        exclude = ("actif",)


class ThemeForm(BootstrapModelForm):
    class Meta:
        model = Theme
        exclude = ("actif",)


from django import forms as _forms


class CritereEvaluationForm(BootstrapModelForm):
    class Meta:
        model = CritereEvaluation
        exclude = ("actif",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'chapitre_norme' in self.fields:
            field = self.fields['chapitre_norme']
            field.queryset = ChapitreNorme.objects.select_related('norme').order_by('norme__nom', 'reference')
            def _chap_label(obj):
                parts = [f"{obj.reference} — {obj.intitule}"]
                if getattr(obj, 'norme', None) and obj.norme.nom:
                    suffix = f"({obj.norme.nom}"
                    if obj.num_page:
                        suffix += f" p.{obj.num_page}"
                    suffix += ")"
                    parts.append(suffix)
                return " ".join(parts)
            field.label_from_instance = _chap_label


class BaremeCotationForm(BootstrapModelForm):
    class Meta:
        model = BaremeCotation
        exclude = ("actif",)


class FormulaireAuditForm(BootstrapModelForm):
    """Formulaire de création/édition d'un formulaire d'audit."""

    class Meta:
        model = FormulaireAudit
        exclude = ("actif",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Ensure a proper empty choice is available for type_audit select
        if 'type_audit' in self.fields:
            field = self.fields['type_audit']
            original = [c for c in list(field.choices) if c[0] != '']
            field.choices = [('', '-- Choisir un type --')] + original
            field.widget.attrs.pop('data-placeholder', None)
        # Make section required and add select2
        if 'section' in self.fields:
            self.fields['section'].required = True
            self.fields['section'].widget.attrs.update({'class': 'form-control select2'})
            self.fields['section'].empty_label = "— Choisir une section —"


class LigneFormulaireForm(BootstrapModelForm):
    """Ligne de formulaire avec chapitres de norme multi-sélection."""

    class Meta:
        model = LigneFormulaire
        fields = "__all__"



class AuditForm(BootstrapModelForm):
    """Création/édition de l'audit."""

    class Meta:
        model = Audit
        fields = ["formulaire", "statut", "date_audit", "commentaire", "responsable_audit"]

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        # Restrict formulaires to user's section
        if user and hasattr(user, "section") and user.section:
            self.fields["formulaire"].queryset = (
                FormulaireAudit.objects.filter(section=user.section).select_related("section")
            )
        else:
            self.fields["formulaire"].queryset = FormulaireAudit.objects.select_related("section")
        # Hide statut on creation — set programmatically in the view
        if not self.instance.pk:
            self.fields["statut"].widget = forms.HiddenInput()
            self.fields["statut"].required = False
        # Responsable: show all users with a full name
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.fields["responsable_audit"].queryset = User.objects.filter(is_active=True).order_by("last_name", "first_name")
        self.fields["responsable_audit"].required = False
        self.fields["commentaire"].required = False
        # Date input
        self.fields["date_audit"].widget.attrs["type"] = "date"


class ParticipantAuditForm(BootstrapModelForm):
    class Meta:
        model = ParticipantAudit
        fields = ["user", "nom_externe", "fonction", "est_auditeur_externe"]

    def clean(self):
        cleaned_data = super().clean()
        has_user = bool(cleaned_data.get("user"))
        has_external = bool(cleaned_data.get("nom_externe", "").strip())
        if has_user == has_external:
            raise ValidationError("Renseignez soit un utilisateur interne, soit un nom externe.")
        return cleaned_data


class ReponseAuditForm(BootstrapModelForm):
    class Meta:
        model = ReponseAudit
        fields = ["audit", "ligne", "commentaire", "document"]

    def clean(self):
        cleaned_data = super().clean()
        audit = cleaned_data.get("audit")
        ligne = cleaned_data.get("ligne")
        if audit and ligne:
            qs = ReponseAudit.objects.filter(audit=audit, ligne=ligne)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError("Une réponse existe déjà pour cette ligne dans cet audit.")
        return cleaned_data


class ReponseAuditMassForm(BootstrapModelForm):
    """Formulaire allégé pour la saisie en masse."""

    class Meta:
        model = ReponseAudit
        fields = ["ligne", "commentaire", "document"]


class ReponseAuditBaseInlineFormSet(BaseInlineFormSet):
    """Formset inline de saisie de réponses d'un audit."""

    def clean(self):
        super().clean()
        seen = set()
        for form in self.forms:
            if not hasattr(form, "cleaned_data"):
                continue
            if form.cleaned_data.get("DELETE", False):
                continue
            ligne = form.cleaned_data.get("ligne")
            if not ligne:
                continue
            if ligne.pk in seen:
                raise ValidationError("Une ligne ne peut apparaître qu'une seule fois dans la saisie.")
            seen.add(ligne.pk)


ReponseAuditFormSet = inlineformset_factory(
    parent_model=Audit,
    model=ReponseAudit,
    form=ReponseAuditMassForm,
    formset=ReponseAuditBaseInlineFormSet,
    extra=0,
    can_delete=False,
)


class ResultatAuditForm(BootstrapModelForm):
    class Meta:
        model = ResultatAudit
        fields = ["points_forts", "risques", "opportunites", "points_sensibles", "niveau_attendu"]



class NiveauxAttendusForm(BootstrapModelForm):
    class Meta:
        model = NiveauxAttendus
        # exclude the model field `type_audit` because we provide a multi-select field
        exclude = ("actif", "type_audit")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # make HTML5 number input with min/max/step for better UX
        if "valeur" in self.fields:
            self.fields["valeur"].widget.attrs.update({
                "type": "number",
                "min": "0",
                "max": "100",
                "step": "0.01",
                "placeholder": "0.00 - 100.00",
            })

        # Provide a multiple-choice field to allow creating one instance per selected type
        from .models import AuditType
        self.fields['type_audit_multiple'] = forms.MultipleChoiceField(
            choices=AuditType.choices,
            required=False,
            widget=forms.SelectMultiple(attrs={
                'class': 'form-control select2',
                'data-placeholder': 'Sélectionnez un ou plusieurs types (ou laissez vide pour Tous)'
            }),
            help_text='Laisser vide crée un niveau pour tous les types.'
        )
        # initialize the multiple select with existing instance value when editing
        if not self.is_bound:
            inst = getattr(self, 'instance', None)
            if inst and getattr(inst, 'pk', None):
                if getattr(inst, 'type_audit', None):
                    self.fields['type_audit_multiple'].initial = [inst.type_audit]
                else:
                    self.fields['type_audit_multiple'].initial = []

    def clean_valeur(self):
        val = self.cleaned_data.get("valeur")
        if val is None:
            return val
        try:
            # Decimal comparisons safe; ensure within bounds
            if val < 0 or val > 100:
                raise ValidationError("La valeur doit être comprise entre 0 et 100.")
        except TypeError:
            raise ValidationError("Valeur invalide pour le pourcentage.")
        return val


class PreuveAttendueForm(BootstrapModelForm):
    class Meta:
        model = None
        # will be set dynamically below


class PreuveAttendueTypeForm(BootstrapModelForm):
    class Meta:
        model = None
        # set dynamically when imported in views to avoid circular import



