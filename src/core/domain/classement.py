"""One club's standing row — see "Classement" in docs/ui.md and the
`Competition` Protocol in docs/architecture.md.
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LigneClassement:
    club_id: int
    joues: int
    victoires: int
    nuls: int
    defaites: int
    buts_pour: int
    buts_contre: int
    points: int

    @property
    def difference_buts(self) -> int:
        return self.buts_pour - self.buts_contre
