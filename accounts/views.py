"""Vues du module Administration (accounts).

Toutes les vues vérifient que l'utilisateur est superadmin.
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render

from .forms import (
    CustomerForm,
    SectionForm,
    SiteForm,
    SocieteForm,
    UserCreateForm,
    UserEditForm,
)
from .models import Customer, Section, Site, Societe, User


def _superadmin_required(request):
    """Retourne None si OK, sinon une réponse 403."""
    if not request.user.is_authenticated or not request.user.is_superuser:
        return render(request, "403.html", status=403)
    return None


def _paginate(qs, request, per_page=15):
    paginator = Paginator(qs, per_page)
    page = request.GET.get("page", 1)
    return paginator.get_page(page)


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------


@login_required
def dashboard_admin(request):
    guard = _superadmin_required(request)
    if guard:
        return guard

    context = {
        "total_users": User.objects.count(),
        "total_societes": Societe.objects.count(),
        "total_sections": Section.objects.count(),
        "total_sites": Site.objects.count(),
        "total_customers": Customer.objects.count(),
        "users_rs": User.objects.filter(is_RS=True).count(),
        "users_ro": User.objects.filter(is_RO=True).count(),
        "users_ce": User.objects.filter(is_CE=True).count(),
        "users_op": User.objects.filter(is_OP=True).count(),
        "users_auditeur": User.objects.filter(is_auditeur=True).count(),
        "users_clt": User.objects.filter(is_CLT=True).count(),
        "recent_users": User.objects.order_by("-date_joined")[:5],
    }
    return render(request, "accounts/dashboard.html", context)


# ---------------------------------------------------------------------------
# Utilisateurs
# ---------------------------------------------------------------------------


@login_required
def liste_utilisateurs(request):
    guard = _superadmin_required(request)
    if guard:
        return guard

    qs = User.objects.select_related("section", "societe").order_by("username")

    q = request.GET.get("q", "").strip()
    section_id = request.GET.get("section", "")
    societe_id = request.GET.get("societe", "")
    role = request.GET.get("role", "")

    if q:
        qs = qs.filter(username__icontains=q) | qs.filter(first_name__icontains=q) | qs.filter(last_name__icontains=q)
    if section_id:
        qs = qs.filter(section_id=section_id)
    if societe_id:
        qs = qs.filter(societe_id=societe_id)
    if role == "RS":
        qs = qs.filter(is_RS=True)
    elif role == "RO":
        qs = qs.filter(is_RO=True)
    elif role == "CE":
        qs = qs.filter(is_CE=True)
    elif role == "OP":
        qs = qs.filter(is_OP=True)
    elif role == "auditeur":
        qs = qs.filter(is_auditeur=True)
    elif role == "CLT":
        qs = qs.filter(is_CLT=True)
    elif role == "superuser":
        qs = qs.filter(is_superuser=True)

    page_obj = _paginate(qs, request)
    return render(request, "accounts/utilisateurs/liste.html", {
        "page_obj": page_obj,
        "sections": Section.objects.all(),
        "societes": Societe.objects.all(),
        "q": q,
        "section_id": section_id,
        "societe_id": societe_id,
        "role": role,
    })


@login_required
def creer_utilisateur(request):
    guard = _superadmin_required(request)
    if guard:
        return guard

    if request.method == "POST":
        form = UserCreateForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f"Utilisateur « {user.username} » créé avec succès.")
            return redirect("administration:utilisateurs")
    else:
        form = UserCreateForm()

    return render(request, "accounts/utilisateurs/form.html", {"form": form, "action": "Créer"})


@login_required
def modifier_utilisateur(request, pk):
    guard = _superadmin_required(request)
    if guard:
        return guard

    user_obj = get_object_or_404(User, pk=pk)
    if request.method == "POST":
        form = UserEditForm(request.POST, instance=user_obj)
        if form.is_valid():
            form.save()
            messages.success(request, f"Utilisateur « {user_obj.username} » mis à jour.")
            return redirect("administration:utilisateurs")
    else:
        form = UserEditForm(instance=user_obj)

    return render(request, "accounts/utilisateurs/form.html", {
        "form": form, "action": "Modifier", "object": user_obj,
    })


@login_required
def supprimer_utilisateur(request, pk):
    guard = _superadmin_required(request)
    if guard:
        return guard

    user_obj = get_object_or_404(User, pk=pk)
    if user_obj == request.user:
        messages.error(request, "Vous ne pouvez pas supprimer votre propre compte.")
        return redirect("administration:utilisateurs")

    if request.method == "POST":
        username = user_obj.username
        user_obj.delete()
        messages.success(request, f"Utilisateur « {username} » supprimé.")
        return redirect("administration:utilisateurs")

    return render(request, "accounts/utilisateurs/confirm_delete.html", {"object": user_obj})


# ---------------------------------------------------------------------------
# Sociétés
# ---------------------------------------------------------------------------


@login_required
def liste_societes(request):
    guard = _superadmin_required(request)
    if guard:
        return guard

    qs = Societe.objects.order_by("nom")
    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(nom__icontains=q)

    page_obj = _paginate(qs, request)
    return render(request, "accounts/societes/liste.html", {"page_obj": page_obj, "q": q})


@login_required
def creer_societe(request):
    guard = _superadmin_required(request)
    if guard:
        return guard

    if request.method == "POST":
        form = SocieteForm(request.POST)
        if form.is_valid():
            obj = form.save()
            messages.success(request, f"Société « {obj.nom} » créée.")
            return redirect("administration:societes")
    else:
        form = SocieteForm()

    return render(request, "accounts/societes/form.html", {"form": form, "action": "Créer"})


@login_required
def modifier_societe(request, pk):
    guard = _superadmin_required(request)
    if guard:
        return guard

    obj = get_object_or_404(Societe, pk=pk)
    if request.method == "POST":
        form = SocieteForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, f"Société « {obj.nom} » mise à jour.")
            return redirect("administration:societes")
    else:
        form = SocieteForm(instance=obj)

    return render(request, "accounts/societes/form.html", {"form": form, "action": "Modifier", "object": obj})


@login_required
def supprimer_societe(request, pk):
    guard = _superadmin_required(request)
    if guard:
        return guard

    obj = get_object_or_404(Societe, pk=pk)
    if request.method == "POST":
        nom = obj.nom
        obj.delete()
        messages.success(request, f"Société « {nom} » supprimée.")
        return redirect("administration:societes")

    return render(request, "accounts/societes/confirm_delete.html", {"object": obj})


# ---------------------------------------------------------------------------
# Sections
# ---------------------------------------------------------------------------


@login_required
def liste_sections(request):
    guard = _superadmin_required(request)
    if guard:
        return guard

    qs = Section.objects.select_related("societe").order_by("Nom")
    q = request.GET.get("q", "").strip()
    societe_id = request.GET.get("societe", "")
    pays = request.GET.get("pays", "").strip()

    if q:
        qs = qs.filter(Nom__icontains=q)
    if societe_id:
        qs = qs.filter(societe_id=societe_id)
    if pays:
        qs = qs.filter(pays__icontains=pays)

    page_obj = _paginate(qs, request)
    return render(request, "accounts/sections/liste.html", {
        "page_obj": page_obj,
        "societes": Societe.objects.all(),
        "q": q, "societe_id": societe_id, "pays": pays,
    })


@login_required
def creer_section(request):
    guard = _superadmin_required(request)
    if guard:
        return guard

    if request.method == "POST":
        form = SectionForm(request.POST)
        if form.is_valid():
            obj = form.save()
            messages.success(request, f"Section « {obj.Nom} » créée.")
            return redirect("administration:sections")
    else:
        form = SectionForm()

    return render(request, "accounts/sections/form.html", {"form": form, "action": "Créer"})


@login_required
def modifier_section(request, pk):
    guard = _superadmin_required(request)
    if guard:
        return guard

    obj = get_object_or_404(Section, pk=pk)
    if request.method == "POST":
        form = SectionForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, f"Section « {obj.Nom} » mise à jour.")
            return redirect("administration:sections")
    else:
        form = SectionForm(instance=obj)

    return render(request, "accounts/sections/form.html", {"form": form, "action": "Modifier", "object": obj})


@login_required
def supprimer_section(request, pk):
    guard = _superadmin_required(request)
    if guard:
        return guard

    obj = get_object_or_404(Section, pk=pk)
    if request.method == "POST":
        nom = obj.Nom
        obj.delete()
        messages.success(request, f"Section « {nom} » supprimée.")
        return redirect("administration:sections")

    return render(request, "accounts/sections/confirm_delete.html", {"object": obj})


# ---------------------------------------------------------------------------
# Sites
# ---------------------------------------------------------------------------


@login_required
def liste_sites(request):
    guard = _superadmin_required(request)
    if guard:
        return guard

    qs = Site.objects.select_related("section").order_by("nom")
    q = request.GET.get("q", "").strip()
    section_id = request.GET.get("section", "")

    if q:
        qs = qs.filter(nom__icontains=q)
    if section_id:
        qs = qs.filter(section_id=section_id)

    page_obj = _paginate(qs, request)
    return render(request, "accounts/sites/liste.html", {
        "page_obj": page_obj,
        "sections": Section.objects.all(),
        "q": q, "section_id": section_id,
    })


@login_required
def creer_site(request):
    guard = _superadmin_required(request)
    if guard:
        return guard

    if request.method == "POST":
        form = SiteForm(request.POST)
        if form.is_valid():
            obj = form.save()
            messages.success(request, f"Site « {obj.nom} » créé.")
            return redirect("administration:sites")
    else:
        form = SiteForm()

    return render(request, "accounts/sites/form.html", {"form": form, "action": "Créer"})


@login_required
def modifier_site(request, pk):
    guard = _superadmin_required(request)
    if guard:
        return guard

    obj = get_object_or_404(Site, pk=pk)
    if request.method == "POST":
        form = SiteForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, f"Site « {obj.nom} » mis à jour.")
            return redirect("administration:sites")
    else:
        form = SiteForm(instance=obj)

    return render(request, "accounts/sites/form.html", {"form": form, "action": "Modifier", "object": obj})


@login_required
def supprimer_site(request, pk):
    guard = _superadmin_required(request)
    if guard:
        return guard

    obj = get_object_or_404(Site, pk=pk)
    if request.method == "POST":
        nom = obj.nom
        obj.delete()
        messages.success(request, f"Site « {nom} » supprimé.")
        return redirect("administration:sites")

    return render(request, "accounts/sites/confirm_delete.html", {"object": obj})


# ---------------------------------------------------------------------------
# Customers
# ---------------------------------------------------------------------------


@login_required
def liste_customers(request):
    guard = _superadmin_required(request)
    if guard:
        return guard

    qs = Customer.objects.select_related("societe").order_by("intitule")
    q = request.GET.get("q", "").strip()
    societe_id = request.GET.get("societe", "")
    type_c = request.GET.get("type", "")
    is_draft = request.GET.get("is_draft", "")

    if q:
        qs = qs.filter(intitule__icontains=q) | qs.filter(compte__icontains=q)
    if societe_id:
        qs = qs.filter(societe_id=societe_id)
    if type_c:
        qs = qs.filter(type=type_c)
    if is_draft == "1":
        qs = qs.filter(is_draft=True)
    elif is_draft == "0":
        qs = qs.filter(is_draft=False)

    page_obj = _paginate(qs, request)
    return render(request, "accounts/customers/liste.html", {
        "page_obj": page_obj,
        "societes": Societe.objects.all(),
        "q": q, "societe_id": societe_id, "type_c": type_c, "is_draft": is_draft,
    })


@login_required
def creer_customer(request):
    guard = _superadmin_required(request)
    if guard:
        return guard

    if request.method == "POST":
        form = CustomerForm(request.POST)
        if form.is_valid():
            obj = form.save()
            messages.success(request, f"Customer « {obj.intitule} » créé.")
            return redirect("administration:customers")
    else:
        form = CustomerForm()

    return render(request, "accounts/customers/form.html", {"form": form, "action": "Créer"})


@login_required
def modifier_customer(request, pk):
    guard = _superadmin_required(request)
    if guard:
        return guard

    obj = get_object_or_404(Customer, pk=pk)
    if request.method == "POST":
        form = CustomerForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, f"Customer « {obj.intitule} » mis à jour.")
            return redirect("administration:customers")
    else:
        form = CustomerForm(instance=obj)

    return render(request, "accounts/customers/form.html", {"form": form, "action": "Modifier", "object": obj})


@login_required
def supprimer_customer(request, pk):
    guard = _superadmin_required(request)
    if guard:
        return guard

    obj = get_object_or_404(Customer, pk=pk)
    if request.method == "POST":
        intitule = obj.intitule
        obj.delete()
        messages.success(request, f"Customer « {intitule} » supprimé.")
        return redirect("administration:customers")

    return render(request, "accounts/customers/confirm_delete.html", {"object": obj})
