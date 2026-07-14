"""Vues du module Achats."""

from collections import defaultdict
from datetime import datetime

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncMonth
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, TemplateView, UpdateView

from accounts.models import Section

from .forms import (
    ArticleCatalogueForm,
    ConfigurationValidationSectionForm,
    DevisForm,
    DemandeAchatForm,
    DysfonctionnementForm,
    EvaluationFournisseurFilterForm,
    FournisseurForm,
    LigneDemandeAchatFormSet,
    OffreFournisseurFormSet,
    ReceptionMarchandiseForm,
    ValidationDemandeForm,
)
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
    ReceptionMarchandise,
)
from .excel import build_demande_excel
from .services import (
    calculer_evaluation_fournisseur,
    calculer_toutes_evaluations,
    lancer_circuit_validation,
    mes_demandes_a_valider,
    traiter_validation_demande,
    user_can_validate_etape,
)


def user_has_achats_access(user):
    """Autorise uniquement superadmin, RS et RO sur le module Achats."""
    return bool(
        user.is_authenticated
        and (
            user.is_superuser
            or getattr(user, "is_RS", False)
            or getattr(user, "is_RO", False)
        )
    )


def achats_roles_required(view_func):
    """Décorateur de rôle pour protéger les endpoints achats."""

    def _wrapped(request, *args, **kwargs):
        if not user_has_achats_access(request.user):
            raise PermissionDenied
        return view_func(request, *args, **kwargs)

    return _wrapped


def _sync_ligne_with_selected_devis(ligne):
    """Réaligne la ligne de demande sur le devis retenu, s'il existe."""
    devis_choisi = ligne.devis.filter(est_choisi=True).select_related("fournisseur").first()

    if devis_choisi is None:
        ligne.prix_unitaire = None
        ligne.fournisseur_retenu = None
        ligne.reference_fournisseur = ""
    else:
        ligne.prix_unitaire = devis_choisi.prix_propose
        ligne.fournisseur_retenu = devis_choisi.fournisseur
        ligne.reference_fournisseur = devis_choisi.reference_fournisseur

    ligne.save()
    ligne.demande.recalculer_total()


def _user_can_view_demande(user, demande):
    """Détermine si l'utilisateur peut consulter la demande."""
    if user_has_achats_access(user):
        return True
    if demande.demandeur_id == user.pk:
        return True
    return any(user_can_validate_etape(user, etape) for etape in demande.etapes.all()) or demande.etapes.filter(validateur=user).exists()


class AchatsRoleRequiredMixin(LoginRequiredMixin):
    """Restreint l'accès global Achats à superadmin, RS et RO."""

    def dispatch(self, request, *args, **kwargs):
        if not user_has_achats_access(request.user):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


class ServiceAchatRequiredMixin(AchatsRoleRequiredMixin):
    """Restreint l'accès aux membres de l'équipe achat."""

    def user_is_service_achat(self):
        return user_has_achats_access(self.request.user)

    def dispatch(self, request, *args, **kwargs):
        if not self.user_is_service_achat():
            messages.error(request, "Cette action est réservée à l'équipe achat.")
            return redirect("achats:dashboard")
        return super().dispatch(request, *args, **kwargs)


class ConfigurationValidationSectionView(ServiceAchatRequiredMixin, TemplateView):
    """Page de paramétrage de la chaîne de validation achats par section."""

    template_name = "achats/configuration_validation_section.html"

    def _get_selected_section(self):
        section_id = self.request.GET.get("section")
        if not section_id:
            return None
        return Section.objects.filter(pk=section_id).first()

    def _build_form(self):
        selected_section = self._get_selected_section()
        initial = {}
        if selected_section:
            config = ConfigurationValidationSection.objects.filter(section=selected_section).first()
            initial = {
                "section": selected_section,
                "validateur_n1": config.validateur_n1 if config else None,
                "validateur_n2": config.validateur_n2 if config else None,
            }
        return ConfigurationValidationSectionForm(initial=initial)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = kwargs.get("form") or self._build_form()
        configurations = ConfigurationValidationSection.objects.select_related(
            "section",
            "validateur_n1",
            "validateur_n2",
        ).order_by("section__Nom")
        configured_section_ids = configurations.values_list("section_id", flat=True)
        sections_non_configurees = Section.objects.exclude(pk__in=configured_section_ids).order_by("Nom")
        context.update(
            {
                "form": form,
                "configurations": configurations,
                "sections_non_configurees": sections_non_configurees,
                "selected_section": self._get_selected_section(),
            }
        )
        return context

    def post(self, request, *args, **kwargs):
        section_id = request.POST.get("section")
        existing_config = None
        if section_id:
            existing_config = ConfigurationValidationSection.objects.filter(section_id=section_id).first()

        form = ConfigurationValidationSectionForm(request.POST, instance=existing_config)
        if not form.is_valid():
            messages.error(request, "Le paramétrage n'a pas pu être enregistré.")
            for field_name, errors in form.errors.items():
                if field_name == "__all__":
                    label = "Erreur"
                else:
                    label = form.fields[field_name].label or field_name
                for error in errors:
                    messages.error(request, f"{label} : {error}")
            return self.render_to_response(self.get_context_data(form=form))

        section = form.cleaned_data["section"]
        created = existing_config is None
        form.save()
        messages.success(
            request,
            "Configuration créée avec succès." if created else "Configuration mise à jour avec succès.",
        )
        return redirect(f"{reverse('achats:validation_config_section')}?section={section.pk}")


