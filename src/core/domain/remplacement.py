from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Remplacement:
    joueur_sortant_id: int
    joueur_entrant_id: int
    minute: int
    motif: str
