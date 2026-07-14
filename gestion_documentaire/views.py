"""Vues du module gestion documentaire."""

from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.base import ContentFile
from django.db.models import Q
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DetailView, TemplateView, UpdateView, View

from .forms import (
    DocumentFilterForm,
    DocumentForm,
    DossierDocumentaireForm,
    DossierParametresForm,
    FichierBibliothequeForm,
    NouvelleRegleAccesFormSet,
    RegleAccesDossierFormSet,
    VersionDocumentForm,
)
from .models import (
    Document,
    DossierDocumentaire,
    FichierBibliotheque,
    RegleAccesDossier,
    ValidationDocument,
    VersionDocument,
)
from .permissions import (
    DirectionOuHabiliteRequiredMixin,
    DocumentVisibilityQuerysetMixin,
    PiloteOuQSERequiredMixin,
    QSERequiredMixin,
    ModuleDocumentaireRequiredMixin,
    ModificationBibliothequeRequiredMixin,
    direction_ou_habilite_required,
    filter_documents_for_user,
    is_direction_ou_habilite,
    is_pilote_ou_qse,
    is_qse,
    pilote_ou_qse_required,
    modification_bibliotheque_required,
    module_documentaire_required,
    peut_modifier_bibliotheque,
    qse_required,
)


def _get_latest_version(document: Document):
    return document.versions.order_by("-version", "-indice", "-date_creation").first()


def _transition_document_with_trace(document: Document, nouveau_statut: str, user, commentaire: str = ""):
    """Applique une transition au document ou à sa version active si disponible."""
    version = _get_latest_version(document)
    if version and version.statut == document.statut:
        version.transitionner_statut(nouveau_statut, utilisateur=user, commentaire=commentaire)
    else:
        document.transitionner_statut(nouveau_statut, utilisateur=user, commentaire=commentaire)


class DocumentListView(ModuleDocumentaireRequiredMixin, TemplateView):
    """Explorateur de dossiers et fichiers de la bibliothèque."""

    template_name = "gestion_documentaire/document_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        dossier_id = self.kwargs.get("dossier_id")
        if dossier_id:
            dossier = get_object_or_404(DossierDocumentaire, pk=dossier_id)
        elif self.kwargs.get("racine"):
            dossier = None
        else:
            dossier = DossierDocumentaire.objects.filter(
                parent__isnull=True, nom="05 - Gestion documentaire"
            ).first()

        if dossier and not dossier.utilisateur_autorise(self.request.user, "lire"):
            raise PermissionDenied("Vous n'avez pas accès à ce dossier.")

        recherche = self.request.GET.get("q", "").strip()
        sous_dossiers = list(DossierDocumentaire.objects.filter(parent=dossier))
        sous_dossiers = [d for d in sous_dossiers if d.utilisateur_autorise(self.request.user, "lire")]
        for enfant in sous_dossiers:
            enfant.peut_editer = (
                peut_modifier_bibliotheque(self.request.user)
                and enfant.utilisateur_autorise(self.request.user, "modifier")
            )
            enfant.peut_supprimer = (
                peut_modifier_bibliotheque(self.request.user)
                and enfant.utilisateur_autorise(self.request.user, "modifier")
            )
        fichiers = FichierBibliotheque.objects.filter(dossier=dossier).select_related("ajoute_par")
        if recherche:
            sous_dossiers = [d for d in sous_dossiers if recherche.lower() in d.nom.lower()]
            fichiers = fichiers.filter(nom__icontains=recherche)

        context.update({
            "dossier_actuel": dossier,
            "fil_ariane": dossier.get_ancestors() if dossier else [],
            "sous_dossiers": sous_dossiers,
            "fichiers": fichiers,
            "dossier_form": DossierParametresForm(),
            "nouveau_regles_formset": NouvelleRegleAccesFormSet(
                queryset=RegleAccesDossier.objects.none(),
                prefix="new_rules",
            ),
            "fichier_form": FichierBibliothequeForm(),
            "peut_modifier": peut_modifier_bibliotheque(self.request.user),
            "peut_ajouter": peut_modifier_bibliotheque(self.request.user) and (
                not dossier or dossier.utilisateur_autorise(self.request.user, "modifier")
            ),
            "peut_editer": peut_modifier_bibliotheque(self.request.user) and (
                not dossier or dossier.utilisateur_autorise(self.request.user, "modifier")
            ),
            "peut_supprimer": peut_modifier_bibliotheque(self.request.user) and (
                not dossier or dossier.utilisateur_autorise(self.request.user, "modifier")
            ),
            "peut_telecharger": not dossier or dossier.utilisateur_autorise(
                self.request.user, "telecharger"
            ),
            "vue": self.request.GET.get("vue", "liste"),
            "recherche": recherche,
        })
        return context


