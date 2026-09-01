import os, sys, fitz
from io import BytesIO
from xhtml2pdf import pisa

svg_test = """
<!DOCTYPE html>
<html>
<head>
<style>
@page { size: a4 portrait; margin: 8mm 10mm; }
body { font-family: Helvetica, Arial, sans-serif; font-size: 8pt; }
</style>
</head>
<body>
<h3>SVG RENDER TEST IN XHTML2PDF</h3>
<svg width="540" height="250" viewBox="0 0 540 250" xmlns="http://www.w3.org/2000/svg">
    <!-- Yellow Cause Favorite Bar -->
    <rect x="150" y="5" width="240" height="16" fill="#ffff00" stroke="#000000" stroke-width="0.5" />
    <text x="270" y="16" font-size="9" font-weight="bold" text-anchor="middle" fill="#000000">Cause favorite</text>
    
    <!-- Connection lines -->
    <line x1="95" y1="100" x2="115" y2="60" stroke="#41719c" stroke-width="1.5" />
    <line x1="95" y1="100" x2="115" y2="100" stroke="#41719c" stroke-width="1.5" />
    <line x1="95" y1="100" x2="115" y2="140" stroke="#41719c" stroke-width="1.5" />
    
    <!-- Node 1 -->
    <rect x="10" y="80" width="85" height="40" rx="4" ry="4" fill="#5b9bd5" />
    <text x="52" y="102" font-size="7" fill="#ffffff" text-anchor="middle">L'opérateur n'a pas</text>
    <text x="52" y="112" font-size="7" fill="#ffffff" text-anchor="middle">détecté le défaut</text>
    
    <!-- Node 2 Top -->
    <rect x="115" y="40" width="85" height="40" rx="4" ry="4" fill="#5b9bd5" />
    <text x="157" y="58" font-size="7" fill="#ffffff" text-anchor="middle">L'opérateur n'a pas</text>
    <text x="157" y="68" font-size="7" fill="#ffffff" text-anchor="middle">procédé par comp.</text>

    <!-- Node 2 Mid -->
    <rect x="115" y="88" width="85" height="40" rx="4" ry="4" fill="#5b9bd5" />
    <text x="157" y="106" font-size="7" fill="#ffffff" text-anchor="middle">L'opérateur n'a pas</text>
    <text x="157" y="116" font-size="7" fill="#ffffff" text-anchor="middle">utilisé la loupe</text>

    <!-- Node 2 Bot -->
    <rect x="115" y="136" width="85" height="40" rx="4" ry="4" fill="#5b9bd5" />
    <text x="157" y="154" font-size="7" fill="#ffffff" text-anchor="middle">Le défaut est</text>
    <text x="157" y="164" font-size="7" fill="#ffffff" text-anchor="middle">difficilement dét.</text>

    <!-- Result Box -->
    <rect x="430" y="40" width="100" height="40" rx="3" ry="3" fill="#fce4d6" stroke="#f8cbad" stroke-width="1" />
    <text x="480" y="58" font-size="7" font-weight="bold" fill="#000000" text-anchor="middle">Avéré : loupe améliore</text>
    <text x="480" y="68" font-size="7" font-weight="bold" fill="#000000" text-anchor="middle">le niveau de détection</text>
</svg>
</body>
</html>
"""

buf = BytesIO()
pisa.pisaDocument(BytesIO(svg_test.encode('utf-8')), buf)

doc = fitz.open(stream=buf.getvalue(), filetype='pdf')
print('SVG render test page count:', len(doc))
with open('test_svg_render.pdf', 'wb') as f:
    f.write(buf.getvalue())
print('Saved test_svg_render.pdf successfully!')
