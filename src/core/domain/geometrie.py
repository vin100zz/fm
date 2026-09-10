"""The pitch geometry the possession engine reasons about. See
docs/moteur-match.md. Fixed in code for the same reason as Poste (see
poste.py): the engine indexes on this exact set, and
core/config/coherence.py checks every config file agrees with it,
**in this exact order** — implications.json's per-poste vectors are
positional, not keyed.
"""

from enum import Enum


class Zone(Enum):
    DEFENSE = "DEFENSE"
    MILIEU_BAS = "MILIEU_BAS"
    MILIEU_HAUT = "MILIEU_HAUT"
    VERITE = "VERITE"


class Couloir(Enum):
    GAUCHE = "GAUCHE"
    AXE = "AXE"
    DROITE = "DROITE"


ZONES_ORDONNEES: tuple[Zone, ...] = (Zone.DEFENSE, Zone.MILIEU_BAS, Zone.MILIEU_HAUT, Zone.VERITE)
COULOIRS_ORDONNES: tuple[Couloir, ...] = (Couloir.GAUCHE, Couloir.AXE, Couloir.DROITE)


def zone_suivante(zone: Zone) -> Zone:
    index = ZONES_ORDONNEES.index(zone)
    return ZONES_ORDONNEES[index + 1]
