import json
from pathlib import Path
from random import Random

from core.config import Config
from benchmarks.suites.stats_match import executer

NOMS_REELS = ("Paris SG", "Toulouse FC", "Man City", "Burnley", "R. Madrid", "Barcelone")


def ecrire_instantane(chemin: Path, forces: dict[str, float]) -> None:
    donnees = {nom: {"force_attaque": force, "force_defense": force} for nom, force in forces.items()}
    with chemin.open("w", encoding="utf-8") as fichier:
        json.dump(donnees, fichier)


def test_deux_cibles_mesurees_le_reste_non_mesurable(cfg: Config, tmp_path: Path) -> None:
    chemin = tmp_path / "match.json"
    ecrire_instantane(chemin, {nom: 60.0 for nom in NOMS_REELS})

    resultats = executer(cfg, Random(1), iterations=100, chemin_effectifs=chemin)

    mesures = {r.nom: r for r in resultats if r.statut != "non_mesurable"}
    assert set(mesures) == {"buts_par_equipe", "avantage_domicile_buts"}
    assert all(r.valeur is not None for r in mesures.values())

    non_mesurables = [r for r in resultats if r.statut == "non_mesurable"]
    assert len(non_mesurables) == 8
    assert all(r.valeur is None for r in non_mesurables)


def test_avantage_domicile_positif_a_forces_egales(cfg: Config, tmp_path: Path) -> None:
    chemin = tmp_path / "match.json"
    ecrire_instantane(chemin, {nom: 60.0 for nom in NOMS_REELS})

    resultats = executer(cfg, Random(2), iterations=300, chemin_effectifs=chemin)

    avantage = next(r for r in resultats if r.nom == "avantage_domicile_buts")
    assert avantage.valeur > 0
