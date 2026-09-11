"""Club budgets: a revenue estimate feeds both the transfer budget and
the wage cap — the cap is the one that actually keeps the AI honest,
per "Budgets" in docs/ia-gestion.md: "sans lui, l'IA explose en cinq
saisons".

Takes plain fields (reputation, pays, solde) rather than a Club so the
same formula serves both an already-assembled Club and a club still
being built at import time (core/world/importation/construction.py),
which has no Club object yet when it needs a starting budget.

`masse_salariale_actuelle`/`effectifs_par_club` (added for the club
list/detail screens, docs/ui.md) compute the *current* wage bill from
the squad, as opposed to `calculer_masse_salariale_max` above which is
the cap — same "sous contrat" filter `core/world/mercato.py`'s
`_peut_se_permettre` already used inline, factored out here so the API
layer and the mercato AI can't quietly disagree on what counts.
"""

from collections import defaultdict
from typing import Iterable

from core.config.modeles.racine import Config
from core.domain.joueur import Joueur


def calculer_revenus(reputation: int, pays: str, classement_precedent: int | None, cfg: Config) -> float:
    cfg_rev = cfg.ia.budgets.revenus
    multiplicateur = cfg_rev.multiplicateur_pays.get(pays, 1.0)
    revenus = reputation * cfg_rev.base_par_point_reputation * multiplicateur

    if classement_precedent is not None and classement_precedent >= 1:
        revenus += cfg_rev.bonus_classement_premier * (cfg_rev.decroissance_par_place ** (classement_precedent - 1))
    return revenus


def calculer_budget_transfert(revenus_saison: float, solde: int, ventes_realisees: int, cfg: Config) -> int:
    cfg_b = cfg.ia.budgets
    return round(revenus_saison * cfg_b.part_revenus_transfert + solde * cfg_b.part_solde_transfert + ventes_realisees)


def calculer_masse_salariale_max(revenus_saison: float, cfg: Config) -> int:
    cfg_b = cfg.ia.budgets
    return round(revenus_saison * cfg_b.part_revenus_salaires / cfg_b.semaines_par_an)


def masse_salariale_actuelle(effectif: Iterable[Joueur]) -> int:
    """Contracted players only — a joueur can have a club_id but no
    Contrat (source data missing "Contract End", see
    core/world/importation/construction.py::_construire_contrat)."""
    return sum(joueur.contrat.salaire_hebdo for joueur in effectif if joueur.contrat is not None)


def effectifs_par_club(joueurs: Iterable[Joueur]) -> tuple[dict[int, int], dict[int, int]]:
    """One pass over the whole population -> (nb sous contrat, masse
    salariale) per club_id. The club list screen needs this for every
    club matching its filters *before* pagination slices the page down
    to 50 — building a per-club effectif via a fresh filter for each of
    up to ~26 000 clubs would be O(clubs x joueurs); this is O(joueurs)
    once, looked up per club afterwards.
    """
    nb_sous_contrat: dict[int, int] = defaultdict(int)
    masse_salariale: dict[int, int] = defaultdict(int)
    for joueur in joueurs:
        if joueur.club_id is not None and joueur.contrat is not None:
            nb_sous_contrat[joueur.club_id] += 1
            masse_salariale[joueur.club_id] += joueur.contrat.salaire_hebdo
    return nb_sous_contrat, masse_salariale