@method_decorator([login_required, modification_bibliotheque_required], name="dispatch")
class DossierCreateView(View):
    def post(self, request, dossier_id=None, *args, **kwargs):
        parent = get_object_or_404(DossierDocumentaire, pk=dossier_id) if dossier_id else None
        if parent and not parent.utilisateur_autorise(request.user, "modifier"):
            raise PermissionDenied("Vous n'avez pas le droit d'ajouter dans ce dossier.")
        form = DossierParametresForm(request.POST)
        regles_formset = NouvelleRegleAccesFormSet(
            request.POST,
            queryset=RegleAccesDossier.objects.none(),
            prefix="new_rules",
        )
        regles_valides = regles_formset.is_valid()
        regles_actives = [
            regle_form for regle_form in regles_formset.forms
            if regle_form.has_changed() and not regle_form.cleaned_data.get("DELETE")
        ] if regles_valides else []
        if form.is_valid() and regles_valides and (
            not form.cleaned_data.get("acces_restreint") or regles_actives
        ):
            dossier = form.save(commit=False)
            dossier.parent = parent
            dossier.cree_par = request.user
            dossier.save()
            for regle_form in regles_actives:
                regle = regle_form.save(commit=False)
                regle.dossier = dossier
                regle.save()
                regle_form.instance = regle
                regle_form.save_m2m()
            messages.success(request, f'Dossier « {dossier.nom} » créé.')
            if dossier.acces_restreint:
                return redirect("gestion_documentaire:modifier_dossier", pk=dossier.pk)
        else:
            messages.error(
                request,
                "Le dossier n'a pas pu être créé. Vérifiez les informations et ajoutez au moins une règle si l'accès est limité.",
            )
        if parent:
            return redirect("gestion_documentaire:dossier_detail", dossier_id=parent.pk)
        return redirect("gestion_documentaire:document_list")


def _retour_dossier(dossier):
    if dossier:
        return redirect("gestion_documentaire:dossier_detail", dossier_id=dossier.pk)
    return redirect("gestion_documentaire:bibliotheque_racine")


@login_required
@modification_bibliotheque_required
@require_POST
def uploader_fichiers(request, dossier_id=None):
    dossier = get_object_or_404(DossierDocumentaire, pk=dossier_id) if dossier_id else None
    if dossier and not dossier.utilisateur_autorise(request.user, "modifier"):
        raise PermissionDenied("Vous n'avez pas le droit d'ajouter dans ce dossier.")
    fichiers = request.FILES.getlist("fichier")
    if not fichiers:
        messages.error(request, "Sélectionnez au moins un fichier.")
        return _retour_dossier(dossier)
    ajoutes = 0
    for upload in fichiers:
        form = FichierBibliothequeForm(files={"fichier": upload})
        if not form.is_valid():
            messages.error(request, f"{upload.name} : {form.errors.as_text()}")
            continue
        if FichierBibliotheque.objects.filter(dossier=dossier, nom=upload.name).exists():
            messages.error(request, f"{upload.name} existe déjà dans ce dossier.")
            continue
        FichierBibliotheque.objects.create(
            dossier=dossier, fichier=upload, nom=upload.name, taille=upload.size,
            type_mime=upload.content_type or "", ajoute_par=request.user,
        )
        ajoutes += 1
    if ajoutes:
        messages.success(request, f"{ajoutes} fichier(s) ajouté(s).")
    return _retour_dossier(dossier)


