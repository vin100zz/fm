"""Weighted random draws: the primitive behind couloir choice, shooter
selection, header-target selection, and corner receivers. See
docs/moteur-match.md.

Player draws key on the *index* into `onze`, not the PositionOnze or
Joueur itself — Joueur is a mutable (unfrozen) dataclass, so it isn't
hashable, and can't be used as a dict key for a weighted draw.
"""

from random import Random
from typing import TypeVar

from core.domain.geometrie import Couloir, Zone
from core.engine.equipe import PositionOnze
from core.engine.implication import TablesImplication

T = TypeVar("T")


def tirage_pondere(poids: dict[T, float], rng: Random) -> T:
    elements = list(poids)
    valeurs = list(poids.values())
    total = sum(valeurs)
    if total <= 0:
        return rng.choice(elements)

    seuil = rng.uniform(0, total)
    cumul = 0.0
    for element, poids_element in zip(elements, valeurs, strict=True):
        cumul += poids_element
        if seuil <= cumul:
            return element
    return elements[-1]  # floating-point safety net


def tirer_joueur_implique(
    onze: tuple[PositionOnze, ...],
    zone: Zone,
    couloir: Couloir,
    tables: TablesImplication,
    phase_attaque: bool,
    rng: Random,
) -> PositionOnze:
    """Weighted by each player's implication in this zone/couloir — used
    to pick the crosser, the shooter, and (in a different zone/couloir)
    who made the last defensive contribution before a card.
    """
    poids = {
        index: tables.implication(position.poste, zone, couloir, phase_attaque)
        for index, position in enumerate(onze)
    }
    return onze[tirage_pondere(poids, rng)]


def tirer_joueur_par_attribut(onze: tuple[PositionOnze, ...], nom_attribut: str, rng: Random) -> PositionOnze:
    """Weighted by a single attribute across the whole onze — used for the
    header target on a cross and for corner/free-kick receivers
    (docs: "tiré parmi tout le onze, pondéré par jeu_tete").
    """
    poids = {index: max(position.joueur.attributs.valeur(nom_attribut), 0.0) for index, position in enumerate(onze)}
    return onze[tirage_pondere(poids, rng)]
