"""Name pools and identity draws for generated players — "6. Identité"
in docs/progression-demographie.md. No name-list data file was ever
provided (only data/clubs.csv and data/players.csv exist, see
docs/modele-donnees.md), so pools are built from the (nom, prenom,
nationalite) triples already present in the imported population —
this doubles as a realistic per-nation name distribution for free.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from random import Random
from typing import Iterable

from core.domain.joueur import Joueur


@dataclass(frozen=True, slots=True)
class PoolsNoms:
    par_nation: dict[str, list[tuple[str, str]]] = field(default_factory=dict)
    # (nationalite, nom, prenom) triples for every nation outside the
    # simulated 5 — the abstract "vivier extérieur" draws a nation and a
    # name together, so the pair always stays realistic.
    exterieur: list[tuple[str, str, str]] = field(default_factory=list)


def construire_pools_noms(population: Iterable[Joueur], nationalites_simulees: frozenset[str]) -> PoolsNoms:
    par_nation: dict[str, list[tuple[str, str]]] = defaultdict(list)
    exterieur: list[tuple[str, str, str]] = []
    for joueur in population:
        if not joueur.nom:
            continue
        if joueur.nationalite in nationalites_simulees:
            par_nation[joueur.nationalite].append((joueur.nom, joueur.prenom))
        else:
            exterieur.append((joueur.nationalite, joueur.nom, joueur.prenom))
    return PoolsNoms(par_nation=dict(par_nation), exterieur=exterieur)


def tirer_identite(
    nationalite_cible: str | None,
    pools: PoolsNoms,
    deja_utilises: frozenset[tuple[str, str]],
    rng: Random,
    tentatives_max: int,
) -> tuple[str, str, str]:
    """Returns (nationalite, nom, prenom). `nationalite_cible` is `None`
    or unknown to `pools` for the vivier extérieur — the nation drawn
    there comes from the name pool itself, not from the caller.

    Redraws on a (nom, prenom) collision with `deja_utilises` ("vérifier
    l'unicité... retirer en cas de collision") up to `tentatives_max`
    times, then accepts the last draw regardless — a genuine collision
    across a population in the thousands is vanishingly rare and not
    worth blocking generation over. `deja_utilises` is never mutated
    here: a caller generating several players in one batch must fold
    each result back in before the next call.
    """
    candidat = _tirer_un(nationalite_cible, pools, rng)
    for _ in range(tentatives_max):
        if (candidat[1], candidat[2]) not in deja_utilises:
            return candidat
        candidat = _tirer_un(nationalite_cible, pools, rng)
    return candidat


def _tirer_un(nationalite_cible: str | None, pools: PoolsNoms, rng: Random) -> tuple[str, str, str]:
    if nationalite_cible is not None and nationalite_cible in pools.par_nation:
        nom, prenom = rng.choice(pools.par_nation[nationalite_cible])
        return nationalite_cible, nom, prenom
    return rng.choice(pools.exterieur)
