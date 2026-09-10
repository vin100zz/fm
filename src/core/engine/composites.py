"""Attribute -> composite, per docs/attributs.md. Zone-aggregated
composites (progression_*, occasion_*) feed notes_zones.py; the
individual ones (tir, arret, tete, sortie) are read directly in
occasion.py — "un agrégat, un buteur à 90 de finition disparaît dans la
moyenne", so those are never averaged across a zone.
"""

from core.config.modeles.attributs import ConfigAttributs
from core.domain.attributs import combinaison_ponderee
from core.domain.joueur import Joueur
from core.domain.poste import Poste

# Which implication table (attaque/defense) weights a given zone-aggregated
# composite — structural, not a tunable number, so it stays in code (see
# "Ce qui reste dans le code" in docs/configuration.md).
PHASE_EST_OFFENSIVE = {
    "progression_attaque": True,
    "progression_defense": False,
    "occasion_attaque": True,
    "occasion_defense": False,
}


def composite(joueur: Joueur, nom_composite: str, cfg: ConfigAttributs) -> float:
    return combinaison_ponderee(joueur.attributs, cfg.composites[nom_composite])


def malus_hors_poste(joueur: Joueur, poste_joue: Poste, cfg: ConfigAttributs) -> float:
    affinite = 1.0 if joueur.poste is poste_joue else joueur.postes_secondaires.get(poste_joue, 0.0)
    return cfg.malus_hors_poste.base + cfg.malus_hors_poste.facteur * affinite
