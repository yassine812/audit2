"""Vues CBV du module audit interne."""

from __future__ import annotations

import logging
import re

from django.contrib import messages
from django.contrib.auth.decorators import login_required as login_required_fn
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db import DatabaseError, transaction
from django.db.models import Count, Q
from django.forms import modelform_factory
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import CreateView, DeleteView, DetailView, ListView, TemplateView, UpdateView

from .forms import (
    AuditForm,
    BaremeCotationForm,
    ChapitreNormeForm,
    CritereEvaluationForm,
    FormulaireAuditForm,
    LigneFormulaireForm,
    NormeDocumentForm,
    ReponseAuditForm,
    ReponseAuditFormSet,
    ResultatAuditForm,
    ThemeForm,
    NiveauxAttendusForm,
)
from .models import (
    Audit,
    AuditStatut,
    AuditType,
    BaremeCotation,
    ChapitreNorme,
    CritereEvaluation,
    FormulaireAudit,
    LigneFormulaire,
    NormeDocument,
    ReponseAudit,
    ResultatAudit,
    Theme,
    PreuveAttendue,
    PreuveAttendueType,
    NiveauxAttendus,
)
from .permissions import (
    CanCreateAuditMixin,
    CanUseAuditMixin,
    PermissionDeniedTemplateMixin,
    filter_allowed_types_for_create,
    filter_allowed_types_for_use,
    user_can_create_audit,
    user_can_use_audit,
)

from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator

logger = logging.getLogger(__name__)


class SafeDbOperationMixin:
    """Mixin d'erreur base de données avec message utilisateur."""

    def _handle_db_error(self, request, exc: Exception, fallback_url: str):
        logger.exception("Erreur DB: %s", exc)
        messages.error(request, "Une erreur base de données est survenue. Veuillez réessayer.")
        return redirect(fallback_url)

    def form_valid(self, form):
        try:
            with transaction.atomic():
                response = super().form_valid(form)
            messages.success(self.request, "Enregistrement effectué avec succès.")
            return response
        except DatabaseError as exc:
            return self._handle_db_error(self.request, exc, self.get_success_url())


class RoleRequiredMixin(PermissionDeniedTemplateMixin):
    """Contrôle d'accès simple par booléens de rôle utilisateur."""

    allowed_flags: tuple[str, ...] = tuple()

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            raise PermissionDenied
        if self.allowed_flags and not any(getattr(request.user, flag, False) for flag in self.allowed_flags):
            return self.render_forbidden(request)
        return super().dispatch(request, *args, **kwargs)


class SuperuserOnlyMixin(RoleRequiredMixin):
    allowed_flags = ("is_superuser",)


class SuperuserOrAuditeurMixin(RoleRequiredMixin):
    allowed_flags = ("is_superuser", "is_auditeur")


class Object404Mixin:
    """Force l'utilisation de `get_object_or_404` pour les vues objet."""

    def get_object(self, queryset=None):
        queryset = queryset or self.get_queryset()
        return get_object_or_404(queryset, pk=self.kwargs["pk"])


class DeactivateMixin:
    """
    Mixin for DeleteView: adds deactivation support.

    On GET (confirm page):
    - Checks if object is referenced by FK/M2M reverse relations
    - Passes `is_referenced` and `has_actif` to template context

    On POST:
    - `_action=deactivate` → sets object.actif = False (if model has actif field)
    - default POST → standard deletion
    """

    def _has_actif_field(self):
        """Return True if model exposes a real `actif` database field."""
        return any(getattr(field, "name", None) == "actif" for field in self.object._meta.fields)

    def _reference_details(self):
        """
                Return relation names that currently reference this object.

                Business rule: any existing FK/O2O/M2M usage means the instance is
                used and should not be hard-deleted.
        """
        from django.db.models import ManyToManyRel, ManyToOneRel, OneToOneRel

        obj = self.object
        relation_names: list[str] = []
        for rel in obj._meta.get_fields():
            if not isinstance(rel, (ManyToOneRel, ManyToManyRel, OneToOneRel)):
                continue

            accessor = rel.get_accessor_name()
            if not accessor:
                continue

            try:
                related_attr = getattr(obj, accessor)
                if hasattr(related_attr, "exists"):
                    if related_attr.exists():
                        relation_names.append(accessor)
                else:
                    if related_attr is not None:
                        relation_names.append(accessor)
            except Exception:
                continue

        return relation_names

    def _is_referenced(self):
        """Return True when object is used by at least one related instance."""
        return bool(self._reference_details())

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        relation_names = self._reference_details()
        ctx['is_referenced'] = self._is_referenced()
        ctx['reference_relations'] = relation_names
        ctx['has_actif'] = self._has_actif_field()
        return ctx

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        if request.POST.get('_action') == 'deactivate' and self._has_actif_field():
            self.object.actif = False
            self.object.save(update_fields=['actif'])
            messages.success(request, "L'élément a été désactivé avec succès.")
            return redirect(self.get_success_url())
        return super().post(request, *args, **kwargs)


# ============== Référentiel (superuser only) ==============


class NormeDocumentListView(LoginRequiredMixin, SuperuserOnlyMixin, ListView):
    model = NormeDocument
    template_name = "audit/referentiel/norme_list.html"
    paginate_by = 25

    def get_queryset(self):
        qs = NormeDocument.objects.filter(actif=True)
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(nom__icontains=q)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["used_norme_ids"] = set(
            ChapitreNorme.objects.exclude(norme__isnull=True)
            .values_list("norme_id", flat=True)
        )
        return context


class NormeDocumentCreateView(LoginRequiredMixin, SuperuserOnlyMixin, SafeDbOperationMixin, CreateView):
    model = NormeDocument
    form_class = NormeDocumentForm
    template_name = "audit/referentiel/form.html"
    success_url = reverse_lazy("audit:norme-list")


class NormeDocumentUpdateView(LoginRequiredMixin, SuperuserOnlyMixin, SafeDbOperationMixin, Object404Mixin, UpdateView):
    model = NormeDocument
    form_class = NormeDocumentForm
    template_name = "audit/referentiel/form.html"
    success_url = reverse_lazy("audit:norme-list")


class NormeDocumentDeleteView(LoginRequiredMixin, SuperuserOnlyMixin, DeactivateMixin, Object404Mixin, DeleteView):
    model = NormeDocument
    template_name = "audit/referentiel/confirm_delete.html"
    success_url = reverse_lazy("audit:norme-list")


class ChapitreNormeListView(LoginRequiredMixin, SuperuserOnlyMixin, ListView):
    model = ChapitreNorme
    template_name = "audit/referentiel/chapitre_list.html"
    paginate_by = 25

    def get_queryset(self):
        qs = ChapitreNorme.objects.filter(actif=True).select_related("norme")
        q = self.request.GET.get("q", "").strip()
        norme = self.request.GET.get("norme", "").strip()
        if q:
            qs = qs.filter(Q(reference__icontains=q) | Q(intitule__icontains=q) | Q(norme__nom__icontains=q))
        if norme:
            qs = qs.filter(norme_id=norme)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["normes"] = NormeDocument.objects.filter(actif=True)
        # Chapitre used if referenced by CritereEvaluation via M2M
        context["used_chapitre_ids"] = set(
            CritereEvaluation.objects.filter(chapitre_norme__isnull=False)
            .values_list("chapitre_norme__id", flat=True)
        )
        return context


class ChapitreNormeCreateView(LoginRequiredMixin, SuperuserOnlyMixin, SafeDbOperationMixin, CreateView):
    model = ChapitreNorme
    form_class = ChapitreNormeForm
    template_name = "audit/referentiel/form.html"
    success_url = reverse_lazy("audit:chapitre-list")


class ChapitreNormeUpdateView(LoginRequiredMixin, SuperuserOnlyMixin, SafeDbOperationMixin, Object404Mixin, UpdateView):
    model = ChapitreNorme
    form_class = ChapitreNormeForm
    template_name = "audit/referentiel/form.html"
    success_url = reverse_lazy("audit:chapitre-list")


class ChapitreNormeDeleteView(LoginRequiredMixin, SuperuserOnlyMixin, DeactivateMixin, Object404Mixin, DeleteView):
    model = ChapitreNorme
    template_name = "audit/referentiel/confirm_delete.html"
    success_url = reverse_lazy("audit:chapitre-list")


class ChapitreNormeDetailView(LoginRequiredMixin, View):
    """Page de consultation d’un chapitre de norme avec son PDF."""

    def get(self, request, pk):
        chapitre = get_object_or_404(
            ChapitreNorme.objects.select_related("norme"), pk=pk
        )
        return render(request, "audit/referentiel/chapitre_detail.html", {"object": chapitre})


class ThemeListView(LoginRequiredMixin, SuperuserOnlyMixin, ListView):
    model = Theme
    template_name = "audit/referentiel/theme_list.html"
    paginate_by = 25

    def get_queryset(self):
        qs = Theme.objects.filter(actif=True).annotate(critere_count=Count('criteres'))
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(Q(texte__icontains=q))
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Theme is used if referenced by any CritereEvaluation
        context["used_theme_ids"] = set(
            CritereEvaluation.objects.exclude(theme__isnull=True).values_list("theme_id", flat=True)
        )
        return context


