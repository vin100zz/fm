import statistics
from random import Random

import pytest

from core.config import Config
from core.engine.analytique import MoteurAnalytique, _tirage_poisson
from core.engine.equipe import Equipe


class TestTiragePoisson:
    def test_toujours_un_entier_positif_ou_nul(self) -> None:
        rng = Random(1)
        for _ in range(500):
            assert _tirage_poisson(1.5, rng) >= 0

    def test_moyenne_proche_de_lambda_sur_beaucoup_de_tirages(self) -> None:
        rng = Random(42)
        lam = 2.3
        tirages = [_tirage_poisson(lam, rng) for _ in range(20_000)]
        assert statistics.mean(tirages) == pytest.approx(lam, abs=0.05)

    def test_deterministe_avec_la_meme_graine(self) -> None:
        a = [_tirage_poisson(1.8, Random(7)) for _ in range(50)]
        b = [_tirage_poisson(1.8, Random(7)) for _ in range(50)]
        assert a == b

    def test_lambda_quasi_nul_donne_presque_toujours_zero(self) -> None:
        rng = Random(1)
        tirages = [_tirage_poisson(0.01, rng) for _ in range(1000)]
        assert tirages.count(0) > 980


class TestMoteurAnalytique:
    def test_resultat_sans_evenements_ni_stats_detaillees(self, cfg: Config) -> None:
        dom = Equipe(club_id=1, force_attaque=60, force_defense=60)
        ext = Equipe(club_id=2, force_attaque=60, force_defense=60)

        resultat = MoteurAnalytique().simuler(dom, ext, cfg, Random(1))

        assert resultat.buts_dom >= 0
        assert resultat.buts_ext >= 0
        assert resultat.evenements == []
        assert resultat.notes == {}
        assert resultat.stats_dom.tirs is None

    def test_deterministe_avec_la_meme_graine(self, cfg: Config) -> None:
        dom = Equipe(club_id=1, force_attaque=70, force_defense=55)
        ext = Equipe(club_id=2, force_attaque=50, force_defense=60)

        premier = MoteurAnalytique().simuler(dom, ext, cfg, Random(20260910))
        second = MoteurAnalytique().simuler(dom, ext, cfg, Random(20260910))

        assert (premier.buts_dom, premier.buts_ext) == (second.buts_dom, second.buts_ext)

    def test_equipe_plus_forte_gagne_plus_souvent(self, cfg: Config) -> None:
        forte = Equipe(club_id=1, force_attaque=85, force_defense=80)
        faible = Equipe(club_id=2, force_attaque=35, force_defense=30)
        moteur = MoteurAnalytique()

        victoires_fortes = 0
        n = 500
        for graine in range(n):
            resultat = moteur.simuler(forte, faible, cfg, Random(graine))
            if resultat.buts_dom > resultat.buts_ext:
                victoires_fortes += 1

        assert victoires_fortes / n > 0.7

    def test_avantage_du_terrain_favorise_le_domicile_a_forces_egales(self, cfg: Config) -> None:
        moteur = MoteurAnalytique()
        n = 2000
        buts_dom_total = 0
        buts_ext_total = 0
        for graine in range(n):
            equipe_dom = Equipe(club_id=1, force_attaque=55, force_defense=55)
            equipe_ext = Equipe(club_id=2, force_attaque=55, force_defense=55)
            resultat = moteur.simuler(equipe_dom, equipe_ext, cfg, Random(graine))
            buts_dom_total += resultat.buts_dom
            buts_ext_total += resultat.buts_ext

        assert buts_dom_total > buts_ext_total

    def test_ne_plante_pas_sur_un_ecart_de_force_extreme(self, cfg: Config) -> None:
        tres_faible = Equipe(club_id=1, force_attaque=1, force_defense=1)
        tres_forte = Equipe(club_id=2, force_attaque=100, force_defense=100)

        resultat = MoteurAnalytique().simuler(tres_faible, tres_forte, cfg, Random(1))

        assert resultat.buts_dom >= 0
        assert resultat.buts_ext >= 0
