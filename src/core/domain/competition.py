from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.domain.match import Journee


@dataclass(slots=True)
class Competition:
    id: int
    nom: str
    pays: str
    niveau: int
    club_ids: list[int]
    # Empty until the fixture list is generated — not part of step 2
    # (import); see Competition.generer_calendrier in docs/architecture.md.
    calendrier: list["Journee"] = field(default_factory=list)
    # Toujours le calendrier CETTE saison — remplacé, pas complété, quand
    # core/world/saison.py relance une nouvelle édition. Independent per
    # competition : Ligue 1 (18 clubs, 34 journées) et La Liga (20, 38)
    # ne terminent pas le même jour.
    saison_actuelle: int = 1