class ArticleCatalogueListView(AchatsRoleRequiredMixin, ListView):
    """Liste paginée du catalogue d'articles."""

    model = ArticleCatalogue
    template_name = "achats/catalogue_list.html"
    context_object_name = "articles"
    paginate_by = 20

    def get_queryset(self):
        queryset = ArticleCatalogue.objects.select_related("cree_par")
        query = self.request.GET.get("q", "").strip()
        categorie = self.request.GET.get("categorie", "").strip()
        type_article = self.request.GET.get("type_article", "").strip()
        actif = self.request.GET.get("actif", "").strip()

        if query:
            queryset = queryset.filter(Q(designation__icontains=query) | Q(reference__icontains=query))
        if categorie:
            queryset = queryset.filter(categorie=categorie)
        if type_article:
            queryset = queryset.filter(type_article=type_article)
        if actif in {"0", "1"}:
            queryset = queryset.filter(actif=bool(int(actif)))

        return queryset.order_by("designation")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["categories"] = ArticleCatalogue.CATEGORIE_CHOICES
        context["types"] = ArticleCatalogue.TYPE_CHOICES
        context["q"] = self.request.GET.get("q", "")
        context["categorie_filter"] = self.request.GET.get("categorie", "")
        context["type_filter"] = self.request.GET.get("type_article", "")
        context["actif_filter"] = self.request.GET.get("actif", "")
        return context


class ArticleCatalogueDetailView(AchatsRoleRequiredMixin, DetailView):
    """Détail d'un article avec ses offres fournisseurs."""

    model = ArticleCatalogue
    template_name = "achats/catalogue_detail.html"
    context_object_name = "article"

    def get_queryset(self):
        return (
            ArticleCatalogue.objects.select_related("cree_par")
            .prefetch_related("offres__fournisseur")
            .all()
        )


class ArticleCatalogueCreateView(AchatsRoleRequiredMixin, CreateView):
    """Création d'un article avec ses offres fournisseurs inline."""

    model = ArticleCatalogue
    form_class = ArticleCatalogueForm
    template_name = "achats/catalogue_form.html"

    def get_formset(self):
        return OffreFournisseurFormSet(self.request.POST or None, instance=self.object)

    def form_valid(self, form):
        formset = OffreFournisseurFormSet(self.request.POST, instance=self.object)
        if not formset.is_valid():
            return self.render_to_response(self.get_context_data(form=form, formset=formset))

        with transaction.atomic():
            form.instance.cree_par = self.request.user
            self.object = form.save()
            formset.instance = self.object
            formset.save()

        messages.success(self.request, "L'article a été créé avec succès.")
        return redirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context["formset"] = OffreFournisseurFormSet(self.request.POST, instance=self.object)
        else:
            context["formset"] = OffreFournisseurFormSet(instance=self.object)
        return context

    def get_success_url(self):
        return reverse_lazy("achats:catalogue_detail", kwargs={"pk": self.object.pk})


class ArticleCatalogueUpdateView(AchatsRoleRequiredMixin, UpdateView):
    """Modification d'un article avec ses offres fournisseurs inline."""

    model = ArticleCatalogue
    form_class = ArticleCatalogueForm
    template_name = "achats/catalogue_form.html"

    def form_valid(self, form):
        formset = OffreFournisseurFormSet(self.request.POST, instance=self.object)
        if not formset.is_valid():
            return self.render_to_response(self.get_context_data(form=form, formset=formset))

        with transaction.atomic():
            self.object = form.save()
            formset.instance = self.object
            formset.save()

        messages.success(self.request, "L'article a été mis à jour avec succès.")
        return redirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context["formset"] = OffreFournisseurFormSet(self.request.POST, instance=self.object)
        else:
            context["formset"] = OffreFournisseurFormSet(instance=self.object)
        return context

    def get_success_url(self):
        return reverse_lazy("achats:catalogue_detail", kwargs={"pk": self.object.pk})


