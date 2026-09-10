"""Cap active-club squads at config/ia_gestion.json ->
garde_fous.effectif_max, keeping the best players by note_globale.

Requested explicitly: the source data mixes first-team and
reserve/academy squads, so an active club can show 70+ contracted
players (see the "effectifs actifs" note in docs/modele-donnees.md).
Cut players are not discarded — they stay in monde.joueurs, just
released to free agency (club_id/contrat cleared), the same state a
real out-of-contract player would be in.
"""

from core.config.modeles.attributs import ConfigAttributs
from core.domain.club import Club, StatutClub
from core.domain.joueur import Joueur
from core.world.note_globale import note_globale


def limiter_effectifs_actifs(
    joueurs: dict[int, Joueur], clubs: dict[int, Club], cfg_attributs: ConfigAttributs, effectif_max: int
) -> list[str]:
    avertissements: list[str] = []

    par_club: dict[int, list[Joueur]] = {}
    for joueur in joueurs.values():
        if joueur.club_id is not None:
            par_club.setdefault(joueur.club_id, []).append(joueur)

    for club_id, effectif in par_club.items():
        club = clubs.get(club_id)
        if club is None or club.statut is not StatutClub.ACTIF or len(effectif) <= effectif_max:
            continue

        effectif.sort(key=lambda joueur: note_globale(joueur, cfg_attributs), reverse=True)
        excedent = effectif[effectif_max:]
        for joueur in excedent:
            joueur.club_id = None
            joueur.contrat = None

        avertissements.append(
            f"club actif {club_id} ({club.nom}): effectif reduit de {len(effectif)} a "
            f"{effectif_max}, {len(excedent)} joueur(s) passes agent libre"
        )
    return avertissements