class ThemeDetailView(LoginRequiredMixin, SuperuserOnlyMixin, DetailView):
    model = Theme
    template_name = "audit/referentiel/theme_detail.html"

    def get_queryset(self):
        return Theme.objects.prefetch_related(
            "criteres__preuves_attendues",
            "criteres__chapitre_norme__norme",
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # provide ordered criteres
        ctx['criteres'] = self.object.criteres.prefetch_related('preuves_attendues', 'chapitre_norme__norme')
        return ctx


class ThemeCreateView(LoginRequiredMixin, SuperuserOnlyMixin, SafeDbOperationMixin, CreateView):
    model = Theme
    form_class = ThemeForm
    template_name = "audit/referentiel/theme_form.html"
    success_url = reverse_lazy("audit:theme-list")

    def form_valid(self, form):
        self.object = form.save()
        # create new criteres if any (optional second step)
        new_criteres = self.request.POST.getlist("new_criteres[]")
        for texte in new_criteres:
            t = texte.strip()
            if not t:
                continue
            CritereEvaluation.objects.create(theme=self.object, texte=t)
        messages.success(self.request, "Thème créé avec succès.")
        return redirect(self.success_url)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['preuves'] = list(PreuveAttendue.objects.filter(actif=True).values('id', 'libelle'))
        context['chapitres_json'] = list(
            ChapitreNorme.objects.select_related('norme').filter(actif=True)
            .order_by('norme__nom', 'reference')
            .values('id', 'reference', 'intitule', 'num_page', 'norme__nom')
        )
        _criteres_qs = (
            CritereEvaluation.objects.select_related('theme')
            .prefetch_related('chapitre_norme', 'preuves_attendues')
            .filter(actif=True)
        )
        context['criteres_catalogue'] = [
            {
                'id': c.id,
                'texte': c.texte,
                'theme_id': c.theme_id,
                'theme__texte': c.theme.texte if c.theme else '',
                'chapitre_ids': list(c.chapitre_norme.values_list('id', flat=True)),
                'preuve_ids': list(c.preuves_attendues.values_list('id', flat=True)),
            }
            for c in _criteres_qs
        ]
        try:
            from django.contrib.admin.widgets import FilteredSelectMultiple
            qs = PreuveAttendue.objects.filter(actif=True)
            widget = FilteredSelectMultiple('Preuves', is_stacked=False)
            widget.choices = [(p.pk, p.libelle) for p in qs]
            proto_html = widget.render('new_criteres_preuves_proto', None, attrs={'id': 'id_new_criteres_preuves_proto'})
        except Exception:
            proto_html = ''
        context['preuves_proto'] = proto_html
        return context

@require_POST
def ajax_create_chapitre(request):
    """AJAX endpoint to create a ChapitreNorme (and optionally a NormeDocument).

    Expects POST fields: new_norme_nom, new_chapitre_reference, new_chapitre_intitule, new_chapitre_num_page
    Returns JSON: {ok: True, id: <chapitre_pk>, text: '<ref> - <intitule>'}
    """
    user = request.user
    if not user.is_authenticated or not user.is_superuser:
        return JsonResponse({"ok": False, "error": "Permission denied"}, status=403)

    # prefer an existing norme id if provided
    norme_id = request.POST.get("new_norme_id")
    nom_norme = request.POST.get("new_norme_nom", "").strip()
    ref = request.POST.get("new_chapitre_reference", "").strip()
    intitule = request.POST.get("new_chapitre_intitule", "").strip()
    page = request.POST.get("new_chapitre_num_page", "").strip()

    if not ref or not intitule:
        return JsonResponse({"ok": False, "error": "Référence et intitulé obligatoire"}, status=400)

    try:
        with transaction.atomic():
            norme_obj = None
            if norme_id:
                try:
                    norme_obj = NormeDocument.objects.get(pk=norme_id)
                except NormeDocument.DoesNotExist:
                    norme_obj = None
            elif nom_norme:
                norme_obj, _ = NormeDocument.objects.get_or_create(nom=nom_norme)
            chapitre = ChapitreNorme.objects.create(reference=ref, intitule=intitule, norme=norme_obj)
            if page:
                try:
                    chapitre.num_page = int(page)
                    chapitre.save()
                except ValueError:
                    pass
    except Exception as exc:
        logger.exception("Erreur création chapitre AJAX: %s", exc)
        return JsonResponse({"ok": False, "error": "Erreur serveur"}, status=500)

    return JsonResponse({"ok": True, "id": chapitre.pk, "text": f"{chapitre.reference} - {chapitre.intitule}"})


@require_POST
def ajax_create_theme(request):
    """Module-level AJAX: create Theme (validates with ThemeForm). Optionally create Norme/Chapitre and attach.

    Expects: texte, chapitre_norme (list of ids, optional), create_new_chapitre, new_norme_nom, new_chapitre_*
    Returns: {ok, id, edit_url}
    """
    if not request.user.is_authenticated or not request.user.is_superuser:
        return JsonResponse({"ok": False, "error": "Permission denied"}, status=403)

    data = request.POST.copy()
    theme_id = request.POST.get('theme_id')
    if theme_id:
        try:
            instance = Theme.objects.get(pk=theme_id)
        except Theme.DoesNotExist:
            return JsonResponse({"ok": False, "error": "Thème introuvable"}, status=404)
        form = ThemeForm(data, instance=instance)
    else:
        form = ThemeForm(data)
    texte = (request.POST.get('texte') or '').strip()
    if not texte:
        return JsonResponse({"ok": False, "errors": {"texte": ["Ce champ est obligatoire."]}}, status=400)
    if not form.is_valid():
        return JsonResponse({"ok": False, "errors": {k: v for k, v in form.errors.items()}}, status=400)
    try:
        with transaction.atomic():
            theme = form.save()
    except Exception as exc:
        logger.exception('Erreur création thème AJAX: %s', exc)
        return JsonResponse({"ok": False, "error": "Erreur serveur"}, status=500)
    edit_url = reverse('audit:theme-edit', args=[theme.pk])
    return JsonResponse({"ok": True, "id": theme.pk, "edit_url": edit_url})


@require_POST
def ajax_add_criteres(request):
    """Module-level AJAX: manage criteres for an existing theme.

    Supports:
    - create new criteres (`new_criteres[]`) with required preuves (`new_criteres_preuves[]`)
    - associate existing criteres (`existing_criteres_add_ids[]`)
    - disassociate criteres from current theme (`disaffect_criteres_ids[]`) without deleting
    """
    if not request.user.is_authenticated or not request.user.is_superuser:
        return JsonResponse({"ok": False, "error": "Permission denied"}, status=403)
    theme_id = request.POST.get('theme_id')
    if not theme_id:
        return JsonResponse({"ok": False, "error": "theme_id requis"}, status=400)
    try:
        theme = Theme.objects.get(pk=theme_id)
    except Theme.DoesNotExist:
        return JsonResponse({"ok": False, "error": "Thème introuvable"}, status=404)

    new_criteres = request.POST.getlist('new_criteres[]')
    new_preuves = request.POST.getlist('new_criteres_preuves[]')
    new_chapitres_raw = request.POST.getlist('new_criteres_chapitres[]')
    existing_add_ids = request.POST.getlist('existing_criteres_add_ids[]')
    disaffect_ids = request.POST.getlist('disaffect_criteres_ids[]')
    created = []
    attached = []
    disaffected = []

    # server validation for newly created criteria: texte + preuves required
    validation_errors = {}
    for i, texte in enumerate(new_criteres):
        t = (texte or '').strip()
        preuves_raw = new_preuves[i] if i < len(new_preuves) else ''
        has_any_preuve = bool((preuves_raw or '').strip())
        if not t and not has_any_preuve:
            # empty row: ignore
            continue
        if not t:
            validation_errors[f'new_criteres[{i}]'] = ['Le texte du critère est obligatoire.']
        if not has_any_preuve:
            validation_errors[f'new_criteres_preuves[{i}]'] = ['Au moins une preuve attendue est obligatoire.']
    if validation_errors:
        return JsonResponse({"ok": False, "errors": validation_errors}, status=400)

    try:
        with transaction.atomic():
            # attach selected existing criteria to this theme
            for cid in existing_add_ids:
                if not str(cid).strip():
                    continue
                crit = CritereEvaluation.objects.filter(pk=cid, actif=True).first()
                if not crit:
                    continue
                crit.theme = theme
                crit.save(update_fields=['theme'])
                attached.append(crit.pk)

            for i, texte in enumerate(new_criteres):
                t = texte.strip()
                if not t:
                    continue
                c = CritereEvaluation.objects.create(theme=theme, texte=t)
                # handle preuves: semicolon or comma separated list in corresponding index
                preuves_raw = ''
                if i < len(new_preuves):
                    preuves_raw = new_preuves[i] or ''
                if preuves_raw:
                    # split on ; or ,
                    parts = [p.strip() for p in re.split(r"[;,]", preuves_raw) if p.strip()]
                    for token in parts:
                        pa = None
                        if token.startswith('__new__:'):
                            lib_val = token[len('__new__:'):].strip()
                            if lib_val:
                                pa = PreuveAttendue.objects.filter(libelle__iexact=lib_val).first()
                                if not pa:
                                    pa = PreuveAttendue.objects.create(libelle=lib_val)
                        elif str(token).isdigit():
                            pa = PreuveAttendue.objects.filter(pk=int(token)).first()
                        else:
                            lib_val = token.strip()
                            if lib_val:
                                pa = PreuveAttendue.objects.filter(libelle__iexact=lib_val).first()
                                if not pa:
                                    pa = PreuveAttendue.objects.create(libelle=lib_val)
                        if pa:
                            c.preuves_attendues.add(pa)
                # assign chapitres
                chap_raw = new_chapitres_raw[i] if i < len(new_chapitres_raw) else ''
                chap_ids = [int(x) for x in chap_raw.split(',') if x.strip().isdigit()]
                if chap_ids:
                    c.chapitre_norme.set(chap_ids)
                created.append(c.pk)

            # disassociate criteria from this theme (without deleting)
            for cid in disaffect_ids:
                if not str(cid).strip():
                    continue
                crit = CritereEvaluation.objects.filter(pk=cid, theme=theme).first()
                if not crit:
                    continue
                crit.theme = None
                crit.save(update_fields=['theme'])
                disaffected.append(crit.pk)
    except Exception as exc:
        logger.exception('Erreur création critères AJAX: %s', exc)
        return JsonResponse({"ok": False, "error": "Erreur serveur"}, status=500)

    return JsonResponse({"ok": True, "created": created, "attached": attached, "disaffected": disaffected})


class ThemeUpdateView(LoginRequiredMixin, SuperuserOnlyMixin, SafeDbOperationMixin, Object404Mixin, UpdateView):
    model = Theme
    form_class = ThemeForm
    template_name = "audit/referentiel/theme_form.html"
    success_url = reverse_lazy("audit:theme-list")

    def form_valid(self, form):
        self.object = form.save()
        # create criteres if provided and attach preuves attendues
        new_criteres = self.request.POST.getlist("new_criteres[]")
        new_preuves = self.request.POST.getlist("new_criteres_preuves[]")
        for i, texte in enumerate(new_criteres):
            t = texte.strip()
            if not t:
                continue
            crit = CritereEvaluation.objects.create(theme=self.object, texte=t)
            preuves_raw = new_preuves[i] if i < len(new_preuves) else ''
            if preuves_raw:
                parts = [p.strip() for p in re.split(r"[;,]", preuves_raw) if p.strip()]
                for lib in parts:
                    pa = PreuveAttendue.objects.filter(libelle__iexact=lib).first()
                    if not pa:
                        pa = PreuveAttendue.objects.create(libelle=lib)
                    crit.preuves_attendues.add(pa)
        messages.success(self.request, "Thème mis à jour avec succès.")
        return redirect(self.success_url)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['preuves'] = list(PreuveAttendue.objects.filter(actif=True).values('id', 'libelle'))
        context['chapitres_json'] = list(
            ChapitreNorme.objects.select_related('norme').filter(actif=True)
            .order_by('norme__nom', 'reference')
            .values('id', 'reference', 'intitule', 'num_page', 'norme__nom')
        )
        context['criteres_catalogue'] = [
            {
                'id': c.id,
                'texte': c.texte,
                'theme_id': c.theme_id,
                'theme__texte': c.theme.texte if c.theme else '',
                'chapitre_ids': list(c.chapitre_norme.values_list('id', flat=True)),
                'preuve_ids': list(c.preuves_attendues.values_list('id', flat=True)),
            }
            for c in CritereEvaluation.objects.select_related('theme')
            .prefetch_related('chapitre_norme', 'preuves_attendues')
            .filter(actif=True)
        ]
        try:
            from django.contrib.admin.widgets import FilteredSelectMultiple
            qs = PreuveAttendue.objects.filter(actif=True)
            widget = FilteredSelectMultiple('Preuves', is_stacked=False)
            widget.choices = [(p.pk, p.libelle) for p in qs]
            proto_html = widget.render('new_criteres_preuves_proto', None, attrs={'id': 'id_new_criteres_preuves_proto'})
        except Exception:
            proto_html = ''
        context['preuves_proto'] = proto_html
        return context


class ThemeDeleteView(LoginRequiredMixin, SuperuserOnlyMixin, DeactivateMixin, Object404Mixin, DeleteView):
    model = Theme
    template_name = "audit/referentiel/confirm_delete.html"
    success_url = reverse_lazy("audit:theme-list")


class CritereEvaluationListView(LoginRequiredMixin, SuperuserOnlyMixin, ListView):
    model = CritereEvaluation
    template_name = "audit/referentiel/critere_list.html"
    paginate_by = 25

    def get_queryset(self):
        qs = CritereEvaluation.objects.filter(actif=True).select_related("theme").prefetch_related("chapitre_norme__norme")
        q = self.request.GET.get("q", "").strip()
        theme = self.request.GET.get("theme", "").strip()
        if q:
            qs = qs.filter(Q(texte__icontains=q) | Q(theme__texte__icontains=q))
        if theme:
            qs = qs.filter(theme_id=theme)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["themes"] = Theme.objects.all()
        # CritereEvaluation is used if referenced by any LigneFormulaire
        context["used_critere_ids"] = set(
            LigneFormulaire.objects.exclude(critere__isnull=True).values_list("critere_id", flat=True)
        )
        return context


class CritereEvaluationCreateView(LoginRequiredMixin, SuperuserOnlyMixin, SafeDbOperationMixin, CreateView):
    model = CritereEvaluation
    form_class = CritereEvaluationForm
    template_name = "audit/referentiel/form.html"
    success_url = reverse_lazy("audit:critere-list")


class CritereEvaluationUpdateView(LoginRequiredMixin, SuperuserOnlyMixin, SafeDbOperationMixin, Object404Mixin, UpdateView):
    model = CritereEvaluation
    form_class = CritereEvaluationForm
    template_name = "audit/referentiel/form.html"
    success_url = reverse_lazy("audit:critere-list")


class CritereEvaluationDeleteView(LoginRequiredMixin, SuperuserOnlyMixin, DeactivateMixin, Object404Mixin, DeleteView):
    model = CritereEvaluation
    template_name = "audit/referentiel/confirm_delete.html"
    success_url = reverse_lazy("audit:critere-list")


class BaremeCotationListView(LoginRequiredMixin, SuperuserOnlyMixin, ListView):
    model = BaremeCotation
    template_name = "audit/referentiel/bareme_list.html"
    paginate_by = 25

    def get_queryset(self):
        qs = BaremeCotation.objects.filter(actif=True)
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(Q(code__icontains=q) | Q(description__icontains=q))
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # BaremeCotation is used if referenced by any ReponseAudit
        context["used_bareme_ids"] = set(
            ReponseAudit.objects.exclude(cotation__isnull=True).values_list("cotation_id", flat=True)
        )
        return context


class BaremeCotationCreateView(LoginRequiredMixin, SuperuserOnlyMixin, SafeDbOperationMixin, CreateView):
    model = BaremeCotation
    form_class = BaremeCotationForm
    template_name = "audit/referentiel/form.html"
    success_url = reverse_lazy("audit:bareme-list")


class BaremeCotationUpdateView(LoginRequiredMixin, SuperuserOnlyMixin, SafeDbOperationMixin, Object404Mixin, UpdateView):
    model = BaremeCotation
    form_class = BaremeCotationForm
    template_name = "audit/referentiel/form.html"
    success_url = reverse_lazy("audit:bareme-list")


class BaremeCotationDeleteView(LoginRequiredMixin, SuperuserOnlyMixin, DeactivateMixin, Object404Mixin, DeleteView):
    model = BaremeCotation
    template_name = "audit/referentiel/confirm_delete.html"
    success_url = reverse_lazy("audit:bareme-list")


# ============== Niveaux attendus ==============


class NiveauxAttendusListView(LoginRequiredMixin, SuperuserOnlyMixin, ListView):
    model = NiveauxAttendus
    template_name = "audit/referentiel/niveaux_list.html"
    paginate_by = 25

    def get_queryset(self):
        qs = NiveauxAttendus.objects.filter(actif=True)
        q = self.request.GET.get("q", "").strip()
        type_audit = self.request.GET.get("type_audit", "").strip()
        if q:
            qs = qs.filter(description__icontains=q)
        if type_audit:
            # include entries that explicitly match the selected type
            # and entries with no type selected (apply to all types)
            qs = qs.filter(Q(type_audit=type_audit) | Q(type_audit__isnull=True) | Q(type_audit=''))
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["type_choices"] = AuditType.choices
        context["used_niveaux_ids"] = set(
            ResultatAudit.objects.exclude(niveau_attendu__isnull=True)
            .values_list("niveau_attendu_id", flat=True)
        )
        return context


class NiveauxAttendusCreateView(LoginRequiredMixin, SuperuserOnlyMixin, SafeDbOperationMixin, CreateView):
    model = NiveauxAttendus
    form_class = NiveauxAttendusForm
    template_name = "audit/referentiel/form.html"
    success_url = reverse_lazy("audit:niveaux-list")

    def form_invalid(self, form):
        messages.error(self.request, "Erreur de validation du formulaire.")
        return super().form_invalid(form)
    
    def form_valid(self, form):
        # create one instance per selected type; if none selected, create a single "Tous" (no type)
        types = form.cleaned_data.get('type_audit_multiple') or []
        valeur = form.cleaned_data.get('valeur')
        description = form.cleaned_data.get('description')
        created_objs = []
        try:
            with transaction.atomic():
                if not types:
                    # create a single instance applying to all types
                    obj = NiveauxAttendus.objects.create(valeur=valeur, description=description, type_audit=None)
                    created_objs.append(obj)
                else:
                    for t in types:
                        obj = NiveauxAttendus.objects.create(valeur=valeur, description=description, type_audit=t)
                        created_objs.append(obj)
            messages.success(self.request, "Enregistrement effectué avec succès.")

            return redirect(self.success_url)
        except DatabaseError as exc:
            logger.exception("Erreur DB lors de création multiple: %s", exc)
            messages.error(self.request, "Une erreur base de données est survenue. Aucun enregistrement n'a été effectué.")
            return self.form_invalid(form)


# ============== Preuves attendues (CRUD) ==============


class PreuveAttendueListView(LoginRequiredMixin, SuperuserOnlyMixin, ListView):
    model = PreuveAttendue
    template_name = "audit/referentiel/preuve_list.html"
    paginate_by = 25

    def get_queryset(self):
        qs = PreuveAttendue.objects.filter(actif=True).select_related('type_preuve')
        q = self.request.GET.get('q', '').strip()
        type_id = self.request.GET.get('type', '').strip()
        if q:
            qs = qs.filter(libelle__icontains=q)
        if type_id:
            qs = qs.filter(type_preuve_id=type_id)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['types'] = PreuveAttendueType.objects.filter(actif=True)
        # PreuveAttendue is used if referenced by any CritereEvaluation M2M
        ctx["used_preuve_ids"] = set(
            CritereEvaluation.objects.filter(preuves_attendues__isnull=False).values_list("preuves_attendues__id", flat=True)
        )
        return ctx


class PreuveAttendueCreateView(LoginRequiredMixin, SuperuserOnlyMixin, SafeDbOperationMixin, CreateView):
    model = PreuveAttendue
    template_name = "audit/referentiel/form.html"
    form_class = None
    success_url = reverse_lazy("audit:preuve-list")

    def get_form_class(self):
        from .forms import BootstrapModelForm
        class _F(BootstrapModelForm):
            class Meta:
                model = PreuveAttendue
                exclude = ('actif',)
        return _F
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['is_preuve'] = True
        return ctx


class PreuveAttendueUpdateView(LoginRequiredMixin, SuperuserOnlyMixin, SafeDbOperationMixin, Object404Mixin, UpdateView):
    model = PreuveAttendue
    template_name = "audit/referentiel/form.html"
    form_class = None
    success_url = reverse_lazy("audit:preuve-list")

    def get_form_class(self):
        from .forms import BootstrapModelForm
        class _F(BootstrapModelForm):
            class Meta:
                model = PreuveAttendue
                exclude = ('actif',)
        return _F
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['is_preuve'] = True
        return ctx


class PreuveAttendueDeleteView(LoginRequiredMixin, SuperuserOnlyMixin, DeactivateMixin, Object404Mixin, DeleteView):
    model = PreuveAttendue
    template_name = "audit/referentiel/confirm_delete.html"
    success_url = reverse_lazy("audit:preuve-list")


# ============== Types de preuves attendues (CRUD) ==============


class PreuveAttendueTypeListView(LoginRequiredMixin, SuperuserOnlyMixin, ListView):
    model = PreuveAttendueType
    template_name = "audit/referentiel/preuve_type_list.html"
    paginate_by = 25

    def get_queryset(self):
        qs = PreuveAttendueType.objects.filter(actif=True)
        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(nom__icontains=q)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # PreuveAttendueType is used if referenced by any PreuveAttendue
        context["used_type_ids"] = set(
            PreuveAttendue.objects.exclude(type_preuve__isnull=True).values_list("type_preuve_id", flat=True)
        )
        return context


class PreuveAttendueTypeCreateView(LoginRequiredMixin, SuperuserOnlyMixin, SafeDbOperationMixin, CreateView):
    model = PreuveAttendueType
    template_name = "audit/referentiel/form.html"
    form_class = None
    success_url = reverse_lazy("audit:preuve-type-list")

    def get_form_class(self):
        from .forms import BootstrapModelForm
        class _F(BootstrapModelForm):
            class Meta:
                model = PreuveAttendueType
                exclude = ('actif',)
        return _F


class PreuveAttendueTypeUpdateView(LoginRequiredMixin, SuperuserOnlyMixin, SafeDbOperationMixin, Object404Mixin, UpdateView):
    model = PreuveAttendueType
    template_name = "audit/referentiel/form.html"
    form_class = None
    success_url = reverse_lazy("audit:preuve-type-list")

    def get_form_class(self):
        from .forms import BootstrapModelForm
        class _F(BootstrapModelForm):
            class Meta:
                model = PreuveAttendueType
                exclude = ('actif',)
        return _F


class PreuveAttendueTypeDeleteView(LoginRequiredMixin, SuperuserOnlyMixin, DeactivateMixin, Object404Mixin, DeleteView):
    model = PreuveAttendueType
    template_name = "audit/referentiel/confirm_delete.html"
    success_url = reverse_lazy("audit:preuve-type-list")
    pass


class NiveauxAttendusUpdateView(LoginRequiredMixin, SuperuserOnlyMixin, SafeDbOperationMixin, Object404Mixin, UpdateView):
    model = NiveauxAttendus
    form_class = NiveauxAttendusForm
    template_name = "audit/referentiel/form.html"
    success_url = reverse_lazy("audit:niveaux-list")

    def form_invalid(self, form):
        messages.error(self.request, "Erreur de validation du formulaire.")
        return super().form_invalid(form)
    
    def form_valid(self, form):
        # on update: update this instance with the first selected type (or None for Tous),
        # and create additional instances for any extra selected types.
        types = form.cleaned_data.get('type_audit_multiple') or []
        valeur = form.cleaned_data.get('valeur')
        description = form.cleaned_data.get('description')
        try:
            with transaction.atomic():
                if not types:
                    # set current object to apply to all types
                    self.object.type_audit = None
                    self.object.valeur = valeur
                    self.object.description = description
                    self.object.save()
                else:
                    # assign first selected type to current object
                    first = types[0]
                    self.object.type_audit = first
                    self.object.valeur = valeur
                    self.object.description = description
                    self.object.save()
                    # create remaining types as new objects
                    for t in types[1:]:
                        # avoid creating duplicate if an identical object already exists
                        exists = NiveauxAttendus.objects.filter(valeur=valeur, description=description, type_audit=t).exists()
                        if not exists:
                            NiveauxAttendus.objects.create(valeur=valeur, description=description, type_audit=t)
            messages.success(self.request, "Enregistrement effectué avec succès.")
            return redirect(self.success_url)
        except DatabaseError as exc:
            logger.exception("Erreur DB lors de mise à jour multiple: %s", exc)
            messages.error(self.request, "Une erreur base de données est survenue. Veuillez réessayer.")
            return super().form_invalid(form)


class NiveauxAttendusDeleteView(LoginRequiredMixin, SuperuserOnlyMixin, DeactivateMixin, Object404Mixin, DeleteView):
    model = NiveauxAttendus
    template_name = "audit/referentiel/confirm_delete.html"
    success_url = reverse_lazy("audit:niveaux-list")


# ============== Formulaires d'audit ==============


def ajax_formulaire_theme_data(request):
    """Return JSON data for all themes with critères, preuves, normes and chapitres."""

    themes = Theme.objects.prefetch_related(
        "criteres__preuves_attendues__type_preuve",
        "criteres__chapitre_norme__norme",
    ).filter(actif=True)

    data = []
    for theme in themes:
        criteres = []
        for critere in theme.criteres.filter(actif=True):
            preuves = [
                {"id": p.id, "libelle": p.libelle, "code": p.code}
                for p in critere.preuves_attendues.all()
            ]
            chapitres = []
            normes_seen = {}
            for chap in critere.chapitre_norme.select_related("norme").all():
                chapitres.append({
                    "id": chap.id,
                    "reference": chap.reference,
                    "intitule": chap.intitule,
                    "norme_id": chap.norme_id,
                    "norme_nom": chap.norme.nom,
                    "num_page": chap.num_page,
                })
                if chap.norme_id not in normes_seen:
                    normes_seen[chap.norme_id] = chap.norme.nom
            normes = [{"id": nid, "nom": nnom} for nid, nnom in normes_seen.items()]
            criteres.append({
                "id": critere.id,
                "texte": critere.texte,
                "preuves": preuves,
                "chapitres": chapitres,
                "normes": normes,
            })
        data.append({
            "id": theme.id,
            "texte": theme.texte,
            "criteres": criteres,
        })

    return JsonResponse({"themes": data})


class FormulaireAuditListView(LoginRequiredMixin, SuperuserOrAuditeurMixin, ListView):
    model = FormulaireAudit
    template_name = "audit/formulaire/list.html"
    paginate_by = 25

    def get_queryset(self):
        qs = FormulaireAudit.objects.filter(actif=True).select_related("section").prefetch_related("lignes")
        if getattr(self.request.user, "is_superuser", False):
            scoped = qs
        else:
            user_section = getattr(self.request.user, "section", None)
            scoped = qs.filter(section=user_section)

        q = self.request.GET.get("q", "").strip()
        type_audit = self.request.GET.get("type_audit", "").strip()
        section_id = self.request.GET.get("section", "").strip()

        if q:
            scoped = scoped.filter(titre__icontains=q)
        if type_audit:
            scoped = scoped.filter(type_audit=type_audit)
        if section_id:
            scoped = scoped.filter(section_id=section_id)

        return scoped

    def get_context_data(self, **kwargs):
        from accounts.models import Section
        context = super().get_context_data(**kwargs)
        context["type_choices"] = AuditType.choices
        # FormulaireAudit is used if referenced by any Audit
        context["used_formulaire_ids"] = set(
            Audit.objects.exclude(formulaire__isnull=True).values_list("formulaire_id", flat=True)
        )
        context["sections"] = Section.objects.all().order_by("Nom")
        return context


class FormulaireAuditCreateView(LoginRequiredMixin, SuperuserOrAuditeurMixin, SafeDbOperationMixin, CreateView):
    model = FormulaireAudit
    form_class = FormulaireAuditForm
    template_name = "audit/formulaire/form.html"
    success_url = reverse_lazy("audit:formulaire-list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["themes"] = Theme.objects.filter(actif=True).prefetch_related("criteres")
        return context

    @transaction.atomic
    def form_valid(self, form):
        response = super().form_valid(form)
        formulaire = self.object
        critere_ids = self.request.POST.getlist("critere_ids[]")
        seen = set()
        ordered_ids = []
        for cid in critere_ids:
            try:
                cid = int(cid)
            except (ValueError, TypeError):
                continue
            if cid in seen:
                continue
            seen.add(cid)
            ordered_ids.append(cid)
        for idx, cid in enumerate(ordered_ids, start=1):
            try:
                critere = CritereEvaluation.objects.get(pk=cid)
                ligne, _ = LigneFormulaire.objects.get_or_create(formulaire=formulaire, critere=critere)
                LigneFormulaire.objects.filter(pk=ligne.pk).update(ordre=idx)
            except CritereEvaluation.DoesNotExist:
                pass
        return response

    def form_invalid(self, form):
        messages.error(self.request, "Veuillez corriger les erreurs ci-dessous.")
        return self.render_to_response(self.get_context_data(
            form=form,
            existing_critere_ids=self._get_submitted_critere_ids(),
        ))

    def _get_submitted_critere_ids(self):
        ids = []
        for cid in self.request.POST.getlist("critere_ids[]"):
            try:
                ids.append(int(cid))
            except (ValueError, TypeError):
                pass
        return ids


class FormulaireAuditUpdateView(LoginRequiredMixin, SuperuserOrAuditeurMixin, SafeDbOperationMixin, Object404Mixin, UpdateView):
    model = FormulaireAudit
    form_class = FormulaireAuditForm
    template_name = "audit/formulaire/form.html"
    success_url = reverse_lazy("audit:formulaire-list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["themes"] = Theme.objects.filter(actif=True).prefetch_related("criteres")
        existing_ids = list(
            self.object.lignes.order_by("ordre", "id").values_list("critere_id", flat=True)
        )
        context["existing_critere_ids"] = existing_ids
        return context

    @transaction.atomic
    def form_valid(self, form):
        response = super().form_valid(form)
        formulaire = self.object
        critere_ids = self.request.POST.getlist("critere_ids[]")
        seen = set()
        ordered_ids = []
        for cid in critere_ids:
            try:
                cid = int(cid)
            except (ValueError, TypeError):
                continue
            if cid in seen:
                continue
            seen.add(cid)
            ordered_ids.append(cid)
        # Remove lines not in new list
        formulaire.lignes.exclude(critere_id__in=ordered_ids).delete()
        # Create/update lines with correct ordre
        for idx, cid in enumerate(ordered_ids, start=1):
            try:
                critere = CritereEvaluation.objects.get(pk=cid)
                ligne, _ = LigneFormulaire.objects.get_or_create(formulaire=formulaire, critere=critere)
                LigneFormulaire.objects.filter(pk=ligne.pk).update(ordre=idx)
            except CritereEvaluation.DoesNotExist:
                pass
        return response

    def form_invalid(self, form):
        messages.error(self.request, "Veuillez corriger les erreurs ci-dessous.")
        existing_ids = self.request.POST.getlist("critere_ids[]")
        ids = []
        for cid in existing_ids:
            try:
                ids.append(int(cid))
            except (ValueError, TypeError):
                pass
        return self.render_to_response(self.get_context_data(
            form=form,
            existing_critere_ids=ids,
        ))


class FormulaireAuditDeleteView(LoginRequiredMixin, SuperuserOrAuditeurMixin, DeactivateMixin, Object404Mixin, DeleteView):
    model = FormulaireAudit
    template_name = "audit/formulaire/confirm_delete.html"
    success_url = reverse_lazy("audit:formulaire-list")


class FormulaireAuditDetailView(LoginRequiredMixin, SuperuserOrAuditeurMixin, Object404Mixin, DetailView):
    model = FormulaireAudit
    template_name = "audit/formulaire/detail.html"

    def get_queryset(self):
        return FormulaireAudit.objects.select_related("section").prefetch_related(
            "lignes__critere__chapitre_norme__norme",
            "lignes__critere__preuves_attendues",
        )


class LigneFormulaireCreateView(LoginRequiredMixin, SuperuserOrAuditeurMixin, SafeDbOperationMixin, CreateView):
    model = LigneFormulaire
    form_class = LigneFormulaireForm
    template_name = "audit/formulaire/ligne_form.html"

    def get_initial(self):
        initial = super().get_initial()
        initial["formulaire"] = self.kwargs.get("formulaire_pk")
        return initial

    def get_success_url(self):
        return reverse("audit:formulaire-detail", kwargs={"pk": self.object.formulaire_id})


class LigneFormulaireUpdateView(LoginRequiredMixin, SuperuserOrAuditeurMixin, SafeDbOperationMixin, Object404Mixin, UpdateView):
    model = LigneFormulaire
    form_class = LigneFormulaireForm
    template_name = "audit/formulaire/ligne_form.html"

    def get_success_url(self):
        return reverse("audit:formulaire-detail", kwargs={"pk": self.object.formulaire_id})


class LigneFormulaireDeleteView(LoginRequiredMixin, SuperuserOrAuditeurMixin, DeactivateMixin, Object404Mixin, DeleteView):
    model = LigneFormulaire
    template_name = "audit/formulaire/ligne_confirm_delete.html"

    def get_success_url(self):
        return reverse("audit:formulaire-detail", kwargs={"pk": self.object.formulaire_id})


@login_required_fn
@require_POST
def ajax_reorder_lignes(request):
    """Reorder LigneFormulaire by receiving an ordered list of IDs."""
    import json as _json
    try:
        data = _json.loads(request.body)
    except Exception:
        return JsonResponse({'ok': False, 'error': 'JSON invalide.'}, status=400)

    ordered_ids = data.get('ids', [])
    if not ordered_ids:
        return JsonResponse({'ok': False, 'error': 'Liste vide.'}, status=400)

    try:
        with transaction.atomic():
            for idx, pk in enumerate(ordered_ids, start=1):
                LigneFormulaire.objects.filter(pk=pk).update(ordre=idx)
    except Exception as exc:
        return JsonResponse({'ok': False, 'error': str(exc)}, status=500)

    return JsonResponse({'ok': True})


# ============== Audit ==============


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "audit/audit/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from django.utils import timezone
        from django.db.models import Avg
        from collections import Counter
        from accounts.models import Section as SectionModel, Societe as SocieteModel

        allowed_types = filter_allowed_types_for_use(self.request.user)
        qs = Audit.objects.filter(actif=True, formulaire__type_audit__in=allowed_types)

        # ── Apply sidebar filters ──
        f_societe = self.request.GET.get('societe', '').strip()
        f_section = self.request.GET.get('section', '').strip()
        f_type    = self.request.GET.get('type', '').strip()
        f_statut  = self.request.GET.get('statut', '').strip()
        f_annee   = self.request.GET.get('annee', '').strip()

        if f_societe:
            qs = qs.filter(formulaire__section__societe_id=f_societe)
        if f_section:
            qs = qs.filter(formulaire__section_id=f_section)
        if f_type:
            qs = qs.filter(formulaire__type_audit=f_type)
        if f_statut:
            qs = qs.filter(statut=f_statut)
        if f_annee:
            try:
                qs = qs.filter(date_audit__year=int(f_annee))
            except ValueError:
                pass

        is_filtered = any([f_societe, f_section, f_type, f_statut, f_annee])

        ctx['today'] = timezone.localdate()
        ctx['total']        = qs.count()
        ctx['nb_brouillon'] = qs.filter(statut='BROUILLON').count()
        ctx['nb_planifie']  = qs.filter(statut='PLANIFIER').count()
        ctx['nb_en_cours']  = qs.filter(statut='EN_COURS').count()
        ctx['nb_termine']   = qs.filter(statut='TERMINE').count()

        # Avg score from ResultatAudit
        score_vals = []
        for r in ResultatAudit.objects.filter(audit__in=qs).select_related('audit'):
            try:
                v = float(r.niveau_prestation_pct)
                score_vals.append(v)
            except Exception:
                pass
        ctx['avg_score'] = (sum(score_vals) / len(score_vals)) if score_vals else None

        # Score distribution [0-25, 25-50, 50-75, 75-100]
        dist = [0, 0, 0, 0]
        for v in score_vals:
            if v < 25:   dist[0] += 1
            elif v < 50: dist[1] += 1
            elif v < 75: dist[2] += 1
            else:        dist[3] += 1
        ctx['score_dist'] = dist

        # By type progression
        type_data = []
        for code, label in AuditType.choices:
            sub = qs.filter(formulaire__type_audit=code)
            count = sub.count()
            done  = sub.filter(statut='TERMINE').count()
            pct   = round(done / count * 100) if count else 0
            type_data.append({'code': code, 'label': label, 'count': count, 'done': done, 'pct': pct})
        ctx['by_type'] = type_data

        # Recent audits with score
        recent = list(
            qs.select_related('formulaire', 'formulaire__section', 'resultat')
            .order_by('-date_audit', '-id')[:10]
        )
        for a in recent:
            try:
                a.score = float(a.resultat.niveau_prestation_pct)
            except Exception:
                a.score = None
        ctx['recent_audits'] = recent
        ctx['can_create_any'] = bool(filter_allowed_types_for_create(self.request.user))

        # ── Filter choices for sidebar ──
        ctx['societes']       = SocieteModel.objects.all().order_by('nom')
        ctx['sections']       = SectionModel.objects.all().order_by('Nom')
        ctx['type_choices']   = [(k, v) for k, v in AuditType.choices if k in allowed_types]
        ctx['statut_choices'] = AuditStatut.choices
        import datetime
        current_year = timezone.localdate().year
        ctx['annee_choices']  = list(range(current_year, current_year - 6, -1))
        ctx['is_filtered']    = is_filtered
        # keep current filter values for form pre-fill
        ctx['f_societe'] = f_societe
        ctx['f_section'] = f_section
        ctx['f_type']    = f_type
        ctx['f_statut']  = f_statut
        ctx['f_annee']   = f_annee
        return ctx


class AuditListView(LoginRequiredMixin, ListView):
    model = Audit
    template_name = "audit/audit/list.html"
    paginate_by = 25

    def get_queryset(self):
        allowed_types = filter_allowed_types_for_use(self.request.user)
        qs = (
            Audit.objects.filter(actif=True).select_related("formulaire", "cree_par", "formulaire__section", "responsable_audit")
            .filter(formulaire__type_audit__in=allowed_types)
            .annotate(participant_count=Count('participants'))
        )
        if self.request.GET.get("type"):
            qs = qs.filter(formulaire__type_audit=self.request.GET["type"])
        if self.request.GET.get("statut"):
            qs = qs.filter(statut=self.request.GET["statut"])
        if self.request.GET.get("section"):
            qs = qs.filter(formulaire__section_id=self.request.GET["section"])
        if self.request.GET.get("date"):
            qs = qs.filter(date_audit=self.request.GET["date"])
        if self.request.GET.get("q"):
            qs = qs.filter(Q(numero__icontains=self.request.GET["q"]) | Q(formulaire__titre__icontains=self.request.GET["q"]))
        return qs

    def get_context_data(self, **kwargs):
        from accounts.models import Section as SectionModel
        context = super().get_context_data(**kwargs)
        allowed_use   = set(filter_allowed_types_for_use(self.request.user))
        allowed_create = set(filter_allowed_types_for_create(self.request.user))
        context["type_choices"]       = [(k, v) for k, v in AuditType.choices if k in allowed_use]
        context["statut_choices"]     = AuditStatut.choices
        context["sections"]           = SectionModel.objects.all().order_by("Nom")
        context["allowed_create_types"] = allowed_create
        context["can_create_any"]     = bool(allowed_create)
        
        # Determine which audits cannot be deleted (have responses or status == TERMINE)
        from django.db.models import Exists, OuterRef
        audits_with_responses = Audit.objects.filter(
            pk=OuterRef('pk'),
            reponses__isnull=False
        )
        context["audit_cannot_delete_ids"] = set(
            Audit.objects.filter(actif=True).filter(
                Q(statut='TERMINE') | Q(Exists(audits_with_responses))
            ).values_list('pk', flat=True)
        )
        return context


class AuditCreateView(LoginRequiredMixin, CreateView):
    model = Audit
    form_class = AuditForm
    template_name = "audit/audit/form.html"
    success_url = reverse_lazy("audit:list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def dispatch(self, request, *args, **kwargs):
        type_audit = request.POST.get("type_audit") or request.GET.get("type_audit")
        if type_audit and not user_can_create_audit(request.user, type_audit):
            return render(request, "403.html", {"message": "Accès non autorisé à la création de cet audit."}, status=403)
        return super().dispatch(request, *args, **kwargs)

    def _save_participants(self, audit):
        """Save participants from POST data."""
        from django.contrib.auth import get_user_model
        User = get_user_model()
        audit.participants.all().delete()
        user_ids    = self.request.POST.getlist('participant_user_id[]')
        noms        = self.request.POST.getlist('participant_nom[]')
        fonctions   = self.request.POST.getlist('participant_fonction[]')
        exterieurs  = self.request.POST.getlist('participant_exterieur[]')
        from .models import ParticipantAudit
        for i in range(len(fonctions)):
            fn = (fonctions[i] or '').strip()
            if not fn:
                continue
            uid  = user_ids[i] if i < len(user_ids) else ''
            nom  = noms[i]    if i < len(noms)     else ''
            ext  = exterieurs[i] if i < len(exterieurs) else ''
            user_obj = None
            if uid:
                user_obj = User.objects.filter(pk=uid).first()
            ParticipantAudit.objects.create(
                audit=audit,
                user=user_obj,
                nom_externe=(nom.strip() if not user_obj else ''),
                fonction=fn,
                est_auditeur_externe=(ext == '1'),
            )

    def form_valid(self, form):
        form.instance.cree_par = self.request.user
        form.instance.statut = AuditStatut.EN_COURS
        try:
            with transaction.atomic():
                self.object = form.save()
                self._save_participants(self.object)
        except DatabaseError as exc:
            logger.exception("Erreur création audit: %s", exc)
            messages.error(self.request, "Erreur base de données lors de la création.")
            return self.form_invalid(form)
        messages.success(self.request, "Audit créé avec succès.")
        return redirect(reverse('audit:audit-evaluation', kwargs={'pk': self.object.pk}))

    def get_context_data(self, **kwargs):
        import json as _json
        from django.contrib.auth import get_user_model
        from django.utils.safestring import mark_safe
        from datetime import date
        User = get_user_model()
        context = super().get_context_data(**kwargs)
        formulaires = list(
            FormulaireAudit.objects.select_related('section').filter(actif=True)
            .values('id', 'titre', 'type_audit', 'section__Nom', 'section_id')
        )
        users = list(
            User.objects.filter(is_active=True).order_by('last_name', 'first_name')
            .values('id', 'first_name', 'last_name', 'username')
        )
        context['formulaires_json'] = mark_safe(_json.dumps(formulaires))
        context['formulaires_list'] = formulaires
        context['users_json'] = users
        context['statut_choices'] = AuditStatut.choices
        context['type_choices'] = [(k, v) for k, v in AuditType.choices if k in filter_allowed_types_for_create(self.request.user)]
        context['participants'] = []
        context['today'] = date.today().isoformat()
        return context


class AuditUpdateView(LoginRequiredMixin, Object404Mixin, UpdateView):
    model = Audit
    form_class = AuditForm
    template_name = "audit/audit/form.html"
    success_url = reverse_lazy("audit:list")

    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        # Check after object is loaded (Object404Mixin fetches it)
        if hasattr(self, 'object') and self.object and not user_can_create_audit(request.user, self.object.formulaire.type_audit):
            return render(request, "403.html", {"message": "Vous n'êtes pas autorisé à modifier cet audit."}, status=403)
        return response

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def _save_participants(self, audit):
        """Save participants from POST data."""
        from django.contrib.auth import get_user_model
        User = get_user_model()
        audit.participants.all().delete()
        user_ids   = self.request.POST.getlist('participant_user_id[]')
        noms       = self.request.POST.getlist('participant_nom[]')
        fonctions  = self.request.POST.getlist('participant_fonction[]')
        exterieurs = self.request.POST.getlist('participant_exterieur[]')
        from .models import ParticipantAudit
        for i in range(len(fonctions)):
            fn = (fonctions[i] or '').strip()
            if not fn:
                continue
            uid  = user_ids[i] if i < len(user_ids) else ''
            nom  = noms[i]    if i < len(noms)     else ''
            ext  = exterieurs[i] if i < len(exterieurs) else ''
            user_obj = None
            if uid:
                user_obj = User.objects.filter(pk=uid).first()
            ParticipantAudit.objects.create(
                audit=audit,
                user=user_obj,
                nom_externe=(nom.strip() if not user_obj else ''),
                fonction=fn,
                est_auditeur_externe=(ext == '1'),
            )

    def form_valid(self, form):
        try:
            with transaction.atomic():
                self.object = form.save()
                self._save_participants(self.object)
        except DatabaseError as exc:
            logger.exception("Erreur mise à jour audit: %s", exc)
            messages.error(self.request, "Erreur base de données lors de la mise à jour.")
            return self.form_invalid(form)
        messages.success(self.request, "Audit mis à jour avec succès.")
        return redirect(self.success_url)

    def get_context_data(self, **kwargs):
        import json as _json
        from django.contrib.auth import get_user_model
        from django.utils.safestring import mark_safe
        from datetime import date
        User = get_user_model()
        context = super().get_context_data(**kwargs)
        formulaires = list(
            FormulaireAudit.objects.select_related('section').filter(actif=True)
            .values('id', 'titre', 'type_audit', 'section__Nom', 'section_id')
        )
        users = list(
            User.objects.filter(is_active=True).order_by('last_name', 'first_name')
            .values('id', 'first_name', 'last_name', 'username')
        )
        context['formulaires_json'] = mark_safe(_json.dumps(formulaires))
        context['formulaires_list'] = formulaires
        context['users_json'] = users
        context['statut_choices'] = AuditStatut.choices
        context['type_choices'] = [(k, v) for k, v in AuditType.choices if k in filter_allowed_types_for_create(self.request.user)]
        context['participants'] = list(
            self.object.participants.select_related('user')
            .values('id', 'user_id', 'user__first_name', 'user__last_name',
                    'nom_externe', 'fonction', 'est_auditeur_externe')
        )
        context['today'] = date.today().isoformat()
        return context


class AuditDeleteView(LoginRequiredMixin, DeactivateMixin, Object404Mixin, DeleteView):
    model = Audit
    template_name = "audit/referentiel/confirm_delete.html"
    success_url = reverse_lazy("audit:list")

    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        # Check permissions
        if hasattr(self, 'object') and self.object:
            if not user_can_create_audit(request.user, self.object.formulaire.type_audit):
                return render(request, "403.html", {"message": "Vous n'êtes pas autorisé à supprimer/désactiver cet audit."}, status=403)
        return response

    def _is_referenced(self):
        """
        Audit can only be deleted/deactivated if:
        - It has no responses (ReponseAudit)
        - AND its status is not TERMINE
        """
        if self.object.statut == 'TERMINE':
            return True  # Cannot delete/deactivate if completed
        if self.object.reponses.exists():
            return True  # Cannot delete if has responses
        return False

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['object_type'] = 'audit'
        return ctx


# ─── AJAX: Copy FormulaireAudit ──────────────────────────────────────────────

from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required as login_required_fn


@login_required_fn
@require_POST
def ajax_copy_formulaire(request):
    """Deep-clone a FormulaireAudit with a new (section, type_audit) pair."""
    import json as _json
    try:
        data = _json.loads(request.body)
    except Exception:
        data = request.POST

    source_id       = data.get('source_id')
    new_section_id  = data.get('new_section_id')
    new_type        = data.get('new_type_audit')
    new_titre       = (data.get('new_titre') or '').strip()

    if not all([source_id, new_section_id, new_type, new_titre]):
        return JsonResponse({'ok': False, 'error': 'Tous les champs sont requis.'}, status=400)

    try:
        source = FormulaireAudit.objects.get(pk=source_id)
    except FormulaireAudit.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'Formulaire source introuvable.'}, status=404)

    from accounts.models import Section as SectionModel
    try:
        new_section = SectionModel.objects.get(pk=new_section_id)
    except SectionModel.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'Section introuvable.'}, status=404)

    from audit.models import AuditType as AT
    multi_types = {AT.EQUIPEMENT, AT.POSTE}
    if new_type not in multi_types and FormulaireAudit.objects.filter(section=new_section, type_audit=new_type).exists():
        return JsonResponse({'ok': False, 'error': "Un formulaire existe déjà pour cette section et ce type d'audit."}, status=409)

    try:
        with transaction.atomic():
            new_form = FormulaireAudit.objects.create(
                titre=new_titre,
                type_audit=new_type,
                section=new_section,
                actif=source.actif,
            )
            for ligne in source.lignes.select_related('critere').all():
                LigneFormulaire.objects.create(
                    formulaire=new_form,
                    critere=ligne.critere,
                )
    except Exception as exc:
        return JsonResponse({'ok': False, 'error': str(exc)}, status=500)

    return JsonResponse({'ok': True, 'id': new_form.pk, 'titre': new_form.titre})


