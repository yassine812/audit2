from datetime import datetime, time

from django.contrib.admin.models import LogEntry
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.contenttypes.models import ContentType
from django.core.paginator import Paginator
from django.shortcuts import render
from django.utils import timezone
from django.utils.dateparse import parse_date

ACTION_FLAG_LABELS = {
    1: {"label": "Ajout", "badge": "badge-success"},
    2: {"label": "Modification", "badge": "badge-info"},
    3: {"label": "Suppression", "badge": "badge-danger"},
}


@login_required
@user_passes_test(lambda u: u.is_superuser, login_url="/login/")
def audit_logs_view(request):
    """Vue centralisée pour consulter l'historique des audits (LogEntry) des modèles."""
    queryset = LogEntry.objects.select_related("user", "content_type").order_by("-action_time")

    # Récupération des filtres depuis la requête GET
    model_id = request.GET.get("model", "").strip()
    user_id = request.GET.get("user", "").strip()
    action_flag = request.GET.get("action", "").strip()
    date_from_str = request.GET.get("date_from", "").strip()
    date_to_str = request.GET.get("date_to", "").strip()

    if model_id and model_id.isdigit():
        queryset = queryset.filter(content_type_id=int(model_id))

    if user_id and user_id.isdigit():
        queryset = queryset.filter(user_id=int(user_id))

    if action_flag and action_flag.isdigit():
        queryset = queryset.filter(action_flag=int(action_flag))

    if date_from_str:
        d_from = parse_date(date_from_str)
        if d_from:
            queryset = queryset.filter(action_time__gte=timezone.make_aware(datetime.combine(d_from, time.min)))

    if date_to_str:
        d_to = parse_date(date_to_str)
        if d_to:
            queryset = queryset.filter(action_time__lte=timezone.make_aware(datetime.combine(d_to, time.max)))

    # Listes pour alimenter les menus déroulants du formulaire de filtre
    EXCLUDED_APPS = {"contenttypes", "sessions", "admin", "auth", "django_celery_beat", "authtoken"}
    content_types = ContentType.objects.exclude(app_label__in=EXCLUDED_APPS).order_by("app_label", "model")

    User = get_user_model()
    users = User.objects.filter(is_active=True).order_by("first_name", "last_name", "username")

    actions = [
        (1, "Ajout"),
        (2, "Modification"),
        (3, "Suppression"),
    ]

    # Pagination (25 éléments par page)
    paginator = Paginator(queryset, 25)
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)

    # Annotation des entrées avec les libellés et badges en français
    for entry in page_obj:
        flag_info = ACTION_FLAG_LABELS.get(entry.action_flag, {"label": f"Action {entry.action_flag}", "badge": "badge-secondary"})
        entry.action_label = flag_info["label"]
        entry.action_badge_class = flag_info["badge"]

    context = {
        "page_obj": page_obj,
        "paginator": paginator,
        "is_paginated": paginator.num_pages > 1,
        "content_types": content_types,
        "users": users,
        "actions": actions,
        "selected_model": int(model_id) if model_id.isdigit() else "",
        "selected_user": int(user_id) if user_id.isdigit() else "",
        "selected_action": int(action_flag) if action_flag.isdigit() else "",
        "date_from": date_from_str,
        "date_to": date_to_str,
    }
    return render(request, "audit_logs/audit_logs.html", context)
