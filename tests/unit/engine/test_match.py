import time
from pathlib import Path
from random import Random

import pytest

from core.config import Config
from core.domain.date import Date
from core.domain.match import TypeEvenement
from core.domain.monde import Monde
from core.engine.equipe import composition_depuis_effectif
from core.engine.match import MoteurPossession
from core.world.importation import importer_monde


@pytest.fixture(scope="module")
def monde(cfg: Config, dossier_donnees: Path) -> Monde:
    monde_importe, _avertissements = importer_monde(dossier_donnees, cfg, Date(2026, 8, 10), 1, Random(1))
    return monde_importe


@pytest.fixture
def psg_toulouse(cfg: Config, monde: Monde):
    psg = next(c for c in monde.clubs.values() if c.nom == "Paris SG")
    toulouse = next(c for c in monde.clubs.values() if c.nom == "Toulouse FC")
    dom = composition_depuis_effectif(psg.id, monde.joueurs, psg.formation_preferee, 0.0, cfg)
    ext = composition_depuis_effectif(toulouse.id, monde.joueurs, toulouse.formation_preferee, 0.0, cfg)
    return dom, ext


class TestMoteurPossession:
    def test_deterministe_avec_la_meme_graine(self, cfg: Config, psg_toulouse) -> None:
        dom, ext = psg_toulouse

        premier = MoteurPossession().simuler(dom, ext, cfg, Random(123))
        second = MoteurPossession().simuler(dom, ext, cfg, Random(123))

        assert (premier.buts_dom, premier.buts_ext) == (second.buts_dom, second.buts_ext)
        assert [e.type for e in premier.evenements] == [e.type for e in second.evenements]

    def test_score_et_stats_dans_des_bornes_credibles(self, cfg: Config, psg_toulouse) -> None:
        dom, ext = psg_toulouse

        for graine in range(15):
            resultat = MoteurPossession().simuler(dom, ext, cfg, Random(graine))
            assert 0 <= resultat.buts_dom < 15
            assert 0 <= resultat.buts_ext < 15
            assert resultat.stats_dom.tirs is not None and resultat.stats_dom.tirs >= 0
            assert resultat.stats_dom.possession_pct is not None
            assert resultat.notes == {}

    def test_temps_sous_20ms_en_moyenne(self, cfg: Config, psg_toulouse) -> None:
        dom, ext = psg_toulouse
        moteur = MoteurPossession()

        debut = time.perf_counter()
        n = 30
        for graine in range(n):
            moteur.simuler(dom, ext, cfg, Random(graine))
        duree_moyenne_ms = (time.perf_counter() - debut) / n * 1000

        assert duree_moyenne_ms < cfg.benchmarks.performance.ms_par_match_possession

    def test_but_est_toujours_precede_dun_tir(self, cfg: Config, psg_toulouse) -> None:
        dom, ext = psg_toulouse
        vu_un_but = False

        for graine in range(20):
            resultat = MoteurPossession().simuler(dom, ext, cfg, Random(graine))
            for i, evenement in enumerate(resultat.evenements):
                if evenement.type is TypeEvenement.BUT:
                    vu_un_but = True
                    assert resultat.evenements[i - 1].type is TypeEvenement.TIR

        assert vu_un_but

    def test_cinquante_matches_entre_clubs_actifs_sans_exception(self, cfg: Config, monde: Monde) -> None:
        clubs_actifs = [c for c in monde.clubs.values() if c.statut.value == "actif"][:10]
        moteur = MoteurPossession()

        for i in range(50):
            dom_club = clubs_actifs[i % len(clubs_actifs)]
            ext_club = clubs_actifs[(i + 1) % len(clubs_actifs)]
            dom = composition_depuis_effectif(dom_club.id, monde.joueurs, dom_club.formation_preferee, 0.0, cfg)
            ext = composition_depuis_effectif(ext_club.id, monde.joueurs, ext_club.formation_preferee, 0.0, cfg)
            moteur.simuler(dom, ext, cfg, Random(i))
