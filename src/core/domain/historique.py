"""Long-lived records that outlive a season. See "Historique et
volumétrie" in docs/modele-donnees.md.

Only `transferts` is populated from step 2 onward (import can seed it
with nothing, but its shape is fully specified). `palmares` and
`trajectoires_attributs` are added once the features that produce them
(end of season, attribute sampling) exist — adding fields later is a
local, additive change, not a redesign.
"""

from dataclasses import dataclass, field

from core.domain.date import Date


@dataclass(frozen=True, slots=True)
class TransfertHistorique:
    date: Date
    joueur_id: int
    club_source_id: int | None
    club_cible_id: int | None
    montant: int


@dataclass(slots=True)
class Historique:
    transferts: list[TransfertHistorique] = field(default_factory=list)