class ArticleCatalogueDeleteView(AchatsRoleRequiredMixin, View):
    """Désactive un article sans le supprimer de la base."""

    def post(self, request, *args, **kwargs):
        article = get_object_or_404(ArticleCatalogue, pk=kwargs.get("pk"))
        article.actif = False
        article.save(update_fields=["actif"])
        messages.success(request, "L'article a été désactivé.")
        return redirect("achats:catalogue_list")

    def get(self, request, *args, **kwargs):
        return self.post(request, *args, **kwargs)


class ArticleCatalogueToggleActifView(AchatsRoleRequiredMixin, View):
    """Bascule l'état actif/inactif d'un article depuis la liste."""

    def post(self, request, *args, **kwargs):
        article = get_object_or_404(ArticleCatalogue, pk=kwargs.get("pk"))
        article.actif = not article.actif
        article.save(update_fields=["actif"])
        statut = "activé" if article.actif else "désactivé"
        messages.success(request, f"L'article a été {statut}.")
        return redirect("achats:catalogue_list")


class FournisseurTogglePriseEnCompteView(AchatsRoleRequiredMixin, View):
    """Bascule la prise en compte d'un fournisseur depuis la liste."""

    def post(self, request, *args, **kwargs):
        fournisseur = get_object_or_404(Fournisseur, pk=kwargs.get("pk"))
        fournisseur.pris_en_compte = not fournisseur.pris_en_compte
        fournisseur.save(update_fields=["pris_en_compte"])
        statut = "activé" if fournisseur.pris_en_compte else "désactivé"
        messages.success(request, f"Le fournisseur a été {statut}.")
        return redirect("achats:fournisseur_list")


class FournisseurListView(AchatsRoleRequiredMixin, ListView):
    """Liste paginée des fournisseurs."""

    model = Fournisseur
    template_name = "achats/fournisseur_list.html"
    context_object_name = "fournisseurs"
    paginate_by = 20

    def get_queryset(self):
        queryset = Fournisseur.objects.all()
        statut = self.request.GET.get("statut_evaluation", "").strip()
        pris_en_compte = self.request.GET.get("pris_en_compte", "")

        if statut:
            queryset = queryset.filter(statut_evaluation=statut)
        if pris_en_compte in {"0", "1"}:
            queryset = queryset.filter(pris_en_compte=bool(int(pris_en_compte)))

        return queryset.order_by("nom")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["statuts"] = Fournisseur.STATUT_CHOICES
        context["statut_filter"] = self.request.GET.get("statut_evaluation", "")
        context["pris_filter"] = self.request.GET.get("pris_en_compte", "")
        return context


class FournisseurDetailView(AchatsRoleRequiredMixin, DetailView):
    """Détail d'un fournisseur avec les articles proposés."""

    model = Fournisseur
    template_name = "achats/fournisseur_detail.html"
    context_object_name = "fournisseur"

    def get_queryset(self):
        return Fournisseur.objects.prefetch_related("offres__article").all()


class FournisseurCreateView(AchatsRoleRequiredMixin, CreateView):
    """Création d'un fournisseur."""

    model = Fournisseur
    form_class = FournisseurForm
    template_name = "achats/fournisseur_form.html"

    def get_success_url(self):
        return reverse_lazy("achats:fournisseur_detail", kwargs={"pk": self.object.pk})


class FournisseurUpdateView(AchatsRoleRequiredMixin, UpdateView):
    """Modification d'un fournisseur."""

    model = Fournisseur
    form_class = FournisseurForm
    template_name = "achats/fournisseur_form.html"

    def get_success_url(self):
        return reverse_lazy("achats:fournisseur_detail", kwargs={"pk": self.object.pk})


class DemandeAchatAccessMixin(AchatsRoleRequiredMixin):
    """Utilitaires communs pour les écrans de demandes d'achat."""

    def user_is_service_achat(self):
        return user_has_achats_access(self.request.user)

    def get_demandes_queryset(self):
        """Retourne le queryset de demandes visible pour l'utilisateur courant."""
        queryset = DemandeAchat.objects.select_related("demandeur", "section_analytique")
        if not self.user_is_service_achat():
            validation_ids = mes_demandes_a_valider(self.request.user).values_list("pk", flat=True)
            queryset = queryset.filter(Q(demandeur=self.request.user) | Q(pk__in=validation_ids)).distinct()
        return queryset


