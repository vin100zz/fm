"""Fixture generation — the `generer_calendrier` half of the
`Competition` Protocol in docs/architecture.md. Standard round-robin
("méthode du cercle"): one club fixed, the rest rotate one position each
round, giving n-1 rounds for a single round-robin; playing it twice with
home/away swapped gives the aller-retour season.
"""

from random import Random

from core.config.modeles.racine import Config
from core.domain.date import Date
from core.domain.match import Journee, Match


def generer_calendrier(
    club_ids: list[int], competition_id: int, saison: int, premier_match_id: int, date_debut: Date, cfg: Config, rng: Random
) -> tuple[list[Match], list[Journee]]:
    equipes: list[int | None] = list(club_ids)
    rng.shuffle(equipes)  # varie les affiches d'une saison a l'autre
    if len(equipes) % 2 == 1:
        equipes.append(None)  # club impair : un "bye" par journee, pas attendu avec les 5 ligues actuelles

    rondes_aller = _rondes_par_methode_du_cercle(equipes)
    rondes = rondes_aller + [[(exterieur, domicile) for domicile, exterieur in ronde] for ronde in rondes_aller]

    matches: list[Match] = []
    journees: list[Journee] = []
    match_id = premier_match_id
    date_journee = date_debut
    for numero, ronde in enumerate(rondes, start=1):
        ids_journee: list[int] = []
        for domicile, exterieur in ronde:
            if domicile is None or exterieur is None:
                continue
            matches.append(
                Match(id=match_id, competition_id=competition_id, journee=numero, date=date_journee, domicile_id=domicile, exterieur_id=exterieur, saison=saison)
            )
            ids_journee.append(match_id)
            match_id += 1
        journees.append(Journee(numero=numero, match_ids=ids_journee))
        date_journee = date_journee.plus_jours(cfg.monde.saison.jours_entre_journees)

    return matches, journees


def _rondes_par_methode_du_cercle(equipes: list[int | None]) -> list[list[tuple[int | None, int | None]]]:
    n = len(equipes)
    fixe, tournants = equipes[0], equipes[1:]
    rondes: list[list[tuple[int | None, int | None]]] = []

    for numero_ronde in range(n - 1):
        cercle = [fixe] + tournants
        paires = [(cercle[i], cercle[n - 1 - i]) for i in range(n // 2)]
        if numero_ronde % 2 == 1:  # alterne qui recoit pour ne pas figer domicile/exterieur
            paires = [(exterieur, domicile) for domicile, exterieur in paires]
        rondes.append(paires)
        tournants = [tournants[-1]] + tournants[:-1]

    return rondes
