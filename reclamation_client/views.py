"""Vues du module Réclamation Client."""

import base64
import json
import os
from datetime import date as date_cls, timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import models
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, DetailView, ListView, TemplateView, UpdateView

from accident_travail.models import ActionCorrective
from accounts.models import Site, Societe

from .forms import (
    ActionPermanenteD6FormSet,
    ActionTestD5FormSet,
    AnalyseCausesDoubleAxeForm,
    CapitalisationSMQSD7Form,
    ClotureRecevabiliteD8Form,
    DescriptionQQOQCCPForm,
    FicheIncidentDoc05Form,
    MesureConservatoireD3FormSet,
    Participant8DFormSet,
    ReclamationHeaderForm,
    ReclamationQuickCreateForm,
)
from .models import (
    ActionPermanenteD6,
    ActionTestD5,
    AnalyseCausesDoubleAxeD4,
    CapitalisationSMQSD7,
    ClotureRecevabiliteD8,
    DescriptionQQOQCCP,
    FicheIncidentDoc05,
    MesureConservatoireD3,
    Participant8D,
    ReclamationClient,
)

class ReclamationDashboardView(LoginRequiredMixin, TemplateView):
    """Dashboard de pilotage QSE des Réclamations Client & Incidents (Industrial Quality Management)."""

    template_name = "reclamation_client/dashboard.html"

    def get(self, request, *args, **kwargs):
        if request.headers.get("x-requested-with") == "XMLHttpRequest" or request.GET.get("ajax") == "1":
            today = timezone.now().date()
            selected_type = request.GET.get("type_signalement", "").strip()
            selected_societe = request.GET.get("societe_id", "").strip()
            selected_site = request.GET.get("site_id", "").strip()
            selected_statut = request.GET.get("statut", "").strip()
            selected_periode = request.GET.get("periode", "all").strip()

            qs = ReclamationClient.objects.all().select_related("site", "societe")
            if selected_type:
                qs = qs.filter(type_signalement=selected_type)
            if selected_societe and selected_societe.isdigit():
                qs = qs.filter(societe_id=int(selected_societe))
            if selected_site and selected_site.isdigit():
                qs = qs.filter(site_id=int(selected_site))
            if selected_statut:
                qs = qs.filter(statut=selected_statut)

            if selected_periode == "30d":
                qs = qs.filter(date_alerte_client__gte=today - timedelta(days=30))
            elif selected_periode == "90d":
                qs = qs.filter(date_alerte_client__gte=today - timedelta(days=90))
            elif selected_periode == "year":
                qs = qs.filter(date_alerte_client__year=today.year)

            evolution_periode = request.GET.get("evolution_periode", "12m").strip()
            date_debut_val = request.GET.get("date_debut", "").strip()
            date_fin_val = request.GET.get("date_fin", "").strip()

            mois_labels, counts_r, counts_i, counts_ai, evolution_title_suffix, evolution_error = self._get_evolution_chart_data(
                qs, today, evolution_periode, date_debut_val, date_fin_val
            )

            has_evolution_data = any(x > 0 for x in counts_r + counts_i + counts_ai)

            if evolution_error:
                return JsonResponse({
                    "success": False,
                    "error": evolution_error,
                    "title_suffix": evolution_title_suffix,
                })

            return JsonResponse({
                "success": True,
                "labels": mois_labels,
                "data_r": counts_r,
                "data_i": counts_i,
                "data_ai": counts_ai,
                "title_suffix": evolution_title_suffix,
                "has_data": has_evolution_data,
                "error": None,
            })

        return super().get(request, *args, **kwargs)

    def _get_evolution_chart_data(self, qs, today, evolution_periode, date_debut_str, date_fin_str):
        mois_labels = []
        counts_r = []
        counts_i = []
        counts_ai = []
        evolution_title_suffix = "12 derniers mois"
        evolution_error = None

        if evolution_periode == "7d":
            evolution_title_suffix = "7 derniers jours"
            for i in range(6, -1, -1):
                dt = today - timedelta(days=i)
                mois_labels.append(dt.strftime("%d/%m"))
                counts_r.append(qs.filter(type_signalement="R", date_alerte_client=dt).count())
                counts_i.append(qs.filter(type_signalement="I", date_alerte_client=dt).count())
                counts_ai.append(qs.filter(type_signalement="AI", date_alerte_client=dt).count())

        elif evolution_periode == "30d":
            evolution_title_suffix = "30 derniers jours"
            for i in range(29, -1, -1):
                dt = today - timedelta(days=i)
                mois_labels.append(dt.strftime("%d/%m"))
                counts_r.append(qs.filter(type_signalement="R", date_alerte_client=dt).count())
                counts_i.append(qs.filter(type_signalement="I", date_alerte_client=dt).count())
                counts_ai.append(qs.filter(type_signalement="AI", date_alerte_client=dt).count())

        elif evolution_periode == "3m":
            evolution_title_suffix = "3 derniers mois"
            for i in range(2, -1, -1):
                year = today.year
                month = today.month - i
                while month <= 0:
                    month += 12
                    year -= 1
                mois_labels.append(f"{month:02d}/{year}")
                counts_r.append(qs.filter(type_signalement="R", date_alerte_client__year=year, date_alerte_client__month=month).count())
                counts_i.append(qs.filter(type_signalement="I", date_alerte_client__year=year, date_alerte_client__month=month).count())
                counts_ai.append(qs.filter(type_signalement="AI", date_alerte_client__year=year, date_alerte_client__month=month).count())

        elif evolution_periode == "6m":
            evolution_title_suffix = "6 derniers mois"
            for i in range(5, -1, -1):
                year = today.year
                month = today.month - i
                while month <= 0:
                    month += 12
                    year -= 1
                mois_labels.append(f"{month:02d}/{year}")
                counts_r.append(qs.filter(type_signalement="R", date_alerte_client__year=year, date_alerte_client__month=month).count())
                counts_i.append(qs.filter(type_signalement="I", date_alerte_client__year=year, date_alerte_client__month=month).count())
                counts_ai.append(qs.filter(type_signalement="AI", date_alerte_client__year=year, date_alerte_client__month=month).count())

        elif evolution_periode == "year":
            evolution_title_suffix = "Cette année"
            for month in range(1, 13):
                mois_labels.append(f"{month:02d}/{today.year}")
                counts_r.append(qs.filter(type_signalement="R", date_alerte_client__year=today.year, date_alerte_client__month=month).count())
                counts_i.append(qs.filter(type_signalement="I", date_alerte_client__year=today.year, date_alerte_client__month=month).count())
                counts_ai.append(qs.filter(type_signalement="AI", date_alerte_client__year=today.year, date_alerte_client__month=month).count())

        elif evolution_periode == "custom":
            if not date_debut_str or not date_fin_str:
                evolution_error = "Veuillez renseigner les dates de début et de fin."
            else:
                try:
                    d_start = date_cls.fromisoformat(date_debut_str)
                    d_end = date_cls.fromisoformat(date_fin_str)

                    if d_start > today or d_end > today:
                        evolution_error = "Une date future n'est pas autorisée."
                    elif d_start > d_end:
                        evolution_error = "La date de début doit être antérieure ou égale à la date de fin."
                    else:
                        evolution_title_suffix = f"{d_start.strftime('%d/%m/%Y')} → {d_end.strftime('%d/%m/%Y')}"
                        delta_days = (d_end - d_start).days + 1

                        if delta_days <= 31:
                            for i in range(delta_days):
                                dt = d_start + timedelta(days=i)
                                mois_labels.append(dt.strftime("%d/%m"))
                                counts_r.append(qs.filter(type_signalement="R", date_alerte_client=dt).count())
                                counts_i.append(qs.filter(type_signalement="I", date_alerte_client=dt).count())
                                counts_ai.append(qs.filter(type_signalement="AI", date_alerte_client=dt).count())
                        else:
                            cur = date_cls(d_start.year, d_start.month, 1)
                            end_cur = date_cls(d_end.year, d_end.month, 1)
                            while cur <= end_cur:
                                mois_labels.append(f"{cur.month:02d}/{cur.year}")
                                counts_r.append(qs.filter(type_signalement="R", date_alerte_client__year=cur.year, date_alerte_client__month=cur.month).count())
                                counts_i.append(qs.filter(type_signalement="I", date_alerte_client__year=cur.year, date_alerte_client__month=cur.month).count())
                                counts_ai.append(qs.filter(type_signalement="AI", date_alerte_client__year=cur.year, date_alerte_client__month=cur.month).count())

                                if cur.month == 12:
                                    cur = date_cls(cur.year + 1, 1, 1)
                                else:
                                    cur = date_cls(cur.year, cur.month + 1, 1)
                except Exception:
                    evolution_error = "Format de date invalide."

        if (evolution_periode == "12m" or not mois_labels) and not evolution_error:
            evolution_title_suffix = "12 derniers mois"
            mois_labels = []
            counts_r = []
            counts_i = []
            counts_ai = []
            for i in range(11, -1, -1):
                year = today.year
                month = today.month - i
                while month <= 0:
                    month += 12
                    year -= 1
                mois_labels.append(f"{month:02d}/{year}")
                counts_r.append(qs.filter(type_signalement="R", date_alerte_client__year=year, date_alerte_client__month=month).count())
                counts_i.append(qs.filter(type_signalement="I", date_alerte_client__year=year, date_alerte_client__month=month).count())
                counts_ai.append(qs.filter(type_signalement="AI", date_alerte_client__year=year, date_alerte_client__month=month).count())

        return mois_labels, counts_r, counts_i, counts_ai, evolution_title_suffix, evolution_error

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.now().date()

        # Filter parameters from GET
        selected_type = self.request.GET.get("type_signalement", "").strip()
        selected_societe = self.request.GET.get("societe_id", "").strip()
        selected_site = self.request.GET.get("site_id", "").strip()
        selected_statut = self.request.GET.get("statut", "").strip()
        selected_periode = self.request.GET.get("periode", "all").strip()

        qs = ReclamationClient.objects.all().select_related("site", "societe")

        if selected_type:
            qs = qs.filter(type_signalement=selected_type)
        if selected_societe and selected_societe.isdigit():
            qs = qs.filter(societe_id=int(selected_societe))
        if selected_site and selected_site.isdigit():
            qs = qs.filter(site_id=int(selected_site))
        if selected_statut:
            qs = qs.filter(statut=selected_statut)

        if selected_periode == "30d":
            qs = qs.filter(date_alerte_client__gte=today - timedelta(days=30))
        elif selected_periode == "90d":
            qs = qs.filter(date_alerte_client__gte=today - timedelta(days=90))
        elif selected_periode == "year":
            qs = qs.filter(date_alerte_client__year=today.year)

        # 1. 8 KPI Metrics & Percentages
        total_reclamations = qs.count()
        nb_type_r = qs.filter(type_signalement=ReclamationClient.TYPE_RECLAMATION).count()
        nb_type_i = qs.filter(type_signalement=ReclamationClient.TYPE_INCIDENT).count()
        nb_type_ai = qs.filter(type_signalement=ReclamationClient.TYPE_AMELIORATION).count()

        pct_type_r = round((nb_type_r / total_reclamations * 100), 1) if total_reclamations > 0 else 0
        pct_type_i = round((nb_type_i / total_reclamations * 100), 1) if total_reclamations > 0 else 0
        pct_type_ai = round((nb_type_ai / total_reclamations * 100), 1) if total_reclamations > 0 else 0

        reclamations_ouvertes = qs.exclude(statut=ReclamationClient.STATUT_CLOTURE).count()
        reclamations_cloturees = qs.filter(statut=ReclamationClient.STATUT_CLOTURE).count()

        # Actions D6 (utilisant le modèle partagé ActionCorrective)
        actions = ActionCorrective.objects.filter(reclamation__in=qs)
        total_actions = actions.count()
        actions_non_demarrees = actions.filter(statut="non_demarre").count()
        actions_en_cours = actions.filter(statut="en_cours").count()
        actions_realisees = actions.filter(statut="realise").count()
        actions_verifiees = actions.filter(statut="verifie").count()
        actions_en_retard = actions.filter(delai__lt=today).exclude(statut="verifie").count()

        pct_actions_en_cours = round((actions_en_cours / total_actions * 100), 1) if total_actions > 0 else 0
        pct_actions_realisees = round((actions_realisees / total_actions * 100), 1) if total_actions > 0 else 0
        pct_actions_verifiees = round((actions_verifiees / total_actions * 100), 1) if total_actions > 0 else 0
        pct_actions_non_demarrees = round((actions_non_demarrees / total_actions * 100), 1) if total_actions > 0 else 0
        pct_actions_en_retard = round((actions_en_retard / total_actions * 100), 1) if total_actions > 0 else 0

        # 2. Recevabilité P05 §5
        clotures = ClotureRecevabiliteD8.objects.filter(reclamation__in=qs)
        nb_recevables = clotures.filter(statut_recevabilite=ClotureRecevabiliteD8.RECEVABILITE_RECEVABLE).count()
        nb_non_recevables = clotures.filter(statut_recevabilite=ClotureRecevabiliteD8.RECEVABILITE_NON_RECEVABLE).count()
        nb_partiels = clotures.filter(statut_recevabilite=ClotureRecevabiliteD8.RECEVABILITE_PARTIEL).count()
        total_recevabilite = nb_recevables + nb_non_recevables + nb_partiels
        has_recevabilite_data = total_recevabilite > 0

        pct_recevables = round((nb_recevables / total_recevabilite * 100), 1) if total_recevabilite > 0 else 0
        pct_non_recevables = round((nb_non_recevables / total_recevabilite * 100), 1) if total_recevabilite > 0 else 0
        pct_partiels = round((nb_partiels / total_recevabilite * 100), 1) if total_recevabilite > 0 else 0

        # 3. Avancement des dossiers (Process Funnel Workflow)
        nb_phase_d1_d3 = qs.filter(statut=ReclamationClient.STATUT_D1_D3).count()
        nb_phase_d4_d6 = qs.filter(statut=ReclamationClient.STATUT_D4_D6).count()
        nb_phase_d7_d8 = qs.filter(statut=ReclamationClient.STATUT_D7_D8).count()
        nb_phase_cloture = qs.filter(statut=ReclamationClient.STATUT_CLOTURE).count()
        has_workflow_data = total_reclamations > 0

        pct_phase_d1_d3 = round((nb_phase_d1_d3 / total_reclamations * 100), 1) if total_reclamations > 0 else 0
        pct_phase_d4_d6 = round((nb_phase_d4_d6 / total_reclamations * 100), 1) if total_reclamations > 0 else 0
        pct_phase_d7_d8 = round((nb_phase_d7_d8 / total_reclamations * 100), 1) if total_reclamations > 0 else 0
        pct_phase_cloture = round((nb_phase_cloture / total_reclamations * 100), 1) if total_reclamations > 0 else 0

        # 4. Évolution (par type R / I / AI) avec choix dynamique de période
        evolution_periode = self.request.GET.get("evolution_periode", "12m").strip()
        date_debut_val = self.request.GET.get("date_debut", "").strip()
        date_fin_val = self.request.GET.get("date_fin", "").strip()

        mois_labels, counts_r, counts_i, counts_ai, evolution_title_suffix, evolution_error = self._get_evolution_chart_data(
            qs, today, evolution_periode, date_debut_val, date_fin_val
        )

        has_type_data = (nb_type_r + nb_type_i + nb_type_ai) > 0
        has_evolution_data = any(x > 0 for x in counts_r + counts_i + counts_ai)
        has_actions_data = total_actions > 0

        # 5. Top Clients & Top Sites
        top_clients = list(
            qs.exclude(client_nom="")
            .values("client_nom")
            .annotate(total=models.Count("id"))
            .order_by("-total")[:5]
        )

        top_sites = list(
            qs.filter(site__isnull=False)
            .values("site__nom")
            .annotate(total=models.Count("id"))
            .order_by("-total")[:5]
        )

        # 6. Âge des dossiers ouverts
        dossiers_ouverts_qs = qs.exclude(statut=ReclamationClient.STATUT_CLOTURE)
        age_0_7 = 0
        age_8_30 = 0
        age_31_60 = 0
        age_plus_60 = 0

        for r in dossiers_ouverts_qs:
            dt = r.date_alerte_client or r.date_ouverture
            if dt:
                days = (today - dt).days
                if days <= 7:
                    age_0_7 += 1
                elif days <= 30:
                    age_8_30 += 1
                elif days <= 60:
                    age_31_60 += 1
                else:
                    age_plus_60 += 1

        # 7. Points nécessitant une attention (Critical Attention Points)
        attention_points = []
        for r in dossiers_ouverts_qs.order_by("date_alerte_client", "id"):
            dt = r.date_alerte_client or r.date_ouverture
            age_days = (today - dt).days if dt else 0
            overdue_acts = actions.filter(reclamation=r, delai__lt=today).exclude(statut="verifie").count()

            if overdue_acts > 0:
                attention_points.append({
                    "reclamation": r,
                    "reason": f"{overdue_acts} action(s) en retard",
                    "badge_class": "badge-danger",
                    "age": age_days,
                })
            elif age_days > 30:
                attention_points.append({
                    "reclamation": r,
                    "reason": f"Ouvert depuis {age_days} jours",
                    "badge_class": "badge-warning text-dark",
                    "age": age_days,
                })
            elif r.statut == "d1_d3" and age_days > 14:
                attention_points.append({
                    "reclamation": r,
                    "reason": f"Prise en charge (D1-D3) depuis {age_days}j",
                    "badge_class": "badge-info",
                    "age": age_days,
                })

        # 8. Derniers Signalements (5 items)
        recent_reclamations = list(qs.select_related("site", "societe").order_by("-date_alerte_client", "-id")[:5])

        # Dropdown options
        societes = Societe.objects.all()
        sites = Site.objects.all()

        context.update({
            # Filters
            "today": today,
            "selected_type": selected_type,
            "selected_societe": selected_societe,
            "selected_site": selected_site,
            "selected_statut": selected_statut,
            "selected_periode": selected_periode,
            "evolution_periode": evolution_periode,
            "date_debut_val": date_debut_val,
            "date_fin_val": date_fin_val,
            "evolution_title_suffix": evolution_title_suffix,
            "evolution_error": evolution_error,
            "societes": societes,
            "sites": sites,
            "statut_choices": ReclamationClient.STATUT_CHOICES,

            # 8 KPI Metrics & Percentages
            "total_reclamations": total_reclamations,
            "nb_type_r": nb_type_r,
            "nb_type_i": nb_type_i,
            "nb_type_ai": nb_type_ai,
            "pct_type_r": pct_type_r,
            "pct_type_i": pct_type_i,
            "pct_type_ai": pct_type_ai,
            "reclamations_ouvertes": reclamations_ouvertes,
            "reclamations_cloturees": reclamations_cloturees,
            "actions_en_cours": actions_en_cours,
            "actions_en_retard": actions_en_retard,

            # Workflow Pipeline
            "nb_phase_d1_d3": nb_phase_d1_d3,
            "nb_phase_d4_d6": nb_phase_d4_d6,
            "nb_phase_d7_d8": nb_phase_d7_d8,
            "nb_phase_cloture": nb_phase_cloture,
            "pct_phase_d1_d3": pct_phase_d1_d3,
            "pct_phase_d4_d6": pct_phase_d4_d6,
            "pct_phase_d7_d8": pct_phase_d7_d8,
            "pct_phase_cloture": pct_phase_cloture,

            # Recevabilité
            "total_recevabilite": total_recevabilite,
            "nb_recevables": nb_recevables,
            "nb_non_recevables": nb_non_recevables,
            "nb_partiels": nb_partiels,
            "pct_recevables": pct_recevables,
            "pct_non_recevables": pct_non_recevables,
            "pct_partiels": pct_partiels,

            # Actions
            "total_actions": total_actions,
            "actions_non_demarrees": actions_non_demarrees,
            "actions_realisees": actions_realisees,
            "actions_verifiees": actions_verifiees,
            "pct_actions_en_cours": pct_actions_en_cours,
            "pct_actions_realisees": pct_actions_realisees,
            "pct_actions_verifiees": pct_actions_verifiees,
            "pct_actions_non_demarrees": pct_actions_non_demarrees,
            "pct_actions_en_retard": pct_actions_en_retard,

            # Rankings & Aging
            "top_clients": top_clients,
            "top_sites": top_sites,
            "age_0_7": age_0_7,
            "age_8_30": age_8_30,
            "age_31_60": age_31_60,
            "age_plus_60": age_plus_60,
            "attention_points": attention_points[:6],
            "recent_reclamations": recent_reclamations,

            # Flags for Empty States
            "has_type_data": has_type_data,
            "has_evolution_data": has_evolution_data,
            "has_workflow_data": has_workflow_data,
            "has_recevabilite_data": has_recevabilite_data,
            "has_actions_data": has_actions_data,
            "has_clients_data": len(top_clients) > 0,
            "has_sites_data": len(top_sites) > 0,
            "has_attention_data": len(attention_points) > 0,
            "has_recent_data": len(recent_reclamations) > 0,

            # Chart JSONs
            "chart_labels_json": json.dumps(mois_labels),
            "chart_data_r_json": json.dumps(counts_r),
            "chart_data_i_json": json.dumps(counts_i),
            "chart_data_ai_json": json.dumps(counts_ai),
            "create_form": ReclamationQuickCreateForm(is_admin=self.request.user.is_superuser or self.request.user.is_staff),
        })
        return context


