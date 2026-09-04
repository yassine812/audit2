"""Vues CBV et export PDF pour le module Plan de Prévention (PDP)."""

import base64
from io import BytesIO
import logging
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.staticfiles import finders as static_finders
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, DeleteView, DetailView, ListView, TemplateView, UpdateView

try:
    from weasyprint import HTML as WeasyprintHTML
except Exception:
    WeasyprintHTML = None

try:
    from xhtml2pdf import pisa
except Exception:
    pisa = None

from accounts.models import Customer, Societe
from .forms import PlanPreventionForm, PlanPreventionRisqueFormSet, RisqueForm, RisquePDPForm
from .models import PlanPrevention, PlanPreventionRisque, RisquePDP
from .permissions import (
    PDPCreatePermissionMixin,
    PDPEditPermissionMixin,
    PDPTenantScopedQuerySetMixin,
    filter_pdp_queryset_for_user,
    get_user_societe,
    user_can_add_pdp_risk,
    user_can_delete_pdp,
    user_can_edit_pdp,
)

User = get_user_model()
logger = logging.getLogger(__name__)



class PDPDashboardView(PDPTenantScopedQuerySetMixin, ListView):
    """Tableau de bord principal du module Plan de Prévention (PDP).

    Affiche les KPI, l'état d'avancement, et permet le filtrage multi-critères.
    """

    model = PlanPrevention
    template_name = "plan_prevention/pdp_dashboard.html"
    context_object_name = "plans_prevention"
    paginate_by = 10

    def get_queryset(self):
        qs = super().get_queryset().select_related("societe", "section", "site", "customer", "created_by")
        # Filtres textuels & statut
        query = self.request.GET.get("q", "").strip()
        statut = self.request.GET.get("statut", "").strip()
        type_op = self.request.GET.get("type_operation", "").strip()
        annee = self.request.GET.get("annee", "").strip()

        if query:
            qs = qs.filter(
                Q(reference__icontains=query)
                | Q(eu_nom__icontains=query)
                | Q(ee_nom__icontains=query)
                | Q(nature_operation__icontains=query)
                | Q(lieu_intervention__icontains=query)
            )
        if statut:
            qs = qs.filter(statut=statut)
        if type_op:
            qs = qs.filter(type_operation=type_op)
        if annee and annee.isdigit():
            qs = qs.filter(date_debut__year=int(annee))

        return qs.order_by("-created_at")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Base KPI sur le périmètre accessible (tenant-scoped)
        kpi_qs = filter_pdp_queryset_for_user(PlanPrevention.objects.all(), user)

        # Liste des années disponibles pour le filtre
        years = kpi_qs.dates("date_debut", "year", order="DESC")
        years_list = [y.year for y in years]
        annee_selected = self.request.GET.get("annee", "").strip()
        if annee_selected and annee_selected.isdigit():
            kpi_qs = kpi_qs.filter(date_debut__year=int(annee_selected))

        today = timezone.now().date()
        total_count = kpi_qs.count()
        upcoming_count = kpi_qs.filter(date_debut__gte=today, statut__in=["brouillon", "en_attente_signature"]).count()
        valide_count = kpi_qs.filter(statut="valide").count()
        brouillon_count = kpi_qs.filter(statut="brouillon").count()
        cloture_count = kpi_qs.filter(statut="cloture").count()

        pct_valide = round((valide_count / total_count * 100)) if total_count > 0 else 0

        # Initialisation du formulaire de création pour la modal (début 100% à vide)
        create_form = PlanPreventionForm(user=user)
        risques_formset = PlanPreventionRisqueFormSet()
        catalogue_risques = RisquePDP.objects.filter(est_actif=True).order_by("ordre", "code")

        context.update({
            "total_count": total_count,
            "upcoming_count": upcoming_count,
            "valide_count": valide_count,
            "brouillon_count": brouillon_count,
            "cloture_count": cloture_count,
            "pct_valide": pct_valide,
            "years_list": years_list,
            "annee_selected": annee_selected,
            "search_q": self.request.GET.get("q", "").strip(),
            "selected_statut": self.request.GET.get("statut", "").strip(),
            "selected_type": self.request.GET.get("type_operation", "").strip(),
            "create_form": create_form,
            "risques_formset": risques_formset,
            "catalogue_risques": catalogue_risques,
            "can_add_risk": user_can_add_pdp_risk(user),
            "risque_form": RisquePDPForm(),
        })
        return context


