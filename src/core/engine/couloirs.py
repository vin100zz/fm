"""Couloir choice (softmax on force differential, never uniform) and
mid-progression wing switches. See "Choix du couloir" in
docs/moteur-match.md.
"""

import math
from random import Random

from core.config.modeles.moteur_match import CouloirsMoteurConfig
from core.domain.geometrie import COULOIRS_ORDONNES, Couloir
from core.engine.selection_joueur import tirage_pondere

_VOISINS: dict[Couloir, tuple[Couloir, ...]] = {
    Couloir.GAUCHE: (Couloir.AXE,),
    Couloir.AXE: (Couloir.GAUCHE, Couloir.DROITE),
    Couloir.DROITE: (Couloir.AXE,),
}


def choisir_couloir(
    notes_attaque_zone: dict[Couloir, float],
    notes_defense_zone: dict[Couloir, float],
    cfg: CouloirsMoteurConfig,
    rng: Random,
) -> Couloir:
    poids = {
        couloir: math.exp(cfg.beta_softmax * (notes_attaque_zone[couloir] - notes_defense_zone[couloir]))
        for couloir in COULOIRS_ORDONNES
    }
    return tirage_pondere(poids, rng)


def _probabilite_changement_aile(vision_moyenne: float, cfg: CouloirsMoteurConfig) -> float:
    """No exact formula in docs/moteur-match.md beyond "pondérée par la
    vision" — this centers the configured base rate on a neutral vision
    of 50 (the midpoint of the 1-100 scale) and nudges it by
    `poids_vision_changement_aile` per point of average vision above
    or below that.
    """
    return cfg.probabilite_changement_aile + cfg.poids_vision_changement_aile * (vision_moyenne - 50.0)


def peut_changer_aile(couloir: Couloir, vision_moyenne: float, cfg: CouloirsMoteurConfig, rng: Random) -> Couloir:
    if rng.random() < _probabilite_changement_aile(vision_moyenne, cfg):
        return rng.choice(_VOISINS[couloir])
    return couloir
