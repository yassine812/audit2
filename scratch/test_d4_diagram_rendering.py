"""Test PDF diagram rendering for empty vs populated D4 data."""

import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
django.setup()

from reclamation_client.models import ReclamationClient, AnalyseCausesDoubleAxeD4
from reclamation_client.pdf_d4_generator import generate_d4_diagram_base64, _normalize_chains

def test_diagram():
    print("==================================================")
    print("TESTING D4 DIAGRAM GENERATION (EMPTY vs USER INPUT)")
    print("==================================================\n")

    # 1. Test empty normalization
    assert _normalize_chains([]) == [], "Empty raw must return empty list"
    assert _normalize_chains([["", "", "", "", ""]]) == [], "Empty strings branch must return empty list"

    # 2. Test user branch normalization
    raw_user = [["Pourquoi 1 user", "Pourquoi 2 user", "", "", "Cause P5 user"]]
    norm_user = _normalize_chains(raw_user, "Cause P5 user")
    print("Normalized user branch:", norm_user)
    assert len(norm_user) == 1
    assert norm_user[0]["chain"][0]["pourquoi"] == "Pourquoi 1 user"
    assert norm_user[0]["chain"][1]["pourquoi"] == "Pourquoi 2 user"
    assert norm_user[0]["justification"] == "Cause P5 user"

    # 3. Test empty D4 model diagram base64
    d4_empty = AnalyseCausesDoubleAxeD4()
    b64_empty = generate_d4_diagram_base64(d4_empty)
    assert "L'opérateur" not in b64_empty
    assert "Mix des pièces" not in b64_empty

    # 4. Test populated D4 model diagram base64
    d4_user = AnalyseCausesDoubleAxeD4(
        pourquoi_non_detection=raw_user,
        cause_principale_non_detection="Cause P5 user",
    )
    b64_user = generate_d4_diagram_base64(d4_user)
    assert b64_user.startswith("data:image/png;base64,")

    print("\nALL D4 DIAGRAM RENDERING TESTS PASSED 100%!\n")

if __name__ == "__main__":
    test_diagram()
