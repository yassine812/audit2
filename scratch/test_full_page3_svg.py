import os, sys, django, fitz
from io import BytesIO
from xhtml2pdf import pisa

sys.path.insert(0, '.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')
django.setup()

from reclamation_client.models import ReclamationClient

rec = ReclamationClient.objects.filter(reference='REC2608010').first() or ReclamationClient.objects.first()

html_page3 = """
<!DOCTYPE html>
<html>
<head>
<style>
@page {
    size: a4 portrait;
    margin: 6mm 8mm;
}
body {
    font-family: Helvetica, Arial, sans-serif;
    font-size: 8pt;
    margin: 0;
    padding: 0;
}
.footer-note {
    font-size: 7pt;
    color: #333;
    margin-top: 5pt;
}
</style>
</head>
<body>

<div style="border:1pt solid #000; font-weight:bold; font-size:11pt; text-align:center; padding:3pt; margin-bottom:4pt;">
    D 4.1 à D 4.2
</div>

<h3 style="margin:2pt 0 1pt 0; font-size:10pt;">D 4.1 - NON DETECTION</h3>

<svg width="540" height="320" viewBox="0 0 540 320" xmlns="http://www.w3.org/2000/svg">
    <!-- Yellow Cause Favorite Bar -->
    <rect x="160" y="2" width="220" height="14" fill="#ffff00" stroke="#000000" stroke-width="0.5"/>
    <text x="270" y="12" font-size="8" font-weight="bold" text-anchor="middle" fill="#000000">Cause favorite</text>
    
    <!-- 5 Column Headers -->
    <text x="50" y="32" font-size="7.5" font-weight="bold" text-anchor="middle">1er POURQUOI?</text>
    <text x="150" y="32" font-size="7.5" font-weight="bold" text-anchor="middle">2ème POURQUOI?</text>
    <text x="250" y="32" font-size="7.5" font-weight="bold" text-anchor="middle">3ème POURQUOI?</text>
    <text x="350" y="32" font-size="7.5" font-weight="bold" text-anchor="middle">4ème POURQUOI?</text>
    <text x="450" y="32" font-size="7.5" font-weight="bold" text-anchor="middle">5ème POURQUOI?</text>

    <!-- Branch Lines D4.1 -->
    <line x1="90" y1="165" x2="105" y2="60" stroke="#41719c" stroke-width="1"/>
    <line x1="90" y1="165" x2="105" y2="125" stroke="#41719c" stroke-width="1"/>
    <line x1="90" y1="165" x2="105" y2="210" stroke="#41719c" stroke-width="1"/>
    <line x1="90" y1="165" x2="105" y2="270" stroke="#41719c" stroke-width="1"/>

    <line x1="195" y1="60" x2="210" y2="60" stroke="#41719c" stroke-width="1"/>
    <line x1="295" y1="60" x2="310" y2="60" stroke="#41719c" stroke-width="1"/>
    <line x1="395" y1="60" x2="410" y2="60" stroke="#41719c" stroke-width="1"/>
    <line x1="495" y1="60" x2="510" y2="60" stroke="#41719c" stroke-width="1"/>

    <line x1="195" y1="125" x2="210" y2="125" stroke="#41719c" stroke-width="1"/>
    <line x1="295" y1="125" x2="310" y2="95" stroke="#41719c" stroke-width="1"/>
    <line x1="295" y1="125" x2="310" y2="135" stroke="#41719c" stroke-width="1"/>
    <line x1="295" y1="125" x2="310" y2="175" stroke="#41719c" stroke-width="1"/>

    <line x1="195" y1="210" x2="210" y2="210" stroke="#41719c" stroke-width="1"/>
    <line x1="195" y1="270" x2="210" y2="270" stroke="#41719c" stroke-width="1"/>

    <line x1="395" y1="95" x2="410" y2="95" stroke="#41719c" stroke-width="1"/>
    <line x1="395" y1="135" x2="410" y2="135" stroke="#41719c" stroke-width="1"/>
    <line x1="395" y1="175" x2="410" y2="175" stroke="#41719c" stroke-width="1"/>
    <line x1="295" y1="210" x2="410" y2="215" stroke="#41719c" stroke-width="1"/>
    <line x1="295" y1="270" x2="410" y2="275" stroke="#41719c" stroke-width="1"/>

    <!-- Nodes Col 1 -->
    <rect x="5" y="145" width="85" height="40" rx="3" fill="#5b9bd5"/>
    <text x="47" y="162" font-size="6.5" fill="#fff" text-anchor="middle">L'opérateur n'a pas</text>
    <text x="47" y="171" font-size="6.5" fill="#fff" text-anchor="middle">détecté le défaut</text>

    <!-- Nodes Col 2 -->
    <rect x="105" y="40" width="90" height="40" rx="3" fill="#5b9bd5"/>
    <text x="150" y="54" font-size="6" fill="#fff" text-anchor="middle">L'opérateur n'a pas</text>
    <text x="150" y="62" font-size="6" fill="#fff" text-anchor="middle">procédé par comp.</text>
    <text x="150" y="70" font-size="6" fill="#fff" text-anchor="middle">(2 pièces à la fois)</text>

    <rect x="105" y="105" width="90" height="40" rx="3" fill="#5b9bd5"/>
    <text x="150" y="122" font-size="6" fill="#fff" text-anchor="middle">L'opérateur n'a pas</text>
    <text x="150" y="130" font-size="6" fill="#fff" text-anchor="middle">utilisé la loupe</text>

    <rect x="105" y="190" width="90" height="40" rx="3" fill="#5b9bd5"/>
    <text x="150" y="207" font-size="6" fill="#fff" text-anchor="middle">Le défaut est</text>
    <text x="150" y="215" font-size="6" fill="#fff" text-anchor="middle">difficilement dét.</text>

    <rect x="105" y="250" width="90" height="40" rx="3" fill="#5b9bd5"/>
    <text x="150" y="264" font-size="6" fill="#fff" text-anchor="middle">Défauthèque différente</text>
    <text x="150" y="272" font-size="6" fill="#fff" text-anchor="middle">des photos de la récl.</text>
    <text x="150" y="280" font-size="6" fill="#fff" text-anchor="middle">Client final</text>

    <!-- Nodes Col 3 -->
    <rect x="205" y="40" width="90" height="40" rx="3" fill="#5b9bd5"/>
    <text x="250" y="58" font-size="6" fill="#fff" text-anchor="middle">Pas demandé dans</text>
    <text x="250" y="66" font-size="6" fill="#fff" text-anchor="middle">la gamme</text>

    <rect x="205" y="105" width="90" height="40" rx="3" fill="#5b9bd5"/>
    <text x="250" y="122" font-size="6" fill="#fff" text-anchor="middle">Pas demandé dans</text>
    <text x="250" y="130" font-size="6" fill="#fff" text-anchor="middle">la gamme</text>

    <rect x="205" y="190" width="90" height="40" rx="3" fill="#5b9bd5"/>
    <text x="250" y="204" font-size="6" fill="#fff" text-anchor="middle">Le défaut est trop</text>
    <text x="250" y="212" font-size="6" fill="#fff" text-anchor="middle">petit pour être dét.</text>
    <text x="250" y="220" font-size="6" fill="#fff" text-anchor="middle">visuellement</text>

    <rect x="205" y="250" width="90" height="40" rx="3" fill="#5b9bd5"/>
    <text x="250" y="264" font-size="6" fill="#fff" text-anchor="middle">Caractérisation du</text>
    <text x="250" y="272" font-size="6" fill="#fff" text-anchor="middle">défaut lors de la</text>
    <text x="250" y="280" font-size="6" fill="#fff" text-anchor="middle">demande prestation</text>

    <!-- Nodes Col 4 -->
    <rect x="305" y="40" width="90" height="40" rx="3" fill="#5b9bd5"/>
    <text x="350" y="54" font-size="6" fill="#fff" text-anchor="middle">Eviter les détériorations</text>
    <text x="350" y="62" font-size="6" fill="#fff" text-anchor="middle">des pièces entre</text>
    <text x="350" y="70" font-size="6" fill="#fff" text-anchor="middle">elles</text>

    <rect x="305" y="82" width="90" height="26" rx="3" fill="#5b9bd5"/>
    <text x="350" y="94" font-size="5.5" fill="#fff" text-anchor="middle">Jugement que le défaut</text>
    <text x="350" y="101" font-size="5.5" fill="#fff" text-anchor="middle">est dét. à l'oeil nu</text>

    <rect x="305" y="122" width="90" height="26" rx="3" fill="#5b9bd5"/>
    <text x="350" y="133" font-size="5.5" fill="#fff" text-anchor="middle">Le défaut est visible</text>
    <text x="350" y="140" font-size="5.5" fill="#fff" text-anchor="middle">par diff. de lumière</text>

    <rect x="305" y="162" width="90" height="26" rx="3" fill="#5b9bd5"/>
    <text x="350" y="173" font-size="5.5" fill="#fff" text-anchor="middle">De façon naturel il</text>
    <text x="350" y="180" font-size="5.5" fill="#fff" text-anchor="middle">aurait du l'utiliser</text>

    <rect x="305" y="202" width="90" height="26" rx="3" fill="#5b9bd5"/>
    <rect x="305" y="262" width="90" height="26" rx="3" fill="#5b9bd5"/>

    <!-- Nodes Col 5 -->
    <rect x="405" y="40" width="90" height="40" rx="3" fill="#5b9bd5"/>
    <text x="450" y="58" font-size="6" fill="#fff" text-anchor="middle">Principe général sur</text>
    <text x="450" y="66" font-size="6" fill="#fff" text-anchor="middle">le site</text>

    <rect x="405" y="82" width="90" height="26" rx="3" fill="#5b9bd5"/>
    <rect x="405" y="122" width="90" height="26" rx="3" fill="#5b9bd5"/>
    <rect x="405" y="162" width="90" height="26" rx="3" fill="#5b9bd5"/>
    <rect x="405" y="202" width="90" height="26" rx="3" fill="#5b9bd5"/>
    <rect x="405" y="262" width="90" height="26" rx="3" fill="#5b9bd5"/>

    <!-- Conclusion Boxes (Column Right) -->
    <rect x="430" y="5" width="105" height="24" rx="2" fill="#fce4d6" stroke="#f8cbad" stroke-width="0.5"/>
    <text x="482" y="14" font-size="5.5" font-weight="bold" fill="#000" text-anchor="middle">Avéré : on augmente le</text>
    <text x="482" y="22" font-size="5.5" font-weight="bold" fill="#000" text-anchor="middle">niveau de détection...</text>

    <rect x="430" y="83" width="105" height="24" rx="2" fill="#fce4d6" stroke="#f8cbad" stroke-width="0.5"/>
    <text x="482" y="93" font-size="5.5" font-weight="bold" fill="#000" text-anchor="middle">Avéré : la loupe améliore</text>
    <text x="482" y="101" font-size="5.5" font-weight="bold" fill="#000" text-anchor="middle">le niveau de détection</text>

    <rect x="430" y="123" width="105" height="24" rx="2" fill="#fce4d6" stroke="#f8cbad" stroke-width="0.5"/>
    <text x="482" y="133" font-size="5.5" font-weight="bold" fill="#000" text-anchor="middle">Non avéré : la méthode</text>
    <text x="482" y="141" font-size="5.5" font-weight="bold" fill="#000" text-anchor="middle">est peu fiable</text>

    <rect x="430" y="163" width="105" height="24" rx="2" fill="#fce4d6" stroke="#f8cbad" stroke-width="0.5"/>
    <text x="482" y="173" font-size="5.5" font-weight="bold" fill="#000" text-anchor="middle">Non avéré : l'utilisation</text>
    <text x="482" y="181" font-size="5.5" font-weight="bold" fill="#000" text-anchor="middle">doit être en gamme</text>

    <rect x="430" y="203" width="105" height="24" rx="2" fill="#fce4d6" stroke="#f8cbad" stroke-width="0.5"/>
    <text x="482" y="213" font-size="5.5" font-weight="bold" fill="#000" text-anchor="middle">Non avéré : écarté des</text>
    <text x="482" y="221" font-size="5.5" font-weight="bold" fill="#000" text-anchor="middle">pièces plus petites</text>

    <rect x="430" y="263" width="105" height="24" rx="2" fill="#fce4d6" stroke="#f8cbad" stroke-width="0.5"/>
    <text x="482" y="273" font-size="5.5" font-weight="bold" fill="#000" text-anchor="middle">Non avéré : défauts se</text>
    <text x="482" y="281" font-size="5.5" font-weight="bold" fill="#000" text-anchor="middle">ressemblent</text>
</svg>

<h3 style="margin:4pt 0 1pt 0; font-size:10pt;">D 4.2 - CAUSE TECHNIQUE</h3>

<svg width="540" height="220" viewBox="0 0 540 220" xmlns="http://www.w3.org/2000/svg">
    <!-- Yellow Cause Favorite Bar -->
    <rect x="160" y="2" width="220" height="14" fill="#ffff00" stroke="#000000" stroke-width="0.5"/>
    <text x="270" y="12" font-size="8" font-weight="bold" text-anchor="middle" fill="#000000">Cause favorite</text>
    
    <!-- Connection Lines D4.2 -->
    <line x1="95" y1="70" x2="115" y2="70" stroke="#41719c" stroke-width="1"/>
    <line x1="205" y1="70" x2="225" y2="70" stroke="#41719c" stroke-width="1"/>
    <line x1="315" y1="70" x2="335" y2="70" stroke="#41719c" stroke-width="1"/>
    <line x1="425" y1="70" x2="445" y2="70" stroke="#41719c" stroke-width="1"/>

    <line x1="95" y1="160" x2="115" y2="160" stroke="#41719c" stroke-width="1"/>
    <line x1="205" y1="160" x2="225" y2="160" stroke="#41719c" stroke-width="1"/>
    <line x1="315" y1="160" x2="335" y2="160" stroke="#41719c" stroke-width="1"/>
    <line x1="425" y1="160" x2="445" y2="160" stroke="#41719c" stroke-width="1"/>

    <!-- Row 1 D4.2 -->
    <rect x="5" y="50" width="90" height="40" rx="3" fill="#5b9bd5"/>
    <text x="50" y="64" font-size="6" fill="#fff" text-anchor="middle">Mix des pièces</text>
    <text x="50" y="72" font-size="6" fill="#fff" text-anchor="middle">(sécurisés et pas) chez</text>
    <text x="50" y="80" font-size="6" fill="#fff" text-anchor="middle">le Client final</text>

    <rect x="115" y="50" width="90" height="40" rx="3" fill="#5b9bd5"/>
    <text x="160" y="68" font-size="6" fill="#fff" text-anchor="middle">Pas d'identification</text>
    <text x="160" y="76" font-size="6" fill="#fff" text-anchor="middle">unitaire sur les pièces</text>

    <rect x="225" y="50" width="90" height="40" rx="3" fill="#5b9bd5"/>
    <text x="270" y="68" font-size="6" fill="#fff" text-anchor="middle">Identification sur l'unité</text>
    <text x="270" y="76" font-size="6" fill="#fff" text-anchor="middle">de Manutention</text>

    <rect x="335" y="50" width="90" height="40" rx="3" fill="#5b9bd5"/>
    <rect x="445" y="50" width="90" height="40" rx="3" fill="#5b9bd5"/>

    <rect x="445" y="50" width="90" height="40" rx="2" fill="#fce4d6" stroke="#f8cbad" stroke-width="0.5"/>
    <text x="490" y="64" font-size="5.5" font-weight="bold" fill="#000" text-anchor="middle">Avéré : un marquage</text>
    <text x="490" y="72" font-size="5.5" font-weight="bold" fill="#000" text-anchor="middle">unitaire aurait permis</text>
    <text x="490" y="80" font-size="5.5" font-weight="bold" fill="#000" text-anchor="middle">de distinguer pièces</text>

    <!-- Row 2 D4.2 -->
    <rect x="5" y="140" width="90" height="40" rx="3" fill="#5b9bd5"/>
    <text x="50" y="154" font-size="6" fill="#fff" text-anchor="middle">Client final réclame sur</text>
    <text x="50" y="162" font-size="6" fill="#fff" text-anchor="middle">des faces différentes</text>
    <text x="50" y="170" font-size="6" fill="#fff" text-anchor="middle">que prévu à la gamme</text>

    <rect x="115" y="140" width="90" height="40" rx="3" fill="#5b9bd5"/>
    <text x="160" y="158" font-size="6" fill="#fff" text-anchor="middle">La sécurisation concerne</text>
    <text x="160" y="166" font-size="6" fill="#fff" text-anchor="middle">les surfaces critiques</text>

    <rect x="225" y="140" width="90" height="40" rx="3" fill="#5b9bd5"/>
    <text x="270" y="154" font-size="6" fill="#fff" text-anchor="middle">Les défauts sur les</text>
    <text x="270" y="162" font-size="6" fill="#fff" text-anchor="middle">autres surfaces n'imp.</text>
    <text x="270" y="170" font-size="6" fill="#fff" text-anchor="middle">pas la fonctionnalité</text>

    <rect x="335" y="140" width="90" height="40" rx="3" fill="#5b9bd5"/>
    <rect x="445" y="140" width="90" height="40" rx="3" fill="#5b9bd5"/>

    <rect x="445" y="140" width="90" height="40" rx="2" fill="#fce4d6" stroke="#f8cbad" stroke-width="0.5"/>
    <text x="490" y="158" font-size="5.5" font-weight="bold" fill="#000" text-anchor="middle">Avéré : les deux</text>
    <text x="490" y="166" font-size="5.5" font-weight="bold" fill="#000" text-anchor="middle">surfaces sont ident.</text>
    <text x="490" y="174" font-size="5.5" font-weight="bold" fill="#000" text-anchor="middle">sur la gamme</text>
</svg>

<div style="font-size:7.5pt; font-style:italic; border:0.8pt solid #000; padding:4pt; margin-top:2pt;">
    A chaque étape du 5 pourquoi, vérifier avec les données que le lien de cause à effet soit effectif. Se demander pourquoi ? Autant de fois que nécessaire.
</div>

<div class="footer-note">D4.1 D4.2 &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; Doc.83 Rapport 8D du 17_03_2020</div>

</body>
</html>
"""

buf = BytesIO()
pisa.pisaDocument(BytesIO(html_page3.encode('utf-8')), buf)

doc = fitz.open(stream=buf.getvalue(), filetype='pdf')
print('SVG Full Page 3 render test page count:', len(doc))
with open('test_full_page3.pdf', 'wb') as f:
    f.write(buf.getvalue())
print('Saved test_full_page3.pdf successfully!')