class AuditDetailView(LoginRequiredMixin, View):
    """Redirige vers le rapport de l'audit."""

    def get(self, request, pk):
        return redirect("audit:audit-rapport", pk=pk)


class AuditLancerView(LoginRequiredMixin, View):
    """Passe l'audit en statut EN_COURS et pré-remplit les réponses."""

    def post(self, request, pk):
        audit = get_object_or_404(
            Audit.objects.select_related("formulaire").prefetch_related("formulaire__lignes__critere__theme"),
            pk=pk,
        )
        if not user_can_create_audit(request.user, audit.formulaire.type_audit):
            return render(request, "403.html", {"message": "Vous ne pouvez pas lancer cet audit."}, status=403)

        try:
            with transaction.atomic():
                for ligne in audit.formulaire.lignes.all():
                    ReponseAudit.objects.get_or_create(audit=audit, ligne=ligne)
                audit.statut = AuditStatut.EN_COURS
                audit.save(update_fields=["statut"])
            messages.success(request, "Audit lancé avec succès.")
        except DatabaseError as exc:
            logger.exception("Erreur lancement audit %s", audit.pk)
            messages.error(request, f"Erreur lors du lancement de l'audit : {exc}")
        return redirect("audit:audit-evaluation", pk=pk)


class AuditTerminerView(LoginRequiredMixin, View):
    """Termine l'audit (signal post_save => création résultat)."""

    def post(self, request, pk):
        audit = get_object_or_404(Audit, pk=pk)
        if not user_can_create_audit(request.user, audit.formulaire.type_audit):
            return render(request, "403.html", {"message": "Vous ne pouvez pas terminer cet audit."}, status=403)

        try:
            audit.statut = AuditStatut.TERMINE
            audit.save(update_fields=["statut"])
            messages.success(request, "Audit terminé avec succès.")
        except DatabaseError as exc:
            logger.exception("Erreur fin audit %s", audit.pk)
            messages.error(request, f"Erreur lors de la clôture de l'audit : {exc}")
        return redirect("audit:audit-rapport", pk=pk)




