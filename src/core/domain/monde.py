from dataclasses import dataclass, field

from core.domain.club import Club
from core.domain.competition import Competition
from core.domain.date import Date
from core.domain.historique import Historique
from core.domain.joueur import Joueur
from core.domain.match import Match


@dataclass(slots=True)
class Monde:
    date: Date
    saison: int
    graine: int
    joueurs: dict[int, Joueur]
    clubs: dict[int, Club]
    competitions: dict[int, Competition]
    historique: Historique
    prochain_id: int
    matches: dict[int, Match] = field(default_factory=dict)
