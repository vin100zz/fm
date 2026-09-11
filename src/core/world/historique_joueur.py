"""Per-season career summary for one player — matches played, goals,
average rating, and the transfer fee that brought them to each club, if
any. See "Historique" in the Joueur screen of docs/ui.md.

Computed on demand from `Monde.matches` + `Historique.transferts`
rather than maintained incrementally — nothing else needs "which club
did this player play for on date X". `Monde.matches` keeps every match
ever played (no purge, see its own module's absence of one), so this is
O(every match ever played in the save) per call: fine at the scale a
save reaches in a handful of seasons, worth an index from
joueur_id -> match ids if it's ever measured otherwise.
"""

from core.domain.date import Date
from core.domain.historique import LigneHistoriqueJoueur, TransfertHistorique
from core.domain.match import TypeEvenement
from core.domain.monde import Monde


def historique_saisons(joueur_id: int, monde: Monde) -> list[LigneHistoriqueJoueur]:
    joueur = monde.joueurs.get(joueur_id)
    if joueur is None:
        return []

    transferts_joueur = sorted(
        (t for t in monde.historique.transferts if t.joueur_id == joueur_id), key=lambda t: t.date
    )

    groupes: dict[tuple[int, int | None], dict] = {}
    for match in monde.matches.values():
        if match.resultat is None:
            continue
        note = match.resultat.notes.get(joueur_id)
        if note is None:
            continue  # ce joueur n'a pas participe a ce match

        club_id = _club_a_la_date(joueur.club_id, transferts_joueur, match.date)
        cle = (match.saison, club_id)
        groupe = groupes.setdefault(cle, {"matches": 0, "buts": 0, "somme_notes": 0.0, "date_min": match.date})
        groupe["matches"] += 1
        groupe["somme_notes"] += note
        groupe["buts"] += sum(
            1 for e in match.resultat.evenements if e.type is TypeEvenement.BUT and e.joueur_id == joueur_id
        )
        if match.date < groupe["date_min"]:
            groupe["date_min"] = match.date

    groupes_tries = sorted(groupes.items(), key=lambda item: (-item[0][0], item[1]["date_min"]))

    return [
        LigneHistoriqueJoueur(
            saison=saison, club_id=club_id, matches_joues=stats["matches"], buts=stats["buts"],
            note_moyenne=round(stats["somme_notes"] / stats["matches"], 1),
            prix_transfert=next(
                (t.montant for t in transferts_joueur if t.saison == saison and t.club_cible_id == club_id), None
            ),
        )
        for (saison, club_id), stats in groupes_tries
    ]


def _club_a_la_date(club_actuel: int | None, transferts_joueur: list[TransfertHistorique], date: Date) -> int | None:
    """Reconstructs which club a player belonged to on a past `date`,
    from their transfer history plus their *current* club_id — the
    only two things `Monde` actually persists about a player's club
    affiliation over time (no per-match roster is stored). Walking the
    player's transfers from most recent to oldest: `date` is on the far
    side of a transfer (before it happened) exactly when it's earlier
    than that transfer's date, in which case the player was still at
    `club_source_id` — and the transfer before that (if any) refines it
    further back, and so on until `date` lands after some transfer (or
    there are none left, meaning `date` predates the player's very
    first tracked transfer and this is as far back as it goes).
    """
    club_id = club_actuel
    for transfert in reversed(transferts_joueur):
        if date >= transfert.date:
            break
        club_id = transfert.club_source_id
    return club_id
