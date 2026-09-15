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

**Recurring cash flow (2026-09-12, explicit user instruction)**:
`revenu_mensuel`/`depense_mensuelle_salaires` feed
`core/world/finances.py`'s monthly wage/billetterie flux, and
`prime_classement` feeds `core/world/saison.py`'s annual, classement-based
payout — see "Budgets" in docs/ia-gestion.md for why a recurring economy
was needed on top of the once-at-import `calculer_budget_transfert`/
`calculer_masse_salariale_max` below.
"""

from collections import defaultdict
from typing import Iterable

from core.config.modeles.racine import Config
from core.domain.joueur import Joueur


def prime_classement(place: int, cfg: Config) -> int:
    """Lump-sum competition prize for one final league position, paid
    once a year at season rollover — factored out of calculer_revenus
    so it can be paid against a season's *actual* classement instead of
    the classement_precedent estimate calculer_revenus takes at import.
    """
    cfg_rev = cfg.ia.budgets.revenus
    return round(cfg_rev.bonus_classement_premier * cfg_rev.decroissance_par_place ** (place - 1))


def calculer_revenus(reputation: int, pays: str, classement_precedent: int | None, cfg: Config) -> float:
    cfg_rev = cfg.ia.budgets.revenus
    multiplicateur = cfg_rev.multiplicateur_pays.get(pays, 1.0)
    revenus = reputation * cfg_rev.base_par_point_reputation * multiplicateur

    if classement_precedent is not None and classement_precedent >= 1:
        revenus += prime_classement(classement_precedent, cfg)
    return revenus


def revenu_mensuel(masse_salariale_hebdo: int, cfg: Config) -> int:
    """Recurring billetterie/merchandising income, credited every month
    (core/world/finances.py) — anchored on the club's *real* wages
    (2026-09-12, explicit user instruction), not on reputation.

    Three passes the same day, each measured against the real dataset
    before moving to the next:

    1. `calculer_revenus(reputation, pays, None, cfg) / 12` — reputation-
       linear, same split as the once-at-import `revenus_saison`. Once
       `masse_salariale_max` got anchored on real imported wages
       (`masse_salariale_max_reelle`) instead of reputation, this stayed
       comically small next to it for elite clubs: Real Madrid netting a
       chronic ~-11M€/mois deficit, -318M€ over 4 simulated seasons.
    2. Anchored on `masse_salariale_max` (the real-wage-based *cap*)
       instead, inverting `part_revenus_salaires` (0.62) so wages could
       never exceed that share of revenue. Overshot the other way: a
       fixed ceiling pays out regardless of the actual squad, and
       mercato only caps *how many* deals a club pursues per window
       (`negociations_actives_max`/`tentatives_prospection_max`), not
       spending relative to income — Real Madrid accumulated over a
       billion euros of unspent `budget_transfert` in 4 seasons.
    3. **Anchored on the wage bill a club is *actually* carrying
       (`masse_salariale_actuelle`), with a much smaller margin
       (`marge_revenu_mensuel`, 0.15, not `part_revenus_salaires`'s
       implied 61%)** — explicit user instruction ("on ne peut pas juste
       réduire les revenus ?") once step 2's real-wage anchor alone still
       left several hundred million euros of unspent surplus after 4
       seasons. A smaller, dedicated margin (rather than reusing
       `part_revenus_salaires`, which also drives the unrelated
       import-time cap-seeding formula) keeps this one tunable on its
       own without touching that formula."""
    cfg_b = cfg.ia.budgets
    salaire_mensuel = masse_salariale_hebdo * cfg_b.semaines_par_an / 12
    return round(salaire_mensuel * (1 + cfg_b.marge_revenu_mensuel))


def depense_mensuelle_salaires(effectif: Iterable[Joueur], cfg: Config) -> int:
    """Monthly wage bill actually paid out, from the same weekly
    salaire_hebdo figures calculer_masse_salariale_max caps."""
    cfg_b = cfg.ia.budgets
    return round(masse_salariale_actuelle(effectif) * cfg_b.semaines_par_an / 12)


def calculer_budget_transfert(revenus_saison: float, solde: int, ventes_realisees: int, cfg: Config) -> int:
    cfg_b = cfg.ia.budgets
    return round(revenus_saison * cfg_b.part_revenus_transfert + solde * cfg_b.part_solde_transfert + ventes_realisees)


def calculer_masse_salariale_max(revenus_saison: float, cfg: Config) -> int:
    cfg_b = cfg.ia.budgets
    return round(revenus_saison * cfg_b.part_revenus_salaires / cfg_b.semaines_par_an)


def masse_salariale_max_reelle(masse_salariale_importee: int, plafond_reputation: int, cfg: Config) -> int:
    """Le plafond salarial d'un club actif est ancré sur sa masse
    salariale réellement importée (+ marge), pas sur la seule réputation
    (2026-09-12, corrigé, demande explicite de l'utilisateur) —
    `calculer_masse_salariale_max` ci-dessus sous-évaluait drastiquement
    les très grands clubs : mesuré, Real Madrid importe 5,3M€/semaine de
    salaires réels contre un plafond dérivé de la réputation à
    1,03M€/semaine (x5,2), ce qui bloquait tout renouvellement de son
    propre effectif (`decision_renouvellement`'s `sous_plafond`) et
    l'a fait s'effondrer à 6 joueurs sur 4 saisons simulées — voir
    "Budgets" dans docs/ia-gestion.md.

    `plafond_reputation` reste un plancher, pas juste un solde de repli
    à zéro : un club dont les données de contrat sont absentes ou
    clairsemées (`masse_salariale_actuelle` alors nulle ou faible,
    `_construire_contrat`) garde un plafond dérivé de sa réputation
    plutôt que de se retrouver bloqué à ~0.
    """
    cfg_b = cfg.ia.budgets
    plafond_reel = round(masse_salariale_importee * (1 + cfg_b.marge_masse_salariale_initiale))
    return max(plafond_reel, plafond_reputation)


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
