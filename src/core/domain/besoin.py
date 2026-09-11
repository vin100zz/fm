"""What ClubController.evaluer_besoins returns — see CLAUDE.md and
"Profil cible et besoins" in docs/ia-gestion.md: a club's squad
compared to its target profile produces under-staffed postes (MANQUE)
and surplus players (SURPLUS), ranked lists a mercato AI acts on.
"""

from dataclasses import dataclass
from enum import Enum

from core.domain.poste import Poste


class TypeBesoin(Enum):
    MANQUE = "manque"
    SURPLUS = "surplus"


@dataclass(frozen=True, slots=True)
class Besoin:
    type: TypeBesoin
    poste: Poste
    urgence: float  # ecart au profil pour un manque ; utilite negative pour un surplus
    joueur_id: int | None = None  # renseigne seulement pour un SURPLUS : le joueur concerne
