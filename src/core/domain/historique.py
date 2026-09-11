"""Long-lived records that outlive a season. See "Historique et
volumétrie" in docs/modele-donnees.md.

`transferts` from step 2 onward, `palmares` from the end-of-season
rollover (`core/world/saison.py`) — added exactly as the module
docstring anticipated: a local, additive change, not a redesign.
`trajectoires_attributs` still isn't produced by anything.
`SaisonTerminee` only records the champion and final table, not a
season's top scorer/passer — nothing aggregates per-player match
events across a season yet (see docs/ui.md).
"""

from dataclasses import dataclass, field

from core.domain.classement import LigneClassement
from core.domain.date import Date


@dataclass(frozen=True, slots=True)
class TransfertHistorique:
    date: Date
    joueur_id: int
    club_source_id: int | None
    club_cible_id: int | None
    montant: int


@dataclass(frozen=True, slots=True)
class SaisonTerminee:
    competition_id: int
    saison: int
    classement_final: list[LigneClassement]

    @property
    def champion_id(self) -> int:
        return self.classement_final[0].club_id


@dataclass(slots=True)
class Historique:
    transferts: list[TransfertHistorique] = field(default_factory=list)
    palmares: list[SaisonTerminee] = field(default_factory=list)
