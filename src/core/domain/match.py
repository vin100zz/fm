"""Match and match-result shapes — see docs/modele-donnees.md and
docs/moteur-match.md. Evenement is produced by the possession engine
(core/engine/match.py); the analytical engine (core/engine/analytique.py)
leaves evenements empty and StatsEquipe's fields at None.
"""

from dataclasses import dataclass, field
from enum import Enum

from core.domain.date import Date
from core.domain.geometrie import Couloir, Zone


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
    zone: Zone | None
    couloir: Couloir | None
    # Free-text classifier docs/modele-donnees.md doesn't otherwise carry a
    # field for — "jaune"/"rouge" for TypeEvenement.CARTON, "corner"/
    # "coup_franc" for a set piece, "contre" for a break. Kept generic
    # rather than a subclass per event type: the engine produces one flat
    # Evenement shape and consumers filter by `type` (and this) as needed.
    detail: str | None = None


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
