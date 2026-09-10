"""Match and match-result shapes. Only the parts modele-donnees.md
already specifies precisely — the Evenement hierarchy and the exact
StatsEquipe fields are a step-3 (moteur de match) concern and will
firm up then; nothing in step 2 constructs any of these, they only
exist so Competition/Monde can be typed per docs/modele-donnees.md.
"""

from dataclasses import dataclass, field
from enum import Enum

from core.domain.date import Date


@dataclass(slots=True)
class Journee:
    numero: int
    match_ids: list[int] = field(default_factory=list)


class TypeEvenement(Enum):
    BUT = "but"
    TIR = "tir"
    ARRET = "arret"
    CARTON = "carton"
    BLESSURE = "blessure"
    REMPLACEMENT = "remplacement"


@dataclass(frozen=True, slots=True)
class Evenement:
    minute: int
    type: TypeEvenement
    joueur_id: int
    joueur_secondaire_id: int | None
    zone: str | None
    couloir: str | None


@dataclass(frozen=True, slots=True)
class StatsEquipe:
    """All fields optional: the analytical engine (step 3) only produces a
    score, none of this detail — see docs/moteur-match.md. The possession
    engine (step 5) always fills every field.
    """

    tirs: int | None = None
    xg: float | None = None
    possession_pct: float | None = None
    corners: int | None = None
    cartons_jaunes: int | None = None
    cartons_rouges: int | None = None


@dataclass(frozen=True, slots=True)
class ResultatMatch:
    buts_dom: int
    buts_ext: int
    evenements: list[Evenement]
    stats_dom: StatsEquipe
    stats_ext: StatsEquipe
    notes: dict[int, float]  # joueur_id -> note 1-10


@dataclass(slots=True)
class Match:
    id: int
    competition_id: int
    journee: int
    date: Date
    domicile_id: int
    exterieur_id: int
    resultat: ResultatMatch | None = None
