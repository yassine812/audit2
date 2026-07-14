"""Formulaires du module Achats."""

from django import forms
from django.contrib.auth import get_user_model
from django.forms import inlineformset_factory

from accounts.models import Section

from .models import (
    ArticleCatalogue,
    ConfigurationValidationSection,
    Devis,
    DemandeAchat,
    Dysfonctionnement,
    EtapeValidation,
    EvaluationFournisseur,
    Fournisseur,
    LigneDemandeAchat,
    OffreFournisseur,
    ReceptionMarchandise,
)


def _apply_accessibility_attrs(fields):
    """Ajoute des attributs d'accessibilité cohérents aux champs obligatoires."""
    for field in fields.values():
        if field.required:
            field.widget.attrs["aria-required"] = "true"


class ArticleCatalogueSelect(forms.Select):
    """Widget select enrichi avec métadonnées pour le JS de prévisualisation."""

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex=subindex, attrs=attrs)
        if value:
            catalogue_map = getattr(self, "catalogue_map", None)
            queryset = getattr(self, "catalogue_queryset", None)
            raw_value = getattr(value, "value", value)
            try:
                article = None
                if catalogue_map is not None:
                    article = catalogue_map.get(str(raw_value)) or catalogue_map.get(raw_value)
                if article is None:
                    if queryset is None:
                        return option
                    article = queryset.get(pk=raw_value)
            except (AttributeError, ArticleCatalogue.DoesNotExist, TypeError, ValueError):
                return option

            option["attrs"]["data-reference"] = article.reference
            option["attrs"]["data-description"] = article.description or ""
            option["attrs"]["data-photo"] = article.photo.url if article.photo else ""
            option["attrs"]["data-stock"] = article.stock_disponible
            option["attrs"]["data-price"] = article.prix_reference_ht if article.prix_reference_ht is not None else ""
        return option


class FournisseurSelect(forms.Select):
    """Widget select enrichi avec la référence fournisseur pour l'auto-remplissage JS."""

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex=subindex, attrs=attrs)
        if value:
            fournisseur_map = getattr(self, "fournisseur_map", None)
            queryset = getattr(self, "fournisseur_queryset", None)
            raw_value = getattr(value, "value", value)
            try:
                fournisseur = None
                if fournisseur_map is not None:
                    fournisseur = fournisseur_map.get(str(raw_value)) or fournisseur_map.get(raw_value)
                if fournisseur is None:
                    if queryset is None:
                        return option
                    fournisseur = queryset.get(pk=raw_value)
            except (AttributeError, Fournisseur.DoesNotExist, TypeError, ValueError):
                return option

            option["attrs"]["data-reference-fournisseur"] = fournisseur.reference_fournisseur or ""
        return option


