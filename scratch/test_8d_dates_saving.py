"""Test saving and rendering of 8D dates."""

import os
import sys
import datetime
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
django.setup()

from accounts.models import Societe
from reclamation_client.models import ReclamationClient
from reclamation_client.forms import ReclamationHeaderForm, ClotureRecevabiliteD8Form

def test_dates_saving():
    print("==================================================")
    print("TESTING 8D DATE FIELDS PERSISTENCE & RENDERING")
    print("==================================================\n")

    soc = Societe.objects.first() or Societe.objects.create(nom="Societe Dates Test")
    rec = ReclamationClient.objects.create(
        reference="REC8D-DATES-TEST",
        type_signalement="R",
        mode_traitement="8D",
        client_nom="Client Dates Test",
        societe=soc,
        quantite_impactee=10,
    )

    # 1. Post date values to ReclamationHeaderForm
    post_data = {
        "numero_reclamation_client": "REC-DATES-01",
        "type_signalement": "R",
        "statut": "brouillon",
        "societe": str(soc.pk),
        "client_nom": "Client Dates Test",
        "quantite_impactee": "10",
        "date_alerte_client": "2026-09-01",
        "date_ouverture": "2026-09-01",
        "date_incident": "2026-08-31",
        "date_envoi_d1_d3": "2026-09-02",
    }

    form = ReclamationHeaderForm(post_data, instance=rec)
    assert form.is_valid(), f"Header form invalid: {form.errors}"
    form.save()

    # 2. Reload object from DB
    rec_reloaded = ReclamationClient.objects.get(pk=rec.pk)
    print(f"Saved DB date_alerte_client: {rec_reloaded.date_alerte_client}")
    print(f"Saved DB date_ouverture: {rec_reloaded.date_ouverture}")
    print(f"Saved DB date_incident: {rec_reloaded.date_incident}")
    print(f"Saved DB date_envoi_d1_d3: {rec_reloaded.date_envoi_d1_d3}")

    assert rec_reloaded.date_alerte_client == datetime.date(2026, 9, 1)
    assert rec_reloaded.date_ouverture == datetime.date(2026, 9, 1)
    assert rec_reloaded.date_incident == datetime.date(2026, 8, 31)
    assert rec_reloaded.date_envoi_d1_d3 == datetime.date(2026, 9, 2)

    # 3. Render bound form for reloaded object
    form_bound = ReclamationHeaderForm(instance=rec_reloaded)
    print("\n--- Rendered HTML for HTML5 date inputs ---")
    print(f"date_alerte_client: {form_bound['date_alerte_client'].as_widget()}")
    print(f"date_ouverture:     {form_bound['date_ouverture'].as_widget()}")
    print(f"date_incident:      {form_bound['date_incident'].as_widget()}")
    print(f"date_envoi_d1_d3:   {form_bound['date_envoi_d1_d3'].as_widget()}")

    assert 'value="2026-09-01"' in form_bound['date_alerte_client'].as_widget()
    assert 'value="2026-09-01"' in form_bound['date_ouverture'].as_widget()
    assert 'value="2026-08-31"' in form_bound['date_incident'].as_widget()
    assert 'value="2026-09-02"' in form_bound['date_envoi_d1_d3'].as_widget()

    print("\nALL 8D DATE PERSISTENCE & RENDERING TESTS PASSED 100%!\n")

if __name__ == "__main__":
    test_dates_saving()
