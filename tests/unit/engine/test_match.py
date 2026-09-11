import time
from pathlib import Path
from random import Random

import pytest

from core.ai.controller import AIController
from core.config import Config
from core.domain.attributs import Attributs
from core.domain.date import Date
from core.domain.match import TypeEvenement
from core.domain.monde import Monde
from core.domain.poste import Poste
from core.engine.equipe import Equipe, PositionOnze, composition_depuis_effectif
from core.engine.match import MoteurPossession
from core.world.importation import importer_monde
from tests.unit.world.fabriques_domaine import des_attributs, un_joueur

POSTES_442 = [
    Poste.GB, Poste.DL, Poste.DC, Poste.DC, Poste.DR,
    Poste.AILG, Poste.MC, Poste.MC, Poste.AILD, Poste.BU, Poste.BU,
]


def _uniforme(note: int) -> Attributs:
    return des_attributs(**{champ: note for champ in Attributs.__dataclass_fields__})


def _equipe_442(club_id: int, fatigue: float) -> Equipe:
    onze = tuple(
        PositionOnze(
            poste=poste,
            joueur=un_joueur(id=club_id * 100 + i, poste=poste, club_id=club_id, attributs=_uniforme(60), fatigue=fatigue),
        )
        for i, poste in enumerate(POSTES_442)
    )
    return Equipe(club_id=club_id, force_attaque=60.0, force_defense=60.0, onze=onze, formation="4-4-2", hauteur_bloc=0.0)


def _banc(club_id: int, taille: int, fatigue: float = 1.0) -> tuple:
    return tuple(
        un_joueur(id=club_id * 1000 + i, poste=POSTES_442[i % len(POSTES_442)], club_id=club_id, attributs=_uniforme(55), fatigue=fatigue)
        for i in range(taille)
    )


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
            assert len(resultat.notes) == len(dom.onze) + len(ext.onze)
            assert all(1.0 <= note <= 10.0 for note in resultat.notes.values())

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


class TestRemplacements:
    """`bancs`/`controleurs` are optional (step 7) — omitting them keeps
    every prior calibration/benchmark call unaffected (see the other
    tests in this file, none of which pass them).
    """

    def test_omis_aucun_evenement_de_remplacement(self, cfg: Config) -> None:
        dom = _equipe_442(1, fatigue=0.1)
        ext = _equipe_442(2, fatigue=0.1)

        resultat = MoteurPossession().simuler(dom, ext, cfg, Random(1))

        assert not any(e.type is TypeEvenement.REMPLACEMENT for e in resultat.evenements)

    def test_joueur_fatigue_est_remplace(self, cfg: Config) -> None:
        dom = _equipe_442(1, fatigue=0.1)  # tout le monde sous le seuil de declenchement
        ext = _equipe_442(2, fatigue=1.0)
        banc_dom = _banc(1, taille=5, fatigue=1.0)

        resultat = MoteurPossession().simuler(
            dom, ext, cfg, Random(1), bancs={True: banc_dom}, controleurs={True: AIController()}
        )

        remplacements = [e for e in resultat.evenements if e.type is TypeEvenement.REMPLACEMENT]
        assert remplacements
        assert all(e.joueur_secondaire_id in {p.joueur.id for p in dom.onze} for e in remplacements)
        assert all(e.joueur_id in {j.id for j in banc_dom} for e in remplacements)

    def test_respecte_le_maximum_de_remplacements(self, cfg: Config) -> None:
        dom = _equipe_442(1, fatigue=0.1)
        ext = _equipe_442(2, fatigue=1.0)
        banc_dom = _banc(1, taille=cfg.monde.regles_match.remplacements_max + 3, fatigue=1.0)

        resultat = MoteurPossession().simuler(
            dom, ext, cfg, Random(1), bancs={True: banc_dom}, controleurs={True: AIController()}
        )

        remplacements = [e for e in resultat.evenements if e.type is TypeEvenement.REMPLACEMENT]
        assert len(remplacements) <= cfg.monde.regles_match.remplacements_max
