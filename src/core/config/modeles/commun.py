"""Small value shapes shared by several config domains."""

from pydantic import ConfigDict
from pydantic.dataclasses import dataclass

STRICT = ConfigDict(extra="forbid")


@dataclass(frozen=True, slots=True, config=STRICT)
class Plage:
    min: float
    max: float


@dataclass(frozen=True, slots=True, config=STRICT)
class CibleTolerance:
    cible: float
    tolerance: float


@dataclass(frozen=True, slots=True, config=STRICT)
class PalierAge:
    age_min: int
    age_max: int
    facteur: float
