"""A range with a midpoint — used wherever the true value is hidden and
only a noisy estimate is exposed (potentiel — see
docs/progression-demographie.md — and, downstream, valorisation).
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Fourchette:
    min: float
    max: float

    @property
    def milieu(self) -> float:
        return (self.min + self.max) / 2
