from core.ai.contrats import salaire_attendu
from core.config import Config
from core.domain.attributs import Attributs
from core.domain.club import StatutClub
from core.domain.contrat import Contrat
from core.domain.date import Date
from core.world.contrats import liberer_contrats_expires, renouveler_contrats
from tests.unit.world.fabriques_domaine import DATE, des_attributs, un_club, un_joueur, un_monde


def _uniforme(note: int) -> Attributs:
    return des_attributs(**{champ: note for champ in Attributs.__dataclass_fields__})


class TestRenouvelerContrats:
    def test_ignore_hors_du_1er_du_mois(self, cfg: Config) -> None:
        club = un_club(id=1, reputation=80, masse_salariale_max=10**9)
        joueur = un_joueur(id=1, club_id=1, attributs=_uniforme(70), contrat=Contrat(1_000, Date(2027, 3, 1), DATE))
        monde = un_monde(date=Date(2027, 1, 15), joueurs={1: joueur}, clubs={1: club})

        assert renouveler_contrats(monde, cfg) == []
        assert monde.joueurs[1].contrat.salaire_hebdo == 1_000

    def test_renouvelle_un_joueur_sous_paye_et_sous_le_plafond(self, cfg: Config) -> None:
        club = un_club(id=1, reputation=80, masse_salariale_max=10**9)
        joueur = un_joueur(id=1, club_id=1, attributs=_uniforme(70), contrat=Contrat(1_000, Date(2027, 3, 1), DATE))
        monde = un_monde(date=Date(2027, 1, 1), joueurs={1: joueur}, clubs={1: club})

        journal = renouveler_contrats(monde, cfg)

        assert monde.joueurs[1].club_id == 1
        assert monde.joueurs[1].contrat.salaire_hebdo > 1_000
        assert monde.joueurs[1].contrat.date_fin > Date(2027, 3, 1)
        assert monde.joueurs[1].contrat.date_fin.mois == 6 and monde.joueurs[1].contrat.date_fin.jour == 30
        assert any(e.type.value == "renouvellement" and e.joueur_id == 1 for e in journal)

    def test_ne_renouvelle_pas_si_plafond_depasse(self, cfg: Config) -> None:
        club = un_club(id=1, reputation=90, masse_salariale_max=1)
        joueur = un_joueur(id=1, club_id=1, attributs=_uniforme(90), contrat=Contrat(1_000, Date(2027, 3, 1), DATE))
        monde = un_monde(date=Date(2027, 1, 1), joueurs={1: joueur}, clubs={1: club})

        journal = renouveler_contrats(monde, cfg)

        assert monde.joueurs[1].contrat.salaire_hebdo == 1_000  # inchange
        assert journal == []

    def test_ignore_les_clubs_dormants(self, cfg: Config) -> None:
        club = un_club(id=1, reputation=80, masse_salariale_max=10**9, statut=StatutClub.DORMANT)
        joueur = un_joueur(id=1, club_id=1, attributs=_uniforme(70), contrat=Contrat(1_000, Date(2027, 3, 1), DATE))
        monde = un_monde(date=Date(2027, 1, 1), joueurs={1: joueur}, clubs={1: club})

        assert renouveler_contrats(monde, cfg) == []
        assert monde.joueurs[1].contrat.salaire_hebdo == 1_000


class TestLibererContratsExpires:
    def test_ignore_hors_du_1er_juillet(self, cfg: Config) -> None:
        club = un_club(id=1)
        joueur = un_joueur(id=1, club_id=1, contrat=Contrat(1_000, Date(2027, 6, 30), DATE))
        monde = un_monde(date=Date(2027, 6, 30), joueurs={1: joueur}, clubs={1: club})

        assert liberer_contrats_expires(monde, cfg) == []
        assert monde.joueurs[1].club_id == 1

    def test_libere_un_joueur_dont_le_contrat_est_expire(self, cfg: Config) -> None:
        club = un_club(id=1, nom="Club Test")
        joueur = un_joueur(id=1, club_id=1, contrat=Contrat(1_000, Date(2027, 6, 30), DATE))
        monde = un_monde(date=Date(2027, 7, 1), joueurs={1: joueur}, clubs={1: club})

        journal = liberer_contrats_expires(monde, cfg)

        assert monde.joueurs[1].club_id is None
        assert monde.joueurs[1].contrat is None
        assert any(e.type.value == "agent_libre" and e.joueur_id == 1 for e in journal)

    def test_ne_libere_pas_un_contrat_qui_court_encore(self, cfg: Config) -> None:
        club = un_club(id=1)
        joueur = un_joueur(id=1, club_id=1, contrat=Contrat(1_000, Date(2029, 6, 30), DATE))
        monde = un_monde(date=Date(2027, 7, 1), joueurs={1: joueur}, clubs={1: club})

        liberer_contrats_expires(monde, cfg)

        assert monde.joueurs[1].club_id == 1
        assert monde.joueurs[1].contrat is not None

    def test_ignore_les_clubs_dormants(self, cfg: Config) -> None:
        club = un_club(id=1, statut=StatutClub.DORMANT)
        joueur = un_joueur(id=1, club_id=1, contrat=Contrat(1_000, Date(2027, 6, 30), DATE))
        monde = un_monde(date=Date(2027, 7, 1), joueurs={1: joueur}, clubs={1: club})

        liberer_contrats_expires(monde, cfg)

        assert monde.joueurs[1].club_id == 1
        assert monde.joueurs[1].contrat is not None
