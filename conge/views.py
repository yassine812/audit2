"""Vues du module Gestion des Congés."""

import base64
import logging
import os
from datetime import date
from io import BytesIO

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import FileResponse, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.views.decorators.clickjacking import xframe_options_exempt

from .forms import DemandeCongeForm, ValidationCongeForm
from .models import DemandeConge
from .validation import (
    peut_valider_conge,
    peut_voir_conge,
    get_validation_chain_for_demande,
    get_prochains_validateurs,
    marquer_validation,
    refuser_conge,
    _get_societe,
    _societe_q,
)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Helper PDF (WeasyPrint)
# ─────────────────────────────────────────────────────────────────────────────

def _generer_pdf_demande(demande, exemplaire: str, request=None) -> bytes:
    """
    Génère les bytes PDF d'une demande de congé via WeasyPrint.

    Utilise un base_url basé sur le système de fichiers (file://) pour éviter
    les requêtes HTTP internes — fiable en développement comme en production.
    """
    from django.conf import settings as django_settings
    from django.contrib.staticfiles import finders as _finders
    from weasyprint import HTML as WeasyprintHTML

    # Résolution du logo : finders → STATIC_ROOT → assets/ à la racine
    logo_b64 = ""
    logo_path = _finders.find("dist/img/abserveLogo.png")
    if not logo_path:
        # Fallback : STATIC_ROOT après collectstatic
        candidate = django_settings.STATIC_ROOT / "dist" / "img" / "abserveLogo.png"
        if candidate.exists():
            logo_path = str(candidate)
    if not logo_path:
        # Fallback : assets/ à la racine du projet
        candidate = django_settings.BASE_DIR / "assets" / "abserveLogo.png"
        if candidate.exists():
            logo_path = str(candidate)
    if logo_path:
        with open(logo_path, "rb") as fh:
            logo_b64 = "data:image/png;base64," + base64.b64encode(fh.read()).decode()

    # Le template PDF est autonome (pas de base.html, pas de tags URL).
    # On n'utilise PAS request pour éviter l'exécution des context processors
    # (notifications, firebase…) qui peuvent échouer et masquer l'erreur.
    html_str = render_to_string(
        "conge/pdf_demande.html",
        {"demande": demande, "exemplaire": exemplaire, "logo_b64": logo_b64},
    )

    # base_url en file:// → WeasyPrint résout les chemins localement,
    # sans aucune requête HTTP vers le serveur (critique en production).
    # pdf_version='1.4' : compatibilité maximale Chrome/Firefox/Edge (Pdfium).
    base_url = f"file://{django_settings.BASE_DIR}/"
    return WeasyprintHTML(string=html_str, base_url=base_url).write_pdf(pdf_version="1.4")


# ─────────────────────────────────────────────────────────────────────────────
# Helpers (legacy, pour compatibilité)
# ─────────────────────────────────────────────────────────────────────────────

def _is_responsable(user) -> bool:
    """True si l'utilisateur peut traiter des demandes (RS, RO, assistante, superuser)."""
    return bool(user.is_RS or user.is_RO or user.is_assistante or user.is_superuser)


def _get_visible_conges_qs(user):
    """
    Retourne le queryset des demandes de congé visibles par l'utilisateur.

    - Superadmin          → toutes
    - RS                  → ses propres + OP/CE de sa section
    - RO                  → ses propres + OP/CE/RS de sa section
                            + RO/autres (non-OP/CE/RS) de même société
    - is_assistante        → ses propres + RO/autres (non-OP/CE/RS) de même société
    - Autres              → uniquement ses propres demandes
    """
    if user.is_superuser:
        return DemandeConge.objects.all()

    qs_filter = Q(demandeur=user)

    # RS : OP/CE de sa section
    if user.is_RS and user.section:
        qs_filter |= (
            Q(section=user.section)
            & (Q(demandeur__is_OP=True) | Q(demandeur__is_CE=True))
        )

    # RO : OP/CE/RS de sa section
    if user.is_RO and user.section:
        qs_filter |= (
            Q(section=user.section)
            & (Q(demandeur__is_OP=True) | Q(demandeur__is_CE=True) | Q(demandeur__is_RS=True))
        )

    # RO ou is_assistante : RO/autres de même société
    if user.is_RO or user.is_assistante:
        societe = _get_societe(user)
        if societe:
            qs_filter |= (
                _societe_q(societe)
                & ~Q(demandeur__is_OP=True)
                & ~Q(demandeur__is_CE=True)
                & ~Q(demandeur__is_RS=True)
                & ~Q(demandeur=user)
            )

    return DemandeConge.objects.filter(qs_filter).distinct()


