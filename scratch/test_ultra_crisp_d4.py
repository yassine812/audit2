import os, sys, math, base64
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

def draw_wrapped_text(draw, x, y, width, height, text, font, fill="#ffffff", line_spacing=22):
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
        if line_w <= width - 14:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = w
    if current_line:
        lines.append(current_line)

    total_h = len(lines) * line_spacing
    start_y = y + (height - total_h) // 2 + 10
    for l in lines:
        draw.text((x + width // 2, start_y), l, font=font, fill=fill, anchor="mm")
        start_y += line_spacing

def draw_arrow_connector(draw, x1, y1, x2, y2, color="#2b6cb0", width=4, arrow_size=12):
    """Draw a connector line with a bold clean arrowhead terminating exactly at (x2, y2)."""
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
    p2 = (x2 - ux * arrow_size + px * (arrow_size * 0.6), y2 - uy * arrow_size + py * (arrow_size * 0.6))
    p3 = (x2 - ux * arrow_size - px * (arrow_size * 0.6), y2 - uy * arrow_size - py * (arrow_size * 0.6))
    draw.polygon([p1, p2, p3], fill=color)

def generate_ultra_crisp_d4_diagram_base64(analyse_d4=None):
    """Génère une image PNG haute lisibilité (1200 x 1150) avec texte gras 18pt ultra lisible."""
    w, h = 1200, 1150
    img = Image.new("RGB", (w, h), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    try:
        font_title = ImageFont.truetype("arialbd.ttf", 30)
        font_sec = ImageFont.truetype("arialbd.ttf", 24)
        font_head = ImageFont.truetype("arialbd.ttf", 20)
        font_node_bold = ImageFont.truetype("arialbd.ttf", 17)
        font_small = ImageFont.truetype("arialbi.ttf", 16)
        font_footer = ImageFont.truetype("arialbd.ttf", 16)
    except Exception:
        font_title = font_sec = font_head = font_node_bold = font_small = font_footer = ImageFont.load_default()

    # Column Positions & Geometry
    col_x = [25, 255, 475, 695, 915]
    col_w = [200, 190, 190, 190, 260]

    # Colors
    color_blue_bg = "#2b6cb0" # Rich High-contrast Blue
    color_pink_bg = "#fde6d8" # Crisp Rose/Peach
    color_pink_border = "#d97724" # Bold Border for Rose box

    # 1. Top Header Box
    draw.rectangle([(25, 15), (1175, 70)], outline="#000000", width=3)
    draw.text((600, 42), "D 4.1 à D 4.2", font=font_title, fill="#000000", anchor="mm")

    # 2. Section D4.1
    draw.text((25, 95), "D 4.1 - NON DETECTION", font=font_sec, fill="#000000")
    draw.rectangle([(25, 135), (1175, 180)], fill="#ffff00", outline="#000000", width=2)
    draw.text((600, 158), "Cause favorite", font=font_head, fill="#000000", anchor="mm")

    # 5 Column Headers D4.1
    draw.text((125, 210), "1er POURQUOI?", font=font_head, fill="#000000", anchor="mm")
    draw.text((350, 210), "2ème POURQUOI?", font=font_head, fill="#000000", anchor="mm")
    draw.text((570, 210), "3ème POURQUOI?", font=font_head, fill="#000000", anchor="mm")
    draw.text((790, 210), "4ème POURQUOI?", font=font_head, fill="#000000", anchor="mm")
    draw.text((1045, 202), "5ème POURQUOI /", font=font_head, fill="#000000", anchor="mm")
    draw.text((1045, 224), "RESULTAT", font=font_head, fill="#000000", anchor="mm")

    # D4.1 Rows: Row 1 (250), Row 2 (360), Row 3 (470). Box height = 90px.
    row_y_d41 = [250, 360, 470]
    box_h = 90

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
        draw.rounded_rectangle([(col_x[0], row_y_d41[1]), (col_x[0] + col_w[0], row_y_d41[1] + box_h)], radius=10, fill=color_blue_bg)
        col1_txt = nd_chains[0].get('chain', [{}])[0].get('pourquoi', "L'opérateur n'a pas\ndétecté le défaut") if len(nd_chains[0].get('chain', [])) > 0 else "L'opérateur n'a pas\ndétecté le défaut"
        draw_wrapped_text(draw, col_x[0], row_y_d41[1], col_w[0], box_h, col1_txt, font_node_bold, fill="#ffffff")

        for idx, item in enumerate(nd_chains[:3]):
            chain = item.get('chain', [])
            cy = row_y_d41[idx]
            for c_idx in range(1, 4):
                if c_idx < len(chain):
                    txt = chain[c_idx].get('pourquoi', '')
                    if txt:
                        cx = col_x[c_idx]
                        cw = col_w[c_idx]
                        draw.rounded_rectangle([(cx, cy), (cx + cw, cy + box_h)], radius=10, fill=color_blue_bg)
                        draw_wrapped_text(draw, cx, cy, cw, box_h, txt, font_node_bold, fill="#ffffff")
            conc = item.get('justification', '')
            if conc:
                cx = col_x[4]
                cw = col_w[4]
                draw.rounded_rectangle([(cx, cy), (cx + cw, cy + box_h)], radius=8, fill=color_pink_bg, outline=color_pink_border, width=3)
                draw_wrapped_text(draw, cx, cy, cw, box_h, conc, font_node_bold, fill="#000000")
    else:
        # Default D4.1 Layout
        draw_arrow_connector(draw, 225, 405, 255, 295)
        draw_arrow_connector(draw, 225, 405, 255, 405)
        draw_arrow_connector(draw, 225, 405, 255, 515)

        draw_arrow_connector(draw, 445, 295, 475, 295)
        draw_arrow_connector(draw, 665, 295, 695, 295)
        draw_arrow_connector(draw, 885, 295, 915, 295)

        draw_arrow_connector(draw, 445, 405, 475, 405)
        draw_arrow_connector(draw, 665, 405, 695, 405)
        draw_arrow_connector(draw, 885, 405, 915, 405)

        draw_arrow_connector(draw, 445, 515, 475, 515)
        draw_arrow_connector(draw, 665, 515, 695, 515)
        draw_arrow_connector(draw, 885, 515, 915, 515)

        boxes_d41 = [
            (25, 360, 200, box_h, "L'opérateur n'a pas\ndétecté le défaut"),
            (255, 250, 190, box_h, "L'opérateur n'a pas\nprocédé par comp.\n(2 pièces à la fois)"),
            (255, 360, 190, box_h, "L'opérateur n'a pas\nutilisé la loupe"),
            (255, 470, 190, box_h, "Le défaut est\ndifficilement dét."),
            (475, 250, 190, box_h, "Pas demandé dans\nla gamme"),
            (475, 360, 190, box_h, "Pas demandé dans\nla gamme"),
            (475, 470, 190, box_h, "Le défaut est trop petit\npour être dét. visuellement"),
            (695, 250, 190, box_h, "Eviter les détériorations\ndes pièces entre elles"),
            (695, 360, 190, box_h, "Jugement que le défaut\nest dét. à l'oeil nu"),
            (695, 470, 190, box_h, "Caractérisation du défaut\nlors de la prestation"),
        ]
        for x, y, bw, bh, text in boxes_d41:
            draw.rounded_rectangle([(x, y), (x + bw, y + bh)], radius=10, fill=color_blue_bg)
            draw_wrapped_text(draw, x, y, bw, bh, text, font_node_bold, fill="#ffffff")

        conclusions_d41 = [
            (915, 250, 260, box_h, "Avéré : on augmente le niveau\nde détection (2 pièces à la fois)"),
            (915, 360, 260, box_h, "Avéré : la loupe améliore\nle niveau de détection"),
            (915, 470, 260, box_h, "Non avéré : l'opérateur a écarté\ndes pièces plus petites"),
        ]
        for x, y, bw, bh, text in conclusions_d41:
            draw.rounded_rectangle([(x, y), (x + bw, y + bh)], radius=8, fill=color_pink_bg, outline=color_pink_border, width=3)
            draw_wrapped_text(draw, x, y, bw, bh, text, font_node_bold, fill="#000000")

    # 3. Section D4.2
    draw.text((25, 595), "D 4.2 - CAUSE TECHNIQUE", font=font_sec, fill="#000000")
    draw.rectangle([(25, 635), (1175, 680)], fill="#ffff00", outline="#000000", width=2)
    draw.text((600, 658), "Cause favorite", font=font_head, fill="#000000", anchor="mm")

    draw.text((125, 710), "1er POURQUOI?", font=font_head, fill="#000000", anchor="mm")
    draw.text((350, 710), "2ème POURQUOI?", font=font_head, fill="#000000", anchor="mm")
    draw.text((570, 710), "3ème POURQUOI?", font=font_head, fill="#000000", anchor="mm")
    draw.text((790, 710), "4ème POURQUOI?", font=font_head, fill="#000000", anchor="mm")
    draw.text((1045, 710), "5ème POURQUOI / RESULTAT", font=font_head, fill="#000000", anchor="mm")

    row_y_d42 = [750, 860]

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
                        draw.rounded_rectangle([(cx, cy), (cx + cw, cy + box_h)], radius=10, fill=color_blue_bg)
                        draw_wrapped_text(draw, cx, cy, cw, box_h, txt, font_node_bold, fill="#ffffff")
            conc = item.get('justification', '')
            if conc:
                cx = col_x[4]
                cw = col_w[4]
                draw.rounded_rectangle([(cx, cy), (cx + cw, cy + box_h)], radius=8, fill=color_pink_bg, outline=color_pink_border, width=3)
                draw_wrapped_text(draw, cx, cy, cw, box_h, conc, font_node_bold, fill="#000000")
    else:
        # Default D4.2 Layout
        draw_arrow_connector(draw, 225, 795, 255, 795)
        draw_arrow_connector(draw, 445, 795, 475, 795)
        draw_arrow_connector(draw, 665, 795, 695, 795)
        draw_arrow_connector(draw, 885, 795, 915, 795)

        draw_arrow_connector(draw, 225, 905, 255, 905)
        draw_arrow_connector(draw, 445, 905, 475, 905)
        draw_arrow_connector(draw, 665, 905, 695, 905)
        draw_arrow_connector(draw, 885, 905, 915, 905)

        boxes_d42_r1 = [
            (25, 750, 200, box_h, "Mix des pièces chez\nle Client final"),
            (255, 750, 190, box_h, "Pas d'identification\nunitaire sur pièces"),
            (475, 750, 190, box_h, "Identification sur\nunité Manutention"),
            (695, 750, 190, box_h, "Pas de repère\nvisuel au poste"),
        ]
        for x, y, bw, bh, text in boxes_d42_r1:
            draw.rounded_rectangle([(x, y), (x + bw, y + bh)], radius=10, fill=color_blue_bg)
            draw_wrapped_text(draw, x, y, bw, bh, text, font_node_bold, fill="#ffffff")

        draw.rounded_rectangle([(915, 750), (1175, 750 + box_h)], radius=8, fill=color_pink_bg, outline=color_pink_border, width=3)
        draw_wrapped_text(draw, 915, 750, 260, box_h, "Avéré : un marquage unitaire\naurait permis de distinguer", font_node_bold, fill="#000000")

        boxes_d42_r2 = [
            (25, 860, 200, box_h, "Client final réclame\nsur faces diff."),
            (255, 860, 190, box_h, "Sécurisation concerne\nsurfaces critiques"),
            (475, 860, 190, box_h, "Défauts sur surfaces\nn'impactent pas func."),
            (695, 860, 190, box_h, "Spécification gamme\nincomplète"),
        ]
        for x, y, bw, bh, text in boxes_d42_r2:
            draw.rounded_rectangle([(x, y), (x + bw, y + bh)], radius=10, fill=color_blue_bg)
            draw_wrapped_text(draw, x, y, bw, bh, text, font_node_bold, fill="#ffffff")

        draw.rounded_rectangle([(915, 860), (1175, 860 + box_h)], radius=8, fill=color_pink_bg, outline=color_pink_border, width=3)
        draw_wrapped_text(draw, 915, 860, 260, box_h, "Avéré : les deux surfaces sont\nidentifiées sur la gamme", font_node_bold, fill="#000000")

    # 4. Instruction Box
    draw.rectangle([(25, 980), (1175, 1040)], fill="#ffffff", outline="#000000", width=2)
    draw.text((600, 1010), "A chaque étape du 5 pourquoi, vérifier avec les données que le lien de cause à effect soit effectif. Se demander pourquoi ? Autant de fois que nécessaire.", font=font_small, fill="#000000", anchor="mm")

    # 5. Footer
    draw.text((25, 1080), "D4.1 D4.2", font=font_footer, fill="#000000")
    draw.text((1175, 1080), "Doc.83 Rapport 8D du 17_03_2020", font=font_footer, fill="#000000", anchor="rm")

    buf = BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("utf-8")

b64 = generate_ultra_crisp_d4_diagram_base64()
print("Generated Ultra Crisp D4 Diagram PNG Base64! Length:", len(b64))
