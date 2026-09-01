import os, sys, math, base64
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

def draw_wrapped_text(draw, x, y, width, height, text, font, fill="#ffffff", line_spacing=18):
    """Draw text wrapped inside a bounding box with proper padding and centering."""
    if not text:
        return
    words = text.replace("\n", " \n ").split(" ")
    lines = []
    current_line = ""
    for w in words:
        if w == "\n":
            lines.append(current_line)
            current_line = ""
            continue
        test_line = (current_line + " " + w).strip()
        bbox = draw.textbbox((0, 0), test_line, font=font)
        line_w = bbox[2] - bbox[0]
        if line_w <= width - 12:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = w
    if current_line:
        lines.append(current_line)

    total_h = len(lines) * line_spacing
    start_y = y + (height - total_h) // 2 + 8
    for l in lines:
        draw.text((x + width // 2, start_y), l, font=font, fill=fill, anchor="mm")
        start_y += line_spacing

def draw_arrow_connector(draw, x1, y1, x2, y2, color="#41719c", width=3, arrow_size=9):
    """Draw a connector line with a clean arrowhead terminating exactly at (x2, y2)."""
    dx = x2 - x1
    dy = y2 - y1
    dist = math.hypot(dx, dy)
    if dist < 2:
        return
    ux, uy = dx / dist, dy / dist
    px, py = -uy, ux

    stop_x = x2 - ux * arrow_size
    stop_y = y2 - uy * arrow_size
    draw.line([(x1, y1), (stop_x, stop_y)], fill=color, width=width)

    p1 = (x2, y2)
    p2 = (x2 - ux * arrow_size + px * (arrow_size * 0.55), y2 - uy * arrow_size + py * (arrow_size * 0.55))
    p3 = (x2 - ux * arrow_size - px * (arrow_size * 0.55), y2 - uy * arrow_size - py * (arrow_size * 0.55))
    draw.polygon([p1, p2, p3], fill=color)

def generate_large_d4_diagram_base64(analyse_d4=None):
    """Génère une image PNG grand format (1100 x 1350) pour remplir la page A4 du PDF."""
    w, h = 1100, 1350
    img = Image.new("RGB", (w, h), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    try:
        font_title = ImageFont.truetype("arialbd.ttf", 26)
        font_sec = ImageFont.truetype("arialbd.ttf", 22)
        font_head = ImageFont.truetype("arialbd.ttf", 17)
        font_node = ImageFont.truetype("arial.ttf", 15)
        font_node_bold = ImageFont.truetype("arialbd.ttf", 15)
        font_small = ImageFont.truetype("ariali.ttf", 15)
        font_footer = ImageFont.truetype("arial.ttf", 15)
    except Exception:
        font_title = font_sec = font_head = font_node = font_node_bold = font_small = font_footer = ImageFont.load_default()

    # Column Positions & Geometry (Proportional for 1100px width)
    col_x = [25, 235, 435, 635, 835]
    col_w = [180, 160, 160, 160, 240]

    # 1. Top Header Box
    draw.rectangle([(25, 15), (1075, 65)], outline="#000000", width=3)
    draw.text((550, 40), "D 4.1 à D 4.2", font=font_title, fill="#000000", anchor="mm")

    # 2. Section D4.1
    draw.text((25, 90), "D 4.1 - NON DETECTION", font=font_sec, fill="#000000")
    draw.rectangle([(25, 125), (1075, 165)], fill="#ffff00", outline="#000000", width=2)
    draw.text((550, 145), "Cause favorite", font=font_head, fill="#000000", anchor="mm")

    # 5 Column Headers D4.1
    draw.text((115, 195), "1er POURQUOI?", font=font_head, fill="#000000", anchor="mm")
    draw.text((315, 195), "2ème POURQUOI?", font=font_head, fill="#000000", anchor="mm")
    draw.text((515, 195), "3ème POURQUOI?", font=font_head, fill="#000000", anchor="mm")
    draw.text((715, 195), "4ème POURQUOI?", font=font_head, fill="#000000", anchor="mm")
    draw.text((955, 187), "5ème POURQUOI /", font=font_head, fill="#000000", anchor="mm")
    draw.text((955, 207), "RESULTAT", font=font_head, fill="#000000", anchor="mm")

    # D4.1 Rows: Row 1 (230), Row 2 (330), Row 3 (430). Box height = 75px.
    row_y_d41 = [230, 330, 430]
    box_h = 75

    nd_chains = getattr(analyse_d4, 'pourquoi_non_detection', []) if analyse_d4 else []
    
    if nd_chains and len(nd_chains) >= 1:
        for idx, item in enumerate(nd_chains[:3]):
            chain = item.get('chain', [])
            cy = row_y_d41[idx]
            box_cy = cy + box_h // 2
            
            if idx == 0:
                root_right_x = col_x[0] + col_w[0]
                root_cy = row_y_d41[1] + box_h // 2
                for r_idx in range(min(len(nd_chains), 3)):
                    target_left_x = col_x[1]
                    target_cy = row_y_d41[r_idx] + box_h // 2
                    draw_arrow_connector(draw, root_right_x, root_cy, target_left_x, target_cy)
            
            for c_idx in range(1, len(chain)):
                if c_idx < 4:
                    src_right_x = col_x[c_idx] + col_w[c_idx]
                    tgt_left_x = col_x[c_idx + 1]
                    draw_arrow_connector(draw, src_right_x, box_cy, tgt_left_x, box_cy)

        # Col 1 Box
        draw.rounded_rectangle([(col_x[0], row_y_d41[1]), (col_x[0] + col_w[0], row_y_d41[1] + box_h)], radius=8, fill="#5b9bd5")
        col1_txt = nd_chains[0].get('chain', [{}])[0].get('pourquoi', "L'opérateur n'a pas\ndétecté le défaut") if len(nd_chains[0].get('chain', [])) > 0 else "L'opérateur n'a pas\ndétecté le défaut"
        draw_wrapped_text(draw, col_x[0], row_y_d41[1], col_w[0], box_h, col1_txt, font_node, fill="#ffffff")

        for idx, item in enumerate(nd_chains[:3]):
            chain = item.get('chain', [])
            cy = row_y_d41[idx]
            for c_idx in range(1, 4):
                if c_idx < len(chain):
                    txt = chain[c_idx].get('pourquoi', '')
                    if txt:
                        cx = col_x[c_idx]
                        cw = col_w[c_idx]
                        draw.rounded_rectangle([(cx, cy), (cx + cw, cy + box_h)], radius=8, fill="#5b9bd5")
                        draw_wrapped_text(draw, cx, cy, cw, box_h, txt, font_node, fill="#ffffff")
            conc = item.get('justification', '')
            if conc:
                cx = col_x[4]
                cw = col_w[4]
                draw.rounded_rectangle([(cx, cy), (cx + cw, cy + box_h)], radius=6, fill="#fce4d6", outline="#f8cbad", width=2)
                draw_wrapped_text(draw, cx, cy, cw, box_h, conc, font_node_bold, fill="#000000")
    else:
        # Default D4.1 Layout
        draw_arrow_connector(draw, 205, 367, 235, 267)
        draw_arrow_connector(draw, 205, 367, 235, 367)
        draw_arrow_connector(draw, 205, 367, 235, 467)

        draw_arrow_connector(draw, 395, 267, 435, 267)
        draw_arrow_connector(draw, 595, 267, 635, 267)
        draw_arrow_connector(draw, 795, 267, 835, 267)

        draw_arrow_connector(draw, 395, 367, 435, 367)
        draw_arrow_connector(draw, 595, 367, 635, 367)
        draw_arrow_connector(draw, 795, 367, 835, 367)

        draw_arrow_connector(draw, 395, 467, 435, 467)
        draw_arrow_connector(draw, 595, 467, 635, 467)
        draw_arrow_connector(draw, 795, 467, 835, 467)

        boxes_d41 = [
            (25, 330, 180, box_h, "L'opérateur n'a pas\ndétecté le défaut"),
            (235, 230, 160, box_h, "L'opérateur n'a pas\nprocédé par comp.\n(2 pièces à la fois)"),
            (235, 330, 160, box_h, "L'opérateur n'a pas\nutilisé la loupe"),
            (235, 430, 160, box_h, "Le défaut est\ndifficilement dét."),
            (435, 230, 160, box_h, "Pas demandé dans\nla gamme"),
            (435, 330, 160, box_h, "Pas demandé dans\nla gamme"),
            (435, 430, 160, box_h, "Le défaut est trop petit\npour être dét. visuellement"),
            (635, 230, 160, box_h, "Eviter les détériorations\ndes pièces entre elles"),
            (635, 330, 160, box_h, "Jugement que le défaut\nest dét. à l'oeil nu"),
            (635, 430, 160, box_h, "Caractérisation du défaut\nlors de la prestation"),
        ]
        for x, y, bw, bh, text in boxes_d41:
            draw.rounded_rectangle([(x, y), (x + bw, y + bh)], radius=8, fill="#5b9bd5")
            draw_wrapped_text(draw, x, y, bw, bh, text, font_node, fill="#ffffff")

        conclusions_d41 = [
            (835, 230, 240, box_h, "Avéré : on augmente le niveau\nde détection (2 pièces à la fois)"),
            (835, 330, 240, box_h, "Avéré : la loupe améliore\nle niveau de détection"),
            (835, 430, 240, box_h, "Non avéré : l'opérateur a écarté\ndes pièces plus petites"),
        ]
        for x, y, bw, bh, text in conclusions_d41:
            draw.rounded_rectangle([(x, y), (x + bw, y + bh)], radius=6, fill="#fce4d6", outline="#f8cbad", width=2)
            draw_wrapped_text(draw, x, y, bw, bh, text, font_node_bold, fill="#000000")

    # 3. Section D4.2
    draw.text((25, 545), "D 4.2 - CAUSE TECHNIQUE", font=font_sec, fill="#000000")
    draw.rectangle([(25, 580), (1075, 620)], fill="#ffff00", outline="#000000", width=2)
    draw.text((550, 600), "Cause favorite", font=font_head, fill="#000000", anchor="mm")

    draw.text((115, 650), "1er POURQUOI?", font=font_head, fill="#000000", anchor="mm")
    draw.text((315, 650), "2ème POURQUOI?", font=font_head, fill="#000000", anchor="mm")
    draw.text((515, 650), "3ème POURQUOI?", font=font_head, fill="#000000", anchor="mm")
    draw.text((715, 650), "4ème POURQUOI?", font=font_head, fill="#000000", anchor="mm")
    draw.text((955, 650), "5ème POURQUOI / RESULTAT", font=font_head, fill="#000000", anchor="mm")

    row_y_d42 = [685, 785]

    tech_chains = getattr(analyse_d4, 'pourquoi_technique', []) if analyse_d4 else []

    if tech_chains and len(tech_chains) >= 1:
        for idx, item in enumerate(tech_chains[:2]):
            chain = item.get('chain', [])
            cy = row_y_d42[idx]
            box_cy = cy + box_h // 2
            for c_idx in range(len(chain) - 1):
                if c_idx < 4:
                    src_right_x = col_x[c_idx] + col_w[c_idx]
                    tgt_left_x = col_x[c_idx + 1]
                    draw_arrow_connector(draw, src_right_x, box_cy, tgt_left_x, box_cy)

        for idx, item in enumerate(tech_chains[:2]):
            chain = item.get('chain', [])
            cy = row_y_d42[idx]
            for c_idx in range(4):
                if c_idx < len(chain):
                    txt = chain[c_idx].get('pourquoi', '')
                    if txt:
                        cx = col_x[c_idx]
                        cw = col_w[c_idx]
                        draw.rounded_rectangle([(cx, cy), (cx + cw, cy + box_h)], radius=8, fill="#5b9bd5")
                        draw_wrapped_text(draw, cx, cy, cw, box_h, txt, font_node, fill="#ffffff")
            conc = item.get('justification', '')
            if conc:
                cx = col_x[4]
                cw = col_w[4]
                draw.rounded_rectangle([(cx, cy), (cx + cw, cy + box_h)], radius=6, fill="#fce4d6", outline="#f8cbad", width=2)
                draw_wrapped_text(draw, cx, cy, cw, box_h, conc, font_node_bold, fill="#000000")
    else:
        # Default D4.2 Layout
        draw_arrow_connector(draw, 205, 722, 235, 722)
        draw_arrow_connector(draw, 395, 722, 435, 722)
        draw_arrow_connector(draw, 595, 722, 635, 722)
        draw_arrow_connector(draw, 795, 722, 835, 722)

        draw_arrow_connector(draw, 205, 822, 235, 822)
        draw_arrow_connector(draw, 395, 822, 435, 822)
        draw_arrow_connector(draw, 595, 822, 635, 822)
        draw_arrow_connector(draw, 795, 822, 835, 822)

        boxes_d42_r1 = [
            (25, 685, 180, box_h, "Mix des pièces chez\nle Client final"),
            (235, 685, 160, box_h, "Pas d'identification\nunitaire sur pièces"),
            (435, 685, 160, box_h, "Identification sur\nunité Manutention"),
            (635, 685, 160, box_h, "Pas de repère\nvisuel au poste"),
        ]
        for x, y, bw, bh, text in boxes_d42_r1:
            draw.rounded_rectangle([(x, y), (x + bw, y + bh)], radius=8, fill="#5b9bd5")
            draw_wrapped_text(draw, x, y, bw, bh, text, font_node, fill="#ffffff")

        draw.rounded_rectangle([(835, 685), (1075, 685 + box_h)], radius=6, fill="#fce4d6", outline="#f8cbad", width=2)
        draw_wrapped_text(draw, 835, 685, 240, box_h, "Avéré : un marquage unitaire\naurait permis de distinguer", font_node_bold, fill="#000000")

        boxes_d42_r2 = [
            (25, 785, 180, box_h, "Client final réclame\nsur faces diff."),
            (235, 785, 160, box_h, "Sécurisation concerne\nsurfaces critiques"),
            (435, 785, 160, box_h, "Défauts sur surfaces\nn'impactent pas func."),
            (635, 785, 160, box_h, "Spécification gamme\nincomplète"),
        ]
        for x, y, bw, bh, text in boxes_d42_r2:
            draw.rounded_rectangle([(x, y), (x + bw, y + bh)], radius=8, fill="#5b9bd5")
            draw_wrapped_text(draw, x, y, bw, bh, text, font_node, fill="#ffffff")

        draw.rounded_rectangle([(835, 785), (1075, 785 + box_h)], radius=6, fill="#fce4d6", outline="#f8cbad", width=2)
        draw_wrapped_text(draw, 835, 785, 240, box_h, "Avéré : les deux surfaces sont\nidentifiées sur la gamme", font_node_bold, fill="#000000")

    # 4. Instruction Box
    draw.rectangle([(25, 895), (1075, 945)], fill="#ffffff", outline="#000000", width=2)
    draw.text((550, 920), "A chaque étape du 5 pourquoi, vérifier avec les données que le lien de cause à effect soit effectif. Se demander pourquoi ? Autant de fois que nécessaire.", font=font_small, fill="#000000", anchor="mm")

    # 5. Footer
    draw.text((25, 970), "D4.1 D4.2", font=font_footer, fill="#000000")
    draw.text((1075, 970), "Doc.83 Rapport 8D du 17_03_2020", font=font_footer, fill="#000000", anchor="rm")

    buf = BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("utf-8")

b64 = generate_large_d4_diagram_base64()
print("Generated Large D4 Diagram PNG Base64! Length:", len(b64))
