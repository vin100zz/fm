"""Suspensions: card accumulation across a season and match countdown.
See "Suspensions" in docs/etats-joueur.md.
"""

from random import Random

from core.config.modeles.etats import SuspensionsConfig
from core.domain.etat_joueur import Suspension
from core.domain.joueur import Joueur


def decrementer(joueur: Joueur) -> None:
    """Call once per match of the relevant competition, played or not by
    this player — see docs/etats-joueur.md.
    """
    if joueur.suspension is None:
        return
    restant = joueur.suspension.matches_restants - 1
    joueur.suspension = None if restant <= 0 else Suspension(matches_restants=restant, motif=joueur.suspension.motif)


def enregistrer_jaune(joueur: Joueur, cfg: SuspensionsConfig) -> None:
    joueur.cartons_jaunes_saison += 1
    for seuil in cfg.seuils_cumul_jaunes:
        if joueur.cartons_jaunes_saison == seuil.jaunes:
            joueur.suspension = Suspension(matches_restants=seuil.matches, motif=f"cumul de {seuil.jaunes} jaunes")


def enregistrer_rouge(joueur: Joueur, deuxieme_jaune: bool, cfg: SuspensionsConfig, rng: Random) -> None:
    if deuxieme_jaune:
        joueur.suspension = Suspension(matches_restants=cfg.matches_double_jaune, motif="deuxieme jaune")
    else:
        matches = rng.randint(cfg.matches_rouge_min, cfg.matches_rouge_max)
        joueur.suspension = Suspension(matches_restants=matches, motif="rouge directe")


def reinitialiser_saison(joueur: Joueur, cfg: SuspensionsConfig) -> None:
    if cfg.remise_a_zero_fin_saison:
        joueur.cartons_jaunes_saison = 0
