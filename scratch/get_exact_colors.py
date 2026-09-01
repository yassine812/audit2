from PIL import Image

img = Image.open("doc83_page1.png")
w, h = img.size
print(f"Image dimensions: {w}x{h}")

# Sample colors down the vertical center of the page
colors = {}
for y in range(0, h, 10):
    rgb = img.getpixel((w // 2, y))
    hex_c = '#{:02x}{:02x}{:02x}'.format(rgb[0], rgb[1], rgb[2])
    colors[hex_c] = colors.get(hex_c, 0) + 1

print("\nDominant non-white colors:")
for c, count in sorted(colors.items(), key=lambda x: x[1], reverse=True)[:15]:
    if c not in ('#ffffff', '#000000'):
        print(f"Hex {c}: {count} occurrences")