def _peut_voir_demande(user, demande) -> bool:
    """True si l'utilisateur a le droit de voir cette demande (legacy)."""
    return peut_voir_conge(user, demande)


def _peut_valider_demande(user, demande) -> bool:
    """True si l'utilisateur peut valider/refuser cette demande (legacy)."""
    return peut_valider_conge(user, demande)


# ─────────────────────────────────────────────────────────────────────────────
# Notifications e-mail
# ─────────────────────────────────────────────────────────────────────────────

def _notifier_responsables(demande, request) -> None:
    """
    Envoie un e-mail d'alerte aux responsables concernés selon le rôle du demandeur,
    PLUS tous les superadmins actifs (qui reçoivent toutes les alertes).

    - OP / CE  → RS et RO de la section du demandeur
    - RS       → RO de la section du demandeur
    - RO       → is_assistante de la même société
    - Autre    → is_RO + is_assistante de la même société
    + Superadmin : toujours inclus dans toutes les alertes
    """
    from django.contrib.auth import get_user_model
    User = get_user_model()

    demandeur = demande.demandeur

    # ── Destinataires spécifiques selon le rôle ───────────────────────────────
    if demandeur.is_OP or demandeur.is_CE:
        if not demande.section:
            logger.warning("Demande %s sans section — destinataires section absents.", demande.pk)
            specifiques = User.objects.none()
        else:
            specifiques = User.objects.filter(
                section=demande.section, is_active=True,
            ).filter(Q(is_RS=True) | Q(is_RO=True))

    elif demandeur.is_RS:
        if not demande.section:
            logger.warning("Demande %s sans section — destinataires section absents.", demande.pk)
            specifiques = User.objects.none()
        else:
            specifiques = User.objects.filter(
                section=demande.section, is_RO=True, is_active=True,
            )

    elif demandeur.is_RO:
        societe = _get_societe(demandeur)
        if not societe:
            logger.warning("Demande %s : société introuvable pour RO %s.", demande.pk, demandeur.username)
            specifiques = User.objects.none()
        else:
            specifiques = User.objects.filter(
                is_assistante=True, is_active=True,
            ).filter(_societe_q(societe)).exclude(pk=demandeur.pk).distinct()

    else:
        # Autres rôles (assistante, resp., divers…)
        societe = _get_societe(demandeur)
        if not societe:
            logger.warning("Demande %s : société introuvable pour %s.", demande.pk, demandeur.username)
            specifiques = User.objects.none()
        else:
            specifiques = User.objects.filter(
                Q(is_RO=True) | Q(is_assistante=True), is_active=True,
            ).filter(_societe_q(societe)).exclude(pk=demandeur.pk).distinct()

    # ── Superadmins : toujours notifiés ───────────────────────────────────────
    superadmins = User.objects.filter(is_superuser=True, is_active=True).exclude(pk=demandeur.pk)

    # ── Fusion via set d'emails (évite le |combine entre querysets distincts) ─
    destinataires = list(
        {u.email for u in specifiques if u.email}
        | {u.email for u in superadmins if u.email}
    )
    if not destinataires:
        logger.warning("Aucun destinataire e-mail pour la demande %s.", demande.pk)
        return

    try:
        html_msg = render_to_string(
            "conge/emails/notification_responsable.html",
            {"demande": demande},
            request=request,
        )
        send_mail(
            subject=f"Congé : Nouvelle demande de {demande.nom} {demande.prenom}",
            message=(
                f"Nouvelle demande de congé de {demande.nom} {demande.prenom} "
                f"du {demande.date_debut} au {demande.date_fin}."
            ),
            from_email=None,
            recipient_list=destinataires,
            html_message=html_msg,
            fail_silently=False,
        )
        logger.info("E-mail alerte congé envoyé à %s", destinataires)
    except Exception as exc:
        logger.error("Erreur envoi e-mail responsables (demande=%s): %s", demande.pk, exc)


