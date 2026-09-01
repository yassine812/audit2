from io import BytesIO
from xhtml2pdf import pisa
import fitz

html = """
<!DOCTYPE html>
<html>
<head>
<style>
@page { size: a4; margin: 10mm; }
body { font-family: Helvetica, Arial, sans-serif; font-size: 9pt; }
table { width: 100%; border-collapse: collapse; }
td, th { border: 1px solid #000; padding: 4px; text-align: center; }
.bg-header { background-color: #d9e1f2; font-weight: bold; }
.italic { font-style: italic; }
.square-filled { font-size: 10pt; }
.square-empty { font-size: 10pt; }
</style>
</head>
<body>
<table>
    <tr class="bg-header">
        <th style="text-align:left;">Actions</th>
        <th class="italic">Oui</th>
        <th class="italic">Non</th>
        <th>Quantité triée</th>
        <th>Quantité NOK</th>
    </tr>
    <tr>
        <td style="text-align:left;">Tri stock interne</td>
        <td>■</td>
        <td>□</td>
        <td>—</td>
        <td>—</td>
    </tr>
    <tr>
        <td style="text-align:left;">Tri stock externe</td>
        <td>[ X ]</td>
        <td>[ &nbsp; ]</td>
        <td>—</td>
        <td>—</td>
    </tr>
    <tr>
        <td style="text-align:left;">Repère unitaire</td>
        <td><font face="Helvetica">&#9632;</font></td>
        <td><font face="Helvetica">&#9633;</font></td>
        <td>—</td>
        <td>—</td>
    </tr>
</table>
</body>
</html>
"""

pdf_buffer = BytesIO()
pisa.pisaDocument(BytesIO(html.encode('utf-8')), pdf_buffer)

with open("scratch_checkbox_test.pdf", "wb") as f:
    f.write(pdf_buffer.getvalue())

doc = fitz.open("scratch_checkbox_test.pdf")
print("=== CHECKBOX RENDERING AUDIT ===")
for b in doc[0].get_text('blocks'):
    print(repr(b[4].strip()))
