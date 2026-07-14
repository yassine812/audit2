"""Vues globales du projet : accueil, connexion, déconnexion, profil."""

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils.http import url_has_allowed_host_and_scheme


def login_view(request):
    """Page de connexion commune à tous les modules."""
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            remember_me = request.POST.get('remember_me') == 'on'
            # Respecter le paramètre ?next= s'il est sûr
            next_url = request.POST.get('next') or request.GET.get('next') or ''
            if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
                response = redirect(next_url)
            else:
                response = redirect('home')
            if remember_me:
                response.set_cookie('remember_me', 'true', max_age=1209600)
            else:
                response.delete_cookie('remember_me')
            return response
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    if field == '__all__':
                        messages.error(request, "Nom d'utilisateur ou mot de passe incorrect.")
                    else:
                        messages.error(request, error)
    else:
        form = AuthenticationForm()

    remember_me = request.COOKIES.get('remember_me') == 'true'
    return render(request, 'adminlte/sales/login.html', {
        'form': form,
        'remember_me': remember_me,
    })


def logout_view(request):
    """Déconnexion et retour à la page de connexion."""
    logout(request)
    return redirect('login')


@login_required
def home_view(request):
    """Page d'accueil – sélection du module."""
    return render(request, 'home.html')


@login_required
def profile_view(request):
    """Page profil partagée par tous les modules."""
    return render(request, 'profile.html', {'user': request.user})


@login_required
def update_profile(request):
    """Mise à jour email/téléphone via AJAX."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'errors': {'__all__': ['Demande invalide']}})

    user = request.user
    new_email = request.POST.get('email')
    new_telephone = request.POST.get('telephone')

    from accounts.models import User as Utilisateur
    if Utilisateur.objects.filter(email=new_email).exclude(pk=user.pk).exists():
        return JsonResponse({
            'success': False,
            'errors': {'email': ['Cet e-mail est déjà utilisé par un autre compte.']}
        })

    user.email = new_email
    if hasattr(user, 'telephone'):
        user.telephone = new_telephone
    try:
        user.save()
        return JsonResponse({
            'success': True,
            'message': 'Votre profil a été mis à jour avec succès.',
            'email': user.email,
        })
    except Exception:
        return JsonResponse({
            'success': False,
            'errors': {'__all__': ["Une erreur s'est produite lors de la mise à jour."]}
        })


@login_required
def change_password(request):
    """Changement de mot de passe via AJAX."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'errors': {'__all__': ['Demande invalide']}})

    form = PasswordChangeForm(request.user, request.POST)
    if form.is_valid():
        user = form.save()
        update_session_auth_hash(request, user)
        return JsonResponse({'success': True, 'message': 'Mot de passe mis à jour avec succès.'})

    errors = {field: list(errs) for field, errs in form.errors.items()}
    return JsonResponse({'success': False, 'errors': errors})