class DashboardAchatsView(DemandeAchatAccessMixin, TemplateView):
    """Dashboard analytique du module Achats."""

    template_name = "achats/dashboard.html"

    @staticmethod
    def _month_starts(month_count=6):
        """Construit la liste des premiers jours des derniers mois jusqu'au mois courant."""
        current = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        months = []
        for offset in range(month_count - 1, -1, -1):
            year = current.year
            month = current.month - offset
            while month <= 0:
                month += 12
                year -= 1
            months.append(datetime(year, month, 1, tzinfo=current.tzinfo))
        return months

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = self.get_demandes_queryset()
        now = timezone.now()

        status_map = dict(DemandeAchat.STATUT_CHOICES)
        status_counts_raw = queryset.values("statut").annotate(total=Count("id"))
        status_counts = {item[0]: 0 for item in DemandeAchat.STATUT_CHOICES}
        for item in status_counts_raw:
            status_counts[item["statut"]] = item["total"]

        total_demandes = queryset.count()
        montant_annee = (
            queryset.filter(date_creation__year=now.year).aggregate(total=Sum("total_commande_ht"))["total"]
            or 0
        )
        montant_en_cours = (
            queryset.filter(
                statut__in=[
                    DemandeAchat.STATUT_SOUMISE,
                    DemandeAchat.STATUT_EN_COURS_DEVIS,
                    DemandeAchat.STATUT_VALIDATION_N1,
                    DemandeAchat.STATUT_VALIDATION_N2,
                    DemandeAchat.STATUT_VALIDEE,
                    DemandeAchat.STATUT_COMMANDEE,
                ]
            ).aggregate(total=Sum("total_commande_ht"))["total"]
            or 0
        )

        recent_months = self._month_starts(6)
        month_labels = [month.strftime("%b %Y") for month in recent_months]
        recent_history = queryset.filter(date_creation__gte=recent_months[0]).annotate(
            month=TruncMonth("date_creation")
        ).values("month", "statut").annotate(total=Count("id")).order_by("month")

        history_map = defaultdict(lambda: defaultdict(int))
        for item in recent_history:
            history_map[item["statut"]][item["month"].strftime("%b %Y")] = item["total"]

        chart_series = []
        forecast_cards = []
        for statut, label in DemandeAchat.STATUT_CHOICES:
            data = [history_map[statut].get(month_label, 0) for month_label in month_labels]
            chart_series.append({"label": label, "data": data})
            recent_slice = data[-3:] if len(data) >= 3 else data
            forecast_value = round(sum(recent_slice) / len(recent_slice), 1) if recent_slice else 0
            forecast_cards.append(
                {
                    "statut": statut,
                    "label": label,
                    "current": status_counts.get(statut, 0),
                    "forecast": forecast_value,
                }
            )

        top_sections = list(
            queryset.values("section_analytique__Nom")
            .annotate(total=Count("id"), montant=Sum("total_commande_ht"))
            .order_by("-total")[:5]
        )

        context.update(
            {
                "total_demandes": total_demandes,
                "montant_annee": montant_annee,
                "montant_en_cours": montant_en_cours,
                "status_counts": status_counts,
                "status_cards": [
                    {
                        "statut": statut,
                        "label": label,
                        "count": status_counts.get(statut, 0),
                    }
                    for statut, label in DemandeAchat.STATUT_CHOICES
                ],
                "month_labels": month_labels,
                "chart_series": chart_series,
                "forecast_cards": forecast_cards,
                "top_sections": top_sections,
                "dashboard_scope": "global" if self.user_is_service_achat() else "mes demandes",
                "next_month_label": self._month_starts(2)[-1].strftime("%b %Y"),
                "can_manage_validation_config": self.user_is_service_achat(),
            }
        )
        return context


class DemandeAchatListView(DemandeAchatAccessMixin, ListView):
    """Liste paginée des demandes d'achat."""

    model = DemandeAchat
    template_name = "achats/demande_list.html"
    context_object_name = "demandes"
    paginate_by = 20

    def get_queryset(self):
        queryset = self.get_demandes_queryset()

        statut = self.request.GET.get("statut", "").strip()
        numero = self.request.GET.get("numero", "").strip()

        if statut:
            queryset = queryset.filter(statut=statut)
        if numero:
            queryset = queryset.filter(numero__icontains=numero)

        return queryset.order_by("-date_creation")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["statuts"] = DemandeAchat.STATUT_CHOICES
        context["statut_filter"] = self.request.GET.get("statut", "")
        context["numero_filter"] = self.request.GET.get("numero", "")
        return context


class DemandeAchatCreateView(DemandeAchatAccessMixin, View):
    """Création d'une demande d'achat avec ses lignes."""

    template_name = "achats/demande_form.html"

    def get(self, request, *args, **kwargs):
        form = DemandeAchatForm()
        formset = LigneDemandeAchatFormSet(prefix="lignes")
        return render(
            request,
            self.template_name,
            {
                "form": form,
                "formset": formset,
                "today": timezone.now(),
                "submit_label": "Créer la demande d'achat",
            },
        )

    def post(self, request, *args, **kwargs):
        form = DemandeAchatForm(request.POST)
        formset = LigneDemandeAchatFormSet(
            request.POST,
            request.FILES,
            prefix="lignes",
        )

        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                demande = form.save(commit=False)
                demande.demandeur = request.user
                if request.POST.get("action") == "soumettre":
                    demande.statut = DemandeAchat.STATUT_SOUMISE
                else:
                    demande.statut = DemandeAchat.STATUT_BROUILLON
                demande.save()

                formset.instance = demande
                formset.save()

            message = "La demande d'achat a été soumise." if demande.statut == DemandeAchat.STATUT_SOUMISE else "La demande d'achat a été enregistrée en brouillon."
            messages.success(request, message)
            return redirect("achats:demande_detail", pk=demande.pk)

        return render(
            request,
            self.template_name,
            {
                "form": form,
                "formset": formset,
                "today": timezone.now(),
                "submit_label": "Créer la demande d'achat",
            },
        )


