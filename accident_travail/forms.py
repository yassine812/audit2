"""Formulaires du module Accidents de Travail."""

from django import forms
from django.forms import inlineformset_factory

from .models import (
    AccidentTravail,
    ActionCorrectiveImmédiate,
    Analyse48h,
    CauseRacine,
    LAP8Jours,
    ActionCorrective,
    QuestionnaireItem,
    QuestionnaireTemplate,
)


class DateInput(forms.DateInput):
    input_type = "date"


class TimeInput(forms.TimeInput):
    input_type = "time"


# ─────────────────────────────────────────────────────────────────────────────
# Formulaire 24h
# ─────────────────────────────────────────────────────────────────────────────

ELEMENTS_MATERIELS_CHOICES = [
    ("circulation_plain_pied", "Circulation en plain-pied"),
    ("chute_denivellation", "Chute avec dénivellation"),
    ("objet", "Objet (en cours de manipulation, tombant, projeté)"),
    ("transport_manuel", "Appareils de transport manuel"),
    ("particules_corps_etrangers", "Particules, corps étrangers"),
    ("appareils_levage", "Appareils de levage"),
    ("elingues_chaines", "Élingues, chaînes, câbles"),
    ("organes_mouvement", "Organes en mouvement"),
    ("materiel_souder", "Matériel à souder"),
    ("outils_mecaniques_manuels", "Outils mécaniques manuels"),
    ("outil_main", "Outil à la main"),
    ("produits_chimiques", "Produits chimiques"),
    ("electricite", "Électricité"),
    ("manutention_manuelle", "Manutention manuelle de charge"),
    ("divers", "Divers"),
]

NATURE_LESIONS_CHOICES = [
    ("fractures", "Fractures"),
    ("douleurs", "Douleurs"),
    ("brulures_coup_arc", "Brûlures / Coup d'arc"),
    ("corps_etrangers", "Corps étrangers"),
    ("entorse_foulure", "Entorse / Foulure"),
    ("plaies_piqures_coupures", "Plaies / Piqûres / Coupures"),
    ("contusions_hematomes", "Contusions / Hématomes"),
    ("malaise", "Malaise"),
]

SIEGE_LESIONS_CHOICES = [
    ("tete", "Tête (hors yeux)"),
    ("yeux", "Yeux"),
    ("cou", "Cou"),
    ("dos_colonne", "Dos / Colonne vertébrale"),
    ("thorax_abdomen", "Thorax / Abdomen"),
    ("epaule", "Épaule"),
    ("bras_avant_bras", "Bras / Avant-bras"),
    ("main_doigts", "Main / Doigts"),
    ("hanche", "Hanche"),
    ("jambe_cuisse", "Jambe / Cuisse"),
    ("pied_orteil", "Pied / Orteil"),
    ("peau", "Peau (brûlure)"),
    ("multiple", "Multiple / Non précisé"),
]


class AccidentQuickCreateForm(forms.ModelForm):
    """Formulaire de création rapide (brouillon) — champs minimum obligatoires."""

    class Meta:
        model = AccidentTravail
        fields = ["type_accident", "societe", "victime_nom_prenom", "date_accident", "heure_accident"]
        widgets = {
            "date_accident": DateInput(attrs={"class": "form-control"}),
            "heure_accident": TimeInput(attrs={"class": "form-control"}),
            "type_accident": forms.Select(attrs={"class": "form-control"}),
            "societe": forms.Select(attrs={"class": "form-control"}),
            "victime_nom_prenom": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Prénom et nom de la victime",
            }),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        user_societe = (
            user.section.societe
            if user and hasattr(user, "section") and user.section and user.section.societe
            else None
        )
        if user_societe:
            self.fields["societe"].initial = user_societe
        # Non-superadmin: lock the société to their own
        if user and not user.is_superuser and user_societe:
            self.fields["societe"].disabled = True
        # Heure obligatoire dans le formulaire rapide
        self.fields["heure_accident"].required = True


