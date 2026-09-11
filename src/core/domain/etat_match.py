"""Live match state exposed to ClubController.decider_remplacement — see
CLAUDE.md and "Décision de remplacement (IA)" in docs/etats-joueur.md.
"""

from dataclasses import dataclass

from core.domain.joueur import Joueur


@dataclass(frozen=True, slots=True)
class EtatMatch:
    minute: int
    buts_pour: int
    buts_contre: int
    onze_actuel: tuple[Joueur, ...]
    banc: tuple[Joueur, ...]
    remplacements_effectues: int