class PDPListView(PDPTenantScopedQuerySetMixin, ListView):
    """Liste filtrée des Plans de Prévention Simplifiés."""

    model = PlanPrevention
    template_name = "plan_prevention/pdp_list.html"
    context_object_name = "plans_prevention"
    paginate_by = 15

    def get_queryset(self):
        qs = super().get_queryset().select_related("societe", "customer", "created_by")
        query = self.request.GET.get("q", "").strip()
        statut = self.request.GET.get("statut", "").strip()
        type_op = self.request.GET.get("type_operation", "").strip()

        if query:
            qs = qs.filter(
                Q(reference__icontains=query)
                | Q(eu_nom__icontains=query)
                | Q(ee_nom__icontains=query)
                | Q(nature_operation__icontains=query)
                | Q(lieu_intervention__icontains=query)
            )
        if statut:
            qs = qs.filter(statut=statut)
        if type_op:
            qs = qs.filter(type_operation=type_op)

        return qs.order_by("-created_at")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        initial_data = {}
        user_soc = get_user_societe(user)
        if user_soc:
            initial_data["societe"] = user_soc.pk

        context.update({
            "create_form": PlanPreventionForm(user=user),
            "risques_formset": PlanPreventionRisqueFormSet(),
            "catalogue_risques": RisquePDP.objects.filter(est_actif=True).order_by("ordre", "code"),
            "can_add_risk": user_can_add_pdp_risk(user),
            "risque_form": RisquePDPForm(),
        })
        return context


class PDPCreateView(PDPCreatePermissionMixin, CreateView):
    """Création d'un nouveau Plan de Prévention Simplifié via modal."""

    model = PlanPrevention
    form_class = PlanPreventionForm
    template_name = "plan_prevention/pdp_form.html"

    def get(self, request, *args, **kwargs):
        """Redirige les requêtes GET vers le tableau de bord (la création se fait via modal)."""
        messages.info(request, "La création de Plan de Prévention s'effectue via le bouton '+ Nouveau Plan'.")
        return redirect("plan_prevention:dashboard")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_initial(self):
        return {}

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        if self.request.POST:
            data["risques_formset"] = PlanPreventionRisqueFormSet(self.request.POST)
        else:
            data["risques_formset"] = PlanPreventionRisqueFormSet()
        data["catalogue_risques"] = RisquePDP.objects.filter(est_actif=True).order_by("ordre", "code")
        data["can_add_risk"] = user_can_add_pdp_risk(self.request.user)
        data["risque_form"] = RisquePDPForm()
        return data

    def form_valid(self, form):
        with transaction.atomic():
            form.instance.created_by = self.request.user
            if not form.instance.societe_id:
                user_soc = get_user_societe(self.request.user)
                if user_soc:
                    form.instance.societe = user_soc

            self.object = form.save()

            # Enregistrer UNIQUEMENT les risques explicitement cochés par l'utilisateur
            # (Un nouveau PDP débute avec 0 risque par défaut)
            catalogue_risques = RisquePDP.objects.filter(est_actif=True).order_by("ordre", "code")
            for ordre, r_obj in enumerate(catalogue_risques, start=1):
                if self.request.POST.get(f"risk_selected_{r_obj.id}"):
                    mesures = self.request.POST.get(f"risk_mesures_{r_obj.id}", "").strip()
                    me_eu = bool(self.request.POST.get(f"risk_me_eu_{r_obj.id}"))
                    me_ee = bool(self.request.POST.get(f"risk_me_ee_{r_obj.id}"))

                    PlanPreventionRisque.objects.create(
                        pdp=self.object,
                        risque=r_obj,
                        concerne_eu=True,
                        concerne_ee=True,
                        mesures_prevention=mesures,
                        mise_en_oeuvre_eu=me_eu,
                        mise_en_oeuvre_ee=me_ee,
                        ordre=ordre,
                    )

        messages.success(self.request, f"Le Plan de Prévention '{self.object.reference}' a été créé avec succès.")
        return redirect("plan_prevention:dashboard")

    def form_invalid(self, form):
        messages.error(self.request, "Erreur lors de la création du PDP. Veuillez vérifier les champs obligatoires.")
        return redirect("plan_prevention:dashboard")