class ReclamationListView(LoginRequiredMixin, ListView):
    """Registre de suivi des réclamations et incidents (P05)."""

    model = ReclamationClient
    template_name = "reclamation_client/liste.html"
    context_object_name = "reclamations"
    paginate_by = 25

    def get_queryset(self):
        qs = super().get_queryset().select_related("societe", "site", "created_by")
        type_sig = self.request.GET.get("type")
        statut = self.request.GET.get("statut")
        q = self.request.GET.get("q")

        if type_sig:
            qs = qs.filter(type_signalement=type_sig)
        if statut:
            qs = qs.filter(statut=statut)
        if q:
            qs = qs.filter(
                models.Q(reference__icontains=q) |
                models.Q(client_nom__icontains=q) |
                models.Q(numero_reclamation_client__icontains=q) |
                models.Q(description_piece__icontains=q)
            )
        return qs.order_by("-created_at", "-id")

    def get_context_data(self, **kwargs):
        if getattr(self, "object_list", None) is None:
            self.object_list = self.get_queryset()
        context = super().get_context_data(**kwargs)
        if "create_form" not in context:
            context["create_form"] = ReclamationQuickCreateForm(is_admin=self.request.user.is_superuser or self.request.user.is_staff)
        return context


class ReclamationCreateView(LoginRequiredMixin, CreateView):
    """Création rapide d'une réclamation / incident client (P05)."""

    model = ReclamationClient
    form_class = ReclamationQuickCreateForm
    template_name = "reclamation_client/form_create.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["is_admin"] = self.request.user.is_superuser or self.request.user.is_staff
        return kwargs

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        self.object = form.save()

        # Initialiser les conteneurs OneToOne D2, D4, D7, D8
        DescriptionQQOQCCP.objects.get_or_create(reclamation=self.object)
        AnalyseCausesDoubleAxeD4.objects.get_or_create(reclamation=self.object)
        CapitalisationSMQSD7.objects.get_or_create(reclamation=self.object)
        ClotureRecevabiliteD8.objects.get_or_create(reclamation=self.object)

        # Initialiser les 4 mesures conservatoires D3 par défaut
        types_d3 = ["tri_interne", "tri_externe", "repere_unitaire", "autre"]
        for t in types_d3:
            MesureConservatoireD3.objects.get_or_create(reclamation=self.object, type_mesure=t)

        # Initialiser FicheIncidentDoc05 pour Doc.05
        FicheIncidentDoc05.objects.get_or_create(
            reclamation=self.object,
            defaults={
                "redacteur": self.request.user.get_full_name() or self.request.user.username,
                "date_detection": self.object.date_alerte_client,
                "date_ouverture": self.object.date_ouverture,
                "site_concerne": self.object.site.nom if self.object.site else "",
            }
        )

        if self.object.mode_traitement == ReclamationClient.MODE_8D:
            messages.success(self.request, f"Réclamation {self.object.reference} créée avec succès. Vous pouvez éditer le rapport 8D.")
            return redirect("reclamation:update_8d", pk=self.object.pk)
        else:
            messages.success(self.request, f"Signalement {self.object.reference} ({self.object.get_mode_traitement_display()}) enregistré avec succès.")
            return redirect("reclamation:update_doc05", pk=self.object.pk)

    def form_invalid(self, form):
        messages.error(self.request, "Erreur dans la création de la réclamation. Veuillez vérifier les champs indiqués.")
        list_view = ReclamationListView()
        list_view.setup(self.request)
        list_view.object_list = list_view.get_queryset()
        context = list_view.get_context_data(
            create_form=form,
            show_create_modal=True,
        )
        return render(self.request, list_view.template_name, context)