class DemandeAchatUpdateView(DemandeAchatAccessMixin, View):
    """Modification d'une demande d'achat selon son statut."""

    template_name = "achats/demande_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.demande = get_object_or_404(DemandeAchat, pk=kwargs["pk"])

        if not self.user_is_service_achat() and self.demande.demandeur != request.user:
            messages.error(request, "Vous ne pouvez pas modifier cette demande d'achat.")
            return redirect("achats:demande_list")

        can_edit_draft = self.demande.statut == DemandeAchat.STATUT_BROUILLON
        can_edit_achat = self.user_is_service_achat() and self.demande.statut == DemandeAchat.STATUT_EN_COURS_DEVIS
        if not can_edit_draft and not can_edit_achat:
            messages.warning(request, "Cette demande n'est plus modifiable dans son état actuel.")
            return redirect("achats:demande_detail", pk=self.demande.pk)

        return super().dispatch(request, *args, **kwargs)

    def get_formset(self, data=None, files=None):
        return LigneDemandeAchatFormSet(
            data=data,
            files=files,
            instance=self.demande,
            prefix="lignes",
            form_kwargs={"service_achat_mode": self.user_is_service_achat() and self.demande.statut == DemandeAchat.STATUT_EN_COURS_DEVIS},
        )

    def get(self, request, *args, **kwargs):
        form = DemandeAchatForm(instance=self.demande)
        formset = self.get_formset()

        if self.user_is_service_achat() and self.demande.statut == DemandeAchat.STATUT_EN_COURS_DEVIS:
            for field in form.fields.values():
                field.disabled = True

        return render(
            request,
            self.template_name,
            {
                "form": form,
                "formset": formset,
                "demande": self.demande,
                "today": self.demande.date_emission,
                "submit_label": "Mettre à jour la demande d'achat",
                "service_achat_mode": self.user_is_service_achat() and self.demande.statut == DemandeAchat.STATUT_EN_COURS_DEVIS,
            },
        )

    def post(self, request, *args, **kwargs):
        form = DemandeAchatForm(request.POST, instance=self.demande)
        formset = self.get_formset(data=request.POST, files=request.FILES)

        if self.user_is_service_achat() and self.demande.statut == DemandeAchat.STATUT_EN_COURS_DEVIS:
            for field in form.fields.values():
                field.disabled = True

        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                demande = form.save(commit=False)
                if self.demande.statut == DemandeAchat.STATUT_BROUILLON:
                    demande.statut = (
                        DemandeAchat.STATUT_SOUMISE
                        if request.POST.get("action") == "soumettre"
                        else DemandeAchat.STATUT_BROUILLON
                    )
                demande.save()
                formset.instance = demande
                formset.save()

            messages.success(request, "La demande d'achat a été mise à jour.")
            return redirect("achats:demande_detail", pk=self.demande.pk)

        return render(
            request,
            self.template_name,
            {
                "form": form,
                "formset": formset,
                "demande": self.demande,
                "today": self.demande.date_emission,
                "submit_label": "Mettre à jour la demande d'achat",
                "service_achat_mode": self.user_is_service_achat() and self.demande.statut == DemandeAchat.STATUT_EN_COURS_DEVIS,
            },
        )


class DemandeAchatDetailView(DemandeAchatAccessMixin, DetailView):
    """Détail complet d'une demande d'achat."""

    model = DemandeAchat
    template_name = "achats/demande_detail.html"
    context_object_name = "demande"

    def get_queryset(self):
        queryset = self.get_demandes_queryset().prefetch_related(
            "lignes__article_catalogue",
            "lignes__fournisseur_retenu",
            "lignes__devis__fournisseur",
            "etapes__validateur",
            "dysfonctionnements",
        )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        demande = self.object
        pending_etape = next(
            (
                etape
                for etape in demande.etapes.filter(statut=EtapeValidation.STATUT_EN_ATTENTE)
                if user_can_validate_etape(self.request.user, etape)
                or etape.validateur_id == self.request.user.pk
            ),
            None,
        )
        current_year = timezone.now().year
        fournisseurs_ids = list(
            demande.lignes.exclude(fournisseur_retenu__isnull=True).values_list("fournisseur_retenu_id", flat=True)
        )
        context.update(
            {
                "pending_etape": pending_etape,
                "validation_form": ValidationDemandeForm(),
                "devis_retenus_count": demande.lignes.filter(fournisseur_retenu__isnull=False).count(),
                "reception": getattr(demande, "reception", None),
                "evaluations_fournisseurs": EvaluationFournisseur.objects.filter(
                    annee=current_year,
                    fournisseur_id__in=fournisseurs_ids,
                ).select_related("fournisseur"),
            }
        )
        return context