# ============== Évaluation ligne par ligne ==============


class AuditEvaluationView(LoginRequiredMixin, View):
    """Évaluation interactive d'un audit, ligne par ligne."""

    template_name = "audit/audit/evaluation.html"

    def _get_audit(self, request, pk):
        audit = get_object_or_404(
            Audit.objects.select_related("formulaire__section").prefetch_related(
                "formulaire__lignes__critere__theme",
                "formulaire__lignes__critere__preuves_attendues",
                "formulaire__lignes__critere__chapitre_norme__norme",
                "reponses__cotation",
                "reponses__images",
            ),
            pk=pk,
        )
        if not user_can_use_audit(request.user, audit.formulaire.type_audit):
            return None, render(request, "403.html", {"message": "Accès non autorisé."}, status=403)
        return audit, None

    def get(self, request, pk):
        audit, err = self._get_audit(request, pk)
        if err:
            return err

        # Auto-lance l'audit si encore planifié
        if audit.statut in (AuditStatut.BROUILLON, AuditStatut.PLANIFIER):
            try:
                with transaction.atomic():
                    for ligne in audit.formulaire.lignes.all():
                        ReponseAudit.objects.get_or_create(audit=audit, ligne=ligne)
                    audit.statut = AuditStatut.EN_COURS
                    audit.save(update_fields=["statut"])
            except DatabaseError as exc:
                logger.exception("Erreur lancement auto audit %s", pk)
                messages.error(request, f"Erreur lors du lancement : {exc}")
                return redirect("audit:list")

        lignes = list(audit.formulaire.lignes.select_related(
            "critere__theme"
        ).prefetch_related(
            "critere__preuves_attendues",
            "critere__chapitre_norme__norme",
        ).order_by("ordre", "id"))

        reponses_map = {r.ligne_id: r for r in audit.reponses.select_related("cotation").prefetch_related("images")}
        baremes = list(BaremeCotation.objects.filter(actif=True).order_by("-note"))

        # Build enriched lines list
        lignes_data = []
        for i, ligne in enumerate(lignes):
            rep = reponses_map.get(ligne.pk)
            lignes_data.append({
                "index": i,
                "ligne": ligne,
                "reponse": rep,
                "has_cotation": rep is not None and rep.cotation_id is not None,
            })

        done_count = sum(1 for ld in lignes_data if ld["has_cotation"])
        total = len(lignes_data)

        return render(request, self.template_name, {
            "audit": audit,
            "lignes_data": lignes_data,
            "baremes": baremes,
            "done_count": done_count,
            "total": total,
            "progress_pct": int(done_count * 100 / total) if total else 0,
            "can_create": user_can_create_audit(request.user, audit.formulaire.type_audit),
        })