class ReclamationDetailView(LoginRequiredMixin, DetailView):
    """Vue détaillée / Synthèse du dossier 8D / Doc 05."""

    model = ReclamationClient
    template_name = "reclamation_client/detail.html"
    context_object_name = "reclamation"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        rec = self.object
        context["participants"] = rec.participants.all()
        context["qqoqccp"] = getattr(rec, "qqoqccp", None)
        context["mesures_d3"] = rec.mesures_conservatoires.all()
        context["analyse_d4"] = getattr(rec, "analyse_causes_d4", None)
        context["actions_tests"] = rec.actions_tests.all()
        actions_permanentes = rec.actions_correctives.all()
        if not actions_permanentes.exists():
            actions_permanentes = rec.actions_permanentes.all()
        context["actions_permanentes"] = actions_permanentes
        context["capitalisation_d7"] = getattr(rec, "capitalisation_d7", None)
        context["cloture_d8"] = getattr(rec, "cloture_d8", None)
        context["fiche_doc05"] = getattr(rec, "fiche_doc05", None)
        return context


@login_required
def reclamation_update_8d(request, pk):
    """Éditeur complet du Rapport 8D (Doc 83) multi-onglets D1 à D8."""

    reclamation = get_object_or_404(ReclamationClient, pk=pk)

    if reclamation.mode_traitement != ReclamationClient.MODE_8D:
        messages.info(request, f"Ce dossier ({reclamation.get_type_signalement_display()}) est géré via une Fiche d'incident.")
        return redirect("reclamation:update_doc05", pk=reclamation.pk)

    qqoqccp, _ = DescriptionQQOQCCP.objects.get_or_create(reclamation=reclamation)
    analyse_d4, _ = AnalyseCausesDoubleAxeD4.objects.get_or_create(reclamation=reclamation)
    capitalisation_d7, _ = CapitalisationSMQSD7.objects.get_or_create(reclamation=reclamation)
    cloture_d8, _ = ClotureRecevabiliteD8.objects.get_or_create(reclamation=reclamation)

    # Assurer présence des 4 mesures conservatoires D3
    for t in ["tri_interne", "tri_externe", "repere_unitaire", "autre"]:
        MesureConservatoireD3.objects.get_or_create(reclamation=reclamation, type_mesure=t)

    is_admin = request.user.is_superuser or request.user.is_staff
    if request.method == "POST":
        header_form = ReclamationHeaderForm(request.POST, instance=reclamation, is_admin=is_admin)
        qqoqccp_form = DescriptionQQOQCCPForm(request.POST, instance=qqoqccp)
        analyse_d4_form = AnalyseCausesDoubleAxeForm(request.POST, instance=analyse_d4)
        capitalisation_d7_form = CapitalisationSMQSD7Form(request.POST, instance=capitalisation_d7)
        cloture_d8_form = ClotureRecevabiliteD8Form(request.POST, instance=cloture_d8)

        participants_formset = Participant8DFormSet(request.POST, instance=reclamation, prefix="participants")
        mesures_d3_formset = MesureConservatoireD3FormSet(request.POST, instance=reclamation, prefix="mesures_d3")
        actions_tests_formset = ActionTestD5FormSet(request.POST, instance=reclamation, prefix="actions_tests")
        actions_permanentes_formset = ActionPermanenteD6FormSet(request.POST, instance=reclamation, prefix="actions_perm")

        # Sauvegarde 5 Pourquoi JSON (depuis formulaire dynamique)
        pourquoi_non_detection_raw = request.POST.get("pourquoi_non_detection_json", "[]")
        pourquoi_technique_raw = request.POST.get("pourquoi_technique_json", "[]")
        try:
            analyse_d4.pourquoi_non_detection = json.loads(pourquoi_non_detection_raw)
            analyse_d4.pourquoi_technique = json.loads(pourquoi_technique_raw)
        except Exception:
            pass

        if (
            header_form.is_valid() and qqoqccp_form.is_valid() and
            analyse_d4_form.is_valid() and capitalisation_d7_form.is_valid() and
            cloture_d8_form.is_valid() and participants_formset.is_valid() and
            mesures_d3_formset.is_valid() and actions_tests_formset.is_valid() and
            actions_permanentes_formset.is_valid()
        ):
            header_form.save()
            qqoqccp_form.save()
            analyse_d4_form.save()
            analyse_d4.save()
            capitalisation_d7_form.save()
            cloture_d8_form.save()
            participants_formset.save()
            mesures_d3_formset.save()
            actions_tests_formset.save()
            actions_permanentes_formset.save()

            messages.success(request, f"Dossier 8D {reclamation.reference} enregistré avec succès.")
            return redirect("reclamation:liste")
        else:
            messages.error(request, "Certains champs du formulaire contiennent des erreurs. Veuillez vérifier.")
    else:
        header_form = ReclamationHeaderForm(instance=reclamation, is_admin=is_admin)
        qqoqccp_form = DescriptionQQOQCCPForm(instance=qqoqccp)
        analyse_d4_form = AnalyseCausesDoubleAxeForm(instance=analyse_d4)
        capitalisation_d7_form = CapitalisationSMQSD7Form(instance=capitalisation_d7)
        cloture_d8_form = ClotureRecevabiliteD8Form(instance=cloture_d8)

        participants_formset = Participant8DFormSet(instance=reclamation, prefix="participants")
        mesures_d3_formset = MesureConservatoireD3FormSet(instance=reclamation, prefix="mesures_d3")
        actions_tests_formset = ActionTestD5FormSet(instance=reclamation, prefix="actions_tests")
        actions_permanentes_formset = ActionPermanenteD6FormSet(instance=reclamation, prefix="actions_perm")

    context = {
        "reclamation": reclamation,
        "header_form": header_form,
        "qqoqccp_form": qqoqccp_form,
        "analyse_d4_form": analyse_d4_form,
        "capitalisation_d7_form": capitalisation_d7_form,
        "cloture_d8_form": cloture_d8_form,
        "participants_formset": participants_formset,
        "mesures_d3_formset": mesures_d3_formset,
        "actions_tests_formset": actions_tests_formset,
        "actions_permanentes_formset": actions_permanentes_formset,
        "pourquoi_non_detection_json": json.dumps(analyse_d4.pourquoi_non_detection),
        "pourquoi_technique_json": json.dumps(analyse_d4.pourquoi_technique),
    }
    return render(request, "reclamation_client/form_8d.html", context)


