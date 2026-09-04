import os
import sys
sys.path.insert(0, r'c:\Users\Yassine\audit2-main')
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')
django.setup()

import fitz
from django.template.loader import render_to_string
from io import BytesIO
from xhtml2pdf import pisa
from plan_prevention.models import PlanPrevention

pdp = PlanPrevention.objects.get(pk=6)
risques = pdp.pdp_risques.select_related('risque').order_by('ordre', 'pk')

html = render_to_string('plan_prevention/pdf_plan_prevention.html', {'pdp': pdp, 'risques': risques})
buf = BytesIO()
pisa.pisaDocument(BytesIO(html.encode('utf-8')), buf)
doc = fitz.open(stream=buf.getvalue(), filetype='pdf')
print(f'Current total pages: {len(doc)}')

# In pdf_plan_prevention.html, Page 2 closes at line 400 and Page 3 opens at 403.
# Let's remove the closing </div> of page 2 and opening <div class="page"> of page 3 so they are in the same page div.
html_2pages = html.replace('  </div>\n\n  <!-- ==================== PAGE 3 : REMARQUES & SIGNATURES ==================== -->\n  <div class="page">', '  <div style="margin-top: 6pt;">')

buf2 = BytesIO()
pisa.pisaDocument(BytesIO(html_2pages.encode('utf-8')), buf2)
doc2 = fitz.open(stream=buf2.getvalue(), filetype='pdf')
print(f'2-page combined total pages: {len(doc2)}')
for i in range(len(doc2)):
    doc2[i].get_pixmap().save(f'scratch/combined_page_{i}.png')
print("Saved combined pages!")
