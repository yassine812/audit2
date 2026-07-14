"""Formulaires du module Gestion des Congés."""

from django import forms
from .models import DemandeConge


class DemandeCongeForm(forms.ModelForm):
    """Formulaire de demande de congé rempli par l'opérateur."""

    signature_demandeur = forms.CharField(
        widget=forms.HiddenInput(),
        required=True,
        error_messages={"required": "La signature électronique est obligatoire."},
    )

    class Meta:
        model = DemandeConge
        fields = [
            "nom", "prenom",
            "date_debut", "date_fin", "date_reprise", "nombre_jours",
            "type_conge", "evenement_familial_precision",
            "signature_demandeur",
        ]
        widgets = {
            "nom": forms.TextInput(attrs={
                "class": "form-control", "placeholder": "Nom de famille",
            }),
            "prenom": forms.TextInput(attrs={
                "class": "form-control", "placeholder": "Prénom",
            }),
            "date_debut": forms.DateInput(attrs={
                "class": "form-control", "type": "date",
            }),
            "date_fin": forms.DateInput(attrs={
                "class": "form-control", "type": "date",
            }),
            "date_reprise": forms.DateInput(attrs={
                "class": "form-control", "type": "date",
            }),
            "nombre_jours": forms.NumberInput(attrs={
                "class": "form-control", "min": "1",
            }),
            "type_conge": forms.RadioSelect(),
            "evenement_familial_precision": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Préciser l'imputation...",
            }),
        }

    def clean(self):
        cleaned_data = super().clean()
        date_debut   = cleaned_data.get("date_debut")
        date_fin     = cleaned_data.get("date_fin")
        date_reprise = cleaned_data.get("date_reprise")
        type_conge   = cleaned_data.get("type_conge")
        precision    = cleaned_data.get("evenement_familial_precision", "").strip()
        signature    = cleaned_data.get("signature_demandeur", "").strip()

        if date_debut and date_fin:
            if date_fin < date_debut:
                self.add_error("date_fin", "La date de fin doit être après la date de début.")

        if date_fin and date_reprise:
            if date_reprise <= date_fin:
                self.add_error("date_reprise", "La date de reprise doit être après la date de fin de congé.")

        if type_conge in {
            DemandeConge.TYPE_EVENEMENT_FAMILIAL,
            DemandeConge.TYPE_AUTRE,
        } and not precision:
            self.add_error(
                "evenement_familial_precision",
                "Veuillez préciser l'imputation.",
            )

        if not signature or not signature.startswith("data:image/"):
            self.add_error("signature_demandeur", "La signature électronique est invalide ou manquante.")

        return cleaned_data


class ValidationCongeForm(forms.Form):
    """Formulaire de validation ou refus par le RO/RS."""

    ACTION_VALIDER = "valider"
    ACTION_REFUSER = "refuser"

    action = forms.ChoiceField(
        choices=[
            (ACTION_VALIDER, "Valider"),
            (ACTION_REFUSER, "Refuser"),
        ],
        widget=forms.HiddenInput(),
    )
    signature_responsable = forms.CharField(
        widget=forms.HiddenInput(),
        required=False,
    )
    commentaire_refus = forms.CharField(
        widget=forms.Textarea(attrs={
            "class": "form-control",
            "rows": "4",
            "placeholder": "Motif du refus (obligatoire en cas de refus)…",
        }),
        required=False,
        label="Motif du refus",
    )

    def clean(self):
        cleaned_data = super().clean()
        action       = cleaned_data.get("action")
        signature    = cleaned_data.get("signature_responsable", "").strip()
        commentaire  = cleaned_data.get("commentaire_refus", "").strip()

        if action == self.ACTION_VALIDER:
            if not signature or not signature.startswith("data:image/"):
                raise forms.ValidationError(
                    "La signature électronique est obligatoire pour valider la demande."
                )

        if action == self.ACTION_REFUSER and not commentaire:
            raise forms.ValidationError("Le motif de refus est obligatoire.")

        return cleaned_data
