# Generated manually for safe non-destructive RisquePDP transition

from django.db import migrations, models
import django.db.models.deletion


def populate_risquepdp_from_risque(apps, schema_editor):
    Risque = apps.get_model('plan_prevention', 'Risque')
    RisquePDP = apps.get_model('plan_prevention', 'RisquePDP')

    code_map = {
        1: ("pieton", "Circulation et déplacement piéton dans l'enceinte de l'E.U.", "Circulation", 1),
        2: ("vehicules", "Circulation de véhicules et des engins de manutention", "Circulation", 2),
        3: ("manutention_manuelle", "Manutention manuelle de charge lourde ou difficilement accessible", "Manutention", 3),
        4: ("manutention_mecanisee", "Manutention mécanisée", "Manutention", 4),
        5: ("stockage_gerbage", "Stockage, gerbage", "Stockage", 5),
        6: ("mecanismes_mouvement", "Mécanismes en mouvement", "Machines & Équipements", 6),
        7: ("manipulation_pieces", "Manipulation de pièces et petits outillages", "Outillage", 7),
        8: ("outils_portatifs", "Utilisation d'outils portatifs et mobiles", "Outillage", 8),
        9: ("projections", "Risques de projections", "Environnement & Sécurité", 9),
        10: ("produits_chimiques", "Emploi et stockage de produits chimiques", "Chimique", 10),
        11: ("incendie_explosion", "Incendie / Explosion", "Incendie", 11),
        12: ("ambiance_physique", "Ambiance physique", "Environnement", 12),
        13: ("haute_tension", "Travaux à proximité d'installations électriques haute tension", "Électrique", 13),
        14: ("autres", "Autres risques", "Divers", 14),
    }

    # Transférer chacun des anciens Risque vers RisquePDP en conservant exactement l'ID
    for r in Risque.objects.all().order_by('id'):
        raw_code = ""
        if "(" in r.activite and ")" in r.activite:
            raw_code = r.activite.split("(")[-1].split(")")[0].strip()

        meta = code_map.get(r.id, (raw_code or f"risk_{r.id}", r.identification[:255], "Général", r.id))
        final_code = meta[0] or f"risk_{r.id}"
        final_titre = meta[1] or r.identification[:255]
        final_categorie = meta[2]
        final_ordre = meta[3]

        RisquePDP.objects.update_or_create(
            id=r.id,
            defaults={
                "code": final_code,
                "titre": final_titre,
                "description": r.identification,
                "categorie": final_categorie,
                "mesures_prevention_recommandees": r.moyens_maitrise or "",
                "est_actif": r.is_active,
                "ordre": final_ordre,
            }
        )

    # Si la table Risque avait moins de 14 risques, compléter avec le catalogue prédéfini
    for r_id, meta in code_map.items():
        if not RisquePDP.objects.filter(id=r_id).exists():
            RisquePDP.objects.create(
                id=r_id,
                code=meta[0],
                titre=meta[1],
                description=meta[1],
                categorie=meta[2],
                mesures_prevention_recommandees="",
                est_actif=True,
                ordre=meta[3],
            )


class Migration(migrations.Migration):

    dependencies = [
        ('plan_prevention', '0003_alter_planprevention_appareils_mis_disposition_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='RisquePDP',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=50, unique=True, verbose_name='Code')),
                ('titre', models.CharField(max_length=255, verbose_name='Titre / Risque')),
                ('description', models.TextField(blank=True, verbose_name='Description détaillée')),
                ('categorie', models.CharField(blank=True, max_length=100, verbose_name='Catégorie')),
                ('mesures_prevention_recommandees', models.TextField(blank=True, verbose_name='Mesures de prévention recommandées')),
                ('est_actif', models.BooleanField(default=True, verbose_name='Actif')),
                ('ordre', models.PositiveIntegerField(default=0, verbose_name="Ordre d'affichage")),
                ('cree_le', models.DateTimeField(auto_now_add=True, verbose_name='Créé le')),
                ('mis_a_jour_le', models.DateTimeField(auto_now=True, verbose_name='Mis à jour le')),
            ],
            options={
                'verbose_name': 'Risque PDP',
                'verbose_name_plural': 'Catalogue des Risques PDP',
                'ordering': ('ordre', 'code'),
            },
        ),
        migrations.RunPython(populate_risquepdp_from_risque, reverse_code=migrations.RunPython.noop),
        migrations.AlterField(
            model_name='planpreventionrisque',
            name='risque',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='pdp_associations',
                to='plan_prevention.risquepdp',
                verbose_name='Risque PDP',
            ),
        ),
    ]
