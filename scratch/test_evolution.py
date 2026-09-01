import os
import sys
import json
import django

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')
django.setup()

from django.test import RequestFactory
from django.contrib.auth import get_user_model
from reclamation_client.views import ReclamationDashboardView

User = get_user_model()
user = User.objects.first()
rf = RequestFactory()

print("--- TESTING DASHBOARD NORMAL PAGE GET (NON-AJAX) ---")

url = "/reclamations/?periode=all&evolution_periode=3m&date_debut=2026-08-28&date_fin=2026-09-01"
req = rf.get(url)
req.user = user
res = ReclamationDashboardView.as_view()(req)
print(f"Normal GET request status: {res.status_code}")

print("\n--- TESTING DASHBOARD AJAX JSON RESPONSES ---")
req_ajax = rf.get(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
req_ajax.user = user
res_ajax = ReclamationDashboardView.as_view()(req_ajax)
data = json.loads(res_ajax.content)
print(f"AJAX GET request status: {res_ajax.status_code}, Success: {data.get('success')}, Title: {data.get('title_suffix')!r}")
