"""Ties a simulated match's ResultatMatch back onto the persistent
Joueur state (forme, fatigue, suspensions). The engine never mutates a
Joueur directly — see "Mutation du monde" in docs/architecture.md — so
this is the applicateur for match results specifically.

Per-player minutes played aren't tracked (core/engine/match.py), so
fatigue consumption assumes the full nominal match duration for every
player who started, including one sent off early. Suspension
countdown for a whole squad after each of its club's matches (docs:
"décrémenté... joué ou non") needs a season calendar to drive it —
not built yet — so only card-driven suspensions are handled here;
`core.world.etats.suspensions.decrementer` is ready to be called once
that calendar loop exists.
"""

from random import Random

from core.config.modeles.racine import Config
from core.domain.joueur import Joueur
from core.domain.match import ResultatMatch, TypeEvenement
from core.world.etats import fatigue, forme, suspensions


def appliquer_resultat_match(resultat: ResultatMatch, joueurs: dict[int, Joueur], cfg: Config, rng: Random) -> None:
    minutes = cfg.moteur.chronologie.duree_match_secondes / 60
    intensite_neutre = cfg.etats.fatigue.intensite_par_hauteur_bloc.equilibre

    for joueur_id, note in resultat.notes.items():
        joueur = joueurs.get(joueur_id)
        if joueur is None:
            continue
        fatigue.consommer(joueur, minutes, intensite_neutre, cfg.etats.fatigue)
        forme.maj_forme(joueur, note, rng, cfg.etats.forme)

    for evenement in resultat.evenements:
        if evenement.type is not TypeEvenement.CARTON:
            continue
        joueur = joueurs.get(evenement.joueur_id)
        if joueur is None:
            continue
        _appliquer_carton(joueur, evenement.detail, cfg, rng)


def _appliquer_carton(joueur: Joueur, detail: str | None, cfg: Config, rng: Random) -> None:
    cfg_suspensions = cfg.etats.suspensions
    if detail == "jaune":
        suspensions.enregistrer_jaune(joueur, cfg_suspensions)
    elif detail == "rouge_directe":
        suspensions.enregistrer_rouge(joueur, deuxieme_jaune=False, cfg=cfg_suspensions, rng=rng)
    elif detail == "rouge_deuxieme_jaune":
        # Two real yellow cards were shown (see core/engine/match.py) —
        # both count toward the season cumul, even though the net
        # effect is a sending-off.
        suspensions.enregistrer_jaune(joueur, cfg_suspensions)
        suspensions.enregistrer_rouge(joueur, deuxieme_jaune=True, cfg=cfg_suspensions, rng=rng)
