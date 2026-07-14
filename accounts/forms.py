"""Formulaires pour le module Administration (accounts)."""

from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import Customer, Section, Site, Societe, User


class _AdminLTEMixin:
    """Ajoute automatiquement la classe 'form-control' et un placeholder sur tous les widgets."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            widget = field.widget
            if isinstance(widget, (forms.CheckboxInput, forms.CheckboxSelectMultiple)):
                continue
            existing_class = widget.attrs.get("class", "")
            widget.attrs["class"] = f"{existing_class} form-control".strip()
            # Placeholder automatique si absent
            if not widget.attrs.get("placeholder"):
                label = field.label or name.replace("_", " ").capitalize()
                widget.attrs["placeholder"] = str(label)


# ---------------------------------------------------------------------------
# Societe
# ---------------------------------------------------------------------------

class SocieteForm(_AdminLTEMixin, forms.ModelForm):
    class Meta:
        model = Societe
        fields = ["nom"]


# ---------------------------------------------------------------------------
# Customer
# ---------------------------------------------------------------------------

CUSTOMER_TYPE_CHOICES = [
    ("client", "Client"),
    ("prospect", "Prospect"),
    ("fournisseur", "Fournisseur"),
]


class CustomerForm(_AdminLTEMixin, forms.ModelForm):
    class Meta:
        model = Customer
        fields = [
            "compte", "type", "intitule", "abrege", "qualite",
            "compte_collectif", "interlocuteur", "commentaire",
            "adresse", "complement", "code_postal", "ville", "region",
            "pays", "telephone", "linkedin", "facebook", "email",
            "site_web", "siret", "code_naf", "code_vat",
            "societe", "is_draft",
        ]
        widgets = {
            "commentaire": forms.Textarea(attrs={"rows": 3}),
            "adresse": forms.Textarea(attrs={"rows": 2}),
        }


# ---------------------------------------------------------------------------
# Section
# ---------------------------------------------------------------------------

class SectionForm(_AdminLTEMixin, forms.ModelForm):
    class Meta:
        model = Section
        fields = [
            "Nom", "societe",
            "pays", "gouvernorat",
            "latitude_max", "latitude_min",
            "longitude_max", "longitude_min",
        ]


# ---------------------------------------------------------------------------
# Site
# ---------------------------------------------------------------------------

class SiteForm(_AdminLTEMixin, forms.ModelForm):
    class Meta:
        model = Site
        fields = ["nom", "section"]


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------

class UserCreateForm(_AdminLTEMixin, UserCreationForm):
    class Meta:
        model = User
        fields = [
            "username", "first_name", "last_name", "email",
            "password1", "password2",
            "telephone", "pays", "adresse", "vat_code",
            "section", "societe", "societes", "customer",
            "cout_horaire", "timezone",
            # Rôles opérationnels
            "is_RS", "is_RO", "is_CE", "is_OP",
            "is_resp", "is_divers", "is_assistante", "is_sais", "is_interime",
            # Rôles audit / commercial
            "is_auditeur", "is_C", "is_RC", "is_CLT",
            # Django admin flags
            "is_superuser", "is_staff", "is_active",
        ]
        widgets = {
            "societes": forms.CheckboxSelectMultiple(),
        }


class UserEditForm(_AdminLTEMixin, forms.ModelForm):
    class Meta:
        model = User
        fields = [
            "username", "first_name", "last_name", "email",
            "telephone", "pays", "adresse", "vat_code",
            "section", "societe", "societes", "customer",
            "cout_horaire", "timezone",
            # Rôles opérationnels
            "is_RS", "is_RO", "is_CE", "is_OP",
            "is_resp", "is_divers", "is_assistante", "is_sais", "is_interime",
            # Rôles audit / commercial
            "is_auditeur", "is_C", "is_RC", "is_CLT",
            # Django admin flags
            "is_superuser", "is_staff", "is_active",
        ]
        widgets = {
            "societes": forms.CheckboxSelectMultiple(),
        }
