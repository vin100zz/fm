"""Forme: a slow mean-reverting random walk driven by the last match
rating. See "Forme" in docs/etats-joueur.md.
"""

from random import Random

from core.config.modeles.etats import FormeConfig
from core.domain.joueur import Joueur


def maj_forme(joueur: Joueur, note_derniere_perf: float, rng: Random, cfg: FormeConfig) -> None:
    cible = 1.0 + cfg.sensibilite_note * (note_derniere_perf - cfg.note_reference)
    joueur.forme += cfg.vitesse_convergence * (cible - joueur.forme) + rng.gauss(0, cfg.bruit_ecart_type)
    joueur.forme = min(max(joueur.forme, cfg.min), cfg.max)
