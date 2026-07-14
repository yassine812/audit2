"""
Vues de configuration de la chaîne de validation (alerte).
"""

import logging
from datetime import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from accounts.models import Section
from .models import ValidationChainConfiguration, DemandeConge

logger = logging.getLogger(__name__)

User = get_user_model()


def _check_permission(user):
    """Vérifie si l'utilisateur peut accéder à la configuration."""
    return user.is_superuser or user.is_staff


@login_required
def configuration_list(request):
    """Affiche la liste des configurations de chaînes de validation."""
    if not _check_permission(request.user):
        messages.error(request, "Vous n'avez pas les droits d'accès.")
        return redirect("conge:liste")

    # Récupérer toutes les sections
    sections = Section.objects.all().order_by("Nom")
    
    # Récupérer ou créer les configurations
    configurations = {}
    for section in sections:
        config, created = ValidationChainConfiguration.objects.get_or_create(
            section=section
        )
        configurations[section.id] = config

    context = {
        "sections": sections,
        "configurations": configurations,
    }

    return render(request, "conge/configuration_list.html", context)


@login_required
def configuration_detail(request, section_id):
    """Affiche et gère la configuration détaillée pour une section."""
    if not _check_permission(request.user):
        messages.error(request, "Vous n'avez pas les droits d'accès.")
        return redirect("conge:liste")

    section = get_object_or_404(Section, pk=section_id)
    config, created = ValidationChainConfiguration.objects.get_or_create(
        section=section
    )

    # Récupérer tous les utilisateurs actifs de la section
    section_users = User.objects.filter(
        section=section,
        is_active=True,
    ).order_by("last_name", "first_name")

    # Utilisateurs déjà sélectionnés
    selected_ro = config.validateurs_ro.all().values_list("id", flat=True)
    selected_rs = config.validateurs_rs.all().values_list("id", flat=True)
    selected_ce = config.gestionnaires_ce.all().values_list("id", flat=True)

    # Utilisateurs disponibles avec le rôle approprié (non sélectionnés)
    available_ro = section_users.filter(is_RO=True).exclude(id__in=selected_ro)
    available_rs = section_users.filter(is_RS=True).exclude(id__in=selected_rs)
    available_ce = section_users.filter(is_CE=True).exclude(id__in=selected_ce)

    context = {
        "section": section,
        "config": config,
        "available_ro": available_ro,
        "selected_ro": config.validateurs_ro.all().order_by("last_name"),
        "available_rs": available_rs,
        "selected_rs": config.validateurs_rs.all().order_by("last_name"),
        "available_ce": available_ce,
        "selected_ce": config.gestionnaires_ce.all().order_by("last_name"),
    }

    return render(request, "conge/configuration_detail.html", context)


@login_required
@require_http_methods(["POST"])
def add_validateur_ro(request, section_id):
    """Ajoute un validateur RO à la chaîne."""
    if not _check_permission(request.user):
        return JsonResponse({"success": False, "error": "Permission denied"}, status=403)

    section = get_object_or_404(Section, pk=section_id)
    config = get_object_or_404(ValidationChainConfiguration, section=section)
    user_id = request.POST.get("user_id")

    try:
        user = User.objects.get(pk=user_id, section=section, is_active=True, is_RO=True)
        config.validateurs_ro.add(user)
        config.modifie_par = request.user
        config.save()
        logger.info(f"RO ajouté: {user} à {section}")
        return JsonResponse({"success": True, "user": f"{user.get_full_name()}"})
    except User.DoesNotExist:
        return JsonResponse({"success": False, "error": "Utilisateur n'a pas le rôle RO"}, status=400)