@login_required_fn
@require_POST
def ajax_save_reponse(request, audit_pk):
    """AJAX: sauvegarde cotation + commentaire + document + images d'une réponse."""
    import json as _json

    audit = get_object_or_404(Audit, pk=audit_pk)
    if not user_can_use_audit(request.user, audit.formulaire.type_audit):
        return JsonResponse({"ok": False, "error": "Accès non autorisé."}, status=403)

    ligne_pk   = request.POST.get("ligne_id")
    cotation_pk = request.POST.get("cotation_id")
    commentaire = request.POST.get("commentaire", "").strip()
    doc_file   = request.FILES.get("document")
    images     = request.FILES.getlist("images")
    delete_document = request.POST.get("delete_document") in {"1", "true", "True", "on"}

    if not ligne_pk:
        return JsonResponse({"ok": False, "error": "ligne_id manquant."}, status=400)

    ligne = get_object_or_404(LigneFormulaire, pk=ligne_pk, formulaire=audit.formulaire)

    cotation = None
    if cotation_pk:
        cotation = get_object_or_404(BaremeCotation, pk=cotation_pk)

    try:
        with transaction.atomic():
            reponse, _ = ReponseAudit.objects.get_or_create(audit=audit, ligne=ligne)
            reponse.cotation = cotation
            reponse.commentaire = commentaire
            if delete_document and reponse.document:
                reponse.document.delete(save=False)
                reponse.document = None
            if doc_file:
                reponse.document = doc_file
            reponse.save()

            # Handle new images
            for img in images:
                from .models import ReponseImage
                ReponseImage.objects.create(reponse=reponse, image=img)

            # Delete images if requested
            delete_image_ids = request.POST.getlist("delete_image_ids[]")
            if delete_image_ids:
                from .models import ReponseImage
                ReponseImage.objects.filter(pk__in=delete_image_ids, reponse=reponse).delete()

    except DatabaseError as exc:
        logger.exception("Erreur sauvegarde réponse audit %s ligne %s", audit_pk, ligne_pk)
        return JsonResponse({"ok": False, "error": str(exc)}, status=500)

    # Compute new progress
    total = audit.formulaire.lignes.count()
    done  = audit.reponses.exclude(cotation__isnull=True).count()

    images_data = [
        {"id": img.pk, "url": img.image.url}
        for img in reponse.images.all()
    ]
    doc_url = reponse.document.url if reponse.document else None
    doc_name = reponse.document.name.split("/")[-1] if reponse.document else None

    return JsonResponse({
        "ok": True,
        "done": done,
        "total": total,
        "progress_pct": int(done * 100 / total) if total else 0,
        "images": images_data,
        "doc_url": doc_url,
        "doc_name": doc_name,
        "cotation_code": reponse.cotation.code if reponse.cotation else None,
    })


