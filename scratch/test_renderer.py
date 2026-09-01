import os, sys, django, fitz
from io import BytesIO
from xhtml2pdf import pisa

sys.path.insert(0, '.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')
django.setup()

from reclamation_client.models import ReclamationClient

rec = ReclamationClient.objects.filter(reference='REC2608010').first() or ReclamationClient.objects.first()

html_content = f"""
<!DOCTYPE html>
<html>
<head>
<style>
@page {{
    size: a4 portrait;
    margin: 8mm 10mm;
}}
body {{
    font-family: Helvetica, Arial, sans-serif;
    font-size: 8pt;
}}
table {{
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 10px;
}}
th, td {{
    border: 1px solid #000000;
    padding: 3px 4px;
    font-size: 8pt;
    vertical-align: middle;
}}
.bg-blue {{
    background-color: #d9e1f2;
    font-weight: bold;
}}
</style>
</head>
<body>

<h3>D3 TEST WITH EXACT COL PT WIDTHS</h3>
<table width="100%">
    <colgroup>
        <col width="216pt">
        <col width="36pt">
        <col width="36pt">
        <col width="126pt">
        <col width="126pt">
    </colgroup>
    <thead>
        <tr class="bg-blue">
            <th width="216pt" align="left">Actions</th>
            <th width="36pt" align="center">Oui</th>
            <th width="36pt" align="center">Non</th>
            <th width="126pt" align="center">Quantité triée</th>
            <th width="126pt" align="center">Quantité NOK</th>
        </tr>
    </thead>
    <tbody>
        <tr><td>Tri stock interne</td><td align="center">☐</td><td align="center">☑</td><td align="center"></td><td align="center"></td></tr>
        <tr><td>Tri stock externe</td><td align="center">☑</td><td align="center">☐</td><td align="center">36720</td><td align="center"></td></tr>
        <tr><td>Repère unitaire</td><td align="center">☐</td><td align="center">☑</td><td align="center"></td><td align="center"></td></tr>
    </tbody>
</table>

<h3>D5 TEST WITH EXACT COL PT WIDTHS</h3>
<table width="100%">
    <colgroup>
        <col width="292pt">
        <col width="124pt">
        <col width="124pt">
    </colgroup>
    <thead>
        <tr class="bg-blue">
            <th width="292pt" align="left">Actions test</th>
            <th width="124pt" align="left">Pilote - Délai</th>
            <th width="124pt" align="left">Conclusion</th>
        </tr>
    </thead>
    <tbody>
        <tr><td>1. Action test unitaire d'assemblage sur poste 5</td><td>FISCHER Fabien - 15/03/2026</td><td>Concluant</td></tr>
        <tr><td>2. Contrôle sous loupe</td><td>MARTZ Fabien - 18/03/2026</td><td>Concluant</td></tr>
        <tr><td>3</td><td></td><td></td></tr>
        <tr><td>4</td><td></td><td></td></tr>
    </tbody>
</table>

<h3>D6 TEST WITH EXACT COL PT WIDTHS</h3>
<table width="100%">
    <colgroup>
        <col width="270pt">
        <col width="90pt">
        <col width="90pt">
        <col width="90pt">
    </colgroup>
    <thead>
        <tr class="bg-blue">
            <th width="270pt" align="left">Action</th>
            <th width="90pt" align="left">Pilote</th>
            <th width="90pt" align="left">Délai</th>
            <th width="90pt" align="left">Date de réalisation</th>
        </tr>
    </thead>
    <tbody>
        <tr><td><strong>Action 1 :</strong> Marquage unitaire</td><td>FISCHER Fabien</td><td>15/03/2026</td><td>14/03/2026</td></tr>
        <tr><td><strong>Action 2 :</strong> Mise à jour gamme</td><td>MARTZ Fabien</td><td>18/03/2026</td><td>17/03/2026</td></tr>
        <tr><td><strong>Action 3 :</strong> Audit de poste Doc 37</td><td>CHILLIARD S.</td><td>22/03/2026</td><td>—</td></tr>
        <tr><td><strong>Action 4 :</strong> Formation opérateurs</td><td>Directeur QSE</td><td>25/03/2026</td><td>—</td></tr>
    </tbody>
</table>

</body>
</html>
"""

buf = BytesIO()
pdf = pisa.pisaDocument(BytesIO(html_content.encode('utf-8')), buf)

if not pdf.err:
    pdf_bytes = buf.getvalue()
    doc = fitz.open(stream=pdf_bytes, filetype='pdf')
    page = doc[0]
    
    print("=== D3, D5, D6 PT WIDTH EXPERIMENT ===")
    print("PDF Page count:", len(doc))
    print("\nPage text blocks:")
    for b in page.get_text("blocks"):
        print(f"Block: ({b[0]:.1f}, {b[1]:.1f}, {b[2]:.1f}, {b[3]:.1f}) -> {repr(b[4].strip()[:60])}")

    with open("scratch_pt_experiment.pdf", "wb") as f:
        f.write(pdf_bytes)
    print("\nSaved to scratch_pt_experiment.pdf")
else:
    print("Pisa error:", pdf.err)
