import os, sys, django, fitz
from io import BytesIO
from xhtml2pdf import pisa

sys.path.insert(0, '.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')
django.setup()

html_table_test = """
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
.header-box {
    border: 1pt solid #000;
    font-weight: bold;
    font-size: 11pt;
    text-align: center;
    padding: 3pt;
    margin-bottom: 4pt;
}
.section-title {
    font-size: 10pt;
    font-weight: bold;
    margin: 4pt 0 2pt 0;
}
.bg-yellow-bar {
    background-color: #ffff00;
    border: 0.8pt solid #000;
    font-weight: bold;
    text-align: center;
    padding: 2pt;
    font-size: 8pt;
    margin-bottom: 4pt;
}
.why-grid-table {
    width: 100%;
    border-collapse: separate;
    border-spacing: 2pt;
    margin-bottom: 4pt;
}
.why-grid-table th {
    font-size: 7.5pt;
    font-weight: bold;
    text-align: center;
    border: none;
    padding: 2pt;
}
.why-grid-table td {
    border: none;
    padding: 0;
    vertical-align: middle;
}
.blue-box {
    background-color: #5b9bd5;
    color: #ffffff;
    font-size: 6.5pt;
    text-align: center;
    padding: 4pt 3pt;
    border-radius: 3pt;
}
.conclusion-box {
    background-color: #fce4d6;
    color: #000000;
    border: 0.8pt solid #f8cbad;
    font-size: 6.5pt;
    font-weight: bold;
    text-align: center;
    padding: 4pt 3pt;
    border-radius: 3pt;
}
.arrow-cell {
    text-align: center;
    font-size: 9pt;
    color: #41719c;
    font-weight: bold;
}
.instruction-box {
    font-size: 7.5pt;
    font-style: italic;
    border: 0.8pt solid #000;
    padding: 4pt;
    margin-top: 4pt;
}
.footer-note {
    font-size: 7pt;
    color: #333;
    margin-top: 6pt;
}
</style>
</head>
<body>

<div class="header-box">D 4.1 à D 4.2</div>

<div class="section-title">D 4.1 - NON DETECTION</div>

<div class="bg-yellow-bar">Cause favorite</div>

<table width="100%" class="why-grid-table">
    <colgroup>
        <col width="90pt">
        <col width="12pt">
        <col width="90pt">
        <col width="12pt">
        <col width="90pt">
        <col width="12pt">
        <col width="90pt">
        <col width="12pt">
        <col width="132pt">
    </colgroup>
    <thead>
        <tr>
            <th width="90pt">1er POURQUOI?</th>
            <th></th>
            <th width="90pt">2ème POURQUOI?</th>
            <th></th>
            <th width="90pt">3ème POURQUOI?</th>
            <th></th>
            <th width="90pt">4ème POURQUOI?</th>
            <th></th>
            <th width="132pt">5ème POURQUOI / RESULTAT</th>
        </tr>
    </thead>
    <tbody>
        <!-- Branch 1 -->
        <tr>
            <td width="90pt" rowspan="4"><div class="blue-box">L'opérateur n'a pas<br>détecté le défaut</div></td>
            <td class="arrow-cell">&rarr;</td>
            <td width="90pt"><div class="blue-box">L'opérateur n'a pas<br>procédé par comp.<br>(2 pièces à la fois)</div></td>
            <td class="arrow-cell">&rarr;</td>
            <td width="90pt"><div class="blue-box">Pas demandé dans<br>la gamme</div></td>
            <td class="arrow-cell">&rarr;</td>
            <td width="90pt"><div class="blue-box">Eviter les détériorations<br>des pièces entre elles</div></td>
            <td class="arrow-cell">&rarr;</td>
            <td width="132pt"><div class="conclusion-box">Avéré : on augmente le niveau<br>de détection (2 pièces à la fois)</div></td>
        </tr>
        <!-- Branch 2 -->
        <tr>
            <td class="arrow-cell">&rarr;</td>
            <td width="90pt" rowspan="2"><div class="blue-box">L'opérateur n'a pas<br>utilisé la loupe</div></td>
            <td class="arrow-cell">&rarr;</td>
            <td width="90pt" rowspan="2"><div class="blue-box">Pas demandé dans<br>la gamme</div></td>
            <td class="arrow-cell">&rarr;</td>
            <td width="90pt"><div class="blue-box">Jugement que le défaut<br>est dét. à l'oeil nu</div></td>
            <td class="arrow-cell">&rarr;</td>
            <td width="132pt"><div class="conclusion-box">Avéré : la loupe améliore<br>le niveau de détection</div></td>
        </tr>
        <tr>
            <td class="arrow-cell"></td>
            <td class="arrow-cell">&rarr;</td>
            <td width="90pt"><div class="blue-box">Le défaut est visible par<br>diff. de lumière</div></td>
            <td class="arrow-cell">&rarr;</td>
            <td width="132pt"><div class="conclusion-box">Non avéré : la méthode<br>est peu fiable</div></td>
        </tr>
        <!-- Branch 3 -->
        <tr>
            <td class="arrow-cell">&rarr;</td>
            <td width="90pt"><div class="blue-box">Le défaut est<br>difficilement dét.</div></td>
            <td class="arrow-cell">&rarr;</td>
            <td width="90pt"><div class="blue-box">Le défaut est trop petit<br>pour être dét. visuellement</div></td>
            <td class="arrow-cell">&rarr;</td>
            <td width="90pt"><div class="blue-box">Caractérisation du défaut<br>lors de la prestation</div></td>
            <td class="arrow-cell">&rarr;</td>
            <td width="132pt"><div class="conclusion-box">Non avéré : l'opérateur a écarté<br>des pièces plus petites</div></td>
        </tr>
    </tbody>
</table>

<div class="section-title" style="margin-top:6pt;">D 4.2 - CAUSE TECHNIQUE</div>

<div class="bg-yellow-bar">Cause favorite</div>

<table width="100%" class="why-grid-table">
    <colgroup>
        <col width="90pt">
        <col width="12pt">
        <col width="90pt">
        <col width="12pt">
        <col width="90pt">
        <col width="12pt">
        <col width="90pt">
        <col width="12pt">
        <col width="132pt">
    </colgroup>
    <thead>
        <tr>
            <th width="90pt">1er POURQUOI?</th>
            <th></th>
            <th width="90pt">2ème POURQUOI?</th>
            <th></th>
            <th width="90pt">3ème POURQUOI?</th>
            <th></th>
            <th width="90pt">4ème POURQUOI?</th>
            <th></th>
            <th width="132pt">5ème POURQUOI / RESULTAT</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td width="90pt"><div class="blue-box">Mix des pièces chez<br>le Client final</div></td>
            <td class="arrow-cell">&rarr;</td>
            <td width="90pt"><div class="blue-box">Pas d'identification<br>unitaire sur pièces</div></td>
            <td class="arrow-cell">&rarr;</td>
            <td width="90pt"><div class="blue-box">Identification sur<br>unité Manutention</div></td>
            <td class="arrow-cell">&rarr;</td>
            <td width="90pt"><div class="blue-box">Pas de repère<br>visuel au poste</div></td>
            <td class="arrow-cell">&rarr;</td>
            <td width="132pt"><div class="conclusion-box">Avéré : un marquage unitaire<br>aurait permis de distinguer</div></td>
        </tr>
        <tr>
            <td width="90pt"><div class="blue-box">Client final réclame<br>sur faces diff.</div></td>
            <td class="arrow-cell">&rarr;</td>
            <td width="90pt"><div class="blue-box">Sécurisation concerne<br>surfaces critiques</div></td>
            <td class="arrow-cell">&rarr;</td>
            <td width="90pt"><div class="blue-box">Défauts sur surfaces<br>n'impactent pas func.</div></td>
            <td class="arrow-cell">&rarr;</td>
            <td width="90pt"><div class="blue-box">Spécification gamme<br>incomplète</div></td>
            <td class="arrow-cell">&rarr;</td>
            <td width="132pt"><div class="conclusion-box">Avéré : les deux surfaces sont<br>identifiées sur la gamme</div></td>
        </tr>
    </tbody>
</table>

<div class="instruction-box">
    A chaque étape du 5 pourquoi, vérifier avec les données que le lien de cause à effet soit effectif. Se demander pourquoi ? Autant de fois que nécessaire.
</div>

<div class="footer-note">
    D4.1 D4.2 &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; Doc.83 Rapport 8D du 17_03_2020
</div>

</body>
</html>
"""

buf = BytesIO()
pisa.pisaDocument(BytesIO(html_table_test.encode('utf-8')), buf)

doc = fitz.open(stream=buf.getvalue(), filetype='pdf')
print('HTML Table D4 Page render count:', len(doc))
with open('test_table_d4.pdf', 'wb') as f:
    f.write(buf.getvalue())
print('Saved test_table_d4.pdf successfully!')