class FournisseurForm(forms.ModelForm):
    """Formulaire de création et modification d'un fournisseur."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _apply_accessibility_attrs(self.fields)
        placeholder_map = {
            "nom": "Nom du fournisseur",
            "adresse": "Adresse complète",
            "reference_fournisseur": "Référence standard chez ce fournisseur",
            "contact_nom": "Nom du contact",
            "contact_mail": "exemple@entreprise.com",
            "contact_tel": "Téléphone du contact",
        }
        for field_name, placeholder in placeholder_map.items():
            self.fields[field_name].widget.attrs.update({"placeholder": placeholder})

        self.fields["nom"].label = "Raison sociale"
        self.fields["adresse"].label = "Adresse complète"
        self.fields["reference_fournisseur"].label = "Réf. fournisseur"
        self.fields["contact_nom"].label = "Nom du contact principal"
        self.fields["contact_mail"].label = "E-mail du contact"
        self.fields["contact_tel"].label = "Téléphone du contact"
        self.fields["nom"].help_text = "Nom affiché dans les demandes, devis et évaluations fournisseurs."
        self.fields["adresse"].help_text = "Adresse utilisée comme référence pour les commandes et échanges."
        self.fields["reference_fournisseur"].help_text = "Code ou référence standard communiqué par ce fournisseur et repris automatiquement dans les demandes d'achat."
        self.fields["contact_nom"].help_text = "Personne à contacter en priorité pour ce fournisseur."

        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")

    class Meta:
        model = Fournisseur
        fields = [
            "nom",
            "adresse",
            "reference_fournisseur",
            "contact_nom",
            "contact_mail",
            "contact_tel",
        ]

class ArticleCatalogueForm(forms.ModelForm):
    """Formulaire de création et modification d'un article du catalogue."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _apply_accessibility_attrs(self.fields)
        placeholder_map = {
            "reference": "Référence interne",
            "designation": "Désignation de l'article",
            "description": "Décrivez l'article, ses caractéristiques et usages",
            "stock_disponible": "Quantité actuellement disponible",
            "prix_reference_ht": "Prix habituel ou constaté en HT",
        }
        for field_name, placeholder in placeholder_map.items():
            self.fields[field_name].widget.attrs.update({"placeholder": placeholder})

        self.fields["reference"].label = "Référence interne"
        self.fields["designation"].label = "Désignation"
        self.fields["description"].label = "Description détaillée"
        self.fields["stock_disponible"].label = "Stock disponible"
        self.fields["prix_reference_ht"].label = "Prix de référence HT"
        self.fields["type_article"].label = "Type d'article"
        self.fields["categorie"].label = "Catégorie achat"
        self.fields["photo"].label = "Photo ou visuel"
        self.fields["reference"].help_text = "Code interne unique utilisé pour rechercher rapidement l'article."
        self.fields["designation"].help_text = "Nom court et explicite visible dans les demandes d'achat."
        self.fields["description"].help_text = "Précisez les caractéristiques utiles à l'achat et à l'utilisation."
        self.fields["stock_disponible"].help_text = "Valeur proposée automatiquement dans les demandes d'achat catalogue."
        self.fields["prix_reference_ht"].help_text = "Valeur proposée automatiquement comme PU HT dans les demandes catalogue."
        self.fields["photo"].help_text = "Facultatif, mais utile pour identifier visuellement l'article."

        for field_name, field in self.fields.items():
            if field_name == "photo":
                field.widget.attrs["class"] = "form-control-file"
            elif isinstance(field.widget, forms.Textarea):
                field.widget.attrs.update({"class": "form-control", "rows": 4})
            else:
                field.widget.attrs.setdefault("class", "form-control")

    class Meta:
        model = ArticleCatalogue
        fields = [
            "reference",
            "designation",
            "description",
            "stock_disponible",
            "prix_reference_ht",
            "photo",
            "type_article",
            "categorie",
        ]


