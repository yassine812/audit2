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

rec = ReclamationClient.objects.get(reference='REC20260085')
res = c.get(f'/reclamations/{rec.pk}/export-pdf-8d/')

assert res.status_code == 200, f"Expected 200 OK, got {res.status_code}"
assert res['Content-Type'] == 'application/pdf', f"Expected PDF content type, got {res['Content-Type']}"

pdf_path = "scratch_REC20260085_Doc83.pdf"
with open(pdf_path, 'wb') as f:
    f.write(res.content)

print(f"Exported PDF saved to {pdf_path} ({len(res.content)} bytes)")

doc = fitz.open(pdf_path)
print(f"Total PDF pages: {len(doc)}")

for i, page in enumerate(doc):
    pix = page.get_pixmap(dpi=150)
    out_img = f"c:/Users/Yassine/audit2-main/scratch/pdf_full_p{i+1}.png"
    pix.save(out_img)
    print(f"Page {i+1} saved to {out_img}")

print("PDF RENDER TEST COMPLETE!")
