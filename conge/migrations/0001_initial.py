"""Migration initiale du module conge."""

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("accounts", "0003_remove_is_admin_field"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="DemandeConge",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nom",    models.CharField(max_length=100, verbose_name="Nom")),
                ("prenom", models.CharField(max_length=100, verbose_name="Prénom")),
                ("date_debut",   models.DateField(verbose_name="S'absentera du")),
                ("date_fin",     models.DateField(verbose_name="Au")),
                ("date_reprise", models.DateField(verbose_name="Date de la reprise")),
                ("nombre_jours", models.PositiveSmallIntegerField(verbose_name="Nombre de jour(s)")),
                ("type_conge", models.CharField(
                    choices=[
                        ("conges_payes",       "Congés payés"),
                        ("banque_heures",      "Banque d'heures"),
                        ("conges_anciennete",  "Congés ancienneté"),
                        ("evenement_familial", "Événement familial"),
                        ("conges_sans_solde",  "Congés sans solde"),
                    ],
                    max_length=30,
                    verbose_name="Imputation sur",
                )),
                ("evenement_familial_precision", models.CharField(
                    blank=True, max_length=200,
                    verbose_name="Préciser lequel (événement familial)",
                )),
                ("statut", models.CharField(
                    choices=[
                        ("en_attente", "En attente"),
                        ("valide",     "Validé"),
                        ("refuse",     "Refusé"),
                    ],
                    default="en_attente",
                    max_length=20,
                    verbose_name="Statut",
                )),
                ("date_demande",  models.DateField(auto_now_add=True, verbose_name="Date de la demande")),
                ("date_validation", models.DateField(blank=True, null=True, verbose_name="Date de validation")),
                ("commentaire_refus",     models.TextField(blank=True, verbose_name="Commentaire de refus")),
                ("signature_demandeur",   models.TextField(blank=True, verbose_name="Signature du demandeur")),
                ("signature_responsable", models.TextField(blank=True, verbose_name="Signature du responsable")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("demandeur", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="demandes_conge",
                    to=settings.AUTH_USER_MODEL,
                    verbose_name="Demandeur",
                )),
                ("section", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="demandes_conge",
                    to="accounts.section",
                    verbose_name="Section",
                )),
                ("validateur", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="conges_traites",
                    to=settings.AUTH_USER_MODEL,
                    verbose_name="Validateur",
                )),
            ],
            options={
                "verbose_name": "Demande de congé",
                "verbose_name_plural": "Demandes de congé",
                "ordering": ["-date_demande", "-created_at"],
            },
        ),
    ]
