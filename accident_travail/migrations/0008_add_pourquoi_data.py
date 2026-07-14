from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accident_travail', '0007_add_cause_racine'),
    ]

    operations = [
        migrations.AddField(
            model_name='analyse48h',
            name='pourquoi_data',
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text='{"code": {"section":..., "question":..., "pourquoi":[p1,p2,p3,p4,p5]}}',
                verbose_name='Données 5 Pourquoi',
            ),
        ),
    ]
