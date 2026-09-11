"""The démographie feedback loop — "Boucle de rétroaction — le point
clé" in docs/progression-demographie.md: comparing observed population
to target, each summer, bucket by bucket, on each axis independently
(niveau, poste, nation), is what keeps the population stable over many
seasons — not the accuracy of the initial draw.

Cohort size itself needs no function: "dimensionner la cohorte sur les
départs réels de l'année" means the season loop (not built yet, see
docs/ia-gestion.md's own "hors périmètre" note for the same reason)
simply generates as many regens as players actually left that year.

`compter_par_*` return raw counts, not proportions: `corriger`'s
`max(observe, 1)` guards against an empty bucket, which only makes
sense against a count (an empty bucket's proportion is already 0, not
something to floor at 1).
"""

from typing import Iterable

from core.config.modeles.attributs import ConfigAttributs
from core.domain.joueur import Joueur
from core.world.note_globale import note_globale


def corriger(cible: float, observe: float, kappa: float) -> float:
    return (cible / max(observe, 1.0)) ** kappa


def corriger_poids(cibles: dict[str, float], observes: dict[str, int], kappa: float) -> dict[str, float]:
    """`cibles` are proportions (as in `cible_postes`, summing to 1.0);
    `observes` are the matching raw counts from `compter_par_*`. Each
    bucket's proportion is corrected by comparing its *expected* count
    (proportion × observed population total) to its actual count, then
    the result is renormalised so it can replace `cibles` directly in a
    weighted draw.
    """
    population_totale = sum(observes.values())
    corriges = {
        cle: poids_cible * corriger(poids_cible * population_totale, observes.get(cle, 0), kappa)
        for cle, poids_cible in cibles.items()
    }
    total = sum(corriges.values())
    if total <= 0:
        return dict(cibles)
    return {cle: poids / total for cle, poids in corriges.items()}


def compter_par_poste(population: Iterable[Joueur]) -> dict[str, int]:
    comptes: dict[str, int] = {}
    for joueur in population:
        comptes[joueur.poste.value] = comptes.get(joueur.poste.value, 0) + 1
    return comptes


def compter_par_nation(population: Iterable[Joueur], nationalites_simulees: frozenset[str]) -> dict[str, int]:
    """Nations outside `nationalites_simulees` are not individually
    targeted (the vivier extérieur has no per-country cible) so they are
    not broken out here — only the axis actually driving generation.
    """
    comptes: dict[str, int] = {}
    for joueur in population:
        if joueur.nationalite in nationalites_simulees:
            comptes[joueur.nationalite] = comptes.get(joueur.nationalite, 0) + 1
    return comptes


def bucket_de(valeur: float, buckets: list[tuple[int, int]]) -> tuple[int, int] | None:
    for bas, haut in buckets:
        if bas <= valeur < haut:
            return (bas, haut)
    return None


def compter_par_bucket_niveau(
    population: Iterable[Joueur], buckets: list[tuple[int, int]], cfg_attributs: ConfigAttributs
) -> dict[tuple[int, int], int]:
    comptes: dict[tuple[int, int], int] = {}
    for joueur in population:
        bucket = bucket_de(note_globale(joueur, cfg_attributs), buckets)
        if bucket is not None:
            comptes[bucket] = comptes.get(bucket, 0) + 1
    return comptes