# ============== Réponses ==============


class ReponseAuditUpdateView(LoginRequiredMixin, CanUseAuditMixin, SafeDbOperationMixin, Object404Mixin, UpdateView):
    model = ReponseAudit
    form_class = ReponseAuditForm
    template_name = "audit/audit/reponse_form.html"

    def get_queryset(self):
        return ReponseAudit.objects.select_related("audit", "ligne")

    def get_audit_type_for_permission(self):
        return self.get_object().audit.formulaire.type_audit

    def get_success_url(self):
        return reverse("audit:detail", kwargs={"pk": self.object.audit_id})


class ReponseAuditMassUpdateView(LoginRequiredMixin, View):
    """Saisie en masse des réponses de l'audit via formset inline."""

    template_name = "audit/audit/reponses_form.html"

    def get(self, request, pk):
        audit = get_object_or_404(
            Audit.objects.select_related("formulaire").prefetch_related(
                "formulaire__lignes__critere__theme",
                "reponses",
            ),
            pk=pk,
        )
        if not user_can_use_audit(request.user, audit.formulaire.type_audit):
            return render(request, "403.html", {"message": "Vous ne pouvez pas saisir les réponses de cet audit."}, status=403)

        self._ensure_reponses(audit)
        formset = ReponseAuditFormSet(instance=audit, queryset=ReponseAudit.objects.filter(audit=audit).select_related("ligne"))
        return render(request, self.template_name, {"audit": audit, "formset": formset})

    def post(self, request, pk):
        audit = get_object_or_404(Audit.objects.select_related("formulaire"), pk=pk)
        if not user_can_use_audit(request.user, audit.formulaire.type_audit):
            return render(request, "403.html", {"message": "Vous ne pouvez pas saisir les réponses de cet audit."}, status=403)

        formset = ReponseAuditFormSet(request.POST, request.FILES, instance=audit)
        try:
            with transaction.atomic():
                if formset.is_valid():
                    formset.save()
                    messages.success(request, "Réponses enregistrées avec succès.")
                    return redirect("audit:detail", pk=audit.pk)
                messages.error(request, "Le formulaire contient des erreurs.")
        except DatabaseError as exc:
            logger.exception("Erreur sauvegarde réponses audit %s", audit.pk)
            messages.error(request, f"Erreur lors de l'enregistrement des réponses : {exc}")

        return render(request, self.template_name, {"audit": audit, "formset": formset})

    @staticmethod
    def _ensure_reponses(audit: Audit):
        for ligne in audit.formulaire.lignes.all():
            ReponseAudit.objects.get_or_create(audit=audit, ligne=ligne)


