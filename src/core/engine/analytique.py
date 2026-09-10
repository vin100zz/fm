"""Reference oracle (docs/moteur-match.md): attack/defense force ->
expected goals -> independent Poisson draw per team. No events, no
per-player stats — see StatsEquipe. Also the fast mode for mass-simulating
competitions nobody is watching.
"""

import math
from random import Random

from core.config.modeles.moteur_match import AnalytiqueConfig
from core.config.modeles.racine import Config
from core.domain.match import ResultatMatch, StatsEquipe
from core.engine.equipe import Equipe


class MoteurAnalytique:
    def simuler(self, dom: Equipe, ext: Equipe, cfg: Config, rng: Random) -> ResultatMatch:
        cfg_analytique = cfg.moteur.analytique

        lambda_dom = _buts_attendus(
            dom.force_attaque, ext.force_defense, cfg_analytique.bonus_domicile_buts, cfg_analytique
        )
        lambda_ext = _buts_attendus(ext.force_attaque, dom.force_defense, 0.0, cfg_analytique)

        return ResultatMatch(
            buts_dom=_tirage_poisson(lambda_dom, rng),
            buts_ext=_tirage_poisson(lambda_ext, rng),
            evenements=[],
            stats_dom=StatsEquipe(),
            stats_ext=StatsEquipe(),
            notes={},
        )


def _buts_attendus(
    force_attaque: float, force_defense_adverse: float, bonus_domicile: float, cfg: AnalytiqueConfig
) -> float:
    brut = (
        cfg.buts_attendus_base
        + cfg.sensibilite_ecart_force * (force_attaque - force_defense_adverse)
        + bonus_domicile
    )
    return max(brut, cfg.buts_attendus_min)


def _tirage_poisson(lam: float, rng: Random) -> int:
    """Knuth's algorithm: exact, and fine for the small lambda (<10)
    football expected-goal counts stay in. Only draws from `rng` — never
    the global random module, see CLAUDE.md "Déterminisme".
    """
    seuil = math.exp(-lam)
    k = 0
    produit = 1.0
    while True:
        produit *= rng.random()
        if produit <= seuil:
            return k
        k += 1
