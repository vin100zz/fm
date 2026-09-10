"""Suite `match`: win/draw/loss distribution for each reference matchup
in config/benchmarks.json -> affrontements_reference, plus the score
distribution aggregated across all of them. See "Suite match" in
docs/benchmarks.md — the suite to check first.
"""

from collections import Counter
from pathlib import Path
from random import Random

from core.config.modeles.racine import Config
from core.engine.analytique import MoteurAnalytique
from benchmarks.cibles import charger_effectifs_reference, resoudre_equipe
from benchmarks.rapport import ResultatCible

CHEMIN_EFFECTIFS_DEFAUT = Path(__file__).resolve().parent.parent / "effectifs" / "match.json"


def executer(
    cfg: Config, rng: Random, iterations: int | None, chemin_effectifs: Path = CHEMIN_EFFECTIFS_DEFAUT
) -> list[ResultatCible]:
    n = iterations or cfg.benchmarks.execution.iterations_defaut_match
    effectifs = charger_effectifs_reference(chemin_effectifs)
    moteur = MoteurAnalytique()

    resultats: list[ResultatCible] = []
    tous_scores: Counter[str] = Counter()
    ecarts_buts: list[int] = []
    matches_zero_but = 0
    matches_quatre_buts_ou_plus = 0
    total_matches = 0

    for affrontement in cfg.benchmarks.affrontements_reference:
        dom = resoudre_equipe(affrontement.domicile, effectifs)
        ext = resoudre_equipe(affrontement.exterieur, effectifs)

        issues: Counter[str] = Counter()
        for _ in range(n):
            resultat_match = moteur.simuler(dom, ext, cfg, rng)
            if resultat_match.buts_dom > resultat_match.buts_ext:
                issues["victoire"] += 1
            elif resultat_match.buts_dom == resultat_match.buts_ext:
                issues["nul"] += 1
            else:
                issues["defaite"] += 1

            tous_scores[f"{resultat_match.buts_dom}-{resultat_match.buts_ext}"] += 1
            ecarts_buts.append(abs(resultat_match.buts_dom - resultat_match.buts_ext))
            total_matches += 1
            buts_totaux = resultat_match.buts_dom + resultat_match.buts_ext
            if buts_totaux == 0:
                matches_zero_but += 1
            if buts_totaux >= 4:
                matches_quatre_buts_ou_plus += 1

        for issue, cible, tolerance in zip(
            ("victoire", "nul", "defaite"),
            (affrontement.victoire, affrontement.nul, affrontement.defaite),
            affrontement.tolerance,
            strict=True,
        ):
            resultats.append(
                ResultatCible.depuis_tolerance(
                    f"{affrontement.id}/{issue}", issues[issue] / n, cible, tolerance
                )
            )

    resultats += _resultats_distribution_scores(
        cfg, total_matches, tous_scores, ecarts_buts, matches_zero_but, matches_quatre_buts_ou_plus
    )
    return resultats


def _resultats_distribution_scores(
    cfg: Config,
    total_matches: int,
    tous_scores: Counter[str],
    ecarts_buts: list[int],
    matches_zero_but: int,
    matches_quatre_buts_ou_plus: int,
) -> list[ResultatCible]:
    cfg_dist = cfg.benchmarks.distribution_scores

    score_le_plus_frequent = tous_scores.most_common(1)[0][0] if tous_scores else "?"
    ok_score = score_le_plus_frequent in cfg_dist.score_le_plus_frequent

    return [
        ResultatCible.depuis_plage(
            "distribution_scores/part_zero_but",
            matches_zero_but / total_matches,
            cfg_dist.part_matches_zero_but,
        ),
        ResultatCible.depuis_plage(
            "distribution_scores/part_quatre_buts_ou_plus",
            matches_quatre_buts_ou_plus / total_matches,
            cfg_dist.part_matches_quatre_buts_ou_plus,
        ),
        ResultatCible.depuis_plage(
            "distribution_scores/ecart_buts_moyen",
            sum(ecarts_buts) / total_matches,
            cfg_dist.ecart_buts_moyen,
        ),
        ResultatCible(
            nom="distribution_scores/score_le_plus_frequent",
            valeur=None,
            description_cible=f"observe {score_le_plus_frequent}, attendu parmi {cfg_dist.score_le_plus_frequent}",
            statut="ok" if ok_score else "echec",
        ),
    ]