class AccidentForm24h(forms.ModelForm):
    """Formulaire de déclaration initiale — étape 24h."""

    elements_materiels = forms.MultipleChoiceField(
        choices=ELEMENTS_MATERIELS_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Éléments matériels impliqués",
    )
    nature_lesions = forms.MultipleChoiceField(
        choices=NATURE_LESIONS_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Nature des lésions",
    )
    siege_lesions = forms.MultipleChoiceField(
        choices=SIEGE_LESIONS_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Siège des lésions",
    )

    class Meta:
        model = AccidentTravail
        fields = [
            # Type
            "type_accident",
            # Employeur
            "societe", "section", "site",
            # Victime
            "victime_nom_prenom",
            # Accident
            "date_accident", "heure_accident", "lieu_accident", "lieu_precisions",
            "lieu_type", "activite_victime", "nature_accident", "objet_contact",
            "reserves",
            # Éléments matériels & lésions
            "elements_materiels", "nature_lesions", "siege_lesions",
            "siege_lesions_schema", "siege_lesions_arrows_data",
            # EPI
            "epi_endommage", "epi_precisions",
            # Soins
            "premiers_soins", "premiers_soins_par", "premiers_soins_lesquels",
            "consultation_medecin", "consultation_medecin_info",
            "transport_hopital", "transport_hopital_nom",
            # Conséquences
            "consequence", "rapport_police", "rapport_police_par",
            "registre_benins_date", "registre_benins_numero", "autres_victimes",
            # Horaires
            "horaire_debut1", "horaire_fin1", "horaire_debut2", "horaire_fin2",
            # Constatation
            "accident_constate_le", "accident_constate_heure",
            "accident_constate_par", "accident_connu_le",
            # Tiers
            "tiers_implique", "tiers_nom_adresse", "tiers_assurance",
            # Témoin
            "temoin_ou_premiere_personne", "temoin_nom_prenom", "temoin_adresse",
            # QR HSE
            "qr_hse",
            # Circonstances
            "circonstances_detaillees",
        ]
        widgets = {
            # "victime_date_naissance": DateInput,  # Supprimé
            "victime_date_embauche": DateInput,
            "date_accident": DateInput,
            "heure_accident": TimeInput,
            "horaire_debut1": TimeInput,
            "horaire_fin1": TimeInput,
            "horaire_debut2": TimeInput,
            "horaire_fin2": TimeInput,
            "accident_constate_le": DateInput,
            "accident_constate_heure": TimeInput,
            "accident_connu_le": DateInput,
            "registre_benins_date": DateInput,
            "type_accident": forms.RadioSelect,
            "epi_endommage": forms.RadioSelect(
                choices=[(True, "Oui"), (False, "Non")],
            ),
            "premiers_soins": forms.RadioSelect(
                choices=[(True, "Oui"), (False, "Non")],
            ),
            "consultation_medecin": forms.RadioSelect(
                choices=[(True, "Oui"), (False, "Non")],
            ),
            "transport_hopital": forms.RadioSelect(
                choices=[(True, "Oui"), (False, "Non")],
            ),
            "rapport_police": forms.RadioSelect(
                choices=[(True, "Oui"), (False, "Non")],
            ),
            "autres_victimes": forms.RadioSelect(
                choices=[(True, "Oui"), (False, "Non")],
            ),
            "tiers_implique": forms.RadioSelect(
                choices=[(True, "Oui"), (False, "Non")],
            ),
            "circonstances_detaillees": forms.Textarea(attrs={"rows": 5}),
            "siege_lesions_schema": forms.HiddenInput(),
            "siege_lesions_arrows_data": forms.HiddenInput(),
            "lieu_precisions": forms.Textarea(attrs={"rows": 2}),
            "activite_victime": forms.Textarea(attrs={"rows": 2}),
            "nature_accident": forms.Textarea(attrs={"rows": 2}),
            "objet_contact": forms.Textarea(attrs={"rows": 2}),
            "temoin_adresse": forms.Textarea(attrs={"rows": 2}),
            "tiers_nom_adresse": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        # Ajouter des classes Bootstrap à tous les champs
        for field_name, field in self.fields.items():
            if isinstance(field.widget, (forms.CheckboxSelectMultiple, forms.RadioSelect)):
                continue
            field.widget.attrs.setdefault("class", "form-control")

        # Filtrer les sections/sites si user connu
        if user and not (user.is_superuser or user.is_CE):
            if user.section and user.section.societe:
                from accounts.models import Section, Site
                self.fields["section"].queryset = Section.objects.filter(
                    societe=user.section.societe
                )
                self.fields["site"].queryset = Site.objects.filter(
                    section__societe=user.section.societe
                )

        # Pré-remplir les JSONField avec les valeurs actuelles
        if self.instance and self.instance.pk:
            self.fields["elements_materiels"].initial = self.instance.elements_materiels
            self.fields["nature_lesions"].initial = self.instance.nature_lesions
            sl = self.instance.siege_lesions
            # Support both list and dict representations
            if isinstance(sl, dict):
                self.fields["siege_lesions"].initial = [k for k, v in sl.items() if v]
            else:
                self.fields["siege_lesions"].initial = sl

        # Placeholders
        _ph = {
            "victime_nom_prenom": "Prénom et nom complet de la victime",
            "lieu_accident": "Localisation précise de l'accident",
            "lieu_precisions": "Précisions sur le lieu...",
            "activite_victime": "Décrivez l'activité en cours au moment de l'accident...",
            "nature_accident": "Comment l'accident s'est-il produit ?",
            "objet_contact": "Objet, substance ou équipement impliqué",
            "reserves": "Réserves éventuelles...",
            "epi_precisions": "Type et état de l'EPI",
            "premiers_soins_par": "Nom du secouriste ou infirmier",
            "premiers_soins_lesquels": "Nature des soins prodigués",
            "consultation_medecin_info": "Médecin, clinique ou hôpital",
            "transport_hopital_nom": "Nom de l'hôpital",
            "rapport_police_par": "Commissariat ou gendarmerie",
            "tiers_nom_adresse": "Nom, prénom et adresse du tiers",
            "tiers_assurance": "Compagnie d'assurance du tiers",
            "temoin_nom_prenom": "Prénom et nom du témoin",
            "temoin_adresse": "Adresse du témoin",
            "qr_hse": "Référence QR HSE",
            "circonstances_detaillees": "Décrivez en détail les circonstances de l'accident...",
        }
        for fname, ph in _ph.items():
            if fname in self.fields and hasattr(self.fields[fname].widget, "attrs"):
                self.fields[fname].widget.attrs.setdefault("placeholder", ph)

    def clean_elements_materiels(self):
        return self.cleaned_data.get("elements_materiels", [])

    def clean_nature_lesions(self):
        return self.cleaned_data.get("nature_lesions", [])

    def clean_siege_lesions(self):
        return self.cleaned_data.get("siege_lesions", [])

    def clean_siege_lesions_arrows_data(self):
        """Convertir la chaîne JSON en liste Python."""
        import json
        data = self.cleaned_data.get("siege_lesions_arrows_data", "")
        if isinstance(data, str):
            try:
                return json.loads(data) if data else []
            except json.JSONDecodeError:
                return []
        return data if data else []


# ─────────────────────────────────────────────────────────────────────────────
# Formset pour les actions correctives immédiates
# ─────────────────────────────────────────────────────────────────────────────

class ActionCorrectiveImmediateForm(forms.ModelForm):
    class Meta:
        model = ActionCorrectiveImmédiate
        fields = ["description", "pilote"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 2, "class": "form-control", "placeholder": "Décrivez l’action corrective immédiate..."}),
            "pilote": forms.TextInput(attrs={"class": "form-control", "placeholder": "Responsable de l’action"}),
        }