class OffreFournisseurForm(forms.ModelForm):
    """Formulaire d'une offre fournisseur liée à un article."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _apply_accessibility_attrs(self.fields)
        self.fields["fournisseur"].widget.attrs.update({"placeholder": "Sélectionner un fournisseur"})
        self.fields["tarif_propose"].widget.attrs.update({"placeholder": "0.00"})
        self.fields["reference_chez_fournisseur"].widget.attrs.update({"placeholder": "Référence chez le fournisseur"})
        self.fields["fournisseur"].label_from_instance = lambda fournisseur: fournisseur.nom
        self.fields["tarif_propose"].label = "Tarif HT proposé"
        self.fields["reference_chez_fournisseur"].label = "Référence fournisseur"
        self.fields["tarif_propose"].help_text = "Dernier tarif connu pour cet article."

        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")

    class Meta:
        model = OffreFournisseur
        fields = [
            "fournisseur",
            "tarif_propose",
            "reference_chez_fournisseur",
        ]


class DemandeAchatForm(forms.ModelForm):
    """Formulaire principal de demande d'achat."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _apply_accessibility_attrs(self.fields)
        self.fields["delai_souhaite"].widget = forms.DateInput(
            attrs={"class": "form-control", "type": "date"}
        )
        self.fields["adresse_livraison"].widget.attrs.update(
            {"class": "form-control", "placeholder": "Adresse ou site de livraison"}
        )
        self.fields["section_analytique"].widget.attrs.setdefault("class", "form-control")
        self.fields["categorie"].widget.attrs.setdefault("class", "form-control")
        self.fields["est_demande_de_prix"].widget.attrs["class"] = "form-check-input"
        self.fields["section_analytique"].queryset = Section.objects.order_by("Nom")
        self.fields["section_analytique"].label_from_instance = lambda section: section.Nom
        self.fields["delai_souhaite"].label = "Date souhaitée de besoin"
        self.fields["adresse_livraison"].label = "Lieu ou adresse de livraison"
        self.fields["section_analytique"].label = "Section analytique imputée"
        self.fields["categorie"].label = "Catégorie de la demande"
        self.fields["delai_souhaite"].help_text = "Date à laquelle le besoin doit idéalement être satisfait."
        self.fields["section_analytique"].help_text = "Section qui portera le besoin et son circuit de validation."
        self.fields["categorie"].help_text = "Permet d'orienter le besoin vers la bonne famille d'achat."

    class Meta:
        model = DemandeAchat
        fields = [
            "delai_souhaite",
            "adresse_livraison",
            "section_analytique",
            "categorie",
            "est_demande_de_prix",
        ]


