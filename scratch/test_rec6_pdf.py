import os, sys, django, fitz

sys.path.insert(0, '.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')
django.setup()

from django.test import Client
from accounts.models import User
from reclamation_client.models import ReclamationClient

c = Client()
user = User.objects.filter(is_superuser=True).first() or User.objects.first()
c.force_login(user)

# Test ID 6
print("Testing PDF export for Reclamation pk=6...")
res6 = c.get('/reclamations/6/export-pdf-8d/')
assert res6.status_code == 200, f"Expected 200 OK, got {res6.status_code}"
assert res6['Content-Type'] == 'application/pdf', f"Expected PDF, got {res6['Content-Type']}"
print(f"SUCCESS: Reclamation pk=6 PDF exported ({len(res6.content)} bytes)")

# Test ID 13 (Full Test Reclamation)
print("Testing PDF export for Reclamation pk=13...")
res13 = c.get('/reclamations/13/export-pdf-8d/')
assert res13.status_code == 200, f"Expected 200 OK, got {res13.status_code}"
assert res13['Content-Type'] == 'application/pdf', f"Expected PDF, got {res13['Content-Type']}"
print(f"SUCCESS: Reclamation pk=13 PDF exported ({len(res13.content)} bytes)")

print("ALL PDF EXPORTS PASSED WITH ZERO ERRORS!")
