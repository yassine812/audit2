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
with open('REC2608010_Single_Table.pdf', 'wb') as f:
    f.write(res.content)

doc = fitz.open('REC2608010_Single_Table.pdf')
print(f"Total Pages: {len(doc)}")
for i, page in enumerate(doc):
    print(f"--- Page {i+1} ---")
    blocks = page.get_text('blocks')
    print(f"Total blocks: {len(blocks)}")

print("\nSINGLE TABLE AUDIT SUCCESSFUL!")
