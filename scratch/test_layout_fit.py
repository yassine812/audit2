import os, sys, django, fitz
from io import BytesIO
from xhtml2pdf import pisa
from django.template.loader import render_to_string

sys.path.insert(0, '.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')
django.setup()

from reclamation_client.models import ReclamationClient

rec = ReclamationClient.objects.filter(reference='REC2608010').first() or ReclamationClient.objects.first()

html_content = '''
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>Rapport 8D — ''' + str(rec.reference) + '''</title>
    <style>
        @page {
            size: a4 portrait;
            margin: 6mm 8mm;
        }
        body {
            font-family: Helvetica, Arial, sans-serif;
            font-size: 8pt;
            line-height: 1.2;
            color: #000000;
            margin: 0;
            padding: 0;
        }

        table {
            width: 100%;
            table-layout: fixed;
            border-collapse: collapse;
            margin-bottom: 3pt;
        }
        th, td {
            border: 0.8pt solid #000000;
            padding: 2.5pt 3pt;
            font-size: 7.5pt;
            vertical-align: top;
            word-wrap: break-word;
        }
        
        .title-header-table td {
            border: 1pt solid #000000;
            padding: 4pt;
        }
        .main-title {
            text-align: center;
            font-size: 13pt;
            font-weight: bold;
        }

        .bg-blue {
            background-color: #d9e1f2;
            font-weight: bold;
        }
        .bg-yellow {
            background-color: #ffff00;
            font-weight: bold;
            text-align: center;
            padding: 2.5pt;
            border: 0.8pt solid #000000;
            margin-bottom: 3pt;
        }
        
        .section-header {
            background-color: #ffffff;
            font-weight: bold;
            font-size: 9.5pt;
            text-align: center;
            border: 1pt solid #000000;
            padding: 2.5pt;
            margin-top: 3pt;
            margin-bottom: 2pt;
        }
        .section-header-left {
            background-color: #ffffff;
            font-weight: bold;
            font-size: 9.5pt;
            text-align: left;
            border: 1pt solid #000000;
            padding: 2.5pt;
            margin-top: 3pt;
            margin-bottom: 2pt;
        }

        .text-center { text-align: center; }
        .text-right { text-align: right; }
        .font-bold { font-weight: bold; }

        .footer-note {
            font-size: 7pt;
            color: #333333;
            margin-top: 4pt;
        }

        /* 5 Whys Double Axis Tree (Page 3) */
        .why-table {
            width: 100%;
            table-layout: fixed;
            border-collapse: separate;
            border-spacing: 2pt;
            margin-bottom: 6pt;
        }
        .why-table th {
            border: none;
            background: #ffffff;
            font-size: 7.5pt;
            font-weight: bold;
            text-align: center;
            padding: 1.5pt;
        }
        .why-table td {
            border: none;
            padding: 0;
            vertical-align: top;
        }
        .why-card {
            background-color: #5b9bd5;
            color: #ffffff;
            border-radius: 2pt;
            padding: 4pt;
            font-size: 7pt;
            text-align: center;
            min-height: 38pt;
        }
        .why-card-result {
            background-color: #fce4d6;
            color: #000000;
            border: 0.8pt solid #f8cbad;
            border-radius: 2pt;
            padding: 4pt;
            font-size: 7pt;
            font-weight: bold;
            min-height: 38pt;
        }
    </style>
</head>
<body>

    <!-- PAGE 1 -->
    <table class="title-header-table">
        <tr>
            <td style="width:25%; text-align:center;">
                <strong style="font-size:12pt; color:#333;">AB Serve<br>Group</strong>
            </td>
            <td style="width:75%;" class="main-title">
                Rapport 8D
            </td>
        </tr>
    </table>

    <table style="margin-top:2pt;">
        <tr>
            <td style="width:22%;" class="bg-blue">Numéro de rapport AB Serve :</td>
            <td style="width:28%;" class="font-bold">''' + str(rec.reference) + '''</td>
            <td style="width:22%;" class="bg-blue">Numéro de réclamation :</td>
            <td style="width:28%;">''' + str(rec.numero_reclamation_client or '—') + '''</td>
        </tr>
        <tr>
            <td class="bg-blue">Date d'alerte client</td>
            <td>''' + str(rec.date_alerte_client.strftime('%d/%m/%Y') if rec.date_alerte_client else '—') + '''</td>
            <td class="bg-blue">Client</td>
            <td>''' + str(rec.client_nom) + '''</td>
        </tr>
        <tr>
            <td class="bg-blue">Date d'ouverture fiche</td>
            <td>''' + str(rec.date_ouverture.strftime('%d/%m/%Y') if rec.date_ouverture else '—') + '''</td>
            <td class="bg-blue">Contact client :</td>
            <td>''' + str(rec.contact_client or '—') + '''</td>
        </tr>
        <tr>
            <td class="bg-blue">Site concerné</td>
            <td colspan="3">''' + str(rec.site.nom if rec.site else rec.societe.nom) + '''</td>
        </tr>
        <tr>
            <td class="bg-blue">Description pièce :</td>
            <td colspan="3">''' + str(rec.description_piece or '—') + '''</td>
        </tr>
        <tr>
            <td class="bg-blue">Référence pièce :</td>
            <td colspan="3">''' + str(rec.reference_piece or '—') + '''</td>
        </tr>
        <tr>
            <td class="bg-blue">Est-ce un problème répétitif ?</td>
            <td colspan="3">
                OUI [''' + ('X' if rec.est_probleme_repetitif else '&nbsp;&nbsp;') + '''] &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
                NON [''' + ('&nbsp;&nbsp;' if rec.est_probleme_repetitif else 'X') + ''']
            </td>
        </tr>
        <tr>
            <td colspan="2" style="border:none;"></td>
            <td class="bg-blue">Date de mise à jour :</td>
            <td>''' + str(rec.date_mise_a_jour.strftime('%d/%m/%Y') if rec.date_mise_a_jour else '—') + '''</td>
        </tr>
    </table>

    <div class="section-header">D1 - Groupe 8D</div>
    <table>
        <tr>
            <td style="width:18%;" class="bg-blue">Participants :</td>
            <td style="width:32%;">FISCHER Fabien, MARTZ Fabien, CHILLIARD Sébastien</td>
            <td style="width:18%;" class="bg-blue">Fonction :</td>
            <td style="width:32%;">Responsable de site RHEINMETALL, Directeur QSE Group</td>
        </tr>
    </table>

    <div class="section-header">D2 - Description du problème</div>
    <div style="border:0.8pt solid #000; padding:3pt; margin-bottom:2pt; font-size:7.5pt;">
        <strong>Description du problème par le client :</strong><br>
        Présence de chocs, de bavures, de manque matière sur les pièces livrées.
    </div>

    <table>
        <thead>
            <tr class="bg-blue">
                <th style="width:50%;">Le problème est :</th>
                <th style="width:50%;">Le problème n'est pas :</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td><strong style="color:#0056b3;">QUOI ?</strong> L'objet ? / La défaillance?<br>Présence de chocs, de bavures, de manque matière</td>
                <td>Erreur de référence / mélange de pièces NC avec les conformes / pièce cassée</td>
            </tr>
            <tr>
                <td><strong style="color:#0056b3;">QUI</strong> rencontre le problème ?<br>Client final Renault CACIA</td>
                <td>RHEINMETALL / L'utilisateur du véhicule final</td>
            </tr>
            <tr>
                <td><strong style="color:#0056b3;">OÙ ?</strong> secteur, site<br>Sur ligne d'assemblage de la pompe</td>
                <td>En stock chez RHEINMETALL</td>
            </tr>
            <tr>
                <td><strong style="color:#0056b3;">QUAND</strong> a-t-on détecté le problème, par qui ?<br>Lors de l'assemblage de la pompe / par l'opérateur sur ligne</td>
                <td>En contrôle réception chez Renault</td>
            </tr>
            <tr>
                <td><strong style="color:#0056b3;">COMMENT</strong> se manifeste le problème?<br>Blocage de la pompe</td>
                <td>L'impossibilité de montage / fuite lors de l'utilisation de la pompe / casse de la pompe</td>
            </tr>
            <tr>
                <td><strong style="color:#0056b3;">COMBIEN ?</strong> Combien de pièces<br>5</td>
                <td>Toutes les pièces</td>
            </tr>
            <tr>
                <td><strong style="color:#0056b3;">POURQUOI</strong> est-ce un problème ?<br>La pompe ne fonctionne pas</td>
                <td>Un fonctionnement partiel de la pompe / un défaut qui s'accentue lors de l'utilisation jusqu'au blocage</td>
            </tr>
        </tbody>
    </table>

    <div class="section-header">D3 : Mesures conservatoires où de sécurisation</div>
    <table>
        <thead>
            <tr class="bg-blue">
                <th style="width:38%;">Actions</th>
                <th style="width:7%;" class="text-center">Oui</th>
                <th style="width:7%;" class="text-center">Non</th>
                <th style="width:24%;" class="text-center">Quantité triée</th>
                <th style="width:24%;" class="text-center">Quantité NOK</th>
            </tr>
        </thead>
        <tbody>
            <tr><td>Tri stock interne</td><td class="text-center">☐</td><td class="text-center">☑</td><td class="text-center"></td><td class="text-center"></td></tr>
            <tr><td>Tri stock externe</td><td class="text-center">☑</td><td class="text-center">☐</td><td class="text-center">36720</td><td class="text-center"></td></tr>
            <tr><td>Repère unitaire</td><td class="text-center">☐</td><td class="text-center">☑</td><td class="text-center"></td><td class="text-center"></td></tr>
        </tbody>
    </table>
    <div style="margin-top:1pt;"><strong>Autre action :</strong></div>
    <div style="margin-top:1pt;"><strong>Commentaires :</strong> Pas la possibilité de trier les pièces en interne car toutes les pièces ont été envoyées au Client</div>

    <div class="footer-note">8D 1 à 3 &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; Doc.83 Rapport 8D du 17_03_2020</div>

    <pdf:nextpage/>

    <!-- PAGE 2 -->
    <div class="section-header-left" style="font-size:11pt; text-align:center; margin-top:0;">8D - D4 à D8</div>
    
    <div class="section-header-left">D4 - Analyse des causes</div>
    <div style="border:0.8pt solid #000; padding:3pt; margin-bottom:3pt; font-size:7.5pt;">
        <strong>D4.1 Cause principale de non détection :</strong> Contrôle unitaire au lieu de 2 par 2. Loupe pas utilisée pour faire le contrôle.<br><br>
        <strong>D4.2 Cause principale technique - Non-conformité :</strong> Pas d'identification des cartons unitairement. Pas de relevé des numéros dans My Report.
    </div>

    <div style="margin-bottom:4pt; padding:1pt;">
        <span style="color:red;">•</span> <strong>La réclamation est-elle recevable ?</strong> &nbsp;&nbsp;&nbsp;&nbsp;
        [ &nbsp;&nbsp; ] OUI &nbsp;&nbsp;&nbsp;&nbsp;
        [ X ] NON<br>
        <span style="color:red;">•</span> <strong>Motif de la décision :</strong> Les pièces que nous avons arrêtées présentent des défauts plus petits que ceux réclamés par le Client final.
    </div>

    <div class="section-header-left">D5 - Actions tests planifiées</div>
    <table>
        <thead>
            <tr class="bg-blue">
                <th style="width:54%;">Actions test</th>
                <th style="width:23%;">Pilote - Délai</th>
                <th style="width:23%;">Conclusion</th>
            </tr>
        </thead>
        <tbody>
            <tr><td>1. Test unitaire d'assemblage</td><td>FISCHER Fabien - 15/03/2026</td><td>Concluant</td></tr>
            <tr><td>2. Contrôle sous loupe</td><td>MARTZ Fabien - 18/03/2026</td><td>Concluant</td></tr>
            <tr><td>3. Test d'étanchéité</td><td>CHILLIARD Sébastien - 20/03/2026</td><td>En cours</td></tr>
            <tr><td>4. Validation finale</td><td>Directeur QSE - 25/03/2026</td><td>En attente</td></tr>
        </tbody>
    </table>

    <div class="section-header-left">D6 - Mise place des actions correctives</div>
    <table>
        <thead>
            <tr class="bg-blue">
                <th style="width:50%;">Action</th>
                <th style="width:18%;">Pilote</th>
                <th style="width:16%;">Délai</th>
                <th style="width:16%;">Date de réalisation</th>
            </tr>
        </thead>
        <tbody>
            <tr><td><strong>Action 1 :</strong> Marquage unitaire des pièces</td><td>FISCHER Fabien</td><td>15/03/2026</td><td>14/03/2026</td></tr>
            <tr><td><strong>Action 2 :</strong> Mise à jour gamme de contrôle</td><td>MARTZ Fabien</td><td>18/03/2026</td><td>17/03/2026</td></tr>
            <tr><td><strong>Action 3 :</strong> Audit de poste Doc 37</td><td>CHILLIARD Sébastien</td><td>22/03/2026</td><td>—</td></tr>
            <tr><td><strong>Action 4 :</strong> Formation opérateurs du site</td><td>Directeur QSE</td><td>25/03/2026</td><td>—</td></tr>
        </tbody>
    </table>
    <div style="font-size:7pt; margin-top:2pt; margin-bottom:4pt;">
        <strong>Validation des actions permanentes - Contrôle d’efficacité :</strong> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; Doc 37 audit de poste
    </div>

    <div class="section-header-left">D7 - Capitaliser</div>
    <table>
        <thead>
            <tr class="bg-blue">
                <th style="width:50%;">Document SMQS</th>
                <th style="width:8%;" class="text-center">Oui</th>
                <th style="width:8%;" class="text-center">Non</th>
                <th style="width:17%;">Pilote</th>
                <th style="width:17%;">Délai</th>
            </tr>
        </thead>
        <tbody>
            <tr><td>Doc.01 Instruction de travail</td><td class="text-center">☑</td><td class="text-center">☐</td><td colspan="2">FISCHER Fabien - 15/03/2026</td></tr>
            <tr><td>Doc 5-24 Tableau de compétence</td><td class="text-center">☑</td><td class="text-center">☐</td><td colspan="2">MARTZ Fabien - 18/03/2026</td></tr>
            <tr><td>Doc.21 formation Nouvel arrivant</td><td class="text-center">☑</td><td class="text-center">☐</td><td colspan="2">QSE - 20/03/2026</td></tr>
            <tr><td>Doc 34 Habilitation idividuelle</td><td class="text-center">☐</td><td class="text-center">☑</td><td colspan="2"></td></tr>
            <tr><td>Doc 38 Habilitation au poste</td><td class="text-center">☑</td><td class="text-center">☐</td><td colspan="2">Responsable site</td></tr>
            <tr><td>Doc 12 Gamme de travail (Précisez : Gamme G05-B)</td><td class="text-center">☑</td><td class="text-center">☐</td><td colspan="2">Directeur QSE</td></tr>
            <tr><td>Doc 37 audit de poste</td><td class="text-center">☑</td><td class="text-center">☐</td><td colspan="2">Pilote Audit</td></tr>
            <tr><td>Doc 50 OK démarrage</td><td class="text-center">☑</td><td class="text-center">☐</td><td colspan="2">Chef d'équipe</td></tr>
        </tbody>
    </table>

    <div class="section-header-left">D8 - Fermeture du 8 D</div>
    <div style="border:0.8pt solid #000; padding:3pt;">
        Féliciter l'équipe : OUI<br>
        Date : 25/03/2026
    </div>

    <div class="footer-note">8D 4 à 8 &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; Doc.83 Rapport 8D du 17_03_2020</div>

    <pdf:nextpage/>

    <!-- PAGE 3 -->
    <div class="section-header-left" style="font-size:11pt; text-align:center; margin-top:0;">D 4.1 à D 4.2</div>
    
    <h3 style="margin:3pt 0 1pt 0; font-size:10pt;">D 4.1 - NON DETECTION</h3>
    <div class="bg-yellow">Cause favorite</div>
    
    <table class="why-table">
        <thead>
            <tr>
                <th style="width:20%;">1er POURQUOI?</th>
                <th style="width:20%;">2ème POURQUOI?</th>
                <th style="width:20%;">3ème POURQUOI?</th>
                <th style="width:20%;">4ème POURQUOI?</th>
                <th style="width:20%;">5ème POURQUOI?</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td><div class="why-card">L'opérateur n'a pas détecté le défaut</div></td>
                <td><div class="why-card">L'opérateur n'a pas utilisé la loupe</div></td>
                <td><div class="why-card">Pas demandé dans la gamme</div></td>
                <td><div class="why-card">Détectable à l'oeil nu selon opérateur</div></td>
                <td><div class="why-card-result">Avéré : la loupe améliore le niveau de détection</div></td>
            </tr>
        </tbody>
    </table>

    <h3 style="margin:5pt 0 1pt 0; font-size:10pt;">D 4.2 - CAUSE TECHNIQUE</h3>
    <div class="bg-yellow">Cause favorite</div>

    <table class="why-table">
        <thead>
            <tr>
                <th style="width:20%;">1er POURQUOI?</th>
                <th style="width:20%;">2ème POURQUOI?</th>
                <th style="width:20%;">3ème POURQUOI?</th>
                <th style="width:20%;">4ème POURQUOI?</th>
                <th style="width:20%;">5ème POURQUOI?</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td><div class="why-card">Mix des pièces chez le client</div></td>
                <td><div class="why-card">Pas d'identification unitaire des cartons</div></td>
                <td><div class="why-card">Manutention vrac sans repère</div></td>
                <td><div class="why-card">Absence de procédure d'étiquetage</div></td>
                <td><div class="why-card-result">Avéré : un marquage unitaire aurait permis d'éviter le mix</div></td>
            </tr>
        </tbody>
    </table>

    <div style="font-size:7.5pt; font-style:italic; border:0.8pt solid #000; padding:4pt; margin-top:10pt;">
        A chaque étape du 5 pourquoi, vérifier avec les données que le lien de cause à effet soit effectif. Se demander pourquoi ? Autant de fois que nécessaire.
    </div>

    <div class="footer-note" style="margin-top:12pt;">D4.1 D4.2 &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; Doc.83 Rapport 8D du 17_03_2020</div>

</body>
</html>
'''

result = BytesIO()
pdf = pisa.pisaDocument(BytesIO(html_content.encode('utf-8')), result)

assert not pdf.err, 'pisa error!'

pdf_bytes = result.getvalue()
doc = fitz.open(stream=pdf_bytes, filetype='pdf')

print('=== LAYOUT FIT TEST RESULT ===')
print(f'Total Page Count: {len(doc)}')

for i, page in enumerate(doc):
    print(f'--- PAGE {i+1} ---')
    lines = [line.strip() for line in page.get_text().split('\n') if line.strip()]
    print('Line count:', len(lines))
    print('First line:', lines[0] if lines else '')
    print('Last line:', lines[-1] if lines else '')

with open('REC2608010_Strict_3Pages.pdf', 'wb') as f:
    f.write(pdf_bytes)

print('\nSUCCESS! Saved strictly to REC2608010_Strict_3Pages.pdf!')
