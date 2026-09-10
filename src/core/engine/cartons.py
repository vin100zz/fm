"""Card generation on a defensive turnover. See "Cartons" in
docs/etats-joueur.md — the offending player is whoever was most
involved defensively in that zone/couloir (same weighting note_zone
already uses for that phase), not drawn uniformly.
"""

from random import Random

from core.config.modeles.moteur_match import CartonsConfig
from core.domain.geometrie import Couloir, Zone
from core.domain.poste import Poste
from core.engine.equipe import PositionOnze
from core.engine.implication import TablesImplication
from core.engine.selection_joueur import tirer_joueur_implique


def determiner_carton(
    zone: Zone,
    couloir: Couloir,
    onze_defenseur: tuple[PositionOnze, ...],
    tables: TablesImplication,
    cfg: CartonsConfig,
    rng: Random,
) -> tuple[PositionOnze, str] | None:
    # Excludes the goalkeeper: a keeper sent off would leave nobody in
    # goal in this simplified model (no reassigning an outfield player
    # to replace them) — see core/engine/match.py's docstring for the
    # other things left out of this pass.
    onze_sans_gardien = tuple(position for position in onze_defenseur if position.poste is not Poste.GB)
    if not onze_sans_gardien:
        return None
    fauteur = tirer_joueur_implique(onze_sans_gardien, zone, couloir, tables, phase_attaque=False, rng=rng)

    poids_zone = cfg.poids_zone_defense if zone is Zone.DEFENSE else 1.0
    poids_agressivite = 1.0 + cfg.poids_agressivite_tacle * fauteur.joueur.attributs.tacle
    p_rouge = cfg.probabilite_rouge_direct_par_turnover_defensif * poids_zone * poids_agressivite
    p_jaune = cfg.probabilite_jaune_par_turnover_defensif * poids_zone * poids_agressivite

    tirage = rng.random()
    if tirage < p_rouge:
        return fauteur, "rouge"
    if tirage < p_rouge + p_jaune:
        return fauteur, "jaune"
    return None
