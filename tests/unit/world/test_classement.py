from core.config import Config
from core.domain.date import Date
from core.domain.match import Match, ResultatMatch, StatsEquipe
from core.world.classement import calculer_classement

DATE = Date(2026, 8, 10)


def _resultat(buts_dom: int, buts_ext: int) -> ResultatMatch:
    return ResultatMatch(buts_dom=buts_dom, buts_ext=buts_ext, evenements=[], stats_dom=StatsEquipe(), stats_ext=StatsEquipe(), notes={})


def _match(id: int, dom: int, ext: int, resultat: ResultatMatch | None) -> Match:
    return Match(id=id, competition_id=1, journee=1, date=DATE, domicile_id=dom, exterieur_id=ext, resultat=resultat)


def test_victoire_domicile(cfg: Config) -> None:
    matches = [_match(1, 10, 20, _resultat(2, 0))]
    classement = calculer_classement([10, 20], matches, cfg)
    ligne_10 = next(l for l in classement if l.club_id == 10)
    ligne_20 = next(l for l in classement if l.club_id == 20)

    assert ligne_10.victoires == 1 and ligne_10.points == cfg.monde.saison.points_victoire
    assert ligne_20.defaites == 1 and ligne_20.points == cfg.monde.saison.points_defaite


def test_match_nul(cfg: Config) -> None:
    matches = [_match(1, 10, 20, _resultat(1, 1))]
    classement = calculer_classement([10, 20], matches, cfg)
    for ligne in classement:
        assert ligne.nuls == 1 and ligne.points == cfg.monde.saison.points_nul


def test_match_non_joue_est_ignore(cfg: Config) -> None:
    matches = [_match(1, 10, 20, None)]
    classement = calculer_classement([10, 20], matches, cfg)
    for ligne in classement:
        assert ligne.joues == 0


def test_club_sans_match_apparait_a_zero(cfg: Config) -> None:
    classement = calculer_classement([10, 20, 30], [], cfg)
    assert {l.club_id for l in classement} == {10, 20, 30}
    assert all(l.joues == 0 and l.points == 0 for l in classement)


def test_tri_par_points_decroissant(cfg: Config) -> None:
    matches = [_match(1, 10, 20, _resultat(3, 0)), _match(2, 20, 30, _resultat(1, 0))]
    classement = calculer_classement([10, 20, 30], matches, cfg)
    assert [l.club_id for l in classement] == [10, 20, 30]


def test_egalite_de_points_departagee_par_difference_de_buts(cfg: Config) -> None:
    # 10 et 20 ont chacun 3 points (une victoire), mais 10 a une meilleure difference.
    matches = [
        _match(1, 10, 30, _resultat(5, 0)),
        _match(2, 20, 40, _resultat(1, 0)),
    ]
    classement = calculer_classement([10, 20, 30, 40], matches, cfg)
    rang_10 = [l.club_id for l in classement].index(10)
    rang_20 = [l.club_id for l in classement].index(20)
    assert rang_10 < rang_20


def test_confrontation_directe_departage_une_egalite_stricte_a_deux(cfg: Config) -> None:
    # 10 et 20 finissent avec les memes points/diff/BP (4, 0, 3), mais 10
    # a pris 4 points sur les 2 confrontations directes contre 1 pour 20.
    matches = [
        _match(1, 10, 20, _resultat(2, 0)),
        _match(2, 20, 10, _resultat(1, 1)),
        _match(3, 10, 30, _resultat(0, 2)),
        _match(4, 20, 30, _resultat(2, 0)),
    ]
    classement = calculer_classement([10, 20, 30], matches, cfg)
    ligne_10 = next(l for l in classement if l.club_id == 10)
    ligne_20 = next(l for l in classement if l.club_id == 20)
    assert ligne_10.points == ligne_20.points == 4
    assert ligne_10.difference_buts == ligne_20.difference_buts == 0
    assert ligne_10.buts_pour == ligne_20.buts_pour == 3
    assert [l.club_id for l in classement].index(10) < [l.club_id for l in classement].index(20)
