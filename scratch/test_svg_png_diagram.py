import os, sys, base64
from io import BytesIO
from svglib.svglib import svg2rlg
from reportlab.graphics import renderPM

svg_code = """<svg width="1080" height="640" viewBox="0 0 1080 640" xmlns="http://www.w3.org/2000/svg">
    <rect width="1080" height="640" fill="#ffffff" />
    
    <!-- Top Header -->
    <rect x="20" y="10" width="1040" height="36" fill="#ffffff" stroke="#000000" stroke-width="2"/>
    <text x="540" y="34" font-family="Helvetica, Arial" font-size="20" font-weight="bold" text-anchor="middle" fill="#000000">D 4.1 à D 4.2</text>

    <!-- D4.1 Title -->
    <text x="20" y="70" font-family="Helvetica, Arial" font-size="18" font-weight="bold" fill="#000000">D 4.1 - NON DETECTION</text>

    <!-- Yellow Cause Favorite Bar D4.1 -->
    <rect x="20" y="80" width="1040" height="28" fill="#ffff00" stroke="#000000" stroke-width="1.5"/>
    <text x="540" y="100" font-family="Helvetica, Arial" font-size="15" font-weight="bold" text-anchor="middle" fill="#000000">Cause favorite</text>

    <!-- 5 Column Headers -->
    <text x="110" y="130" font-family="Helvetica, Arial" font-size="14" font-weight="bold" text-anchor="middle">1er POURQUOI?</text>
    <text x="310" y="130" font-family="Helvetica, Arial" font-size="14" font-weight="bold" text-anchor="middle">2ème POURQUOI?</text>
    <text x="510" y="130" font-family="Helvetica, Arial" font-size="14" font-weight="bold" text-anchor="middle">3ème POURQUOI?</text>
    <text x="710" y="130" font-family="Helvetica, Arial" font-size="14" font-weight="bold" text-anchor="middle">4ème POURQUOI?</text>
    <text x="940" y="125" font-family="Helvetica, Arial" font-size="13" font-weight="bold" text-anchor="middle">5ème POURQUOI /</text>
    <text x="940" y="140" font-family="Helvetica, Arial" font-size="13" font-weight="bold" text-anchor="middle">RESULTAT</text>

    <!-- Connecting lines D4.1 -->
    <line x1="200" y1="240" x2="230" y2="175" stroke="#41719c" stroke-width="2"/>
    <line x1="200" y1="240" x2="230" y2="240" stroke="#41719c" stroke-width="2"/>
    <line x1="200" y1="240" x2="230" y2="305" stroke="#41719c" stroke-width="2"/>
    
    <line x1="390" y1="175" x2="430" y2="175" stroke="#41719c" stroke-width="2"/>
    <line x1="590" y1="175" x2="630" y2="175" stroke="#41719c" stroke-width="2"/>
    <line x1="790" y1="175" x2="830" y2="175" stroke="#41719c" stroke-width="2"/>

    <line x1="390" y1="240" x2="430" y2="240" stroke="#41719c" stroke-width="2"/>
    <line x1="590" y1="240" x2="630" y2="240" stroke="#41719c" stroke-width="2"/>
    <line x1="790" y1="240" x2="830" y2="240" stroke="#41719c" stroke-width="2"/>

    <line x1="390" y1="305" x2="430" y2="305" stroke="#41719c" stroke-width="2"/>
    <line x1="590" y1="305" x2="630" y2="305" stroke="#41719c" stroke-width="2"/>
    <line x1="790" y1="305" x2="830" y2="305" stroke="#41719c" stroke-width="2"/>

    <!-- Nodes D4.1 Col 1 -->
    <rect x="20" y="215" width="180" height="50" rx="6" fill="#5b9bd5"/>
    <text x="110" y="238" font-family="Helvetica, Arial" font-size="12" fill="#ffffff" text-anchor="middle">L'opérateur n'a pas</text>
    <text x="110" y="253" font-family="Helvetica, Arial" font-size="12" fill="#ffffff" text-anchor="middle">détecté le défaut</text>

    <!-- Nodes D4.1 Col 2 -->
    <rect x="230" y="150" width="160" height="50" rx="6" fill="#5b9bd5"/>
    <text x="310" y="167" font-family="Helvetica, Arial" font-size="11" fill="#ffffff" text-anchor="middle">L'opérateur n'a pas</text>
    <text x="310" y="180" font-family="Helvetica, Arial" font-size="11" fill="#ffffff" text-anchor="middle">procédé par comp.</text>
    <text x="310" y="193" font-family="Helvetica, Arial" font-size="10" fill="#ffffff" text-anchor="middle">(2 pièces à la fois)</text>

    <rect x="230" y="215" width="160" height="50" rx="6" fill="#5b9bd5"/>
    <text x="310" y="238" font-family="Helvetica, Arial" font-size="11" fill="#ffffff" text-anchor="middle">L'opérateur n'a pas</text>
    <text x="310" y="253" font-family="Helvetica, Arial" font-size="11" fill="#ffffff" text-anchor="middle">utilisé la loupe</text>

    <rect x="230" y="280" width="160" height="50" rx="6" fill="#5b9bd5"/>
    <text x="310" y="303" font-family="Helvetica, Arial" font-size="11" fill="#ffffff" text-anchor="middle">Le défaut est</text>
    <text x="310" y="318" font-family="Helvetica, Arial" font-size="11" fill="#ffffff" text-anchor="middle">difficilement dét.</text>

    <!-- Nodes D4.1 Col 3 -->
    <rect x="430" y="150" width="160" height="50" rx="6" fill="#5b9bd5"/>
    <text x="510" y="174" font-family="Helvetica, Arial" font-size="11" fill="#ffffff" text-anchor="middle">Pas demandé dans</text>
    <text x="510" y="189" font-family="Helvetica, Arial" font-size="11" fill="#ffffff" text-anchor="middle">la gamme</text>

    <rect x="430" y="215" width="160" height="50" rx="6" fill="#5b9bd5"/>
    <text x="510" y="239" font-family="Helvetica, Arial" font-size="11" fill="#ffffff" text-anchor="middle">Pas demandé dans</text>
    <text x="510" y="254" font-family="Helvetica, Arial" font-size="11" fill="#ffffff" text-anchor="middle">la gamme</text>

    <rect x="430" y="280" width="160" height="50" rx="6" fill="#5b9bd5"/>
    <text x="510" y="301" font-family="Helvetica, Arial" font-size="10" fill="#ffffff" text-anchor="middle">Le défaut est trop petit</text>
    <text x="510" y="315" font-family="Helvetica, Arial" font-size="10" fill="#ffffff" text-anchor="middle">pour être dét. visuellement</text>

    <!-- Nodes D4.1 Col 4 -->
    <rect x="630" y="150" width="160" height="50" rx="6" fill="#5b9bd5"/>
    <text x="710" y="167" font-family="Helvetica, Arial" font-size="10" fill="#ffffff" text-anchor="middle">Eviter les détériorations</text>
    <text x="710" y="180" font-family="Helvetica, Arial" font-size="10" fill="#ffffff" text-anchor="middle">des pièces entre</text>
    <text x="710" y="193" font-family="Helvetica, Arial" font-size="10" fill="#ffffff" text-anchor="middle">elles</text>

    <rect x="630" y="215" width="160" height="50" rx="6" fill="#5b9bd5"/>
    <text x="710" y="238" font-family="Helvetica, Arial" font-size="10" fill="#ffffff" text-anchor="middle">Jugement que le défaut</text>
    <text x="710" y="253" font-family="Helvetica, Arial" font-size="10" fill="#ffffff" text-anchor="middle">est dét. à l'oeil nu</text>

    <rect x="630" y="280" width="160" height="50" rx="6" fill="#5b9bd5"/>
    <text x="710" y="303" font-family="Helvetica, Arial" font-size="10" fill="#ffffff" text-anchor="middle">Caractérisation du défaut</text>
    <text x="710" y="318" font-family="Helvetica, Arial" font-size="10" fill="#ffffff" text-anchor="middle">lors de la prestation</text>

    <!-- Conclusions D4.1 -->
    <rect x="830" y="150" width="230" height="50" rx="4" fill="#fce4d6" stroke="#f8cbad" stroke-width="1.5"/>
    <text x="945" y="172" font-family="Helvetica, Arial" font-size="10" font-weight="bold" fill="#000000" text-anchor="middle">Avéré : on augmente le niveau</text>
    <text x="945" y="187" font-family="Helvetica, Arial" font-size="10" font-weight="bold" fill="#000000" text-anchor="middle">de détection (2 pièces à la fois)</text>

    <rect x="830" y="215" width="230" height="50" rx="4" fill="#fce4d6" stroke="#f8cbad" stroke-width="1.5"/>
    <text x="945" y="237" font-family="Helvetica, Arial" font-size="10" font-weight="bold" fill="#000000" text-anchor="middle">Avéré : la loupe améliore</text>
    <text x="945" y="252" font-family="Helvetica, Arial" font-size="10" font-weight="bold" fill="#000000" text-anchor="middle">le niveau de détection</text>

    <rect x="830" y="280" width="230" height="50" rx="4" fill="#fce4d6" stroke="#f8cbad" stroke-width="1.5"/>
    <text x="945" y="302" font-family="Helvetica, Arial" font-size="10" font-weight="bold" fill="#000000" text-anchor="middle">Non avéré : l'opérateur a écarté</text>
    <text x="945" y="317" font-family="Helvetica, Arial" font-size="10" font-weight="bold" fill="#000000" text-anchor="middle">des pièces plus petites</text>

    <!-- D4.2 Section -->
    <text x="20" y="365" font-family="Helvetica, Arial" font-size="18" font-weight="bold" fill="#000000">D 4.2 - CAUSE TECHNIQUE</text>

    <!-- Yellow Cause Favorite Bar D4.2 -->
    <rect x="20" y="375" width="1040" height="28" fill="#ffff00" stroke="#000000" stroke-width="1.5"/>
    <text x="540" y="395" font-family="Helvetica, Arial" font-size="15" font-weight="bold" text-anchor="middle" fill="#000000">Cause favorite</text>

    <!-- 5 Column Headers D4.2 -->
    <text x="110" y="425" font-family="Helvetica, Arial" font-size="14" font-weight="bold" text-anchor="middle">1er POURQUOI?</text>
    <text x="310" y="425" font-family="Helvetica, Arial" font-size="14" font-weight="bold" text-anchor="middle">2ème POURQUOI?</text>
    <text x="510" y="425" font-family="Helvetica, Arial" font-size="14" font-weight="bold" text-anchor="middle">3ème POURQUOI?</text>
    <text x="710" y="425" font-family="Helvetica, Arial" font-size="14" font-weight="bold" text-anchor="middle">4ème POURQUOI?</text>
    <text x="940" y="425" font-family="Helvetica, Arial" font-size="13" font-weight="bold" text-anchor="middle">5ème POURQUOI / RESULTAT</text>

    <!-- Connecting lines D4.2 -->
    <line x1="200" y1="465" x2="230" y2="465" stroke="#41719c" stroke-width="2"/>
    <line x1="390" y1="465" x2="430" y2="465" stroke="#41719c" stroke-width="2"/>
    <line x1="590" y1="465" x2="630" y2="465" stroke="#41719c" stroke-width="2"/>
    <line x1="790" y1="465" x2="830" y2="465" stroke="#41719c" stroke-width="2"/>

    <line x1="200" y1="530" x2="230" y2="530" stroke="#41719c" stroke-width="2"/>
    <line x1="390" y1="530" x2="430" y2="530" stroke="#41719c" stroke-width="2"/>
    <line x1="590" y1="530" x2="630" y2="530" stroke="#41719c" stroke-width="2"/>
    <line x1="790" y1="530" x2="830" y2="530" stroke="#41719c" stroke-width="2"/>

    <!-- Nodes D4.2 Row 1 -->
    <rect x="20" y="440" width="180" height="50" rx="6" fill="#5b9bd5"/>
    <text x="110" y="457" font-family="Helvetica, Arial" font-size="11" fill="#ffffff" text-anchor="middle">Mix des pièces chez</text>
    <text x="110" y="472" font-family="Helvetica, Arial" font-size="11" fill="#ffffff" text-anchor="middle">le Client final</text>

    <rect x="230" y="440" width="160" height="50" rx="6" fill="#5b9bd5"/>
    <text x="310" y="457" font-family="Helvetica, Arial" font-size="11" fill="#ffffff" text-anchor="middle">Pas d'identification</text>
    <text x="310" y="472" font-family="Helvetica, Arial" font-size="11" fill="#ffffff" text-anchor="middle">unitaire sur pièces</text>

    <rect x="430" y="440" width="160" height="50" rx="6" fill="#5b9bd5"/>
    <text x="510" y="457" font-family="Helvetica, Arial" font-size="11" fill="#ffffff" text-anchor="middle">Identification sur</text>
    <text x="510" y="472" font-family="Helvetica, Arial" font-size="11" fill="#ffffff" text-anchor="middle">unité Manutention</text>

    <rect x="630" y="440" width="160" height="50" rx="6" fill="#5b9bd5"/>
    <text x="710" y="457" font-family="Helvetica, Arial" font-size="11" fill="#ffffff" text-anchor="middle">Pas de repère</text>
    <text x="710" y="472" font-family="Helvetica, Arial" font-size="11" fill="#ffffff" text-anchor="middle">visuel au poste</text>

    <rect x="830" y="440" width="230" height="50" rx="4" fill="#fce4d6" stroke="#f8cbad" stroke-width="1.5"/>
    <text x="945" y="462" font-family="Helvetica, Arial" font-size="10" font-weight="bold" fill="#000000" text-anchor="middle">Avéré : un marquage unitaire</text>
    <text x="945" y="477" font-family="Helvetica, Arial" font-size="10" font-weight="bold" fill="#000000" text-anchor="middle">aurait permis de distinguer</text>

    <!-- Nodes D4.2 Row 2 -->
    <rect x="20" y="505" width="180" height="50" rx="6" fill="#5b9bd5"/>
    <text x="110" y="522" font-family="Helvetica, Arial" font-size="11" fill="#ffffff" text-anchor="middle">Client final réclame</text>
    <text x="110" y="537" font-family="Helvetica, Arial" font-size="11" fill="#ffffff" text-anchor="middle">sur faces diff.</text>

    <rect x="230" y="505" width="160" height="50" rx="6" fill="#5b9bd5"/>
    <text x="310" y="522" font-family="Helvetica, Arial" font-size="11" fill="#ffffff" text-anchor="middle">Sécurisation concerne</text>
    <text x="310" y="537" font-family="Helvetica, Arial" font-size="11" fill="#ffffff" text-anchor="middle">surfaces critiques</text>

    <rect x="430" y="505" width="160" height="50" rx="6" fill="#5b9bd5"/>
    <text x="510" y="522" font-family="Helvetica, Arial" font-size="11" fill="#ffffff" text-anchor="middle">Défauts sur surfaces</text>
    <text x="510" y="537" font-family="Helvetica, Arial" font-size="11" fill="#ffffff" text-anchor="middle">n'impactent pas func.</text>

    <rect x="630" y="505" width="160" height="50" rx="6" fill="#5b9bd5"/>
    <text x="710" y="522" font-family="Helvetica, Arial" font-size="11" fill="#ffffff" text-anchor="middle">Spécification gamme</text>
    <text x="710" y="537" font-family="Helvetica, Arial" font-size="11" fill="#ffffff" text-anchor="middle">incomplète</text>

    <rect x="830" y="505" width="230" height="50" rx="4" fill="#fce4d6" stroke="#f8cbad" stroke-width="1.5"/>
    <text x="945" y="527" font-family="Helvetica, Arial" font-size="10" font-weight="bold" fill="#000000" text-anchor="middle">Avéré : les deux surfaces sont</text>
    <text x="945" y="542" font-family="Helvetica, Arial" font-size="10" font-weight="bold" fill="#000000" text-anchor="middle">identifiées sur la gamme</text>

    <!-- Instruction Box -->
    <rect x="20" y="570" width="1040" height="30" fill="#ffffff" stroke="#000000" stroke-width="1.5"/>
    <text x="540" y="590" font-family="Helvetica, Arial" font-size="12" font-style="italic" text-anchor="middle" fill="#000000">A chaque étape du 5 pourquoi, vérifier avec les données que le lien de cause à effet soit effectif. Se demander pourquoi ? Autant de fois que nécessaire.</text>

    <!-- Footer -->
    <text x="20" y="625" font-family="Helvetica, Arial" font-size="12" fill="#000000">D4.1 D4.2</text>
    <text x="1060" y="625" font-family="Helvetica, Arial" font-size="12" fill="#000000" text-anchor="end">Doc.83 Rapport 8D du 17_03_2020</text>
</svg>"""

drawing = svg2rlg(BytesIO(svg_code.encode('utf-8')))
img_data = renderPM.drawToString(drawing, fmt='PNG')

base64_png = "data:image/png;base64," + base64.b64encode(img_data).decode('utf-8')
print("Successfully generated high-res PNG from SVG! Length:", len(base64_png))

with open("test_generated_diagram.png", "wb") as f:
    f.write(img_data)
print("Saved test_generated_diagram.png successfully!")