def _notifier_demandeur(demande, request) -> None:
    """
    Notifie le demandeur de la décision (validation ou refus).
    Si la demande est validée, le PDF exemplaire demandeur est joint en pièce jointe.
    """
    if not demande.demandeur.email:
        return

    from django.core.mail import EmailMessage

    is_valide = demande.is_valide
    template  = (
        "conge/emails/notification_validation.html"
        if is_valide
        else "conge/emails/notification_refus.html"
    )
    subject = (
        "Congé : Votre demande a été validée ✓"
        if is_valide
        else "Congé : Votre demande a été refusée ✗"
    )
    try:
        html_body = render_to_string(template, {"demande": demande}, request=request)
        email = EmailMessage(
            subject=subject,
            body=html_body,
            to=[demande.demandeur.email],
        )
        email.content_subtype = "html"

        # ── Joindre le PDF exemplaire demandeur si la demande est validée ────
        if is_valide:
            try:
                pdf_bytes = _generer_pdf_demande(demande, "demandeur", request=request)
                filename = (
                    f"conge_{demande.nom}_{demande.prenom}_{demande.date_debut}_demandeur.pdf"
                ).replace(" ", "_")
                email.attach(filename, pdf_bytes, "application/pdf")
                logger.info("PDF exemplaire demandeur joint à l'e-mail de validation.")
            except Exception as exc:
                logger.warning("Impossible de joindre le PDF à l'e-mail de validation : %s", exc)

        try:
            email.send(fail_silently=False)
            logger.info("E-mail décision envoyé à %s", demande.demandeur.email)
        except Exception as exc:
            logger.error("Échec envoi e-mail décision à %s : %s", demande.demandeur.email, exc)
    except Exception as exc:
        logger.error("Erreur envoi e-mail demandeur: %s", exc)


# ─────────────────────────────────────────────────────────────────────────────
# Vues métier
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def liste_conges(request):
    """Liste paginée des demandes de congé avec sidebar filtre."""
    user = request.user

    # Queryset selon le rôle
    qs = _get_visible_conges_qs(user).select_related("demandeur", "section", "validateur")

    # Filtres
    q          = request.GET.get("q", "").strip()
    statut     = request.GET.get("statut", "").strip()
    type_conge = request.GET.get("type_conge", "").strip()
    date_debut = request.GET.get("date_debut", "").strip()
    date_fin   = request.GET.get("date_fin", "").strip()

    if q:
        qs = qs.filter(
            Q(nom__icontains=q) | Q(prenom__icontains=q)
            | Q(demandeur__username__icontains=q)
            | Q(demandeur__first_name__icontains=q)
            | Q(demandeur__last_name__icontains=q)
        )
    if statut:
        qs = qs.filter(statut=statut)
    if type_conge:
        qs = qs.filter(type_conge=type_conge)
    if date_debut:
        try:
            qs = qs.filter(date_debut__gte=date_debut)
        except Exception:
            pass
    if date_fin:
        try:
            qs = qs.filter(date_fin__lte=date_fin)
        except Exception:
            pass

    has_filters = any([q, statut, type_conge, date_debut, date_fin])

    paginator = Paginator(qs, 15)
    page_obj  = paginator.get_page(request.GET.get("page", 1))

    return render(request, "conge/liste.html", {
        "page_obj":    page_obj,
        "paginator":   paginator,
        "is_paginated": paginator.num_pages > 1,
        "is_responsable": _is_responsable(user),
        "statut_choices":     DemandeConge.STATUT_CHOICES,
        "type_conge_choices": DemandeConge.TYPE_CONGE_CHOICES,
        # Filtres actifs
        "q": q, "statut": statut, "type_conge": type_conge,
        "date_debut": date_debut, "date_fin": date_fin,
        "has_filters": has_filters,
    })


@login_required
def nouvelle_demande(request):
    """Formulaire de création d'une nouvelle demande de congé."""
    user = request.user

    if request.method == "POST":
        form = DemandeCongeForm(request.POST)
        if form.is_valid():
            demande = form.save(commit=False)
            demande.demandeur = user
            demande.section   = user.section
            # Sécuriser nom/prénom depuis le profil si vides
            if not demande.nom:
                demande.nom = user.last_name or user.username
            if not demande.prenom:
                demande.prenom = user.first_name or ""
            demande.save()
            _notifier_responsables(demande, request)
            messages.success(
                request,
                "Votre demande de congé a été soumise. "
                "Les responsables de votre section ont été notifiés par e-mail.",
            )
            return redirect("conge:detail", pk=demande.pk)
        else:
            messages.error(request, "Veuillez corriger les erreurs du formulaire.")
    else:
        form = DemandeCongeForm(initial={
            "nom":    user.last_name  or "",
            "prenom": user.first_name or "",
        })
        # Marquer readonly si l'utilisateur a déjà ces données dans son profil
        if user.last_name:
            form.fields["nom"].widget.attrs.update({"readonly": True, "class": "form-control bg-light"})
        if user.first_name:
            form.fields["prenom"].widget.attrs.update({"readonly": True, "class": "form-control bg-light"})

    return render(request, "conge/demande_form.html", {
        "form": form,
        "user": user,
    })


