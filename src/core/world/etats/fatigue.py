"""Fatigue: in-match consumption and between-match recovery. See
"Fatigue" in docs/etats-joueur.md.
"""

from core.config.modeles.etats import FatigueConfig
from core.domain.date import Date
from core.domain.joueur import Joueur


def consommer(joueur: Joueur, minutes: float, intensite: float, cfg: FatigueConfig) -> None:
    base = cfg.consommation_par_minute * minutes
    resistance = cfg.resistance_base + cfg.resistance_facteur_endurance * (joueur.attributs.endurance / 100)
    joueur.fatigue = max(joueur.fatigue - base * intensite / resistance, cfg.min)


def recuperer(joueur: Joueur, jours: float, date_actuelle: Date, cfg: FatigueConfig) -> None:
    age = joueur.date_naissance.age_a(date_actuelle)
    if age < cfg.seuil_age_jeune:
        facteur_age = cfg.facteur_age_jeune
    elif age > cfg.seuil_age_vieux:
        facteur_age = cfg.facteur_age_vieux
    else:
        facteur_age = 1.0

    vitesse = cfg.recuperation_base_par_jour + cfg.recuperation_facteur_endurance * (joueur.attributs.endurance / 100)
    joueur.fatigue = min(joueur.fatigue + jours * vitesse * facteur_age, cfg.max)