class PDPUpdateView(PDPEditPermissionMixin, UpdateView):
    """Modification d'un Plan de Prévention existant."""

    model = PlanPrevention
    form_class = PlanPreventionForm
    template_name = "plan_prevention/pdp_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)

        if self.request.POST:
            data["risques_formset"] = PlanPreventionRisqueFormSet(self.request.POST, instance=self.object)
        else:
            data["risques_formset"] = PlanPreventionRisqueFormSet(
                instance=self.object,
                queryset=self.object.pdp_risques.select_related("risque").order_by("ordre", "pk"),
            )
        data["can_add_risk"] = user_can_add_pdp_risk(self.request.user)
        data["risque_form"] = RisquePDPForm()
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        risques_formset = context["risques_formset"]

        with transaction.atomic():
            self.object = form.save()
            if risques_formset.is_valid():
                risques_formset.instance = self.object
                risques_formset.save()

        messages.success(self.request, f"Le Plan de Prévention {self.object.reference} a été mis à jour.")
        return redirect(self.object.get_absolute_url())


class PDPDetailView(PDPTenantScopedQuerySetMixin, DetailView):
    """Visualisation détaillée / Prévisualisation du PDP."""

    model = PlanPrevention
    template_name = "plan_prevention/pdp_detail.html"
    context_object_name = "pdp"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["risques"] = self.object.pdp_risques.select_related("risque").order_by("ordre", "pk")
        context["can_edit"] = user_can_edit_pdp(self.request.user, self.object)
        context["can_delete"] = user_can_delete_pdp(self.request.user, self.object)
        return context