@login_required
def detail_conge(request, pk: int):
    """Détail d'une demande de congé."""
    user    = request.user
    demande = get_object_or_404(DemandeConge, pk=pk)

    if not _peut_voir_demande(user, demande):
        messages.error(request, "Vous n'avez pas accès à cette demande.")
        return redirect("conge:liste")

    is_own        = demande.demandeur == user
    is_resp       = _is_responsable(user)  # RS | RO | assistante | superuser
    if user.is_superuser:
        show_demandeur_pdf = True
        show_employeur_pdf = True
    elif is_own and is_resp:
        show_demandeur_pdf = True
        show_employeur_pdf = True
    elif is_resp:
        show_demandeur_pdf = False
        show_employeur_pdf = True
    else:
        show_demandeur_pdf = True
        show_employeur_pdf = False

    return render(request, "conge/detail.html", {
        "demande":             demande,
        "can_validate":        _peut_valider_demande(user, demande),
        "can_download":        demande.is_valide,
        "is_responsable":      is_resp,
        "is_own":              is_own,
        "show_demandeur_pdf":  show_demandeur_pdf,
        "show_employeur_pdf":  show_employeur_pdf,
    })


@login_required
def valider_conge(request, pk: int):
    """Valider ou refuser une demande de congé (hiérarchie en cascade)."""
    user = request.user

    demande = get_object_or_404(DemandeConge, pk=pk)

    # Vérifier les droits d'accès
    if demande.statut in [demande.STATUT_VALIDE, demande.STATUT_REFUSE]:
        statut_label = demande.get_statut_display()
        messages.warning(request, f"Cette demande a déjà été {statut_label.lower()}. Aucune modification n'est possible.")
        return redirect("conge:detail", pk=pk)

    if not peut_valider_conge(user, demande):
        messages.error(request, "Vous n'avez pas les droits pour valider cette demande.")
        return redirect("conge:detail", pk=pk)

    # Récupérer la chaîne de validation requise
    chain = get_validation_chain_for_demande(demande)
    prochains_validateurs = get_prochains_validateurs(demande)

    if request.method == "POST":
        form = ValidationCongeForm(request.POST)
        if form.is_valid():
            action = form.cleaned_data["action"]

            if action == ValidationCongeForm.ACTION_VALIDER:
                # Une seule validation suffit - plus de cascade
                signature = form.cleaned_data.get("signature_responsable", "")
                marquer_validation(demande, user, signature=signature)
                messages.success(
                    request,
                    f"La demande a été validée par {user.get_full_name() or user.username}."
                )
            else:
                # Refus à n'importe quel niveau arrête la chaîne
                motif = form.cleaned_data.get("commentaire_refus", "")
                refuser_conge(demande, user, motif)
                messages.warning(request, "La demande de congé a été refusée.")

            _notifier_demandeur(demande, request)
            return redirect("conge:detail", pk=pk)
        else:
            messages.error(request, "Veuillez corriger les erreurs du formulaire.")
    else:
        form = ValidationCongeForm()

    context = {
        "demande": demande,
        "form": form,
        "validation_chain": chain,
        "validation_status": {
            "validateur_rs": demande.validateur_rs,
            "date_validation_rs": demande.date_validation_rs,
            "validateur_ro": demande.validateur_ro,
            "date_validation_ro": demande.date_validation_ro,
        },
    }

    return render(request, "conge/validation_form.html", context)


@login_required
@xframe_options_exempt
def telecharger_pdf(request, pk: int, exemplaire: str = "demandeur"):
    """Génère et télécharge le PDF de la demande de congé."""
    user    = request.user
    demande = get_object_or_404(DemandeConge, pk=pk)

    if not _peut_voir_demande(user, demande):
        messages.error(request, "Accès refusé à cette demande.")
        return redirect("conge:liste")

    if exemplaire not in ("demandeur", "employeur"):
        exemplaire = "demandeur"

    if exemplaire == "employeur" and not _is_responsable(user) and not user.is_superuser:
        messages.error(request, "Accès refusé : exemplaire réservé au responsable.")
        return redirect("conge:detail", pk=pk)

    if not demande.is_valide:
        messages.error(request, "Le PDF n'est disponible qu'après validation de la demande.")
        return redirect("conge:detail", pk=pk)

    try:
        from weasyprint import HTML  # noqa: F401 — vérifie la disponibilité
    except ImportError:
        messages.error(request, "WeasyPrint n'est pas disponible. Impossible de générer le PDF.")
        return redirect("conge:detail", pk=pk)

    try:
        pdf_bytes = _generer_pdf_demande(demande, exemplaire)
    except Exception as exc:
        logger.error("Erreur génération PDF (demande=%s, exemplaire=%s): %s", pk, exemplaire, exc)
        messages.error(request, f"Erreur lors de la génération du PDF : {exc}")
        return redirect("conge:detail", pk=pk)

    filename = (
        f"conge_{demande.nom}_{demande.prenom}_{demande.date_debut}_{exemplaire}.pdf"
    ).replace(" ", "_")

    # FileResponse avec BytesIO : sert le PDF en streaming, Content-Length exact,
    # compatible Chrome/Firefox/Edge. @xframe_options_exempt retire le header
    # X-Frame-Options qui peut bloquer le viewer PDF intégré du navigateur.
    response = FileResponse(
        BytesIO(pdf_bytes),
        content_type="application/pdf",
        as_attachment=True,
        filename=filename,
    )
    return response