class DemandeAchatExcelDownloadView(DemandeAchatAccessMixin, View):
    """Télécharge une demande d'achat au format Excel Doc 07."""

    def get(self, request, *args, **kwargs):
        demande = get_object_or_404(self.get_demandes_queryset(), pk=kwargs["pk"])
        workbook_content = build_demande_excel(demande)
        filename = f"demande_achat_{(demande.numero or demande.pk)}.xlsx".replace("/", "-")
        response = HttpResponse(
            workbook_content,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


class DemandePasserEnDevisView(ServiceAchatRequiredMixin, View):
    """Passe une demande soumise dans l'étape de consultation devis."""

    def post(self, request, *args, **kwargs):
        demande = get_object_or_404(DemandeAchat, pk=kwargs["pk"])
        if demande.statut != DemandeAchat.STATUT_SOUMISE:
            messages.warning(request, "Seules les demandes soumises peuvent passer en cours de devis.")
            return redirect("achats:demande_detail", pk=demande.pk)

        demande.statut = DemandeAchat.STATUT_EN_COURS_DEVIS
        demande.save(update_fields=["statut", "date_modification"])
        messages.success(request, "La demande est maintenant en cours de devis.")
        return redirect("achats:devis_manage", pk=demande.pk)


class DemandeLancerValidationView(ServiceAchatRequiredMixin, View):
    """Lance le circuit de validation après sélection des devis."""

    def post(self, request, *args, **kwargs):
        demande = get_object_or_404(DemandeAchat, pk=kwargs["pk"])
        lignes_sans_choix = demande.lignes.filter(Q(fournisseur_retenu__isnull=True) | Q(prix_unitaire__isnull=True))
        if lignes_sans_choix.exists():
            messages.error(request, "Chaque ligne doit avoir un fournisseur retenu et un prix avant validation.")
            return redirect("achats:devis_manage", pk=demande.pk)

        try:
            lancer_circuit_validation(demande)
        except ValidationError as exc:
            messages.error(request, exc.messages[0])
            return redirect("achats:devis_manage", pk=demande.pk)

        messages.success(request, "Le circuit de validation a été lancé.")
        return redirect("achats:demande_detail", pk=demande.pk)


class DemandeTraiterValidationView(AchatsRoleRequiredMixin, View):
    """Traite une étape de validation hiérarchique d'une demande."""

    def post(self, request, *args, **kwargs):
        demande = get_object_or_404(DemandeAchat, pk=kwargs["pk"])
        etape = get_object_or_404(EtapeValidation, pk=kwargs["etape_pk"], demande=demande)
        form = ValidationDemandeForm(request.POST)
        if not form.is_valid():
            messages.error(request, "La décision de validation est invalide.")
            return redirect("achats:demande_detail", pk=demande.pk)

        try:
            traiter_validation_demande(
                demande,
                etape,
                form.cleaned_data["decision"],
                form.cleaned_data["commentaire"],
                request.user,
            )
        except (ValidationError, PermissionDenied) as exc:
            message = exc.messages[0] if hasattr(exc, "messages") else str(exc)
            messages.error(request, message)
            return redirect("achats:demande_detail", pk=demande.pk)

        messages.success(request, "La décision de validation a été enregistrée.")
        return redirect("achats:demande_detail", pk=demande.pk)


class DevisDemandesListView(ServiceAchatRequiredMixin, ListView):
    """Liste des demandes à consulter ou compléter en phase devis."""

    model = DemandeAchat
    template_name = "achats/devis_queue.html"
    context_object_name = "demandes"

    def get_queryset(self):
        return (
            DemandeAchat.objects.filter(
                statut__in=[DemandeAchat.STATUT_SOUMISE, DemandeAchat.STATUT_EN_COURS_DEVIS]
            )
            .select_related("demandeur", "section_analytique")
            .prefetch_related("lignes")
            .order_by("-date_creation")
        )


class DevisManageView(ServiceAchatRequiredMixin, DetailView):
    """Écran de pilotage des devis rattachés à une demande d'achat."""

    model = DemandeAchat
    template_name = "achats/devis_manage.html"
    context_object_name = "demande"

    def get_queryset(self):
        return DemandeAchat.objects.select_related("demandeur", "section_analytique").prefetch_related(
            "lignes__article_catalogue",
            "lignes__devis__fournisseur",
            "lignes__fournisseur_retenu",
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        demande = self.object
        context.update(
            {
                "lignes_sans_choix": demande.lignes.filter(fournisseur_retenu__isnull=True).count(),
                "peut_lancer_validation": demande.statut == DemandeAchat.STATUT_EN_COURS_DEVIS,
            }
        )
        return context


class DevisCreateView(ServiceAchatRequiredMixin, View):
    """Création d'un devis pour une ligne de demande."""

    template_name = "achats/devis_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.ligne = get_object_or_404(
            LigneDemandeAchat.objects.select_related("demande", "article_catalogue"),
            pk=kwargs["ligne_pk"],
        )
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        form = DevisForm()
        return render(request, self.template_name, {"form": form, "ligne": self.ligne, "demande": self.ligne.demande})

    def post(self, request, *args, **kwargs):
        form = DevisForm(request.POST, request.FILES)
        if form.is_valid():
            devis = form.save(commit=False)
            devis.ligne = self.ligne
            devis.saisi_par = request.user
            if self.ligne.demande.statut == DemandeAchat.STATUT_SOUMISE:
                self.ligne.demande.statut = DemandeAchat.STATUT_EN_COURS_DEVIS
                self.ligne.demande.save(update_fields=["statut", "date_modification"])
            devis.save()
            _sync_ligne_with_selected_devis(self.ligne)
            messages.success(request, "Le devis a été ajouté à la ligne.")
            return redirect("achats:devis_manage", pk=self.ligne.demande.pk)
        return render(request, self.template_name, {"form": form, "ligne": self.ligne, "demande": self.ligne.demande})


class DevisUpdateView(ServiceAchatRequiredMixin, UpdateView):
    """Modification d'un devis existant."""

    model = Devis
    form_class = DevisForm
    template_name = "achats/devis_form.html"
    context_object_name = "devis"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["ligne"] = self.object.ligne
        context["demande"] = self.object.ligne.demande
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        _sync_ligne_with_selected_devis(self.object.ligne)
        messages.success(self.request, "Le devis a été mis à jour.")
        return response

    def get_success_url(self):
        return reverse("achats:devis_manage", kwargs={"pk": self.object.ligne.demande.pk})


class DevisDeleteView(ServiceAchatRequiredMixin, View):
    """Suppression d'un devis saisi pour une ligne."""

    def post(self, request, *args, **kwargs):
        devis = get_object_or_404(Devis.objects.select_related("ligne__demande"), pk=kwargs["pk"])
        demande_pk = devis.ligne.demande.pk
        ligne = devis.ligne
        devis.delete()
        _sync_ligne_with_selected_devis(ligne)
        messages.success(request, "Le devis a été supprimé.")
        return redirect("achats:devis_manage", pk=demande_pk)


class DevisChoisirView(ServiceAchatRequiredMixin, View):
    """Marque un devis comme retenu et synchronise la ligne d'achat."""

    def post(self, request, *args, **kwargs):
        devis = get_object_or_404(Devis.objects.select_related("ligne__demande"), pk=kwargs["pk"])
        devis.est_choisi = True
        devis.save(update_fields=["est_choisi"])
        _sync_ligne_with_selected_devis(devis.ligne)
        if devis.ligne.demande.statut == DemandeAchat.STATUT_SOUMISE:
            devis.ligne.demande.statut = DemandeAchat.STATUT_EN_COURS_DEVIS
            devis.ligne.demande.save(update_fields=["statut", "date_modification"])
        messages.success(request, "Le devis retenu a été enregistré.")
        return redirect("achats:devis_manage", pk=devis.ligne.demande.pk)


class ReceptionListView(ServiceAchatRequiredMixin, ListView):
    """Liste des demandes prêtes à être réceptionnées ou déjà réceptionnées."""

    model = DemandeAchat
    template_name = "achats/reception_list.html"
    context_object_name = "demandes"

    def get_queryset(self):
        return (
            DemandeAchat.objects.filter(
                statut__in=[
                    DemandeAchat.STATUT_VALIDEE,
                    DemandeAchat.STATUT_COMMANDEE,
                    DemandeAchat.STATUT_RECEPTIONNEE,
                    DemandeAchat.STATUT_CLOTUREE,
                ]
            )
            .select_related("demandeur", "section_analytique", "reception")
            .order_by("-date_creation")
        )


class ReceptionCreateUpdateView(ServiceAchatRequiredMixin, View):
    """Saisie ou mise à jour d'une réception marchandise."""

    template_name = "achats/reception_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.demande = get_object_or_404(
            DemandeAchat.objects.select_related("demandeur", "section_analytique"),
            pk=kwargs["pk"],
        )
        self.reception = getattr(self.demande, "reception", None)
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        form = ReceptionMarchandiseForm(instance=self.reception)
        dysfonctionnement_form = DysfonctionnementForm()
        return render(
            request,
            self.template_name,
            {
                "form": form,
                "demande": self.demande,
                "reception": self.reception,
                "dysfonctionnement_form": dysfonctionnement_form,
            },
        )

    def post(self, request, *args, **kwargs):
        form = ReceptionMarchandiseForm(request.POST, instance=self.reception)
        if form.is_valid():
            reception = form.save(commit=False)
            reception.demande = self.demande
            if reception.pk is None:
                reception.receptionne_par = request.user
            reception.save()
            self.demande.statut = DemandeAchat.STATUT_RECEPTIONNEE
            self.demande.save(update_fields=["statut", "date_modification"])
            messages.success(request, "La réception marchandise a été enregistrée.")
            return redirect("achats:reception_edit", pk=self.demande.pk)

        dysfonctionnement_form = DysfonctionnementForm()
        return render(
            request,
            self.template_name,
            {
                "form": form,
                "demande": self.demande,
                "reception": self.reception,
                "dysfonctionnement_form": dysfonctionnement_form,
            },
        )


