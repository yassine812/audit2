"""Test HTML rendering of DateInput widget with and without format='%Y-%m-%d'."""

import os
import sys
import datetime
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
django.setup()

from django import forms
from reclamation_client.forms import DateInput, ReclamationHeaderForm
from reclamation_client.models import ReclamationClient

def test_widget():
    rec = ReclamationClient(
        date_alerte_client=datetime.date(2026, 9, 1),
        date_ouverture=datetime.date(2026, 9, 1),
        date_incident=datetime.date(2026, 8, 31),
        date_envoi_d1_d3=datetime.date(2026, 9, 2),
    )
    form = ReclamationHeaderForm(instance=rec)
    print("--- Date Alerte Client Rendered HTML ---")
    print(form["date_alerte_client"].as_widget())
    print("\n--- Date Ouverture Rendered HTML ---")
    print(form["date_ouverture"].as_widget())

if __name__ == "__main__":
    test_widget()