# ============== Résultat post-audit ==============


class ResultatAuditDetailView(LoginRequiredMixin, CanUseAuditMixin, DetailView):
    model = ResultatAudit
    template_name = "audit/resultat/resultat.html"

    def get_queryset(self):
        return ResultatAudit.objects.select_related("audit").prefetch_related("audit__reponses")

    def get_audit_type_for_permission(self):
        return self.get_object().audit.formulaire.type_audit

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        resultat = self.object
        context["radar_labels"] = ["Conformes", "Partiels", "NC", "Niveau %"]
        context["radar_values"] = [
            resultat.nb_conformes,
            resultat.nb_partiels,
            resultat.nb_nc,
            float(resultat.niveau_prestation_pct),
        ]
        return context


class ResultatAuditUpdateView(LoginRequiredMixin, CanUseAuditMixin, SafeDbOperationMixin, Object404Mixin, UpdateView):
    model = ResultatAudit
    form_class = ResultatAuditForm
    template_name = "audit/resultat/form.html"

    def get_queryset(self):
        return ResultatAudit.objects.select_related("audit")

    def get_audit_type_for_permission(self):
        return self.get_object().audit.formulaire.type_audit

    def get_success_url(self):
        return reverse("audit:resultat-detail", kwargs={"pk": self.object.pk})


# ─── Rapport complet d'audit ─────────────────────────────────────────────────

