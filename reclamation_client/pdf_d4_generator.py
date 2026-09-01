import base64, math, json
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont


def _normalize_chains(raw, cause_principale=""):
    """Normalize data from pourquoi JSON fields."""
    if not raw:
        return []

    if isinstance(raw, list) and len(raw) > 0 and isinstance(raw[0], dict) and "chain" in raw[0]:
        return raw

    if isinstance(raw, list) and len(raw) > 0 and isinstance(raw[0], dict) and "pourquoi" in raw[0]:
        chain = [{"pourquoi": d.get("pourquoi", "")} for d in raw if d.get("pourquoi")]
        if chain:
            return [{"chain": chain, "justification": cause_principale}]
        return []

    if isinstance(raw, list) and len(raw) > 0 and isinstance(raw[0], str):
        chain = [{"pourquoi": s} for s in raw if s]
        if chain:
            return [{"chain": chain, "justification": cause_principale}]
        return []

    return []


def draw_wrapped_text(draw, x, y, width, height, text, font, fill="#002060", line_spacing=26):
    """Draw text wrapped inside a bounding box with proper padding and vertical centering.
    
    Guarantees no newline characters exist in individual line strings to prevent PIL anchor errors.
    """
    if not text:
        return

    lines = []
    for paragraph in str(text).splitlines():
        words = paragraph.split()
        if not words:
            lines.append("")
            continue
        current_line = ""
        for w in words:
            test_line = f"{current_line} {w}" if current_line else w
            bbox = draw.textbbox((0, 0), test_line, font=font)
            line_w = bbox[2] - bbox[0]
            if line_w <= width - 18:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = w
        if current_line:
            lines.append(current_line)

    if not lines:
        return

    total_h = len(lines) * line_spacing
    start_y = y + max(8, (height - total_h) // 2)
    for l in lines:
        if l:
            draw.text((x + width // 2, start_y), l, font=font, fill=fill, anchor="mt")
        start_y += line_spacing


def draw_arrow_connector(draw, x1, y1, x2, y2, color="#305496", width=8, arrow_size=22):
    """Draw a bold connector line with a clean arrowhead terminating exactly at (x2, y2)."""
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
    p2 = (x2 - ux * arrow_size + px * (arrow_size * 0.65), y2 - uy * arrow_size + py * (arrow_size * 0.65))
    p3 = (x2 - ux * arrow_size - px * (arrow_size * 0.65), y2 - uy * arrow_size - py * (arrow_size * 0.65))
    draw.polygon([p1, p2, p3], fill=color)


def _draw_chain_row(draw, item, col_x, col_w, row_y, box_h,
                    color_blue_bg, color_blue_border, color_blue_text,
                    color_pink_bg, color_pink_border, color_pink_text,
                    font_node_bold):
    """Draw a single horizontal chain row of up to 5 Pourquoi boxes + 1 conclusion box."""
    chain = item.get('chain', []) if isinstance(item, dict) else []
    if not chain:
        return

    cy = row_y
    box_cy = cy + box_h // 2

    # Draw arrows between consecutive boxes
    for c_idx in range(len(chain) - 1):
        if c_idx < 4:
            src_right_x = col_x[c_idx] + col_w[c_idx]
            tgt_left_x = col_x[c_idx + 1]
            draw_arrow_connector(draw, src_right_x, box_cy, tgt_left_x, box_cy, color=color_blue_border)

    # Arrow from last chain box to conclusion box (column 4)
    if len(chain) > 0 and len(chain) <= 4:
        last_idx = len(chain) - 1
        src_right_x = col_x[last_idx] + col_w[last_idx]
        tgt_left_x = col_x[4]
        draw_arrow_connector(draw, src_right_x, box_cy, tgt_left_x, box_cy, color=color_blue_border)

    # Chain boxes (cols 0..3 or 0..4)
    for c_idx in range(min(len(chain), 4)):
        txt = chain[c_idx].get('pourquoi', '') if isinstance(chain[c_idx], dict) else str(chain[c_idx])
        if txt:
            cx = col_x[c_idx]
            cw = col_w[c_idx]
            draw.rounded_rectangle([(cx, cy), (cx + cw, cy + box_h)], radius=14, fill=color_blue_bg, outline=color_blue_border, width=3)
            draw_wrapped_text(draw, cx, cy, cw, box_h, txt, font_node_bold, fill=color_blue_text, line_spacing=26)

    # Conclusion box (column 4 - Pink/Orange Box)
    conc = item.get('justification', '') if isinstance(item, dict) else ''
    if not conc and len(chain) >= 5:
        conc = chain[4].get('pourquoi', '') if isinstance(chain[4], dict) else str(chain[4])

    if conc:
        cx = col_x[4]
        cw = col_w[4]
        draw.rounded_rectangle([(cx, cy), (cx + cw, cy + box_h)], radius=14, fill=color_pink_bg, outline=color_pink_border, width=4)
        draw_wrapped_text(draw, cx, cy, cw, box_h, conc, font_node_bold, fill=color_pink_text, line_spacing=26)


def generate_d4_diagram_base64(analyse_d4=None):
    """Génère une image PNG HD (1400 x 1540) du diagramme 5 Pourquoi D4.1 & D4.2 avec contraste ultra-élevé et zéro débordement."""
    w, h = 1400, 1540
    img = Image.new("RGB", (w, h), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    try:
        font_title = ImageFont.truetype("arialbd.ttf", 38)
        font_sec = ImageFont.truetype("arialbd.ttf", 32)
        font_head = ImageFont.truetype("arialbd.ttf", 26)
        font_node_bold = ImageFont.truetype("arialbd.ttf", 21)
        font_small = ImageFont.truetype("arialbi.ttf", 21)
        font_footer = ImageFont.truetype("arialbd.ttf", 22)
    except Exception:
        font_title = font_sec = font_head = font_node_bold = font_small = font_footer = ImageFont.load_default()

    # Column Positions & Geometry (Full Width 1400px)
    col_x = [25, 290, 545, 800, 1055]
    col_w = [230, 220, 220, 220, 320]

    # Doc.83 High-Contrast Color Palette
    color_blue_bg = "#d9e1f2"      # Soft Light Blue (Doc.83 Subheader Background)
    color_blue_border = "#305496"  # Dark Steel Blue Border
    color_blue_text = "#002060"    # Deep Navy Blue Text (Max Contrast & Clarity)

    color_pink_bg = "#fce4d6"      # Soft Pastel Orange (Doc.83 Highlight)
    color_pink_border = "#c65911"  # Dark Orange Border
    color_pink_text = "#000000"    # Solid Black Text

    # 1. Top Header Box
    draw.rectangle([(25, 15), (1375, 80)], outline="#000000", width=4)
    draw.text((700, 48), "D 4.1 à D 4.2", font=font_title, fill="#000000", anchor="mm")

    # 2. Section D4.1 - Non Détection
    draw.text((25, 100), "D 4.1 - NON DETECTION", font=font_sec, fill="#000000")
    draw.rectangle([(25, 140), (1375, 195)], fill="#ffff00", outline="#000000", width=3)
    draw.text((700, 168), "Cause favorite", font=font_head, fill="#000000", anchor="mm")

    # 5 Column Headers D4.1
    draw.text((140, 225), "1er POURQUOI?", font=font_head, fill="#000000", anchor="mm")
    draw.text((400, 225), "2ème POURQUOI?", font=font_head, fill="#000000", anchor="mm")
    draw.text((655, 225), "3ème POURQUOI?", font=font_head, fill="#000000", anchor="mm")
    draw.text((910, 225), "4ème POURQUOI?", font=font_head, fill="#000000", anchor="mm")
    draw.text((1215, 215), "5ème POURQUOI /", font=font_head, fill="#000000", anchor="mm")
    draw.text((1215, 240), "RESULTAT", font=font_head, fill="#000000", anchor="mm")

    row_y_d41 = [265, 460, 655]
    box_h = 175

    nd_cause_synth = getattr(analyse_d4, 'cause_principale_non_detection', '') if analyse_d4 else ''
    nd_chains_raw = getattr(analyse_d4, 'pourquoi_non_detection', []) if analyse_d4 else []
    nd_chains = _normalize_chains(nd_chains_raw, nd_cause_synth)

    if nd_chains:
        for idx, item in enumerate(nd_chains[:3]):
            _draw_chain_row(
                draw, item, col_x, col_w,
                row_y_d41[idx], box_h,
                color_blue_bg, color_blue_border, color_blue_text,
                color_pink_bg, color_pink_border, color_pink_text,
                font_node_bold
            )
    else:
        # Default D4.1 Layout
        draw_arrow_connector(draw, 255, 547, 290, 352, color=color_blue_border)
        draw_arrow_connector(draw, 255, 547, 290, 547, color=color_blue_border)
        draw_arrow_connector(draw, 255, 547, 290, 742, color=color_blue_border)

        draw_arrow_connector(draw, 510, 352, 545, 352, color=color_blue_border)
        draw_arrow_connector(draw, 765, 352, 800, 352, color=color_blue_border)
        draw_arrow_connector(draw, 1020, 352, 1055, 352, color=color_blue_border)

        draw_arrow_connector(draw, 510, 547, 545, 547, color=color_blue_border)
        draw_arrow_connector(draw, 765, 547, 800, 547, color=color_blue_border)
        draw_arrow_connector(draw, 1020, 547, 1055, 547, color=color_blue_border)

        draw_arrow_connector(draw, 510, 742, 545, 742, color=color_blue_border)
        draw_arrow_connector(draw, 765, 742, 800, 742, color=color_blue_border)
        draw_arrow_connector(draw, 1020, 742, 1055, 742, color=color_blue_border)

        boxes_d41 = [
            (25, 460, 230, box_h, "L'opérateur n'a pas\ndétecté le défaut"),
            (290, 265, 220, box_h, "L'opérateur n'a pas\nprocédé par comp.\n(2 pièces à la fois)"),
            (290, 460, 220, box_h, "L'opérateur n'a pas\nutilisé la loupe"),
            (290, 655, 220, box_h, "Le défaut est\ndifficilement dét."),
            (545, 265, 220, box_h, "Pas demandé dans\nla gamme"),
            (545, 460, 220, box_h, "Pas demandé dans\nla gamme"),
            (545, 655, 220, box_h, "Le défaut est trop petit\npour être dét. visuellement"),
            (800, 265, 220, box_h, "Eviter les détériorations\ndes pièces entre elles"),
            (800, 460, 220, box_h, "Jugement que le défaut\nest dét. à l'oeil nu"),
            (800, 655, 220, box_h, "Caractérisation du défaut\nlors de la prestation"),
        ]
        for x, y, bw, bh, text in boxes_d41:
            draw.rounded_rectangle([(x, y), (x + bw, y + bh)], radius=14, fill=color_blue_bg, outline=color_blue_border, width=3)
            draw_wrapped_text(draw, x, y, bw, bh, text, font_node_bold, fill=color_blue_text, line_spacing=26)

        conclusions_d41 = [
            (1055, 265, 320, box_h, "Avéré : on augmente le niveau\nde détection (2 pièces à la fois)"),
            (1055, 460, 320, box_h, "Avéré : la loupe améliore\nle niveau de détection"),
            (1055, 655, 320, box_h, "Non avéré : l'opérateur a écarté\ndes pièces plus petites"),
        ]
        for x, y, bw, bh, text in conclusions_d41:
            draw.rounded_rectangle([(x, y), (x + bw, y + bh)], radius=14, fill=color_pink_bg, outline=color_pink_border, width=4)
            draw_wrapped_text(draw, x, y, bw, bh, text, font_node_bold, fill=color_pink_text, line_spacing=26)

    # 3. Section D4.2 - Cause Technique
    draw.text((25, 855), "D 4.2 - CAUSE TECHNIQUE", font=font_sec, fill="#000000")
    draw.rectangle([(25, 895), (1375, 950)], fill="#ffff00", outline="#000000", width=3)
    draw.text((700, 923), "Cause favorite", font=font_head, fill="#000000", anchor="mm")

    draw.text((140, 980), "1er POURQUOI?", font=font_head, fill="#000000", anchor="mm")
    draw.text((400, 980), "2ème POURQUOI?", font=font_head, fill="#000000", anchor="mm")
    draw.text((655, 980), "3ème POURQUOI?", font=font_head, fill="#000000", anchor="mm")
    draw.text((910, 980), "4ème POURQUOI?", font=font_head, fill="#000000", anchor="mm")
    draw.text((1215, 980), "5ème POURQUOI / RESULTAT", font=font_head, fill="#000000", anchor="mm")

    row_y_d42 = [1015, 1210]

    tech_cause_synth = getattr(analyse_d4, 'cause_principale_technique', '') if analyse_d4 else ''
    tech_chains_raw = getattr(analyse_d4, 'pourquoi_technique', []) if analyse_d4 else []
    tech_chains = _normalize_chains(tech_chains_raw, tech_cause_synth)

    if tech_chains:
        for idx, item in enumerate(tech_chains[:2]):
            _draw_chain_row(
                draw, item, col_x, col_w,
                row_y_d42[idx], box_h,
                color_blue_bg, color_blue_border, color_blue_text,
                color_pink_bg, color_pink_border, color_pink_text,
                font_node_bold
            )
    else:
        # Default D4.2 Layout
        draw_arrow_connector(draw, 255, 1102, 290, 1102, color=color_blue_border)
        draw_arrow_connector(draw, 510, 1102, 545, 1102, color=color_blue_border)
        draw_arrow_connector(draw, 765, 1102, 800, 1102, color=color_blue_border)
        draw_arrow_connector(draw, 1020, 1102, 1055, 1102, color=color_blue_border)

        draw_arrow_connector(draw, 255, 1297, 290, 1297, color=color_blue_border)
        draw_arrow_connector(draw, 510, 1297, 545, 1297, color=color_blue_border)
        draw_arrow_connector(draw, 765, 1297, 800, 1297, color=color_blue_border)
        draw_arrow_connector(draw, 1020, 1297, 1055, 1297, color=color_blue_border)

        boxes_d42_r1 = [
            (25, 1015, 230, box_h, "Mix des pièces chez\nle Client final"),
            (290, 1015, 220, box_h, "Pas d'identification\nunitaire sur pièces"),
            (545, 1015, 220, box_h, "Identification sur\nunité Manutention"),
            (800, 1015, 220, box_h, "Pas de repère\nvisuel au poste"),
        ]
        for x, y, bw, bh, text in boxes_d42_r1:
            draw.rounded_rectangle([(x, y), (x + bw, y + bh)], radius=14, fill=color_blue_bg, outline=color_blue_border, width=3)
            draw_wrapped_text(draw, x, y, bw, bh, text, font_node_bold, fill=color_blue_text, line_spacing=26)

        draw.rounded_rectangle([(1055, 1015), (1375, 1015 + box_h)], radius=14, fill=color_pink_bg, outline=color_pink_border, width=4)
        draw_wrapped_text(draw, 1055, 1015, 320, box_h, "Avéré : un marquage unitaire\naurait permis de distinguer", font_node_bold, fill=color_pink_text, line_spacing=26)

        boxes_d42_r2 = [
            (25, 1210, 230, box_h, "Client final réclame\nsur faces diff."),
            (290, 1210, 220, box_h, "Sécurisation concerne\nsurfaces critiques"),
            (545, 1210, 220, box_h, "Défauts sur surfaces\nn'impactent pas func."),
            (800, 1210, 220, box_h, "Spécification gamme\nincomplète"),
        ]
        for x, y, bw, bh, text in boxes_d42_r2:
            draw.rounded_rectangle([(x, y), (x + bw, y + bh)], radius=14, fill=color_blue_bg, outline=color_blue_border, width=3)
            draw_wrapped_text(draw, x, y, bw, bh, text, font_node_bold, fill=color_blue_text, line_spacing=26)

        draw.rounded_rectangle([(1055, 1210), (1375, 1210 + box_h)], radius=14, fill=color_pink_bg, outline=color_pink_border, width=4)
        draw_wrapped_text(draw, 1055, 1210, 320, box_h, "Avéré : les deux surfaces sont\nidentifiées sur la gamme", font_node_bold, fill=color_pink_text, line_spacing=26)

    # 4. Instruction Box
    draw.rectangle([(25, 1410), (1375, 1485)], fill="#ffffff", outline="#000000", width=3)
    instruction_text = "A chaque étape du 5 pourquoi, vérifier avec les données que le lien de cause à effect soit effectif. Se demander pourquoi ? Autant de fois que nécessaire."
    draw_wrapped_text(draw, 25, 1410, 1350, 75, instruction_text, font_small, fill="#000000", line_spacing=24)

    # 5. Footer
    draw.text((25, 1505), "D4.1 D4.2", font=font_footer, fill="#000000")

    buf = BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("utf-8")
