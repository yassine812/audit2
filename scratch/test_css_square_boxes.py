from io import BytesIO
from xhtml2pdf import pisa
import fitz

html = """
<!DOCTYPE html>
<html>
<head>
<style>
@page { size: a4; margin: 10mm; }
body { font-family: Helvetica, Arial, sans-serif; font-size: 8pt; }
table { width: 540pt; border-collapse: collapse; margin: 0 auto; }
td, th { border: 0.8pt solid #000; padding: 3pt; vertical-align: middle; }
.bg-header { background-color: #d9e1f2; font-weight: bold; }
.italic { font-style: italic; }
.box-filled { width: 6pt; height: 6pt; background-color: #000000; border: 0.8pt solid #000000; margin: 0 auto; }
.box-empty { width: 6pt; height: 6pt; background-color: #ffffff; border: 0.8pt solid #000000; margin: 0 auto; }
</style>
</head>
<body>
<table>
    <tr class="bg-header">
        <th width="200pt" style="text-align:left;">Actions</th>
        <th width="35pt" class="italic" style="text-align:center;">Oui</th>
        <th width="35pt" class="italic" style="text-align:center;">Non</th>
        <th width="135pt" style="text-align:center;">Quantité triée</th>
        <th width="135pt" style="text-align:center;">Quantité NOK</th>
    </tr>
    <tr>
        <td width="200pt" style="text-align:left;">Tri stock interne</td>
        <td width="35pt" align="center"><div class="box-empty"></div></td>
        <td width="35pt" align="center"><div class="box-filled"></div></td>
        <td width="135pt" align="center">—</td>
        <td width="135pt" align="center">—</td>
    </tr>
    <tr>
        <td width="200pt" style="text-align:left;">Tri stock externe</td>
        <td width="35pt" align="center"><div class="box-filled"></div></td>
        <td width="35pt" align="center"><div class="box-empty"></div></td>
        <td width="135pt" align="center">—</td>
        <td width="135pt" align="center">—</td>
    </tr>
</table>
</body>
</html>
"""

pdf_buffer = BytesIO()
pisa.pisaDocument(BytesIO(html.encode('utf-8')), pdf_buffer)

with open("scratch_css_square_test.pdf", "wb") as f:
    f.write(pdf_buffer.getvalue())

doc = fitz.open("scratch_css_square_test.pdf")
print("=== CSS SQUARE BOXES AUDIT ===")
page = doc[0]
print("Total page drawings / rects:", len(page.get_drawings()))
for b in page.get_text('blocks'):
    print(repr(b[4].strip()))

print("\nSUCCESS!")
