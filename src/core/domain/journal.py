"""One day's worth of world events for the UI's "journal du jour" —
see "Contrôle du temps" in docs/ui.md. Transfers aren't produced yet:
no mercato loop exists (docs/ia-gestion.md's own "hors périmètre" note).
"""

from dataclasses import dataclass
from enum import Enum


class TypeEvenementJour(Enum):
    RESULTAT = "resultat"
    BLESSURE = "blessure"
    FIN_DE_SAISON = "fin_de_saison"
    TRANSFERT = "transfert"


@dataclass(frozen=True, slots=True)
class EvenementJour:
    type: TypeEvenementJour
    description: str
    match_id: int | None = None
    joueur_id: int | None = None
    competition_id: int | None = None
