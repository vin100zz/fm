"""Suite `stats_match`, partial: `buts_par_equipe` and
`avantage_domicile_buts` are measurable with the analytical engine —
everything else (tirs, xG, possession, corners, cartons, répartition
par couloir) needs the possession engine (step 5). See
docs/benchmarks.md — normally the suite to calibrate first, but for the
analytical oracle specifically these two targets are the whole
calibration surface for `buts_attendus_base` and `bonus_domicile_buts`.
"""

from pathlib import Path
from random import Random

from core.config.modeles.racine import Config
from core.engine.analytique import MoteurAnalytique
from benchmarks.cibles import charger_effectifs_reference, resoudre_equipe
from benchmarks.rapport import ResultatCible

CHEMIN_EFFECTIFS_DEFAUT = Path(__file__).resolve().parent.parent / "effectifs" / "match.json"

_NON_MESURABLES = (
    "tirs_par_equipe",
    "xg_par_equipe",
    "possession_pct",
    "part_buts_coups_arretes",
    "jaunes_par_equipe",
    "rouges_par_equipe",
    "repartition_couloirs",
    "xg_axe_superieur_aile",
)


def executer(
    cfg: Config, rng: Random, iterations: int | None, chemin_effectifs: Path = CHEMIN_EFFECTIFS_DEFAUT
) -> list[ResultatCible]:
    n = iterations or cfg.benchmarks.execution.iterations_defaut_match
    effectifs = charger_effectifs_reference(chemin_effectifs)
    moteur = MoteurAnalytique()
    cfg_stats = cfg.benchmarks.stats_match

    tous_buts: list[int] = []
    ecarts_dom_moins_ext: list[int] = []
    for affrontement in cfg.benchmarks.affrontements_reference:
        dom = resoudre_equipe(affrontement.domicile, effectifs)
        ext = resoudre_equipe(affrontement.exterieur, effectifs)
        for _ in range(n):
            resultat_match = moteur.simuler(dom, ext, cfg, rng)
            tous_buts.append(resultat_match.buts_dom)
            tous_buts.append(resultat_match.buts_ext)
            ecarts_dom_moins_ext.append(resultat_match.buts_dom - resultat_match.buts_ext)

    resultats = [
        ResultatCible.depuis_tolerance(
            "buts_par_equipe",
            sum(tous_buts) / len(tous_buts),
            cfg_stats.buts_par_equipe.cible,
            cfg_stats.buts_par_equipe.tolerance,
        ),
        ResultatCible.depuis_tolerance(
            "avantage_domicile_buts",
            sum(ecarts_dom_moins_ext) / len(ecarts_dom_moins_ext),
            cfg_stats.avantage_domicile_buts.cible,
            cfg_stats.avantage_domicile_buts.tolerance,
        ),
    ]
    resultats += [
        ResultatCible(
            nom=nom, valeur=None, description_cible="necessite le moteur par possessions (etape 5)",
            statut="non_mesurable",
        )
        for nom in _NON_MESURABLES
    ]
    return resultats