ActionCorrectiveImmediateFormSet = inlineformset_factory(
    AccidentTravail,
    ActionCorrectiveImmédiate,
    form=ActionCorrectiveImmediateForm,
    extra=1,
    can_delete=True,
)


# ─────────────────────────────────────────────────────────────────────────────
# Formulaire 48h
# ─────────────────────────────────────────────────────────────────────────────

class Analyse48hForm(forms.ModelForm):
    class Meta:
        model = Analyse48h
        fields = [
            # Participants
            "participants_exploitation", "participants_cssct", "participants_rh",
            "participants_qse", "participants_direction", "participants_finance",
            "participants_achat", "participants_commercial", "participants_autre",
            "participants_client",
            # Victime
            "victime_age", "victime_sexe", "victime_date_visite_medicale", 
            "victime_restriction_aptitude", "victime_restriction_precisions", 
            "victime_poste_conforme", "victime_poste_occupe", "victime_anciennete_poste_analyse",
            # Horaires
            "horaire_travail",
            # Milieu
            "emplacement_interieur_exterieur", "poste_travail_habituel",
            "emplacement_connu_victime", "lieu_depart", "lieu_arrivee",
            "motif_deplacement", "nuisances_precisions",
            # Description
            "description_activite",
            # Validation
            "date_analyse", "valide_par",
        ]
        widgets = {
            "victime_age": forms.NumberInput(attrs={"class": "form-control", "min": "1", "max": "100"}),
            "victime_sexe": forms.Select(attrs={"class": "form-control"}),
            "victime_date_visite_medicale": DateInput,
            "victime_poste_occupe": forms.TextInput(attrs={"class": "form-control"}),
            "victime_anciennete_poste_analyse": forms.TextInput(attrs={"class": "form-control"}),
            "horaire_travail": forms.TextInput(attrs={"class": "form-control"}),
            "date_analyse": DateInput,
            "participants_exploitation": forms.TextInput,
            "participants_cssct": forms.TextInput,
            "participants_rh": forms.TextInput,
            "participants_qse": forms.TextInput,
            "participants_direction": forms.TextInput,
            "participants_finance": forms.TextInput,
            "participants_achat": forms.TextInput,
            "participants_commercial": forms.TextInput,
            "participants_autre": forms.TextInput,
            "participants_client": forms.TextInput,
            "victime_restriction_aptitude": forms.RadioSelect(
                choices=[(True, "Oui"), (False, "Non")],
            ),
            "victime_poste_conforme": forms.RadioSelect(
                choices=[(True, "Oui"), (False, "Non")],
            ),
            "poste_travail_habituel": forms.RadioSelect(
                choices=[(True, "Oui"), (False, "Non")],
            ),
            "emplacement_connu_victime": forms.RadioSelect(
                choices=[(True, "Oui"), (False, "Non")],
            ),
            "description_activite": forms.Textarea(attrs={"rows": 5, "class": "form-control"}),
            "victime_restriction_precisions": forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
            "nuisances_precisions": forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.RadioSelect):
                continue
            field.widget.attrs.setdefault("class", "form-control")
        _ph = {
            "participants_exploitation": "Noms et prénoms des participants",
            "participants_cssct": "Noms et prénoms des participants",
            "participants_rh": "Noms et prénoms des participants",
            "participants_qse": "Noms et prénoms des participants",
            "participants_direction": "Noms et prénoms des participants",
            "participants_finance": "Noms et prénoms des participants",
            "participants_achat": "Noms et prénoms des participants",
            "participants_commercial": "Noms et prénoms des participants",
            "participants_autre": "Noms et prénoms des participants",
            "participants_client": "Noms et prénoms des participants",
            "victime_poste_occupe": "Intitulé du poste occupé",
            "victime_age": "ex: 35",
            "victime_anciennete_poste_analyse": "ex: 6 mois, 2 ans",
            "victime_restriction_precisions": "Décrivez les restrictions d’aptitude...",            "horaire_travail": "ex: 08:00-12:00, 14:00-18:00",            "lieu_depart": "Lieu de départ",
            "lieu_arrivee": "Lieu d’arrivée",
            "motif_deplacement": "Motif du déplacement professionnel",
            "nuisances_precisions": "Précisez les nuisances identifiées...",
            "description_activite": "Décrivez en détail l’activité au moment de l’accident...",
            "valide_par": "Nom et qualité du validateur",
        }
        for fname, ph in _ph.items():
            if fname in self.fields and hasattr(self.fields[fname].widget, "attrs"):
                self.fields[fname].widget.attrs.setdefault("placeholder", ph)


