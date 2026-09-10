from random import Random

from core.config import Config
from benchmarks.suites.performance import executer


def test_chargement_donnees_est_mesure_et_dans_la_cible(cfg: Config) -> None:
    resultats = executer(cfg, Random(1), iterations=None)

    chargement = next(r for r in resultats if r.nom == "secondes_chargement_donnees")
    assert chargement.statut == "ok"
    assert chargement.valeur is not None
    assert chargement.valeur < cfg.benchmarks.performance.secondes_chargement_donnees


def test_les_metriques_non_disponibles_sont_signalees_non_mesurables(cfg: Config) -> None:
    resultats = executer(cfg, Random(1), iterations=None)

    non_mesurables = [r for r in resultats if r.statut == "non_mesurable"]
    assert {r.nom for r in non_mesurables} == {
        "ms_par_match_possession",
        "secondes_par_saison_complete",
        "secondes_100_saisons_analytique",
        "secondes_sauvegarde",
    }
    assert all(r.valeur is None for r in non_mesurables)
