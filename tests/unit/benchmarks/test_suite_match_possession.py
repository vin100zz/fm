from random import Random

import pytest

from core.config import Config
from benchmarks.suites.match_possession import executer


def test_produit_victoire_nul_defaite_par_affrontement_reel(cfg: Config) -> None:
    resultats = executer(cfg, Random(1), iterations=30)

    noms_affrontements_reels = {
        affrontement.id
        for affrontement in cfg.benchmarks.affrontements_reference
        if "NIVEAU" not in affrontement.domicile and "NIVEAU" not in affrontement.exterieur
    }
    for affrontement_id in noms_affrontements_reels:
        for issue in ("victoire", "nul", "defaite"):
            assert any(r.nom == f"{affrontement_id}/{issue}" for r in resultats)


def test_ignore_les_affrontements_synthetiques(cfg: Config) -> None:
    resultats = executer(cfg, Random(1), iterations=10)

    assert not any(r.nom.startswith("egaux_dom/") for r in resultats)


def test_les_trois_issues_epuisent_les_matches(cfg: Config) -> None:
    n = 50
    resultats = executer(cfg, Random(1), iterations=n)

    premier_id = next(
        affrontement.id
        for affrontement in cfg.benchmarks.affrontements_reference
        if "NIVEAU" not in affrontement.domicile
    )
    parts = [r.valeur for r in resultats if r.nom.startswith(f"{premier_id}/")]
    assert sum(parts) == pytest.approx(1.0)
