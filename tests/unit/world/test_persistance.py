from pathlib import Path
from random import Random

from core.domain.classement import LigneClassement
from core.domain.date import Date
from core.domain.etat_joueur import Blessure, Gravite, Suspension
from core.domain.geometrie import Couloir, Zone
from core.domain.historique import Historique, SaisonTerminee
from core.domain.match import Evenement, Journee, Match, ResultatMatch, StatsEquipe, TypeEvenement
from core.domain.poste import Poste
from core.world.persistance import charger, lister_sauvegardes, sauvegarder
from tests.unit.world.fabriques_domaine import DATE, un_club, un_joueur, un_monde, une_competition


def test_round_trip_un_joueur_avec_blessure_suspension_contrat(tmp_path: Path) -> None:
    joueur = un_joueur(
        id=1,
        blessure=Blessure(date_debut=DATE, date_fin=Date(2026, 9, 1), gravite=Gravite.MOYENNE, description="test"),
        suspension=Suspension(matches_restants=2, motif="cumul"),
        postes_secondaires={Poste.DC: 0.6, Poste.MDC: 0.3},
    )
    monde = un_monde(joueurs={1: joueur})
    rng = Random(1)

    sauvegarder(monde, rng, tmp_path / "s.json.gz")
    monde2, _ = charger(tmp_path / "s.json.gz")

    assert monde2 == monde
    assert monde2.joueurs[1].blessure.gravite is Gravite.MOYENNE
    assert monde2.joueurs[1].postes_secondaires == {Poste.DC: 0.6, Poste.MDC: 0.3}


def test_round_trip_un_club(tmp_path: Path) -> None:
    club = un_club(id=42)
    monde = un_monde(clubs={42: club})
    rng = Random(1)

    sauvegarder(monde, rng, tmp_path / "s.json.gz")
    monde2, _ = charger(tmp_path / "s.json.gz")

    assert monde2.clubs[42] == club


def test_round_trip_competition_et_match_avec_resultat(tmp_path: Path) -> None:
    resultat = ResultatMatch(
        buts_dom=2, buts_ext=1,
        evenements=[Evenement(10, TypeEvenement.BUT, 1, 2, Zone.VERITE, Couloir.AXE, detail="corner")],
        stats_dom=StatsEquipe(tirs=8, xg=1.2, possession_pct=55.0, corners=3, cartons_jaunes=1, cartons_rouges=0),
        stats_ext=StatsEquipe(),
        notes={1: 7.5, 2: 6.0},
    )
    match = Match(id=100, competition_id=1, journee=1, date=DATE, domicile_id=10, exterieur_id=20, resultat=resultat)
    competition = une_competition(id=1, club_ids=[10, 20], calendrier=[Journee(numero=1, match_ids=[100])])
    monde = un_monde(competitions={1: competition}, matches={100: match})
    rng = Random(1)

    sauvegarder(monde, rng, tmp_path / "s.json.gz")
    monde2, _ = charger(tmp_path / "s.json.gz")

    assert monde2 == monde
    assert monde2.matches[100].resultat.evenements[0].zone is Zone.VERITE


def test_round_trip_match_sans_resultat(tmp_path: Path) -> None:
    match = Match(id=1, competition_id=1, journee=1, date=DATE, domicile_id=10, exterieur_id=20)
    monde = un_monde(matches={1: match})
    rng = Random(1)

    sauvegarder(monde, rng, tmp_path / "s.json.gz")
    monde2, _ = charger(tmp_path / "s.json.gz")

    assert monde2.matches[1].resultat is None


def test_flux_aleatoire_reprend_exactement(tmp_path: Path) -> None:
    monde = un_monde()
    rng = Random(123)
    rng.random()  # avance un peu le flux avant la sauvegarde
    rng.random()

    sauvegarder(monde, rng, tmp_path / "s.json.gz")
    _, rng2 = charger(tmp_path / "s.json.gz")

    attendu = [rng.random() for _ in range(10)]
    obtenu = [rng2.random() for _ in range(10)]
    assert attendu == obtenu


def test_round_trip_match_tague_avec_sa_saison(tmp_path: Path) -> None:
    match = Match(id=1, competition_id=1, journee=1, date=DATE, domicile_id=10, exterieur_id=20, saison=2)
    monde = un_monde(matches={1: match})
    rng = Random(1)

    sauvegarder(monde, rng, tmp_path / "s.json.gz")
    monde2, _ = charger(tmp_path / "s.json.gz")

    assert monde2.matches[1].saison == 2


def test_round_trip_palmares(tmp_path: Path) -> None:
    saison_archivee = SaisonTerminee(
        competition_id=1, saison=1,
        classement_final=[
            LigneClassement(club_id=10, joues=6, victoires=4, nuls=1, defaites=1, buts_pour=12, buts_contre=5, points=13),
            LigneClassement(club_id=20, joues=6, victoires=3, nuls=1, defaites=2, buts_pour=9, buts_contre=7, points=10),
        ],
    )
    monde = un_monde(historique=Historique(palmares=[saison_archivee]))
    rng = Random(1)

    sauvegarder(monde, rng, tmp_path / "s.json.gz")
    monde2, _ = charger(tmp_path / "s.json.gz")

    assert monde2 == monde
    assert monde2.historique.palmares[0].champion_id == 10


def test_lister_sauvegardes_dossier_absent(tmp_path: Path) -> None:
    assert lister_sauvegardes(tmp_path / "inexistant") == []


def test_lister_sauvegardes(tmp_path: Path) -> None:
    monde = un_monde()
    rng = Random(1)
    sauvegarder(monde, rng, tmp_path / "alpha.json.gz")
    sauvegarder(monde, rng, tmp_path / "beta.json.gz")

    infos = lister_sauvegardes(tmp_path)
    assert {i.slot for i in infos} == {"alpha", "beta"}
    assert all(i.taille_octets > 0 for i in infos)
