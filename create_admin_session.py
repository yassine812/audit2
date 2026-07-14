#!/usr/bin/env python
"""
Script pour configurer le cookie de session admin dans le navigateur
"""
import os
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')
django.setup()

from django.contrib.sessions.models import Session
from django.contrib.auth import get_user_model
from django.contrib.sessions.backends.db import SessionStore
from datetime import datetime, timedelta

User = get_user_model()

# Récupérer l'admin
admin_user = User.objects.get(username='admin.test')

# Créer une nouvelle session
session = SessionStore()
session['_auth_user_id'] = str(admin_user.pk)
session['_auth_user_backend'] = 'django.contrib.auth.backends.ModelBackend'
session['_auth_user_hash'] = admin_user.get_session_auth_hash()
session.set_expiry(3600)  # 1 heure
session.save()

print(f"Session créée pour {admin_user.username}")
print(f"Session Key: {session.session_key}")
print(f"\nPour utiliser dans le navigateur:")
print(f"1. Ouvrir la console développeur (F12)")
print(f"2. Aller dans l'onglet Console")
print(f"3. Exécuter:")
print(f"   document.cookie = 'sessionid={session.session_key}; path=/; max-age=3600'")
print(f"4. Rafraîchir la page")