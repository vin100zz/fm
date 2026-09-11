from random import Random

from core.config import Config
from core.domain.date import Date
from core.world.calendrier import generer_calendrier

DATE_DEBUT = Date(2026, 8, 10)


def test_round_robin_aller_retour_pour_un_nombre_pair_de_clubs(cfg: Config) -> None:
    clubs = [1, 2, 3, 4]
    matches, journees = generer_calendrier(clubs, competition_id=99, saison=1, premier_match_id=1000, date_debut=DATE_DEBUT, cfg=cfg, rng=Random(1))

    assert len(journees) == (len(clubs) - 1) * 2
    assert len(matches) == len(clubs) * (len(clubs) - 1)  # chaque paire s'affronte deux fois


def test_chaque_club_joue_exactement_une_fois_par_journee(cfg: Config) -> None:
    clubs = [1, 2, 3, 4, 5, 6]
    matches, journees = generer_calendrier(clubs, competition_id=99, saison=1, premier_match_id=1000, date_debut=DATE_DEBUT, cfg=cfg, rng=Random(1))
    matches_par_id = {m.id: m for m in matches}

    for journee in journees:
        joueurs_du_jour = []
        for match_id in journee.match_ids:
            match = matches_par_id[match_id]
            joueurs_du_jour += [match.domicile_id, match.exterieur_id]
        assert sorted(joueurs_du_jour) == sorted(clubs)


def test_chaque_paire_s_affronte_deux_fois_domicile_et_exterieur(cfg: Config) -> None:
    clubs = [1, 2, 3, 4]
    matches, _ = generer_calendrier(clubs, competition_id=99, saison=1, premier_match_id=1000, date_debut=DATE_DEBUT, cfg=cfg, rng=Random(1))

    paires = [(m.domicile_id, m.exterieur_id) for m in matches]
    for a, b in [(1, 2), (1, 3), (1, 4), (2, 3), (2, 4), (3, 4)]:
        assert (a, b) in paires
        assert (b, a) in paires


def test_gere_un_nombre_impair_de_clubs_avec_un_bye(cfg: Config) -> None:
    clubs = [1, 2, 3]
    matches, journees = generer_calendrier(clubs, competition_id=99, saison=1, premier_match_id=1000, date_debut=DATE_DEBUT, cfg=cfg, rng=Random(1))

    for journee in journees:
        assert len(journee.match_ids) == 1  # un des 3 clubs est au repos chaque journee


def test_les_dates_avancent_de_jours_entre_journees(cfg: Config) -> None:
    clubs = [1, 2, 3, 4]
    matches, journees = generer_calendrier(clubs, competition_id=99, saison=1, premier_match_id=1000, date_debut=DATE_DEBUT, cfg=cfg, rng=Random(1))
    matches_par_id = {m.id: m for m in matches}

    dates_par_journee = [matches_par_id[j.match_ids[0]].date for j in journees]
    for avant, apres in zip(dates_par_journee, dates_par_journee[1:]):
        assert avant.jours_jusqua(apres) == cfg.monde.saison.jours_entre_journees


def test_ids_de_match_uniques_et_sequentiels(cfg: Config) -> None:
    clubs = [1, 2, 3, 4, 5, 6]
    matches, _ = generer_calendrier(clubs, competition_id=99, saison=1, premier_match_id=5000, date_debut=DATE_DEBUT, cfg=cfg, rng=Random(1))

    ids = [m.id for m in matches]
    assert len(ids) == len(set(ids))
    assert min(ids) == 5000


def test_chaque_match_est_tague_avec_la_saison_donnee(cfg: Config) -> None:
    clubs = [1, 2, 3, 4]
    matches, _ = generer_calendrier(clubs, competition_id=99, saison=3, premier_match_id=1000, date_debut=DATE_DEBUT, cfg=cfg, rng=Random(1))

    assert all(m.saison == 3 for m in matches)
