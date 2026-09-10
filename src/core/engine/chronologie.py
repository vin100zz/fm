"""Possession duration and stoppage time. See "Chronologie" in
docs/moteur-match.md and config/moteur_match.json -> chronologie.
"""

from random import Random

from core.config.modeles.moteur_match import ChronologieConfig


def duree_possession(cfg: ChronologieConfig, rng: Random) -> float:
    """Gamma distribution, mean `duree_possession_moyenne`, shape
    `duree_possession_forme_gamma` — Python's gammavariate takes
    (alpha, beta) with mean = alpha*beta, so beta is derived from the
    two configured numbers rather than stored as a third.
    """
    alpha = cfg.duree_possession_forme_gamma
    beta = cfg.duree_possession_moyenne / alpha
    return rng.gammavariate(alpha, beta)


def temps_additionnel(nb_arrets_de_jeu: int, cfg: ChronologieConfig, rng: Random) -> float:
    base = rng.uniform(cfg.temps_additionnel_min, cfg.temps_additionnel_max)
    return base + nb_arrets_de_jeu * cfg.secondes_par_arret_de_jeu
