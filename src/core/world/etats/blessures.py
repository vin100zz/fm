"""Injuries: gravity draw, out-of-match occurrence, and effects on
return. See "Blessures" in docs/etats-joueur.md.

In-match occurrence is not modeled yet: the documented formula is
per-possession, but with no substitution mechanism (AIController,
step 7) an in-match injury would just permanently weaken a side for the
rest of the match exactly like a red card — which misrepresents what an
injury is. Only the daily out-of-match roll (independent of fatigue,
"15 à 20% des blessures" per docs) is implemented for now.
"""

from random import Random

from core.config.modeles.etats import BlessuresConfig
from core.config.modeles.racine import Config
from core.domain.date import Date
from core.domain.etat_joueur import Blessure, Gravite
from core.domain.joueur import Joueur


def tirer_blessure(date_debut: Date, cfg: BlessuresConfig, rng: Random) -> Blessure:
    roulette = rng.random()
    cumul = 0.0
    gravite_choisie = cfg.gravites[-1]
    for candidate in cfg.gravites:
        cumul += candidate.part
        if roulette <= cumul:
            gravite_choisie = candidate
            break

    jours = rng.randint(gravite_choisie.jours_min, gravite_choisie.jours_max)
    return Blessure(
        date_debut=date_debut,
        date_fin=date_debut.plus_jours(jours),
        gravite=Gravite(gravite_choisie.nom),
        description=f"blessure {gravite_choisie.nom}",
    )


def evaluer_blessure_hors_match(joueur: Joueur, date_du_jour: Date, cfg: BlessuresConfig, rng: Random) -> bool:
    """No-op if already injured. Returns whether a new injury occurred."""
    if joueur.blessure is not None:
        return False
    if rng.random() < cfg.probabilite_quotidienne_hors_match:
        joueur.blessure = tirer_blessure(date_du_jour, cfg, rng)
        return True
    return False


def retablir(joueur: Joueur, cfg: Config, rng: Random) -> None:
    """Clears the injury and applies its lasting effects — "Effets" in
    docs/etats-joueur.md: fatigue and forme reset low, and a long
    injury past 30 leaves a permanent mark.
    """
    blessure = joueur.blessure
    if blessure is None:
        return

    _appliquer_penalite_permanente_si_applicable(joueur, blessure, cfg, rng)

    joueur.blessure = None
    joueur.fatigue = cfg.etats.fatigue.fatigue_retour_de_blessure
    joueur.forme = cfg.etats.blessures.forme_retour_de_blessure


def _appliquer_penalite_permanente_si_applicable(joueur: Joueur, blessure: Blessure, cfg: Config, rng: Random) -> None:
    penalite = cfg.etats.blessures.penalite_permanente
    duree_jours = blessure.date_debut.jours_jusqua(blessure.date_fin)
    age_a_la_blessure = joueur.date_naissance.age_a(blessure.date_debut)

    if duree_jours < penalite.duree_minimale_jours or age_a_la_blessure < penalite.age_minimal:
        return

    for nom in penalite.attributs_touches:
        points = round(rng.uniform(penalite.points_min, penalite.points_max))
        valeur = joueur.attributs.valeur(nom)
        setattr(joueur.attributs, nom, max(valeur - points, cfg.attributs.bornes.min))
