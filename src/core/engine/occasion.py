"""Resolve a chance once the ball reaches VERITE: a cross on the wings,
a shot through the middle — see "Résolution de l'occasion" in
docs/moteur-match.md. Always resolves to either a goal or a turnover;
the turnover feeds back into coups_arretes.py the same way any other
advanced-zone turnover does (a saved shot can become a corner exactly
like a failed final pass can).
"""

import math
from dataclasses import dataclass
from random import Random

from core.config.modeles.racine import Config
from core.domain.geometrie import Couloir, Zone
from core.domain.match import Evenement, TypeEvenement
from core.domain.poste import Poste
from core.engine.composites import composite
from core.engine.equipe import PositionOnze
from core.engine.implication import TablesImplication
from core.engine.selection_joueur import tirer_joueur_implique


@dataclass(frozen=True, slots=True)
class ResultatTir:
    but: bool
    evenements: tuple[Evenement, ...]
    xg: float


def gardien(onze: tuple[PositionOnze, ...]) -> PositionOnze:
    return next(position for position in onze if position.poste is Poste.GB)


def ajuster(xg: float, comp_attaquant: float, comp_defenseur: float, sensibilite: float) -> float:
    """No exact formula is given for "ajuster" in docs/moteur-match.md —
    this shifts xg's log-odds by the attacker/defender composite gap, so
    p_but == xg exactly when both are equal (the base rate is
    calibrated for an average matchup) and the sigmoid keeps the result
    in (0, 1) regardless of how lopsided the gap is.
    """
    xg_borne = min(max(xg, 1e-6), 1 - 1e-6)
    logit = math.log(xg_borne / (1 - xg_borne)) + sensibilite * (comp_attaquant - comp_defenseur)
    return 1 / (1 + math.exp(-logit))


def resoudre_occasion(
    minute: int,
    couloir: Couloir,
    est_contre: bool,
    onze_attaquant: tuple[PositionOnze, ...],
    onze_defenseur: tuple[PositionOnze, ...],
    tables: TablesImplication,
    cfg: Config,
    rng: Random,
) -> ResultatTir:
    """No goal -> the caller turns this into a Turnover at VERITE, same
    as any failed progression.
    """
    if couloir in (Couloir.GAUCHE, Couloir.DROITE):
        return _resoudre_centre(minute, couloir, onze_attaquant, onze_defenseur, tables, cfg, rng)
    return _resoudre_frappe(minute, couloir, est_contre, onze_attaquant, onze_defenseur, tables, cfg, rng)


def _resoudre_frappe(
    minute: int,
    couloir: Couloir,
    est_contre: bool,
    onze_attaquant: tuple[PositionOnze, ...],
    onze_defenseur: tuple[PositionOnze, ...],
    tables: TablesImplication,
    cfg: Config,
    rng: Random,
) -> ResultatTir:
    cfg_occasion = cfg.moteur.occasion
    tireur = tirer_joueur_implique(onze_attaquant, Zone.VERITE, couloir, tables, phase_attaque=True, rng=rng)
    gardien_adverse = gardien(onze_defenseur)

    xg = cfg_occasion.xg_base_frappe * (cfg_occasion.multiplicateur_contre if est_contre else 1.0)
    p_but = ajuster(
        xg,
        composite(tireur.joueur, "tir", cfg.attributs),
        composite(gardien_adverse.joueur, "arret", cfg.attributs),
        cfg_occasion.sensibilite_tireur_gardien,
    )

    but = rng.random() < p_but
    evenements = (
        Evenement(minute, TypeEvenement.TIR, tireur.joueur.id, None, Zone.VERITE, couloir),
        evenement_issue(minute, but, tireur, gardien_adverse, Zone.VERITE, couloir),
    )
    return ResultatTir(but=but, evenements=evenements, xg=xg)


def _resoudre_centre(
    minute: int,
    couloir: Couloir,
    onze_attaquant: tuple[PositionOnze, ...],
    onze_defenseur: tuple[PositionOnze, ...],
    tables: TablesImplication,
    cfg: Config,
    rng: Random,
) -> ResultatTir:
    cfg_occasion = cfg.moteur.occasion
    centreur = tirer_joueur_implique(onze_attaquant, Zone.VERITE, couloir, tables, phase_attaque=True, rng=rng)
    receptionneur = tirer_joueur_implique(onze_attaquant, Zone.VERITE, couloir, tables, phase_attaque=True, rng=rng)
    gardien_adverse = gardien(onze_defenseur)

    xg = cfg_occasion.xg_base_centre
    p_but = ajuster(
        xg,
        composite(receptionneur.joueur, "tete", cfg.attributs),
        composite(gardien_adverse.joueur, "sortie", cfg.attributs),
        cfg_occasion.sensibilite_tireur_gardien,
    )

    but = rng.random() < p_but
    evenements = (
        Evenement(minute, TypeEvenement.TIR, centreur.joueur.id, receptionneur.joueur.id, Zone.VERITE, couloir),
        evenement_issue(minute, but, receptionneur, gardien_adverse, Zone.VERITE, couloir),
    )
    return ResultatTir(but=but, evenements=evenements, xg=xg)


def evenement_issue(
    minute: int, but: bool, tireur: PositionOnze, gardien_adverse: PositionOnze, zone: Zone, couloir: Couloir
) -> Evenement:
    if but:
        return Evenement(minute, TypeEvenement.BUT, tireur.joueur.id, None, zone, couloir)
    return Evenement(minute, TypeEvenement.ARRET, gardien_adverse.joueur.id, tireur.joueur.id, zone, couloir)
