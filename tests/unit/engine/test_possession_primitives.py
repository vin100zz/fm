import statistics
from random import Random

import pytest

from core.engine.occasion import ajuster
from core.engine.possession import reussite


class TestReussite:
    def test_zero_donne_environ_moitie_moitie(self) -> None:
        rng = Random(1)
        resultats = [reussite(0.0, rng) for _ in range(20_000)]
        assert statistics.mean(resultats) == pytest.approx(0.5, abs=0.02)

    def test_grand_positif_presque_toujours_vrai(self) -> None:
        rng = Random(1)
        assert sum(reussite(10.0, rng) for _ in range(1000)) > 990

    def test_grand_negatif_presque_toujours_faux(self) -> None:
        rng = Random(1)
        assert sum(reussite(-10.0, rng) for _ in range(1000)) < 10

    def test_biais_deplace_le_seuil(self) -> None:
        rng_a = Random(1)
        rng_b = Random(1)
        avec_biais = statistics.mean(reussite(0.0, rng_a, biais=2.0) for _ in range(5000))
        sans_biais = statistics.mean(reussite(0.0, rng_b) for _ in range(5000))
        assert avec_biais > sans_biais


class TestAjuster:
    def test_composites_egaux_reproduit_le_xg_de_base(self) -> None:
        assert ajuster(0.11, 50.0, 50.0, 0.035) == pytest.approx(0.11, abs=1e-6)

    def test_attaquant_dominant_augmente_la_probabilite(self) -> None:
        assert ajuster(0.11, 80.0, 40.0, 0.035) > 0.11

    def test_defenseur_dominant_diminue_la_probabilite(self) -> None:
        assert ajuster(0.11, 40.0, 80.0, 0.035) < 0.11

    def test_reste_dans_lintervalle_ouvert(self) -> None:
        resultat = ajuster(0.5, 70.0, 30.0, 0.1)
        assert 0.0 < resultat < 1.0