@login_required
def reclamation_update_doc05(request, pk):
    """Éditeur dédié pour Fiche Incident Client (I) & Fiche d'Amélioration Interne (AI) - Doc 05."""

    reclamation = get_object_or_404(ReclamationClient, pk=pk)

    if reclamation.mode_traitement == ReclamationClient.MODE_8D:
        messages.info(request, "Ce dossier est une Réclamation gérée via un Rapport 8D.")
        return redirect("reclamation:update_8d", pk=reclamation.pk)

    fiche_doc05, _ = FicheIncidentDoc05.objects.get_or_create(
        reclamation=reclamation,
        defaults={
            "redacteur": request.user.get_full_name() or request.user.username,
            "date_detection": reclamation.date_alerte_client,
            "date_ouverture": reclamation.date_ouverture,
            "site_concerne": reclamation.site.nom if reclamation.site else "",
        }
    )

    if request.method == "POST":
        doc05_form = FicheIncidentDoc05Form(request.POST, instance=fiche_doc05)

        pourquoi_json = request.POST.get("pourquoi_chains_json", "[]")
        mesures_immediates_json = request.POST.get("mesures_immediates_json", "[]")
        actions_correctives_json = request.POST.get("actions_correctives_json", "[]")

        try:
            fiche_doc05.pourquoi_chains = json.loads(pourquoi_json)
            fiche_doc05.mesures_immediates = json.loads(mesures_immediates_json)
            fiche_doc05.actions_correctives = json.loads(actions_correctives_json)
        except Exception:
            pass

        if doc05_form.is_valid():
            doc05_form.save()
            messages.success(request, f"Fiche Doc.05 {reclamation.reference} enregistrée avec succès.")
            return redirect("reclamation:liste")
        else:
            messages.error(request, "Certains champs contiennent des erreurs. Veuillez vérifier.")
    else:
        doc05_form = FicheIncidentDoc05Form(instance=fiche_doc05)

    context = {
        "reclamation": reclamation,
        "fiche_doc05": fiche_doc05,
        "doc05_form": doc05_form,
        "pourquoi_chains_json": json.dumps(fiche_doc05.pourquoi_chains),
        "mesures_immediates_json": json.dumps(fiche_doc05.mesures_immediates),
        "actions_correctives_json": json.dumps(fiche_doc05.actions_correctives),
    }
    return render(request, "reclamation_client/form_doc05.html", context)