@login_required
@modification_bibliotheque_required
def modifier_dossier(request, pk):
    dossier = get_object_or_404(DossierDocumentaire, pk=pk)
    if not dossier.utilisateur_autorise(request.user, "modifier"):
        raise PermissionDenied("Vous n'avez pas le droit de modifier ce dossier.")
    if request.method == "GET":
        return render(
            request,
            "gestion_documentaire/dossier_form.html",
            {
                "form": DossierParametresForm(instance=dossier),
                "regles_formset": RegleAccesDossierFormSet(instance=dossier),
                "dossier": dossier,
            },
        )
    ancien_nom = dossier.nom
    form = DossierParametresForm(request.POST, instance=dossier)
    regles_formset = RegleAccesDossierFormSet(request.POST, instance=dossier)
    if form.is_valid() and regles_formset.is_valid():
        form.save()
        regles_formset.save()
        if ancien_nom != dossier.nom:
            def deplacer_contenu(courant):
                for fichier in courant.fichiers.all():
                    ancien_chemin = fichier.fichier.name
                    contenu = ContentFile(fichier.fichier.read())
                    fichier.fichier.save(fichier.nom, contenu, save=True)
                    if ancien_chemin != fichier.fichier.name:
                        fichier.fichier.storage.delete(ancien_chemin)
                for enfant in courant.sous_dossiers.all():
                    deplacer_contenu(enfant)
            deplacer_contenu(dossier)
        messages.success(request, "Dossier modifié.")
    else:
        return render(
            request,
            "gestion_documentaire/dossier_form.html",
            {"form": form, "regles_formset": regles_formset, "dossier": dossier},
            status=400,
        )
    return redirect("gestion_documentaire:dossier_detail", dossier_id=dossier.pk)


@login_required
@modification_bibliotheque_required
@require_POST
def supprimer_dossier(request, pk):
    dossier = get_object_or_404(DossierDocumentaire, pk=pk)
    if not dossier.utilisateur_autorise(request.user, "modifier"):
        raise PermissionDenied("Vous n'avez pas le droit de supprimer ce dossier.")
    parent = dossier.parent
    def supprimer_contenu(courant):
        for enfant in courant.sous_dossiers.all():
            supprimer_contenu(enfant)
        for fichier in courant.fichiers.all():
            fichier.delete()
    supprimer_contenu(dossier)
    dossier.delete()
    messages.success(request, "Dossier supprimé.")
    return _retour_dossier(parent)


@login_required
@modification_bibliotheque_required
@require_POST
def renommer_fichier(request, pk):
    objet = get_object_or_404(FichierBibliotheque, pk=pk)
    if objet.dossier and not objet.dossier.utilisateur_autorise(request.user, "modifier"):
        raise PermissionDenied("Vous n'avez pas le droit de modifier ce fichier.")
    nouveau_nom = request.POST.get("nom", "").strip()
    extension_originale = objet.extension
    if not nouveau_nom:
        messages.error(request, "Le nom est obligatoire.")
    else:
        if not nouveau_nom.lower().endswith(extension_originale):
            nouveau_nom += extension_originale
        if FichierBibliotheque.objects.filter(dossier=objet.dossier, nom=nouveau_nom).exclude(pk=pk).exists():
            messages.error(request, "Un fichier porte déjà ce nom.")
        else:
            ancien_chemin = objet.fichier.name
            contenu = ContentFile(objet.fichier.read())
            objet.nom = nouveau_nom
            objet.fichier.save(nouveau_nom, contenu, save=True)
            if ancien_chemin != objet.fichier.name:
                objet.fichier.storage.delete(ancien_chemin)
            objet.save(update_fields=["nom", "date_modification"])
            messages.success(request, "Fichier renommé.")
    return _retour_dossier(objet.dossier)


