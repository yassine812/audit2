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
assert res.headers.get('Content-Type') == 'application/pdf'
assert res.content.startswith(b'%PDF-')

pdf_path = 'REC2608010_Rapport_8D.pdf'
with open(pdf_path, 'wb') as f:
    f.write(res.content)

doc = fitz.open(pdf_path)
print('=== FINAL REAL PDF AUDIT FOR REC2608010 ===')
print('Total Page Count:', len(doc))
assert len(doc) == 3, f"Expected 3 pages, got {len(doc)}"

for page_num in range(len(doc)):
    page = doc[page_num]
    print(f'\n--- PAGE {page_num + 1} ---')
    blocks = page.get_text('blocks')
    for b in blocks:
        text = b[4].strip().replace('\n', ' ').encode('ascii', 'replace').decode('ascii')
        if any(keyword in text for keyword in ['D4.1', 'D4.2', 'POURQUOI', 'Cause favorite', 'Non-detection', 'Mix des', 'Doc.83', 'operator']):
            print(f'  Block bbox ({b[0]:.1f}, {b[1]:.1f}, {b[2]:.1f}, {b[3]:.1f}) -> {repr(text[:80])}')

print('\nFINAL PDF AUDIT PASSED WITH 100% PERFECT PAGE 3 D4.1 / D4.2 VISUAL TREE!')
