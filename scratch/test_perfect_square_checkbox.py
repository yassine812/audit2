from io import BytesIO
from xhtml2pdf import pisa
import fitz
from PIL import Image, ImageDraw
import base64

# Create 16x16 crisp empty checkbox PNG & filled checkbox PNG
img_empty = Image.new('RGBA', (16, 16), (255, 255, 255, 0))
draw_empty = ImageDraw.Draw(img_empty)
draw_empty.rectangle([1, 1, 14, 14], outline=(0, 0, 0, 255), fill=(255, 255, 255, 255), width=2)
buf_empty = BytesIO()
img_empty.save(buf_empty, format='PNG')
b64_empty = "data:image/png;base64," + base64.b64encode(buf_empty.getvalue()).decode('utf-8')

img_filled = Image.new('RGBA', (16, 16), (255, 255, 255, 0))
draw_filled = ImageDraw.Draw(img_filled)
draw_filled.rectangle([1, 1, 14, 14], outline=(0, 0, 0, 255), fill=(0, 0, 0, 255), width=2)
buf_filled = BytesIO()
img_filled.save(buf_filled, format='PNG')
b64_filled = "data:image/png;base64," + base64.b64encode(buf_filled.getvalue()).decode('utf-8')

html = f"""
<!DOCTYPE html>
<html>
<head>
<style>
@page {{ size: a4; margin: 10mm; }}
body {{ font-family: Helvetica, Arial, sans-serif; font-size: 8pt; }}
table {{ width: 540pt; border-collapse: collapse; margin: 0 auto; }}
td, th {{ border: 0.8pt solid #000; padding: 4pt; vertical-align: middle; }}
</style>
</head>
<body>
<table>
    <tr>
        <th width="200pt">Actions</th>
        <th width="35pt">Oui</th>
        <th width="35pt">Non</th>
    </tr>
    <tr>
        <td>Tri stock interne (Base64 PNG Test)</td>
        <td align="center"><img src="{b64_empty}" width="9pt" height="9pt" /></td>
        <td align="center"><img src="{b64_filled}" width="9pt" height="9pt" /></td>
    </tr>
</table>
</body>
</html>
"""

pdf_buffer = BytesIO()
pisa.pisaDocument(BytesIO(html.encode('utf-8')), pdf_buffer)

with open("scratch_square_png_test.pdf", "wb") as f:
    f.write(pdf_buffer.getvalue())

doc = fitz.open("scratch_square_png_test.pdf")
print("=== PERFECT SQUARE PNG TEST ===")
page = doc[0]
print("Images found on page:", len(page.get_images()))
for img in page.get_images():
    print("  Image:", img)

print("\nSUCCESS!")