class LigneDemandeAchatForm(forms.ModelForm):
    """Formulaire de ligne de demande d'achat."""

    CHAMPS_SERVICE_ACHAT = {"prix_unitaire", "fournisseur_retenu", "reference_fournisseur"}

    def __init__(self, *args, **kwargs):
        service_achat_mode = kwargs.pop("service_achat_mode", False)
        super().__init__(*args, **kwargs)
        _apply_accessibility_attrs(self.fields)

        self.fields["article_catalogue"].widget = ArticleCatalogueSelect(
            attrs={
                "class": "form-control js-article-catalogue-select",
                "data-placeholder": "Rechercher un article du catalogue",
            }
        )
        catalogue_queryset = ArticleCatalogue.objects.filter(actif=True).order_by("designation")
        self.fields["article_catalogue"].queryset = catalogue_queryset
        self.fields["article_catalogue"].label_from_instance = (
            lambda article: f"{article.reference} - {article.designation}"
        )
        self.fields["article_catalogue"].widget.catalogue_queryset = self.fields["article_catalogue"].queryset
        self.fields["article_catalogue"].widget.catalogue_map = {
            str(article.pk): article for article in catalogue_queryset
        }
        self.fields["article_catalogue"].widget.choices = self.fields["article_catalogue"].choices

        self.fields["fournisseur_retenu"].widget = FournisseurSelect(attrs={"class": "form-control"})
        fournisseur_queryset = Fournisseur.objects.order_by("nom")
        self.fields["fournisseur_retenu"].queryset = fournisseur_queryset
        self.fields["fournisseur_retenu"].label_from_instance = lambda fournisseur: fournisseur.nom
        self.fields["fournisseur_retenu"].widget.fournisseur_queryset = fournisseur_queryset
        self.fields["fournisseur_retenu"].widget.fournisseur_map = {
            str(fournisseur.pk): fournisseur for fournisseur in fournisseur_queryset
        }
        self.fields["fournisseur_retenu"].widget.choices = self.fields["fournisseur_retenu"].choices
        self.fields["article_catalogue"].label = "Article du catalogue"
        self.fields["hors_catalogue"].label = "Hors catalogue"
        self.fields["nouvelle_designation"].label = "Désignation hors catalogue"
        self.fields["nouvelle_description"].label = "Description hors catalogue"
        self.fields["nouvelle_photo"].label = "Photo hors catalogue"
        self.fields["quantite"].label = "Qté"
        self.fields["qte_stock"].label = "Stock"
        self.fields["prix_unitaire"].label = "PU HT"
        self.fields["prix_total"].label = "Total HT"
        self.fields["reference_fournisseur"].label = "Réf. fournisseur"
        self.fields["fournisseur_retenu"].label = "Fournisseur"
        self.fields["commentaire"].label = "Commentaire achat"
        self.fields["engin_concerne"].label = "Engin"
        self.fields["article_catalogue"].help_text = "Choisissez un article déjà référencé si le besoin existe au catalogue."
        self.fields["hors_catalogue"].help_text = "Cochez uniquement si l'article n'existe pas encore au catalogue."
        self.fields["prix_total"].help_text = "Calculé automatiquement à partir de la quantité et du prix unitaire."

        placeholder_map = {
            "nouvelle_designation": "Nom du nouvel article",
            "nouvelle_description": "Description du besoin hors catalogue",
            "quantite": "Quantité demandée",
            "qte_stock": "Quantité disponible en stock",
            "prix_unitaire": "Prix unitaire HT",
            "reference_fournisseur": "Référence fournisseur",
            "commentaire": "Commentaire utile au service achat",
            "engin_concerne": "Engin ou machine concerné",
        }

        for field_name, field in self.fields.items():
            if field_name in placeholder_map:
                field.widget.attrs["placeholder"] = placeholder_map[field_name]

            if field_name == "hors_catalogue":
                field.widget.attrs["class"] = "form-check-input js-hors-catalogue-toggle"
            elif field_name == "nouvelle_photo":
                field.widget.attrs["class"] = "form-control-file"
            elif isinstance(field.widget, forms.Textarea):
                field.widget.attrs.update({"class": "form-control", "rows": 3})
            else:
                field.widget.attrs.setdefault("class", "form-control")

        auto_filled_fields = ["qte_stock", "prix_unitaire", "prix_total", "reference_fournisseur"]
        for field_name in auto_filled_fields:
            self.fields[field_name].widget.attrs.update(
                {
                    "disabled": "disabled",
                    "class": f"{self.fields[field_name].widget.attrs.get('class', 'form-control')} js-auto-filled-field".strip(),
                }
            )

        if service_achat_mode:
            for field_name, field in self.fields.items():
                if field_name not in self.CHAMPS_SERVICE_ACHAT:
                    field.disabled = True

    def clean(self):
        cleaned_data = super().clean()
        fournisseur = cleaned_data.get("fournisseur_retenu")

        if fournisseur:
            cleaned_data["reference_fournisseur"] = fournisseur.reference_fournisseur or ""

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        reference_fournisseur = self.cleaned_data.get("reference_fournisseur")
        if reference_fournisseur is not None:
            instance.reference_fournisseur = reference_fournisseur

        if commit:
            instance.save()
            self.save_m2m()

        return instance

    class Meta:
        model = LigneDemandeAchat
        fields = [
            "article_catalogue",
            "hors_catalogue",
            "nouvelle_designation",
            "nouvelle_description",
            "nouvelle_photo",
            "quantite",
            "qte_stock",
            "prix_unitaire",
            "prix_total",
            "reference_fournisseur",
            "fournisseur_retenu",
            "commentaire",
            "engin_concerne",
        ]


