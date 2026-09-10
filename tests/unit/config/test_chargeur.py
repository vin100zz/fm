from pathlib import Path

import pytest

from core.config.chargeur import charger_config
from core.config.erreurs import ConfigInvalide
from tests.unit.config.conftest import ecrire, lire


def test_charge_la_config_reelle(dossier_config: Path) -> None:
    config = charger_config(dossier_config)

    assert {c.pays for c in config.monde.competitions_simulees} == {
        "FRA", "ESP", "ITA", "ENG", "GER",
    }
    assert config.attributs.bornes.min == 1
    assert config.attributs.bornes.max == 100
    assert set(config.formations.formations) == {
        "4-4-2", "4-3-3", "4-2-3-1", "3-5-2", "5-3-2", "5-4-1",
    }
    assert config.moteur.densite.reference == 3.5
    assert config.benchmarks.execution.graine_defaut == 20260910


def test_config_est_immuable(dossier_config: Path) -> None:
    config = charger_config(dossier_config)

    with pytest.raises(Exception):
        config.moteur.transitions.k_prog = 0.1  # type: ignore[misc]


def test_echoue_si_fichier_manquant(tmp_path: Path) -> None:
    dossier_vide = tmp_path / "config_vide"
    dossier_vide.mkdir()

    with pytest.raises(ConfigInvalide) as exc:
        charger_config(dossier_vide)

    assert any("introuvable" in erreur for erreur in exc.value.erreurs)
    assert len(exc.value.erreurs) == 10  # one per missing file


def test_echoue_si_cle_inconnue(config_modifiable: Path) -> None:
    chemin = config_modifiable / "moteur_match.json"
    donnees = lire(chemin)
    donnees["transitions"]["cle_inconnue"] = 1.0
    ecrire(chemin, donnees)

    with pytest.raises(ConfigInvalide) as exc:
        charger_config(config_modifiable)

    assert any("transitions" in erreur for erreur in exc.value.erreurs)


def test_echoue_si_champ_manquant(config_modifiable: Path) -> None:
    chemin = config_modifiable / "moteur_match.json"
    donnees = lire(chemin)
    del donnees["transitions"]["k_prog"]
    ecrire(chemin, donnees)

    with pytest.raises(ConfigInvalide) as exc:
        charger_config(config_modifiable)

    assert any("k_prog" in erreur for erreur in exc.value.erreurs)


def test_echoue_si_composite_ne_somme_pas_a_un(config_modifiable: Path) -> None:
    chemin = config_modifiable / "attributs.json"
    donnees = lire(chemin)
    donnees["composites"]["tir"]["finition"] = 0.99
    ecrire(chemin, donnees)

    with pytest.raises(ConfigInvalide) as exc:
        charger_config(config_modifiable)

    assert any("composites.tir" in erreur for erreur in exc.value.erreurs)


def test_echoue_si_formation_incomplete(config_modifiable: Path) -> None:
    chemin = config_modifiable / "formations.json"
    donnees = lire(chemin)
    donnees["formations"]["4-4-2"].pop()
    ecrire(chemin, donnees)

    with pytest.raises(ConfigInvalide) as exc:
        charger_config(config_modifiable)

    assert any("4-4-2" in erreur and "10 postes" in erreur for erreur in exc.value.erreurs)


def test_echoue_si_poste_inconnu_dans_formation(config_modifiable: Path) -> None:
    chemin = config_modifiable / "formations.json"
    donnees = lire(chemin)
    donnees["formations"]["4-4-2"][0] = "LIBERO"
    ecrire(chemin, donnees)

    with pytest.raises(ConfigInvalide) as exc:
        charger_config(config_modifiable)

    assert any("LIBERO" in erreur for erreur in exc.value.erreurs)


def test_echoue_si_bornes_desordonnees(config_modifiable: Path) -> None:
    chemin = config_modifiable / "etats.json"
    donnees = lire(chemin)
    donnees["forme"]["min"] = 1.5
    ecrire(chemin, donnees)

    with pytest.raises(ConfigInvalide) as exc:
        charger_config(config_modifiable)

    assert any("etats.forme" in erreur for erreur in exc.value.erreurs)


def test_surcharge_remplace_uniquement_les_cles_donnees(
    dossier_config: Path, tmp_path: Path
) -> None:
    surcharge = tmp_path / "surcharge"
    surcharge.mkdir()
    ecrire(surcharge / "moteur_match.json", {"transitions": {"k_prog": 0.09}})

    config = charger_config(dossier_config, surcharge=surcharge)

    assert config.moteur.transitions.k_prog == 0.09
    assert config.moteur.transitions.k_occ == 0.11  # untouched
