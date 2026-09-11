"""Corners and free kicks, generated from a turnover in the advanced
zone — see "Coups de pied arrêtés" in docs/moteur-match.md. Only
called for a turnover at Zone.VERITE; returns None (no set piece,
just a normal turnover) most of the time.
"""

from random import Random

from core.config.modeles.racine import Config
from core.domain.geometrie import Couloir, Zone
from core.domain.match import Evenement, TypeEvenement
from core.engine.composites import composite
from core.engine.equipe import PositionOnze
from core.engine.implication import TablesImplication
from core.engine.occasion import ResultatTir, ajuster, evenement_issue, gardien
from core.engine.selection_joueur import tirer_joueur_implique, tirer_joueur_par_attribut


def evaluer_coup_arrete(
    zone: Zone,
    couloir: Couloir,
    minute: int,
    onze_attaquant: tuple[PositionOnze, ...],
    onze_defenseur: tuple[PositionOnze, ...],
    tables: TablesImplication,
    cfg: Config,
    rng: Random,
) -> ResultatTir | None:
    if zone is not Zone.VERITE:
        return None

    cfg_cpa = cfg.moteur.coups_arretes
    tirage = rng.random()
    if tirage < cfg_cpa.probabilite_corner_sur_turnover_avance:
        return _resoudre_corner(minute, couloir, onze_attaquant, onze_defenseur, cfg, rng)
    if tirage < cfg_cpa.probabilite_corner_sur_turnover_avance + cfg_cpa.probabilite_coup_franc_sur_turnover:
        return _resoudre_coup_franc(minute, couloir, onze_attaquant, onze_defenseur, tables, cfg, rng)
    return None


def _resoudre_corner(
    minute: int,
    couloir: Couloir,
    onze_attaquant: tuple[PositionOnze, ...],
    onze_defenseur: tuple[PositionOnze, ...],
    cfg: Config,
    rng: Random,
) -> ResultatTir:
    receptionneur = tirer_joueur_par_attribut(onze_attaquant, "jeu_tete", rng)
    gardien_adverse = gardien(onze_defenseur)

    xg = cfg.moteur.coups_arretes.xg_base_corner
    p_but = ajuster(
        xg,
        composite(receptionneur.joueur, "tete", cfg.attributs),
        composite(gardien_adverse.joueur, "sortie", cfg.attributs),
        cfg.moteur.occasion.sensibilite_tireur_gardien,
    )

    but = rng.random() < p_but
    evenements = (
        Evenement(minute, TypeEvenement.TIR, receptionneur.joueur.id, None, Zone.VERITE, couloir, detail="corner"),
        evenement_issue(minute, but, receptionneur, gardien_adverse, Zone.VERITE, couloir, detail="corner"),
    )
    return ResultatTir(but=but, evenements=evenements, xg=xg)


def _resoudre_coup_franc(
    minute: int,
    couloir: Couloir,
    onze_attaquant: tuple[PositionOnze, ...],
    onze_defenseur: tuple[PositionOnze, ...],
    tables: TablesImplication,
    cfg: Config,
    rng: Random,
) -> ResultatTir:
    tireur = tirer_joueur_implique(onze_attaquant, Zone.VERITE, couloir, tables, phase_attaque=True, rng=rng)
    gardien_adverse = gardien(onze_defenseur)

    xg = cfg.moteur.coups_arretes.xg_base_coup_franc_direct
    p_but = ajuster(
        xg,
        composite(tireur.joueur, "tir", cfg.attributs),
        composite(gardien_adverse.joueur, "arret", cfg.attributs),
        cfg.moteur.occasion.sensibilite_tireur_gardien,
    )

    but = rng.random() < p_but
    evenements = (
        Evenement(minute, TypeEvenement.TIR, tireur.joueur.id, None, Zone.VERITE, couloir, detail="coup_franc"),
        evenement_issue(minute, but, tireur, gardien_adverse, Zone.VERITE, couloir, detail="coup_franc"),
    )
    return ResultatTir(but=but, evenements=evenements, xg=xg)
