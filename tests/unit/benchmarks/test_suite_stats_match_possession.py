from random import Random

from core.config import Config
from benchmarks.suites.stats_match_possession import executer


def test_produit_les_cibles_mesurables(cfg: Config) -> None:
    resultats = executer(cfg, Random(1), iterations=20)

    noms = {r.nom for r in resultats}
    for cible in ("tirs_par_equipe", "xg_par_equipe", "possession_pct", "jaunes_par_equipe", "rouges_par_equipe"):
        assert cible in noms

    assert all(r.statut != "non_mesurable" for r in resultats)


def test_repartition_couloirs_somme_a_un(cfg: Config) -> None:
    resultats = executer(cfg, Random(2), iterations=30)

    parts = [r.valeur for r in resultats if r.nom.startswith("repartition_couloirs/")]
    assert len(parts) == 3
    assert sum(parts) == 1.0 or abs(sum(parts) - 1.0) < 1e-9


def test_deterministe_avec_la_meme_graine(cfg: Config) -> None:
    a = executer(cfg, Random(7), iterations=15)
    b = executer(cfg, Random(7), iterations=15)

    assert [r.valeur for r in a] == [r.valeur for r in b]
