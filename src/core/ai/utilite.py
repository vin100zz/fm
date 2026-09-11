"""Marginal utility: what actually drives transfer/team decisions, not
raw valeur() — see "Utilité marginale" in docs/ia-gestion.md. A club
with three great keepers gets almost nothing from a fourth; this is
the one idea that stops that.
"""

from core.ai.valorisation import estimation_potentiel
from core.config.modeles.racine import Config
from core.domain.club import Club
from core.domain.date import Date
from core.domain.joueur import Joueur
from core.engine.equipe import meilleure_affectation
from core.world.note_globale import note_globale


def note_meilleur_onze(effectif: list[Joueur], formation: str, cfg: Config) -> float:
    if len(effectif) < 11:
        return sum(note_globale(joueur, cfg.attributs) for joueur in effectif) / max(len(effectif), 1)
    onze = meilleure_affectation(effectif, formation, cfg)
    return sum(note_globale(position.joueur, cfg.attributs) for position in onze) / len(onze)


def utilite(joueur: Joueur, club: Club, effectif: list[Joueur], date_actuelle: Date, cfg: Config) -> float:
    avec = note_meilleur_onze([*effectif, joueur], club.formation_preferee, cfg)
    sans = note_meilleur_onze(effectif, club.formation_preferee, cfg)
    brute = avec - sans

    ajustement = _ajustement_personnalite(joueur, club, date_actuelle, cfg)
    return brute * ajustement


def _ajustement_personnalite(joueur: Joueur, club: Club, date_actuelle: Date, cfg: Config) -> float:
    cfg_util = cfg.ia.utilite
    age = joueur.date_naissance.age_a(date_actuelle)
    jeunesse = max((cfg_util.age_seuil_jeunesse - age) / cfg_util.age_seuil_jeunesse, 0.0)

    cfg_est = cfg.demographie.estimation_potentiel
    fourchette = estimation_potentiel(joueur, date_actuelle, cfg)
    incertitude_potentiel = (fourchette.max - fourchette.min) / (2 * cfg_est.bruit_max) if cfg_est.bruit_max else 0.0

    return (1 + cfg_util.poids_preference_jeunes * club.personnalite.preference_jeunes * jeunesse) * (
        1 + cfg_util.poids_appetit_risque * club.personnalite.appetit_risque * incertitude_potentiel
    )
