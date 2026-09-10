"""Integrity checks over an assembled Monde. See "Validation au
chargement" in docs/modele-donnees.md: the first group raises
ImportInvalide (refuse to start), the second is returned as warnings.
"""

from core.config.modeles.monde import CompetitionSimulee
from core.domain.attributs import NOMS_ATTRIBUTS
from core.domain.club import StatutClub
from core.domain.monde import Monde
from core.domain.poste import Poste
from core.world.importation.erreurs import ImportInvalide

_EFFECTIF_MIN_CLUB_ACTIF = 16


def valider(
    monde: Monde, competitions_simulees: list[CompetitionSimulee], effectif_max_avertissement: int
) -> list[str]:
    erreurs = (
        _verifier_bornes_attributs(monde)
        + _verifier_references_club(monde)
        + _verifier_effectifs_clubs_actifs(monde)
        + _verifier_nombre_clubs_par_competition(monde, competitions_simulees)
    )
    if erreurs:
        raise ImportInvalide(erreurs)
    return _avertissements(monde, effectif_max_avertissement)


def _verifier_bornes_attributs(monde: Monde) -> list[str]:
    erreurs: list[str] = []
    for joueur in monde.joueurs.values():
        for nom in NOMS_ATTRIBUTS:
            valeur = joueur.attributs.valeur(nom)
            if not (1 <= valeur <= 100):
                erreurs.append(f"joueur {joueur.id}: attribut {nom}={valeur} hors de [1, 100]")
    return erreurs


def _verifier_references_club(monde: Monde) -> list[str]:
    return [
        f"joueur {joueur.id}: club_id {joueur.club_id} introuvable"
        for joueur in monde.joueurs.values()
        if joueur.club_id is not None and joueur.club_id not in monde.clubs
    ]


def _effectifs_par_club(monde: Monde) -> dict[int, list]:
    effectifs: dict[int, list] = {}
    for joueur in monde.joueurs.values():
        if joueur.club_id is not None:
            effectifs.setdefault(joueur.club_id, []).append(joueur)
    return effectifs


def _verifier_effectifs_clubs_actifs(monde: Monde) -> list[str]:
    erreurs: list[str] = []
    effectifs = _effectifs_par_club(monde)
    for club in monde.clubs.values():
        if club.statut is not StatutClub.ACTIF:
            continue
        joueurs_club = effectifs.get(club.id, [])
        if len(joueurs_club) < _EFFECTIF_MIN_CLUB_ACTIF:
            erreurs.append(
                f"club actif {club.id} ({club.nom}): {len(joueurs_club)} joueurs sous contrat, "
                f"minimum {_EFFECTIF_MIN_CLUB_ACTIF}"
            )
        if not any(joueur.poste is Poste.GB for joueur in joueurs_club):
            erreurs.append(f"club actif {club.id} ({club.nom}): aucun gardien")
    return erreurs


def _verifier_nombre_clubs_par_competition(
    monde: Monde, competitions_simulees: list[CompetitionSimulee]
) -> list[str]:
    comptage: dict[int, int] = {}
    for club in monde.clubs.values():
        if club.statut is StatutClub.ACTIF:
            comptage[club.competition_id] = comptage.get(club.competition_id, 0) + 1

    erreurs = []
    for competition in competitions_simulees:
        trouve = comptage.get(competition.division_id, 0)
        if trouve != competition.nb_clubs:
            erreurs.append(
                f"competition {competition.nom} ({competition.pays}): {trouve} clubs actifs, "
                f"attendu {competition.nb_clubs}"
            )
    return erreurs


def _avertissements(monde: Monde, effectif_max_avertissement: int) -> list[str]:
    avertissements: list[str] = []
    effectifs = _effectifs_par_club(monde)

    masses: dict[int, int] = {}
    for joueur in monde.joueurs.values():
        if joueur.club_id is not None and joueur.contrat is not None:
            masses[joueur.club_id] = masses.get(joueur.club_id, 0) + joueur.contrat.salaire_hebdo

    for club in monde.clubs.values():
        if club.statut is not StatutClub.ACTIF:
            continue
        nb_joueurs = len(effectifs.get(club.id, []))
        if nb_joueurs > effectif_max_avertissement:
            avertissements.append(
                f"club actif {club.id} ({club.nom}): {nb_joueurs} joueurs, "
                f"au-dessus de {effectif_max_avertissement}"
            )
        masse = masses.get(club.id, 0)
        if masse > club.masse_salariale_max:
            avertissements.append(
                f"club actif {club.id} ({club.nom}): masse salariale {masse} au-dessus "
                f"du plafond {club.masse_salariale_max}"
            )
    return avertissements
