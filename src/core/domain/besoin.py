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
    # renseigne seulement pour un MANQUE : le niveau que doit atteindre un
    # candidat pour combler ce besoin (voir core.world.mercato._meilleur_candidat,
    # 2026-09-11 — critere d'acceptation direct, plutot que de ne dependre
    # que du delta d'utilite sur le meilleur onze, bruite par l'affectation
    # gloutonne de core.engine.equipe.meilleure_affectation).
    niveau_attendu: float = 0.0
