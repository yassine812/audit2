"""Formulaires et formset dynamique du module Plan de Prévention (PDP)."""

from django import forms
from django.forms import inlineformset_factory

from accounts.models import Customer, Section, Site, Societe
from .models import PlanPrevention, PlanPreventionRisque, RisquePDP


class PlanPreventionForm(forms.ModelForm):
    """Formulaire principal de saisie/édition d'un PDP."""

    class Meta:
        model = PlanPrevention
        fields = [
            # Organisation / Scope
            "societe",
            "section",
            "site",
            "customer",
            # Opération
            "type_operation",
            "nature_operation",
            # Entreprise Utilisatrice (E.U.)
            "eu_nom",
            "eu_adresse",
            "eu_telephone",
            "eu_representant_nom",
            "eu_representant_fonction",
            "eu_representant_telephone",
            # Entreprise Extérieure (E.E.)
            "ee_nom",
            "ee_adresse",
            "ee_telephone",
            "ee_representant_nom",
            "ee_representant_fonction",
            "ee_representant_telephone",
            # Intervention
            "lieu_intervention",
            "date_debut",
            "date_fin",
            "horaire_travail",
            "effectif_prevu",
            "duree_approximative",
            "sous_traitants",
            # Visite préalable & consignes
            "date_visite_prealable",
            "secteur_intervention",
            "itineraire",
            "zone_danger_particulier",
            "locaux_mis_disposition",
            "appareils_mis_disposition",
            # Secours
            "numeros_urgence",
            "infirmerie_trousse_sst_location",
            "consigne_evacuation",
            # SIR
            "suivi_medical_renforce",
            "postes_concernes",
            # Remarques & Signatures
            "remarques_cssct",
            "date_signature_eu",
            "signature_eu_nom",
            "signature_eu_image",
            "date_signature_ee",
            "signature_ee_nom",
            "signature_ee_image",
            # Statut
            "statut",
        ]
        widgets = {
            "societe": forms.Select(attrs={"class": "form-control custom-select"}),
            "section": forms.Select(attrs={"class": "form-control custom-select"}),
            "site": forms.Select(attrs={"class": "form-control custom-select"}),
            "customer": forms.Select(attrs={"class": "form-control custom-select", "id": "id_customer_select"}),
            "type_operation": forms.RadioSelect(attrs={"class": "form-check-input"}),
            "nature_operation": forms.TextInput(attrs={"class": "form-control"}),
            "eu_nom": forms.TextInput(attrs={"class": "form-control"}),
            "eu_adresse": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "eu_telephone": forms.TextInput(attrs={"class": "form-control"}),
            "eu_representant_nom": forms.TextInput(attrs={"class": "form-control"}),
            "eu_representant_fonction": forms.TextInput(attrs={"class": "form-control"}),
            "eu_representant_telephone": forms.TextInput(attrs={"class": "form-control"}),
            "ee_nom": forms.TextInput(attrs={"class": "form-control"}),
            "ee_adresse": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "ee_telephone": forms.TextInput(attrs={"class": "form-control"}),
            "ee_representant_nom": forms.TextInput(attrs={"class": "form-control"}),
            "ee_representant_fonction": forms.TextInput(attrs={"class": "form-control"}),
            "ee_representant_telephone": forms.TextInput(attrs={"class": "form-control"}),
            "lieu_intervention": forms.TextInput(attrs={"class": "form-control"}),
            "date_debut": forms.DateInput(format="%Y-%m-%d", attrs={"class": "form-control", "type": "date"}),
            "date_fin": forms.DateInput(format="%Y-%m-%d", attrs={"class": "form-control", "type": "date"}),
            "horaire_travail": forms.TimeInput(attrs={"class": "form-control", "type": "time"}),
            "effectif_prevu": forms.TextInput(attrs={"class": "form-control"}),
            "duree_approximative": forms.TextInput(attrs={"class": "form-control"}),
            "sous_traitants": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "date_visite_prealable": forms.DateInput(format="%Y-%m-%d", attrs={"class": "form-control", "type": "date"}),
            "secteur_intervention": forms.TextInput(attrs={"class": "form-control"}),
            "itineraire": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "zone_danger_particulier": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "locaux_mis_disposition": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "appareils_mis_disposition": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "numeros_urgence": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "infirmerie_trousse_sst_location": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "consigne_evacuation": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "suivi_medical_renforce": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "postes_concernes": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "remarques_cssct": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "date_signature_eu": forms.DateInput(format="%Y-%m-%d", attrs={"class": "form-control", "type": "date"}),
            "signature_eu_nom": forms.TextInput(attrs={"class": "form-control"}),
            "signature_eu_image": forms.HiddenInput(attrs={"id": "id_signature_eu_image"}),
            "date_signature_ee": forms.DateInput(format="%Y-%m-%d", attrs={"class": "form-control", "type": "date"}),
            "signature_ee_nom": forms.TextInput(attrs={"class": "form-control"}),
            "signature_ee_image": forms.HiddenInput(attrs={"id": "id_signature_ee_image"}),
            "statut": forms.Select(attrs={"class": "form-control custom-select"}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        if user and not user.is_superuser:
            # Filtrer les sociétés accessibles
            if hasattr(user, "societe") and user.societe:
                self.fields["societe"].queryset = Societe.objects.filter(pk=user.societe.pk)
                self.fields["societe"].initial = user.societe
            # Filtrer les sections et sites selon la société
            if hasattr(user, "section") and user.section:
                self.fields["section"].queryset = Section.objects.filter(societe=user.section.societe)
                if user.section.societe:
                    self.fields["site"].queryset = Site.objects.filter(section__societe=user.section.societe)


class RisquePDPForm(forms.ModelForm):
    """Formulaire de création / édition d'un Risque PDP (sans champ Processus)."""

    class Meta:
        model = RisquePDP
        fields = [
            "code",
            "titre",
            "description",
            "categorie",
            "mesures_prevention_recommandees",
            "ordre",
            "est_actif",
        ]
        widgets = {
            "code": forms.TextInput(attrs={"class": "form-control", "placeholder": "ex: circulation_pieton, hauteur..."}),
            "titre": forms.TextInput(attrs={"class": "form-control", "placeholder": "Titre / Libellé du risque"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Description du risque et des dangers associés"}),
            "categorie": forms.TextInput(attrs={"class": "form-control", "placeholder": "ex: Circulation, Manutention, Électrique..."}),
            "mesures_prevention_recommandees": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Mesures de prévention recommandées..."}),
            "ordre": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "est_actif": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


# Alias conservé temporairement pour éviter toute régression sur d'anciens imports
RisqueForm = RisquePDPForm


class PlanPreventionRisqueForm(forms.ModelForm):
    """Formulaire individuel pour une ligne d'association risque PDP."""

    class Meta:
        model = PlanPreventionRisque
        fields = [
            "risque",
            "concerne_eu",
            "concerne_ee",
            "mesures_prevention",
            "mise_en_oeuvre_eu",
            "mise_en_oeuvre_ee",
            "ordre",
        ]
        widgets = {
            "risque": forms.Select(attrs={"class": "form-control form-control-sm custom-select risk-select"}),
            "concerne_eu": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "concerne_ee": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "mesures_prevention": forms.Textarea(attrs={"class": "form-control form-control-sm", "rows": 2}),
            "mise_en_oeuvre_eu": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "mise_en_oeuvre_ee": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "ordre": forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "risque" in self.fields:
            self.fields["risque"].queryset = RisquePDP.objects.filter(est_actif=True).order_by("ordre", "code")


PlanPreventionRisqueFormSet = inlineformset_factory(
    PlanPrevention,
    PlanPreventionRisque,
    form=PlanPreventionRisqueForm,
    fk_name="pdp",
    extra=0,
    can_delete=True,
)

