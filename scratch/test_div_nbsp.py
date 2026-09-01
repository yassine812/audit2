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
td, th { border: 0.8pt solid #000; padding: 4pt; vertical-align: middle; }

.chk-box-empty {
    width: 7pt;
    height: 7pt;
    border: 0.8pt solid #000000;
    background-color: #ffffff;
    font-size: 1pt;
    line-height: 1pt;
    margin: 0 auto;
}
.chk-box-filled {
    width: 7pt;
    height: 7pt;
    border: 0.8pt solid #000000;
    background-color: #000000;
    font-size: 1pt;
    line-height: 1pt;
    margin: 0 auto;
}
</style>
</head>
<body>
<table>
    <tr>
        <th>Actions</th>
        <th>Oui</th>
        <th>Non</th>
    </tr>
    <tr>
        <td>Tri stock interne</td>
        <td align="center"><div class="chk-box-empty">&nbsp;</div></td>
        <td align="center"><div class="chk-box-filled">&nbsp;</div></td>
    </tr>
</table>
</body>
</html>
"""

pdf_buffer = BytesIO()
pisa.pisaDocument(BytesIO(html.encode('utf-8')), pdf_buffer)

with open("scratch_div_nbsp_test.pdf", "wb") as f:
    f.write(pdf_buffer.getvalue())

doc = fitz.open("scratch_div_nbsp_test.pdf")
print("=== DIV NBSP TEST ===")
page = doc[0]
drawings = page.get_drawings()
print("Total page drawings (rectangles drawn):", len(drawings))
for d in drawings:
    if 'rect' in d and d['rect'].width < 20 and d['rect'].height < 20:
        print("FOUND SMALL BOX RECT:", d['rect'], "fill:", d.get('fill'), "color:", d.get('color'))

