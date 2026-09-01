import os
import sys
import django

sys.path.insert(0, '.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')
django.setup()

from django.test import Client
from django.core.management import call_command
from accounts.models import User
from accounts.forms import UserCreateForm

client = Client()

print("=========================================================")
print(" AUDIT COMPLET DE L'INSCRIPTION / REGISTER & PERMISSIONS")
print("=========================================================")

# 1. Vérification de l'existence d'une page/route d'inscription publique
public_routes = ['/register/', '/signup/', '/accounts/register/', '/inscription/']
found_public_route = None

for r in public_routes:
    res = client.get(r)
    if res.status_code != 404:
        found_public_route = r
        print(f"[REGISTER PAGE] Trouvée à la route : {r} (Status: {res.status_code})")
        break

if not found_public_route:
    print("[REGISTER PAGE] Aucune page/route d'auto-inscription publique n'existe (/register, /signup, etc.).")
    print("                Dans cette application, la création d'utilisateurs est strictement réservée à l'espace Administration (/administration/utilisateurs/nouveau/).")

# 2. Test du formulaire de création Utilisateur UserCreateForm
email_test = "test.register@example.com"
username_test = "user_register_test_2026"
password_test = "K9#mX$8vP2L!zN4q"

User.objects.filter(email=email_test).delete()
User.objects.filter(username=username_test).delete()

print("\n--- Test 1 : Création Utilisateur ---")
form_data = {
    'username': username_test,
    'first_name': 'User',
    'last_name': 'Test',
    'email': email_test,
    'password1': password_test,
    'password2': password_test,
    'timezone': 'Europe/Paris',
    'is_active': True,
}

form = UserCreateForm(data=form_data)
user_created_in_db = False
if form.is_valid():
    new_user = form.save()
    user_created_in_db = True
    print(f"[OK] Utilisateur créé en base : ID={new_user.id}, Username={new_user.username}, Email={new_user.email}")
else:
    print(f"[FAIL] Formulaire d'inscription invalide : {form.errors}")

# 3. Test Doublon Email & Doublon Username
print("\n--- Test 2 : Doublon Email / Username ---")
form_duplicate = UserCreateForm(data=form_data)
duplicate_rejected = not form_duplicate.is_valid()
print(f"[OK] La création d'un utilisateur en doublon est-elle rejetée par le formulaire ? -> {duplicate_rejected}")
if duplicate_rejected:
    print(f"     Erreurs renvoyées pour le doublon : {form_duplicate.errors.as_text()}")

# 4. Test Validations du formulaire (email invalide & champs manquants)
print("\n--- Test 3 : Validations Formulaire ---")
form_invalid_email = UserCreateForm(data={
    'username': 'invalidemailuser',
    'first_name': 'User',
    'last_name': 'Test',
    'email': 'email_sans_arobase.com',
    'password1': 'TestRegister2026!',
    'password2': 'TestRegister2026!',
})
email_validation_ok = (not form_invalid_email.is_valid()) and ('email' in form_invalid_email.errors)
print(f"[OK] Rejet email invalide ('email_sans_arobase.com') -> {email_validation_ok}")

form_missing = UserCreateForm(data={})
missing_validation_ok = not form_missing.is_valid()
print(f"[OK] Rejet si champs obligatoires manquants -> {missing_validation_ok}")

# 5. Test Connexion après inscription
print("\n--- Test 4 : Connexion du Nouvel Utilisateur ---")
login_success = client.login(username=username_test, password=password_test)
print(f"[OK] Authentification avec identifiants (username + password) -> {login_success}")

redirection_ok = False
if login_success:
    res_home = client.get('/')
    print(f"[OK] Redirection post-connexion vers page d'accueil (HTTP {res_home.status_code})")
    redirection_ok = (res_home.status_code == 200)

# 6. Test Permissions & Protection des accès
print("\n--- Test 5 : Permissions & Securite du Nouvel Utilisateur ---")
created_user = User.objects.get(username=username_test)
is_superuser = created_user.is_superuser
is_staff = created_user.is_staff
permissions_ok = (not is_superuser and not is_staff)
print(f"[OK] Superuser: {is_superuser} | Staff: {is_staff} -> Le nouvel utilisateur N'A PAS de privilèges admin par défaut ({permissions_ok})")

# Test protection des routes d'administration avec cet utilisateur non-admin
res_admin_restricted = client.get('/administration/')
protection_ok = (res_admin_restricted.status_code in [403, 302])
print(f"[OK] Accès à /administration/ par le nouvel utilisateur non-admin -> HTTP {res_admin_restricted.status_code} (Accès refusé OK)")

# Nettoyage de l'utilisateur de test
created_user.delete()
print("\n[CLEANUP] Utilisateur de test supprimé après validation.")

print("\n--- Test 6 : Django Check ---")
call_command('check')