class DysfonctionnementCreateView(ServiceAchatRequiredMixin, View):
    """Crée un dysfonctionnement lié à une demande ou une réception."""

    def post(self, request, *args, **kwargs):
        demande = get_object_or_404(DemandeAchat, pk=kwargs["pk"])
        reception = getattr(demande, "reception", None)
        form = DysfonctionnementForm(request.POST, request.FILES)
        if not form.is_valid():
            messages.error(request, "Le dysfonctionnement n'a pas pu être enregistré.")
            return render(
                request,
                "achats/reception_form.html",
                {
                    "form": ReceptionMarchandiseForm(instance=reception),
                    "demande": demande,
                    "reception": reception,
                    "dysfonctionnement_form": form,
                },
            )

        dysfonctionnement = form.save(commit=False)
        dysfonctionnement.demande = demande
        dysfonctionnement.reception = reception
        dysfonctionnement.signale_par = request.user
        dysfonctionnement.save()
        messages.success(request, "Le dysfonctionnement a été enregistré.")
        return redirect("achats:reception_edit", pk=demande.pk)


class EvaluationFournisseurListView(ServiceAchatRequiredMixin, TemplateView):
    """Consultation et recalcul des évaluations annuelles fournisseurs."""

    template_name = "achats/evaluation_list.html"

    def _get_initial_year(self):
        return timezone.now().year

    def _build_filter_form(self, data=None):
        if data is None:
            return EvaluationFournisseurFilterForm(initial={"annee": self._get_initial_year()})
        return EvaluationFournisseurFilterForm(data)

    def _get_queryset(self, annee, fournisseur=None):
        queryset = EvaluationFournisseur.objects.select_related("fournisseur").filter(annee=annee)
        if fournisseur is not None:
            queryset = queryset.filter(fournisseur=fournisseur)
        return queryset.order_by("fournisseur__nom")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = kwargs.get("filter_form") or self._build_filter_form(self.request.GET or None)
        annee = form.cleaned_data["annee"] if form.is_bound and form.is_valid() else self._get_initial_year()
        fournisseur = form.cleaned_data.get("fournisseur") if form.is_bound and form.is_valid() else None
        evaluations = self._get_queryset(annee, fournisseur)
        context.update(
            {
                "filter_form": form,
                "evaluations": evaluations,
                "annee_courante": annee,
                "fournisseur_filtre": fournisseur,
            }
        )
        return context

    def post(self, request, *args, **kwargs):
        filter_form = self._build_filter_form(request.POST)
        if not filter_form.is_valid():
            return self.render_to_response(self.get_context_data(filter_form=filter_form))

        annee = filter_form.cleaned_data["annee"]
        fournisseur = filter_form.cleaned_data.get("fournisseur")
        action = request.POST.get("action")

        if action == "calculer_toutes":
            evaluations = calculer_toutes_evaluations(annee)
            if evaluations:
                messages.success(request, f"{len(evaluations)} évaluation(s) fournisseur recalculée(s).")
            else:
                messages.warning(request, "Aucune réception exploitable n'a été trouvée pour cette année.")
        elif action == "calculer_fournisseur" and fournisseur is not None:
            evaluation = calculer_evaluation_fournisseur(fournisseur, annee)
            if evaluation is None:
                messages.warning(request, "Aucune réception exploitable n'a été trouvée pour ce fournisseur.")
            else:
                messages.success(request, "L'évaluation du fournisseur a été recalculée.")

        params = {"annee": annee}
        if fournisseur is not None:
            params["fournisseur"] = fournisseur.pk
        return HttpResponseRedirect(f"{reverse('achats:evaluation_list')}?" + "&".join(f"{key}={value}" for key, value in params.items()))
