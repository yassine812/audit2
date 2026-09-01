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

rec = ReclamationClient.objects.filter(reference='REC2608010').first() or ReclamationClient.objects.first()
res = c.get(f'/reclamations/{rec.pk}/export-pdf-8d/')

assert res.status_code == 200
with open('REC2608010_Oui_Non_Cols.pdf', 'wb') as f:
    f.write(res.content)

doc = fitz.open('REC2608010_Oui_Non_Cols.pdf')
print("Total Pages:", len(doc))
for i, page in enumerate(doc):
    print(f"--- Page {i+1} ---")
    blocks = page.get_text('blocks')
    for b in blocks:
        txt = b[4].strip().replace('\n', ' ')
        if 'Oui' in txt or 'Non' in txt or 'Doc.01' in txt:
            print(f"  Block bbox ({b[0]:.1f}, {b[1]:.1f}, {b[2]:.1f}, {b[3]:.1f}) -> {repr(txt)}")

print("\nOUI NON COLUMNS AUDIT SUCCESSFUL!")
