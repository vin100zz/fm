"""Two ways out of the population — "Sorties" in
docs/progression-demographie.md. Retirement removes a player from the
world entirely (not built here: nothing yet deletes a `Joueur`, that's
the season loop's job); "abandon" only demotes a player to a dormant
club, evaluated here as a pure predicate.
"""

from core.ai.valorisation import estimation_potentiel
from core.config.modeles.racine import Config
from core.domain.date import Date
from core.domain.joueur import Joueur
from core.world.note_globale import note_globale


def probabilite_retraite(joueur: Joueur, date_actuelle: Date, cfg: Config) -> float:
    cfg_r = cfg.demographie.sorties.retraite
    age = joueur.date_naissance.age_a(date_actuelle)
    if age < cfg_r.age_minimal:
        return 0.0

    base = cfg_r.coefficient * (age - cfg_r.age_minimal + 1) ** cfg_r.exposant
    return base * (cfg_r.facteur_niveau_base - cfg_r.facteur_niveau_pente * note_globale(joueur, cfg.attributs) / 100)


def sort_du_perimetre(joueur: Joueur, date_actuelle: Date, cfg: Config) -> bool:
    """A player already outside a club (sold or released, not yet picked
    up by a dormant club) whose age and estimated ceiling put him below
    the perimeter's floor drops to the dormant market — "il reste
    consultable, et pourra remonter s'il progresse".
    """
    cfg_sp = cfg.demographie.sorties.sortie_perimetre
    if cfg_sp.sans_club_requis and joueur.club_id is not None:
        return False

    age = joueur.date_naissance.age_a(date_actuelle)
    if age < cfg_sp.age_minimal:
        return False

    return estimation_potentiel(joueur, date_actuelle, cfg).max < cfg_sp.seuil_potentiel_estime
