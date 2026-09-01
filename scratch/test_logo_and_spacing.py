import os, sys, django, fitz, base64
sys.path.insert(0, '.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')
django.setup()

from django.test import Client
from accounts.models import User
from reclamation_client.models import ReclamationClient

c = Client()
user = User.objects.filter(is_superuser=True).first() or User.objects.first()
c.force_login(user)

rec = ReclamationClient.objects.filter(reference='REC2608010').first() or ReclamationClient.objects.first()
res = c.get(f'/reclamations/{rec.pk}/export-pdf-8d/')

assert res.status_code == 200
with open('REC2608010_Logo_Tight_Test.pdf', 'wb') as f:
    f.write(res.content)

doc = fitz.open('REC2608010_Logo_Tight_Test.pdf')
page1 = doc[0]
print("=== D2 SPACING & LOGO AUDIT ===")
print("Images on Page 1:", len(page1.get_images()))
for b in page1.get_text('blocks'):
    txt = b[4].strip().replace('\n', ' ')
    if 'QUOI' in txt or 'Description' in txt:
        print(f"Block bbox ({b[0]:.1f}, {b[1]:.1f}, {b[2]:.1f}, {b[3]:.1f}) -> {repr(txt)}")

print("\nAUDIT SUCCESSFUL!")
