from random import Random

from core.config import Config
from core.world.etats.forme import maj_forme
from tests.unit.world.fabriques_domaine import un_joueur


def test_bonne_performance_pousse_la_forme_vers_le_haut(cfg: Config) -> None:
    joueur = un_joueur(forme=1.0)
    note_excellente = cfg.etats.forme.note_reference + 3
    for graine in range(20):
        maj_forme(joueur, note_excellente, Random(graine), cfg.etats.forme)
    assert joueur.forme > 1.0


def test_mauvaise_performance_pousse_la_forme_vers_le_bas(cfg: Config) -> None:
    joueur = un_joueur(forme=1.0)
    note_mauvaise = cfg.etats.forme.note_reference - 3
    for graine in range(20):
        maj_forme(joueur, note_mauvaise, Random(graine), cfg.etats.forme)
    assert joueur.forme < 1.0


def test_note_de_reference_stabilise_la_forme_au_centre(cfg: Config) -> None:
    joueur = un_joueur(forme=1.0)
    for graine in range(50):
        maj_forme(joueur, cfg.etats.forme.note_reference, Random(graine), cfg.etats.forme)
    assert 0.9 <= joueur.forme <= 1.1


def test_reste_dans_les_bornes(cfg: Config) -> None:
    joueur = un_joueur(forme=1.0)
    for graine in range(200):
        maj_forme(joueur, 10.0, Random(graine), cfg.etats.forme)
    assert cfg.etats.forme.min <= joueur.forme <= cfg.etats.forme.max
