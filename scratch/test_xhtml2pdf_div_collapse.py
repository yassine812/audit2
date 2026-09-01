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

/* Test 1: Empty Div */
.box-empty-div { width: 8pt; height: 8pt; background-color: #ffffff; border: 1pt solid #000000; margin: 0 auto; }

/* Test 2: Span with non-breaking space & line-height */
.box-empty-span { display: inline-block; width: 8pt; height: 8pt; border: 1pt solid #000000; background-color: #ffffff; font-size: 1pt; line-height: 8pt; }

/* Test 3: Table cell with inner mini table or symbol */
.box-table { width: 8pt; height: 8pt; border: 1pt solid #000000; background-color: #ffffff; margin: 0 auto; }

/* Test 4: Unicode Ballot Box ☐ (U+2610) vs font DejaVu / Wingdings / standard */
</style>
</head>
<body>
<table>
    <tr>
        <th>Method</th>
        <th>Oui</th>
        <th>Non</th>
    </tr>
    <tr>
        <td>Test 1: Empty Div</td>
        <td align="center"><div class="box-empty-div"></div></td>
        <td align="center"><div class="box-empty-div"></div></td>
    </tr>
    <tr>
        <td>Test 2: Span with space</td>
        <td align="center"><span class="box-empty-span">&nbsp;</span></td>
        <td align="center"><span class="box-empty-span">&nbsp;</span></td>
    </tr>
    <tr>
        <td>Test 3: Inner Table Box</td>
        <td align="center"><table class="box-table"><tr><td>&nbsp;</td></tr></table></td>
        <td align="center"><table class="box-table"><tr><td>&nbsp;</td></tr></table></td>
    </tr>
    <tr>
        <td>Test 4: Unicode Checkbox Square U+25A2 or [ ]</td>
        <td align="center">&#9633;</td>
        <td align="center">&#9633;</td>
    </tr>
    <tr>
        <td>Test 5: Clean Bracket Square [ &nbsp; ]</td>
        <td align="center">[ &nbsp; ]</td>
        <td align="center">[ &nbsp; ]</td>
    </tr>
</table>
</body>
</html>
"""

pdf_buffer = BytesIO()
pisa.pisaDocument(BytesIO(html.encode('utf-8')), pdf_buffer)

with open("scratch_div_collapse_test.pdf", "wb") as f:
    f.write(pdf_buffer.getvalue())

doc = fitz.open("scratch_div_collapse_test.pdf")
print("=== DIV COLLAPSE AUDIT ===")
page = doc[0]
print("Total page drawings (rectangles drawn):", len(page.get_drawings()))
for b in page.get_text('blocks'):
    print(repr(b[4].strip()))
