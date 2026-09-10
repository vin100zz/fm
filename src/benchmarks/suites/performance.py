"""Suite `performance`. Only "secondes_chargement_donnees" is
measurable at this point in the ordre de construction — the rest need
the possession engine, a season calendar, or save/load, none of which
exist yet. Reported as "non_mesurable", not silently skipped, so the
gap stays visible in every run. See docs/benchmarks.md.
"""

import time
from pathlib import Path
from random import Random

from core.config.modeles.racine import Config
from core.domain.date import Date
from core.world.importation import importer_monde
from benchmarks.rapport import ResultatCible

_RACINE = Path(__file__).resolve().parent.parent.parent.parent
_DATE_DEBUT = Date(2026, 8, 10)

_NON_MESURABLES = (
    ("ms_par_match_possession", "necessite le moteur par possessions (etape 5)"),
    ("secondes_par_saison_complete", "necessite le calendrier de saison (etape 5+)"),
    ("secondes_100_saisons_analytique", "necessite le calendrier de saison (etape 5+)"),
    ("secondes_sauvegarde", "necessite la persistance de partie"),
)


def executer(cfg: Config, rng: Random, iterations: int | None) -> list[ResultatCible]:
    cfg_perf = cfg.benchmarks.performance

    debut = time.perf_counter()
    importer_monde(_RACINE / "data", cfg, _DATE_DEBUT, cfg.benchmarks.execution.graine_defaut, rng)
    duree = time.perf_counter() - debut

    resultats = [
        ResultatCible(
            nom="secondes_chargement_donnees",
            valeur=duree,
            description_cible=f"cible < {cfg_perf.secondes_chargement_donnees}s",
            statut="ok" if duree < cfg_perf.secondes_chargement_donnees else "echec",
        )
    ]
    resultats += [
        ResultatCible(nom=nom, valeur=None, description_cible=raison, statut="non_mesurable")
        for nom, raison in _NON_MESURABLES
    ]
    return resultats
