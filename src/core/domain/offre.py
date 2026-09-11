"""A transfer offer and a selling club's response — see "Réponse du
vendeur" in docs/ia-gestion.md.
"""

from dataclasses import dataclass
from enum import Enum


@dataclass(frozen=True, slots=True)
class Offre:
    joueur_id: int
    club_acheteur_id: int
    montant: int
    salaire_propose: int


class TypeReponse(Enum):
    ACCEPTE = "accepte"
    CONTRE_OFFRE = "contre_offre"
    REFUSE = "refuse"


@dataclass(frozen=True, slots=True)
class Reponse:
    type: TypeReponse
    contre_montant: int | None = None
