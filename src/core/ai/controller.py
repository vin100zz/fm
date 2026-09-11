"""ClubController — the single interface every club decision goes
through (CLAUDE.md "Conséquence architecturale du mode observateur").
`AIController` is v1's only implementation; adding user control later
means writing a `HumanController` and swapping the assignment, per
CLAUDE.md — no business code should ever test "is this the user's club".

CLAUDE.md's sketch (`choisir_composition(self, club, match) -> Composition`,
etc.) is a shorthand: there is no `Composition` type, and the real
selection/remplacement/mercato functions need more context (the
opposing club, whether at home, the current effectif) than a bare
`club`/`match` pair carries. The Protocol below takes the concrete
parameters those functions actually need instead.
"""

from random import Random
from typing import Protocol

from core.ai.besoins import evaluer_besoins
from core.ai.mercato import repondre_offre as _repondre_offre
from core.ai.mercato import score_offre as _score_offre
from core.ai.selection import choisir_composition as _choisir_composition
from core.ai.selection import decider_remplacement as _decider_remplacement
from core.config.modeles.racine import Config
from core.domain.besoin import Besoin
from core.domain.club import Club
from core.domain.date import Date
from core.domain.etat_match import EtatMatch
from core.domain.joueur import Joueur
from core.domain.offre import Offre, Reponse
from core.domain.remplacement import Remplacement
from core.engine.equipe import Equipe


class ClubController(Protocol):
    def choisir_composition(
        self, club: Club, effectif: list[Joueur], adversaire: Club, domicile: bool, cfg: Config
    ) -> Equipe: ...

    def decider_remplacement(
        self, etat: EtatMatch, joueurs_avertis: frozenset[int], remplacements_max: int, cfg: Config
    ) -> Remplacement | None: ...

    def evaluer_besoins(self, club: Club, effectif: list[Joueur], cfg: Config) -> list[Besoin]: ...

    def repondre_offre(
        self, offre: Offre, club: Club, joueur: Joueur, effectif: list[Joueur], date_actuelle: Date, cfg: Config
    ) -> Reponse: ...

    def score_offre(
        self,
        joueur: Joueur,
        club: Club,
        salaire_propose: int,
        effectif_cible: list[Joueur],
        date_actuelle: Date,
        cfg: Config,
        rng: Random,
    ) -> float: ...


class AIController:
    """Stateless: every decision is a pure function of the arguments
    passed in, so one instance can be shared by all 96 clubs.
    """

    def choisir_composition(
        self, club: Club, effectif: list[Joueur], adversaire: Club, domicile: bool, cfg: Config
    ) -> Equipe:
        return _choisir_composition(club, effectif, adversaire, domicile, cfg)

    def decider_remplacement(
        self, etat: EtatMatch, joueurs_avertis: frozenset[int], remplacements_max: int, cfg: Config
    ) -> Remplacement | None:
        return _decider_remplacement(etat, joueurs_avertis, remplacements_max, cfg)

    def evaluer_besoins(self, club: Club, effectif: list[Joueur], cfg: Config) -> list[Besoin]:
        return evaluer_besoins(club, effectif, cfg)

    def repondre_offre(
        self, offre: Offre, club: Club, joueur: Joueur, effectif: list[Joueur], date_actuelle: Date, cfg: Config
    ) -> Reponse:
        return _repondre_offre(offre, club, joueur, effectif, date_actuelle, cfg)

    def score_offre(
        self,
        joueur: Joueur,
        club: Club,
        salaire_propose: int,
        effectif_cible: list[Joueur],
        date_actuelle: Date,
        cfg: Config,
        rng: Random,
    ) -> float:
        return _score_offre(joueur, club, salaire_propose, effectif_cible, date_actuelle, cfg, rng)