class PDPDeleteView(PDPTenantScopedQuerySetMixin, DeleteView):
    """Suppression d'un Plan de Prévention."""

    model = PlanPrevention
    template_name = "plan_prevention/pdp_confirm_delete.html"
    success_url = reverse_lazy("plan_prevention:liste")

    def dispatch(self, request, *args, **kwargs):
        obj = self.get_object()
        if not user_can_delete_pdp(request.user, obj):
            raise PermissionDenied("Vous n'avez pas le droit de supprimer ce Plan de Prévention.")
        return super().dispatch(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        obj = self.get_object()
        ref = obj.reference
        response = super().delete(request, *args, **kwargs)
        messages.success(request, f"Le Plan de Prévention {ref} a été supprimé.")
        return response


@login_required
def export_pdp_pdf(request, pk):
    """Génération directe du fichier PDF officiel (3 pages) du PDP via WeasyPrint."""

    qs = PlanPrevention.objects.all()
    qs = filter_pdp_queryset_for_user(qs, request.user)
    pdp = get_object_or_404(qs, pk=pk)

    # Résolution du logo AB Serve
    logo_b64 = ""
    logo_path = static_finders.find("dist/img/abserveLogo.png")
    if not logo_path:
        candidate = settings.STATIC_ROOT / "dist" / "img" / "abserveLogo.png"
        if candidate.exists():
            logo_path = str(candidate)
    if not logo_path:
        candidate = settings.BASE_DIR / "assets" / "ab_serve_logo.png"
        if candidate.exists():
            logo_path = str(candidate)

    if logo_path and settings.BASE_DIR:
        try:
            with open(logo_path, "rb") as fh:
                logo_b64 = "data:image/png;base64," + base64.b64encode(fh.read()).decode("utf-8")
        except Exception as e:
            logger.warning(f"Erreur chargement logo PDF PDP: {e}")

    risques = pdp.pdp_risques.select_related("risque").order_by("ordre", "pk")

    context = {
        "pdp": pdp,
        "risques": risques,
        "logo_b64": logo_b64,
    }

    html_str = render_to_string("plan_prevention/pdf_plan_prevention.html", context)
    pdf_bytes = None

    if WeasyprintHTML is not None:
        try:
            base_url = f"file://{settings.BASE_DIR}/"
            pdf_bytes = WeasyprintHTML(string=html_str, base_url=base_url).write_pdf(pdf_version="1.4")
        except Exception as e:
            logger.warning(f"Weasyprint generation failed, falling back to xhtml2pdf: {e}")

    if pdf_bytes is None and pisa is not None:
        pdf_buffer = BytesIO()
        pisa_status = pisa.pisaDocument(BytesIO(html_str.encode("utf-8")), pdf_buffer)
        if not pisa_status.err:
            pdf_bytes = pdf_buffer.getvalue()

    if pdf_bytes is None:
        messages.error(request, "Impossible de générer le fichier PDF (moteur non disponible).")
        return render(request, "plan_prevention/pdf_plan_prevention.html", context)

    filename = f"{pdp.reference}_Plan_de_prevention.pdf"
    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@login_required
def api_customer_details(request, pk):
    """API endpoint retournant les détails d'un Customer pour auto-complétion du formulaire E.U."""
    customer = get_object_or_404(Customer, pk=pk)
    data = {
        "nom": customer.intitule or "",
        "adresse": f"{customer.adresse or ''} {customer.code_postal or ''} {customer.ville or ''}".strip(),
        "telephone": customer.telephone or "",
    }
    return JsonResponse(data)


@login_required
def api_create_risque(request):
    """API endpoint permettant la création d'un RisquePDP (Réservé à Administrateur, RO, Auditeur, Superuser)."""
    if not user_can_add_pdp_risk(request.user):
        return JsonResponse({
            "success": False,
            "error": "Accès non autorisé. Seuls Administrateur, RO, Auditeur et Superuser peuvent créer de nouveaux risques."
        }, status=403)

    if request.method == "POST":
        form = RisquePDPForm(request.POST)
        if form.is_valid():
            r_obj = form.save()
            return JsonResponse({
                "success": True,
                "id": r_obj.pk,
                "code": r_obj.code,
                "titre": r_obj.titre,
                "text": str(r_obj),
                "description": r_obj.description,
                "categorie": r_obj.categorie,
            })
        else:
            return JsonResponse({"success": False, "errors": form.errors}, status=400)

    return JsonResponse({"success": False, "error": "Méthode non autorisée"}, status=405)


class RisqueListView(ListView):
    """Vue dédiée au Catalogue Global des Risques PDP."""

    model = RisquePDP
    template_name = "plan_prevention/risque_list.html"
    context_object_name = "risques"
    paginate_by = 30

    def get_queryset(self):
        qs = RisquePDP.objects.filter(est_actif=True)
        query = self.request.GET.get("q", "").strip()
        categorie = self.request.GET.get("categorie", "").strip()

        if query:
            qs = qs.filter(
                Q(titre__icontains=query)
                | Q(code__icontains=query)
                | Q(description__icontains=query)
                | Q(categorie__icontains=query)
                | Q(mesures_prevention_recommandees__icontains=query)
            )
        if categorie:
            qs = qs.filter(categorie__iexact=categorie)

        return qs.order_by("ordre", "code")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context["can_add_risk"] = user_can_add_pdp_risk(user)
        if context["can_add_risk"]:
            context["risque_form"] = RisquePDPForm()

        all_risques = RisquePDP.objects.filter(est_actif=True)
        context["total_risques"] = all_risques.count()
        context["categories_list"] = sorted(
            list(set(RisquePDP.objects.exclude(categorie="").values_list("categorie", flat=True)))
        )
        return context