@login_required
@modification_bibliotheque_required
@require_POST
def supprimer_fichier(request, pk):
    objet = get_object_or_404(FichierBibliotheque, pk=pk)
    if objet.dossier and not objet.dossier.utilisateur_autorise(request.user, "modifier"):
        raise PermissionDenied("Vous n'avez pas le droit de supprimer ce fichier.")
    dossier = objet.dossier
    objet.delete()
    messages.success(request, "Fichier supprimé.")
    return _retour_dossier(dossier)


@login_required
@module_documentaire_required
def telecharger_fichier_bibliotheque(request, pk):
    objet = get_object_or_404(FichierBibliotheque.objects.select_related("dossier"), pk=pk)
    if objet.dossier and not objet.dossier.utilisateur_autorise(request.user, "telecharger"):
        return HttpResponse(status=403)
    return FileResponse(
        objet.fichier.open("rb"), as_attachment=True, filename=objet.nom,
        content_type=objet.type_mime or "application/octet-stream",
    )


@login_required
@module_documentaire_required
def visualiser_fichier_bibliotheque(request, pk):
    """Aperçu sécurisé : PDF natif, fiche moderne pour les formats bureautiques."""
    objet = get_object_or_404(FichierBibliotheque.objects.select_related("dossier"), pk=pk)
    if objet.dossier and not objet.dossier.utilisateur_autorise(request.user, "lire"):
        return HttpResponse(status=403)

    if objet.extension == ".pdf":
        try:
            response = FileResponse(
                objet.fichier.open("rb"),
                as_attachment=False,
                filename=objet.nom,
                content_type="application/pdf",
            )
            response["Content-Disposition"] = f'inline; filename="{objet.nom}"'
            response["X-Content-Type-Options"] = "nosniff"
            return response
        except FileNotFoundError as exc:
            raise Http404("Fichier introuvable.") from exc

    peut_telecharger = (
        objet.dossier is None
        or objet.dossier.utilisateur_autorise(request.user, "telecharger")
    )
    response = render(
        request,
        "gestion_documentaire/fichier_preview.html",
        {"fichier": objet, "peut_telecharger": peut_telecharger},
    )
    response["Content-Security-Policy"] = (
        "default-src 'none'; style-src 'unsafe-inline'; "
        "img-src 'self'; frame-ancestors 'self'; base-uri 'none'; form-action 'none'"
    )
    response["X-Content-Type-Options"] = "nosniff"
    return response


class DocumentDetailView(ModuleDocumentaireRequiredMixin, DocumentVisibilityQuerysetMixin, DetailView):
    """Détail documentaire avec historique des versions."""

    model = Document
    template_name = "gestion_documentaire/document_detail.html"
    context_object_name = "document"

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related("processus_service", "cree_par")
            .prefetch_related("versions__redacteur", "validations__utilisateur")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        document = self.object
        versions = document.versions.order_by("-version", "-indice", "-date_creation")
        context["versions"] = versions
        context["version_active"] = versions.filter(statut=Document.Statut.APPLICABLE).first() or versions.first()
        context["version_form"] = VersionDocumentForm()
        context["is_qse_user"] = is_qse(self.request.user)
        context["is_pilote_ou_qse_user"] = is_pilote_ou_qse(self.request.user)
        context["is_direction_ou_habilite_user"] = is_direction_ou_habilite(self.request.user)
        return context