@login_required
def autosave_reclamation_8d(request, pk):
    """Endpoint AJAX d'auto-sauvegarde brouillon."""

    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "POST requis"}, status=400)

    reclamation = get_object_or_404(ReclamationClient, pk=pk)
    try:
        # Auto-save minimal fields
        reclamation.updated_by = request.user
        reclamation.save()
        return JsonResponse({"status": "ok", "reference": reclamation.reference})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


from io import BytesIO
from django.template.loader import render_to_string
from xhtml2pdf import pisa


from .pdf_d4_generator import generate_d4_diagram_base64


@login_required
def reclamation_export_pdf_8d(request, pk):
    """Génération directe d'un fichier PDF binaire (Doc 83 Rapport 8D)."""

    reclamation = get_object_or_404(ReclamationClient, pk=pk)
    if reclamation.mode_traitement != ReclamationClient.MODE_8D:
        return redirect("reclamation:export_pdf_doc05", pk=reclamation.pk)

    d4 = getattr(reclamation, "analyse_causes_d4", None)
    d4_diagram_png = generate_d4_diagram_base64(d4)

    logo_path = os.path.join(settings.BASE_DIR, "assets", "ab_serve_logo.png")
    logo_base64 = ""
    if os.path.exists(logo_path):
        with open(logo_path, "rb") as img_f:
            logo_base64 = "data:image/png;base64," + base64.b64encode(img_f.read()).decode("utf-8")

    actions_permanentes = reclamation.actions_correctives.all()
    if not actions_permanentes.exists():
        actions_permanentes = reclamation.actions_permanentes.all()

    context = {
        "reclamation": reclamation,
        "participants": reclamation.participants.all(),
        "qqoqccp": getattr(reclamation, "qqoqccp", None),
        "mesures_d3": reclamation.mesures_conservatoires.all(),
        "analyse_d4": d4,
        "d4_diagram_png": d4_diagram_png,
        "logo_base64": logo_base64,
        "actions_tests": reclamation.actions_tests.all(),
        "actions_permanentes": actions_permanentes,
        "capitalisation_d7": getattr(reclamation, "capitalisation_d7", None),
        "cloture_d8": getattr(reclamation, "cloture_d8", None),
    }

    html_content = render_to_string("reclamation_client/rapport_8d_pdf.html", context)
    pdf_buffer = BytesIO()
    pisa_status = pisa.pisaDocument(BytesIO(html_content.encode("utf-8")), pdf_buffer)

    if not pisa_status.err:
        response = HttpResponse(pdf_buffer.getvalue(), content_type="application/pdf")
        filename = f"{reclamation.reference}_Rapport_8D.pdf"
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    return render(request, "reclamation_client/rapport_8d_pdf.html", context)


