import json
from pathlib import Path

import pytest

from benchmarks.cibles import charger_effectifs_reference, resoudre_equipe


@pytest.fixture
def chemin_instantane(tmp_path: Path) -> Path:
    chemin = tmp_path / "match.json"
    with chemin.open("w", encoding="utf-8") as fichier:
        json.dump({"Paris SG": {"force_attaque": 98.7, "force_defense": 98.7}}, fichier)
    return chemin


def test_charge_l_instantane(chemin_instantane: Path) -> None:
    effectifs = charger_effectifs_reference(chemin_instantane)

    assert effectifs["Paris SG"].force_attaque == 98.7
    assert effectifs["Paris SG"].force_defense == 98.7


def test_resoudre_un_club_connu(chemin_instantane: Path) -> None:
    effectifs = charger_effectifs_reference(chemin_instantane)

    equipe = resoudre_equipe("Paris SG", effectifs)

    assert equipe.force_attaque == 98.7


def test_resoudre_niveau_synthetique_ne_touche_pas_a_l_instantane(chemin_instantane: Path) -> None:
    effectifs = charger_effectifs_reference(chemin_instantane)

    equipe = resoudre_equipe("__NIVEAU_70__", effectifs)

    assert equipe.force_attaque == 70.0
    assert equipe.force_defense == 70.0


def test_resoudre_club_inconnu_leve_key_error(chemin_instantane: Path) -> None:
    effectifs = charger_effectifs_reference(chemin_instantane)

    with pytest.raises(KeyError):
        resoudre_equipe("Club Fantome", effectifs)