class DocumentCreateView(ModificationBibliothequeRequiredMixin, CreateView):
    """Création d'un document en brouillon."""

    model = Document
    form_class = DocumentForm
    template_name = "gestion_documentaire/document_form.html"

    def get_initial(self):
        initial = super().get_initial()
        dossier_id = self.request.GET.get("dossier")
        if dossier_id and DossierDocumentaire.objects.filter(pk=dossier_id).exists():
            initial["dossier"] = dossier_id
        return initial

    def form_valid(self, form):
        form.instance.cree_par = self.request.user
        form.instance.statut = Document.Statut.BROUILLON
        response = super().form_valid(form)
        ValidationDocument.objects.create(
            document=self.object,
            type_action=ValidationDocument.TypeAction.REDACTION,
            utilisateur=self.request.user,
            commentaire="Création du brouillon documentaire.",
            ancien_statut="",
            nouveau_statut=Document.Statut.BROUILLON,
        )
        messages.success(self.request, "Document créé en brouillon.")
        return response

    def get_success_url(self):
        return reverse("gestion_documentaire:document_detail", kwargs={"pk": self.object.pk})


class DocumentUpdateView(ModificationBibliothequeRequiredMixin, UpdateView):
    """Mise à jour du contenu documentaire."""

    model = Document
    form_class = DocumentForm
    template_name = "gestion_documentaire/document_form.html"

    def get_queryset(self):
        return Document.objects.filter(est_supprime=False)

    def form_valid(self, form):
        response = super().form_valid(form)
        ValidationDocument.objects.create(
            document=self.object,
            type_action=ValidationDocument.TypeAction.REDACTION,
            utilisateur=self.request.user,
            commentaire="Mise à jour du contenu documentaire.",
            ancien_statut=self.object.statut,
            nouveau_statut=self.object.statut,
        )
        messages.success(self.request, "Document mis à jour.")
        return response

    def get_success_url(self):
        return reverse("gestion_documentaire:document_detail", kwargs={"pk": self.object.pk})


class DashboardQSEView(ModuleDocumentaireRequiredMixin, TemplateView):
    """Vue d'ensemble de la bibliothèque documentaire."""

    template_name = "gestion_documentaire/dashboard_qse.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        dossiers = [
            dossier for dossier in DossierDocumentaire.objects.select_related("parent")
            if dossier.utilisateur_autorise(self.request.user, "lire")
        ]
        dossier_ids = [dossier.pk for dossier in dossiers]
        fichiers = list(FichierBibliotheque.objects.filter(
            Q(dossier_id__in=dossier_ids) | Q(dossier__isnull=True)
        ).select_related("dossier", "ajoute_par"))
        for fichier in fichiers:
            fichier.peut_telecharger = (
                fichier.dossier is None
                or fichier.dossier.utilisateur_autorise(self.request.user, "telecharger")
            )
        context["total_dossiers"] = len(dossiers)
        context["total_fichiers"] = len(fichiers)
        context["total_taille"] = sum(f.taille for f in fichiers)
        context["dossiers_restraints"] = sum(1 for d in dossiers if d.acces_restreint)
        context["fichiers_recents"] = sorted(
            fichiers, key=lambda f: f.date_modification, reverse=True
        )[:10]
        context["dossiers_recents"] = sorted(
            dossiers, key=lambda d: d.date_modification, reverse=True
        )[:8]
        context["peut_modifier"] = peut_modifier_bibliotheque(self.request.user)
        return context