class DevisForm(forms.ModelForm):
    """Formulaire de saisie d'un devis fournisseur pour une ligne."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _apply_accessibility_attrs(self.fields)
        self.fields["fournisseur"].widget = FournisseurSelect(attrs={"class": "form-control js-fournisseur-select"})
        fournisseur_queryset = Fournisseur.objects.filter(pris_en_compte=True).order_by("nom")
        self.fields["fournisseur"].queryset = fournisseur_queryset
        self.fields["fournisseur"].label_from_instance = lambda fournisseur: fournisseur.nom
        self.fields["fournisseur"].widget.fournisseur_queryset = fournisseur_queryset
        self.fields["fournisseur"].widget.fournisseur_map = {
            str(fournisseur.pk): fournisseur for fournisseur in fournisseur_queryset
        }
        self.fields["fournisseur"].widget.choices = self.fields["fournisseur"].choices
        self.fields["fournisseur"].label = "Fournisseur consulté"
        self.fields["prix_propose"].label = "Prix proposé HT"
        self.fields["reference_fournisseur"].label = "Référence fournisseur"
        self.fields["document"].label = "Pièce jointe du devis"
        self.fields["delai_livraison_propose"].label = "Délai de livraison proposé"
        self.fields["est_choisi"].label = "Retenir ce devis"
        self.fields["prix_propose"].help_text = "Montant proposé par le fournisseur pour cette ligne."
        self.fields["est_choisi"].help_text = "Si coché, ce devis devient l'offre retenue pour la ligne."
        self.fields["reference_fournisseur"].widget.attrs["placeholder"] = "Référence ou code article fournisseur"
        self.fields["delai_livraison_propose"].widget.attrs["placeholder"] = "Ex. 48h, 1 semaine, immédiat"
        self.fields["reference_fournisseur"].widget.attrs.update(
            {
                "disabled": "disabled",
                "class": "form-control js-auto-filled-field",
            }
        )

        for field_name, field in self.fields.items():
            if field_name == "document":
                field.widget.attrs["class"] = "form-control-file"
            elif field_name == "est_choisi":
                field.widget.attrs["class"] = "form-check-input"
            else:
                field.widget.attrs.setdefault("class", "form-control")

    def clean(self):
        cleaned_data = super().clean()
        fournisseur = cleaned_data.get("fournisseur")

        if fournisseur:
            cleaned_data["reference_fournisseur"] = fournisseur.reference_fournisseur or ""

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        reference_fournisseur = self.cleaned_data.get("reference_fournisseur")
        if reference_fournisseur is not None:
            instance.reference_fournisseur = reference_fournisseur

        if commit:
            instance.save()
            self.save_m2m()

        return instance

    class Meta:
        model = Devis
        fields = [
            "fournisseur",
            "prix_propose",
            "reference_fournisseur",
            "document",
            "delai_livraison_propose",
            "est_choisi",
        ]


class ReceptionMarchandiseForm(forms.ModelForm):
    """Formulaire de réception et évaluation fournisseur selon la grille P03."""

    CRITERES = (
        "c1_reponse_demande_prix",
        "c2_livraisons",
        "c3_disponibilite",
        "c4_qualite_utilisation",
        "c5_qualite_reception",
        "c6_information_produit",
        "c7_reglement_litiges",
        "c8_couts",
        "c9_communication",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _apply_accessibility_attrs(self.fields)
        self.fields["conforme_quantite_etat"].label = "Réception conforme en quantité et en état"
        self.fields["conforme_quantite_etat"].widget.attrs["class"] = "form-check-input"
        for field_name, field in self.fields.items():
            if field_name == "conforme_quantite_etat":
                continue
            field.widget.attrs.setdefault("class", "form-control")

    class Meta:
        model = ReceptionMarchandise
        fields = [
            "conforme_quantite_etat",
            "c1_reponse_demande_prix",
            "c2_livraisons",
            "c3_disponibilite",
            "c4_qualite_utilisation",
            "c5_qualite_reception",
            "c6_information_produit",
            "c7_reglement_litiges",
            "c8_couts",
            "c9_communication",
        ]


class DysfonctionnementForm(forms.ModelForm):
    """Formulaire de signalement d'un dysfonctionnement fournisseur."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _apply_accessibility_attrs(self.fields)
        self.fields["heure_signalement"].widget = forms.TimeInput(
            attrs={"class": "form-control", "type": "time"}
        )
        self.fields["description"].label = "Description du dysfonctionnement"
        self.fields["plan_action"].label = "Plan d'action fournisseur"
        self.fields["date_cloture"].widget = forms.DateInput(
            attrs={"class": "form-control", "type": "date"}
        )
        self.fields["description"].widget.attrs.update(
            {"class": "form-control", "rows": 4, "placeholder": "Décrivez précisément le problème constaté"}
        )
        self.fields["plan_action"].widget.attrs.update(
            {"class": "form-control", "rows": 3, "placeholder": "Actions correctives prévues par le fournisseur"}
        )
        self.fields["photo"].widget.attrs["class"] = "form-control-file"
        self.fields["statut"].widget.attrs.setdefault("class", "form-control")

    class Meta:
        model = Dysfonctionnement
        fields = [
            "heure_signalement",
            "description",
            "photo",
            "statut",
            "plan_action",
            "date_cloture",
        ]


