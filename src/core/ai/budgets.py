"""Club budgets: a revenue estimate feeds both the transfer budget and
the wage cap — the cap is the one that actually keeps the AI honest,
per "Budgets" in docs/ia-gestion.md: "sans lui, l'IA explose en cinq
saisons".

Takes plain fields (reputation, pays, solde) rather than a Club so the
same formula serves both an already-assembled Club and a club still
being built at import time (core/world/importation/construction.py),
which has no Club object yet when it needs a starting budget.
"""

from core.config.modeles.racine import Config


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