@method_decorator([login_required, modification_bibliotheque_required], name="dispatch")
class CreerNouvelleVersionView(View):
    """Crée une nouvelle version documentaire avec incrément version/indice."""

    def post(self, request, pk, *args, **kwargs):
        document = get_object_or_404(Document, pk=pk, est_supprime=False)
        form = VersionDocumentForm(request.POST, request.FILES)
        if not form.is_valid():
            messages.error(request, "Impossible de créer la nouvelle version.")
            versions = document.versions.order_by("-version", "-indice", "-date_creation")
            context = {
                "document": document,
                "versions": versions,
                "version_active": versions.filter(statut=Document.Statut.APPLICABLE).first() or versions.first(),
                "version_form": form,
                "is_qse_user": is_qse(request.user),
                "is_pilote_ou_qse_user": is_pilote_ou_qse(request.user),
                "is_direction_ou_habilite_user": is_direction_ou_habilite(request.user),
            }
            return render(request, "gestion_documentaire/document_detail.html", context, status=400)

        derniere_version = _get_latest_version(document)
        if derniere_version is None:
            next_version = 1
            next_indice = 0
        elif form.cleaned_data["type_increment"] == VersionDocumentForm.TypeIncrement.MAJEUR:
            next_version = derniere_version.version + 1
            next_indice = 0
        else:
            next_version = derniere_version.version
            next_indice = derniere_version.indice + 1

        version = form.save(commit=False)
        version.document = document
        version.version = next_version
        version.indice = next_indice
        version.redacteur = request.user
        version.statut = Document.Statut.BROUILLON
        version.copie_non_maitrisee = True
        version.save()

        ValidationDocument.objects.create(
            document=document,
            version_document=version,
            type_action=ValidationDocument.TypeAction.REDACTION,
            utilisateur=request.user,
            commentaire=form.cleaned_data.get("resume_changements", "Nouvelle version créée."),
            ancien_statut=document.statut,
            nouveau_statut=document.statut,
        )

        messages.success(
            request,
            f"Nouvelle version créée: v{version.version}.{version.indice}.",
        )
        return redirect("gestion_documentaire:document_detail", pk=document.pk)


@login_required
@modification_bibliotheque_required
def soumettre_verification(request, pk):
    """Transition brouillon -> en_verification."""
    document = get_object_or_404(Document, pk=pk, est_supprime=False)
    try:
        _transition_document_with_trace(
            document,
            Document.Statut.EN_VERIFICATION,
            user=request.user,
            commentaire="Soumission en vérification.",
        )
    except ValidationError as exc:
        messages.error(request, "; ".join(exc.messages))
    else:
        messages.success(request, "Document soumis en vérification.")
    return redirect("gestion_documentaire:document_detail", pk=document.pk)


@login_required
@modification_bibliotheque_required
def approuver_document(request, pk):
    """Fait progresser le document jusqu'à l'état applicable."""
    document = get_object_or_404(Document, pk=pk, est_supprime=False)

    try:
        if document.statut == Document.Statut.EN_VERIFICATION:
            _transition_document_with_trace(
                document,
                Document.Statut.EN_APPROBATION,
                user=request.user,
                commentaire="Document passé en approbation.",
            )
            # Recharger le document après la première transition.
            document.refresh_from_db()

        _transition_document_with_trace(
            document,
            Document.Statut.APPLICABLE,
            user=request.user,
            commentaire="Document approuvé et rendu applicable.",
        )

        ValidationDocument.objects.create(
            document=document,
            type_action=ValidationDocument.TypeAction.APPROBATION,
            utilisateur=request.user,
            commentaire="Validation finale et mise en application.",
            ancien_statut=Document.Statut.EN_APPROBATION,
            nouveau_statut=Document.Statut.APPLICABLE,
        )
    except ValidationError as exc:
        messages.error(request, "; ".join(exc.messages))
    else:
        messages.success(request, "Document approuvé et publié.")

    return redirect("gestion_documentaire:document_detail", pk=document.pk)


@login_required
@modification_bibliotheque_required
def archiver_document(request, pk):
    """Archive un document applicable."""
    document = get_object_or_404(Document, pk=pk, est_supprime=False)
    try:
        _transition_document_with_trace(
            document,
            Document.Statut.ARCHIVE,
            user=request.user,
            commentaire="Archivage documentaire.",
        )
        ValidationDocument.objects.create(
            document=document,
            type_action=ValidationDocument.TypeAction.ARCHIVAGE,
            utilisateur=request.user,
            commentaire="Document archivé via action QSE.",
            ancien_statut=Document.Statut.APPLICABLE,
            nouveau_statut=Document.Statut.ARCHIVE,
        )
    except ValidationError as exc:
        messages.error(request, "; ".join(exc.messages))
    else:
        messages.success(request, "Document archivé.")

    return redirect("gestion_documentaire:document_detail", pk=document.pk)