class AuditRapportView(LoginRequiredMixin, View):
    """Page rapport complet d'un audit : KPIs, SWOT éditable, lignes & réponses."""
    template_name = "audit/audit/rapport.html"

    def _get_audit(self, pk):
        return get_object_or_404(
            Audit.objects.select_related(
                "formulaire", "formulaire__section", "responsable_audit", "cree_par"
            ).prefetch_related(
                "participants__user",
                "reponses__ligne__critere__theme",
                "reponses__ligne__critere__preuves_attendues",
                "reponses__cotation",
                "reponses__images",
            ),
            pk=pk,
        )

    def get(self, request, pk):
        audit = self._get_audit(pk)
        if not user_can_use_audit(request.user, audit.formulaire.type_audit):
            return render(request, "403.html", {"message": "Accès non autorisé."}, status=403)
        resultat, _ = ResultatAudit.objects.get_or_create(audit=audit)

        # Build lignes data with responses
        reponses_map = {r.ligne_id: r for r in audit.reponses.all()}
        lignes_data = []
        for i, ligne in enumerate(audit.formulaire.lignes.select_related("critere__theme").prefetch_related(
            "critere__preuves_attendues"
        ), 1):
            rep = reponses_map.get(ligne.pk)
            lignes_data.append({
                "num": i,
                "ligne": ligne,
                "reponse": rep,
                "cotation": rep.cotation if rep else None,
            })

        # SWOT help: PC criteria for points_sensibles, NC/NA for risques
        pc_lignes = [
            ld for ld in lignes_data
            if ld["cotation"] and ld["cotation"].code.upper() == "PC"
        ]
        nc_na_lignes = [
            ld for ld in lignes_data
            if ld["cotation"] and ld["cotation"].code.upper() in ("NC", "NA")
        ]

        # KPI counts by code
        from collections import Counter
        code_counts = Counter()
        for ld in lignes_data:
            if ld["cotation"]:
                code_counts[ld["cotation"].code.upper()] += 1

        # Niveau attendu for this type
        from .models import NiveauxAttendus
        niveau_attendu_obj = (
            NiveauxAttendus.objects.filter(type_audit=audit.formulaire.type_audit)
            .order_by("-valeur").first()
        )

        return render(request, self.template_name, {
            "audit": audit,
            "resultat": resultat,
            "lignes_data": lignes_data,
            "pc_lignes": pc_lignes,
            "nc_na_lignes": nc_na_lignes,
            "code_counts": code_counts,
            "niveau_attendu_obj": niveau_attendu_obj,
            "save_swot_url": reverse("audit:ajax-save-swot", kwargs={"pk": audit.pk}),
            "csrf_token": request.META.get("CSRF_COOKIE", ""),
            "can_create": user_can_create_audit(request.user, audit.formulaire.type_audit),
            "can_use": user_can_use_audit(request.user, audit.formulaire.type_audit),
        })


@login_required_fn
@require_POST
def ajax_save_swot(request, pk):
    """Sauvegarde AJAX des champs SWOT du résultat d'audit."""
    audit = get_object_or_404(Audit, pk=pk)
    if not user_can_use_audit(request.user, audit.formulaire.type_audit):
        return JsonResponse({"ok": False, "error": "Accès refusé."}, status=403)
    resultat, _ = ResultatAudit.objects.get_or_create(audit=audit)
    field = request.POST.get("field")
    value = request.POST.get("value", "")
    allowed = {"points_forts", "risques", "opportunites", "points_sensibles"}
    if field not in allowed:
        return JsonResponse({"ok": False, "error": "Champ invalide."})
    setattr(resultat, field, value)
    resultat.save(update_fields=[field])
    return JsonResponse({"ok": True})


@login_required_fn
def norme_pdf_view(request, pk):
    """
    Sert une page HTML embarquant PDF.js pour afficher le PDF à la bonne page
    sur tous les appareils (desktop + mobile).
    ?page=N  — numéro de page (défaut : 1)
    """
    from django.http import HttpResponse, Http404
    norme = get_object_or_404(NormeDocument, pk=pk)
    if not norme.fichier:
        raise Http404("Aucun fichier PDF associé à cette norme.")
    try:
        page = max(1, int(request.GET.get('page', 1)))
    except (ValueError, TypeError):
        page = 1
    pdf_url = request.build_absolute_uri(norme.fichier.url)
    titre   = norme.nom.replace('"', '&quot;')
    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{titre}</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/pdf.js/4.2.67/pdf.min.mjs" type="module"></script>
<style>
  *{{margin:0;padding:0;box-sizing:border-box}}
  html,body{{width:100%;height:100%;background:#525659;overflow:hidden;font-family:sans-serif}}
  #toolbar{{display:flex;align-items:center;gap:8px;padding:6px 12px;background:#3c3f41;color:#fff;font-size:13px;flex-shrink:0}}
  #toolbar button{{background:#555;color:#fff;border:none;padding:4px 10px;border-radius:4px;cursor:pointer;font-size:13px}}
  #toolbar button:hover{{background:#1a73e8}}
  #toolbar input{{width:48px;text-align:center;background:#555;color:#fff;border:1px solid #777;border-radius:4px;padding:3px 4px;font-size:13px}}
  #wrap{{width:100%;height:calc(100% - 38px);overflow:auto;display:flex;flex-direction:column;align-items:center;padding:12px 0;gap:8px}}
  canvas{{box-shadow:0 2px 8px rgba(0,0,0,.5)}}
  #loading{{color:#ccc;margin-top:40px;font-size:14px}}
</style>
</head>
<body>
<div id="toolbar">
  <button onclick="changePage(-1)">&#8249;</button>
  <input type="number" id="pageInput" min="1" value="{page}" onchange="goToPage(parseInt(this.value))">
  <span>/ <span id="totalPages">—</span></span>
  <button onclick="changePage(1)">&#8250;</button>
  <span style="flex:1"></span>
  <a href="{pdf_url}" download style="color:#adf;font-size:12px;text-decoration:none"><i>⬇ Télécharger</i></a>
</div>
<div id="wrap"><div id="loading">Chargement…</div></div>
<script type="module">
import * as pdfjsLib from 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/4.2.67/pdf.min.mjs';
pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/4.2.67/pdf.worker.min.mjs';

const PDF_URL = "{pdf_url}";
let pdfDoc = null, currentPage = {page}, scale = window.devicePixelRatio > 1 ? 1.2 : 1.5;

const wrap = document.getElementById('wrap');

async function renderPage(num) {{
  document.getElementById('pageInput').value = num;
  const page = await pdfDoc.getPage(num);
  const viewport = page.getViewport({{scale: Math.min(scale, (wrap.clientWidth - 24) / page.getViewport({{scale:1}}).width)}});
  let canvas = document.getElementById('canvas' + num);
  if (!canvas) {{
    canvas = document.createElement('canvas');
    canvas.id = 'canvas' + num;
    wrap.innerHTML = '';
    wrap.appendChild(canvas);
  }}
  canvas.height = viewport.height;
  canvas.width  = viewport.width;
  await page.render({{canvasContext: canvas.getContext('2d'), viewport}}).promise;
}}

(async function() {{
  document.getElementById('loading').textContent = 'Chargement…';
  pdfDoc = await pdfjsLib.getDocument(PDF_URL).promise;
  document.getElementById('totalPages').textContent = pdfDoc.numPages;
  document.getElementById('pageInput').max = pdfDoc.numPages;
  currentPage = Math.min({page}, pdfDoc.numPages);
  await renderPage(currentPage);
  document.getElementById('loading') && (document.getElementById('loading').style.display='none');
}})();

window.changePage = function(dir) {{
  const n = currentPage + dir;
  if (pdfDoc && n >= 1 && n <= pdfDoc.numPages) {{ currentPage = n; renderPage(n); }}
}};
window.goToPage = function(n) {{
  if (pdfDoc && n >= 1 && n <= pdfDoc.numPages) {{ currentPage = n; renderPage(n); }}
}};
window.addEventListener('resize', () => renderPage(currentPage));
</script>
</body></html>"""
    response = HttpResponse(html, content_type='text/html; charset=utf-8')
    return response


@login_required_fn
def audit_pdf(request, pk):
    """Génère un PDF professionnel A4 du rapport d'audit via WeasyPrint."""
    from weasyprint import HTML, CSS
    from django.http import HttpResponse

    audit = get_object_or_404(
        Audit.objects.select_related(
            "formulaire__section", "responsable_audit", "cree_par"
        ).prefetch_related(
            "participants__user",
            "reponses__ligne__critere__theme",
            "reponses__ligne__critere__preuves_attendues",
            "reponses__cotation",
            "reponses__images",
        ),
        pk=pk,
    )
    resultat, _ = ResultatAudit.objects.get_or_create(audit=audit)

    lignes = list(audit.formulaire.lignes.select_related(
        "critere__theme"
    ).prefetch_related(
        "critere__preuves_attendues",
    ).order_by("id"))

    reponses_map = {r.ligne_id: r for r in audit.reponses.select_related("cotation").prefetch_related("images")}
    from collections import Counter
    code_counts = Counter()
    lignes_data = []
    for i, ligne in enumerate(lignes, start=1):
        rep = reponses_map.get(ligne.pk)
        cotation = rep.cotation if rep else None
        if cotation:
            code_counts[cotation.code.upper()] += 1
        lignes_data.append({"num": i, "ligne": ligne, "reponse": rep, "cotation": cotation})

    # Logo en base64 pour WeasyPrint
    import base64
    from django.contrib.staticfiles import finders as static_finders
    _logo_path = static_finders.find("dist/img/abserveLogo.png")
    _logo_b64 = ""
    if _logo_path:
        with open(_logo_path, "rb") as _f:
            _logo_b64 = "data:image/png;base64," + base64.b64encode(_f.read()).decode()

    html_string = render_to_string("audit/audit/rapport_pdf.html", {
        "audit": audit,
        "resultat": resultat,
        "lignes_data": lignes_data,
        "code_counts": code_counts,
        "request": request,
        "logo_b64": _logo_b64,
    })

    pdf_file = HTML(string=html_string, base_url=request.build_absolute_uri("/")).write_pdf()
    response = HttpResponse(pdf_file, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="rapport-audit-{audit.numero}.pdf"'
    return response


# ============== Pages d'erreur personnalisées ==============


def custom_403_view(request, exception=None):
    """Page 403 personnalisée AdminLTE."""
    return render(request, "403.html", status=403)


def custom_404_view(request, exception=None):
    """Page 404 personnalisée AdminLTE."""
    return render(request, "404.html", status=404)
