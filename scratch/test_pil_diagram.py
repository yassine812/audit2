import os, sys, base64
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

def generate_d4_diagram_png(nd_chains=None, tech_chains=None):
    # Dimensions for high-res A4 printable diagram (1080 x 640)
    w, h = 1080, 640
    img = Image.new("RGB", (w, h), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    # Try loading Helvetica / Arial font or default font
    try:
        font_title = ImageFont.truetype("arial.ttf", 20)
        font_sec = ImageFont.truetype("arial.ttf", 16)
        font_head = ImageFont.truetype("arial.ttf", 13)
        font_node = ImageFont.truetype("arial.ttf", 11)
        font_node_bold = ImageFont.truetype("arialbd.ttf", 11)
        font_small = ImageFont.truetype("ariali.ttf", 11)
        font_footer = ImageFont.truetype("arial.ttf", 11)
    except Exception:
        font_title = font_sec = font_head = font_node = font_node_bold = font_small = font_footer = ImageFont.load_default()

    # 1. Top Header
    draw.rectangle([(20, 10), (1060, 46)], outline="#000000", width=2)
    draw.text((540, 28), "D 4.1 à D 4.2", font=font_title, fill="#000000", anchor="mm")

    # 2. D4.1 Section
    draw.text((20, 65), "D 4.1 - NON DETECTION", font=font_sec, fill="#000000")
    
    # Yellow Cause favorite bar D4.1
    draw.rectangle([(20, 80), (1060, 106)], fill="#ffff00", outline="#000000", width=1)
    draw.text((540, 93), "Cause favorite", font=font_head, fill="#000000", anchor="mm")

    # 5 Column Headers D4.1
    draw.text((110, 122), "1er POURQUOI?", font=font_head, fill="#000000", anchor="mm")
    draw.text((310, 122), "2ème POURQUOI?", font=font_head, fill="#000000", anchor="mm")
    draw.text((510, 122), "3ème POURQUOI?", font=font_head, fill="#000000", anchor="mm")
    draw.text((710, 122), "4ème POURQUOI?", font=font_head, fill="#000000", anchor="mm")
    draw.text((945, 118), "5ème POURQUOI /", font=font_head, fill="#000000", anchor="mm")
    draw.text((945, 132), "RESULTAT", font=font_head, fill="#000000", anchor="mm")

    # Connectors D4.1
    draw.line([(200, 230), (230, 175)], fill="#41719c", width=2)
    draw.line([(200, 230), (230, 230)], fill="#41719c", width=2)
    draw.line([(200, 230), (230, 285)], fill="#41719c", width=2)

    draw.line([(390, 175), (430, 175)], fill="#41719c", width=2)
    draw.line([(590, 175), (630, 175)], fill="#41719c", width=2)
    draw.line([(790, 175), (830, 175)], fill="#41719c", width=2)

    draw.line([(390, 230), (430, 230)], fill="#41719c", width=2)
    draw.line([(590, 230), (630, 230)], fill="#41719c", width=2)
    draw.line([(790, 230), (830, 230)], fill="#41719c", width=2)

    draw.line([(390, 285), (430, 285)], fill="#41719c", width=2)
    draw.line([(590, 285), (630, 285)], fill="#41719c", width=2)
    draw.line([(790, 285), (830, 285)], fill="#41719c", width=2)

    # Blue Boxes D4.1
    boxes_d41 = [
        # Col 1
        (20, 205, 180, 50, "L'opérateur n'a pas\ndétecté le défaut"),
        # Col 2
        (230, 150, 160, 50, "L'opérateur n'a pas\nprocédé par comp.\n(2 pièces à la fois)"),
        (230, 205, 160, 50, "L'opérateur n'a pas\nutilisé la loupe"),
        (230, 260, 160, 50, "Le défaut est\ndifficilement dét."),
        # Col 3
        (430, 150, 160, 50, "Pas demandé dans\nla gamme"),
        (430, 205, 160, 50, "Pas demandé dans\nla gamme"),
        (430, 260, 160, 50, "Le défaut est trop petit\npour être dét. visuellement"),
        # Col 4
        (630, 150, 160, 50, "Eviter les détériorations\ndes pièces entre elles"),
        (630, 205, 160, 50, "Jugement que le défaut\nest dét. à l'oeil nu"),
        (630, 260, 160, 50, "Caractérisation du défaut\nlors de la prestation"),
    ]

    for x, y, bw, bh, text in boxes_d41:
        draw.rounded_rectangle([(x, y), (x + bw, y + bh)], radius=6, fill="#5b9bd5")
        lines = text.split("\n")
        total_th = len(lines) * 13
        sy = y + (bh - total_th) // 2 + 6
        for line in lines:
            draw.text((x + bw // 2, sy), line, font=font_node, fill="#ffffff", anchor="mm")
            sy += 13

    # Conclusions D4.1
    conclusions_d41 = [
        (830, 150, 230, 50, "Avéré : on augmente le niveau\nde détection (2 pièces à la fois)"),
        (830, 205, 230, 50, "Avéré : la loupe améliore\nle niveau de détection"),
        (830, 260, 230, 50, "Non avéré : l'opérateur a écarté\ndes pièces plus petites"),
    ]

    for x, y, bw, bh, text in conclusions_d41:
        draw.rounded_rectangle([(x, y), (x + bw, y + bh)], radius=4, fill="#fce4d6", outline="#f8cbad", width=2)
        lines = text.split("\n")
        total_th = len(lines) * 13
        sy = y + (bh - total_th) // 2 + 6
        for line in lines:
            draw.text((x + bw // 2, sy), line, font=font_node_bold, fill="#000000", anchor="mm")
            sy += 13

    # 3. D4.2 Section
    draw.text((20, 335), "D 4.2 - CAUSE TECHNIQUE", font=font_sec, fill="#000000")

    # Yellow Cause favorite bar D4.2
    draw.rectangle([(20, 350), (1060, 376)], fill="#ffff00", outline="#000000", width=1)
    draw.text((540, 363), "Cause favorite", font=font_head, fill="#000000", anchor="mm")

    # 5 Column Headers D4.2
    draw.text((110, 392), "1er POURQUOI?", font=font_head, fill="#000000", anchor="mm")
    draw.text((310, 392), "2ème POURQUOI?", font=font_head, fill="#000000", anchor="mm")
    draw.text((510, 392), "3ème POURQUOI?", font=font_head, fill="#000000", anchor="mm")
    draw.text((710, 392), "4ème POURQUOI?", font=font_head, fill="#000000", anchor="mm")
    draw.text((945, 392), "5ème POURQUOI / RESULTAT", font=font_head, fill="#000000", anchor="mm")

    # Connectors D4.2
    draw.line([(200, 435), (230, 435)], fill="#41719c", width=2)
    draw.line([(390, 435), (430, 435)], fill="#41719c", width=2)
    draw.line([(590, 435), (630, 435)], fill="#41719c", width=2)
    draw.line([(790, 435), (830, 435)], fill="#41719c", width=2)

    draw.line([(200, 495), (230, 495)], fill="#41719c", width=2)
    draw.line([(390, 495), (430, 495)], fill="#41719c", width=2)
    draw.line([(590, 495), (630, 495)], fill="#41719c", width=2)
    draw.line([(790, 495), (830, 495)], fill="#41719c", width=2)

    # Blue Boxes D4.2 Row 1
    boxes_d42_r1 = [
        (20, 410, 180, 50, "Mix des pièces chez\nle Client final"),
        (230, 410, 160, 50, "Pas d'identification\nunitaire sur pièces"),
        (430, 410, 160, 50, "Identification sur\nunité Manutention"),
        (630, 410, 160, 50, "Pas de repère\nvisuel au poste"),
    ]
    for x, y, bw, bh, text in boxes_d42_r1:
        draw.rounded_rectangle([(x, y), (x + bw, y + bh)], radius=6, fill="#5b9bd5")
        lines = text.split("\n")
        total_th = len(lines) * 13
        sy = y + (bh - total_th) // 2 + 6
        for line in lines:
            draw.text((x + bw // 2, sy), line, font=font_node, fill="#ffffff", anchor="mm")
            sy += 13

    draw.rounded_rectangle([(830, 410), (1060, 460)], radius=4, fill="#fce4d6", outline="#f8cbad", width=2)
    draw.text((945, 428), "Avéré : un marquage unitaire", font=font_node_bold, fill="#000000", anchor="mm")
    draw.text((945, 442), "aurait permis de distinguer", font=font_node_bold, fill="#000000", anchor="mm")

    # Blue Boxes D4.2 Row 2
    boxes_d42_r2 = [
        (20, 470, 180, 50, "Client final réclame\nsur faces diff."),
        (230, 470, 160, 50, "Sécurisation concerne\nsurfaces critiques"),
        (430, 470, 160, 50, "Défauts sur surfaces\nn'impactent pas func."),
        (630, 470, 160, 50, "Spécification gamme\nincomplète"),
    ]
    for x, y, bw, bh, text in boxes_d42_r2:
        draw.rounded_rectangle([(x, y), (x + bw, y + bh)], radius=6, fill="#5b9bd5")
        lines = text.split("\n")
        total_th = len(lines) * 13
        sy = y + (bh - total_th) // 2 + 6
        for line in lines:
            draw.text((x + bw // 2, sy), line, font=font_node, fill="#ffffff", anchor="mm")
            sy += 13

    draw.rounded_rectangle([(830, 470), (1060, 520)], radius=4, fill="#fce4d6", outline="#f8cbad", width=2)
    draw.text((945, 488), "Avéré : les deux surfaces sont", font=font_node_bold, fill="#000000", anchor="mm")
    draw.text((945, 502), "identifiées sur la gamme", font=font_node_bold, fill="#000000", anchor="mm")

    # 4. Instruction Box
    draw.rectangle([(20, 535), (1060, 565)], fill="#ffffff", outline="#000000", width=1)
    draw.text((540, 550), "A chaque étape du 5 pourquoi, vérifier avec les données que le lien de cause à effet soit effectif. Se demander pourquoi ? Autant de fois que nécessaire.", font=font_small, fill="#000000", anchor="mm")

    # 5. Footer
    draw.text((20, 580), "D4.1 D4.2", font=font_footer, fill="#000000")
    draw.text((1060, 580), "Doc.83 Rapport 8D du 17_03_2020", font=font_footer, fill="#000000", anchor="rm")

    buf = BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("utf-8")

b64 = generate_d4_diagram_png()
print("Generated PIL PNG Data URI! Length:", len(b64))

# Test putting in xhtml2pdf
html = f"""
<!DOCTYPE html>
<html>
<head>
<style>
@page {{ size: a4 portrait; margin: 6mm 8mm; }}
body {{ margin: 0; padding: 0; }}
</style>
</head>
<body>
<img src="{b64}" style="width:100%; height:auto;" />
</body>
</html>
"""

from xhtml2pdf import pisa
buf_pdf = BytesIO()
pisa.pisaDocument(BytesIO(html.encode("utf-8")), buf_pdf)

import fitz
doc = fitz.open(stream=buf_pdf.getvalue(), filetype="pdf")
print("PIL Diagram PDF Page Count:", len(doc))
with open("test_pil_d4_pdf.pdf", "wb") as f:
    f.write(buf_pdf.getvalue())
print("Saved test_pil_d4_pdf.pdf successfully!")
