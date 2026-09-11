from random import Random

from core.config import Config
from core.domain.geometrie import Couloir, Zone
from core.domain.match import Evenement, ResultatMatch, StatsEquipe, TypeEvenement
from core.world.appliquer_match import appliquer_resultat_match
from tests.unit.world.fabriques_domaine import un_joueur


def un_resultat(evenements: tuple[Evenement, ...] = (), notes: dict[int, float] | None = None) -> ResultatMatch:
    return ResultatMatch(
        buts_dom=0, buts_ext=0, evenements=list(evenements),
        stats_dom=StatsEquipe(), stats_ext=StatsEquipe(), notes=notes or {},
    )


def test_met_a_jour_fatigue_et_forme_des_joueurs_notes(cfg: Config) -> None:
    joueur = un_joueur(id=1, fatigue=1.0, forme=1.0)
    joueurs = {1: joueur}
    resultat = un_resultat(notes={1: cfg.etats.forme.note_reference + 2})

    appliquer_resultat_match(resultat, joueurs, cfg, Random(1))

    assert joueur.fatigue < 1.0
    assert joueur.forme != 1.0  # a bouge (vers le haut, note au-dessus de la reference)


def test_ignore_les_joueurs_absents_du_dictionnaire(cfg: Config) -> None:
    resultat = un_resultat(notes={999: 6.5})
    appliquer_resultat_match(resultat, {}, cfg, Random(1))  # ne doit pas lever


def test_carton_jaune_incremente_le_cumul(cfg: Config) -> None:
    joueur = un_joueur(id=1)
    joueurs = {1: joueur}
    evenement = Evenement(10, TypeEvenement.CARTON, 1, None, Zone.DEFENSE, Couloir.AXE, detail="jaune")
    resultat = un_resultat(evenements=(evenement,))

    appliquer_resultat_match(resultat, joueurs, cfg, Random(1))

    assert joueur.cartons_jaunes_saison == 1


def test_rouge_directe_suspend_le_joueur(cfg: Config) -> None:
    joueur = un_joueur(id=1)
    joueurs = {1: joueur}
    evenement = Evenement(10, TypeEvenement.CARTON, 1, None, Zone.DEFENSE, Couloir.AXE, detail="rouge_directe")
    resultat = un_resultat(evenements=(evenement,))

    appliquer_resultat_match(resultat, joueurs, cfg, Random(1))

    assert joueur.suspension is not None


def test_rouge_deuxieme_jaune_compte_pour_le_cumul_et_suspend(cfg: Config) -> None:
    joueur = un_joueur(id=1)
    joueurs = {1: joueur}
    evenement = Evenement(10, TypeEvenement.CARTON, 1, None, Zone.DEFENSE, Couloir.AXE, detail="rouge_deuxieme_jaune")
    resultat = un_resultat(evenements=(evenement,))

    appliquer_resultat_match(resultat, joueurs, cfg, Random(1))

    assert joueur.cartons_jaunes_saison == 1
    assert joueur.suspension is not None
    assert joueur.suspension.matches_restants == cfg.etats.suspensions.matches_double_jaune
