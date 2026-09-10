"""Injury and suspension records. See docs/etats-joueur.md.

Structure only in step 2 (the data model): nothing constructs a Blessure
or a Suspension yet, that happens once match simulation exists (step 6).
"""

from dataclasses import dataclass
from enum import Enum

from core.domain.date import Date


class Gravite(Enum):
    LEGERE = "legere"
    MOYENNE = "moyenne"
    GRAVE = "grave"
    TRES_GRAVE = "tres_grave"


@dataclass(frozen=True, slots=True)
class Blessure:
    date_debut: Date
    date_fin: Date
    gravite: Gravite
    description: str


@dataclass(frozen=True, slots=True)
class Suspension:
    matches_restants: int
    motif: str
