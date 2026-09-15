from core.ai.budgets import depense_mensuelle_salaires, revenu_mensuel
from core.config import Config
from core.domain.club import StatutClub
from core.domain.date import Date
from core.world.finances import appliquer_flux_mensuel
from tests.unit.world.fabriques_domaine import un_club, un_joueur, un_monde


def test_ne_fait_rien_hors_du_premier_du_mois(cfg: Config) -> None:
    club = un_club(id=1, budget_transfert=1_000, solde=1_000)
    joueur = un_joueur(id=1, club_id=1)
    monde = un_monde(clubs={1: club}, joueurs={1: joueur}, competitions={})
    monde.date = Date(2028, 3, 15)

    appliquer_flux_mensuel(monde, cfg)

    assert club.budget_transfert == 1_000
    assert club.solde == 1_000


def test_credite_le_revenu_mensuel_et_debite_les_salaires(cfg: Config) -> None:
    # revenu_mensuel est ancre sur la masse salariale REELLEMENT payee
    # (l'effectif), pas sur club.masse_salariale_max (2026-09-12,
    # deuxieme passe) : un plafond fixe payait plein pot quel que soit
    # le vrai effectif, et faisait accumuler plus d'un milliard d'euros
    # de budget transfert inutilise a Real Madrid sur 4 saisons simulees.
    club = un_club(id=1, masse_salariale_max=10**9, budget_transfert=1_000, solde=1_000)
    joueur = un_joueur(id=1, club_id=1)
    monde = un_monde(clubs={1: club}, joueurs={1: joueur}, competitions={})
    monde.date = Date(2028, 3, 1)

    appliquer_flux_mensuel(monde, cfg)

    masse_hebdo = joueur.contrat.salaire_hebdo
    flux_attendu = revenu_mensuel(masse_hebdo, cfg) - depense_mensuelle_salaires([joueur], cfg)
    assert club.budget_transfert == 1_000 + flux_attendu
    assert club.solde == 1_000 + flux_attendu


def test_un_effectif_sans_joueur_ne_genere_ni_revenu_ni_depense(cfg: Config) -> None:
    club = un_club(id=1, masse_salariale_max=10**9, budget_transfert=1_000, solde=1_000)
    monde = un_monde(clubs={1: club}, joueurs={}, competitions={})
    monde.date = Date(2028, 3, 1)

    appliquer_flux_mensuel(monde, cfg)

    assert club.budget_transfert == 1_000
    assert club.solde == 1_000


def test_le_flux_est_toujours_positif_ou_nul_les_salaires_reels_ne_mettent_plus_en_dette(cfg: Config) -> None:
    # revenu_mensuel et depense_mensuelle_salaires derivent tous deux de
    # la meme masse salariale actuelle : le flux ne peut plus etre
    # negatif du seul fait des salaires (seul un depassement du budget
    # transfert a l'achat pourrait, en theorie, y mener — deja bloque en
    # amont par _peut_se_permettre).
    club = un_club(id=1, masse_salariale_max=10**9, budget_transfert=0, solde=0)
    effectif = [un_joueur(id=i, club_id=1) for i in range(20)]
    monde = un_monde(clubs={1: club}, joueurs={j.id: j for j in effectif}, competitions={})
    monde.date = Date(2028, 3, 1)

    appliquer_flux_mensuel(monde, cfg)

    assert club.budget_transfert >= 0
    assert club.solde >= 0


def test_ignore_les_clubs_dormants(cfg: Config) -> None:
    club = un_club(id=1, statut=StatutClub.DORMANT, masse_salariale_max=1_000_000, budget_transfert=1_000, solde=1_000)
    monde = un_monde(clubs={1: club}, joueurs={}, competitions={})
    monde.date = Date(2028, 3, 1)

    appliquer_flux_mensuel(monde, cfg)

    assert club.budget_transfert == 1_000
    assert club.solde == 1_000
