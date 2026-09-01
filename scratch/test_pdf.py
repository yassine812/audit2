import os, sys, django
from io import BytesIO
from xhtml2pdf import pisa
from django.template.loader import render_to_string
import fitz

sys.path.insert(0, '.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')
django.setup()

from reclamation_client.models import ReclamationClient

rec = ReclamationClient.objects.filter(reference='REC2608010').first() or ReclamationClient.objects.first()

context = {
    'reclamation': rec,
    'participants': rec.participants.all(),
    'qqoqccp': getattr(rec, 'qqoqccp', None),
    'mesures_d3': rec.mesures_conservatoires.all(),
    'analyse_d4': getattr(rec, 'analyse_causes_d4', None),
    'actions_tests': rec.actions_tests.all(),
    'actions_permanentes': rec.actions_correctives.all(),
    'capitalisation_d7': getattr(rec, 'capitalisation_d7', None),
    'cloture_d8': getattr(rec, 'cloture_d8', None),
}

html = render_to_string('reclamation_client/rapport_8d_pdf.html', context)
result = BytesIO()
pdf = pisa.pisaDocument(BytesIO(html.encode('utf-8')), result)

if not pdf.err:
    pdf_bytes = result.getvalue()
    doc = fitz.open(stream=pdf_bytes, filetype='pdf')
    print(f'SUCCESS! Generated PDF size: {len(pdf_bytes)} bytes | Total Pages: {len(doc)}')
    for i, page in enumerate(doc):
        print(f'Page {i+1} text length: {len(page.get_text())} chars')
    with open('REC2608010_Rapport_8D.pdf', 'wb') as f:
        f.write(pdf_bytes)
else:
    print('PDF Generation Error:', pdf.err)
