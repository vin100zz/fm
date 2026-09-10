"""Shared interface for match engines — see "MoteurMatch" in
docs/architecture.md. MoteurAnalytique (core/engine/analytique.py) is
the only implementation until step 5's MoteurPossession.
"""

from random import Random
from typing import Protocol

from core.config.modeles.racine import Config
from core.domain.match import ResultatMatch
from core.engine.equipe import Equipe


class MoteurMatch(Protocol):
    def simuler(self, dom: Equipe, ext: Equipe, cfg: Config, rng: Random) -> ResultatMatch: ...