@login_required
@require_http_methods(["POST"])
def remove_validateur_ro(request, section_id):
    """Retire un validateur RO de la chaîne."""
    if not _check_permission(request.user):
        return JsonResponse({"success": False, "error": "Permission denied"}, status=403)

    section = get_object_or_404(Section, pk=section_id)
    config = get_object_or_404(ValidationChainConfiguration, section=section)
    user_id = request.POST.get("user_id")

    try:
        user = User.objects.get(pk=user_id, section=section)
        config.validateurs_ro.remove(user)
        config.modifie_par = request.user
        config.save()
        logger.info(f"RO retiré: {user} de {section}")
        return JsonResponse({"success": True})
    except User.DoesNotExist:
        return JsonResponse({"success": False, "error": "Utilisateur non trouvé"}, status=404)


@login_required
@require_http_methods(["POST"])
def add_validateur_rs(request, section_id):
    """Ajoute un validateur RS à la chaîne."""
    if not _check_permission(request.user):
        return JsonResponse({"success": False, "error": "Permission denied"}, status=403)

    section = get_object_or_404(Section, pk=section_id)
    config = get_object_or_404(ValidationChainConfiguration, section=section)
    user_id = request.POST.get("user_id")

    try:
        user = User.objects.get(pk=user_id, section=section, is_active=True, is_RS=True)
        config.validateurs_rs.add(user)
        config.modifie_par = request.user
        config.save()
        logger.info(f"RS ajouté: {user} à {section}")
        return JsonResponse({"success": True, "user": f"{user.get_full_name()}"})
    except User.DoesNotExist:
        return JsonResponse({"success": False, "error": "Utilisateur n'a pas le rôle RS"}, status=400)


@login_required
@require_http_methods(["POST"])
def remove_validateur_rs(request, section_id):
    """Retire un validateur RS de la chaîne."""
    if not _check_permission(request.user):
        return JsonResponse({"success": False, "error": "Permission denied"}, status=403)

    section = get_object_or_404(Section, pk=section_id)
    config = get_object_or_404(ValidationChainConfiguration, section=section)
    user_id = request.POST.get("user_id")

    try:
        user = User.objects.get(pk=user_id, section=section)
        config.validateurs_rs.remove(user)
        config.modifie_par = request.user
        config.save()
        logger.info(f"RS retiré: {user} de {section}")
        return JsonResponse({"success": True})
    except User.DoesNotExist:
        return JsonResponse({"success": False, "error": "Utilisateur non trouvé"}, status=404)


@login_required
@require_http_methods(["POST"])
def add_gestionnaire_ce(request, section_id):
    """Ajoute un gestionnaire CE à la chaîne."""
    if not _check_permission(request.user):
        return JsonResponse({"success": False, "error": "Permission denied"}, status=403)

    section = get_object_or_404(Section, pk=section_id)
    config = get_object_or_404(ValidationChainConfiguration, section=section)
    user_id = request.POST.get("user_id")

    try:
        user = User.objects.get(pk=user_id, section=section, is_active=True, is_CE=True)
        config.gestionnaires_ce.add(user)
        config.modifie_par = request.user
        config.save()
        logger.info(f"CE ajouté: {user} à {section}")
        return JsonResponse({"success": True, "user": f"{user.get_full_name()}"})
    except User.DoesNotExist:
        return JsonResponse({"success": False, "error": "Utilisateur n'a pas le rôle CE"}, status=400)


@login_required
@require_http_methods(["POST"])
def remove_gestionnaire_ce(request, section_id):
    """Retire un gestionnaire CE de la chaîne."""
    if not _check_permission(request.user):
        return JsonResponse({"success": False, "error": "Permission denied"}, status=403)

    section = get_object_or_404(Section, pk=section_id)
    config = get_object_or_404(ValidationChainConfiguration, section=section)
    user_id = request.POST.get("user_id")

    try:
        user = User.objects.get(pk=user_id, section=section)
        config.gestionnaires_ce.remove(user)
        config.modifie_par = request.user
        config.save()
        logger.info(f"CE retiré: {user} de {section}")
        return JsonResponse({"success": True})
    except User.DoesNotExist:
        return JsonResponse({"success": False, "error": "Utilisateur non trouvé"}, status=404)