# ─────────────────────────────────────────────────────────────────────────────
# Dashboard stats
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def dashboard_conge(request):
    """Tableau de bord des congés : stats globales (superadmin) ou par section (RO/RS)."""
    user = request.user

    # Queryset de base selon le rôle
    qs_base = _get_visible_conges_qs(user)

    # Totaux par statut
    total          = qs_base.count()
    total_attente  = qs_base.filter(statut=DemandeConge.STATUT_EN_ATTENTE).count()
    total_valide   = qs_base.filter(statut=DemandeConge.STATUT_VALIDE).count()
    total_refuse   = qs_base.filter(statut=DemandeConge.STATUT_REFUSE).count()

    # Dernières demandes (5)
    dernieres = qs_base.select_related("demandeur", "section").order_by("-date_demande")[:5]

    # Stats par section (superadmin uniquement)
    stats_sections = []
    if user.is_superuser:
        stats_sections = (
            DemandeConge.objects
            .values("section__Nom")
            .annotate(
                total=Count("id"),
                en_attente=Count("id", filter=Q(statut=DemandeConge.STATUT_EN_ATTENTE)),
                valide=Count("id", filter=Q(statut=DemandeConge.STATUT_VALIDE)),
                refuse=Count("id", filter=Q(statut=DemandeConge.STATUT_REFUSE)),
            )
            .order_by("-total")
        )

    # Stats par type de congé
    stats_types = (
        qs_base
        .values("type_conge")
        .annotate(total=Count("id"))
        .order_by("-total")
    )
    type_labels = dict(DemandeConge.TYPE_CONGE_CHOICES)
    stats_types_display = [
        {"label": type_labels.get(s["type_conge"], s["type_conge"]), "total": s["total"]}
        for s in stats_types
    ]

    # Filtres pour superadmin (section, année)
    from django.contrib.auth import get_user_model
    from accounts.models import Section
    sections_disponibles = Section.objects.all() if user.is_superuser else []
    filtre_section = request.GET.get("section", "").strip()
    filtre_annee   = request.GET.get("annee", "").strip()

    if user.is_superuser and filtre_section:
        qs_base = qs_base.filter(section__id=filtre_section)
        total          = qs_base.count()
        total_attente  = qs_base.filter(statut=DemandeConge.STATUT_EN_ATTENTE).count()
        total_valide   = qs_base.filter(statut=DemandeConge.STATUT_VALIDE).count()
        total_refuse   = qs_base.filter(statut=DemandeConge.STATUT_REFUSE).count()

    if filtre_annee:
        try:
            qs_base = qs_base.filter(date_demande__year=int(filtre_annee))
            total          = qs_base.count()
            total_attente  = qs_base.filter(statut=DemandeConge.STATUT_EN_ATTENTE).count()
            total_valide   = qs_base.filter(statut=DemandeConge.STATUT_VALIDE).count()
            total_refuse   = qs_base.filter(statut=DemandeConge.STATUT_REFUSE).count()
        except (ValueError, TypeError):
            pass

    import datetime
    current_year = datetime.date.today().year
    annees = list(range(current_year, current_year - 5, -1))

    return render(request, "conge/dashboard.html", {
        "total":                total,
        "total_attente":        total_attente,
        "total_valide":         total_valide,
        "total_refuse":         total_refuse,
        "dernieres":            dernieres,
        "stats_sections":       stats_sections,
        "stats_types":          stats_types_display,
        "sections_disponibles": sections_disponibles,
        "filtre_section":       filtre_section,
        "filtre_annee":         filtre_annee,
        "annees":               annees,
        "is_responsable":       _is_responsable(user),
    })
