from io import BytesIO
from PIL import Image, ImageDraw
import base64

# Empty Box: 16x16 crisp white square with 1.5px black border
img_empty = Image.new('RGBA', (16, 16), (255, 255, 255, 0))
draw_empty = ImageDraw.Draw(img_empty)
draw_empty.rectangle([1, 1, 14, 14], outline=(0, 0, 0, 255), fill=(255, 255, 255, 255), width=2)
buf_empty = BytesIO()
img_empty.save(buf_empty, format='PNG')
b64_empty = "data:image/png;base64," + base64.b64encode(buf_empty.getvalue()).decode('utf-8')

# Filled Box: 16x16 solid black square
img_filled = Image.new('RGBA', (16, 16), (255, 255, 255, 0))
draw_filled = ImageDraw.Draw(img_filled)
draw_filled.rectangle([1, 1, 14, 14], outline=(0, 0, 0, 255), fill=(0, 0, 0, 255), width=2)
buf_filled = BytesIO()
img_filled.save(buf_filled, format='PNG')
b64_filled = "data:image/png;base64," + base64.b64encode(buf_filled.getvalue()).decode('utf-8')

print("b64_empty =", repr(b64_empty))
print("b64_filled =", repr(b64_filled))
