"""Suite `stats_match_possession`: the stats_match target set, measured
against the production engine (core.engine.match.MoteurPossession)
rather than the analytical oracle — see "État de l'implémentation" in
docs/moteur-match.md.

Re-imports data/ fresh each run instead of a frozen snapshot: "effectifs
figés" (docs/benchmarks.md) exists to stop results drifting as mercato
changes rosters — mercato doesn't exist yet, so nothing can make this
drift between runs. A fresh import is exactly as reproducible right now,
just slower. Revisit once mercato/season progression exist.

Synthetic matchups ("__NIVEAU_70__") are skipped: the possession engine
needs a real onze, not just two force numbers.
"""

import re
from collections import Counter
from pathlib import Path
from random import Random

from core.config.modeles.racine import Config
from core.domain.club import StatutClub
from core.domain.date import Date
from core.domain.geometrie import Couloir
from core.domain.match import TypeEvenement
from core.engine.equipe import composition_depuis_effectif
from core.engine.match import MoteurPossession
from core.world.importation import importer_monde
from benchmarks.rapport import ResultatCible

_RACINE = Path(__file__).resolve().parent.parent.parent.parent
_DATE_DEBUT = Date(2026, 8, 10)
_MOTIF_NIVEAU_SYNTHETIQUE = re.compile(r"^__NIVEAU_(\d+(?:\.\d+)?)__$")


def executer(cfg: Config, rng: Random, iterations: int | None) -> list[ResultatCible]:
    n = iterations or cfg.benchmarks.execution.iterations_defaut_match
    monde, _avertissements = importer_monde(
        _RACINE / "data", cfg, _DATE_DEBUT, cfg.benchmarks.execution.graine_defaut, Random(cfg.benchmarks.execution.graine_defaut)
    )
    moteur = MoteurPossession()

    accumulateurs = {
        "possessions": [], "tirs": [], "xg": [], "possession_pct": [],
        "jaunes": [], "rouges": [], "buts_totaux": 0, "buts_cpa": 0,
    }
    couloirs_tirs: Counter[Couloir] = Counter()

    matchs_reels = [
        affrontement
        for affrontement in cfg.benchmarks.affrontements_reference
        if not _MOTIF_NIVEAU_SYNTHETIQUE.match(affrontement.domicile)
        and not _MOTIF_NIVEAU_SYNTHETIQUE.match(affrontement.exterieur)
    ]

    for affrontement in matchs_reels:
        dom_equipe = _equipe_pour_club(affrontement.domicile, monde, cfg)
        ext_equipe = _equipe_pour_club(affrontement.exterieur, monde, cfg)

        for _ in range(n):
            resultat = moteur.simuler(dom_equipe, ext_equipe, cfg, rng)
            for stats in (resultat.stats_dom, resultat.stats_ext):
                accumulateurs["tirs"].append(stats.tirs)
                accumulateurs["xg"].append(stats.xg)
                accumulateurs["possession_pct"].append(stats.possession_pct)
                accumulateurs["jaunes"].append(stats.cartons_jaunes)
                accumulateurs["rouges"].append(stats.cartons_rouges)
            accumulateurs["buts_totaux"] += resultat.buts_dom + resultat.buts_ext
            for evenement in resultat.evenements:
                if evenement.type is TypeEvenement.TIR:
                    couloirs_tirs[evenement.couloir] += 1
                if evenement.type is TypeEvenement.BUT and evenement.detail is not None:
                    accumulateurs["buts_cpa"] += 1  # detail is only set for corners/coup francs

    cfg_stats = cfg.benchmarks.stats_match

    def moyenne(cle: str) -> float:
        return sum(accumulateurs[cle]) / len(accumulateurs[cle])

    resultats = [
        ResultatCible.depuis_plage("tirs_par_equipe", moyenne("tirs"), cfg_stats.tirs_par_equipe),
        ResultatCible.depuis_plage("xg_par_equipe", moyenne("xg"), cfg_stats.xg_par_equipe),
        ResultatCible.depuis_plage("possession_pct", moyenne("possession_pct"), cfg_stats.possession_pct),
        ResultatCible.depuis_plage("jaunes_par_equipe", moyenne("jaunes"), cfg_stats.jaunes_par_equipe),
        ResultatCible.depuis_plage("rouges_par_equipe", moyenne("rouges"), cfg_stats.rouges_par_equipe),
    ]

    if accumulateurs["buts_totaux"] > 0:
        part_cpa = accumulateurs["buts_cpa"] / accumulateurs["buts_totaux"]
        resultats.append(ResultatCible.depuis_plage("part_buts_coups_arretes", part_cpa, cfg_stats.part_buts_coups_arretes))

    total_tirs_couloir = sum(couloirs_tirs.values())
    if total_tirs_couloir > 0:
        for couloir in Couloir:
            part = couloirs_tirs[couloir] / total_tirs_couloir
            resultats.append(
                ResultatCible.depuis_tolerance(
                    f"repartition_couloirs/{couloir.value}",
                    part,
                    cfg_stats.repartition_couloirs.cible,
                    cfg_stats.repartition_couloirs.tolerance,
                )
            )

    return resultats


def _equipe_pour_club(nom: str, monde, cfg: Config):
    club = next((c for c in monde.clubs.values() if c.nom == nom and c.statut is StatutClub.ACTIF), None)
    if club is None:
        raise KeyError(f"club de reference introuvable ou non actif: {nom!r}")
    return composition_depuis_effectif(club.id, monde.joueurs, club.formation_preferee, 0.0, cfg)
