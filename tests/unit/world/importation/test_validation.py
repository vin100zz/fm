import pytest

from core.domain.club import Club, StatutClub
from core.domain.historique import Historique
from core.domain.joueur import Joueur
from core.domain.monde import Monde
from core.domain.poste import Poste
from core.world.importation.erreurs import ImportInvalide
from core.world.importation.validation import valider
from tests.unit.world.fabriques_domaine import DATE, un_club, un_effectif_complet, un_joueur


def un_monde(clubs: list[Club], joueurs: list[Joueur]) -> Monde:
    return Monde(
        date=DATE, saison=1, graine=1,
        joueurs={j.id: j for j in joueurs},
        clubs={c.id: c for c in clubs},
        competitions={}, historique=Historique(), prochain_id=10_000,
    )


COMPETITIONS_UNE_LIGUE = [type("Comp", (), {"nom": "Test", "pays": "ENG", "division_id": 11, "nb_clubs": 1})()]
EFFECTIF_MAX_AVERTISSEMENT = 32


def test_effectif_suffisant_avec_gardien_passe() -> None:
    club = un_club()
    monde = un_monde([club], un_effectif_complet(club.id))

    avertissements = valider(monde, COMPETITIONS_UNE_LIGUE, EFFECTIF_MAX_AVERTISSEMENT)

    assert avertissements == []


def test_effectif_sous_seize_est_bloquant() -> None:
    club = un_club()
    joueurs = un_effectif_complet(club.id)[:10]  # 10 < 16
    monde = un_monde([club], joueurs)

    with pytest.raises(ImportInvalide) as exc:
        valider(monde, COMPETITIONS_UNE_LIGUE, EFFECTIF_MAX_AVERTISSEMENT)

    assert any("16" in erreur for erreur in exc.value.erreurs)


def test_aucun_gardien_est_bloquant() -> None:
    club = un_club()
    joueurs = [un_joueur(id=200 + i, poste=Poste.MC, club_id=club.id) for i in range(16)]
    monde = un_monde([club], joueurs)

    with pytest.raises(ImportInvalide) as exc:
        valider(monde, COMPETITIONS_UNE_LIGUE, EFFECTIF_MAX_AVERTISSEMENT)

    assert any("gardien" in erreur for erreur in exc.value.erreurs)


def test_club_id_inconnu_est_bloquant() -> None:
    club = un_club()
    joueurs = un_effectif_complet(club.id)
    joueurs.append(un_joueur(id=500, club_id=999))  # 999 n'existe pas
    monde = un_monde([club], joueurs)

    with pytest.raises(ImportInvalide) as exc:
        valider(monde, COMPETITIONS_UNE_LIGUE, EFFECTIF_MAX_AVERTISSEMENT)

    assert any("999" in erreur for erreur in exc.value.erreurs)


def test_mauvais_nombre_de_clubs_par_competition_est_bloquant() -> None:
    monde = un_monde([un_club()], un_effectif_complet(1))
    competitions = [type("Comp", (), {"nom": "Test", "pays": "ENG", "division_id": 11, "nb_clubs": 2})()]

    with pytest.raises(ImportInvalide) as exc:
        valider(monde, competitions, EFFECTIF_MAX_AVERTISSEMENT)

    assert any("1 clubs actifs" in erreur for erreur in exc.value.erreurs)


def test_attribut_hors_bornes_est_bloquant() -> None:
    club = un_club()
    joueurs = un_effectif_complet(club.id)
    joueurs[0].attributs.finition = 150  # invariant casse volontairement
    monde = un_monde([club], joueurs)

    with pytest.raises(ImportInvalide) as exc:
        valider(monde, COMPETITIONS_UNE_LIGUE, EFFECTIF_MAX_AVERTISSEMENT)

    assert any("finition" in erreur for erreur in exc.value.erreurs)


def test_effectif_au_dessus_du_seuil_est_un_avertissement_pas_bloquant() -> None:
    club = un_club()
    joueurs = un_effectif_complet(club.id)
    joueurs += [un_joueur(id=300 + i, club_id=club.id) for i in range(20)]  # 36 au total
    monde = un_monde([club], joueurs)

    avertissements = valider(monde, COMPETITIONS_UNE_LIGUE, EFFECTIF_MAX_AVERTISSEMENT)

    assert any("36 joueurs" in avertissement for avertissement in avertissements)


def test_masse_salariale_au_dessus_du_plafond_est_un_avertissement() -> None:
    club = un_club(masse_salariale_max=1_000)
    monde = un_monde([club], un_effectif_complet(club.id))

    avertissements = valider(monde, COMPETITIONS_UNE_LIGUE, EFFECTIF_MAX_AVERTISSEMENT)

    assert any("masse salariale" in avertissement for avertissement in avertissements)


def test_club_dormant_sans_effectif_ne_bloque_rien() -> None:
    club_actif = un_club(id=1, competition_id=11)
    club_dormant = un_club(id=2, statut=StatutClub.DORMANT, competition_id=-1)
    monde = un_monde([club_actif, club_dormant], un_effectif_complet(1))

    avertissements = valider(monde, COMPETITIONS_UNE_LIGUE, EFFECTIF_MAX_AVERTISSEMENT)

    assert avertissements == []