class EvaluationFournisseurFilterForm(forms.Form):
    """Filtres d'affichage et de calcul des évaluations fournisseurs."""

    fournisseur = forms.ModelChoiceField(
        queryset=Fournisseur.objects.order_by("nom"),
        required=False,
        empty_label="Tous les fournisseurs",
        label="Fournisseur",
    )
    annee = forms.IntegerField(label="Année", min_value=2000, max_value=2100)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["annee"].widget.attrs.update({"class": "form-control", "placeholder": "2026"})
        self.fields["fournisseur"].widget.attrs.update({"class": "form-control"})


class ValidationDemandeForm(forms.Form):
    """Formulaire de traitement d'une étape de validation achat."""

    decision = forms.ChoiceField(
        label="Décision",
        choices=[
            (EtapeValidation.STATUT_APPROUVE, "Approuver"),
            (EtapeValidation.STATUT_REFUSE, "Refuser"),
            (EtapeValidation.STATUT_MODIFICATION_DEMANDEE, "Demander une modification"),
        ],
    )
    commentaire = forms.CharField(
        label="Commentaire",
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Motif ou commentaire de validation"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["decision"].widget.attrs.update({"class": "form-control"})


class ConfigurationValidationSectionForm(forms.ModelForm):
    """Formulaire de paramétrage des validateurs N1/N2 par section."""

    class Meta:
        model = ConfigurationValidationSection
        fields = ["section", "validateur_n1", "validateur_n2"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user_model = get_user_model()
        users_qs = user_model.objects.filter(is_active=True).order_by("first_name", "last_name", "username")

        self.fields["section"].queryset = Section.objects.order_by("Nom")
        self.fields["section"].label_from_instance = lambda section: section.Nom
        self.fields["validateur_n1"].queryset = users_qs
        self.fields["validateur_n2"].queryset = users_qs
        self.fields["validateur_n1"].required = False
        self.fields["validateur_n2"].required = False

        self.fields["section"].label = "Section"
        self.fields["validateur_n1"].label = "Validateur N1 (optionnel)"
        self.fields["validateur_n2"].label = "Validateur N2 (optionnel)"
        self.fields["validateur_n1"].help_text = "Si vide, le workflow utilisera le rôle RO pour le niveau N1."
        self.fields["validateur_n2"].help_text = "Si vide, le workflow utilisera un super administrateur pour le niveau N2."

        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("validateur_n1") and cleaned_data.get("validateur_n1") == cleaned_data.get("validateur_n2"):
            raise forms.ValidationError("Les validateurs N1 et N2 doivent être différents.")
        return cleaned_data


OffreFournisseurFormSet = inlineformset_factory(
    ArticleCatalogue,
    OffreFournisseur,
    form=OffreFournisseurForm,
    extra=1,
    can_delete=True,
)


LigneDemandeAchatFormSet = inlineformset_factory(
    DemandeAchat,
    LigneDemandeAchat,
    form=LigneDemandeAchatForm,
    extra=1,
    can_delete=True,
)
