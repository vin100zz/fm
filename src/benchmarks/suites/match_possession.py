"""Suite `match_possession`: win/draw/loss distribution for each real
reference matchup, measured against the production engine
(core.engine.match.MoteurPossession). See suites/stats_match_possession.py
for why this re-imports data/ fresh rather than using a frozen snapshot,
and why synthetic "__NIVEAU_N__" matchups are skipped (no real onze to
build for them).
"""

import re
from pathlib import Path
from random import Random

from core.config.modeles.racine import Config
from core.domain.club import StatutClub
from core.domain.date import Date
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

    resultats: list[ResultatCible] = []
    for affrontement in cfg.benchmarks.affrontements_reference:
        if _MOTIF_NIVEAU_SYNTHETIQUE.match(affrontement.domicile) or _MOTIF_NIVEAU_SYNTHETIQUE.match(
            affrontement.exterieur
        ):
            continue

        dom = _equipe_pour_club(affrontement.domicile, monde, cfg)
        ext = _equipe_pour_club(affrontement.exterieur, monde, cfg)

        issues = {"victoire": 0, "nul": 0, "defaite": 0}
        for _ in range(n):
            resultat_match = moteur.simuler(dom, ext, cfg, rng)
            if resultat_match.buts_dom > resultat_match.buts_ext:
                issues["victoire"] += 1
            elif resultat_match.buts_dom == resultat_match.buts_ext:
                issues["nul"] += 1
            else:
                issues["defaite"] += 1

        for issue, cible, tolerance in zip(
            ("victoire", "nul", "defaite"),
            (affrontement.victoire, affrontement.nul, affrontement.defaite),
            affrontement.tolerance,
            strict=True,
        ):
            resultats.append(
                ResultatCible.depuis_tolerance(f"{affrontement.id}/{issue}", issues[issue] / n, cible, tolerance)
            )

    return resultats


def _equipe_pour_club(nom: str, monde, cfg: Config):
    club = next((c for c in monde.clubs.values() if c.nom == nom and c.statut is StatutClub.ACTIF), None)
    if club is None:
        raise KeyError(f"club de reference introuvable ou non actif: {nom!r}")
    return composition_depuis_effectif(club.id, monde.joueurs, club.formation_preferee, 0.0, cfg)