class QuestionnaireItemForm(forms.ModelForm):
    class Meta:
        model = QuestionnaireItem
        fields = ["reponse", "precisions"]
        widgets = {
            "precisions": forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
        }


# ─────────────────────────────────────────────────────────────────────────────
# Formulaire LAP 8 jours
# ─────────────────────────────────────────────────────────────────────────────

class LAP8JForm(forms.ModelForm):
    class Meta:
        model = LAP8Jours
        fields = [
            "participants_exploitation", "participants_cssct", "participants_rh",
            "participants_qse", "participants_direction", "participants_finance",
            "participants_achat", "participants_commercial", "participants_autre",
            "participants_client",
            "communication_alerte_securite", "communication_date",
            "mise_a_jour_duer", "duer_date",
            "transversalisation_groupe",
            "transversalisation_valide_par",
        ]
        widgets = {
            "communication_date": DateInput,
            "duer_date": DateInput,
            "participants_exploitation": forms.TextInput,
            "participants_cssct": forms.TextInput,
            "participants_rh": forms.TextInput,
            "participants_qse": forms.TextInput,
            "participants_direction": forms.TextInput,
            "participants_finance": forms.TextInput,
            "participants_achat": forms.TextInput,
            "participants_commercial": forms.TextInput,
            "participants_autre": forms.TextInput,
            "participants_client": forms.TextInput,
            "communication_alerte_securite": forms.RadioSelect(
                choices=[(True, "Oui"), (False, "Non")],
            ),
            "mise_a_jour_duer": forms.RadioSelect(
                choices=[(True, "Oui"), (False, "Non")],
            ),
            "transversalisation_groupe": forms.RadioSelect(
                choices=[(True, "Oui"), (False, "Non")],
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.RadioSelect):
                continue
            field.widget.attrs.setdefault("class", "form-control")
        _ph = {
            "participants_exploitation": "Noms et prénoms des participants",
            "participants_cssct": "Noms et prénoms des participants",
            "participants_rh": "Noms et prénoms des participants",
            "participants_qse": "Noms et prénoms des participants",
            "participants_direction": "Noms et prénoms des participants",
            "participants_finance": "Noms et prénoms des participants",
            "participants_achat": "Noms et prénoms des participants",
            "participants_commercial": "Noms et prénoms des participants",
            "participants_autre": "Noms et prénoms des participants",
            "participants_client": "Noms et prénoms des participants",
            "transversalisation_valide_par": "Nom et qualité du validateur",
        }
        for fname, ph in _ph.items():
            if fname in self.fields and hasattr(self.fields[fname].widget, "attrs"):
                self.fields[fname].widget.attrs.setdefault("placeholder", ph)


class ActionCorrectiveForm(forms.ModelForm):
    class Meta:
        model = ActionCorrective
        fields = [
            "cause_racine", "description", "pilote", "delai",
            "date_realisation", "date_verification", "efficace",
        ]
        widgets = {
            "cause_racine": forms.Textarea(attrs={"rows": 2, "class": "form-control", "placeholder": "Cause racine identifiée..."}),
            "description": forms.Textarea(attrs={"rows": 2, "class": "form-control", "placeholder": "Description de l’action corrective..."}),
            "pilote": forms.TextInput(attrs={"class": "form-control", "placeholder": "Responsable de l’action"}),
            "delai": DateInput(attrs={"class": "form-control"}),
            "date_realisation": DateInput(attrs={"class": "form-control"}),
            "date_verification": DateInput(attrs={"class": "form-control"}),
            "efficace": forms.RadioSelect(choices=[(True, "Oui"), (False, "Non")]),
        }


ActionCorrectiveFormSet = inlineformset_factory(
    LAP8Jours,
    ActionCorrective,
    form=ActionCorrectiveForm,
    extra=1,
    can_delete=True,
)


# ─────────────────────────────────────────────────────────────────────────────
# CRUD Questionnaire Template (questions & sous-questions 48h)
# ─────────────────────────────────────────────────────────────────────────────

CONDITION_CHOICES = [
    ("", "— Aucune —"),
    ("O", "Si parent = Oui"),
    ("N", "Si parent = Non"),
]

SECTION_SUGGESTIONS = [
    "1. Engagement de la direction et organisation du travail",
    "2. Évaluation des risques",
    "3. Formation / Information / Instruction / Compétences",
    "4. Intervention d'entreprises extérieures",
    "5. Conditions de travail",
]


class QuestionnaireTemplateForm(forms.ModelForm):
    """Formulaire de création/modification d'une question (ou sous-question) du questionnaire 48h."""

    parent = forms.ModelChoiceField(
        queryset=QuestionnaireTemplate.objects.filter(est_sous_question=False).order_by("ordre", "code"),
        required=False,
        label="Question parente",
        empty_label="— Aucune (question principale) —",
        widget=forms.Select(attrs={"class": "form-control select2", "id": "id_parent"}),
        help_text="Sélectionner une question parente transforme cette entrée en sous-question.",
    )
    condition_affichage = forms.ChoiceField(
        choices=CONDITION_CHOICES,
        required=False,
        label="Condition d'affichage",
        widget=forms.Select(attrs={"class": "form-control"}),
        help_text="Afficher cette sous-question uniquement si la réponse du parent vaut cette valeur.",
    )

    class Meta:
        model = QuestionnaireTemplate
        fields = ["code", "section", "question", "ordre"]
        widgets = {
            "code": forms.TextInput(attrs={"class": "form-control", "placeholder": "ex: 1.4b"}),
            "section": forms.TextInput(attrs={
                "class": "form-control",
                "list": "section-suggestions",
                "placeholder": "ex: 1. Engagement de la direction…",
            }),
            "question": forms.Textarea(attrs={"class": "form-control", "rows": 3,
                                               "placeholder": "Texte de la question…"}),
            "ordre": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Pre-fill parent field from instance.parent_code
        if self.instance and self.instance.pk and self.instance.parent_code:
            try:
                self.fields["parent"].initial = QuestionnaireTemplate.objects.get(
                    code=self.instance.parent_code
                )
            except QuestionnaireTemplate.DoesNotExist:
                pass
        # Pre-fill condition from instance
        if self.instance and self.instance.pk:
            self.fields["condition_affichage"].initial = self.instance.condition_affichage
        # Exclude self from parent choices on update
        if self.instance and self.instance.pk:
            self.fields["parent"].queryset = QuestionnaireTemplate.objects.filter(
                est_sous_question=False
            ).exclude(pk=self.instance.pk).order_by("ordre", "code")

    def save(self, commit=True):
        instance = super().save(commit=False)
        parent = self.cleaned_data.get("parent")
        if parent:
            instance.parent_code = parent.code
            instance.est_sous_question = True
        else:
            instance.parent_code = ""
            instance.est_sous_question = False
        instance.condition_affichage = self.cleaned_data.get("condition_affichage", "")
        if commit:
            instance.save()
        return instance


# ─────────────────────────────────────────────────────────────────────────────
# Causes racines (formulaire 48h — méthode 5 Pourquoi)
# ─────────────────────────────────────────────────────────────────────────────

class CauseRacineForm(forms.ModelForm):
    class Meta:
        model = CauseRacine
        fields = ["texte"]
        widgets = {
            "texte": forms.TextInput(attrs={
                "class": "form-control form-control-sm cause-autocomplete",
                "placeholder": "Saisir ou rechercher une cause…",
                "autocomplete": "off",
            }),
        }


CauseRacineFormSet = inlineformset_factory(
    Analyse48h,
    CauseRacine,
    form=CauseRacineForm,
    extra=0,
    can_delete=True,
    min_num=0,
    max_num=5,
    validate_max=True,
)
