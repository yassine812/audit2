from io import BytesIO
from PIL import Image, ImageDraw
import base64

# Empty Box: 16x16 white square with crisp black border
img_empty = Image.new('RGBA', (16, 16), (255, 255, 255, 0))
draw_empty = ImageDraw.Draw(img_empty)
draw_empty.rectangle([1, 1, 14, 14], outline=(0, 0, 0, 255), fill=(255, 255, 255, 255), width=2)
buf_empty = BytesIO()
img_empty.save(buf_empty, format='PNG')
b64_empty = "data:image/png;base64," + base64.b64encode(buf_empty.getvalue()).decode('utf-8')

# Checked Box: 16x16 white square with crisp black border AND a clean black checkmark (tick mark)
img_checked = Image.new('RGBA', (16, 16), (255, 255, 255, 0))
draw_checked = ImageDraw.Draw(img_checked)
draw_checked.rectangle([1, 1, 14, 14], outline=(0, 0, 0, 255), fill=(255, 255, 255, 255), width=2)
# Draw thick checkmark lines: (3, 8) -> (6, 12) -> (12, 4)
draw_checked.line([(3, 8), (6, 11)], fill=(0, 0, 0, 255), width=2)
draw_checked.line([(6, 11), (12, 4)], fill=(0, 0, 0, 255), width=2)

buf_checked = BytesIO()
img_checked.save(buf_checked, format='PNG')
b64_checked = "data:image/png;base64," + base64.b64encode(buf_checked.getvalue()).decode('utf-8')

print("b64_empty =", repr(b64_empty))
print("b64_checked =", repr(b64_checked))
