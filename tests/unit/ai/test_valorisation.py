from core.ai.valorisation import estimation_potentiel, valeur
from core.config import Config
from core.domain.attributs import Attributs
from core.domain.contrat import Contrat
from core.domain.date import Date
from tests.unit.world.fabriques_domaine import DATE, des_attributs, un_club, un_joueur


def test_estimation_potentiel_est_bruitee_pour_un_jeune(cfg: Config) -> None:
    jeune = un_joueur(date_naissance=Date(2010, 1, 1), potentiel=70)
    fourchette = estimation_potentiel(jeune, DATE, cfg)
    assert fourchette.max - fourchette.min > 0


def test_estimation_potentiel_converge_pour_un_veteran(cfg: Config) -> None:
    veteran = un_joueur(date_naissance=Date(1998, 1, 1), potentiel=70)
    fourchette = estimation_potentiel(veteran, DATE, cfg)
    assert fourchette.min == fourchette.max == 70


def test_estimation_potentiel_plus_incertaine_pour_observateur_faible_reputation(cfg: Config) -> None:
    jeune = un_joueur(date_naissance=Date(2010, 1, 1), potentiel=70)
    gros_club = un_club(reputation=95)
    petit_club = un_club(reputation=10)
    large_petit = estimation_potentiel(jeune, DATE, cfg, club_observateur=petit_club)
    large_gros = estimation_potentiel(jeune, DATE, cfg, club_observateur=gros_club)
    assert (large_petit.max - large_petit.min) > (large_gros.max - large_gros.min)


def _attributs_uniformes(note: int) -> Attributs:
    return des_attributs(**{champ: note for champ in Attributs.__dataclass_fields__})


def test_valeur_convexe_en_talent(cfg: Config) -> None:
    moyen = un_joueur(attributs=_attributs_uniformes(75), potentiel=75)
    fort = un_joueur(attributs=_attributs_uniformes(90), potentiel=90)

    # Convexite en talent (docs/ia-gestion.md) : 90 vaut nettement plus que 1.2x 75.
    assert valeur(fort, DATE, cfg) > valeur(moyen, DATE, cfg) * 2


def test_valeur_decote_fin_de_contrat_proche(cfg: Config) -> None:
    attributs = _attributs_uniformes(70)
    loin = un_joueur(attributs=attributs, contrat=Contrat(10_000, Date(2030, 6, 30), DATE))
    proche = un_joueur(attributs=attributs, contrat=Contrat(10_000, Date(2026, 12, 1), DATE))

    assert valeur(proche, DATE, cfg) < valeur(loin, DATE, cfg)
