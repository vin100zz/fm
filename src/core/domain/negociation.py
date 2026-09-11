"""An in-progress transfer negotiation, tracked across mercato turns —
see "Boucle de mercato" in docs/ia-gestion.md: "limiter chaque club à 3
négociations actives". Lives on `Monde.negociations`; rebuilt wholesale
each `core/world/mercato.py::tour_mercato` call rather than mutated in
place (short-lived, no need for identity across the rebuild).
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Negociation:
    club_acheteur_id: int
    joueur_id: int
    montant_offert: int
    salaire_propose: int
    tours: int = 0
