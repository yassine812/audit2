import os, sys, math, base64
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

def draw_arrow_line(draw, x1, y1, x2, y2, color="#41719c", width=2, arrow_size=7):
    # Draw main line segment up to arrow base
    dx = x2 - x1
    dy = y2 - y1
    dist = math.hypot(dx, dy)
    if dist < 1:
        return
    ux, uy = dx / dist, dy / dist
    px, py = -uy, ux

    # Line stops slightly before tip so arrow head covers it
    stop_x = x2 - ux * arrow_size
    stop_y = y2 - uy * arrow_size
    draw.line([(x1, y1), (stop_x, stop_y)], fill=color, width=width)

    # Arrowhead polygon
    p1 = (x2, y2)
    p2 = (x2 - ux * arrow_size + px * (arrow_size * 0.6), y2 - uy * arrow_size + py * (arrow_size * 0.6))
    p3 = (x2 - ux * arrow_size - px * (arrow_size * 0.6), y2 - uy * arrow_size - py * (arrow_size * 0.6))
    draw.polygon([p1, p2, p3], fill=color)

print("Testing arrow function...")
img = Image.new("RGB", (400, 200), (255, 255, 255))
draw = ImageDraw.Draw(img)
draw_arrow_line(draw, 50, 100, 200, 100)
draw_arrow_line(draw, 50, 150, 200, 50)
img.save("test_arrow_out.png")
print("Saved test_arrow_out.png successfully!")
