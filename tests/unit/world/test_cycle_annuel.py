from random import Random

from core.config import Config
from core.domain.club import StatutClub
from core.domain.date import Date
from core.domain.historique import TypeMouvementEffectif
from core.domain.journal import TypeEvenementJour
from core.world.demographie.cycle_annuel import appliquer_cycle_annuel_effectif
from tests.unit.world.fabriques_domaine import un_club, un_joueur, un_monde


class _RngRetraiteForce(Random):
    """Meme principe que le RngDemarcheForce de test_mercato.py : force
    le tirage de la retraite a reussir de facon deterministe. Herite de
    Random (pas juste .random()) : _appliquer_promotions, appelee dans
    la meme passe, a aussi besoin de randint/choice/gauss/betavariate."""

    def random(self) -> float:
        return 0.0  # toujours < probabilite_retraite (des lors qu'elle est > 0)


def _date_cycle(cfg: Config, annee: int) -> Date:
    dc = cfg.monde.dates_cles.promotion_centre_formation
    return Date(annee, dc.mois, dc.jour)


def _avec_population_de_base(joueurs: dict) -> dict:
    """`_appliquer_promotions` construit ses pools de noms depuis la
    population courante (`construire_pools_noms`) — sans au moins un
    joueur d'une nation hors des 5 simulees, le "vivier exterieur" est
    vide et `promouvoir_centre_formation` plante en tirant dedans (meme
    fixture que `tests/unit/world/demographie/test_generation.py::_pools`)."""
    base = {
        90000 + i: un_joueur(id=90000 + i, nom=f"Base{i}", prenom=f"Base{i}", nationalite="Bresil", club_id=None, contrat=None)
        for i in range(20)
    }
    return {**base, **joueurs}


class TestGate:
    def test_ne_fait_rien_hors_de_la_date_du_cycle(self, cfg: Config) -> None:
        age_minimal = cfg.demographie.sorties.retraite.age_minimal
        club = un_club(id=1)
        joueur = un_joueur(id=1, club_id=1, date_naissance=Date(2026 - (age_minimal + 5), 1, 1))
        monde = un_monde(clubs={1: club}, joueurs=_avec_population_de_base({1: joueur}), competitions={})
        monde.date = Date(2027, 3, 15)

        journal = appliquer_cycle_annuel_effectif(monde, cfg, _RngRetraiteForce())

        assert journal == []
        assert 1 in monde.joueurs
        assert monde.historique.mouvements_effectif == []


class TestRetraites:
    def test_un_joueur_eligible_prend_sa_retraite_et_quitte_le_monde(self, cfg: Config) -> None:
        age_minimal = cfg.demographie.sorties.retraite.age_minimal
        club = un_club(id=1)
        joueur = un_joueur(id=1, club_id=1, nom="Vieux", prenom="Joueur", date_naissance=Date(2027 - (age_minimal + 5), 1, 1))
        monde = un_monde(clubs={1: club}, joueurs=_avec_population_de_base({1: joueur}), competitions={})
        monde.date = _date_cycle(cfg, 2027)

        journal = appliquer_cycle_annuel_effectif(monde, cfg, _RngRetraiteForce())

        assert 1 not in monde.joueurs
        assert any(e.type is TypeEvenementJour.RETRAITE for e in journal)
        mouvements = [m for m in monde.historique.mouvements_effectif if m.type is TypeMouvementEffectif.RETRAITE]
        assert len(mouvements) == 1
        assert mouvements[0].joueur_id == 1
        assert mouvements[0].nom == "Vieux" and mouvements[0].prenom == "Joueur"
        assert mouvements[0].club_id == 1

    def test_un_joueur_dun_club_dormant_ne_prend_pas_sa_retraite(self, cfg: Config) -> None:
        age_minimal = cfg.demographie.sorties.retraite.age_minimal
        club = un_club(id=1, statut=StatutClub.DORMANT)
        joueur = un_joueur(id=1, club_id=1, date_naissance=Date(2027 - (age_minimal + 5), 1, 1))
        monde = un_monde(clubs={1: club}, joueurs=_avec_population_de_base({1: joueur}), competitions={})
        monde.date = _date_cycle(cfg, 2027)

        appliquer_cycle_annuel_effectif(monde, cfg, _RngRetraiteForce())

        assert 1 in monde.joueurs

    def test_un_agent_libre_ne_prend_pas_sa_retraite(self, cfg: Config) -> None:
        age_minimal = cfg.demographie.sorties.retraite.age_minimal
        joueur = un_joueur(id=1, club_id=None, contrat=None, date_naissance=Date(2027 - (age_minimal + 5), 1, 1))
        monde = un_monde(clubs={}, joueurs=_avec_population_de_base({1: joueur}), competitions={})
        monde.date = _date_cycle(cfg, 2027)

        appliquer_cycle_annuel_effectif(monde, cfg, _RngRetraiteForce())

        assert 1 in monde.joueurs

    def test_un_joueur_sous_l_age_minimal_ne_prend_jamais_sa_retraite(self, cfg: Config) -> None:
        # probabilite_retraite vaut structurellement 0 sous l'age minimal
        # (core/world/demographie/sorties.py) : meme avec un rng force a
        # toujours "reussir" le tirage, ce joueur ne doit jamais partir.
        age_minimal = cfg.demographie.sorties.retraite.age_minimal
        club = un_club(id=1)
        jeune = un_joueur(id=1, club_id=1, date_naissance=Date(2027 - (age_minimal - 1), 1, 1))
        monde = un_monde(clubs={1: club}, joueurs=_avec_population_de_base({1: jeune}), competitions={})
        monde.date = _date_cycle(cfg, 2027)

        appliquer_cycle_annuel_effectif(monde, cfg, _RngRetraiteForce())

        assert 1 in monde.joueurs


class TestPromotions:
    def test_un_club_actif_recoit_des_joueurs_promus(self, cfg: Config) -> None:
        club = un_club(id=1)
        monde = un_monde(clubs={1: club}, joueurs=_avec_population_de_base({}), competitions={})
        monde.date = _date_cycle(cfg, 2027)
        monde.prochain_id = 100_000

        journal = appliquer_cycle_annuel_effectif(monde, cfg, Random(1))

        promus = [m for m in monde.historique.mouvements_effectif if m.type is TypeMouvementEffectif.PROMOTION]
        assert len(promus) > 0
        assert all(e.type is TypeEvenementJour.PROMOTION for e in journal)
        for mouvement in promus:
            assert mouvement.joueur_id in monde.joueurs
            assert monde.joueurs[mouvement.joueur_id].club_id == 1

    def test_un_club_dormant_ne_recoit_aucune_promotion(self, cfg: Config) -> None:
        club = un_club(id=1, statut=StatutClub.DORMANT)
        monde = un_monde(clubs={1: club}, joueurs=_avec_population_de_base({}), competitions={})
        monde.date = _date_cycle(cfg, 2027)
        monde.prochain_id = 100_000

        appliquer_cycle_annuel_effectif(monde, cfg, Random(1))

        assert monde.historique.mouvements_effectif == []

    def test_deux_clubs_actifs_ne_recoivent_jamais_le_meme_id(self, cfg: Config) -> None:
        clubs = {1: un_club(id=1), 2: un_club(id=2)}
        monde = un_monde(clubs=clubs, joueurs=_avec_population_de_base({}), competitions={})
        monde.date = _date_cycle(cfg, 2027)
        monde.prochain_id = 100_000

        appliquer_cycle_annuel_effectif(monde, cfg, Random(1))

        ids = [m.joueur_id for m in monde.historique.mouvements_effectif]
        assert len(ids) == len(set(ids))
