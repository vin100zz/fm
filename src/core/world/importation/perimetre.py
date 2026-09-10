"""Active vs dormant: a club is active iff its source Division ID matches
one of config/monde.json -> competitions_simulees. See "Périmètre : actif
et dormant" in docs/modele-donnees.md — division_id, never the free-text
division name, which is ambiguous in the source data.
"""

from core.config.modeles.monde import CompetitionSimulee, ConfigMonde
from core.domain.club import StatutClub


def trouver_competition(division_id: int, cfg_monde: ConfigMonde) -> CompetitionSimulee | None:
    for competition in cfg_monde.competitions_simulees:
        if competition.division_id == division_id:
            return competition
    return None


def determiner_statut(division_id: int, cfg_monde: ConfigMonde) -> StatutClub:
    if trouver_competition(division_id, cfg_monde) is not None:
        return StatutClub.ACTIF
    return StatutClub.DORMANT