@login_required
def reclamation_export_pdf_doc05(request, pk):
    """Génération directe du PDF officiel Fiche Incident / FAI (Doc 05)."""

    reclamation = get_object_or_404(ReclamationClient, pk=pk)
    if reclamation.mode_traitement == ReclamationClient.MODE_8D:
        return redirect("reclamation:export_pdf_8d", pk=reclamation.pk)

    fiche_doc05, _ = FicheIncidentDoc05.objects.get_or_create(
        reclamation=reclamation,
        defaults={
            "redacteur": request.user.get_full_name() or request.user.username,
            "date_detection": reclamation.date_alerte_client,
            "date_ouverture": reclamation.date_ouverture,
            "site_concerne": reclamation.site.nom if reclamation.site else "",
        }
    )

    logo_path = os.path.join(settings.BASE_DIR, "assets", "ab_serve_logo.png")
    logo_base64 = ""
    if os.path.exists(logo_path):
        with open(logo_path, "rb") as img_f:
            logo_base64 = "data:image/png;base64," + base64.b64encode(img_f.read()).decode("utf-8")

    context = {
        "reclamation": reclamation,
        "fiche": fiche_doc05,
        "logo_base64": logo_base64,
    }

    html_content = render_to_string("reclamation_client/rapport_doc05_pdf.html", context)
    pdf_buffer = BytesIO()
    pisa_status = pisa.pisaDocument(BytesIO(html_content.encode("utf-8")), pdf_buffer)

    if not pisa_status.err:
        response = HttpResponse(pdf_buffer.getvalue(), content_type="application/pdf")
        filename = f"{reclamation.reference}_Fiche_Doc05.pdf"
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    return render(request, "reclamation_client/rapport_doc05_pdf.html", context)


@login_required
def api_evolution_chart_data(request):
    """API endpoint AJAX pour la mise à jour dynamique du graphique Évolution."""
    view = ReclamationDashboardView()
    view.request = request
    return view.get(request)