@login_required
@module_documentaire_required
def exporter_document_pdf(request, pk):
    """Export PDF non modifiable (cohérent avec WeasyPrint déjà utilisé)."""
    document = get_object_or_404(Document.objects.filter(est_supprime=False), pk=pk)

    # Contrôle d'accès équivalent à la visibilité des documents.
    visible = filter_documents_for_user(Document.objects.filter(pk=pk), request.user)
    if not visible.exists():
        return HttpResponse(status=403)

    version = (
        document.versions.filter(statut=Document.Statut.APPLICABLE)
        .order_by("-version", "-indice", "-date_creation")
        .first()
        or _get_latest_version(document)
    )
    version_label = f"v{version.version}.{version.indice}" if version else "N/A"

    html = f"""
    <html>
    <head>
      <meta charset="utf-8" />
      <style>
        body {{ font-family: Arial, sans-serif; font-size: 12px; margin: 24px; }}
        h1 {{ font-size: 18px; margin-bottom: 6px; }}
        .meta {{ margin-bottom: 12px; color: #333; }}
        .watermark {{
          position: fixed;
          top: 40%;
          left: 10%;
          transform: rotate(-28deg);
          font-size: 54px;
          color: rgba(180, 0, 0, 0.12);
          letter-spacing: 2px;
          z-index: -1;
          white-space: nowrap;
        }}
        .section {{ margin-bottom: 10px; }}
      </style>
    </head>
    <body>
        <div class="watermark">COPIE NON MAITRISEE</div>
      <h1>{document.code_documentaire} - {document.titre}</h1>
        <div class="meta">Statut: {document.get_statut_display()} | Date export: {timezone.localdate().isoformat()}</div>
        <div class="meta">Version: {version_label}</div>
        <div class="section"><strong>Objet:</strong><br/>{document.objet or ''}</div>
        <div class="section"><strong>Domaine d'application:</strong><br/>{document.domaine_application or ''}</div>
        <div class="section"><strong>Règles / étapes:</strong><br/>{document.regles_etapes or ''}</div>
        <div class="section"><strong>Responsabilités:</strong><br/>{document.responsabilites or ''}</div>
    </body>
    </html>
    """

    try:
        from weasyprint import HTML
    except Exception:
        return HttpResponse("WeasyPrint est requis pour l'export PDF.", status=500)

    pdf_bytes = HTML(string=html).write_pdf(pdf_version="1.4")
    filename = f"{document.code_documentaire}_{timezone.localdate().isoformat()}.pdf"
    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@login_required
@module_documentaire_required
def fichier_version(request, pk, nature):
    """Sert un fichier après contrôle de visibilité, en aperçu ou téléchargement."""
    version = get_object_or_404(
        VersionDocument.objects.select_related("document"),
        pk=pk,
        est_supprime=False,
    )
    if not filter_documents_for_user(
        Document.objects.filter(pk=version.document_id), request.user
    ).exists():
        return HttpResponse(status=403)

    if nature == "reference":
        fichier = version.fichier_reference
        content_type = "application/pdf"
    elif nature == "editable":
        fichier = version.fichier_editable
        content_type = "application/octet-stream"
    else:
        raise Http404
    if not fichier:
        raise Http404

    inline = nature == "reference" and request.GET.get("download") != "1"
    try:
        return FileResponse(
            fichier.open("rb"),
            as_attachment=not inline,
            filename=fichier.name.rsplit("/", 1)[-1],
            content_type=content_type,
        )
    except FileNotFoundError as exc:
        raise Http404("Fichier introuvable.") from exc
